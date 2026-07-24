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
    prompt = generator.build_prompt(
        model=model,
        table=model.tables[0],
        business_input={"reference_data": {"cities": ["London", "Paris"], "brands": ["North", "South"]}, "postgres_password": "secret"},
        ddl_text="CREATE TABLE dim_store (...);",
        rows_per_table=2,
        generated_so_far={},
    )
    assert "London" in prompt and "Paris" in prompt
    assert "North" in prompt and "South" in prompt
    assert "City values must come only from YAML cities" in prompt
    assert "Brand values must come only from YAML brands" in prompt
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
        return '{"tables":{"dim_customer":[{"customer_id":"1","status":"Bad","amount":"12.30","active_flag":"true"}]}}'
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
        return '{"tables":{"dim_method":[{"method":"Card"},{"method":"Cash"}]}}'
    generator = CodexCliDataGenerator(output_dir=tmp_path)
    monkeypatch.setattr(generator, "_run_codex", fake_run)
    data = generator.generate_tables(model=model, business_input={}, ddl_text="", rows_per_table=10)
    assert data["__expected_rows__"] == {"dim_method": 2}
    assert len(data["dim_method"]) == 2
    assert validate_generated_data(model, data, data["__expected_rows__"])["status"] == "passed"


def test_codex_warehouse_elt_prompt_requires_raw_only_generation(tmp_path):
    model = parse_ddl("""
CREATE TABLE load_customer_raw (customer_id varchar(20));
CREATE TABLE stg_customer (customer_id varchar(20));
""")
    generator = CodexCliDataGenerator(output_dir=tmp_path)
    prompt = generator.build_warehouse_elt_prompt(
        model=model,
        business_input={"postgres_password": "secret"},
        ddl_text="CREATE TABLE load_customer_raw (customer_id varchar(20));",
        semantic_context=None,
        pipeline_plan={"raw_tables": ["load_customer_raw"], "staging_tables": ["stg_customer"], "dimension_tables": [], "fact_tables": [], "lineage": {"stg_customer": ["load_customer_raw"]}},
        rows_per_table=3,
    )
    assert "Generate rows only for load/raw tables" in prompt
    assert "Do not generate staging rows independently" in prompt
    assert "INSERT ... SELECT or WITH ... INSERT" in prompt
    assert "CREATE TABLE" in prompt
    assert "Do not generate CREATE TABLE" in prompt
    assert "warehouse_generation_profile" in prompt
    assert "Reuse master/parent business keys" in prompt
    assert "exact raw/load row count" in prompt
    assert "secret" not in prompt


def test_codex_warehouse_elt_writes_artifacts(tmp_path, monkeypatch):
    model = parse_ddl("CREATE TABLE load_customer_raw (customer_id varchar(20));")
    generator = CodexCliDataGenerator(output_dir=tmp_path)
    monkeypatch.setattr(generator, "_run_codex", lambda _prompt: '{"load_table_rows":{"load_customer_raw":[{"customer_id":"C1"}]},"staging_sql":[],"dimension_sql":[],"fact_sql":[],"assumptions":["demo"]}')
    response = generator.generate_warehouse_elt(model=model, business_input={}, ddl_text="", semantic_context=None, pipeline_plan={"raw_tables": ["load_customer_raw"]}, rows_per_table=1)
    assert response["load_table_rows"]["load_customer_raw"][0]["customer_id"] == "C1"
    assert (tmp_path / "warehouse_elt_prompt.txt").exists()
    assert (tmp_path / "warehouse_elt_raw_output.txt").exists()
    assert (tmp_path / "warehouse_elt_sql.json").exists()
    assert (tmp_path / "warehouse_generation_profile.json").exists()


def test_codex_warehouse_elt_reuses_matching_cached_response(tmp_path, monkeypatch):
    model = parse_ddl("CREATE TABLE load_customer_raw (customer_id varchar(20));")
    calls = []

    def fake_run(_prompt):
        calls.append(1)
        return '{"load_table_rows":{"load_customer_raw":[{"customer_id":"C1"}]},"staging_sql":[],"dimension_sql":[],"fact_sql":[],"assumptions":[]}'

    generator = CodexCliDataGenerator(output_dir=tmp_path)
    monkeypatch.setattr(generator, "_run_codex", fake_run)
    kwargs = {
        "model": model,
        "business_input": {},
        "ddl_text": "",
        "semantic_context": None,
        "pipeline_plan": {"raw_tables": ["load_customer_raw"]},
        "rows_per_table": 1,
    }
    first = generator.generate_warehouse_elt(**kwargs)
    second = generator.generate_warehouse_elt(**kwargs)
    assert first == second
    assert len(calls) == 1
    assert (tmp_path / "warehouse_elt_cache.json").exists()
