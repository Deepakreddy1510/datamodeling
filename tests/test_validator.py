from phase2.ddl_parser import parse_ddl
from phase2.synthetic_data_generator import generate_synthetic_data
from phase2.validator import validate_generated_data


def test_validator_fails_over_length_strings_before_load():
    model = parse_ddl("CREATE TABLE t (id integer PRIMARY KEY, short_value varchar(5));")
    data = {"t": [{"id": 1, "short_value": "too_long"}]}
    result = validate_generated_data(model, data, expected_rows=1)
    assert result["status"] == "failed"
    assert "exceeds max length" in result["errors"][0]


def test_validator_reports_fk_inconsistency():
    model = parse_ddl("""
CREATE TABLE parent (parent_id integer PRIMARY KEY);
CREATE TABLE child (child_id integer PRIMARY KEY, parent_id integer REFERENCES parent(parent_id));
""")
    data = {"parent": [{"parent_id": 1}], "child": [{"child_id": 1, "parent_id": 999}]}
    result = validate_generated_data(model, data, expected_rows=1)
    assert result["status"] == "failed"
    assert "foreign key" in result["errors"][0]


def test_validator_row_count_validation_works():
    model = parse_ddl("CREATE TABLE t (id integer PRIMARY KEY);")
    data = generate_synthetic_data(model, rows_per_table=2, seed=1)
    result = validate_generated_data(model, data, expected_rows=100)
    assert result["status"] == "failed"
    assert "expected 100 rows" in result["errors"][0]


def test_validator_fails_numeric_precision_overflow_before_load():
    model = parse_ddl("CREATE TABLE t (id integer PRIMARY KEY, amount numeric(5,2));")
    data = {"t": [{"id": 1, "amount": "1000.00"}]}
    result = validate_generated_data(model, data, expected_rows=1)
    assert result["status"] == "failed"
    assert "numeric(5,2)" in result["errors"][0]


def test_validator_fails_numeric_scale_overflow_before_load():
    model = parse_ddl("CREATE TABLE t (id integer PRIMARY KEY, amount numeric(5,2));")
    data = {"t": [{"id": 1, "amount": "1.234"}]}
    result = validate_generated_data(model, data, expected_rows=1)
    assert result["status"] == "failed"
    assert "numeric(5,2)" in result["errors"][0]


def test_validator_fails_missing_catalog_for_analytical_tables():
    model = parse_ddl("CREATE TABLE dim_customer (customer_key integer PRIMARY KEY, customer_name varchar(50));")
    data = {"dim_customer": [{"customer_key": 1, "customer_name": "Alex Smith"}]}
    result = validate_generated_data(model, data, expected_rows=1, value_catalog={"catalog_found": False, "markers_present": False, "warnings": [], "errors": [], "rule_count": 0, "catalog": {}})
    assert result["status"] == "failed"
    assert any("Analytical DDL" in error for error in result["errors"])


def test_validator_fails_unique_constraint_violation():
    model = parse_ddl("CREATE TABLE t (id integer PRIMARY KEY, code varchar(20) UNIQUE);")
    data = {"t": [{"id": 1, "code": "A"}, {"id": 2, "code": "A"}]}
    result = validate_generated_data(model, data, expected_rows=2)
    assert result["status"] == "failed"
    assert result["constraint_errors"]


def test_validator_fails_check_in_and_numeric_check_violations():
    model = parse_ddl("""
CREATE TABLE t (
  id integer PRIMARY KEY,
  status varchar(20),
  amount numeric(5,2),
  CHECK (status IN ('Active','Inactive')),
  CHECK (amount >= 0)
);
""")
    data = {"t": [{"id": 1, "status": "Deleted", "amount": "-1.00"}]}
    result = validate_generated_data(model, data, expected_rows=1)
    assert result["status"] == "failed"
    assert len(result["constraint_errors"]) == 2
