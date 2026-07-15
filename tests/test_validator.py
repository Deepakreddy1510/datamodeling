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


def test_validator_skips_nullable_fk_values():
    model = parse_ddl("""
CREATE TABLE parent (id integer PRIMARY KEY);
CREATE TABLE child (id integer PRIMARY KEY, parent_id integer REFERENCES parent(id));
""")
    data = {
        "parent": [{"id": 1}],
        "child": [{"id": 1, "parent_id": None}, {"id": 2, "parent_id": ""}],
    }
    result = validate_generated_data(model, data, expected_rows={"parent": 1, "child": 2})
    assert result["status"] == "passed"
    assert not result["errors"]


def test_validator_skips_composite_fk_when_any_component_is_nullable_but_rejects_non_null_value():
    model = parse_ddl("""
CREATE TABLE parent (id_a integer, id_b integer, PRIMARY KEY (id_a, id_b));
CREATE TABLE child (
    id integer PRIMARY KEY,
    parent_a integer,
    parent_b integer,
    FOREIGN KEY (parent_a, parent_b) REFERENCES parent(id_a, id_b)
);
""")
    data = {
        "parent": [{"id_a": 1, "id_b": 2}],
        "child": [
            {"id": 1, "parent_a": 1, "parent_b": None},
            {"id": 2, "parent_a": 999, "parent_b": 999},
        ],
    }
    result = validate_generated_data(model, data, expected_rows={"parent": 1, "child": 2})
    assert result["status"] == "failed"
    assert any("value (999, 999) not found" in error for error in result["errors"])
    assert not any("value (1, None) not found" in error for error in result["errors"])


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
