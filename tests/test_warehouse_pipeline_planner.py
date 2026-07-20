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


def test_pipeline_planner_maps_grocery_staging_tables_to_exact_load_entities():
    model = parse_ddl("""
CREATE TABLE raw.load_order (
    load_id integer PRIMARY KEY,
    order_id text,
    customer_id text,
    source_payload jsonb,
    loaded_at timestamp
);
CREATE TABLE raw.load_order_item (
    load_id integer PRIMARY KEY,
    order_item_id text,
    order_id text,
    product_id text,
    source_payload jsonb,
    loaded_at timestamp
);
CREATE TABLE raw.load_customer (
    load_id integer PRIMARY KEY,
    customer_id text,
    customer_name text,
    source_payload jsonb,
    loaded_at timestamp
);
CREATE TABLE raw.load_product (
    load_id integer PRIMARY KEY,
    product_id text,
    product_name text,
    source_payload jsonb,
    loaded_at timestamp
);
CREATE TABLE raw.load_store (
    load_id integer PRIMARY KEY,
    store_id text,
    store_name text,
    source_payload jsonb,
    loaded_at timestamp
);
CREATE TABLE raw.load_payment (
    load_id integer PRIMARY KEY,
    payment_id text,
    order_id text,
    source_payload jsonb,
    loaded_at timestamp
);
CREATE TABLE raw.load_delivery (
    load_id integer PRIMARY KEY,
    delivery_id text,
    order_id text,
    source_payload jsonb,
    loaded_at timestamp
);
CREATE TABLE stg.stg_order (
    order_id text,
    customer_id text,
    staged_at timestamp
);
CREATE TABLE stg.stg_order_item (
    order_item_id text,
    order_id text,
    product_id text,
    staged_at timestamp
);
CREATE TABLE stg.stg_customer (
    customer_id text,
    customer_name text,
    staged_at timestamp
);
CREATE TABLE stg.stg_product (
    product_id text,
    product_name text,
    staged_at timestamp
);
CREATE TABLE stg.stg_store (
    store_id text,
    store_name text,
    staged_at timestamp
);
CREATE TABLE stg.stg_payment (
    payment_id text,
    order_id text,
    staged_at timestamp
);
CREATE TABLE stg.stg_delivery (
    delivery_id text,
    order_id text,
    staged_at timestamp
);
""")
    plan = build_warehouse_pipeline_plan(model)
    assert plan["lineage"]["stg_order"] == ["load_order"]
    assert plan["lineage"]["stg_order_item"] == ["load_order_item"]
    assert plan["lineage"]["stg_customer"] == ["load_customer"]
    assert plan["lineage"]["stg_product"] == ["load_product"]
    assert plan["lineage"]["stg_store"] == ["load_store"]
    assert plan["lineage"]["stg_payment"] == ["load_payment"]
    assert plan["lineage"]["stg_delivery"] == ["load_delivery"]
