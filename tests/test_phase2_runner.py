import pytest

pytest.importorskip("openpyxl")

import phase2_runner


def test_phase2_dry_run_generates_excel_and_reports_from_ddl_only(tmp_path, monkeypatch):
    yaml_path = tmp_path / "input.yaml"
    yaml_path.write_text("business_name: Demo\ntarget_database: PostgreSQL\n", encoding="utf-8")
    phase1_output = tmp_path / "final_output.md"
    phase1_output.write_text(
        """
# SQL DDL
```sql
CREATE TABLE dim_date (
  date_key integer PRIMARY KEY,
  full_date date NOT NULL,
  day_name varchar(20)
);
CREATE TABLE dim_customer (
  customer_key integer PRIMARY KEY,
  customer_id varchar(20) UNIQUE,
  customer_name varchar(60) NOT NULL,
  customer_segment varchar(20) CHECK (customer_segment IN ('New', 'Premium'))
);
CREATE TABLE fact_sales (
  sales_key integer PRIMARY KEY,
  customer_key integer REFERENCES dim_customer(customer_key),
  order_date_key integer REFERENCES dim_date(date_key),
  quantity integer CHECK (quantity BETWEEN 1 AND 10),
  unit_price numeric(8,2) CHECK (unit_price > 0),
  line_total_amount numeric(10,2),
  UNIQUE (customer_key, order_date_key)
);
```
# AI Additions / Assumptions
""",
        encoding="utf-8",
    )
    excel_path = tmp_path / "synthetic.xlsx"
    args = [
        "phase2_runner.py",
        "--yaml", str(yaml_path),
        "--phase1-output", str(phase1_output),
        "--rows-per-table", "5",
        "--excel-output", str(excel_path),
        "--output-dir", str(tmp_path),
        "--no-load-to-postgres",
    ]
    monkeypatch.setattr("sys.argv", args)
    assert phase2_runner.main() == 0
    assert excel_path.exists()
    assert "Final status: **passed" in (tmp_path / "validation_report.md").read_text(encoding="utf-8")


def test_phase2_runner_generation_engine_defaults_to_python(monkeypatch):
    monkeypatch.setattr("sys.argv", ["phase2_runner.py", "--yaml", "input.yaml"])
    args = phase2_runner.parse_args()
    assert args.generation_engine == "python"


def test_phase2_runner_parses_codex_generation_options(monkeypatch):
    monkeypatch.setattr("sys.argv", ["phase2_runner.py", "--yaml", "input.yaml", "--generation-engine", "codex-cli", "--allow-generator-fallback", "--codex-timeout-seconds", "12"])
    args = phase2_runner.parse_args()
    assert args.generation_engine == "codex-cli"
    assert args.allow_generator_fallback is True
    assert args.codex_timeout_seconds == 12


def test_phase2_codex_cli_elt_flow_uses_postgres_readback(tmp_path, monkeypatch):
    yaml_path = tmp_path / "input.yaml"
    yaml_path.write_text("business_name: Demo\ntarget_database: PostgreSQL\n", encoding="utf-8")
    phase1_output = tmp_path / "final_output.md"
    phase1_output.write_text(
        """
```sql
CREATE TABLE load_customer_raw (customer_id varchar(20), customer_name varchar(50));
CREATE TABLE stg_customer (customer_id varchar(20), customer_name varchar(50));
CREATE TABLE dim_customer (customer_key integer PRIMARY KEY, customer_id varchar(20), customer_name varchar(50));
CREATE TABLE fact_sales (sales_key integer PRIMARY KEY, customer_key integer REFERENCES dim_customer(customer_key));
```
""",
        encoding="utf-8",
    )
    excel_path = tmp_path / "synthetic.xlsx"
    response = {
        "load_table_rows": {"load_customer_raw": [{"customer_id": "C1", "customer_name": "Alex"}]},
        "staging_sql": ["INSERT INTO stg_customer (customer_id, customer_name) SELECT customer_id, customer_name FROM load_customer_raw;"],
        "dimension_sql": ["INSERT INTO dim_customer (customer_key, customer_id, customer_name) SELECT 1, customer_id, customer_name FROM stg_customer;"],
        "fact_sql": ["INSERT INTO fact_sales (sales_key, customer_key) SELECT 1, customer_key FROM dim_customer;"],
        "assumptions": ["mocked"],
    }
    final_data = {
        "load_customer_raw": [{"customer_id": "C1", "customer_name": "Alex"}],
        "stg_customer": [{"customer_id": "C1", "customer_name": "Alex"}],
        "dim_customer": [{"customer_key": 1, "customer_id": "C1", "customer_name": "Alex"}],
        "fact_sales": [{"sales_key": 1, "customer_key": 1}],
    }
    monkeypatch.setattr(phase2_runner.CodexCliDataGenerator, "generate_warehouse_elt", lambda self, **kwargs: response)
    monkeypatch.setattr(phase2_runner, "execute_codex_transformation", lambda *args, **kwargs: {
        "status": "passed",
        "target_schema": "demo",
        "inserted_rows": {"load_customer_raw": 1},
        "transformed_rows": {name: len(rows) for name, rows in final_data.items()},
        "table_data": final_data,
        "executed_sql": {"staging_sql": response["staging_sql"], "dimension_sql": response["dimension_sql"], "fact_sql": response["fact_sql"]},
        "errors": [],
        "transaction_status": "committed",
    })
    monkeypatch.setattr("sys.argv", [
        "phase2_runner.py", "--yaml", str(yaml_path), "--phase1-output", str(phase1_output),
        "--rows-per-table", "1", "--excel-output", str(excel_path), "--output-dir", str(tmp_path),
        "--generation-engine", "codex-cli", "--load-to-postgres", "--create-schema-if-missing", "--create-tables-if-missing",
    ])
    assert phase2_runner.main() == 0
    assert excel_path.exists()
    assert "Lineage Validation" in (tmp_path / "validation_report.md").read_text(encoding="utf-8")


def test_phase2_codex_cli_requires_postgres(tmp_path, monkeypatch):
    yaml_path = tmp_path / "input.yaml"
    yaml_path.write_text("business_name: Demo\n", encoding="utf-8")
    phase1_output = tmp_path / "final_output.md"
    phase1_output.write_text("```sql\nCREATE TABLE load_customer_raw (customer_id varchar(20));\n```", encoding="utf-8")
    monkeypatch.setattr("sys.argv", [
        "phase2_runner.py", "--yaml", str(yaml_path), "--phase1-output", str(phase1_output),
        "--output-dir", str(tmp_path), "--generation-engine", "codex-cli",
    ])
    assert phase2_runner.main() == 1
    assert "requires --load-to-postgres" in (tmp_path / "validation_report.md").read_text(encoding="utf-8")
