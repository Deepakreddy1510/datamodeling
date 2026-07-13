from .lineage_mapper import analyze_lineage, business_key_columns, shared_columns


def _type_family(column):
    dtype = column.data_type.lower()
    if any(token in dtype for token in ["int", "serial"]):
        return "integer"
    if any(token in dtype for token in ["numeric", "decimal", "double", "float", "real"]):
        return "numeric"
    if "bool" in dtype:
        return "boolean"
    if dtype.startswith("date"):
        return "date"
    if "timestamp" in dtype or "time" in dtype:
        return "timestamp"
    if any(token in dtype for token in ["char", "text"]):
        return "text"
    return dtype


def _same_type_shared_columns(source, target):
    source_lookup = {column.name: column for column in source.columns}
    target_lookup = {column.name: column for column in target.columns}
    return [
        name for name in shared_columns(source, target, include_keys=False)
        if _type_family(source_lookup[name]) == _type_family(target_lookup[name])
    ]


def _rows_by_key(rows, keys):
    return {tuple(row.get(key) for key in keys): row for row in rows}


def _display_table(table):
    return table.name if hasattr(table, "name") else str(table)


def validate_lineage(model, data):
    mappings = analyze_lineage(model)
    errors = []
    checked_raw_staging = []
    checked_staging_dimension = []
    checked_fact_dimension = []

    for mapping in mappings["raw_to_staging"]:
        source = mapping["source"]
        target = mapping["target"]
        keys = [key for key in business_key_columns(source) if key in target.column_names()]
        columns = _same_type_shared_columns(source, target)
        checked_raw_staging.append(f"{source.name} -> {target.name}")
        if keys:
            source_by_key = _rows_by_key(data.get(source.name, []), keys)
            target_rows = data.get(target.name, [])
            for target_row in target_rows:
                source_row = source_by_key.get(tuple(target_row.get(key) for key in keys))
                if not source_row:
                    continue
                for column in columns:
                    if source_row.get(column) != target_row.get(column):
                        errors.append(f"{target.name}.{column} does not match {source.name}.{column} for {', '.join(f'{key}={target_row.get(key)}' for key in keys)}.")
                        break
        else:
            for idx, (source_row, target_row) in enumerate(zip(data.get(source.name, []), data.get(target.name, [])), start=1):
                for column in columns:
                    if source_row.get(column) != target_row.get(column):
                        errors.append(f"{target.name}.{column} row {idx} does not match {source.name}.{column}.")
                        break

    for mapping in mappings["staging_to_dimension"]:
        source = mapping["source"]
        target = mapping["target"]
        keys = [key for key in business_key_columns(source) if key in target.column_names()]
        columns = _same_type_shared_columns(source, target)
        checked_staging_dimension.append(f"{source.name} -> {target.name}")
        if keys:
            source_by_key = _rows_by_key(data.get(source.name, []), keys)
            for target_row in data.get(target.name, []):
                source_row = source_by_key.get(tuple(target_row.get(key) for key in keys))
                if not source_row:
                    continue
                for column in columns:
                    if source_row.get(column) != target_row.get(column):
                        errors.append(f"{target.name}.{column} does not match {source.name}.{column} for {', '.join(f'{key}={target_row.get(key)}' for key in keys)}.")
                        break
        else:
            for idx, (source_row, target_row) in enumerate(zip(data.get(source.name, []), data.get(target.name, [])), start=1):
                for column in columns:
                    if source_row.get(column) != target_row.get(column):
                        errors.append(f"{target.name}.{column} row {idx} does not match {source.name}.{column}.")
                        break

    for mapping in mappings["fact_to_dimension"]:
        fact = mapping["fact"]
        dimension = mapping["dimension"]
        dim_key = mapping["dimension_key"]
        business_keys = mapping["business_keys"]
        checked_fact_dimension.append(f"{fact.name}.{dim_key} -> {dimension.name}.{dim_key}")
        if not business_keys:
            continue
        dim_by_surrogate = {row.get(dim_key): row for row in data.get(dimension.name, [])}
        for idx, fact_row in enumerate(data.get(fact.name, []), start=1):
            dim_row = dim_by_surrogate.get(fact_row.get(dim_key))
            if not dim_row:
                continue
            for key in business_keys:
                if fact_row.get(key) != dim_row.get(key):
                    errors.append(f"{fact.name}.{dim_key} row {idx} points to {dimension.name} {key}={dim_row.get(key)} but fact has {key}={fact_row.get(key)}.")
                    break

    return {
        "status": "failed" if errors else "passed",
        "errors": errors,
        "checked_raw_to_staging": checked_raw_staging,
        "checked_staging_to_dimension": checked_staging_dimension,
        "checked_fact_to_dimension": checked_fact_dimension,
        "identified_entities": sorted(mappings["entities"].keys()),
    }
