from pathlib import Path


def write_text(path, lines):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _overall_status(*statuses):
    if any(status == "failed" for status in statuses if status):
        return "failed"
    if any(status == "passed_with_warnings" for status in statuses if status):
        return "passed_with_warnings"
    return "passed"


def write_generation_report(path, *, yaml_path, phase1_output, ddl_text, model, rows_per_table, excel_output, validation, value_catalog=None):
    stats = validation.get("generation_stats", {})
    final_status = _overall_status(validation.get("status"), "passed_with_warnings" if getattr(model, "warnings", []) else None)
    lines = [
        "# Synthetic Data Generation Report", "",
        f"- Final status: **{final_status}**",
        f"- YAML input: `{yaml_path}`",
        f"- Phase 1 output: `{phase1_output}`",
        f"- Excel output: `{excel_output}`",
        f"- Excel written in this run: {validation.get('excel_written', False)}",
        f"- Rows per table: {rows_per_table}",
        f"- Phase 1 catalog found: {bool((value_catalog or {}).get('catalog_found'))}",
        f"- Catalog parsed: {bool((value_catalog or {}).get('catalog_found')) and not (value_catalog or {}).get('errors')}",
        f"- Catalog table-column rules: {(value_catalog or {}).get('rule_count', 0)}", "",
        "## DDL Extraction Summary", "",
        f"- Extracted DDL characters: {len(ddl_text)}",
        f"- Tables parsed: {len(model.tables)}", "",
        "## Parsed Tables", "",
        "| Table | Columns | Primary Key | Foreign Keys |",
        "|---|---:|---|---:|",
    ]
    for table in model.tables:
        lines.append(f"| {table.full_name} | {len(table.columns)} | {', '.join(table.primary_key) or 'None'} | {len(table.foreign_keys)} |")

    lines.extend(["", "## Ignored Constraints / Warnings", ""])
    ignored = []
    for table in model.tables:
        ignored.extend([f"{table.full_name}: {constraint}" for constraint in table.ignored_constraints])
    lines.extend([f"- {item}" for item in ignored] or ["- None"])
    if getattr(model, "warnings", []):
        lines.extend(["", "### Parser Warnings", ""])
        lines.extend([f"- {warning}" for warning in model.warnings])

    lines.extend(["", "## Column Length Rules", ""])
    lines.extend([f"- {item}" for item in validation.get("length_checks", [])] or ["- No varchar length limits parsed."])
    lines.append(f"- Generated-short/truncated value count: {stats.get('truncated_values', 0)}")

    lines.extend(["", "## Numeric Precision / Scale Rules", ""])
    lines.extend([f"- {item}" for item in validation.get("numeric_checks", [])] or ["- No numeric precision/scale limits parsed."])
    lines.append(f"- Numeric bounded value count: {stats.get('numeric_bounded_values', 0)}")

    lines.extend(["", "## Foreign Key Relationships", "", "### Parsed", ""])
    lines.extend([f"- {item}" for item in validation.get("parsed_fk_relationships", [])] or ["- None"])
    lines.extend(["", "### Validated", ""])
    lines.extend([f"- {item}" for item in validation.get("checked_fk_relationships", [])] or ["- None"])
    lines.extend(["", "### FK-like Columns Skipped Because No FK Exists in DDL", ""])
    lines.extend([f"- {item}" for item in validation.get("skipped_fk_like_columns", [])] or ["- None"])

    lines.extend(["", "## Catalog Generation Strategy", ""])
    lines.extend([f"- Catalog parser warning: {item}" for item in (value_catalog or {}).get("warnings", [])] or ["- Catalog parser warnings: None"])
    lines.extend([f"- Catalog parser error: {item}" for item in (value_catalog or {}).get("errors", [])] or ["- Catalog parser errors: None"])
    lines.append(f"- Columns generated using catalog: {len(stats.get('catalog_columns_used', []))}")
    lines.append(f"- Columns generated using fallback: {len(stats.get('fallback_columns_used', []))}")
    lines.append(f"- Placeholder warning count: {len(validation.get('placeholder_warnings', []))}")
    lines.append(f"- Unsupported calculation rule warnings: {len(stats.get('calculation_warnings', []))}")
    lines.extend([f"  - unsupported calculation: {item}" for item in stats.get("calculation_warnings", [])])
    lines.extend([f"  - catalog: {item}" for item in stats.get("catalog_columns_used", [])])
    lines.extend([f"  - fallback: {item}" for item in stats.get("fallback_columns_used", [])])

    lines.extend(["", "## Pre-load Validation", "", f"Status: **{validation['status']}**", ""])
    lines.extend([f"- {error}" for error in validation.get("errors", [])] or ["- No validation errors."])
    write_text(path, lines)


def write_postgres_report(path, load_requested, result):
    lines = ["# PostgreSQL Load Report", "", f"- Load requested: {load_requested}", ""]
    if not load_requested:
        lines.append("PostgreSQL load was skipped because `--no-load-to-postgres` was used or `--load-to-postgres` was not passed.")
    else:
        lines.extend([
            f"- Final status: **{result.get('status', 'unknown')}**",
            f"- Target schema: `{result.get('target_schema', '')}`",
            f"- Schema creation status: {result.get('schema_creation_status', 'not_attempted')}",
            f"- Table creation status: {result.get('table_creation_status', 'not_attempted')}",
            f"- Transaction status: {result.get('transaction_status', 'unknown')}",
            "", "## Inserted Rows", "", "| Table | Rows Inserted |", "|---|---:|",
        ])
        for table, count in result.get("inserted_rows", {}).items():
            lines.append(f"| {table} | {count} |")
        if result.get("errors"):
            lines.extend(["", "## Errors", ""])
            lines.extend([f"- {error}" for error in result["errors"]])
    write_text(path, lines)


def write_validation_report(path, pre_validation, post_validation=None):
    final_status = _overall_status(pre_validation.get("status"), post_validation.get("status") if post_validation else None)
    stats = pre_validation.get("generation_stats", {})
    lines = ["# Validation Report", "", f"- Final status: **{final_status}**", f"- Catalog found: {stats.get('catalog_found', False)}", f"- Catalog rule count: {stats.get('catalog_rule_count', 0)}", f"- Catalog rules checked: {pre_validation.get('catalog_rules_checked', 0)}", f"- Catalog columns used: {len(stats.get('catalog_columns_used', []))}", f"- Fallback columns used: {len(stats.get('fallback_columns_used', []))}", f"- Placeholder warning count: {len(pre_validation.get('placeholder_warnings', []))}", "", "## Pre-load Validation", "", f"Status: **{pre_validation['status']}**", ""]
    lines.extend([f"- {error}" for error in pre_validation.get("errors", [])] or ["- No validation errors."])
    lines.extend(["", "## FK Validation Coverage", "", "### Parsed FK Relationships", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("parsed_fk_relationships", [])] or ["- None"])
    lines.extend(["", "### Checked FK Relationships", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("checked_fk_relationships", [])] or ["- None"])
    lines.extend(["", "### FK-like Columns Skipped Because No Parsed FK Exists", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("skipped_fk_like_columns", [])] or ["- None"])
    lines.extend(["", "## Catalog Parser Warnings", ""])
    lines.extend([f"- {item}" for item in stats.get("catalog_warnings", [])] or ["- None"])
    lines.extend(["", "## Catalog Parser Errors", ""])
    lines.extend([f"- {item}" for item in stats.get("catalog_errors", [])] or ["- None"])
    lines.extend(["", "## Catalog Compliance", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("catalog_compliance_errors", [])] or ["- No catalog compliance errors."])
    lines.extend(["", "## Data Type Validation", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("data_type_errors", [])] or ["- No data type errors."])
    lines.extend(["", "## Constraint Validation", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("constraint_errors", [])] or ["- No constraint errors."])
    lines.extend(["", "## Calculation Validation", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("calculation_errors", [])] or ["- No calculation errors."])
    lines.extend(["", "## Date Rule Validation", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("date_rule_errors", [])] or ["- No date rule errors."])
    lines.extend(["", "## Boolean Rule Validation", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("boolean_rule_errors", [])] or ["- No boolean rule errors."])
    lines.extend(["", "## Placeholder Validation", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("placeholder_warnings", [])] or ["- No placeholder warnings."])
    lines.extend(["", "## Row Count Summary", "", "| Table | Rows |", "|---|---:|"])
    row_counts = pre_validation.get("row_count_summary", {})
    if row_counts:
        for table, count in row_counts.items():
            lines.append(f"| {table} | {count} |")
    else:
        lines.append("| None | 0 |")
    lines.extend(["", "## Unsupported Calculation Rules", ""])
    lines.extend([f"- {item}" for item in stats.get("calculation_warnings", [])] or ["- None"])
    lines.extend(["", "## PostgreSQL Validation", ""])
    if post_validation is None:
        lines.append("PostgreSQL validation was skipped because no database load was requested.")
    else:
        lines.extend([f"Status: **{post_validation.get('status', 'unknown')}**", ""])
        lines.extend([f"- {error}" for error in post_validation.get("errors", [])] or ["- No validation errors."])
        if post_validation.get("row_counts"):
            lines.extend(["", "### Row Counts", "", "| Table | Expected | Actual |", "|---|---:|---:|"])
            for table, counts in post_validation["row_counts"].items():
                lines.append(f"| {table} | {counts['expected']} | {counts['actual']} |")
    write_text(path, lines)
