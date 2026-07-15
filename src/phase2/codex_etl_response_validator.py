from __future__ import annotations

import json
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
IDENTIFIER_PART = r'(?:"(?:[^"]|"")+"|[A-Za-z_][A-Za-z0-9_$]*)'
QUALIFIED_IDENTIFIER = rf"{IDENTIFIER_PART}(?:\s*\.\s*{IDENTIFIER_PART})?"
INSERT_TARGET_RE = re.compile(
    rf"(?:^|\b)INSERT\s+INTO\s+(?:ONLY\s+)?(?P<target>{QUALIFIED_IDENTIFIER})",
    re.IGNORECASE | re.DOTALL,
)
TABLE_REF_RE = re.compile(
    rf"\b(?P<keyword>FROM|JOIN|INTO|UPDATE)\s+(?:ONLY\s+)?(?:LATERAL\s+)?"
    rf"(?P<ref>{QUALIFIED_IDENTIFIER})(?![A-Za-z0-9_$\"]|\s*\.)",
    re.IGNORECASE,
)
CTE_RE = re.compile(
    rf"(?:\bWITH\b|,)\s*(?:RECURSIVE\s+)?(?P<name>{IDENTIFIER_PART})"
    rf"\s*(?:\([^)]*\))?\s+AS\s+(?:(?:NOT\s+)?MATERIALIZED\s+)?\(",
    re.IGNORECASE,
)
NON_TABLE_FROM_FUNCTIONS = {"extract", "overlay", "substring", "substr", "trim"}


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


def _matching_parenthesis(sql_text: str, open_index: int) -> int | None:
    depth = 0
    in_single_quote = False
    index = open_index
    while index < len(sql_text):
        char = sql_text[index]
        if char == "'":
            if in_single_quote and index + 1 < len(sql_text) and sql_text[index + 1] == "'":
                index += 2
                continue
            in_single_quote = not in_single_quote
        elif not in_single_quote:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return index
        index += 1
    return None


def _mask_non_table_from_syntax(sql_text: str) -> str:
    """Mask PostgreSQL function syntax whose FROM keyword is not a table clause."""
    masked = list(sql_text)
    function_re = re.compile(r"\b([A-Za-z_][A-Za-z0-9_$]*)\s*\(", re.IGNORECASE)
    for match in function_re.finditer(sql_text):
        if match.group(1).lower() not in NON_TABLE_FROM_FUNCTIONS:
            continue
        open_index = sql_text.find("(", match.start(), match.end())
        close_index = _matching_parenthesis(sql_text, open_index)
        if close_index is None:
            continue
        for index in range(open_index + 1, close_index):
            masked[index] = " "
    return "".join(masked)


def _extract_table_references(sql_text: str) -> list[str]:
    safe_sql = _mask_non_table_from_syntax(sql_text)
    references = []
    for match in TABLE_REF_RE.finditer(safe_sql):
        remainder = safe_sql[match.end():]
        if match.group("keyword").lower() in {"from", "join"} and re.match(r"\s*\(", remainder):
            continue
        references.append(match.group("ref"))
    return references


def _extract_cte_names(sql_text: str) -> set[str]:
    return {_clean_identifier(match.group("name")) for match in CTE_RE.finditer(sql_text)}


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
        cte_names = _extract_cte_names(sql)
        for ref in _extract_table_references(sql):
            schema, ref_name = _table_name(ref)
            if schema is None and ref_name in cte_names:
                continue
            if schema and schema in {"pg_catalog", "information_schema"}:
                errors.append(f"{name}[{index}] references disallowed schema {schema}.")
            elif ref_name not in known_tables:
                errors.append(f"{name}[{index}] references unknown table {ref}.")


def validate_codex_etl_response(response, model, pipeline_plan, generation_profile=None) -> dict:
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

    generation_profile = generation_profile or {}
    table_profiles = generation_profile.get("table_profiles", {})
    expected_counts = generation_profile.get("raw_table_row_counts", {})
    relationships = generation_profile.get("relationships", [])

    load_rows = response.get("load_table_rows", {})
    if not isinstance(load_rows, dict):
        errors.append("load_table_rows must be an object keyed by raw/load table name.")
    else:
        for expected_table in sorted(raw_tables):
            if expected_table not in {str(name).lower() for name in load_rows}:
                errors.append(f"load_table_rows is missing required raw/load table {expected_table}.")
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
            expected_count = expected_counts.get(table_name, expected_counts.get(normalized))
            if expected_count is not None and len(rows) != expected_count:
                errors.append(
                    f"load_table_rows.{table_name} contains {len(rows)} rows; expected exactly {expected_count} "
                    "from the warehouse generation profile."
                )
            allowed_columns = columns_by_table[normalized]
            profile = table_profiles.get(table_name, table_profiles.get(normalized, {}))
            required_payload = set(profile.get("required_payload_columns", []))
            for row_index, row in enumerate(rows, start=1):
                extra = set(row) - allowed_columns
                if extra:
                    errors.append(f"load_table_rows.{table_name}[{row_index}] contains unknown columns: {', '.join(sorted(extra))}.")
                if profile.get("has_source_payload"):
                    payload = row.get("source_payload")
                    if isinstance(payload, str):
                        try:
                            payload = json.loads(payload)
                        except json.JSONDecodeError:
                            errors.append(
                                f"load_table_rows.{table_name}[{row_index}].source_payload is not valid JSON."
                            )
                            continue
                    if not isinstance(payload, dict):
                        errors.append(
                            f"load_table_rows.{table_name}[{row_index}].source_payload must be a JSON object."
                        )
                        continue
                    missing = required_payload - set(payload)
                    if missing:
                        errors.append(
                            f"load_table_rows.{table_name}[{row_index}].source_payload is missing required "
                            f"mapped staging columns: {', '.join(sorted(missing))}."
                        )

        # Validate business-key relationships in raw JSON payloads before SQL execution.
        payload_cache = {}
        for table_name, rows in load_rows.items():
            normalized = str(table_name).lower()
            profile = table_profiles.get(table_name, table_profiles.get(normalized, {}))
            parsed_rows = []
            for row in rows if isinstance(rows, list) else []:
                payload = row.get("source_payload") if isinstance(row, dict) and profile.get("has_source_payload") else row
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError:
                        payload = None
                if isinstance(payload, dict):
                    parsed_rows.append(payload)
            payload_cache[normalized] = parsed_rows

        for relationship in relationships:
            child_name = str(relationship.get("child_raw_table", "")).lower()
            parent_name = str(relationship.get("parent_raw_table", "")).lower()
            child_columns = relationship.get("child_columns", [])
            parent_columns = relationship.get("parent_columns", [])
            child_rows = payload_cache.get(child_name, [])
            parent_rows = payload_cache.get(parent_name, [])
            if not child_rows or not parent_rows or not child_columns or not parent_columns:
                continue
            parent_keys = {tuple(row.get(column) for column in parent_columns) for row in parent_rows}
            child_keys = [tuple(row.get(column) for column in child_columns) for row in child_rows]
            unresolved = [key for key in child_keys if key not in parent_keys]
            if unresolved:
                errors.append(
                    f"Raw relationship {child_name} -> {parent_name} has {len(unresolved)} unresolved "
                    f"foreign-key values for {', '.join(child_columns)}."
                )
            if relationship.get("require_reuse") and len(set(child_keys)) == len(child_keys):
                errors.append(
                    f"Raw relationship {child_name} -> {parent_name} requires realistic parent reuse, "
                    "but every child row references a different parent."
                )

    _validate_sql_list("staging_sql", response.get("staging_sql"), staging_tables, known_tables, errors, warnings)
    _validate_sql_list("dimension_sql", response.get("dimension_sql"), dimension_tables, known_tables, errors, warnings)
    _validate_sql_list("fact_sql", response.get("fact_sql"), fact_tables, known_tables, errors, warnings)
    if not isinstance(response.get("assumptions", []), list):
        errors.append("assumptions must be a list.")
    return {"status": "failed" if errors else "passed", "errors": errors, "warnings": warnings}
