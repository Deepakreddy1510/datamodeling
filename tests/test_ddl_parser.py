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


def test_parse_table_level_check_constraint_is_not_column():
    model = parse_ddl("""
CREATE TABLE audit_load (
  audit_load_id integer PRIMARY KEY,
  load_status varchar(30) NOT NULL,
  CHECK (load_status IN ('started','completed','failed','validated'))
);
""")
    table = model.tables[0]
    assert table.column_names() == ["audit_load_id", "load_status"]
    assert "CHECK" not in table.column_names()
    assert table.ignored_constraints


def test_parse_named_check_constraint_is_not_column():
    model = parse_ddl("""
CREATE TABLE audit_load (
  audit_load_id integer PRIMARY KEY,
  load_status varchar(30) NOT NULL,
  CONSTRAINT ck_audit_load_status CHECK (load_status IN ('started','completed','failed','validated'))
);
""")
    table = model.tables[0]
    assert table.column_names() == ["audit_load_id", "load_status"]
    assert "CONSTRAINT" not in table.column_names()
    assert "CHECK" not in table.column_names()
    assert table.ignored_constraints


def test_parse_varchar_and_character_varying_lengths():
    model = parse_ddl("""
CREATE TABLE length_test (
  id integer PRIMARY KEY,
  short_name varchar(30),
  campaign_name CHARACTER VARYING(20)
);
""")
    columns = {column.name: column for column in model.tables[0].columns}
    assert columns["short_name"].max_length == 30
    assert columns["campaign_name"].max_length == 20


def test_parse_numeric_precision_and_scale():
    model = parse_ddl("""
CREATE TABLE numeric_test (
  id integer PRIMARY KEY,
  small_amount NUMERIC(5,2),
  large_amount decimal(10,4)
);
""")
    columns = {column.name: column for column in model.tables[0].columns}
    assert columns["small_amount"].numeric_precision == 5
    assert columns["small_amount"].numeric_scale == 2
    assert columns["large_amount"].numeric_precision == 10
    assert columns["large_amount"].numeric_scale == 4


def test_parse_column_default_value():
    model = parse_ddl("""
CREATE TABLE default_test (
  id integer PRIMARY KEY,
  status varchar(20) DEFAULT 'new' NOT NULL
);
""")
    columns = {column.name: column for column in model.tables[0].columns}
    assert columns["status"].default == "'new'"
