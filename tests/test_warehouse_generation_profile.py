from phase2.ddl_parser import parse_ddl
from phase2.warehouse_generation_profile import build_warehouse_generation_profile
from phase2.warehouse_pipeline_planner import build_warehouse_pipeline_plan


def _model():
    return parse_ddl("""
CREATE TABLE raw.load_customer (load_id bigint PRIMARY KEY, source_payload jsonb NOT NULL);
CREATE TABLE raw.load_order (LIKE raw.load_customer INCLUDING ALL);
CREATE TABLE raw.load_order_item (LIKE raw.load_customer INCLUDING ALL);
CREATE TABLE stg.stg_customer (customer_id varchar(20) PRIMARY KEY, customer_name text NOT NULL);
CREATE TABLE stg.stg_order (
  order_id varchar(20) PRIMARY KEY,
  customer_id varchar(20) NOT NULL REFERENCES stg.stg_customer(customer_id),
  order_date date NOT NULL
);
CREATE TABLE stg.stg_order_item (
  order_item_id varchar(20) PRIMARY KEY,
  order_id varchar(20) NOT NULL REFERENCES stg.stg_order(order_id),
  quantity integer NOT NULL
);
CREATE TABLE dw.dim_customer (customer_key integer PRIMARY KEY, customer_id varchar(20) UNIQUE);
CREATE TABLE dw.fact_order (order_key integer PRIMARY KEY, customer_key integer REFERENCES dw.dim_customer(customer_key));
CREATE TABLE dw.fact_order_item (order_item_key integer PRIMARY KEY, customer_key integer REFERENCES dw.dim_customer(customer_key));
""")


def test_profile_is_domain_neutral_and_uses_relationship_cardinality():
    model = _model()
    plan = build_warehouse_pipeline_plan(model)
    profile = build_warehouse_generation_profile(model, plan, 10)
    assert profile["raw_table_row_counts"]["load_customer"] < 10
    assert profile["raw_table_row_counts"]["load_order"] == 10
    assert profile["raw_table_row_counts"]["load_order_item"] > 10
    relationships = profile["relationships"]
    assert any(r["child_raw_table"] == "load_order" and r["parent_raw_table"] == "load_customer" and r["require_reuse"] for r in relationships)
    assert any(r["child_raw_table"] == "load_order_item" and r["parent_raw_table"] == "load_order" and r["require_reuse"] for r in relationships)
    assert profile["table_profiles"]["load_customer"]["required_payload_columns"] == ["customer_id", "customer_name"]


def test_profile_does_not_depend_on_grocery_table_names():
    model = parse_ddl("""
CREATE TABLE load_account_raw (source_payload jsonb NOT NULL);
CREATE TABLE load_claim_raw (source_payload jsonb NOT NULL);
CREATE TABLE load_claim_line_raw (source_payload jsonb NOT NULL);
CREATE TABLE stg_account (account_id text PRIMARY KEY, account_name text NOT NULL);
CREATE TABLE stg_claim (claim_id text PRIMARY KEY, account_id text REFERENCES stg_account(account_id));
CREATE TABLE stg_claim_line (claim_line_id text PRIMARY KEY, claim_id text REFERENCES stg_claim(claim_id));
CREATE TABLE dim_account (account_key integer PRIMARY KEY, account_id text UNIQUE);
CREATE TABLE fact_claim (claim_key integer PRIMARY KEY, account_key integer REFERENCES dim_account(account_key));
CREATE TABLE fact_claim_line (claim_line_key integer PRIMARY KEY, account_key integer REFERENCES dim_account(account_key));
""")
    plan = build_warehouse_pipeline_plan(model)
    profile = build_warehouse_generation_profile(model, plan, 20)
    assert profile["raw_table_row_counts"]["load_account_raw"] < 20
    assert profile["raw_table_row_counts"]["load_claim_raw"] == 20
    assert profile["raw_table_row_counts"]["load_claim_line_raw"] > 20
