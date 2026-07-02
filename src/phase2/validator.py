from decimal import Decimal, InvalidOperation


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


def validate_generated_data(model, data, expected_rows):
    errors = []
    table_map = model.table_map()
    parsed_fks = [_fk_label(fk) for table in model.tables for fk in table.foreign_keys]
    checked_fks = []
    skipped_fk_like_columns = _fk_like_columns(model)
    length_checks = []
    numeric_checks = []

    for table in model.tables:
        rows = data.get(table.name, [])
        if len(rows) != expected_rows:
            errors.append(f"{table.name}: expected {expected_rows} rows, found {len(rows)}.")
        for column in table.columns:
            if column.max_length:
                length_checks.append(f"{table.name}.{column.name} <= {column.max_length}")
            if not column.nullable:
                missing = [idx for idx, row in enumerate(rows, start=1) if row.get(column.name) in (None, "")]
                if missing:
                    errors.append(f"{table.name}.{column.name}: required value missing in rows {missing[:5]}.")
            if column.max_length:
                too_long = [
                    idx for idx, row in enumerate(rows, start=1)
                    if isinstance(row.get(column.name), str) and len(row[column.name]) > column.max_length
                ]
                if too_long:
                    errors.append(
                        f"{table.name}.{column.name}: value exceeds max length {column.max_length} in rows {too_long[:5]}."
                    )
            if column.numeric_precision is not None and column.numeric_scale is not None:
                numeric_checks.append(f"{table.name}.{column.name} numeric({column.numeric_precision},{column.numeric_scale})")
                integer_digits = column.numeric_precision - column.numeric_scale
                max_abs_value = Decimal(10) ** integer_digits
                bad_rows = []
                for idx, row in enumerate(rows, start=1):
                    value = row.get(column.name)
                    if value in (None, ""):
                        continue
                    try:
                        decimal_value = Decimal(str(value))
                    except (InvalidOperation, ValueError):
                        bad_rows.append(idx)
                        continue
                    exponent = decimal_value.as_tuple().exponent
                    value_scale = abs(exponent) if exponent < 0 else 0
                    if abs(decimal_value) >= max_abs_value or value_scale > column.numeric_scale:
                        bad_rows.append(idx)
                if bad_rows:
                    errors.append(
                        f"{table.name}.{column.name}: value exceeds numeric({column.numeric_precision},{column.numeric_scale}) precision/scale in rows {bad_rows[:5]}."
                    )
        if table.primary_key:
            seen = set()
            for row in rows:
                key = tuple(row.get(col) for col in table.primary_key)
                if key in seen:
                    errors.append(f"{table.name}: duplicate primary key {key}.")
                    break
                seen.add(key)
        for fk in table.foreign_keys:
            checked_fks.append(_fk_label(fk))
            parent = table_map[fk.parent_table.lower()]
            parent_keys = {tuple(row.get(col) for col in fk.parent_columns) for row in data.get(parent.name, [])}
            for row in rows:
                child_key = tuple(row.get(col) for col in fk.child_columns)
                if child_key not in parent_keys:
                    errors.append(f"{table.name}: foreign key {fk.child_columns} value {child_key} not found in {parent.name}.")
                    break
    status = "failed" if errors else ("passed_with_warnings" if skipped_fk_like_columns else "passed")
    return {
        "status": status,
        "errors": errors,
        "parsed_fk_relationships": parsed_fks,
        "checked_fk_relationships": checked_fks,
        "skipped_fk_like_columns": skipped_fk_like_columns,
        "length_checks": length_checks,
        "numeric_checks": numeric_checks,
    }
