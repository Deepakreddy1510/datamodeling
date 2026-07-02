from phase2.ddl_parser import parse_ddl


def test_parse_table_primary_and_foreign_keys():
    model = parse_ddl("""
CREATE SCHEMA analytics;
CREATE TABLE analytics.customer (
  customer_id integer PRIMARY KEY,
  customer_name varchar(100) NOT NULL
);
CREATE TABLE analytics.sales_order (
  order_id integer,
  customer_id integer REFERENCES analytics.customer(customer_id),
  CONSTRAINT pk_sales_order PRIMARY KEY (order_id)
);
""")
    assert model.schemas == ["analytics"]
    assert len(model.tables) == 2
    order = model.tables[1]
    assert order.primary_key == ["order_id"]
    assert order.foreign_keys[0].child_columns == ["customer_id"]
    assert order.foreign_keys[0].parent_table == "customer"


def test_parse_table_level_unique_constraint_is_not_column():
    model = parse_ddl("""
CREATE TABLE product_listing (
  product_listing_id integer PRIMARY KEY,
  sku_code text NOT NULL,
  asin text NOT NULL,
  UNIQUE (sku_code, asin)
);
""")
    table = model.tables[0]
    assert table.column_names() == ["product_listing_id", "sku_code", "asin"]
    assert "UNIQUE" not in table.column_names()


def test_parse_named_unique_constraint_is_not_column():
    model = parse_ddl("""
CREATE TABLE product_listing (
  product_listing_id integer PRIMARY KEY,
  sku_code text NOT NULL,
  asin text NOT NULL,
  CONSTRAINT uq_sku_asin UNIQUE (sku_code, asin)
);
""")
    table = model.tables[0]
    assert table.column_names() == ["product_listing_id", "sku_code", "asin"]
    assert "CONSTRAINT" not in table.column_names()
    assert "UNIQUE" not in table.column_names()
