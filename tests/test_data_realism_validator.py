from phase2.data_realism_validator import validate_data_realism
from phase2.ddl_parser import parse_ddl


def test_realism_validator_reports_reused_parent_keys():
    model = parse_ddl("""
CREATE TABLE parent_entity (entity_id integer PRIMARY KEY);
CREATE TABLE event_row (
  event_id integer PRIMARY KEY,
  entity_id integer REFERENCES parent_entity(entity_id),
  event_date date
);
""")
    data = {
        "parent_entity": [{"entity_id": 1}, {"entity_id": 2}],
        "event_row": [
            {"event_id": 1, "entity_id": 1, "event_date": __import__('datetime').date(2026, 1, 1)},
            {"event_id": 2, "entity_id": 1, "event_date": __import__('datetime').date(2026, 2, 15)},
            {"event_id": 3, "entity_id": 2, "event_date": __import__('datetime').date(2026, 3, 20)},
        ],
    }
    result = validate_data_realism(model, data, {"date_span_days": 30})
    assert result["status"] == "passed"
    assert any("reused parents" in check for check in result["checks"])


def test_realism_validator_ignores_nullable_foreign_keys():
    model = parse_ddl("""
CREATE TABLE dim_date (date_key integer PRIMARY KEY);
CREATE TABLE fact_event (
  event_key integer PRIMARY KEY,
  actual_date_key integer NULL REFERENCES dim_date(date_key)
);
""")
    data = {
        "dim_date": [{"date_key": 20260101}],
        "fact_event": [
            {"event_key": 1, "actual_date_key": 20260101},
            {"event_key": 2, "actual_date_key": None},
        ],
    }
    result = validate_data_realism(model, data, {})
    assert result["status"] == "passed"
    assert not result["errors"]
    assert any("nullable FK row(s) skipped" in check for check in result["checks"])
