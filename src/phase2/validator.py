from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re

from .value_catalog_parser import get_catalog_rule


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


def _normalize_rule_value(value, column):
    dtype = column.data_type.lower()
    if value is None:
        return None
    try:
        if any(token in dtype for token in ["int", "serial"]):
            return int(Decimal(str(value)))
        if any(token in dtype for token in ["numeric", "decimal", "double", "float"]):
            decimal_value = Decimal(str(value))
            if column.numeric_scale is not None:
                decimal_value = decimal_value.quantize(Decimal(1).scaleb(-column.numeric_scale) if column.numeric_scale else Decimal(1))
            return decimal_value
        if "bool" in dtype:
            if isinstance(value, bool):
                return value
            normalized = str(value).strip().lower()
            if normalized in {"true", "yes", "1", "y"}:
                return True
            if normalized in {"false", "no", "0", "n"}:
                return False
        if dtype.startswith("date"):
            if isinstance(value, date) and not isinstance(value, datetime):
                return value
            return datetime.fromisoformat(str(value)).date()
        if "timestamp" in dtype:
            if isinstance(value, datetime):
                return value
            return datetime.fromisoformat(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value
    return str(value)


def _validate_calculation(rule, row, column):
    calculation = str((rule or {}).get("calculation_rule") or "").strip()
    if not calculation:
        return None
    flag_match = re.search(
        r"(?:flag\s+)?true\s+when\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*['\"]?([^'\"]+)['\"]?",
        calculation,
        re.IGNORECASE,
    )
    if flag_match and ("bool" in column.data_type.lower() or column.name.lower().endswith("flag") or column.name.lower().startswith("is_")):
        source_name, expected = flag_match.groups()
        return row.get(column.name) == (str(row.get(source_name, "")).strip().lower() == expected.strip().lower())
    if "=" not in calculation:
        return None
    target, expression = [part.strip() for part in calculation.split("=", 1)]
    if target.lower() != column.name.lower():
        return None
    percentage_match = re.fullmatch(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*/\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\*\s*100", expression, re.IGNORECASE)
    if percentage_match:
        numerator = _decimal(row.get(percentage_match.group(1)))
        denominator = _decimal(row.get(percentage_match.group(2)))
        actual = _decimal(row.get(column.name))
        if numerator is None or denominator in (None, Decimal("0")) or actual is None:
            return False
        expected = (numerator / denominator) * Decimal("100")
        return actual == expected.quantize(actual) if actual.as_tuple().exponent < 0 else actual == expected
    delay_match = re.fullmatch(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*-\s*([a-zA-Z_][a-zA-Z0-9_]*)", expression)
    if delay_match and "minute" in column.name.lower():
        left = row.get(delay_match.group(1))
        right = row.get(delay_match.group(2))
        if isinstance(left, datetime) and isinstance(right, datetime):
            return row.get(column.name) == int((left - right).total_seconds() // 60)
    match = re.fullmatch(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*([*+\-/])\s*([a-zA-Z_][a-zA-Z0-9_]*)", expression)
    if not match:
        return None
    left_name, operator, right_name = match.groups()
    left = _decimal(row.get(left_name))
    right = _decimal(row.get(right_name))
    actual = _decimal(row.get(column.name))
    if left is None or right is None or actual is None:
        return False
    if operator == "*":
        expected = left * right
    elif operator == "+":
        expected = left + right
    elif operator == "-":
        expected = left - right
    elif operator == "/" and right != 0:
        expected = left / right
    else:
        return None
    return actual == expected.quantize(actual) if actual.as_tuple().exponent < 0 else actual == expected


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

def validate_generated_data(model, data, expected_rows, value_catalog=None):
    errors = []
    catalog_compliance_errors = []
    data_type_errors = []
    calculation_errors = []
    constraint_errors = []
    date_rule_errors = []
    boolean_rule_errors = []
    placeholder_warnings = []
    table_map = model.table_map()
    parsed_fks = [_fk_label(fk) for table in model.tables for fk in table.foreign_keys]
    checked_fks = []
    skipped_fk_like_columns = _fk_like_columns(model)
    length_checks = []
    numeric_checks = []
    catalog_rules_checked = 0
    catalog_warnings = list((value_catalog or {}).get("warnings", []))
    catalog_errors = list((value_catalog or {}).get("errors", []))
    if catalog_errors:
        errors.extend(catalog_errors)
    if (value_catalog or {}).get("markers_present") and (value_catalog or {}).get("rule_count", 0) == 0:
        errors.append("Synthetic value catalog markers were present but no usable table_column_rules were found.")
    if _is_analytical_model(model) and not (value_catalog or {}).get("catalog_found"):
        errors.append("Analytical DDL contains dim_/fact_ tables but no valid Synthetic Data Value Catalog was found.")

    for table in model.tables:
        rows = data.get(table.name, [])
        if len(rows) != expected_rows:
            errors.append(f"{table.name}: expected {expected_rows} rows, found {len(rows)}.")
        for column in table.columns:
            rule = get_catalog_rule(value_catalog, table.name, column.name)
            if rule:
                catalog_rules_checked += 1
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
                if any(token in dtype for token in ["numeric", "decimal", "double", "float"]):
                    decimal_value = _decimal(value)
                    if value not in (None, "") and decimal_value is None:
                        data_type_errors.append(f"{table.name}.{column.name} row {idx}: expected numeric, got {value!r}.")
                if "bool" in dtype and value not in (None, "") and not isinstance(value, bool):
                    data_type_errors.append(f"{table.name}.{column.name} row {idx}: expected boolean, got {value!r}.")
                if dtype.startswith("date") and value not in (None, "") and not isinstance(value, date):
                    data_type_errors.append(f"{table.name}.{column.name} row {idx}: expected date, got {value!r}.")
                if "timestamp" in dtype and value not in (None, "") and not isinstance(value, (date, datetime)):
                    data_type_errors.append(f"{table.name}.{column.name} row {idx}: expected timestamp, got {value!r}.")

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

                if rule:
                    allowed = [_normalize_rule_value(item, column) for item in (rule.get("allowed_values") or [])]
                    if allowed and value not in allowed and value not in (None, ""):
                        catalog_compliance_errors.append(f"{table.name}.{column.name} row {idx} value {value!r} is not in allowed_values {allowed!r}.")
                    numeric_min = rule.get("numeric_min")
                    numeric_max = rule.get("numeric_max")
                    if numeric_min is not None or numeric_max is not None:
                        decimal_value = _decimal(value)
                        if decimal_value is not None:
                            if numeric_min is not None and decimal_value < Decimal(str(numeric_min)):
                                catalog_compliance_errors.append(f"{table.name}.{column.name} row {idx} value {value!r} is below numeric_min {numeric_min}.")
                            if numeric_max is not None and decimal_value > Decimal(str(numeric_max)):
                                catalog_compliance_errors.append(f"{table.name}.{column.name} row {idx} value {value!r} is above numeric_max {numeric_max}.")
                    calculation_ok = _validate_calculation(rule, row, column)
                    if calculation_ok is False:
                        calculation_errors.append(f"{table.name}.{column.name} row {idx}: calculation_rule {rule.get('calculation_rule')!r} is not satisfied.")
                    if _is_placeholder(value):
                        catalog_compliance_errors.append(f"{table.name}.{column.name} row {idx}: placeholder-like value {value!r} generated despite catalog rule.")
                elif _is_placeholder(value):
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
    errors.extend(catalog_compliance_errors)
    errors.extend(data_type_errors)
    errors.extend(constraint_errors)
    errors.extend(date_rule_errors)
    errors.extend(boolean_rule_errors)
    errors.extend(calculation_errors)
    status = "failed" if errors else ("passed_with_warnings" if skipped_fk_like_columns or placeholder_warnings else "passed")
    return {
        "status": status,
        "errors": errors,
        "parsed_fk_relationships": parsed_fks,
        "checked_fk_relationships": checked_fks,
        "skipped_fk_like_columns": skipped_fk_like_columns,
        "length_checks": length_checks,
        "numeric_checks": numeric_checks,
        "catalog_rules_checked": catalog_rules_checked,
        "catalog_compliance_errors": catalog_compliance_errors,
        "data_type_errors": data_type_errors,
        "calculation_errors": calculation_errors,
        "constraint_errors": constraint_errors,
        "date_rule_errors": date_rule_errors,
        "boolean_rule_errors": boolean_rule_errors,
        "placeholder_warnings": placeholder_warnings,
        "catalog_parser_warnings": catalog_warnings,
        "catalog_parser_errors": catalog_errors,
        "row_count_summary": {table.name: len(data.get(table.name, [])) for table in model.tables},
    }
