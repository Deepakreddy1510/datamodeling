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
