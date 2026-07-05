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
