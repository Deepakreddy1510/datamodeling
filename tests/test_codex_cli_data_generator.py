from decimal import Decimal
from pathlib import Path

import pytest

from phase2.codex_cli_data_generator import CodexCliDataGenerator, CodexCliGenerationError
from phase2.ddl_parser import parse_ddl
from phase2.validator import validate_generated_data


def test_codex_generator_builds_prompt_with_yaml_city_brand_and_rules(tmp_path):
    model = parse_ddl("""
CREATE TABLE dim_store (
  store_id integer PRIMARY KEY,
  city varchar(30),
  brand varchar(30),
  status varchar(20) CHECK (status IN ('Open','Closed'))
);
""")
    generator = CodexCliDataGenerator(output_dir=tmp_path)
    from phase2.warehouse_lineage_planner import build_warehouse_lineage_plan
    prompt = generator.build_canonical_prompt(
        model=model,
        business_input={"reference_data": {"cities": ["London", "Paris"], "brands": ["North", "South"]}, "postgres_password": "secret"},
        ddl_text="CREATE TABLE dim_store (...);",
        rows_per_table=2,
        warehouse_plan=build_warehouse_lineage_plan(model),
    )
    assert "London" in prompt and "Paris" in prompt
    assert "North" in prompt and "South" in prompt
    assert "canonical_records" in prompt
    assert "Python will deterministically materialize" in prompt
    assert "Do not generate final raw, staging, dimension, or fact tables independently" in prompt
    assert "secret" not in prompt


def test_codex_json_parsing_strips_markdown_fences(tmp_path):
    generator = CodexCliDataGenerator(output_dir=tmp_path)
    parsed = generator.parse_json_output('```json\n{"tables":{"demo":[{"id":1}]}}\n```')
    assert parsed == {"tables": {"demo": [{"id": 1}]}}


def test_invalid_codex_json_fails_clearly_and_writes_raw(tmp_path):
    generator = CodexCliDataGenerator(output_dir=tmp_path)
    raw_path = tmp_path / "codex_raw_output.txt"
    with pytest.raises(CodexCliGenerationError, match="invalid JSON"):
        generator.parse_json_output("not json", raw_path=raw_path)
    assert raw_path.read_text(encoding="utf-8") == "not json"


def test_codex_generated_rows_are_finalized_and_validate(tmp_path, monkeypatch):
    model = parse_ddl("""
CREATE TABLE dim_customer (
  customer_id integer PRIMARY KEY,
  status varchar(10) CHECK (status IN ('Active','Inactive')),
  amount numeric(8,2),
  active_flag boolean
);
""")
    def fake_run(_prompt):
        return '{"canonical_records":{"customer":[{"customer_id":"1","status":"Bad","amount":"12.30","active_flag":"true"}]}}'
    generator = CodexCliDataGenerator(output_dir=tmp_path)
    monkeypatch.setattr(generator, "_run_codex", fake_run)
    data = generator.generate_tables(model=model, business_input={}, ddl_text="", rows_per_table=1)
    row = data["dim_customer"][0]
    assert isinstance(row["customer_id"], int)
    assert row["status"] in {"Active", "Inactive"}
    assert isinstance(row["amount"], Decimal)
    assert row["active_flag"] is True
    assert validate_generated_data(model, data, data["__expected_rows__"])["status"] == "passed"


def test_codex_adaptive_row_count_for_unique_check_values(tmp_path, monkeypatch):
    model = parse_ddl("""
CREATE TABLE dim_method (
  method varchar(20) UNIQUE CHECK (method IN ('Card','Cash'))
);
""")
    def fake_run(_prompt):
        return '{"canonical_records":{"method":[{"method":"Card"},{"method":"Cash"}]}}'
    generator = CodexCliDataGenerator(output_dir=tmp_path)
    monkeypatch.setattr(generator, "_run_codex", fake_run)
    data = generator.generate_tables(model=model, business_input={}, ddl_text="", rows_per_table=10)
    assert data["__expected_rows__"] == {"dim_method": 2}
    assert len(data["dim_method"]) == 2
    assert validate_generated_data(model, data, data["__expected_rows__"])["status"] == "passed"


def test_codex_cli_uses_stdin_dash_and_resolves_executable(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setattr("phase2.codex_cli_data_generator.resolve_codex_executable", lambda: "codex.cmd")
    def fake_run(args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        class Result:
            returncode = 0
            stdout = '{"tables":{"demo":[]}}'
            stderr = ""
        return Result()
    monkeypatch.setattr("phase2.codex_cli_data_generator.subprocess.run", fake_run)
    generator = CodexCliDataGenerator(output_dir=tmp_path)
    assert generator._run_codex("PROMPT") == '{"tables":{"demo":[]}}'
    assert calls["args"] == ["codex.cmd", "exec", "-"]
    assert calls["kwargs"]["input"] == "PROMPT"
