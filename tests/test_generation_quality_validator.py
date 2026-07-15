from generation_quality_validator import validate_generation_quality


ANALYTICAL_INTENT = {"model_type": "analytical_data_warehouse", "required_layers": ["raw_load", "staging", "dimension", "fact", "reporting"]}
BLUEPRINT = {"inferred_fact_tables": ["fact_sales"]}


def _response(markdown):
    return {"final_output_markdown": markdown}


def _warehouse_markdown():
    return """
# SQL DDL
```sql
CREATE TABLE load_customer_raw (customer_id integer PRIMARY KEY);
CREATE TABLE stg_customer (customer_id integer PRIMARY KEY);
CREATE TABLE dim_customer (customer_key integer PRIMARY KEY, customer_id integer);
CREATE TABLE fact_sales (sales_key integer PRIMARY KEY, customer_key integer REFERENCES dim_customer(customer_key));
CREATE VIEW reporting_sales_summary AS SELECT customer_key, COUNT(*) AS order_count FROM fact_sales GROUP BY customer_key;
```
# AI Additions / Assumptions

| Added Item | Type | Reason | Mandatory / Optional |
|---|---|---|---|
| load_customer_raw | table | Inferred raw load layer. | mandatory |
"""


def test_analytical_quality_passes_without_synthetic_value_json():
    result = validate_generation_quality(_response(_warehouse_markdown()), ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] in {"passed", "passed_with_warnings"}
    assert result["checks"]["load_tables_present"] is True
    assert result["checks"]["staging_tables_present"] is True
    assert result["checks"]["dimension_tables_present"] is True
    assert result["checks"]["fact_tables_present"] is True
    assert result["checks"]["ddl_present"] is True


def test_analytical_quality_fails_when_dimension_missing():
    markdown = _warehouse_markdown().replace("CREATE TABLE dim_customer (customer_key integer PRIMARY KEY, customer_id integer);\n", "")
    result = validate_generation_quality(_response(markdown), ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] == "failed"
    assert any("dim_" in error for error in result["errors"])


def test_analytical_quality_fails_when_fact_missing():
    markdown = _warehouse_markdown().replace("CREATE TABLE fact_sales (sales_key integer PRIMARY KEY, customer_key integer REFERENCES dim_customer(customer_key));\n", "")
    result = validate_generation_quality(_response(markdown), ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] == "failed"
    assert any("fact_" in error for error in result["errors"])


def test_analytical_quality_fails_when_ddl_missing():
    result = validate_generation_quality(_response("# AI Additions / Assumptions\n"), ANALYTICAL_INTENT, BLUEPRINT)
    assert result["status"] == "failed"
    assert any("CREATE TABLE" in error for error in result["errors"])
