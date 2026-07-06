import json

from catalog_repair import build_catalog_repair_prompt, is_catalog_repairable_quality_failure
from generation_quality_validator import validate_generation_quality

INTENT = {"model_type": "analytical_data_warehouse", "required_layers": ["raw_load", "staging", "dimension", "fact"]}
BLUEPRINT = {"inferred_fact_tables": ["fact_sales"]}


def _markdown(catalog_json, include_fact=True):
    fact = "CREATE TABLE fact_sales (sales_key integer, customer_key integer, customer_name varchar(50));" if include_fact else ""
    return f"""
# SQL DDL
```sql
CREATE TABLE load_customer_raw (customer_id varchar(30), customer_name varchar(50));
CREATE TABLE stg_customer (customer_id varchar(30), customer_name varchar(50));
CREATE TABLE dim_customer (customer_key integer, customer_id varchar(30), customer_name varchar(50));
{fact}
```
# AI Additions / Assumptions
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{catalog_json}
END_SYNTHETIC_VALUE_CATALOG_JSON
"""


def test_catalog_coverage_failure_is_repairable():
    report = validate_generation_quality(
        {"final_output_markdown": _markdown('{"table_column_rules": [{"table_name":"dim_customer", "column_name":"customer_key"}]}')},
        INTENT,
        BLUEPRINT,
    )
    assert report["status"] == "failed"
    assert is_catalog_repairable_quality_failure(report) is True


def test_missing_ddl_is_not_repairable():
    report = validate_generation_quality(
        {"final_output_markdown": "# AI Additions / Assumptions\n# Synthetic Data Value Catalog\nBEGIN_SYNTHETIC_VALUE_CATALOG_JSON\n{\"table_column_rules\": []}\nEND_SYNTHETIC_VALUE_CATALOG_JSON"},
        INTENT,
        BLUEPRINT,
    )
    assert is_catalog_repairable_quality_failure(report) is False


def test_missing_fact_is_not_repairable():
    report = validate_generation_quality(
        {"final_output_markdown": _markdown('{"table_column_rules": [{"table_name":"dim_customer", "column_name":"customer_key"}]}', include_fact=False)},
        INTENT,
        BLUEPRINT,
    )
    assert is_catalog_repairable_quality_failure(report) is False


def test_invalid_catalog_json_is_not_repairable():
    report = validate_generation_quality({"final_output_markdown": _markdown('{bad')}, INTENT, BLUEPRINT)
    assert is_catalog_repairable_quality_failure(report) is False


def test_missing_catalog_markers_is_not_repairable():
    report = validate_generation_quality(
        {"final_output_markdown": "# SQL DDL\n```sql\nCREATE TABLE dim_customer (customer_key integer);\nCREATE TABLE fact_sales (sales_key integer);\n```\n# AI Additions / Assumptions"},
        INTENT,
        BLUEPRINT,
    )
    assert is_catalog_repairable_quality_failure(report) is False


def test_catalog_repair_prompt_contains_required_context_and_instructions():
    report = validate_generation_quality(
        {"final_output_markdown": _markdown('{"table_column_rules": [{"table_name":"dim_customer", "column_name":"customer_key"}]}')},
        INTENT,
        BLUEPRINT,
    )
    prompt = build_catalog_repair_prompt("business_name: Demo", _markdown(json.dumps({"table_column_rules": []})), report)
    assert "business_name: Demo" in prompt
    assert "current_final_output_markdown" in prompt
    assert "missing_catalog_rules" in prompt
    assert "catalog_coverage_percentage" in prompt
    assert "Prefer global reusable rules" in prompt
    assert "Do not delete existing valid catalog rules" in prompt
    assert "FULL corrected markdown" in prompt
