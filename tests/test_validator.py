from phase2.ddl_parser import parse_ddl
from phase2.validator import validate_generated_data


def test_validator_detects_fk_violation():
    model = parse_ddl("""
CREATE TABLE parent (id integer PRIMARY KEY);
CREATE TABLE child (id integer PRIMARY KEY, parent_id integer REFERENCES parent(id));
""")
    data = {"parent": [{"id": 1}], "child": [{"id": 1, "parent_id": 999}]}
    result = validate_generated_data(model, data, expected_rows=1)
    assert result["status"] == "failed"
    assert any("foreign key" in error for error in result["errors"])


def test_validator_detects_unique_violation():
    model = parse_ddl("CREATE TABLE item (id integer PRIMARY KEY, code varchar(10) UNIQUE);")
    data = {"item": [{"id": 1, "code": "A"}, {"id": 2, "code": "A"}]}
    result = validate_generated_data(model, data, expected_rows=2)
    assert result["status"] == "failed"
    assert result["constraint_errors"]


def test_validator_detects_check_violation():
    model = parse_ddl("CREATE TABLE item (id integer PRIMARY KEY, status varchar(10) CHECK (status IN ('A','B')));")
    data = {"item": [{"id": 1, "status": "C"}]}
    result = validate_generated_data(model, data, expected_rows=1)
    assert result["status"] == "failed"
    assert result["constraint_errors"]


def test_validator_passes_analytical_ddl_without_synthetic_value_json():
    model = parse_ddl("CREATE TABLE dim_customer (customer_key integer PRIMARY KEY, customer_name varchar(50) NOT NULL);")
    data = {"dim_customer": [{"customer_key": 1, "customer_name": "Alex Smith"}]}
    result = validate_generated_data(model, data, expected_rows=1)
    assert result["status"] == "passed"


def test_nullable_fk_values_are_skipped_but_invalid_non_null_fk_fails():
    from phase2.ddl_parser import parse_ddl
    from phase2.validator import validate_generated_data
    model = parse_ddl("""
CREATE TABLE parent_entity (parent_id integer PRIMARY KEY);
CREATE TABLE child_entity (child_id integer PRIMARY KEY, parent_id integer REFERENCES parent_entity(parent_id));
""")
    data = {"parent_entity": [{"parent_id": 1}], "child_entity": [{"child_id": 1, "parent_id": None}]}
    assert validate_generated_data(model, data, 1)["status"] == "passed"
    data["child_entity"][0]["parent_id"] = 999
    validation = validate_generated_data(model, data, 1)
    assert validation["status"] == "failed"
    assert any("foreign key" in error for error in validation["errors"])
