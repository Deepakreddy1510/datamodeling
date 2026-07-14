from __future__ import annotations

import re


REQUIRED_KEYS = ["load_table_rows", "staging_sql", "dimension_sql", "fact_sql", "assumptions"]
BLOCKED_PATTERNS = [
    r"\bDROP\s+DATABASE\b",
    r"\bDROP\s+SCHEMA\b",
    r"\bDROP\s+TABLE\b",
    r"\bALTER\s+SYSTEM\b",
    r"\bALTER\s+TABLE\b",
    r"\bCREATE\s+USER\b",
    r"\bCREATE\s+ROLE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bDELETE\b",
    r"\bTRUNCATE\b",
    r"\bCOPY\s+PROGRAM\b",
    r"\bSECURITY\s+DEFINER\b",
    r"\bCREATE\s+TABLE\b",
    r"\bCREATE\s+SCHEMA\b",
]
INSERT_TARGET_RE = re.compile(r"(?:^|\b)INSERT\s+INTO\s+(?:ONLY\s+)?(?P<target>[\w\".]+)", re.IGNORECASE | re.DOTALL)
TABLE_REF_RE = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE)\s+(?:ONLY\s+)?([\w\".]+)", re.IGNORECASE)
CTE_RE = re.compile(r"(?:WITH|,)\s+([\w\"]+)\s+AS\s*\(", re.IGNORECASE)


class CodexEtlResponseValidationError(Exception):
    pass


def _clean_identifier(identifier: str) -> str:
    return identifier.strip().strip('"').lower()


def _table_name(identifier: str) -> tuple[str | None, str]:
    parts = [_clean_identifier(part) for part in identifier.split(".")]
    if len(parts) == 1:
        return None, parts[0]
    if len(parts) == 2:
        return parts[0], parts[1]
    return ".".join(parts[:-1]), parts[-1]


def _has_select_after_insert(sql: str) -> bool:
    match = INSERT_TARGET_RE.search(sql)
    if not match:
        return False
    return bool(re.search(r"\bSELECT\b", sql[match.end():], re.IGNORECASE | re.DOTALL))


def _is_allowed_transform(sql: str) -> bool:
    stripped = sql.strip().rstrip(";").strip()
    return bool(re.match(r"^(?:WITH\b[\s\S]+?\bINSERT\s+INTO\b|INSERT\s+INTO\b)", stripped, re.IGNORECASE)) and _has_select_after_insert(stripped)


def _validate_sql_list(name: str, statements, allowed_targets: set[str], known_tables: set[str], errors: list[str], warnings: list[str]) -> None:
    if not isinstance(statements, list) or not all(isinstance(item, str) for item in statements):
        errors.append(f"{name} must be a list of SQL strings.")
        return
    for index, statement in enumerate(statements, start=1):
        sql = statement.strip()
        if not sql:
            errors.append(f"{name}[{index}] is empty.")
            continue
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                errors.append(f"{name}[{index}] contains blocked SQL pattern {pattern}.")
        if not _is_allowed_transform(sql):
            errors.append(f"{name}[{index}] must be INSERT ... SELECT or WITH ... INSERT ... SELECT.")
        target_match = INSERT_TARGET_RE.search(sql)
        if not target_match:
            errors.append(f"{name}[{index}] does not contain an INSERT INTO target.")
            continue
        schema_name, target_name = _table_name(target_match.group("target"))
        if schema_name:
            warnings.append(f"{name}[{index}] uses schema-qualified target {schema_name}.{target_name}; executor will run with a controlled search_path.")
        if target_name not in allowed_targets:
            errors.append(f"{name}[{index}] inserts into {target_name}, which is not allowed for this layer.")
        cte_names = {_clean_identifier(match) for match in CTE_RE.findall(sql)}
        for ref in TABLE_REF_RE.findall(sql):
            schema, ref_name = _table_name(ref)
            if ref_name in cte_names:
                continue
            if schema and schema in {"pg_catalog", "information_schema"}:
                errors.append(f"{name}[{index}] references disallowed schema {schema}.")
            elif ref_name not in known_tables:
                errors.append(f"{name}[{index}] references unknown table {ref}.")


def validate_codex_etl_response(response, model, pipeline_plan) -> dict:
    errors = []
    warnings = []
    if not isinstance(response, dict):
        return {"status": "failed", "errors": ["Codex ETL response must be a JSON object."], "warnings": []}
    for key in REQUIRED_KEYS:
        if key not in response:
            errors.append(f"Missing required key: {key}.")

    known_tables = {table.name.lower() for table in model.tables}
    columns_by_table = {table.name.lower(): {column.name for column in table.columns} for table in model.tables}
    raw_tables = {name.lower() for name in pipeline_plan.get("raw_tables", [])}
    staging_tables = {name.lower() for name in pipeline_plan.get("staging_tables", [])}
    dimension_tables = {name.lower() for name in pipeline_plan.get("dimension_tables", [])}
    fact_tables = {name.lower() for name in pipeline_plan.get("fact_tables", [])}

    load_rows = response.get("load_table_rows", {})
    if not isinstance(load_rows, dict):
        errors.append("load_table_rows must be an object keyed by raw/load table name.")
    else:
        for table_name, rows in load_rows.items():
            normalized = table_name.lower()
            if normalized not in raw_tables:
                errors.append(f"load_table_rows contains non-raw/load table {table_name}.")
            if normalized not in known_tables:
                errors.append(f"load_table_rows contains unknown table {table_name}.")
                continue
            if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
                errors.append(f"load_table_rows.{table_name} must be a list of row objects.")
                continue
            allowed_columns = columns_by_table[normalized]
            for row_index, row in enumerate(rows, start=1):
                extra = set(row) - allowed_columns
                if extra:
                    errors.append(f"load_table_rows.{table_name}[{row_index}] contains unknown columns: {', '.join(sorted(extra))}.")

    _validate_sql_list("staging_sql", response.get("staging_sql"), staging_tables, known_tables, errors, warnings)
    _validate_sql_list("dimension_sql", response.get("dimension_sql"), dimension_tables, known_tables, errors, warnings)
    _validate_sql_list("fact_sql", response.get("fact_sql"), fact_tables, known_tables, errors, warnings)
    if not isinstance(response.get("assumptions", []), list):
        errors.append("assumptions must be a list.")
    return {"status": "failed" if errors else "passed", "errors": errors, "warnings": warnings}
