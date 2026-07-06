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
    assert table.check_constraints


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
    assert table.check_constraints


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


def test_parse_unique_constraints_metadata():
    model = parse_ddl("""
CREATE TABLE unique_test (
  id integer PRIMARY KEY,
  code varchar(20) UNIQUE,
  sku varchar(20),
  asin varchar(20),
  CONSTRAINT uq_sku_asin UNIQUE (sku, asin)
);
""")
    table = model.tables[0]
    assert [constraint.columns for constraint in table.unique_constraints] == [["code"], ["sku", "asin"]]


def test_parse_supported_check_constraints_metadata():
    model = parse_ddl("""
CREATE TABLE check_test (
  id integer PRIMARY KEY,
  status varchar(20),
  amount numeric(6,2),
  score integer,
  CHECK (status IN ('Active','Inactive')),
  CHECK (amount >= 0),
  CHECK (score BETWEEN 1 AND 10)
);
""")
    checks = model.tables[0].check_constraints
    assert [(check.column, check.operator, check.supported) for check in checks] == [
        ("status", "IN", True),
        ("amount", ">=", True),
        ("score", "BETWEEN", True),
    ]


def test_unsupported_check_constraint_is_reported_as_warning():
    model = parse_ddl("""
CREATE TABLE unsupported_check_test (
  id integer PRIMARY KEY,
  amount numeric(6,2),
  CHECK (amount IS NOT NULL OR id > 0)
);
""")
    table = model.tables[0]
    assert table.check_constraints[0].supported is False
    assert table.ignored_constraints
    assert model.warnings


def test_parse_postgres_types_without_constraint_text_in_data_type():
    model = parse_ddl("""
CREATE TABLE postgres_type_test (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  payload JSONB NOT NULL,
  raw_payload JSON DEFAULT '{}' NOT NULL,
  event_time TIMESTAMPTZ NOT NULL DEFAULT now(),
  display_name VARCHAR(50) NOT NULL,
  amount NUMERIC(12,2) CHECK (amount >= 0),
  short_code CHAR(5) COLLATE "C",
  sequence_no BIGSERIAL,
  score DOUBLE PRECISION,
  ratio REAL,
  event_clock TIME
);
""")
    columns = {column.name: column for column in model.tables[0].columns}
    assert columns["payload"].data_type.upper() == "JSONB"
    assert columns["payload"].nullable is False
    assert columns["raw_payload"].data_type.upper() == "JSON"
    assert columns["raw_payload"].default == "'{}'"
    assert columns["event_time"].data_type.upper() == "TIMESTAMPTZ"
    assert columns["event_time"].nullable is False
    assert columns["display_name"].data_type.upper() == "VARCHAR(50)"
    assert columns["display_name"].max_length == 50
    assert columns["amount"].data_type.upper() == "NUMERIC(12,2)"
    assert columns["amount"].numeric_precision == 12
    assert columns["amount"].numeric_scale == 2
    assert "NOT NULL" not in columns["payload"].data_type.upper()
    assert "DEFAULT" not in columns["event_time"].data_type.upper()
