from phase2.ddl_parser import parse_ddl
from phase2.synthetic_data_generator import generate_synthetic_data
from phase2.validator import validate_generated_data


def _lineage_model():
    return parse_ddl("""
CREATE TABLE load_item_raw (
  item_id varchar(20) PRIMARY KEY,
  item_name varchar(60),
  category varchar(30)
);
CREATE TABLE stg_item (
  item_id varchar(20) PRIMARY KEY,
  item_name varchar(60),
  category varchar(30)
);
CREATE TABLE dim_item (
  item_key integer PRIMARY KEY,
  item_id varchar(20),
  item_name varchar(60),
  category varchar(30),
  UNIQUE (item_id)
);
CREATE TABLE fact_sales (
  sales_key integer PRIMARY KEY,
  item_key integer REFERENCES dim_item(item_key),
  item_id varchar(20),
  quantity integer CHECK (quantity > 0),
  unit_price numeric(8,2) CHECK (unit_price > 0),
  sale_amount numeric(10,2)
);
""")


def test_lineage_generation_derives_stg_dim_and_fact_keys_generically():
    model = _lineage_model()
    data = generate_synthetic_data(model, rows_per_table=5, seed=20)
    raw_by_id = {row["item_id"]: row for row in data["load_item_raw"]}
    stg_by_id = {row["item_id"]: row for row in data["stg_item"]}
    dim_by_id = {row["item_id"]: row for row in data["dim_item"]}
    dim_by_key = {row["item_key"]: row for row in data["dim_item"]}
    for item_id, stg in stg_by_id.items():
        assert stg["item_name"] == raw_by_id[item_id]["item_name"]
        assert stg["category"] == raw_by_id[item_id]["category"]
    for item_id, dim in dim_by_id.items():
        assert dim["item_name"] == stg_by_id[item_id]["item_name"]
        assert dim["category"] == stg_by_id[item_id]["category"]
    for fact in data["fact_sales"]:
        assert dim_by_key[fact["item_key"]]["item_id"] == fact["item_id"]
        assert fact["sale_amount"] == fact["quantity"] * fact["unit_price"]
    validation = validate_generated_data(model, data, 5)
    assert validation["status"] in {"passed", "passed_with_warnings"}
    assert validation["lineage_validation"]["status"] == "passed"


def test_lineage_validator_fails_when_staging_differs_from_raw():
    model = _lineage_model()
    data = generate_synthetic_data(model, rows_per_table=3, seed=21)
    data["stg_item"][0]["item_name"] = "Different"
    validation = validate_generated_data(model, data, 3)
    assert validation["status"] == "failed"
    assert any("does not match load_item_raw.item_name" in err for err in validation["lineage_validation"]["errors"])


def test_lineage_validator_fails_when_dimension_differs_from_staging():
    model = _lineage_model()
    data = generate_synthetic_data(model, rows_per_table=3, seed=22)
    data["dim_item"][0]["category"] = "Different"
    validation = validate_generated_data(model, data, 3)
    assert validation["status"] == "failed"
    assert any("does not match stg_item.category" in err for err in validation["lineage_validation"]["errors"])


def test_lineage_validator_fails_when_fact_key_points_to_wrong_dimension():
    model = _lineage_model()
    data = generate_synthetic_data(model, rows_per_table=3, seed=23)
    data["fact_sales"][0]["item_key"] = data["dim_item"][1]["item_key"]
    validation = validate_generated_data(model, data, 3)
    assert validation["status"] == "failed"
    assert any("points to dim_item" in err for err in validation["lineage_validation"]["errors"])


def test_lineage_generation_works_for_non_pharma_route_example():
    model = parse_ddl("""
CREATE TABLE load_route_raw (route_id varchar(20) PRIMARY KEY, origin_city varchar(50), destination_city varchar(50));
CREATE TABLE stg_route (route_id varchar(20) PRIMARY KEY, origin_city varchar(50), destination_city varchar(50));
CREATE TABLE dim_route (route_key integer PRIMARY KEY, route_id varchar(20), origin_city varchar(50), destination_city varchar(50));
CREATE TABLE fact_trip (trip_key integer PRIMARY KEY, route_key integer REFERENCES dim_route(route_key), route_id varchar(20), passenger_count integer CHECK (passenger_count >= 0));
""")
    data = generate_synthetic_data(model, rows_per_table=4, seed=24)
    validation = validate_generated_data(model, data, 4)
    assert validation["status"] in {"passed", "passed_with_warnings"}
    assert validation["lineage_validation"]["checked_raw_to_staging"] == ["load_route_raw -> stg_route"]
    assert validation["lineage_validation"]["checked_staging_to_dimension"] == ["stg_route -> dim_route"]


def test_warehouse_lineage_plan_maps_customer_product_and_generic_names():
    from phase2.warehouse_lineage_planner import build_warehouse_lineage_plan
    model = parse_ddl("""
CREATE TABLE load_customer_raw (customer_id varchar(20) PRIMARY KEY, customer_name varchar(50));
CREATE TABLE stg_customer (customer_id varchar(20) PRIMARY KEY, customer_name varchar(50));
CREATE TABLE dim_customer (customer_key integer PRIMARY KEY, customer_id varchar(20), customer_name varchar(50));
CREATE TABLE load_product_raw (product_id varchar(20) PRIMARY KEY, product_name varchar(50));
CREATE TABLE stg_product (product_id varchar(20) PRIMARY KEY, product_name varchar(50));
CREATE TABLE dim_product (product_key integer PRIMARY KEY, product_id varchar(20), product_name varchar(50));
CREATE TABLE load_route_raw (route_id varchar(20) PRIMARY KEY, origin_city varchar(50));
CREATE TABLE stg_route (route_id varchar(20) PRIMARY KEY, origin_city varchar(50));
CREATE TABLE dim_route (route_key integer PRIMARY KEY, route_id varchar(20), origin_city varchar(50));
""")
    plan = build_warehouse_lineage_plan(model)
    assert set(plan.entities) >= {"customer", "product", "route"}
    assert "load_customer_raw -> stg_customer" in plan.stats()["lineage_raw_to_staging"]
    assert "stg_product -> dim_product" in plan.stats()["lineage_staging_to_dimension"]
    assert "stg_route -> dim_route" in plan.stats()["lineage_staging_to_dimension"]


def test_canonical_records_are_extracted_from_source_layers():
    from phase2.canonical_record_generator import CanonicalRecordGenerator
    model = _lineage_model()
    data = generate_synthetic_data(model, rows_per_table=2, seed=25)
    canonical = CanonicalRecordGenerator(model).from_generated_sources(data)
    assert "item" in canonical
    assert canonical["item"] == data["load_item_raw"]


def test_fact_surrogate_only_lineage_is_validated_with_internal_source_mapping():
    model = parse_ddl("""
CREATE TABLE load_product_raw (product_id varchar(20) PRIMARY KEY, product_name varchar(50));
CREATE TABLE stg_product (product_id varchar(20) PRIMARY KEY, product_name varchar(50));
CREATE TABLE dim_product (product_key integer PRIMARY KEY, product_id varchar(20), product_name varchar(50));
CREATE TABLE stg_order_item (order_item_id varchar(20) PRIMARY KEY, product_id varchar(20), quantity integer, unit_price numeric(8,2));
CREATE TABLE fact_sales (sales_key integer PRIMARY KEY, product_key integer REFERENCES dim_product(product_key), quantity integer, unit_price numeric(8,2), line_total_amount numeric(10,2));
""")
    data = generate_synthetic_data(model, rows_per_table=3, seed=26)
    validation = validate_generated_data(model, data, 3)
    assert validation["status"] in {"passed", "passed_with_warnings"}
    data["fact_sales"][0]["product_key"] = data["dim_product"][1]["product_key"]
    broken = validate_generated_data(model, data, 3)
    assert broken["status"] == "failed"
    assert any("source lineage" in err for err in broken["lineage_validation"]["errors"])
