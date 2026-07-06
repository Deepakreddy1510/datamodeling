from datetime import date, datetime, time
from decimal import Decimal

from phase2.ddl_parser import parse_ddl
from phase2.synthetic_data_generator import SyntheticDataError, generate_synthetic_data
from phase2.validator import validate_generated_data


def test_generate_data_preserves_pk_and_fk_consistency():
    model = parse_ddl("""
CREATE TABLE customer (customer_id integer PRIMARY KEY, customer_name text NOT NULL);
CREATE TABLE sales_order (
  order_id integer PRIMARY KEY,
  customer_id integer REFERENCES customer(customer_id),
  order_date date NOT NULL
);
""")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    assert len(data["customer"]) == 100
    assert len(data["sales_order"]) == 100
    assert validate_generated_data(model, data, 100)["status"] == "passed"


def test_varchar_max_lengths_are_respected_for_fallback_values():
    model = parse_ddl("""
CREATE TABLE web_values (
  id integer PRIMARY KEY,
  email varchar(30),
  source_file_name varchar(30),
  campaign_theme varchar(30),
  customer_segment character varying(20),
  status varchar(30)
);
""")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    row = data["web_values"][0]
    for column in model.tables[0].columns:
        value = row[column.name]
        if isinstance(value, str) and column.max_length:
            assert len(value) <= column.max_length
    assert "@" in row["email"]
    assert row["status"] in {"New", "Active", "Pending", "Completed", "Inactive"}


def test_phase2_generates_analytical_data_from_ddl_only():
    model = parse_ddl("""
CREATE TABLE dim_customer (
  customer_id varchar(20) PRIMARY KEY,
  customer_name varchar(50) NOT NULL,
  customer_segment varchar(20) CHECK (customer_segment IN ('New', 'Premium'))
);
CREATE TABLE fact_sales (
  sales_key integer PRIMARY KEY,
  customer_id varchar(20) REFERENCES dim_customer(customer_id),
  quantity integer CHECK (quantity BETWEEN 1 AND 10),
  order_total_amount numeric(8,2)
);
""")
    data = generate_synthetic_data(model, rows_per_table=25, seed=1)
    assert data["dim_customer"][0]["customer_id"].startswith("CUST-")
    assert {row["customer_segment"] for row in data["dim_customer"]} <= {"New", "Premium"}
    parent_ids = {row["customer_id"] for row in data["dim_customer"]}
    assert {row["customer_id"] for row in data["fact_sales"]} <= parent_ids
    assert validate_generated_data(model, data, 25)["status"] in {"passed", "passed_with_warnings"}


def test_business_key_inference_generates_readable_ids_from_ddl_only():
    model = parse_ddl("""
CREATE TABLE business_keys (
  customer_id varchar(30) PRIMARY KEY,
  product_id varchar(30),
  store_id varchar(30),
  order_id varchar(40),
  payment_id varchar(30),
  delivery_id varchar(30)
);
""")
    data = generate_synthetic_data(model, rows_per_table=1, seed=1)
    row = data["business_keys"][0]
    assert row["customer_id"] == "CUST-000001"
    assert row["product_id"] == "PROD-000001"
    assert row["store_id"] == "STORE-000001"
    assert row["order_id"] == "ORDER-20260706-000001"
    assert row["payment_id"] == "PAYMENT-000001"
    assert row["delivery_id"] == "DELIVERY-000001"


def test_composite_unique_constraints_are_repaired_from_ddl_only():
    model = parse_ddl("""
CREATE TABLE dim_location (
  location_key integer PRIMARY KEY,
  city varchar(40),
  region varchar(40),
  country varchar(40),
  UNIQUE (city, region, country)
);
""")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    tuples = {(row["city"], row["region"], row["country"]) for row in data["dim_location"]}
    assert len(tuples) == 100
    assert validate_generated_data(model, data, 100)["status"] in {"passed", "passed_with_warnings"}


def test_generation_supports_common_postgres_types_and_json():
    model = parse_ddl("""
CREATE TABLE typed_values (
  id integer PRIMARY KEY,
  text_value text NOT NULL,
  varchar_value varchar(20) NOT NULL,
  int_value integer NOT NULL,
  bigint_value bigint NOT NULL,
  amount numeric(12,2) CHECK (amount >= 0),
  active boolean NOT NULL,
  event_date date NOT NULL,
  event_time time NOT NULL,
  event_timestamp timestamp NOT NULL,
  event_timestamptz timestamptz NOT NULL,
  row_uuid uuid NOT NULL,
  payload json NOT NULL,
  payload_b jsonb NOT NULL
);
""")
    data = generate_synthetic_data(model, rows_per_table=5, seed=1)
    row = data["typed_values"][0]
    assert isinstance(row["text_value"], str)
    assert isinstance(row["varchar_value"], str)
    assert isinstance(row["int_value"], int)
    assert isinstance(row["bigint_value"], int)
    assert isinstance(row["amount"], Decimal)
    assert isinstance(row["active"], bool)
    assert isinstance(row["event_date"], date)
    assert isinstance(row["event_time"], time)
    assert isinstance(row["event_timestamp"], datetime)
    assert isinstance(row["event_timestamptz"], datetime)
    assert isinstance(row["row_uuid"], str)
    assert isinstance(row["payload"], dict)
    assert isinstance(row["payload_b"], dict)
    assert validate_generated_data(model, data, 5)["status"] == "passed"


def test_primary_key_uniqueness_for_multiple_pk_shapes():
    model = parse_ddl("""
CREATE TABLE integer_pk (id integer PRIMARY KEY, value text);
CREATE TABLE text_pk (customer_id varchar(30) PRIMARY KEY, value text);
CREATE TABLE uuid_pk (id uuid PRIMARY KEY, value text);
CREATE TABLE composite_pk (part_a varchar(20), part_b integer, value text, PRIMARY KEY (part_a, part_b));
""")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    for table in model.tables:
        tuples = {tuple(row[col] for col in table.primary_key) for row in data[table.name]}
        assert len(tuples) == 100
    assert validate_generated_data(model, data, 100)["status"] in {"passed", "passed_with_warnings"}


def test_fk_inside_unique_constraint_remains_valid():
    model = parse_ddl("""
CREATE TABLE parent_product (product_id varchar(20) PRIMARY KEY);
CREATE TABLE order_line (
  line_id integer PRIMARY KEY,
  order_id varchar(20),
  product_id varchar(20) REFERENCES parent_product(product_id),
  UNIQUE (order_id, product_id)
);
""")
    data = generate_synthetic_data(model, rows_per_table=20, seed=1)
    parent_ids = {row["product_id"] for row in data["parent_product"]}
    assert {row["product_id"] for row in data["order_line"]} <= parent_ids
    assert validate_generated_data(model, data, 20)["status"] in {"passed", "passed_with_warnings"}


def test_unique_check_in_capacity_failure_is_clear():
    model = parse_ddl("""
CREATE TABLE constrained_unique (
  id integer PRIMARY KEY,
  status varchar(10) UNIQUE CHECK (status IN ('A', 'B'))
);
""")
    try:
        generate_synthetic_data(model, rows_per_table=100, seed=1)
    except SyntheticDataError as exc:
        assert "DDL constraint capacity exceeded" in str(exc)
    else:
        raise AssertionError("Expected capacity failure for UNIQUE CHECK IN with only two values")


def test_generic_calculations_from_column_names():
    model = parse_ddl("""
CREATE TABLE fact_line (
  line_id integer PRIMARY KEY,
  quantity integer CHECK (quantity > 0),
  unit_price numeric(8,2) CHECK (unit_price > 0),
  line_total_amount numeric(10,2),
  promised_delivery_time timestamp,
  actual_delivery_time timestamp,
  delivery_delay_minutes integer,
  is_delayed boolean
);
""")
    data = generate_synthetic_data(model, rows_per_table=10, seed=1)
    for row in data["fact_line"]:
        assert row["line_total_amount"] == row["quantity"] * row["unit_price"]
        assert row["delivery_delay_minutes"] >= 0
        assert row["is_delayed"] == (row["delivery_delay_minutes"] > 0)
    assert validate_generated_data(model, data, 10)["status"] == "passed"
