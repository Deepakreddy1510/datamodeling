import json
import re

AI_ADDITIONS_HEADING = "# AI Additions / Assumptions"
CATALOG_START = "BEGIN_SYNTHETIC_VALUE_CATALOG_JSON"
CATALOG_END = "END_SYNTHETIC_VALUE_CATALOG_JSON"
ANALYTICAL_TYPES = {"analytical_data_warehouse", "dimensional_model", "star_schema"}
IMPORTANT_COLUMN_TOKENS = (
    "name", "status", "segment", "category", "type", "method", "city", "country",
    "amount", "price", "cost", "quantity", "count", "percentage", "rate", "score",
    "date", "time", "flag", "boolean", "key", "_id",
)


def _combined_generation_text(generation_response):
    pieces = [generation_response.get("final_output_markdown", "")]
    for key in ["ddl", "tables", "dimensions", "facts"]:
        value = generation_response.get(key)
        if value is not None:
            pieces.append(str(value))
    return "\n".join(pieces)


def _has_prefix_table(text, prefix):
    ddl_pattern = rf"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[a-zA-Z0-9_\"]+\.)?[\"]?{re.escape(prefix)}[a-zA-Z0-9_]+[\"]?"
    return bool(re.search(ddl_pattern, text, re.IGNORECASE))


def _reasonable_fact_present(text, fact_name):
    if fact_name.lower() in text.lower():
        return True
    suffix = fact_name.lower().replace("fact_", "")
    return bool(re.search(rf"\bfact_[a-zA-Z0-9_]*{re.escape(suffix)}[a-zA-Z0-9_]*\b", text, re.IGNORECASE))


def _split_top_level_commas(text):
    parts, current, depth, in_quote = [], [], 0, False
    for char in text:
        if char == '"':
            in_quote = not in_quote
        elif not in_quote:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append("".join(current).strip())
                current = []
                continue
        current.append(char)
    if current:
        parts.append("".join(current).strip())
    return [part for part in parts if part]


def _ddl_tables_and_columns(text):
    tables = {}
    pattern = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w\".]+)\s*\((.*?)\)\s*;", re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(text):
        table_name = match.group(1).strip('"').split(".")[-1].lower()
        columns = []
        for part in _split_top_level_commas(match.group(2)):
            if re.match(r"^CONSTRAINT\b|^(PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|CHECK)\b", part.strip(), re.IGNORECASE):
                continue
            col_match = re.match(r"([\w\"]+)\s+", part.strip())
            if col_match:
                columns.append(col_match.group(1).strip('"').lower())
        tables[table_name] = columns
    return tables


def _parse_catalog(markdown):
    start = markdown.find(CATALOG_START)
    end = markdown.find(CATALOG_END)
    result = {
        "catalog_markers_present": start != -1 and end != -1 and end > start,
        "catalog_parsed": False,
        "catalog_rule_count": 0,
        "catalog_tables_covered": [],
        "catalog_columns_covered": [],
        "missing_catalog_rules": [],
        "catalog_coverage_percentage": 0,
        "catalog_parse_error": "",
        "catalog_root_valid": False,
        "catalog_table_column_rules_valid": False,
    }
    if not result["catalog_markers_present"]:
        return result, None
    try:
        catalog = json.loads(markdown[start + len(CATALOG_START):end].strip())
    except json.JSONDecodeError as exc:
        result["catalog_parse_error"] = f"Synthetic Data Value Catalog JSON is invalid: {exc}"
        return result, None
    if not isinstance(catalog, dict):
        result["catalog_parse_error"] = "Synthetic Data Value Catalog root must be a JSON object."
        return result, None
    result["catalog_root_valid"] = True
    rules = catalog.get("table_column_rules")
    if not isinstance(rules, list):
        result["catalog_parse_error"] = "Synthetic Data Value Catalog table_column_rules must be a list."
        return result, catalog
    result["catalog_table_column_rules_valid"] = True
    valid_rules = [rule for rule in rules if isinstance(rule, dict) and rule.get("column_name")]
    result["catalog_parsed"] = True
    result["catalog_rule_count"] = len(valid_rules)
    table_cols = set()
    tables = set()
    for rule in valid_rules:
        table = str(rule.get("table_name") or "").strip().strip('"').split(".")[-1].lower()
        column = str(rule.get("column_name") or "").strip().strip('"').lower()
        if table and table != "*":
            tables.add(table)
            table_cols.add((table, column))
    result["catalog_tables_covered"] = sorted(tables)
    result["catalog_columns_covered"] = [f"{table}.{column}" for table, column in sorted(table_cols)]
    return result, catalog


def _catalog_coverage(markdown, catalog_checks):
    ddl_tables = _ddl_tables_and_columns(markdown)
    if not ddl_tables:
        return
    covered = set()
    covered_tables = set(catalog_checks.get("catalog_tables_covered", []))
    for item in catalog_checks.get("catalog_columns_covered", []):
        table, _, column = item.partition(".")
        covered.add((table, column))
    missing = []
    total_important = 0
    covered_important = 0
    for table, columns in ddl_tables.items():
        if table not in covered_tables:
            missing.append(f"{table}: no catalog rule covers this generated table.")
        for column in columns:
            important = column.endswith("_id") or any(token in column for token in IMPORTANT_COLUMN_TOKENS)
            if not important:
                continue
            total_important += 1
            if (table, column) in covered:
                covered_important += 1
            else:
                missing.append(f"{table}.{column}: important column has no catalog rule.")
    catalog_checks["missing_catalog_rules"] = missing
    catalog_checks["catalog_coverage_percentage"] = round((covered_important / total_important) * 100, 2) if total_important else 100


def validate_generation_quality(generation_response, model_intent, model_blueprint):
    text = _combined_generation_text(generation_response)
    markdown = generation_response.get("final_output_markdown", "")
    model_type = model_intent.get("model_type", "operational_model")
    required_layers = model_intent.get("required_layers", [])
    expected_output = text.lower()
    errors = []
    warnings = []
    checks = {
        "model_type": model_type,
        "required_layers": required_layers,
        "dimension_tables_present": _has_prefix_table(text, "dim_"),
        "fact_tables_present": _has_prefix_table(text, "fact_"),
        "load_tables_present": _has_prefix_table(text, "load_"),
        "staging_tables_present": _has_prefix_table(text, "stg_"),
        "ddl_present": bool(re.search(r"\bCREATE\s+TABLE\b", text, re.IGNORECASE)),
        "ai_additions_present": AI_ADDITIONS_HEADING.lower() in markdown.lower(),
        "synthetic_value_catalog_section_present": "# synthetic data value catalog" in markdown.lower(),
        "synthetic_value_catalog_json_present": CATALOG_START in markdown and CATALOG_END in markdown,
    }
    catalog_checks, _ = _parse_catalog(markdown)
    _catalog_coverage(markdown, catalog_checks)
    checks.update(catalog_checks)

    if model_type in ANALYTICAL_TYPES:
        if not checks["dimension_tables_present"]:
            errors.append("Analytical warehouse requested but no dim_ tables found.")
        if not checks["fact_tables_present"]:
            errors.append("Analytical warehouse requested but no fact_ tables found.")
        if "raw_load" in required_layers and not checks["load_tables_present"]:
            errors.append("Raw load layer requested but no load_ tables found.")
        if "staging" in required_layers and not checks["staging_tables_present"]:
            errors.append("Staging layer requested but no stg_ tables found.")
        if not checks["ddl_present"]:
            errors.append("Generated output does not contain CREATE TABLE DDL.")
        if not checks["ai_additions_present"]:
            errors.append("Generated output is missing AI Additions / Assumptions.")
        if not checks["synthetic_value_catalog_section_present"] or not checks["synthetic_value_catalog_json_present"]:
            errors.append("Synthetic Data Value Catalog is required for analytical outputs but was not found.")
        elif not checks["catalog_parsed"]:
            errors.append(checks.get("catalog_parse_error") or "Synthetic Data Value Catalog could not be parsed.")
        elif checks["catalog_rule_count"] == 0:
            errors.append("Synthetic Data Value Catalog table_column_rules must contain at least one valid rule for analytical outputs.")
        missing_facts = [
            fact for fact in model_blueprint.get("inferred_fact_tables", [])
            if not _reasonable_fact_present(expected_output, fact)
        ]
        if missing_facts:
            warnings.append(f"Inferred fact table(s) not found by name or close equivalent: {', '.join(missing_facts)}")
        if checks.get("missing_catalog_rules"):
            errors.append("Synthetic Data Value Catalog is missing rules for generated tables or critical semantic columns.")
            warnings.extend(checks["missing_catalog_rules"][:25])
        if checks.get("catalog_coverage_percentage", 0) < 80:
            errors.append("Synthetic Data Value Catalog coverage is below the required 80% threshold for analytical output.")
    else:
        if not markdown.strip():
            errors.append("Generated final_output_markdown is empty.")
        requested = str(model_blueprint).lower()
        if "sql ddl" in requested and not checks["ddl_present"]:
            errors.append("SQL DDL was requested but generated output does not contain CREATE TABLE DDL.")

    return {"status": "failed" if errors else ("passed_with_warnings" if warnings else "passed"), "errors": errors, "warnings": warnings, "checks": checks}
