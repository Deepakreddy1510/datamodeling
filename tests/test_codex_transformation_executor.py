import pytest

from phase2.codex_transformation_executor import execute_codex_transformation
from phase2.ddl_parser import parse_ddl
from phase2.postgres_loader import PostgresLoadError
from phase2.warehouse_pipeline_planner import build_warehouse_pipeline_plan


def test_codex_transformation_executor_reports_setup_failure(monkeypatch):
    model = parse_ddl("CREATE TABLE load_customer_raw (customer_id varchar(20));")
    plan = build_warehouse_pipeline_plan(model)
    monkeypatch.setattr("phase2.codex_transformation_executor._require_psycopg", lambda: (_ for _ in ()).throw(PostgresLoadError("psycopg unavailable")))
    result = execute_codex_transformation(model, {"load_table_rows": {}}, plan)
    assert result["status"] == "failed"
    assert "psycopg unavailable" in result["errors"][0]
