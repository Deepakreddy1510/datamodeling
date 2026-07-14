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


def write_generation_report(path, *, yaml_path, phase1_output, ddl_text, model, rows_per_table, excel_output, validation, pipeline_plan=None, codex_assumptions=None, codex_sql_artifact=None, elt_execution=None, lineage_validation=None):
    stats = validation.get("generation_stats", {})
    final_status = _overall_status(validation.get("status"), "passed_with_warnings" if getattr(model, "warnings", []) else None)
    lines = [
        "# Synthetic Data Generation Report", "",
        f"- Final status: **{final_status}**",
        f"- YAML input: `{yaml_path}`",
        f"- Phase 1 output: `{phase1_output}`",
        f"- Excel output: `{excel_output}`",
        f"- Excel written in this run: {validation.get('excel_written', False)}",
        f"- Rows per table: {rows_per_table}", "",
        "## DDL Extraction Summary", "",
        f"- Extracted DDL characters: {len(ddl_text)}",
        f"- Tables parsed: {len(model.tables)}", "",
        "## Parsed Tables", "",
        "| Table | Columns | Primary Key | Foreign Keys |",
        "|---|---:|---|---:|",
    ]
    for table in model.tables:
        lines.append(f"| {table.full_name} | {len(table.columns)} | {', '.join(table.primary_key) or 'None'} | {len(table.foreign_keys)} |")

    if pipeline_plan:
        lines.extend(["", "## Warehouse Pipeline Classification", ""])
        lines.append(f"- Raw/load tables: {', '.join(pipeline_plan.get('raw_tables', [])) or 'None'}")
        lines.append(f"- Staging tables: {', '.join(pipeline_plan.get('staging_tables', [])) or 'None'}")
        lines.append(f"- Dimension tables: {', '.join(pipeline_plan.get('dimension_tables', [])) or 'None'}")
        lines.append(f"- Fact tables: {', '.join(pipeline_plan.get('fact_tables', [])) or 'None'}")
        lines.append(f"- Other tables: {', '.join(pipeline_plan.get('other_tables', [])) or 'None'}")
        lines.extend(["", "## Warehouse Lineage Plan", ""])
        for target, sources in pipeline_plan.get('lineage', {}).items():
            lines.append(f"- {target}: {', '.join(sources) or 'None'}")
        if pipeline_plan.get('warnings'):
            lines.extend(["", "### Pipeline Plan Warnings", ""])
            lines.extend([f"- {warning}" for warning in pipeline_plan.get('warnings', [])])
    if codex_assumptions is not None:
        lines.extend(["", "## Codex ELT Assumptions", ""])
        lines.extend([f"- {item}" for item in codex_assumptions] or ["- None"])
    if codex_sql_artifact:
        lines.extend(["", "## Codex SQL Artifact", "", f"- `{codex_sql_artifact}`"])
    if elt_execution:
        lines.extend(["", "## ELT Execution Summary", ""])
        lines.append(f"- SQL execution status: {elt_execution.get('status', 'unknown')}")
        lines.append(f"- Transaction status: {elt_execution.get('transaction_status', 'unknown')}")
        lines.extend(["", "### Raw/Load Inserted Rows", "", "| Table | Rows |", "|---|---:|"])
        for table, count in elt_execution.get('inserted_rows', {}).items():
            lines.append(f"| {table} | {count} |")
        lines.extend(["", "### Final Row Counts by Table", "", "| Table | Rows |", "|---|---:|"])
        for table, count in elt_execution.get('transformed_rows', {}).items():
            lines.append(f"| {table} | {count} |")
    if lineage_validation:
        lines.extend(["", "## Lineage Validation Summary", "", f"- Status: **{lineage_validation.get('status', 'unknown')}**"])
        lines.extend([f"- {error}" for error in lineage_validation.get('errors', [])] or ["- No lineage errors."])

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
    lines.extend(["", "## CHECK IN Value Source Summary", ""])
    lines.extend([f"- {item}" for item in stats.get("check_in_value_sources", [])] or ["- No CHECK IN constrained columns generated in this run."])

    lines.extend(["", "## Foreign Key Relationships", "", "### Parsed", ""])
    lines.extend([f"- {item}" for item in validation.get("parsed_fk_relationships", [])] or ["- None"])
    lines.extend(["", "### Validated", ""])
    lines.extend([f"- {item}" for item in validation.get("checked_fk_relationships", [])] or ["- None"])
    lines.extend(["", "### FK-like Columns Skipped Because No FK Exists in DDL", ""])
    lines.extend([f"- {item}" for item in validation.get("skipped_fk_like_columns", [])] or ["- None"])

    lines.extend(["", "## Semantic Inference Summary", ""])
    lines.append(f"- Context terms: {', '.join(stats.get('semantic_context_terms', [])) or 'None'}")
    lines.append("- Generated semantic types:")
    for semantic_type, count in sorted(stats.get('semantic_types', {}).items()):
        lines.append(f"  - {semantic_type}: {count}")
    lines.extend(["", "## Reference Data Matching Summary", ""])
    lines.extend([f"- {item}" for item in stats.get("reference_data_matches", [])] or ["- No YAML reference_data matches were applied."])
    lines.extend(["", "## Entity Reuse Summary", ""])
    lines.extend([f"- {item}" for item in stats.get("entity_reuse_events", [])] or ["- No cross-layer entity reuse events were needed."])
    lines.extend(["", "## Relationship Generation Summary", ""])
    lines.extend([f"- {item}" for item in stats.get("relationship_generation_events", [])] or ["- No parsed FK relationships were used."])

    lines.extend(["", "## DDL-Only Generation Strategy", ""])
    lines.append(f"- Columns generated using DDL/name inference: {len(stats.get('fallback_columns_used', []))}")
    lines.append(f"- Columns generated from CHECK IN allowed values: {len(stats.get('check_in_value_sources', []))}")
    lines.append(f"- Fallback-to-DDL inference count: {stats.get('fallback_to_ddl_inference_count', 0)}")
    lines.append(f"- DDL type corrections: {len(stats.get('ddl_type_corrections', []))}")
    lines.append(f"- VARCHAR length corrections: {len(stats.get('varchar_length_corrections', []))}")
    lines.append(f"- Incompatible reuse corrections: {len(stats.get('incompatible_reuse_corrections', []))}")
    lines.append(f"- Calculation corrections: {len(stats.get('calculation_corrections', []))}")
    lines.append(f"- FK-safe unique adjustments: {len(stats.get('fk_safe_unique_adjustments', []))}")
    lines.append(f"- Composite unique adjustments: {len(stats.get('composite_unique_adjustments', []))}")
    lines.append(f"- Placeholder warning count: {len(validation.get('placeholder_warnings', []))}")
    lines.append(f"- Semantic placeholder validation status: {'failed' if validation.get('semantic_placeholder_errors') else 'passed'}")
    lines.append(f"- Semantic placeholder checked values: {validation.get('semantic_placeholder_checked_values', 0)}")
    lines.append(f"- Calculation warning count: {len(stats.get('calculation_warnings', []))}")
    lines.extend([f"  - calculation warning: {item}" for item in stats.get("calculation_warnings", [])])
    lines.extend([f"  - DDL type correction: {item}" for item in stats.get("ddl_type_corrections", [])])
    lines.extend([f"  - VARCHAR length correction: {item}" for item in stats.get("varchar_length_corrections", [])])
    lines.extend([f"  - incompatible reuse correction: {item}" for item in stats.get("incompatible_reuse_corrections", [])])
    lines.extend([f"  - calculation correction: {item}" for item in stats.get("calculation_corrections", [])])
    lines.extend([f"  - fk-safe unique adjustment: {item}" for item in stats.get("fk_safe_unique_adjustments", [])])
    lines.extend([f"  - composite unique adjustment: {item}" for item in stats.get("composite_unique_adjustments", [])])
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


def write_validation_report(path, pre_validation, post_validation=None, lineage_validation=None):
    final_status = _overall_status(pre_validation.get("status"), post_validation.get("status") if post_validation else None)
    stats = pre_validation.get("generation_stats", {})
    lines = ["# Validation Report", "", f"- Final status: **{final_status}**", f"- DDL validation status: **{'failed' if pre_validation.get('errors') else 'passed'}**", f"- Fallback inference count: {stats.get('fallback_to_ddl_inference_count', 0)}", f"- Semantic type count: {len(stats.get('semantic_types', {}))}", f"- Placeholder warning count: {len(pre_validation.get('placeholder_warnings', []))}", f"- Semantic placeholder validation status: **{'failed' if pre_validation.get('semantic_placeholder_errors') else 'passed'}**", "", "## Pre-load Validation", "", f"Status: **{pre_validation['status']}**", ""]
    lines.extend([f"- {error}" for error in pre_validation.get("errors", [])] or ["- No validation errors."])
    lines.extend(["", "## FK Validation Coverage", "", "### Parsed FK Relationships", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("parsed_fk_relationships", [])] or ["- None"])
    lines.extend(["", "### Checked FK Relationships", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("checked_fk_relationships", [])] or ["- None"])
    lines.extend(["", "### FK-like Columns Skipped Because No Parsed FK Exists", ""])
    lines.extend([f"- {item}" for item in pre_validation.get("skipped_fk_like_columns", [])] or ["- None"])
    lines.extend(["", "## Unique Constraint Adjustments", ""])
    lines.extend([f"- FK-safe: {item}" for item in stats.get("fk_safe_unique_adjustments", [])] or ["- FK-safe: None"])
    lines.extend([f"- Composite: {item}" for item in stats.get("composite_unique_adjustments", [])] or ["- Composite: None"])
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
    lines.extend(["", "## Semantic Placeholder Validation", ""])
    lines.append(f"- Checked values: {pre_validation.get('semantic_placeholder_checked_values', 0)}")
    lines.extend([f"- {item}" for item in pre_validation.get("semantic_placeholder_errors", [])] or ["- No semantic placeholder errors."])
    lines.extend(["", "## Row Count Summary", "", "| Table | Rows |", "|---|---:|"])
    row_counts = pre_validation.get("row_count_summary", {})
    if row_counts:
        for table, count in row_counts.items():
            lines.append(f"| {table} | {count} |")
    else:
        lines.append("| None | 0 |")
    lines.extend(["", "## Unsupported Calculation Rules", ""])
    lines.extend([f"- {item}" for item in stats.get("calculation_warnings", [])] or ["- None"])
    lines.extend(["", "## Lineage Validation", ""])
    if lineage_validation is None:
        lineage_validation = pre_validation.get("lineage_validation")
    if lineage_validation is None:
        lines.append("Lineage validation was skipped.")
    else:
        lines.append(f"Status: **{lineage_validation.get('status', 'unknown')}**")
        lines.extend([f"- {item}" for item in lineage_validation.get("errors", [])] or ["- No lineage errors."])
        if lineage_validation.get("warnings"):
            lines.extend(["", "### Lineage Warnings", ""])
            lines.extend([f"- {item}" for item in lineage_validation.get("warnings", [])])
        if lineage_validation.get("checks"):
            lines.extend(["", "### Lineage Checks", ""])
            lines.extend([f"- {item}" for item in lineage_validation.get("checks", [])])

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
