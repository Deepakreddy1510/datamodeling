import json
import sys
from pathlib import Path

import main as phase1_main
from output_writer import KNOWN_GENERATED_FILES, clean_known_outputs, write_text


def test_output_cleanup_includes_new_phase1_files(tmp_path):
    for filename in ["model_intent.json", "model_blueprint.json", "generation_quality_report.json", "generation_quality_report.md", "catalog_repair_prompt.md", "catalog_repair_response_raw.txt", "catalog_repair_response.json"]:
        write_text(tmp_path / filename, "stale")
    clean_known_outputs(tmp_path)
    for filename in ["model_intent.json", "model_blueprint.json", "generation_quality_report.json", "generation_quality_report.md", "catalog_repair_prompt.md", "catalog_repair_response_raw.txt", "catalog_repair_response.json"]:
        assert filename in KNOWN_GENERATED_FILES
        assert not (tmp_path / filename).exists()


def test_existing_mock_codex_flow_still_writes_final_output(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", [
        "main.py",
        "--input", "input/business_input_sample.yaml",
        "--output-dir", str(output_dir),
        "--mock-codex",
        "--mock-ai-score", "100",
    ])
    assert phase1_main.main() == 0
    assert (output_dir / "model_intent.json").exists()
    assert (output_dir / "model_blueprint.json").exists()
    assert (output_dir / "generation_quality_report.json").exists()
    assert (output_dir / "final_output.md").exists()


def test_validation_errors_still_work(tmp_path, monkeypatch):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("business_name: Only Name\n", encoding="utf-8")
    output_dir = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", ["main.py", "--input", str(bad_yaml), "--output-dir", str(output_dir), "--mock-codex"])
    assert phase1_main.main() == 1
    assert (output_dir / "validation_errors.json").exists()


def _phase1_response(markdown):
    return json.dumps({
        "status": "generated",
        "final_output_markdown": markdown,
        "ai_additions_and_assumptions": [],
    })


def _weak_catalog_markdown():
    return """
# SQL DDL
```sql
CREATE TABLE load_customer_raw (customer_id varchar(30), customer_name varchar(50));
CREATE TABLE stg_customer (customer_id varchar(30), customer_name varchar(50));
CREATE TABLE dim_customer (customer_key integer, customer_id varchar(30), customer_name varchar(50));
CREATE TABLE fact_sales (sales_key integer, customer_key integer, customer_id varchar(30), customer_name varchar(50));
```
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{"table_column_rules": [{"table_name":"dim_customer", "column_name":"customer_key"}]}
END_SYNTHETIC_VALUE_CATALOG_JSON
# AI Additions / Assumptions
"""


def _strong_catalog_markdown():
    return """
# SQL DDL
```sql
CREATE TABLE load_customer_raw (customer_id varchar(30), customer_name varchar(50));
CREATE TABLE stg_customer (customer_id varchar(30), customer_name varchar(50));
CREATE TABLE dim_customer (customer_key integer, customer_id varchar(30), customer_name varchar(50));
CREATE TABLE fact_sales (sales_key integer, customer_key integer, customer_id varchar(30), customer_name varchar(50));
```
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{"table_column_rules": [
  {"table_name":"*", "column_name":"customer_id", "value_pattern":"CUST-{number}"},
  {"table_name":"*", "column_name":"customer_name", "value_pattern":"realistic person full name"},
  {"table_name":"*", "column_name":"customer_key", "relationship_rule":"choose existing dim_customer.customer_key"},
  {"table_name":"fact_sales", "column_name":"sales_key", "relationship_rule":"surrogate key"}
]}
END_SYNTHETIC_VALUE_CATALOG_JSON
# AI Additions / Assumptions
"""


def test_phase1_catalog_repair_success_writes_final_output(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--input", "input/business_input_sample.yaml", "--output-dir", str(output_dir), "--mock-codex", "--mock-ai-score", "100",
    ])
    monkeypatch.setattr(phase1_main, "get_raw_generation_response", lambda args, prompt: _phase1_response(_weak_catalog_markdown()))
    monkeypatch.setattr(phase1_main, "get_raw_catalog_repair_response", lambda args, prompt: _phase1_response(_strong_catalog_markdown()))
    assert phase1_main.main() == 0
    assert (output_dir / "final_output.md").exists()
    assert (output_dir / "catalog_repair_prompt.md").exists()
    assert (output_dir / "catalog_repair_response.json").exists()
    report = (output_dir / "generation_quality_report.md").read_text(encoding="utf-8")
    assert "Catalog repair attempted: True" in report
    assert "Catalog repair status: passed" in report
    assert "Final output written: True" in report


def test_phase1_catalog_repair_failure_does_not_write_final_output(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--input", "input/business_input_sample.yaml", "--output-dir", str(output_dir), "--mock-codex", "--mock-ai-score", "100",
    ])
    monkeypatch.setattr(phase1_main, "get_raw_generation_response", lambda args, prompt: _phase1_response(_weak_catalog_markdown()))
    monkeypatch.setattr(phase1_main, "get_raw_catalog_repair_response", lambda args, prompt: _phase1_response(_weak_catalog_markdown()))
    assert phase1_main.main() == 1
    assert not (output_dir / "final_output.md").exists()
    assert (output_dir / "catalog_repair_prompt.md").exists()
    assert (output_dir / "catalog_repair_response_raw.txt").exists()


def test_phase1_structural_failure_does_not_trigger_catalog_repair(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    structural_bad = """
# SQL DDL
```sql
CREATE TABLE dim_customer (customer_key integer);
```
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{"table_column_rules": [{"table_name":"dim_customer", "column_name":"customer_key"}]}
END_SYNTHETIC_VALUE_CATALOG_JSON
# AI Additions / Assumptions
"""
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--input", "input/business_input_sample.yaml", "--output-dir", str(output_dir), "--mock-codex", "--mock-ai-score", "100",
    ])
    monkeypatch.setattr(phase1_main, "get_raw_generation_response", lambda args, prompt: _phase1_response(structural_bad))
    def fail_if_called(args, prompt):
        raise AssertionError("repair should not be called for structural failures")
    monkeypatch.setattr(phase1_main, "get_raw_catalog_repair_response", fail_if_called)
    assert phase1_main.main() == 1
    assert not (output_dir / "catalog_repair_prompt.md").exists()
