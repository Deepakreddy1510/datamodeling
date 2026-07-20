from phase2.ddl_parser import parse_ddl
from phase2.semantic_context import build_semantic_context
from phase2.synthetic_data_generator import generate_synthetic_data
from phase2.validator import validate_generated_data


def _product_model():
    return parse_ddl("""
CREATE TABLE dim_customer (
  customer_id varchar(30) PRIMARY KEY,
  customer_name varchar(80),
  email varchar(120)
);
CREATE TABLE dim_product (
  product_id varchar(30) PRIMARY KEY,
  product_name varchar(120),
  brand_name varchar(80)
);
CREATE TABLE fact_order (
  order_key integer PRIMARY KEY,
  customer_id varchar(30) REFERENCES dim_customer(customer_id),
  product_id varchar(30) REFERENCES dim_product(product_id),
  quantity integer CHECK (quantity > 0),
  unit_price numeric(8,2) CHECK (unit_price > 0),
  line_total_amount numeric(10,2)
);
""")


def test_semantic_context_infers_column_types_from_yaml_and_ddl():
    model = _product_model()
    context = build_semantic_context({
        "business_name": "Nimbus",
        "business_type": "Subscription analytics",
        "business_description": "Track subscription offerings, customers, orders, and payments.",
    }, model)
    assert context.semantic_for("dim_customer", "customer_name").semantic_type == "person_name"
    assert context.semantic_for("dim_customer", "email").semantic_type == "email"
    assert context.semantic_for("dim_product", "product_name").semantic_type == "product_or_service"
    assert context.semantic_for("fact_order", "customer_id").semantic_type == "foreign_key"


def test_generator_uses_yaml_context_without_hardcoded_business_values():
    model = _product_model()
    context_a = build_semantic_context({
        "business_name": "Alpha",
        "business_type": "grocery subscription",
        "business_description": "Online grocery subscriptions with baskets and weekly deliveries.",
    }, model)
    context_b = build_semantic_context({
        "business_name": "Beta",
        "business_type": "insurance claims",
        "business_description": "Insurance claim processing with policies and adjuster reviews.",
    }, model)
    data_a = generate_synthetic_data(model, rows_per_table=3, seed=1, semantic_context=context_a)
    data_b = generate_synthetic_data(model, rows_per_table=3, seed=1, semantic_context=context_b)
    name_a = data_a["dim_product"][0]["product_name"].lower()
    name_b = data_b["dim_product"][0]["product_name"].lower()
    assert "grocery" in name_a or "subscription" in name_a
    assert "insurance" in name_b or "claims" in name_b
    assert name_a != name_b
    assert validate_generated_data(model, data_a, 3)["status"] in {"passed", "passed_with_warnings"}
    assert validate_generated_data(model, data_b, 3)["status"] in {"passed", "passed_with_warnings"}


def test_customer_email_matches_generated_name():
    model = parse_ddl("""
CREATE TABLE dim_customer (
  customer_id varchar(30) PRIMARY KEY,
  customer_name varchar(80),
  email varchar(120)
);
""")
    data = generate_synthetic_data(model, rows_per_table=5, seed=1, business_input={"business_description": "Customer engagement analytics"})
    first = data["dim_customer"][0]
    first_name, last_name = first["customer_name"].lower().split()[0], first["customer_name"].lower().split()[-1]
    assert first_name in first["email"]
    assert last_name in first["email"]
