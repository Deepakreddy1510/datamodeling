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


def test_global_catalog_rule_covers_same_column_across_layers():
    markdown = """
# SQL DDL
```sql
CREATE TABLE raw_load.load_order_raw (order_id varchar(30), source_file_name varchar(100), loaded_at timestamp);
CREATE TABLE staging.stg_order (order_id varchar(30), customer_id varchar(30), loaded_at timestamp);
CREATE TABLE warehouse.dim_customer (customer_key integer, customer_id varchar(30), city varchar(50));
CREATE TABLE warehouse.fact_sales (sales_key integer, customer_key integer, order_id varchar(30), order_total_amount numeric(8,2));
```
# AI Additions / Assumptions
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{"table_column_rules": [
  {"table_name":"*", "column_name":"order_id", "value_pattern":"ORD-{number}"},
  {"table_name":"*", "column_name":"customer_id", "value_pattern":"CUST-{number}"},
  {"table_name":"*", "column_name":"loaded_at", "date_rule":"between 2026-01-01 and 2026-01-31"},
  {"table_name":"*", "column_name":"source_file_name", "value_pattern":"{table_name}_{number}.csv"},
  {"table_name":"warehouse.dim_customer", "column_name":"customer_key", "relationship_rule":"surrogate key"},
  {"table_name":"warehouse.dim_customer", "column_name":"city", "value_examples":["London"]},
  {"table_name":"warehouse.fact_sales", "column_name":"sales_key", "relationship_rule":"surrogate key"},
  {"table_name":"warehouse.fact_sales", "column_name":"customer_key", "relationship_rule":"references dim_customer.customer_key"},
  {"table_name":"warehouse.fact_sales", "column_name":"order_total_amount", "numeric_min":1, "numeric_max":100}
]}
END_SYNTHETIC_VALUE_CATALOG_JSON
"""
    result = validate_generation_quality({"final_output_markdown": markdown}, ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] == "passed"
    assert result["checks"]["catalog_coverage_percentage"] >= 80
    assert "order_id" in result["checks"]["catalog_global_columns_covered"]


def test_table_specific_rule_does_not_contaminate_other_table_for_coverage():
    markdown = """
# SQL DDL
```sql
CREATE TABLE load_payment_raw (status varchar(20));
CREATE TABLE stg_delivery (status varchar(20));
CREATE TABLE dim_status (status_key integer, status varchar(20));
CREATE TABLE fact_sales (sales_key integer, status_key integer);
```
# AI Additions / Assumptions
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{"table_column_rules": [
  {"table_name":"load_payment_raw", "column_name":"status", "allowed_values":["Paid"]},
  {"table_name":"dim_status", "column_name":"status_key", "relationship_rule":"surrogate key"},
  {"table_name":"dim_status", "column_name":"status", "allowed_values":["Active"]},
  {"table_name":"fact_sales", "column_name":"sales_key", "relationship_rule":"surrogate key"},
  {"table_name":"fact_sales", "column_name":"status_key", "relationship_rule":"references dim_status.status_key"}
]}
END_SYNTHETIC_VALUE_CATALOG_JSON
"""
    result = validate_generation_quality({"final_output_markdown": markdown}, ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] == "failed"
    assert any("stg_delivery.status" in warning for warning in result["warnings"])


def test_technical_metadata_columns_use_known_fallback_without_lowering_business_coverage():
    markdown = """
# SQL DDL
```sql
CREATE TABLE load_customer_raw (customer_id varchar(30), ingestion_id uuid, source_system varchar(50), source_file_name varchar(100), loaded_at timestamp);
CREATE TABLE stg_customer (customer_id varchar(30), batch_id varchar(50), created_at timestamp, updated_at timestamp);
CREATE TABLE dim_customer (customer_key integer, customer_id varchar(30), customer_name varchar(50));
CREATE TABLE fact_sales (sales_key integer, customer_key integer, customer_id varchar(30));
```
# AI Additions / Assumptions
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{"table_column_rules": [
  {"table_name":"*", "column_name":"customer_id", "value_pattern":"CUST-{number}"},
  {"table_name":"dim_customer", "column_name":"customer_key", "relationship_rule":"surrogate key"},
  {"table_name":"dim_customer", "column_name":"customer_name", "value_pattern":"Customer {number}"},
  {"table_name":"fact_sales", "column_name":"sales_key", "relationship_rule":"surrogate key"},
  {"table_name":"fact_sales", "column_name":"customer_key", "relationship_rule":"references dim_customer.customer_key"}
]}
END_SYNTHETIC_VALUE_CATALOG_JSON
"""
    result = validate_generation_quality({"final_output_markdown": markdown}, ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] == "passed"
    assert result["checks"]["technical_columns_using_known_fallback"]
    assert result["checks"]["catalog_coverage_percentage"] == 100


def test_no_raw_or_staging_global_coverage_still_fails():
    markdown = """
# SQL DDL
```sql
CREATE TABLE load_order_raw (order_id varchar(30), customer_id varchar(30));
CREATE TABLE stg_order (order_id varchar(30), customer_id varchar(30));
CREATE TABLE dim_customer (customer_key integer, customer_id varchar(30));
CREATE TABLE fact_sales (sales_key integer, customer_key integer, order_id varchar(30));
```
# AI Additions / Assumptions
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{"table_column_rules": [
  {"table_name":"dim_customer", "column_name":"customer_key", "relationship_rule":"surrogate key"},
  {"table_name":"dim_customer", "column_name":"customer_id", "value_pattern":"CUST-{number}"},
  {"table_name":"fact_sales", "column_name":"sales_key", "relationship_rule":"surrogate key"},
  {"table_name":"fact_sales", "column_name":"customer_key", "relationship_rule":"references dim_customer.customer_key"},
  {"table_name":"fact_sales", "column_name":"order_id", "value_pattern":"ORD-{number}"}
]}
END_SYNTHETIC_VALUE_CATALOG_JSON
"""
    result = validate_generation_quality({"final_output_markdown": markdown}, ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] == "failed"
    assert result["checks"]["catalog_coverage_percentage"] < 80
