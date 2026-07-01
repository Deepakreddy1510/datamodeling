from pathlib import Path


def write_text(path, lines):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_generation_report(path, *, yaml_path, phase1_output, ddl_text, model, rows_per_table, excel_output, validation):
    lines = [
        "# Synthetic Data Generation Report", "",
        f"- YAML input: `{yaml_path}`",
        f"- Phase 1 output: `{phase1_output}`",
        f"- Excel output: `{excel_output}`",
        f"- Rows per table: {rows_per_table}", "",
        "## DDL Extraction", "",
        f"- Extracted DDL characters: {len(ddl_text)}", "",
        "## Parsed Tables", "",
        "| Table | Columns | Primary Key | Foreign Keys |",
        "|---|---:|---|---:|",
    ]
    for table in model.tables:
        lines.append(f"| {table.full_name} | {len(table.columns)} | {', '.join(table.primary_key) or 'None'} | {len(table.foreign_keys)} |")
    lines.extend(["", "## Pre-load Validation", "", f"Status: **{validation['status']}**", ""])
    lines.extend([f"- {error}" for error in validation.get("errors", [])] or ["- No validation errors."])
    write_text(path, lines)


def write_postgres_report(path, load_requested, result):
    lines = ["# PostgreSQL Load Report", "", f"- Load requested: {load_requested}", ""]
    if not load_requested:
        lines.append("PostgreSQL load was skipped because `--no-load-to-postgres` was used or `--load-to-postgres` was not passed.")
    else:
        lines.extend([
            f"- Status: **{result.get('status', 'unknown')}**",
            f"- Target schema: `{result.get('target_schema', '')}`",
            "", "## Inserted Rows", "", "| Table | Rows Inserted |", "|---|---:|",
        ])
        for table, count in result.get("inserted_rows", {}).items():
            lines.append(f"| {table} | {count} |")
        if result.get("errors"):
            lines.extend(["", "## Errors", ""])
            lines.extend([f"- {error}" for error in result["errors"]])
    write_text(path, lines)


def write_validation_report(path, pre_validation, post_validation=None):
    lines = ["# Validation Report", "", "## Pre-load Validation", "", f"Status: **{pre_validation['status']}**", ""]
    lines.extend([f"- {error}" for error in pre_validation.get("errors", [])] or ["- No validation errors."])
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
