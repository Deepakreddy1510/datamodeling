from pathlib import Path

from runtime_config import derive_target_schema, resolve_excel_output, resolve_output_dir, slugify


def test_slugify_produces_postgres_safe_identifier():
    assert slugify("Air India Cabin Capacity Optimization") == "air_india_cabin_capacity_optimization"
    assert slugify("123 Demo").startswith("uc_")


def test_use_case_paths_are_isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("POSTGRES_TARGET_SCHEMA", "stale_schema_should_be_ignored")
    business = {"business_name": "Air India Cabin Capacity Optimization"}
    yaml_path = tmp_path / "air.yaml"
    output = resolve_output_dir(yaml_path, business)
    excel = resolve_excel_output(yaml_path, business, output)
    assert output.name == "air_india_cabin_capacity_optimization"
    assert excel.parent == output
    assert excel.name == "air_india_cabin_capacity_optimization_synthetic_data.xlsx"
    assert derive_target_schema(yaml_path, business) == "air_india_cabin_capacity_optimization"
