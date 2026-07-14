from phase2.codex_etl_response_validator import validate_codex_etl_response
from phase2.ddl_parser import parse_ddl
from phase2.warehouse_pipeline_planner import build_warehouse_pipeline_plan


def _model_plan():
    model = parse_ddl("""
CREATE TABLE load_customer_raw (customer_id varchar(20), customer_name varchar(50));
CREATE TABLE stg_customer (customer_id varchar(20), customer_name varchar(50));
CREATE TABLE dim_customer (customer_key integer PRIMARY KEY, customer_id varchar(20) UNIQUE, customer_name varchar(50));
CREATE TABLE fact_sales (sales_key integer PRIMARY KEY, customer_key integer REFERENCES dim_customer(customer_key));
""")
    return model, build_warehouse_pipeline_plan(model)


def _valid_response():
    return {
        "load_table_rows": {"load_customer_raw": [{"customer_id": "C1", "customer_name": "Alex"}]},
        "staging_sql": ["INSERT INTO stg_customer (customer_id, customer_name) SELECT customer_id, customer_name FROM load_customer_raw;"],
        "dimension_sql": ["WITH src AS (SELECT customer_id, customer_name FROM stg_customer) INSERT INTO dim_customer (customer_key, customer_id, customer_name) SELECT row_number() over (), customer_id, customer_name FROM src;"],
        "fact_sql": ["INSERT INTO fact_sales (sales_key, customer_key) SELECT 1, customer_key FROM dim_customer;"],
        "assumptions": [],
    }


def test_valid_codex_etl_response_passes():
    model, plan = _model_plan()
    assert validate_codex_etl_response(_valid_response(), model, plan)["status"] == "passed"


def test_load_table_rows_rejects_non_raw_tables():
    model, plan = _model_plan()
    response = _valid_response()
    response["load_table_rows"]["dim_customer"] = [{"customer_key": 1}]
    result = validate_codex_etl_response(response, model, plan)
    assert result["status"] == "failed"
    assert any("non-raw/load" in error for error in result["errors"])


def test_sql_layer_targets_are_enforced():
    model, plan = _model_plan()
    response = _valid_response()
    response["staging_sql"] = ["INSERT INTO dim_customer (customer_key) SELECT 1 FROM load_customer_raw;"]
    result = validate_codex_etl_response(response, model, plan)
    assert result["status"] == "failed"
    assert any("not allowed for this layer" in error for error in result["errors"])


def test_dangerous_sql_is_blocked():
    model, plan = _model_plan()
    for bad in ["CREATE TABLE x (id int);", "DROP TABLE dim_customer;", "ALTER TABLE dim_customer ADD COLUMN x int;", "TRUNCATE dim_customer;"]:
        response = _valid_response()
        response["dimension_sql"] = [bad]
        result = validate_codex_etl_response(response, model, plan)
        assert result["status"] == "failed"
