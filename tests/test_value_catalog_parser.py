from phase2.value_catalog_parser import parse_synthetic_value_catalog


def test_extracts_catalog_json_between_markers():
    text = '''
# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{"table_column_rules": [{"table_name": "dim_customer", "column_name": "segment", "allowed_values": ["New"]}]}
END_SYNTHETIC_VALUE_CATALOG_JSON
'''
    result = parse_synthetic_value_catalog(text)
    assert result["catalog_found"] is True
    assert result["rule_count"] == 1
    assert result["catalog"]["table_column_rules"][0]["allowed_values"] == ["New"]


def test_missing_catalog_is_warning_not_error():
    result = parse_synthetic_value_catalog("# SQL DDL")
    assert result["catalog_found"] is False
    assert result["warnings"]
    assert not result["errors"]


def test_invalid_catalog_returns_error():
    result = parse_synthetic_value_catalog("BEGIN_SYNTHETIC_VALUE_CATALOG_JSON\n{bad\nEND_SYNTHETIC_VALUE_CATALOG_JSON")
    assert result["catalog_found"] is False
    assert result["errors"]
