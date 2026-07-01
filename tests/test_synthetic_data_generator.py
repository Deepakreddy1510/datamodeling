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
