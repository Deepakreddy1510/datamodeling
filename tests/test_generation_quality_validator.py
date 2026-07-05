from generation_quality_validator import validate_generation_quality


ANALYTICAL_INTENT = {
    "model_type": "analytical_data_warehouse",
    "required_layers": ["raw_load", "staging", "dimension", "fact", "reporting"],
}
BLUEPRINT = {"inferred_fact_tables": ["fact_sales"]}
CATALOG = '''
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{"table_column_rules": [
  {"table_name":"load_customer_raw","column_name":"id","semantic_role":"source key"},
  {"table_name":"stg_customer","column_name":"id","semantic_role":"source key"},
  {"table_name":"dim_customer","column_name":"customer_key","semantic_role":"surrogate key"},
  {"table_name":"fact_sales","column_name":"sales_key","semantic_role":"surrogate key"},
  {"table_name":"fact_sales","column_name":"customer_key","relationship_rule":"references dim_customer.customer_key"}
]}
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


def test_analytical_quality_fails_invalid_catalog_json():
    markdown = """
# SQL DDL
```sql
CREATE TABLE load_customer_raw (id integer);
CREATE TABLE stg_customer (id integer);
CREATE TABLE dim_customer (customer_key integer);
CREATE TABLE fact_sales (sales_key integer, customer_key integer);
```
# AI Additions / Assumptions
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{bad
END_SYNTHETIC_VALUE_CATALOG_JSON
"""
    result = validate_generation_quality({"final_output_markdown": markdown}, ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] == "failed"
    assert any("invalid" in error.lower() for error in result["errors"])


def test_analytical_quality_fails_empty_catalog_rules():
    markdown = """
# SQL DDL
```sql
CREATE TABLE load_customer_raw (id integer);
CREATE TABLE stg_customer (id integer);
CREATE TABLE dim_customer (customer_key integer);
CREATE TABLE fact_sales (sales_key integer, customer_key integer);
```
# AI Additions / Assumptions
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{"table_column_rules": []}
END_SYNTHETIC_VALUE_CATALOG_JSON
"""
    result = validate_generation_quality({"final_output_markdown": markdown}, ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] == "failed"
    assert any("table_column_rules" in error for error in result["errors"])


def test_analytical_quality_fails_when_catalog_coverage_below_threshold():
    markdown = """
# SQL DDL
```sql
CREATE TABLE load_customer_raw (id integer, customer_name varchar(50));
CREATE TABLE stg_customer (id integer, customer_name varchar(50));
CREATE TABLE dim_customer (customer_key integer, customer_name varchar(50), customer_status varchar(20));
CREATE TABLE fact_sales (sales_key integer, customer_key integer, order_total_amount numeric(8,2));
```
# AI Additions / Assumptions
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{"table_column_rules": [{"table_name":"dim_customer","column_name":"customer_key"}]}
END_SYNTHETIC_VALUE_CATALOG_JSON
"""
    result = validate_generation_quality({"final_output_markdown": markdown}, ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] == "failed"
    assert any("coverage" in error.lower() or "missing rules" in error.lower() for error in result["errors"])
