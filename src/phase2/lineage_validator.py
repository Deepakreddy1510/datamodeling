from __future__ import annotations


def _table_map(model):
    return {table.name: table for table in model.tables}


def _business_key_columns(table):
    keys = []
    pk = set(table.primary_key)
    for column in table.columns:
        name = column.name.lower()
        if column.name in pk:
            continue
        if name.endswith(("_id", "_code", "_number", "_no")):
            keys.append(column.name)
    return keys


def _common_columns(left, right):
    left_cols = {column.name for column in left.columns}
    return [column.name for column in right.columns if column.name in left_cols]


def _values(data, table_name, column_name):
    return {row.get(column_name) for row in data.get(table_name, []) if row.get(column_name) not in (None, "")}


def _check_values_exist(child_name, child_col, parent_names, data, parent_col=None):
    parent_values = set()
    for parent_name in parent_names:
        parent_values.update(_values(data, parent_name, parent_col or child_col))
    child_values = _values(data, child_name, child_col)
    missing = child_values - parent_values
    return child_values, missing


def validate_lineage(model, data, pipeline_plan) -> dict:
    errors = []
    warnings = []
    checks = []
    tables = _table_map(model)
    lineage = pipeline_plan.get("lineage", {})

    for stg_name in pipeline_plan.get("staging_tables", []):
        sources = [source for source in lineage.get(stg_name, []) if source in pipeline_plan.get("raw_tables", [])]
        if not sources:
            warnings.append(f"{stg_name}: no raw/load lineage source available for validation.")
            continue
        stg_table = tables[stg_name]
        candidate_cols = _business_key_columns(stg_table)
        if not candidate_cols:
            for source in sources:
                candidate_cols.extend(_common_columns(tables[source], stg_table))
        candidate_cols = list(dict.fromkeys(candidate_cols))
        checked = False
        for col in candidate_cols:
            if not any(col in {column.name for column in tables[source].columns} for source in sources):
                continue
            child_values, missing = _check_values_exist(stg_name, col, sources, data)
            if child_values:
                checked = True
                checks.append(f"{stg_name}.{col} values exist in raw/load sources {', '.join(sources)}.")
            if missing:
                errors.append(f"{stg_name}.{col}: {len(missing)} value(s) are not present in raw/load sources {', '.join(sources)}.")
        if not checked:
            warnings.append(f"{stg_name}: no comparable business-key columns found in raw/load sources.")

    for dim_name in pipeline_plan.get("dimension_tables", []):
        sources = [source for source in lineage.get(dim_name, []) if source in pipeline_plan.get("staging_tables", [])]
        if not sources:
            warnings.append(f"{dim_name}: no staging lineage source available for validation.")
            continue
        dim_table = tables[dim_name]
        checked = False
        for col in _business_key_columns(dim_table):
            if not any(col in {column.name for column in tables[source].columns} for source in sources):
                continue
            child_values, missing = _check_values_exist(dim_name, col, sources, data)
            if child_values:
                checked = True
                checks.append(f"{dim_name}.{col} values exist in staging sources {', '.join(sources)}.")
            if missing:
                errors.append(f"{dim_name}.{col}: {len(missing)} value(s) are not present in staging sources {', '.join(sources)}.")
        if not checked:
            warnings.append(f"{dim_name}: no comparable business-key columns found in staging sources.")

    for fact_name in pipeline_plan.get("fact_tables", []):
        fact_table = tables[fact_name]
        checked_fk = False
        for fk in fact_table.foreign_keys:
            if fk.parent_table not in pipeline_plan.get("dimension_tables", []):
                continue
            checked_fk = True
            parent_rows = data.get(fk.parent_table, [])
            parent_keys = {tuple(row.get(col) for col in fk.parent_columns) for row in parent_rows}
            missing_count = 0
            for row in data.get(fact_name, []):
                child_key = tuple(row.get(col) for col in fk.child_columns)
                if any(value in (None, "") for value in child_key):
                    continue
                if child_key not in parent_keys:
                    missing_count += 1
            checks.append(f"{fact_name}.{', '.join(fk.child_columns)} resolves to dimension {fk.parent_table}.")
            if missing_count:
                errors.append(f"{fact_name}: {missing_count} fact row(s) contain random/unresolved dimension key(s) for {fk.parent_table}.")
        if not checked_fk:
            warnings.append(f"{fact_name}: no parsed fact-to-dimension foreign keys available for lineage validation.")

    return {"status": "failed" if errors else "passed", "errors": errors, "warnings": warnings, "checks": checks}
