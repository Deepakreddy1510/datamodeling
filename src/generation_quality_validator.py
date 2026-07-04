import re

AI_ADDITIONS_HEADING = "# AI Additions / Assumptions"
ANALYTICAL_TYPES = {"analytical_data_warehouse", "dimensional_model", "star_schema"}


def _combined_generation_text(generation_response):
    pieces = [generation_response.get("final_output_markdown", "")]
    for key in ["ddl", "tables", "dimensions", "facts"]:
        value = generation_response.get(key)
        if value is not None:
            pieces.append(str(value))
    return "\n".join(pieces)


def _has_prefix_table(text, prefix):
    return bool(re.search(rf"\b{re.escape(prefix)}[a-zA-Z0-9_]+\b", text, re.IGNORECASE))


def _reasonable_fact_present(text, fact_name):
    if fact_name.lower() in text.lower():
        return True
    suffix = fact_name.lower().replace("fact_", "")
    return bool(re.search(rf"\bfact_[a-zA-Z0-9_]*{re.escape(suffix)}[a-zA-Z0-9_]*\b", text, re.IGNORECASE))


def validate_generation_quality(generation_response, model_intent, model_blueprint):
    text = _combined_generation_text(generation_response)
    markdown = generation_response.get("final_output_markdown", "")
    model_type = model_intent.get("model_type", "operational_model")
    required_layers = model_intent.get("required_layers", [])
    expected_output = text.lower()
    errors = []
    warnings = []
    checks = {
        "dimension_tables_present": _has_prefix_table(text, "dim_"),
        "fact_tables_present": _has_prefix_table(text, "fact_"),
        "load_tables_present": _has_prefix_table(text, "load_"),
        "staging_tables_present": _has_prefix_table(text, "stg_"),
        "ddl_present": bool(re.search(r"\bCREATE\s+TABLE\b", text, re.IGNORECASE)),
        "ai_additions_present": AI_ADDITIONS_HEADING.lower() in markdown.lower(),
    }

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
        missing_facts = [
            fact for fact in model_blueprint.get("inferred_fact_tables", [])
            if not _reasonable_fact_present(expected_output, fact)
        ]
        if missing_facts:
            warnings.append(f"Inferred fact table(s) not found by name or close equivalent: {', '.join(missing_facts)}")
    else:
        if not markdown.strip():
            errors.append("Generated final_output_markdown is empty.")
        requested = str(model_blueprint).lower()
        if "sql ddl" in requested and not checks["ddl_present"]:
            errors.append("SQL DDL was requested but generated output does not contain CREATE TABLE DDL.")

    return {"status": "failed" if errors else "passed", "errors": errors, "warnings": warnings, "checks": checks}
