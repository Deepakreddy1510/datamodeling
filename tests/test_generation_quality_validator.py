from generation_quality_validator import validate_generation_quality


ANALYTICAL_INTENT = {
    "model_type": "analytical_data_warehouse",
    "required_layers": ["raw_load", "staging", "dimension", "fact", "reporting"],
}
BLUEPRINT = {"inferred_fact_tables": ["fact_sales"]}
CATALOG = '''
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{"table_column_rules": []}
END_SYNTHETIC_VALUE_CATALOG_JSON
'''


def test_analytical_quality_fails_without_dim_or_fact_tables():
    result = validate_generation_quality(
        {"final_output_markdown": "# SQL DDL\n```sql\nCREATE TABLE customers (id integer);\n```\n# AI Additions / Assumptions\n" + CATALOG},
        ANALYTICAL_INTENT,
        BLUEPRINT,
    )
    assert result["status"] == "failed"
    assert any("dim_" in error for error in result["errors"])
    assert any("fact_" in error for error in result["errors"])


def test_analytical_quality_fails_without_catalog_markers():
    markdown = """
# SQL DDL
```sql
CREATE TABLE load_customer_raw (id integer);
CREATE TABLE stg_customer (id integer);
CREATE TABLE dim_customer (customer_key integer);
CREATE TABLE fact_sales (sales_key integer, customer_key integer);
```
# AI Additions / Assumptions
"""
    result = validate_generation_quality({"final_output_markdown": markdown}, ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] == "failed"
    assert any("Synthetic Data Value Catalog" in error for error in result["errors"])


def test_analytical_quality_passes_layered_output():
    markdown = """
# SQL DDL
```sql
CREATE TABLE load_customer_raw (id integer);
CREATE TABLE stg_customer (id integer);
CREATE TABLE dim_customer (customer_key integer);
CREATE TABLE fact_sales (sales_key integer, customer_key integer);
```
# AI Additions / Assumptions
""" + CATALOG
    result = validate_generation_quality({"final_output_markdown": markdown}, ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] == "passed"


def test_operational_quality_does_not_require_dim_or_fact_tables():
    result = validate_generation_quality(
        {"final_output_markdown": "# SQL DDL\n```sql\nCREATE TABLE customers (id integer);\n```"},
        {"model_type": "operational_model", "required_layers": ["operational"]},
        {"model_type": "operational_model"},
    )
    assert result["status"] == "passed"
