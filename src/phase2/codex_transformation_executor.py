from __future__ import annotations

from .postgres_loader import (
    PostgresLoadError,
    _adapt,
    _create_table,
    _require_psycopg,
    load_env,
    psycopg,
    sql,
)
from .synthetic_data_generator import table_generation_order


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


def _ensure_schema_and_tables(conn, model, schema, *, create_schema_if_missing, create_tables_if_missing, result):
    if create_schema_if_missing:
        conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
        result["schema_creation_status"] = "created_or_already_exists"
    else:
        exists = conn.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", [schema]).fetchone()
        result["schema_creation_status"] = "exists" if exists else "missing"
        if not exists:
            raise PostgresLoadError(f"Target schema {schema} does not exist. Use --create-schema-if-missing to create it.")

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
    tables = {table.name: table for table in model.tables}
    for table_name, rows in load_table_rows.items():
        table = tables[table_name]
        columns = table.column_names()
        insert = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
            sql.Identifier(schema),
            sql.Identifier(table.name),
            sql.SQL(", ").join(sql.Identifier(col) for col in columns),
            sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        )
        values = [[_adapt(row.get(col)) for col in columns] for row in rows]
        with conn.cursor() as cur:
            cur.executemany(insert, values)
        inserted[table_name] = len(values)
    return inserted


def _execute_sql_group(conn, schema, statements, label, result):
    before_after = {}
    for statement in statements:
        result["executed_sql"][label].append(statement)
        result["failing_sql"] = statement
        conn.execute(sql.SQL("SET LOCAL search_path TO {}, pg_temp").format(sql.Identifier(schema)))
        conn.execute(statement)
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


def execute_codex_transformation(model, etl_response, pipeline_plan, *, create_schema_if_missing=False, create_tables_if_missing=False, truncate_before_load=False, allow_insert_into_nonempty_tables=False):
    result = _default_result()
    try:
        _require_psycopg()
        cfg = load_env()
        schema = cfg["target_schema"]
        result["target_schema"] = schema
        with psycopg.connect(host=cfg["host"], port=cfg["port"], dbname=cfg["dbname"], user=cfg["user"], password=cfg["password"], sslmode=cfg["sslmode"]) as conn:
            try:
                result["transaction_status"] = "in_progress"
                _ensure_schema_and_tables(conn, model, schema, create_schema_if_missing=create_schema_if_missing, create_tables_if_missing=create_tables_if_missing, result=result)
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
                    _execute_sql_group(conn, schema, etl_response.get(label, []), label, result)
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
