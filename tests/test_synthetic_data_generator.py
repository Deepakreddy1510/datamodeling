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


def test_phase2_generates_analytical_data_without_catalog():
    model = parse_ddl("""
CREATE TABLE dim_customer (
  customer_id varchar(20) PRIMARY KEY,
  customer_name varchar(50),
  customer_segment varchar(20) CHECK (customer_segment IN ('New', 'Premium'))
);
CREATE TABLE fact_sales (
  sales_key integer PRIMARY KEY,
  customer_id varchar(20) REFERENCES dim_customer(customer_id),
  quantity integer CHECK (quantity BETWEEN 1 AND 10),
  order_total_amount numeric(8,2)
);
""")
    no_catalog = {"catalog_found": False, "markers_present": False, "warnings": [], "errors": [], "rule_count": 0, "catalog": {}}
    data = generate_synthetic_data(model, rows_per_table=25, seed=1, value_catalog=no_catalog)
    assert data["dim_customer"][0]["customer_id"].startswith("CUST-")
    assert {row["customer_segment"] for row in data["dim_customer"]} <= {"New", "Premium"}
    parent_ids = {row["customer_id"] for row in data["dim_customer"]}
    assert {row["customer_id"] for row in data["fact_sales"]} <= parent_ids
    assert validate_generated_data(model, data, 25, value_catalog=no_catalog)["status"] in {"passed", "passed_with_warnings"}


def test_business_key_inference_generates_readable_ids_without_catalog():
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


def test_composite_unique_constraints_are_respected_without_catalog():
    model = parse_ddl("""
CREATE TABLE dim_location (
  location_key integer PRIMARY KEY,
  city varchar(40),
  region varchar(40),
  country varchar(40),
  UNIQUE (city, region, country)
);
""")
    data = generate_synthetic_data(model, rows_per_table=40, seed=1)
    tuples = {(row["city"], row["region"], row["country"]) for row in data["dim_location"]}
    assert len(tuples) == 40
    assert validate_generated_data(model, data, 40)["status"] in {"passed", "passed_with_warnings"}


def test_malformed_catalog_is_non_blocking_for_generation_and_validation():
    model = parse_ddl("CREATE TABLE dim_customer (customer_id varchar(20) PRIMARY KEY, customer_name varchar(50));")
    malformed_catalog = {
        "catalog_found": False,
        "markers_present": True,
        "warnings": [],
        "errors": ["Synthetic value catalog JSON is invalid"],
        "rule_count": 0,
        "catalog": {},
    }
    data = generate_synthetic_data(model, rows_per_table=3, seed=1, value_catalog=malformed_catalog)
    result = validate_generated_data(model, data, 3, value_catalog=malformed_catalog)
    assert result["status"] == "passed_with_warnings"
    assert data["dim_customer"][0]["customer_id"] == "CUST-000001"
    assert result["errors"] == []


def test_fk_safe_unique_constraint_does_not_mutate_fk_values():
    model = parse_ddl("""
CREATE TABLE dim_order (order_id varchar(30) PRIMARY KEY);
CREATE TABLE dim_product (product_id varchar(30) PRIMARY KEY);
CREATE TABLE fact_sales (
  sales_key integer PRIMARY KEY,
  order_id varchar(30) REFERENCES dim_order(order_id),
  product_id varchar(30) REFERENCES dim_product(product_id),
  UNIQUE (order_id, product_id)
);
""")
    data = generate_synthetic_data(model, rows_per_table=20, seed=1)
    product_ids = {row["product_id"] for row in data["dim_product"]}
    order_ids = {row["order_id"] for row in data["dim_order"]}
    assert {row["product_id"] for row in data["fact_sales"]} <= product_ids
    assert {row["order_id"] for row in data["fact_sales"]} <= order_ids
    assert validate_generated_data(model, data, 20)["status"] in {"passed", "passed_with_warnings"}


def test_composite_unique_keeps_constrained_country_value():
    model = parse_ddl("""
CREATE TABLE dim_location (
  location_key integer PRIMARY KEY,
  city varchar(40),
  region varchar(40),
  country varchar(40),
  UNIQUE (city, region, country)
);
""")
    catalog = {
        "catalog_found": True,
        "rule_count": 1,
        "warnings": [],
        "errors": [],
        "catalog": {"table_column_rules": [
            {"table_name": "dim_location", "column_name": "country", "allowed_values": ["India"]},
        ]},
    }
    data = generate_synthetic_data(model, rows_per_table=100, seed=1, value_catalog=catalog)
    tuples = {(row["city"], row["region"], row["country"]) for row in data["dim_location"]}
    assert len(tuples) == 100
    assert {row["country"] for row in data["dim_location"]} == {"India"}
    assert validate_generated_data(model, data, 100, value_catalog=catalog)["status"] in {"passed", "passed_with_warnings"}
