from decimal import Decimal
from phase2.ddl_parser import parse_ddl
from phase2.synthetic_data_generator import generate_synthetic_data
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


def test_generate_data_succeeds_with_table_level_unique_constraints():
    model = parse_ddl("""
CREATE TABLE product_listing (
  product_listing_id integer PRIMARY KEY,
  sku_code text NOT NULL,
  asin text NOT NULL,
  UNIQUE (sku_code, asin)
);
CREATE TABLE named_product_listing (
  named_product_listing_id integer PRIMARY KEY,
  sku_code text NOT NULL,
  asin text NOT NULL,
  CONSTRAINT uq_named_sku_asin UNIQUE (sku_code, asin)
);
""")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    assert len(data["product_listing"]) == 100
    assert len(data["named_product_listing"]) == 100
    assert validate_generated_data(model, data, 100)["status"] == "passed"


def test_varchar_max_lengths_are_respected_for_catalog_or_fallback_values():
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
    catalog = {
        "catalog_found": True,
        "rule_count": 3,
        "warnings": [],
        "errors": [],
        "catalog": {"table_column_rules": [
            {"table_name": "web_values", "column_name": "source_file_name", "value_pattern": "source_{number}.csv"},
            {"table_name": "web_values", "column_name": "campaign_theme", "allowed_values": ["Awareness", "Retention"]},
            {"table_name": "web_values", "column_name": "customer_segment", "allowed_values": ["New", "Premium"]},
        ]},
    }
    data = generate_synthetic_data(model, rows_per_table=100, seed=1, value_catalog=catalog)
    row = data["web_values"][0]
    for column in model.tables[0].columns:
        value = row[column.name]
        if isinstance(value, str) and column.max_length:
            assert len(value) <= column.max_length
    assert row["source_file_name"].endswith(".csv")
    assert row["campaign_theme"] in {"Awareness", "Retention"}
    assert row["customer_segment"] in {"New", "Premium"}
    assert row["status"] in {"New", "Active", "Pending", "Completed", "Inactive"}


def test_fk_child_values_copy_exact_parent_values():
    model = parse_ddl("""
CREATE TABLE dim_device (device_id varchar(20) PRIMARY KEY, raw_device_value varchar(30));
CREATE TABLE fact_session (
  session_id integer PRIMARY KEY,
  device_id varchar(20) REFERENCES dim_device(device_id)
);
""")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    parent_values = {row["device_id"] for row in data["dim_device"]}
    assert all(row["device_id"] in parent_values for row in data["fact_session"])


def test_numeric_precision_and_scale_are_respected():
    model = parse_ddl("""
CREATE TABLE numeric_values (
  id integer PRIMARY KEY,
  amount numeric(5,2),
  price decimal(6,2),
  score numeric(3,0)
);
""")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    for row in data["numeric_values"]:
        assert row["amount"] <= Decimal("999.99")
        assert row["price"] <= Decimal("9999.99")
        assert row["score"] <= Decimal("999")
        assert abs(row["amount"].as_tuple().exponent) == 2
        assert abs(row["price"].as_tuple().exponent) == 2
        assert row["score"].as_tuple().exponent == 0
