from phase2.ddl_parser import parse_ddl
from phase2.semantic_context import build_semantic_context
from phase2.warehouse_pipeline_planner import build_warehouse_pipeline_plan


def test_pipeline_planner_classifies_and_maps_lineage():
    model = parse_ddl("""
CREATE TABLE load_customer_raw (customer_id varchar(20), customer_name varchar(50));
CREATE TABLE stg_customer (customer_id varchar(20), customer_name varchar(50));
CREATE TABLE dim_customer (customer_key integer PRIMARY KEY, customer_id varchar(20) UNIQUE, customer_name varchar(50));
CREATE TABLE fact_sales (sales_key integer PRIMARY KEY, customer_key integer REFERENCES dim_customer(customer_key), customer_id varchar(20));
""")
    context = build_semantic_context({}, model)
    plan = build_warehouse_pipeline_plan(model, context)
    assert plan["raw_tables"] == ["load_customer_raw"]
    assert plan["staging_tables"] == ["stg_customer"]
    assert plan["dimension_tables"] == ["dim_customer"]
    assert plan["fact_tables"] == ["fact_sales"]
    assert plan["lineage"]["stg_customer"] == ["load_customer_raw"]
    assert plan["lineage"]["dim_customer"] == ["stg_customer"]
    assert "dim_customer" in plan["lineage"]["fact_sales"]
