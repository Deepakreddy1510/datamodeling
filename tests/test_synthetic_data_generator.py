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


def test_varchar_max_lengths_are_respected_for_business_values():
    model = parse_ddl("""
CREATE TABLE web_values (
  id integer PRIMARY KEY,
  email varchar(30),
  source_file_name varchar(30),
  campaign_theme varchar(30),
  vehicle_segment character varying(20),
  raw_device_value varchar(30),
  raw_browser_value varchar(30),
  raw_operating_system_value varchar(30),
  raw_page_value varchar(30),
  raw_referrer_value varchar(30),
  raw_utm_parameter_value varchar(30),
  raw_event_value varchar(30),
  market_name varchar(30)
);
""")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    row = data["web_values"][0]
    for column in model.tables[0].columns:
        value = row[column.name]
        if isinstance(value, str) and column.max_length:
            assert len(value) <= column.max_length
    assert row["source_file_name"].endswith(".csv")
    assert row["raw_device_value"] in {"Desktop", "Mobile", "Tablet"}
    assert row["raw_browser_value"] in {"Chrome", "Safari", "Edge", "Firefox", "Samsung Internet", "Opera"}
    assert row["raw_operating_system_value"] in {"Windows", "macOS", "iOS", "Android", "Linux", "Chrome OS"}
    assert row["raw_page_value"].startswith("/")
    assert row["raw_referrer_value"] in {"google.com", "bing.com", "facebook.com", "autotrader.co.uk", "direct", "email_campaign"}
    assert row["raw_utm_parameter_value"] in {"google_cpc", "facebook_paid", "email_june", "organic_search", "direct_none", "display_retargeting"}
    assert row["raw_event_value"] in {"page_view", "search_started", "vehicle_viewed", "finance_clicked", "lead_submitted", "valuation_started", "call_clicked"}
    assert row["market_name"] in {"United Kingdom", "England", "Scotland", "Wales", "Northern Ireland", "London", "Manchester", "Birmingham", "Leeds", "Glasgow"}


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
