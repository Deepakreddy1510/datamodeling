from __future__ import annotations

import re


ROLE_KEYS = {
    "raw_load": "raw_tables",
    "staging": "staging_tables",
    "dimension": "dimension_tables",
    "fact": "fact_tables",
}

TECHNICAL_COLUMNS = {
    "batch_id",
    "load_id",
    "load_row_id",
    "source_payload",
    "source_file",
    "loaded_at",
    "staged_at",
    "created_at",
    "updated_at",
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
    for plural, singular in (("_details", "_detail"), ("_items", "_item"), ("_events", "_event")):
        if name.endswith(plural):
            name = name[: -len(plural)] + singular
    return name


def _column_names(table) -> set[str]:
    return {column.name.lower() for column in table.columns}


def _lineage_columns(table) -> set[str]:
    return _column_names(table) - TECHNICAL_COLUMNS


def _business_key_columns(table) -> set[str]:
    keys = set()
    for column in table.columns:
        name = column.name.lower()
        if column.is_primary_key or name in TECHNICAL_COLUMNS:
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
        "primary_sources": {},
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

    raw_entities = {}
    for name in plan["raw_tables"]:
        raw_entities.setdefault(_entity_token(name), []).append(name)
    staging_entities = {}
    for name in plan["staging_tables"]:
        staging_entities.setdefault(_entity_token(name), []).append(name)

    for table_name in plan["staging_tables"]:
        entity = _entity_token(table_name)
        sources = []
        if entity in raw_entities:
            sources.append(sorted(raw_entities[entity], key=len)[0])
        else:
            stg_cols = _lineage_columns(tables_by_name[table_name])
            candidates = []
            for raw_name in plan["raw_tables"]:
                raw_table = tables_by_name[raw_name]
                raw_cols = _lineage_columns(raw_table)
                business_key_overlap = _business_key_columns(raw_table) & stg_cols
                overlap = stg_cols & raw_cols
                if business_key_overlap or len(overlap) >= 2:
                    candidates.append((len(business_key_overlap), len(overlap), raw_name))
            if candidates:
                sources.append(max(candidates)[2])
        plan["lineage"][table_name] = sources
        if sources:
            plan["primary_sources"][table_name] = sources[0]
        if not sources:
            plan["warnings"].append(f"No likely raw/load source inferred for staging table {table_name}.")

    for table_name in plan["dimension_tables"]:
        entity = _entity_token(table_name)
        sources = []
        if entity in staging_entities:
            sources.append(sorted(staging_entities[entity], key=len)[0])
        else:
            dim_keys = _business_key_columns(tables_by_name[table_name])
            candidates = []
            for stg_name in plan["staging_tables"]:
                stg_cols = _lineage_columns(tables_by_name[stg_name])
                overlap = dim_keys & stg_cols
                if overlap:
                    candidates.append((len(overlap), stg_name))
            if candidates:
                sources.append(max(candidates)[1])
        plan["lineage"][table_name] = sources
        if sources:
            plan["primary_sources"][table_name] = sources[0]
        if not sources:
            plan["warnings"].append(f"No likely staging source inferred for dimension table {table_name}.")

    for table_name in plan["fact_tables"]:
        table = tables_by_name[table_name]
        sources = []
        _append_unique(
            sources,
            [fk.parent_table for fk in table.foreign_keys if fk.parent_table in plan["dimension_tables"]],
        )

        fact_entity = _entity_token(table_name)
        exact_staging = sorted(staging_entities.get(fact_entity, []), key=len)
        primary_staging = exact_staging[0] if exact_staging else None

        if primary_staging:
            _append_unique(sources, [primary_staging])
            primary_table = tables_by_name[primary_staging]
            # Include explicit staging parents needed to reconstruct the event,
            # but do not include similarly named sibling/detail tables.
            _append_unique(
                sources,
                [fk.parent_table for fk in primary_table.foreign_keys if fk.parent_table in plan["staging_tables"]],
            )
        else:
            fact_cols = _lineage_columns(table)
            candidates = []
            for stg_name in plan["staging_tables"]:
                stg_table = tables_by_name[stg_name]
                stg_cols = _lineage_columns(stg_table)
                business_overlap = _business_key_columns(stg_table) & fact_cols
                column_overlap = stg_cols & fact_cols
                if business_overlap or len(column_overlap) >= 2:
                    candidates.append(
                        (len(business_overlap), len(column_overlap), -len(_entity_token(stg_name)), stg_name)
                    )
            if candidates:
                primary_staging = max(candidates)[3]
                _append_unique(sources, [primary_staging])
                primary_table = tables_by_name[primary_staging]
                _append_unique(
                    sources,
                    [fk.parent_table for fk in primary_table.foreign_keys if fk.parent_table in plan["staging_tables"]],
                )

        if primary_staging:
            plan["primary_sources"][table_name] = primary_staging
        plan["lineage"][table_name] = sources
        if not sources:
            plan["warnings"].append(f"No likely staging/dimension sources inferred for fact table {table_name}.")

    return plan
