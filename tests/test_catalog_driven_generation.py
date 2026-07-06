from decimal import Decimal

from phase2.ddl_parser import parse_ddl
from phase2.synthetic_data_generator import generate_synthetic_data
from phase2.validator import validate_generated_data


def catalog_for(values):
    return {
        "catalog_found": True,
        "rule_count": 1,
        "warnings": [],
        "errors": [],
        "catalog": {
            "business_context": {"business_name": "TestCo"},
            "table_column_rules": [
                {"table_name": "dim_customer", "column_name": "customer_segment", "allowed_values": values}
            ],
        },
    }


def test_allowed_values_drive_generation_without_domain_profile():
    model = parse_ddl("CREATE TABLE dim_customer (customer_id integer PRIMARY KEY, customer_segment varchar(30));")
    catalog = catalog_for(["New", "Premium", "Family Shopper"])
    data = generate_synthetic_data(model, rows_per_table=10, seed=1, value_catalog=catalog)
    assert {row["customer_segment"] for row in data["dim_customer"]} <= {"New", "Premium", "Family Shopper"}
    assert validate_generated_data(model, data, 10, value_catalog=catalog)["status"] == "passed"


def test_no_cross_catalog_contamination():
    model = parse_ddl("CREATE TABLE dim_customer (customer_id integer PRIMARY KEY, customer_segment varchar(30));")
    catalog_a = catalog_for(["New", "Premium", "Family Shopper"])
    catalog_b = catalog_for(["Fleet Buyer", "Private Buyer", "Dealer"])
    data_a = generate_synthetic_data(model, rows_per_table=10, seed=1, value_catalog=catalog_a)
    data_b = generate_synthetic_data(model, rows_per_table=10, seed=1, value_catalog=catalog_b)
    values_a = {row["customer_segment"] for row in data_a["dim_customer"]}
    values_b = {row["customer_segment"] for row in data_b["dim_customer"]}
    assert values_a.isdisjoint({"Fleet Buyer", "Private Buyer", "Dealer"})
    assert values_b.isdisjoint({"New", "Premium", "Family Shopper"})


def test_partial_catalog_uses_catalog_and_semantic_fallback_for_business_keys():
    model = parse_ddl("""
CREATE TABLE stg_customer (
  customer_id varchar(30) PRIMARY KEY,
  customer_segment varchar(30),
  order_id varchar(40)
);
""")
    catalog = {
        "catalog_found": True,
        "rule_count": 1,
        "warnings": [],
        "errors": [],
        "catalog": {"table_column_rules": [
            {"table_name": "stg_customer", "column_name": "customer_segment", "allowed_values": ["New", "Premium"]},
        ]},
    }
    data = generate_synthetic_data(model, rows_per_table=2, seed=1, value_catalog=catalog)
    first = data["stg_customer"][0]
    assert first["customer_segment"] in {"New", "Premium"}
    assert first["customer_id"] == "CUST-000001"
    assert first["order_id"] == "ORDER-20260706-000001"
    assert "stg_customer_001" not in first.values()


def test_calculation_rule_quantity_times_unit_price():
    model = parse_ddl("""
CREATE TABLE fact_sales (
  sales_id integer PRIMARY KEY,
  quantity integer,
  unit_price numeric(6,2),
  line_total_amount numeric(8,2)
);
""")
    catalog = {
        "catalog_found": True,
        "rule_count": 3,
        "warnings": [],
        "errors": [],
        "catalog": {"table_column_rules": [
            {"table_name": "fact_sales", "column_name": "quantity", "numeric_min": 1, "numeric_max": 3},
            {"table_name": "fact_sales", "column_name": "unit_price", "numeric_min": 2, "numeric_max": 5},
            {"table_name": "fact_sales", "column_name": "line_total_amount", "calculation_rule": "line_total_amount = quantity * unit_price"},
        ]},
    }
    data = generate_synthetic_data(model, rows_per_table=10, seed=1, value_catalog=catalog)
    for row in data["fact_sales"]:
        assert row["line_total_amount"] == Decimal(row["quantity"]) * row["unit_price"]
    assert validate_generated_data(model, data, 10, value_catalog=catalog)["status"] == "passed"


def test_fk_values_exist_in_parent_table():
    model = parse_ddl("""
CREATE TABLE dim_customer (customer_key integer PRIMARY KEY, customer_name varchar(50));
CREATE TABLE fact_sales (sales_key integer PRIMARY KEY, customer_key integer REFERENCES dim_customer(customer_key));
""")
    data = generate_synthetic_data(model, rows_per_table=10, seed=1, value_catalog={"catalog_found": False, "warnings": [], "errors": [], "rule_count": 0, "catalog": {}})
    parent_keys = {row["customer_key"] for row in data["dim_customer"]}
    assert all(row["customer_key"] in parent_keys for row in data["fact_sales"])


def test_generic_fallback_avoids_ugly_name_placeholders():
    model = parse_ddl("CREATE TABLE dim_product (product_id integer PRIMARY KEY, product_name varchar(50), customer_segment varchar(20), email varchar(50));")
    data = generate_synthetic_data(model, rows_per_table=3, seed=1, value_catalog={"catalog_found": False, "warnings": [], "errors": [], "rule_count": 0, "catalog": {}})
    first = data["dim_product"][0]
    assert first["product_name"] != "product_name_001"
    assert first["customer_segment"] in {"New", "Regular", "Premium"}
    assert "@" in first["email"]


def test_catalog_allowed_values_are_normalized_to_column_types():
    model = parse_ddl("""
CREATE TABLE typed_catalog (
  id integer PRIMARY KEY,
  int_value integer,
  bool_value boolean,
  date_value date,
  amount numeric(5,2)
);
""")
    catalog = {
        "catalog_found": True,
        "rule_count": 4,
        "warnings": [],
        "errors": [],
        "catalog": {"table_column_rules": [
            {"table_name": "typed_catalog", "column_name": "int_value", "allowed_values": ["1", "2"]},
            {"table_name": "typed_catalog", "column_name": "bool_value", "allowed_values": ["true", "false"]},
            {"table_name": "typed_catalog", "column_name": "date_value", "allowed_values": ["2026-01-01"]},
            {"table_name": "typed_catalog", "column_name": "amount", "numeric_min": 1, "numeric_max": 3},
        ]},
    }
    data = generate_synthetic_data(model, rows_per_table=4, seed=1, value_catalog=catalog)
    for row in data["typed_catalog"]:
        assert isinstance(row["int_value"], int)
        assert isinstance(row["bool_value"], bool)
        assert row["date_value"].isoformat() == "2026-01-01"
        assert row["amount"] <= Decimal("3.00")


def test_percentage_delay_and_status_flag_calculations():
    model = parse_ddl("""
CREATE TABLE fact_metrics (
  id integer PRIMARY KEY,
  numerator numeric(6,2),
  denominator numeric(6,2),
  percentage numeric(6,2),
  promised_timestamp timestamp,
  actual_timestamp timestamp,
  delay_minutes integer,
  status varchar(20),
  success_flag boolean
);
""")
    catalog = {
        "catalog_found": True,
        "rule_count": 8,
        "warnings": [],
        "errors": [],
        "catalog": {"table_column_rules": [
            {"table_name": "fact_metrics", "column_name": "numerator", "numeric_min": 10, "numeric_max": 10},
            {"table_name": "fact_metrics", "column_name": "denominator", "numeric_min": 20, "numeric_max": 20},
            {"table_name": "fact_metrics", "column_name": "percentage", "calculation_rule": "percentage = numerator / denominator * 100"},
            {"table_name": "fact_metrics", "column_name": "promised_timestamp", "value_examples": ["2026-01-01T10:00:00"]},
            {"table_name": "fact_metrics", "column_name": "actual_timestamp", "value_examples": ["2026-01-01T10:30:00"]},
            {"table_name": "fact_metrics", "column_name": "delay_minutes", "calculation_rule": "delay_minutes = actual_timestamp - promised_timestamp"},
            {"table_name": "fact_metrics", "column_name": "status", "allowed_values": ["Successful"]},
            {"table_name": "fact_metrics", "column_name": "success_flag", "calculation_rule": "true when status = Successful"},
        ]},
    }
    data = generate_synthetic_data(model, rows_per_table=2, seed=1, value_catalog=catalog)
    for row in data["fact_metrics"]:
        assert row["percentage"] == Decimal("50.00")
        assert row["delay_minutes"] == 30
        assert row["success_flag"] is True
    assert validate_generated_data(model, data, 2, value_catalog=catalog)["status"] == "passed"


def test_catalog_date_key_pattern_yyyymmdd_generates_integer_without_crash():
    model = parse_ddl("CREATE TABLE date_values (id integer PRIMARY KEY, date_key integer);")
    catalog = {
        "catalog_found": True,
        "rule_count": 1,
        "warnings": [],
        "errors": [],
        "catalog": {"table_column_rules": [
            {"table_name": "date_values", "column_name": "date_key", "value_pattern": "YYYYMMDD"},
        ]},
    }
    data = generate_synthetic_data(model, rows_per_table=2, seed=1, value_catalog=catalog)
    assert isinstance(data["date_values"][0]["date_key"], int)
    assert data["date_values"][0]["date_key"] == 20260706


def test_catalog_braced_yyyymmdd_pattern_generates_integer_date_key():
    model = parse_ddl("CREATE TABLE fact_sales (sales_key integer PRIMARY KEY, order_date_key integer);")
    catalog = {
        "catalog_found": True,
        "rule_count": 1,
        "warnings": [],
        "errors": [],
        "catalog": {"table_column_rules": [
            {"table_name": "fact_sales", "column_name": "order_date_key", "value_pattern": "{YYYYMMDD}"},
        ]},
    }
    data = generate_synthetic_data(model, rows_per_table=1, seed=1, value_catalog=catalog)
    assert data["fact_sales"][0]["order_date_key"] == 20260706


def test_zero_padded_sequence_patterns_render_generically():
    model = parse_ddl("""
CREATE TABLE generated_ids (
  id integer PRIMARY KEY,
  customer_id varchar(20),
  store_id varchar(20),
  order_id varchar(40),
  line_number integer
);
""")
    catalog = {
        "catalog_found": True,
        "rule_count": 4,
        "warnings": [],
        "errors": [],
        "catalog": {"table_column_rules": [
            {"table_name": "generated_ids", "column_name": "customer_id", "value_pattern": "CUST-{000001}"},
            {"table_name": "generated_ids", "column_name": "store_id", "value_pattern": "STORE-{0001}"},
            {"table_name": "generated_ids", "column_name": "order_id", "value_pattern": "ORD-{YYYYMMDD}-{000001}"},
            {"table_name": "generated_ids", "column_name": "line_number", "value_pattern": "{line_number}"},
        ]},
    }
    data = generate_synthetic_data(model, rows_per_table=1, seed=1, value_catalog=catalog)
    row = data["generated_ids"][0]
    assert row["customer_id"] == "CUST-000001"
    assert row["store_id"] == "STORE-0001"
    assert row["order_id"] == "ORD-20260706-000001"
    assert row["line_number"] == 1


def test_catalog_pattern_applies_to_varchar_primary_key():
    model = parse_ddl("CREATE TABLE stg_product (product_id varchar(30) PRIMARY KEY, product_name varchar(50));")
    catalog = {
        "catalog_found": True,
        "rule_count": 1,
        "warnings": [],
        "errors": [],
        "catalog": {"table_column_rules": [
            {"table_name": "stg_product", "column_name": "product_id", "value_pattern": "PROD-{000001}"},
        ]},
    }
    data = generate_synthetic_data(model, rows_per_table=1, seed=1, value_catalog=catalog)
    assert data["stg_product"][0]["product_id"] == "PROD-000001"


def test_invalid_decimal_pattern_falls_back_without_crashing():
    model = parse_ddl("CREATE TABLE bad_pattern (id integer PRIMARY KEY, amount numeric(6,2));")
    catalog = {
        "catalog_found": True,
        "rule_count": 1,
        "warnings": [],
        "errors": [],
        "catalog": {"table_column_rules": [
            {"table_name": "bad_pattern", "column_name": "amount", "value_pattern": "not-a-number"},
        ]},
    }
    data = generate_synthetic_data(model, rows_per_table=1, seed=1, value_catalog=catalog)
    assert data["bad_pattern"][0]["amount"] == Decimal("0.00")
    assert data["__stats__"]["type_normalization_warnings"]


def test_fact_date_key_uses_existing_dim_date_values_when_possible():
    model = parse_ddl("""
CREATE TABLE dim_date (date_key integer PRIMARY KEY, full_date date);
CREATE TABLE fact_sales (
  sales_key integer PRIMARY KEY,
  order_date_key integer
);
""")
    catalog = {
        "catalog_found": True,
        "rule_count": 2,
        "warnings": [],
        "errors": [],
        "catalog": {"table_column_rules": [
            {"table_name": "dim_date", "column_name": "date_key", "value_pattern": "YYYYMMDD"},
            {"table_name": "fact_sales", "column_name": "order_date_key", "relationship_rule": "choose existing dim_date.date_key"},
        ]},
    }
    data = generate_synthetic_data(model, rows_per_table=3, seed=1, value_catalog=catalog)
    dim_keys = {row["date_key"] for row in data["dim_date"]}
    assert dim_keys == {20260706, 20260707, 20260708}
    assert {row["order_date_key"] for row in data["fact_sales"]} <= dim_keys
