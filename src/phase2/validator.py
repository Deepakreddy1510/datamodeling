from datetime import date, datetime, time as dt_time
from decimal import Decimal, InvalidOperation
import json
import re
from .semantic_context import build_semantic_context
from .semantic_quality_validator import validate_semantic_quality
from .lineage_validator import validate_lineage



class Phase2ValidationError(Exception):
    pass


def _fk_label(fk):
    return f"{fk.child_table}({', '.join(fk.child_columns)}) -> {fk.parent_table}({', '.join(fk.parent_columns)})"


def _fk_like_columns(model):
    parsed_fk_columns = {(fk.child_table, col) for table in model.tables for fk in table.foreign_keys for col in fk.child_columns}
    skipped = []
    for table in model.tables:
        for column in table.columns:
            name = column.name.lower()
            if (name.endswith("_id") or name.endswith("_key")) and not column.is_primary_key and (table.name, column.name) not in parsed_fk_columns:
                skipped.append(f"{table.name}.{column.name}")
    return skipped


def _decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _is_placeholder(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[a-z_]+_\d{3}", value.lower()))


def _is_analytical_model(model):
    return any(table.name.lower().startswith(("dim_", "fact_")) for table in model.tables)


def _validate_check_value(check, value):
    if value in (None, "") or not check.supported:
        return True
    if check.operator == "IN":
        return str(value) in {str(item) for item in check.values}
    decimal_value = _decimal(value)
    if decimal_value is None:
        return True
    if check.operator == "BETWEEN":
        return Decimal(str(check.min_value)) <= decimal_value <= Decimal(str(check.max_value))
    threshold = Decimal(str(check.min_value))
    if check.operator == ">":
        return decimal_value > threshold
    if check.operator == ">=":
        return decimal_value >= threshold
    if check.operator == "<":
        return decimal_value < threshold
    if check.operator == "<=":
        return decimal_value <= threshold
    return True


def _is_json_serializable(value):
    if isinstance(value, str):
        try:
            json.loads(value)
            return True
        except ValueError:
            return True
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False

def validate_generated_data(model, data, expected_rows, semantic_context=None, business_input=None):
    errors = []
    data_type_errors = []
    constraint_errors = []
    placeholder_warnings = []
    table_map = model.table_map()
    parsed_fks = [_fk_label(fk) for table in model.tables for fk in table.foreign_keys]
    checked_fks = []
    skipped_fk_like_columns = _fk_like_columns(model)
    length_checks = []
    numeric_checks = []

    for table in model.tables:
        rows = data.get(table.name, [])
        expected_count = expected_rows.get(table.name, expected_rows) if isinstance(expected_rows, dict) else expected_rows
        if len(rows) != expected_count:
            errors.append(f"{table.name}: expected {expected_count} rows, found {len(rows)}.")
        for column in table.columns:
            if column.max_length:
                length_checks.append(f"{table.name}.{column.name} <= {column.max_length}")
            if column.numeric_precision is not None and column.numeric_scale is not None:
                numeric_checks.append(f"{table.name}.{column.name} numeric({column.numeric_precision},{column.numeric_scale})")

            for idx, row in enumerate(rows, start=1):
                value = row.get(column.name)
                if not column.nullable and value in (None, ""):
                    errors.append(f"{table.name}.{column.name}: required value missing in row {idx}.")
                if column.max_length and isinstance(value, str) and len(value) > column.max_length:
                    errors.append(f"{table.name}.{column.name}: value exceeds max length {column.max_length} in row {idx}.")
                dtype = column.data_type.lower()
                if any(token in dtype for token in ["int", "serial"]) and value not in (None, "") and not isinstance(value, int):
                    data_type_errors.append(f"{table.name}.{column.name} row {idx}: expected integer, got {value!r}.")
                if any(token in dtype for token in ["numeric", "decimal", "double", "float", "real"]):
                    decimal_value = _decimal(value)
                    if value not in (None, "") and decimal_value is None:
                        data_type_errors.append(f"{table.name}.{column.name} row {idx}: expected numeric, got {value!r}.")
                if "bool" in dtype and value not in (None, "") and not isinstance(value, bool):
                    data_type_errors.append(f"{table.name}.{column.name} row {idx}: expected boolean, got {value!r}.")
                if dtype.startswith("date") and value not in (None, "") and not isinstance(value, date):
                    data_type_errors.append(f"{table.name}.{column.name} row {idx}: expected date, got {value!r}.")
                if dtype.startswith("time") and "timestamp" not in dtype and value not in (None, "") and not isinstance(value, dt_time):
                    data_type_errors.append(f"{table.name}.{column.name} row {idx}: expected time, got {value!r}.")
                if ("timestamp" in dtype or "timestamptz" in dtype) and value not in (None, "") and not isinstance(value, (date, datetime)):
                    data_type_errors.append(f"{table.name}.{column.name} row {idx}: expected timestamp, got {value!r}.")
                if dtype in {"json", "jsonb"} and value not in (None, "") and not _is_json_serializable(value):
                    data_type_errors.append(f"{table.name}.{column.name} row {idx}: expected JSON-serializable value, got {value!r}.")

                if column.numeric_precision is not None and column.numeric_scale is not None and value not in (None, ""):
                    decimal_value = _decimal(value)
                    if decimal_value is None:
                        continue
                    integer_digits = column.numeric_precision - column.numeric_scale
                    max_abs_value = Decimal(10) ** integer_digits
                    exponent = decimal_value.as_tuple().exponent
                    value_scale = abs(exponent) if exponent < 0 else 0
                    if abs(decimal_value) >= max_abs_value or value_scale > column.numeric_scale:
                        errors.append(f"{table.name}.{column.name}: value exceeds numeric({column.numeric_precision},{column.numeric_scale}) precision/scale in row {idx}.")

                if _is_placeholder(value):
                    placeholder_warnings.append(f"{table.name}.{column.name} row {idx}: placeholder-like fallback value {value!r}.")

        if table.primary_key:
            seen = set()
            for row in rows:
                key = tuple(row.get(col) for col in table.primary_key)
                if key in seen:
                    errors.append(f"{table.name}: duplicate primary key {key}.")
                    break
                seen.add(key)
        for unique in getattr(table, "unique_constraints", []):
            seen_unique = set()
            for row in rows:
                key = tuple(row.get(col) for col in unique.columns)
                if key in seen_unique:
                    constraint_errors.append(f"{table.name}: duplicate UNIQUE constraint value {key} for columns {unique.columns}.")
                    break
                seen_unique.add(key)
        for check in getattr(table, "check_constraints", []):
            if not getattr(check, "supported", False):
                continue
            for idx, row in enumerate(rows, start=1):
                if not _validate_check_value(check, row.get(check.column)):
                    constraint_errors.append(f"{table.name}.{check.column} row {idx}: CHECK constraint {check.expression!r} is not satisfied.")
                    break
        for fk in table.foreign_keys:
            checked_fks.append(_fk_label(fk))
            parent = table_map[fk.parent_table.lower()]
            parent_keys = {tuple(row.get(col) for col in fk.parent_columns) for row in data.get(parent.name, [])}
            for row in rows:
                child_key = tuple(row.get(col) for col in fk.child_columns)
                if child_key not in parent_keys:
                    errors.append(f"{table.name}: foreign key {fk.child_columns} value {child_key} not found in {parent.name}.")
                    break
    if semantic_context is None:
        semantic_context = build_semantic_context(business_input or {}, model)
    semantic_quality = validate_semantic_quality(model, data, semantic_context)
    semantic_placeholder_errors = semantic_quality.get("errors", [])
    errors.extend(semantic_placeholder_errors)
    lineage_validation = validate_lineage(model, data)
    errors.extend(lineage_validation.get("errors", []))
    errors.extend(data_type_errors)
    errors.extend(constraint_errors)
    status = "failed" if errors else ("passed_with_warnings" if skipped_fk_like_columns or placeholder_warnings else "passed")
    return {
        "status": status,
        "errors": errors,
        "parsed_fk_relationships": parsed_fks,
        "checked_fk_relationships": checked_fks,
        "skipped_fk_like_columns": skipped_fk_like_columns,
        "length_checks": length_checks,
        "numeric_checks": numeric_checks,
        "data_type_errors": data_type_errors,
        "constraint_errors": constraint_errors,
        "placeholder_warnings": placeholder_warnings,
        "semantic_placeholder_errors": semantic_placeholder_errors,
        "semantic_placeholder_checked_values": semantic_quality.get("checked_values", 0),
        "lineage_validation": lineage_validation,
        "row_count_summary": {table.name: len(data.get(table.name, [])) for table in model.tables},
    }
