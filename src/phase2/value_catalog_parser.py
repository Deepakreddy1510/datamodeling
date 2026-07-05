import json

CATALOG_START = "BEGIN_SYNTHETIC_VALUE_CATALOG_JSON"
CATALOG_END = "END_SYNTHETIC_VALUE_CATALOG_JSON"
MISSING_CATALOG_WARNING = "Synthetic value catalog missing. Used generic fallback rules."


def parse_synthetic_value_catalog(phase1_output_text):
    start = phase1_output_text.find(CATALOG_START)
    end = phase1_output_text.find(CATALOG_END)
    if start == -1 or end == -1 or end <= start:
        return {
            "catalog_found": False,
            "catalog": {},
            "warnings": [MISSING_CATALOG_WARNING],
            "errors": [],
            "rule_count": 0,
        }

    json_text = phase1_output_text[start + len(CATALOG_START):end].strip()
    try:
        catalog = json.loads(json_text)
    except json.JSONDecodeError as exc:
        return {
            "catalog_found": False,
            "catalog": {},
            "warnings": [],
            "errors": [f"Synthetic value catalog JSON is invalid: {exc}"],
            "rule_count": 0,
        }
    if not isinstance(catalog, dict):
        return {
            "catalog_found": False,
            "catalog": {},
            "warnings": [],
            "errors": ["Synthetic value catalog JSON root must be an object."],
            "rule_count": 0,
        }
    rules = catalog.get("table_column_rules", [])
    if not isinstance(rules, list):
        return {
            "catalog_found": False,
            "catalog": {},
            "warnings": [],
            "errors": ["Synthetic value catalog table_column_rules must be a list."],
            "rule_count": 0,
        }
    return {
        "catalog_found": True,
        "catalog": catalog,
        "warnings": [],
        "errors": [],
        "rule_count": len(rules),
    }


def build_rule_lookup(value_catalog):
    catalog = (value_catalog or {}).get("catalog", value_catalog or {})
    rules = catalog.get("table_column_rules", []) if isinstance(catalog, dict) else []
    exact = {}
    global_by_column = {}
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        table = str(rule.get("table_name", "")).lower()
        column = str(rule.get("column_name", "")).lower()
        if not column:
            continue
        is_global = table in {"", "*"} or rule.get("applies_to_all_tables") is True or rule.get("scope") == "global"
        if table and table != "*":
            exact[(table, column)] = rule
            if "." in table:
                exact[(table.split(".")[-1], column)] = rule
        if is_global:
            global_by_column.setdefault(column, rule)
    return exact, global_by_column


def get_catalog_rule(value_catalog, table_name, column_name):
    exact, global_by_column = build_rule_lookup(value_catalog)
    table = str(table_name).lower()
    column = str(column_name).lower()
    return exact.get((table, column)) or global_by_column.get(column)
