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


def test_validator_accepts_cte_with_extract_from_column_alias():
    model = parse_ddl("""
CREATE TABLE stg_order (order_date timestamp);
CREATE TABLE stg_payment (payment_date timestamp);
CREATE TABLE dim_date (
    date_key integer PRIMARY KEY,
    full_date date NOT NULL,
    iso_day smallint
);
""")
    plan = build_warehouse_pipeline_plan(model)
    response = {
        "load_table_rows": {},
        "staging_sql": [],
        "dimension_sql": ["""
WITH event_dates AS (
    SELECT order_date::date AS full_date FROM stg_order
    UNION SELECT payment_date::date FROM stg_payment
)
INSERT INTO dim_date (date_key, full_date, iso_day)
SELECT to_char(full_date,'YYYYMMDD')::integer,
       full_date,
       extract(isodow FROM full_date)::smallint
FROM event_dates;
"""],
        "fact_sql": [],
        "assumptions": [],
    }
    result = validate_codex_etl_response(response, model, plan)
    assert result["status"] == "passed", result["errors"]


def test_validator_rejects_unknown_real_table_with_cte_and_extract():
    model = parse_ddl("""
CREATE TABLE stg_order (order_date timestamp);
CREATE TABLE dim_date (date_key integer PRIMARY KEY, full_date date NOT NULL);
""")
    plan = build_warehouse_pipeline_plan(model)
    response = {
        "load_table_rows": {},
        "staging_sql": [],
        "dimension_sql": ["""
WITH event_dates AS (
    SELECT order_date::date AS full_date FROM external_orders
)
INSERT INTO dim_date (date_key, full_date)
SELECT to_char(full_date,'YYYYMMDD')::integer, full_date
FROM event_dates;
"""],
        "fact_sql": [],
        "assumptions": [],
    }
    result = validate_codex_etl_response(response, model, plan)
    assert result["status"] == "failed"
    assert any("external_orders" in error for error in result["errors"])


def test_validator_enforces_generic_profile_counts_payload_and_reuse():
    model = parse_ddl("""
CREATE TABLE load_account_raw (source_payload jsonb NOT NULL);
CREATE TABLE load_event_raw (source_payload jsonb NOT NULL);
CREATE TABLE stg_account (account_id text PRIMARY KEY, account_name text NOT NULL);
CREATE TABLE stg_event (event_id text PRIMARY KEY, account_id text NOT NULL REFERENCES stg_account(account_id));
""")
    plan = build_warehouse_pipeline_plan(model)
    profile = {
        "raw_table_row_counts": {"load_account_raw": 1, "load_event_raw": 2},
        "table_profiles": {
            "load_account_raw": {
                "has_source_payload": True,
                "required_payload_columns": ["account_id", "account_name"],
            },
            "load_event_raw": {
                "has_source_payload": True,
                "required_payload_columns": ["event_id", "account_id"],
            },
        },
        "relationships": [{
            "child_raw_table": "load_event_raw",
            "parent_raw_table": "load_account_raw",
            "child_columns": ["account_id"],
            "parent_columns": ["account_id"],
            "require_reuse": True,
        }],
    }
    response = {
        "load_table_rows": {
            "load_account_raw": [{"source_payload": {"account_id": "A1", "account_name": "Acme"}}],
            "load_event_raw": [
                {"source_payload": {"event_id": "E1", "account_id": "A1"}},
                {"source_payload": {"event_id": "E2", "account_id": "A1"}},
            ],
        },
        "staging_sql": [],
        "dimension_sql": [],
        "fact_sql": [],
        "assumptions": [],
    }
    assert validate_codex_etl_response(response, model, plan, profile)["status"] == "passed"

    response["load_table_rows"]["load_event_raw"][1]["source_payload"]["account_id"] = "A2"
    result = validate_codex_etl_response(response, model, plan, profile)
    assert result["status"] == "failed"
    assert any("unresolved foreign-key" in error for error in result["errors"])


def test_validator_accepts_postgresql_join_lateral_function():
    model = parse_ddl("""
CREATE TABLE load_airport (source_payload jsonb NOT NULL);
CREATE TABLE stg_airport (airport_id text PRIMARY KEY);
""")
    plan = build_warehouse_pipeline_plan(model)
    response = {
        "load_table_rows": {"load_airport": [{"source_payload": {"airport_id": "DEL"}}]},
        "staging_sql": ["""
INSERT INTO stg_airport (airport_id)
SELECT parsed.airport_id
FROM load_airport source
CROSS JOIN LATERAL jsonb_to_record(source.source_payload)
AS parsed(airport_id text);
"""],
        "dimension_sql": [],
        "fact_sql": [],
        "assumptions": [],
    }
    result = validate_codex_etl_response(response, model, plan)
    assert result["status"] == "passed", result["errors"]
