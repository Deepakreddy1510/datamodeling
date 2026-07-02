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
