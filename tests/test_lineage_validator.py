from phase2.ddl_parser import parse_ddl
from phase2.lineage_validator import validate_lineage
from phase2.warehouse_pipeline_planner import build_warehouse_pipeline_plan


def test_lineage_validator_passes_connected_data_and_fails_random_fact_key():
    model = parse_ddl("""
CREATE TABLE load_customer_raw (customer_id varchar(20), customer_name varchar(50));
CREATE TABLE stg_customer (customer_id varchar(20), customer_name varchar(50));
CREATE TABLE dim_customer (customer_key integer PRIMARY KEY, customer_id varchar(20));
CREATE TABLE fact_sales (sales_key integer PRIMARY KEY, customer_key integer REFERENCES dim_customer(customer_key));
""")
    plan = build_warehouse_pipeline_plan(model)
    data = {
        "load_customer_raw": [{"customer_id": "C1", "customer_name": "Alex"}],
        "stg_customer": [{"customer_id": "C1", "customer_name": "Alex"}],
        "dim_customer": [{"customer_key": 10, "customer_id": "C1"}],
        "fact_sales": [{"sales_key": 1, "customer_key": 10}],
    }
    assert validate_lineage(model, data, plan)["status"] == "passed"
    data["fact_sales"] = [{"sales_key": 1, "customer_key": 999}]
    result = validate_lineage(model, data, plan)
    assert result["status"] == "failed"
    assert any("random/unresolved" in error for error in result["errors"])
