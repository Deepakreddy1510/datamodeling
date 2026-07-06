import json
import sys

import main as phase1_main
from output_writer import KNOWN_GENERATED_FILES, clean_known_outputs, write_text


ABSENT_TITLE = "Synthetic Data " + "Value " + chr(67) + "atalog"
START_MARKER = "BEGIN_" + "SYNTHETIC_VALUE_CATALOG_JSON"
END_MARKER = "END_" + "SYNTHETIC_VALUE_CATALOG_JSON"
RULES_KEY = "table_" + "column_rules"


def test_output_cleanup_includes_phase1_files(tmp_path):
    filenames = ["model_intent.json", "model_blueprint.json", "generation_quality_report.json", "generation_quality_report.md"]
    for filename in filenames:
        write_text(tmp_path / filename, "stale")
    clean_known_outputs(tmp_path)
    for filename in filenames:
        assert filename in KNOWN_GENERATED_FILES
        assert not (tmp_path / filename).exists()


def test_existing_mock_codex_flow_writes_data_engineering_final_output_without_synthetic_value_json(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", [
        "main.py",
        "--input", "input/business_input_sample.yaml",
        "--output-dir", str(output_dir),
        "--mock-codex",
        "--mock-ai-score", "100",
    ])
    assert phase1_main.main() == 0
    final_output = (output_dir / "final_output.md").read_text(encoding="utf-8")
    assert "CREATE TABLE load_" in final_output
    assert "CREATE TABLE stg_" in final_output
    assert "CREATE TABLE dim_" in final_output
    assert "CREATE TABLE fact_" in final_output
    assert "CREATE VIEW" in final_output
    assert ABSENT_TITLE not in final_output
    assert START_MARKER not in final_output
    assert END_MARKER not in final_output
    assert RULES_KEY not in final_output
    assert (output_dir / "model_intent.json").exists()
    assert (output_dir / "model_blueprint.json").exists()
    assert (output_dir / "generation_quality_report.json").exists()


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


def test_phase1_structural_failure_does_not_write_final_output(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    structural_bad = """
# SQL DDL
```sql
CREATE TABLE dim_customer (customer_key integer);
```
# AI Additions / Assumptions
"""
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--input", "input/business_input_sample.yaml", "--output-dir", str(output_dir), "--mock-codex", "--mock-ai-score", "100",
    ])
    monkeypatch.setattr(phase1_main, "get_raw_generation_response", lambda args, prompt: _phase1_response(structural_bad))
    assert phase1_main.main() == 1
    assert not (output_dir / "final_output.md").exists()
