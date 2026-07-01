
class Phase2ValidationError(Exception):
    pass


def validate_generated_data(model, data, expected_rows):
    errors = []
    table_map = model.table_map()
    for table in model.tables:
        rows = data.get(table.name, [])
        if len(rows) != expected_rows:
            errors.append(f"{table.name}: expected {expected_rows} rows, found {len(rows)}.")
        for column in table.columns:
            if not column.nullable:
                missing = [idx for idx, row in enumerate(rows, start=1) if row.get(column.name) in (None, "")]
                if missing:
                    errors.append(f"{table.name}.{column.name}: required value missing in rows {missing[:5]}.")
        if table.primary_key:
            seen = set()
            for row in rows:
                key = tuple(row.get(col) for col in table.primary_key)
                if key in seen:
                    errors.append(f"{table.name}: duplicate primary key {key}.")
                    break
                seen.add(key)
        for fk in table.foreign_keys:
            parent = table_map[fk.parent_table.lower()]
            parent_keys = {tuple(row.get(col) for col in fk.parent_columns) for row in data.get(parent.name, [])}
            for row in rows:
                child_key = tuple(row.get(col) for col in fk.child_columns)
                if child_key not in parent_keys:
                    errors.append(f"{table.name}: foreign key {fk.child_columns} value {child_key} not found in {parent.name}.")
                    break
    return {"status": "passed" if not errors else "failed", "errors": errors}
