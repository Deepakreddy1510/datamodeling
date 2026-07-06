import json


def is_catalog_repairable_quality_failure(quality_report):
    checks = quality_report.get("checks", {})
    if quality_report.get("status") != "failed":
        return False
    if checks.get("model_type") not in {"analytical_data_warehouse", "dimensional_model", "star_schema"}:
        return False
    required_layers = checks.get("required_layers", []) or []
    required_checks = [
        checks.get("ddl_present"),
        checks.get("dimension_tables_present"),
        checks.get("fact_tables_present"),
        checks.get("ai_additions_present"),
        checks.get("synthetic_value_catalog_section_present"),
        checks.get("synthetic_value_catalog_json_present"),
        checks.get("catalog_root_valid"),
        checks.get("catalog_table_column_rules_valid"),
        checks.get("catalog_parsed"),
    ]
    if "raw_load" in required_layers:
        required_checks.append(checks.get("load_tables_present"))
    if "staging" in required_layers:
        required_checks.append(checks.get("staging_tables_present"))
    if not all(required_checks):
        return False
    coverage = checks.get("catalog_coverage_percentage", 100)
    missing_rules = checks.get("missing_catalog_rules", [])
    return bool(missing_rules) or coverage < 80


def build_catalog_repair_prompt(original_yaml_text, current_final_output_markdown, quality_report):
    checks = quality_report.get("checks", {})
    missing_rules = checks.get("missing_catalog_rules", [])
    prompt = {
        "task": "Repair only the Synthetic Data Value Catalog in the current final_output_markdown.",
        "catalog_coverage_percentage": checks.get("catalog_coverage_percentage"),
        "required_coverage_percentage": 80,
        "missing_catalog_rules": missing_rules,
        "catalog_global_columns_covered": checks.get("catalog_global_columns_covered", []),
        "catalog_columns_covered": checks.get("catalog_columns_covered", []),
        "technical_columns_using_known_fallback": checks.get("technical_columns_using_known_fallback", []),
        "instructions": [
            "Preserve the existing data model, DDL, relationships, data dictionary, and AI assumptions unless a tiny catalog-alignment correction is absolutely required.",
            "Repair the Synthetic Data Value Catalog so every generated DDL table has exact table.column rules or appropriate global reusable column rules.",
            "Prefer global reusable rules for repeated columns across raw, staging, dimension, and fact layers by using table_name '*', scope 'global', or applies_to_all_tables true.",
            "Use table-specific rules only when the same column name has different business meaning in different tables.",
            "Do not delete existing valid catalog rules; add or refine rules needed to reach at least 80% coverage.",
            "Do not introduce unrelated business values from another business context.",
            "Use the missing_catalog_rules list below as examples generated from validation, not as hard-coded domain logic.",
            "Return strict JSON with status='generated', final_output_markdown containing the full corrected markdown, and ai_additions_and_assumptions.",
        ],
        "original_yaml": original_yaml_text,
        "current_final_output_markdown": current_final_output_markdown,
    }
    return (
        "You are repairing a generated data model output for the AI Data Model Accelerator.\n"
        "Focus on Synthetic Data Value Catalog coverage only.\n\n"
        f"REPAIR_CONTEXT_JSON:\n{json.dumps(prompt, indent=2)}\n\n"
        "Return only strict JSON in this shape:\n"
        "{\n"
        "  \"status\": \"generated\",\n"
        "  \"final_output_markdown\": \"FULL corrected markdown with repaired catalog\",\n"
        "  \"ai_additions_and_assumptions\": []\n"
        "}\n"
    )


def attach_repair_metadata(final_report, *, attempted, attempt_count, original_report, repaired_report=None, final_output_written=False):
    original_checks = original_report.get("checks", {}) if original_report else {}
    repaired_checks = repaired_report.get("checks", {}) if repaired_report else {}
    final_report["repair"] = {
        "catalog_repair_attempted": attempted,
        "repair_attempt_count": attempt_count,
        "original_generation_status": original_report.get("status") if original_report else None,
        "repaired_generation_status": repaired_report.get("status") if repaired_report else None,
        "catalog_repair_status": (repaired_report or {}).get("status") if attempted else "not_attempted",
        "catalog_coverage_before_repair": original_checks.get("catalog_coverage_percentage"),
        "catalog_coverage_after_repair": repaired_checks.get("catalog_coverage_percentage"),
        "missing_rules_before_repair": original_checks.get("missing_catalog_rules", []),
        "missing_rules_after_repair": repaired_checks.get("missing_catalog_rules", []),
        "final_output_written": final_output_written,
    }
    return final_report
