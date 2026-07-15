from __future__ import annotations

import re

from .postgres_loader import (
    PostgresLoadError,
    _adapt,
    _connect,
    _create_table,
    _require_psycopg,
    load_env,
    sql,
)
from .synthetic_data_generator import table_generation_order


def _quote_identifier(identifier: str) -> str:
    return '"' + str(identifier).replace('"', '""') + '"'


def _identifier_pattern(identifier: str) -> str:
    quoted = re.escape(_quote_identifier(identifier))
    unquoted = re.escape(identifier)
    return rf"(?:{quoted}|{unquoted})"


def _rewrite_sql_code_segments(statement: str, transform) -> str:
    """Apply a transform only to SQL code, preserving strings and comments."""
    output = []
    code = []

    def flush_code():
        if code:
            output.append(transform("".join(code)))
            code.clear()

    index = 0
    length = len(statement)
    while index < length:
        if statement[index] == "'":
            flush_code()
            end = index + 1
            while end < length:
                if statement[end] == "'":
                    if end + 1 < length and statement[end + 1] == "'":
                        end += 2
                        continue
                    end += 1
                    break
                end += 1
            output.append(statement[index:end])
            index = end
            continue
        if statement.startswith("--", index):
            flush_code()
            end = statement.find("\n", index)
            end = length if end == -1 else end
            output.append(statement[index:end])
            index = end
            continue
        if statement.startswith("/*", index):
            flush_code()
            end = statement.find("*/", index + 2)
            end = length if end == -1 else end + 2
            output.append(statement[index:end])
            index = end
            continue
        if statement[index] == "$":
            dollar_match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", statement[index:])
            if dollar_match:
                delimiter = dollar_match.group(0)
                closing = statement.find(delimiter, index + len(delimiter))
                if closing != -1:
                    flush_code()
                    end = closing + len(delimiter)
                    output.append(statement[index:end])
                    index = end
                    continue
        code.append(statement[index])
        index += 1
    flush_code()
    return "".join(output)


def _normalize_sql_for_target_schema(statement, model, schema):
    """Map known DDL schema-qualified tables into the approved target schema."""
    replacements = []
    for table in model.tables:
        if not table.schema:
            continue
        qualified_pattern = (
            rf"(?<![A-Za-z0-9_$\"])"
            rf"{_identifier_pattern(table.schema)}\s*\.\s*{_identifier_pattern(table.name)}"
            rf"(?![A-Za-z0-9_$\"])"
        )
        replacements.append(
            (
                len(table.full_name),
                re.compile(qualified_pattern, re.IGNORECASE),
                f"{_quote_identifier(schema)}.{_quote_identifier(table.name)}",
            )
        )

    def transform(code):
        normalized = code
        for _, pattern, replacement in sorted(replacements, reverse=True, key=lambda item: item[0]):
            normalized = pattern.sub(replacement, normalized)
        return normalized

    return _rewrite_sql_code_segments(statement, transform)


def _default_result():
    return {
        "status": "failed",
        "target_schema": "",
        "inserted_rows": {},
        "transformed_rows": {},
        "table_data": {},
        "executed_sql": {"staging_sql": [], "dimension_sql": [], "fact_sql": []},
        "errors": [],
        "schema_creation_status": "not_attempted",
        "table_creation_status": "not_attempted",
        "transaction_status": "not_started",
        "failing_sql": "",
    }


def _ensure_schema_and_tables(
    conn,
    model,
    schema,
    *,
    create_schema_if_missing,
    create_tables_if_missing,
    recreate_schema,
    result,
):
    if recreate_schema:
        conn.execute(
            sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema))
        )
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        result["schema_creation_status"] = "recreated"
        create_tables_if_missing = True
    elif create_schema_if_missing:
        conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
        result["schema_creation_status"] = "created_or_already_exists"
    else:
        exists = conn.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
            [schema],
        ).fetchone()
        result["schema_creation_status"] = "exists" if exists else "missing"
        if not exists:
            raise PostgresLoadError(f"Target schema {schema} does not exist.")

    table_status = "all_tables_exist"
    for table in table_generation_order(model):
        exists = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
            [schema, table.name],
        ).fetchone()
        if not exists:
            if not create_tables_if_missing:
                raise PostgresLoadError(f"Table {schema}.{table.name} does not exist. Use --create-tables-if-missing to create it.")
            _create_table(conn, table, schema)
            table_status = "created_missing_tables"
    result["table_creation_status"] = table_status


def _truncate_tables(conn, model, schema):
    for table in reversed(table_generation_order(model)):
        conn.execute(sql.SQL("TRUNCATE TABLE {}.{} CASCADE").format(sql.Identifier(schema), sql.Identifier(table.name)))


def _insert_load_rows(conn, model, schema, load_table_rows):
    inserted = {}
    tables = {}
    for table in model.tables:
        tables[table.name.lower()] = table
        tables[table.full_name.lower()] = table
    for table_name, rows in load_table_rows.items():
        lookup_name = str(table_name).lower()
        if lookup_name not in tables:
            raise PostgresLoadError(f"Codex load rows reference unknown model table {table_name}.")
        table = tables[lookup_name]
        if not isinstance(rows, list):
            raise PostgresLoadError(f"Codex load rows for {table_name} must be a list.")

        allowed_columns = set(table.column_names())
        grouped_rows = {}
        for row_index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise PostgresLoadError(f"Codex load row {table_name}[{row_index}] must be an object.")
            unknown_columns = set(row) - allowed_columns
            if unknown_columns:
                raise PostgresLoadError(
                    f"Codex load row {table_name}[{row_index}] contains unknown columns: "
                    f"{', '.join(sorted(unknown_columns))}."
                )
            provided_columns = tuple(column for column in table.column_names() if column in row)
            if not provided_columns:
                raise PostgresLoadError(
                    f"Codex load row {table_name}[{row_index}] has no valid model columns to insert."
                )
            grouped_rows.setdefault(provided_columns, []).append(
                [_adapt(row[column]) for column in provided_columns]
            )

        for columns, values in grouped_rows.items():
            insert = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
                sql.Identifier(schema),
                sql.Identifier(table.name),
                sql.SQL(", ").join(sql.Identifier(col) for col in columns),
                sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            )
            with conn.cursor() as cur:
                cur.executemany(insert, values)
        inserted[table.name] = len(rows)
    return inserted


def _execute_sql_group(conn, schema, model, statements, label, result):
    before_after = {}
    for statement in statements:
        normalized_statement = _normalize_sql_for_target_schema(statement, model, schema)
        result["executed_sql"][label].append(normalized_statement)
        result["failing_sql"] = normalized_statement
        conn.execute(sql.SQL("SET LOCAL search_path TO {}, pg_temp").format(sql.Identifier(schema)))
        conn.execute(normalized_statement)
    return before_after


def _row_counts(conn, model, schema):
    counts = {}
    for table in model.tables:
        counts[table.name] = conn.execute(
            sql.SQL("SELECT COUNT(*) FROM {}.{}").format(sql.Identifier(schema), sql.Identifier(table.name))
        ).fetchone()[0]
    return counts


def _read_table_data(conn, model, schema):
    data = {}
    for table in model.tables:
        columns = table.column_names()
        query = sql.SQL("SELECT {} FROM {}.{}").format(
            sql.SQL(", ").join(sql.Identifier(col) for col in columns),
            sql.Identifier(schema),
            sql.Identifier(table.name),
        )
        rows = conn.execute(query).fetchall()
        data[table.name] = [dict(zip(columns, row)) for row in rows]
    return data


def read_existing_postgres_data(model, *, target_schema=None):
    """Read all parsed model tables from the configured target schema.

    This is intentionally read-only and lets a completed PostgreSQL ELT run be
    revalidated/exported without invoking the generation engine again.
    """
    result = _default_result()
    try:
        _require_psycopg()
        cfg = load_env(target_schema)
        schema = cfg["target_schema"]
        result["target_schema"] = schema
        with _connect(cfg) as conn:
            missing = []
            for table in model.tables:
                exists = conn.execute(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_name = %s",
                    [schema, table.name],
                ).fetchone()
                if not exists:
                    missing.append(table.name)
            if missing:
                raise PostgresLoadError(
                    f"Target schema {schema} is missing parsed model tables: "
                    f"{', '.join(missing)}."
                )
            result["transformed_rows"] = _row_counts(conn, model, schema)
            result["table_data"] = _read_table_data(conn, model, schema)
            result["schema_creation_status"] = "existing_read_only"
            result["table_creation_status"] = "all_tables_exist"
            result["transaction_status"] = "read_only"
            result["status"] = "passed"
    except Exception as exc:
        result["errors"].append(str(exc))
    return result


def execute_codex_transformation(
    model,
    etl_response,
    pipeline_plan,
    *,
    target_schema=None,
    create_schema_if_missing=False,
    create_tables_if_missing=False,
    truncate_before_load=False,
    allow_insert_into_nonempty_tables=False,
    recreate_schema=False,
):
    result = _default_result()
    try:
        _require_psycopg()
        cfg = load_env(target_schema)
        schema = cfg["target_schema"]
        result["target_schema"] = schema
        with _connect(cfg) as conn:
            try:
                result["transaction_status"] = "in_progress"
                _ensure_schema_and_tables(
                    conn,
                    model,
                    schema,
                    create_schema_if_missing=create_schema_if_missing,
                    create_tables_if_missing=create_tables_if_missing,
                    recreate_schema=recreate_schema,
                    result=result,
                )
                if truncate_before_load:
                    _truncate_tables(conn, model, schema)
                elif not allow_insert_into_nonempty_tables:
                    counts = _row_counts(conn, model, schema)
                    nonempty = [name for name, count in counts.items() if count]
                    if nonempty:
                        raise PostgresLoadError(f"Target schema {schema} contains non-empty tables: {', '.join(nonempty)}. Use --allow-insert-into-nonempty-tables or --truncate-before-load.")
                conn.execute(sql.SQL("SET LOCAL search_path TO {}, pg_temp").format(sql.Identifier(schema)))
                result["inserted_rows"] = _insert_load_rows(conn, model, schema, etl_response.get("load_table_rows", {}))
                for label in ("staging_sql", "dimension_sql", "fact_sql"):
                    _execute_sql_group(conn, schema, model, etl_response.get(label, []), label, result)
                result["failing_sql"] = ""
                result["transformed_rows"] = _row_counts(conn, model, schema)
                result["table_data"] = _read_table_data(conn, model, schema)
                conn.commit()
                result["transaction_status"] = "committed"
                result["status"] = "passed"
            except Exception as exc:
                conn.rollback()
                result["transaction_status"] = "rolled_back"
                failing = f" Failing SQL: {result['failing_sql']}" if result.get("failing_sql") else ""
                raise PostgresLoadError(f"Codex ELT transaction failed: {exc}.{failing}") from exc
    except Exception as exc:
        result["errors"].append(str(exc))
        result["inserted_rows"] = {}
        result["transformed_rows"] = {}
        result["table_data"] = {}
    return result
