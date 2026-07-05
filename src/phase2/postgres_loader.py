import os
from decimal import Decimal
from dotenv import load_dotenv
import psycopg
from psycopg import sql

from .synthetic_data_generator import table_generation_order


class PostgresLoadError(Exception):
    pass


def _quote_type(data_type):
    return sql.SQL(data_type)


def _column_ddl(column):
    pieces = [sql.Identifier(column.name), _quote_type(column.data_type)]
    if not column.nullable or column.is_primary_key:
        pieces.append(sql.SQL("NOT NULL"))
    return sql.SQL(" ").join(pieces)


def _adapt(value):
    return value


def load_env():
    load_dotenv()
    required = ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_TARGET_SCHEMA"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise PostgresLoadError(f"Missing required PostgreSQL environment variable(s): {', '.join(missing)}")
    schema = os.getenv("POSTGRES_TARGET_SCHEMA")
    if schema.lower() == "public":
        raise PostgresLoadError("POSTGRES_TARGET_SCHEMA must not be public.")
    return {
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT"),
        "dbname": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "sslmode": os.getenv("POSTGRES_SSLMODE", "prefer"),
        "target_schema": schema,
    }


def _create_table(conn, table, schema):
    column_defs = [_column_ddl(column) for column in table.columns]
    constraints = []
    if table.primary_key:
        constraints.append(sql.SQL("PRIMARY KEY ({})").format(sql.SQL(", ").join(sql.Identifier(col) for col in table.primary_key)))
    for fk in table.foreign_keys:
        constraints.append(sql.SQL("FOREIGN KEY ({}) REFERENCES {}.{} ({})").format(
            sql.SQL(", ").join(sql.Identifier(col) for col in fk.child_columns),
            sql.Identifier(schema),
            sql.Identifier(fk.parent_table),
            sql.SQL(", ").join(sql.Identifier(col) for col in fk.parent_columns),
        ))
    ddl = sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} ({})").format(
        sql.Identifier(schema), sql.Identifier(table.name), sql.SQL(", ").join(column_defs + constraints)
    )
    conn.execute(ddl)


def load_to_postgres(model, data, *, create_schema_if_missing=False, create_tables_if_missing=False, truncate_before_load=False, allow_insert_into_nonempty_tables=False):
    cfg = {}
    inserted = {}
    errors = []
    schema_status = "not_attempted"
    table_status = "not_attempted"
    transaction_status = "not_started"
    try:
        cfg = load_env()
        with psycopg.connect(host=cfg["host"], port=cfg["port"], dbname=cfg["dbname"], user=cfg["user"], password=cfg["password"], sslmode=cfg["sslmode"]) as conn:
            try:
                if create_schema_if_missing:
                    conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(cfg["target_schema"])))
                    schema_status = "created_or_already_exists"
                else:
                    exists = conn.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", [cfg["target_schema"]]).fetchone()
                    schema_status = "exists" if exists else "missing"
                    if not exists:
                        raise PostgresLoadError(f"Target schema {cfg['target_schema']} does not exist. Use --create-schema-if-missing to create it.")

                for table in model.tables:
                    exists = conn.execute(
                        "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                        [cfg["target_schema"], table.name],
                    ).fetchone()
                    if not exists:
                        if create_tables_if_missing:
                            _create_table(conn, table, cfg["target_schema"])
                            table_status = "created_missing_tables"
                        else:
                            raise PostgresLoadError(f"Table {cfg['target_schema']}.{table.name} does not exist. Use --create-tables-if-missing to create it.")
                    count = conn.execute(
                        sql.SQL("SELECT COUNT(*) FROM {}.{}").format(sql.Identifier(cfg["target_schema"]), sql.Identifier(table.name))
                    ).fetchone()[0]
                    if count and not truncate_before_load and not allow_insert_into_nonempty_tables:
                        raise PostgresLoadError(f"Table {cfg['target_schema']}.{table.name} is non-empty. Use --allow-insert-into-nonempty-tables or --truncate-before-load.")
                    if exists and table_status == "not_attempted":
                        table_status = "all_tables_exist"
                    if truncate_before_load:
                        conn.execute(sql.SQL("TRUNCATE TABLE {}.{} CASCADE").format(sql.Identifier(cfg["target_schema"]), sql.Identifier(table.name)))

                transaction_status = "in_progress"
                for table in table_generation_order(model):
                    columns = table.column_names()
                    insert = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
                        sql.Identifier(cfg["target_schema"]),
                        sql.Identifier(table.name),
                        sql.SQL(", ").join(sql.Identifier(col) for col in columns),
                        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
                    )
                    values = [[_adapt(row.get(col)) for col in columns] for row in data[table.name]]
                    with conn.cursor() as cur:
                        cur.executemany(insert, values)
                    inserted[table.name] = len(values)
                conn.commit()
                transaction_status = "committed"
            except Exception:
                conn.rollback()
                inserted = {}
                transaction_status = "rolled_back"
                raise
    except Exception as exc:
        errors.append(str(exc))
        return {"status": "failed", "target_schema": cfg.get("target_schema", ""), "inserted_rows": inserted, "errors": errors, "schema_creation_status": schema_status, "table_creation_status": table_status, "transaction_status": transaction_status}
    return {"status": "passed", "target_schema": cfg["target_schema"], "inserted_rows": inserted, "errors": [], "schema_creation_status": schema_status, "table_creation_status": table_status, "transaction_status": transaction_status}


def validate_postgres_load(model, expected_counts):
    cfg = load_env()
    errors = []
    row_counts = {}
    with psycopg.connect(host=cfg["host"], port=cfg["port"], dbname=cfg["dbname"], user=cfg["user"], password=cfg["password"], sslmode=cfg["sslmode"]) as conn:
        for table in model.tables:
            actual = conn.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(sql.Identifier(cfg["target_schema"]), sql.Identifier(table.name))).fetchone()[0]
            expected = expected_counts.get(table.name, 0)
            row_counts[table.name] = {"expected": expected, "actual": actual}
            if actual < expected:
                errors.append(f"{table.name}: expected at least {expected} rows, found {actual}.")
            for fk in table.foreign_keys:
                conditions = [sql.SQL("c.{} IS NOT NULL").format(sql.Identifier(col)) for col in fk.child_columns]
                joins = [sql.SQL("c.{} = p.{}").format(sql.Identifier(child), sql.Identifier(parent)) for child, parent in zip(fk.child_columns, fk.parent_columns)]
                query = sql.SQL("SELECT COUNT(*) FROM {}.{} c LEFT JOIN {}.{} p ON {} WHERE {} AND p.{} IS NULL").format(
                    sql.Identifier(cfg["target_schema"]), sql.Identifier(table.name),
                    sql.Identifier(cfg["target_schema"]), sql.Identifier(fk.parent_table),
                    sql.SQL(" AND ").join(joins),
                    sql.SQL(" AND ").join(conditions),
                    sql.Identifier(fk.parent_columns[0]),
                )
                orphan_count = conn.execute(query).fetchone()[0]
                if orphan_count:
                    errors.append(f"{table.name}: {orphan_count} orphan rows for FK to {fk.parent_table}.")
    return {"status": "passed" if not errors else "failed", "errors": errors, "row_counts": row_counts}
