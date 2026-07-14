from __future__ import annotations

import re


ROLE_KEYS = {
    "raw_load": "raw_tables",
    "staging": "staging_tables",
    "dimension": "dimension_tables",
    "fact": "fact_tables",
}


def _role_for_table(table_name: str) -> str:
    name = table_name.lower()
    if name.startswith("load_") or name.endswith("_raw"):
        return "raw_load"
    if name.startswith("stg_"):
        return "staging"
    if name.startswith("dim_"):
        return "dimension"
    if name.startswith("fact_"):
        return "fact"
    return "other"


def _entity_token(table_name: str) -> str:
    name = table_name.lower()
    name = re.sub(r"^(load|stg|dim|fact)_", "", name)
    name = re.sub(r"_raw$", "", name)
    for suffix in ("_detail", "_details", "_item", "_items", "_event", "_events"):
        name = re.sub(f"{suffix}$", "", name)
    return name


def _column_names(table) -> set[str]:
    return {column.name.lower() for column in table.columns}


def _business_key_columns(table) -> set[str]:
    keys = set()
    for column in table.columns:
        name = column.name.lower()
        if column.is_primary_key:
            continue
        if name.endswith(("_id", "_code", "_number", "_no")):
            keys.add(name)
    return keys


def _append_unique(items: list[str], values) -> None:
    for value in values:
        if value and value not in items:
            items.append(value)


def build_warehouse_pipeline_plan(model, semantic_context=None) -> dict:
    """Classify warehouse tables and infer lightweight lineage hints.

    The planner intentionally uses generic DDL/name metadata only; it does not
    encode any business-domain-specific table names.
    """
    plan = {
        "raw_tables": [],
        "staging_tables": [],
        "dimension_tables": [],
        "fact_tables": [],
        "other_tables": [],
        "lineage": {},
        "warnings": [],
    }
    tables_by_name = {table.name: table for table in model.tables}
    roles = {}
    for table in model.tables:
        semantic_role = None
        if semantic_context is not None:
            semantic_role = getattr(semantic_context, "table_roles", {}).get(table.name)
        role = semantic_role if semantic_role in ROLE_KEYS else _role_for_table(table.name)
        roles[table.name] = role
        plan[ROLE_KEYS.get(role, "other_tables")].append(table.name)

    raw_entities = {_entity_token(name): name for name in plan["raw_tables"]}
    staging_entities = {_entity_token(name): name for name in plan["staging_tables"]}

    for table_name in plan["staging_tables"]:
        entity = _entity_token(table_name)
        sources = []
        if entity in raw_entities:
            sources.append(raw_entities[entity])
        stg_cols = _column_names(tables_by_name[table_name])
        for raw_name in plan["raw_tables"]:
            raw_cols = _column_names(tables_by_name[raw_name])
            if raw_name not in sources and len(stg_cols & raw_cols) >= 2:
                sources.append(raw_name)
        plan["lineage"][table_name] = sources
        if not sources:
            plan["warnings"].append(f"No likely raw/load source inferred for staging table {table_name}.")

    for table_name in plan["dimension_tables"]:
        entity = _entity_token(table_name)
        sources = []
        if entity in staging_entities:
            sources.append(staging_entities[entity])
        dim_keys = _business_key_columns(tables_by_name[table_name])
        for stg_name in plan["staging_tables"]:
            stg_cols = _column_names(tables_by_name[stg_name])
            if stg_name not in sources and dim_keys and dim_keys & stg_cols:
                sources.append(stg_name)
        plan["lineage"][table_name] = sources
        if not sources:
            plan["warnings"].append(f"No likely staging source inferred for dimension table {table_name}.")

    for table_name in plan["fact_tables"]:
        table = tables_by_name[table_name]
        sources = []
        _append_unique(sources, [fk.parent_table for fk in table.foreign_keys if fk.parent_table in plan["dimension_tables"]])
        fact_cols = _column_names(table)
        for stg_name in plan["staging_tables"]:
            stg_table = tables_by_name[stg_name]
            stg_cols = _column_names(stg_table)
            stg_entity = _entity_token(stg_name)
            if stg_name in sources:
                continue
            if stg_entity in _entity_token(table_name) or _business_key_columns(stg_table) & fact_cols or len(stg_cols & fact_cols) >= 2:
                sources.append(stg_name)
        if not any(source in plan["staging_tables"] for source in sources):
            event_like = [name for name in plan["staging_tables"] if _entity_token(name) in {"order", "orders", "sale", "sales", "transaction", "transactions", "event", "events"}]
            _append_unique(sources, event_like)
        plan["lineage"][table_name] = sources
        if not sources:
            plan["warnings"].append(f"No likely staging/dimension sources inferred for fact table {table_name}.")

    return plan
