from __future__ import annotations

import math
import re
from collections import defaultdict


TECHNICAL_COLUMNS = {
    "batch_id",
    "load_id",
    "load_row_id",
    "source_payload",
    "source_file",
    "source_file_name",
    "source_system",
    "loaded_at",
    "staged_at",
    "created_at",
    "updated_at",
}

DETAIL_TOKENS = {
    "item", "items", "line", "lines", "detail", "details", "entry", "entries",
    "component", "components", "member", "members", "participant", "participants",
    "segment", "segments", "leg", "legs", "position", "positions",
}
EVENT_TOKENS = {
    "order", "orders", "transaction", "transactions", "booking", "bookings",
    "sale", "sales", "invoice", "invoices", "payment", "payments", "delivery",
    "deliveries", "shipment", "shipments", "claim", "claims", "visit", "visits",
    "event", "events", "flight", "flights", "movement", "movements", "activity",
    "activities", "interaction", "interactions", "ticket", "tickets", "request",
    "requests", "case", "cases", "reading", "readings", "snapshot", "snapshots",
}


def _entity_token(table_name: str) -> str:
    name = table_name.lower()
    name = re.sub(r"^(load|stg|dim|fact)_", "", name)
    name = re.sub(r"_raw$", "", name)
    return name


def _tokens(table_name: str) -> set[str]:
    return set(_entity_token(table_name).split("_"))


def _is_detail(table_name: str) -> bool:
    return bool(_tokens(table_name) & DETAIL_TOKENS)


def _is_event(table_name: str) -> bool:
    return bool(_tokens(table_name) & EVENT_TOKENS)


def _column_map(table):
    return {column.name.lower(): column for column in table.columns}


def _business_key_columns(table) -> list[str]:
    result = []
    for column in table.columns:
        name = column.name.lower()
        if name in TECHNICAL_COLUMNS or name.endswith("_key"):
            continue
        if name.endswith(("_id", "_code", "_number", "_no")):
            result.append(column.name)
    return result


def _payload_columns(table) -> list[str]:
    return [
        column.name
        for column in table.columns
        if column.name.lower() not in TECHNICAL_COLUMNS and not column.name.lower().endswith("_key")
    ]


def _required_payload_columns(table) -> list[str]:
    business_keys = set(_business_key_columns(table))
    return [
        column.name
        for column in table.columns
        if column.name.lower() not in TECHNICAL_COLUMNS
        and not column.name.lower().endswith("_key")
        and (not column.nullable or column.name in business_keys)
        and column.default is None
    ]


def _unique_capacity(table) -> int | None:
    capacities = []
    for unique in getattr(table, "unique_constraints", []):
        if len(unique.columns) != 1:
            continue
        column_name = unique.columns[0].lower()
        for check in getattr(table, "check_constraints", []):
            if (
                getattr(check, "supported", False)
                and check.operator == "IN"
                and str(check.column or "").lower() == column_name
                and check.values
            ):
                capacities.append(len(set(check.values)))
    return min(capacities) if capacities else None


def _fk_is_one_to_one(table, fk) -> bool:
    child = {name.lower() for name in fk.child_columns}
    if child and child == {name.lower() for name in table.primary_key}:
        return True
    for unique in getattr(table, "unique_constraints", []):
        if child and child == {name.lower() for name in unique.columns}:
            return True
    return False


def _resolve_raw_source(table_name: str, pipeline_plan: dict) -> str | None:
    raw_tables = set(pipeline_plan.get("raw_tables", []))
    staging_tables = set(pipeline_plan.get("staging_tables", []))
    dimension_tables = set(pipeline_plan.get("dimension_tables", []))
    if table_name in raw_tables:
        return table_name
    if table_name in staging_tables:
        sources = pipeline_plan.get("lineage", {}).get(table_name, [])
        return next((source for source in sources if source in raw_tables), None)
    if table_name in dimension_tables:
        for source in pipeline_plan.get("lineage", {}).get(table_name, []):
            raw = _resolve_raw_source(source, pipeline_plan)
            if raw:
                return raw
    return None


def build_warehouse_generation_profile(model, pipeline_plan: dict, rows_per_table: int) -> dict:
    """Build domain-neutral row-count, reuse, and raw-payload requirements.

    ``rows_per_table`` is treated as the target size of the main business-event
    population. Master/reference entities are intentionally smaller and detail
    tables are intentionally larger so generated data exercises real one-to-many
    relationships instead of producing a trivial one-row-per-entity pattern.
    """
    base_rows = max(1, int(rows_per_table))
    tables = {table.name: table for table in model.tables}
    raw_tables = list(pipeline_plan.get("raw_tables", []))
    staging_tables = list(pipeline_plan.get("staging_tables", []))
    dimensions = set(pipeline_plan.get("dimension_tables", []))
    facts = set(pipeline_plan.get("fact_tables", []))
    lineage = pipeline_plan.get("lineage", {})

    raw_to_staging = defaultdict(list)
    for staging in staging_tables:
        for source in lineage.get(staging, []):
            if source in raw_tables:
                raw_to_staging[source].append(staging)

    fact_staging_sources = {
        source
        for fact in facts
        for source in [pipeline_plan.get("primary_sources", {}).get(fact)]
        if source in staging_tables
    }
    dimension_staging_sources = {
        source
        for dimension in dimensions
        for source in lineage.get(dimension, [])
        if source in staging_tables
    }

    # Parent entities of events/details should be smaller to force realistic reuse.
    event_parent_tables = set()
    for staging_name in staging_tables:
        staging = tables[staging_name]
        if not (_is_event(staging_name) or _is_detail(staging_name) or staging_name in fact_staging_sources):
            continue
        for fk in staging.foreign_keys:
            if fk.parent_table in staging_tables:
                event_parent_tables.add(fk.parent_table)

    table_profiles = {}
    raw_counts = {}
    for raw_name in raw_tables:
        mapped_staging = sorted(raw_to_staging.get(raw_name, []))
        representative_name = mapped_staging[0] if mapped_staging else raw_name
        representative = tables[representative_name]

        if _is_detail(representative_name):
            category = "detail"
            target_rows = max(base_rows + 2, int(math.ceil(base_rows * 3.0)))
        elif _is_event(representative_name) or representative_name in fact_staging_sources:
            category = "event"
            target_rows = base_rows
        elif representative_name in event_parent_tables:
            category = "master"
            target_rows = max(1, int(math.ceil(base_rows * 0.45)))
        elif representative_name in dimension_staging_sources:
            category = "master"
            target_rows = max(1, int(math.ceil(base_rows * 0.60)))
        else:
            category = "general"
            target_rows = base_rows

        capacity = _unique_capacity(representative)
        if capacity is not None:
            target_rows = min(target_rows, capacity)

        raw_table = tables[raw_name]
        has_source_payload = any(
            column.name.lower() == "source_payload" and column.data_type.lower() in {"json", "jsonb"}
            for column in raw_table.columns
        )
        table_profiles[raw_name] = {
            "category": category,
            "target_rows": max(1, target_rows),
            "mapped_staging_tables": mapped_staging,
            "business_keys": _business_key_columns(representative),
            "payload_columns": _payload_columns(representative) if has_source_payload else [],
            "required_payload_columns": _required_payload_columns(representative) if has_source_payload else [],
            "has_source_payload": has_source_payload,
        }
        raw_counts[raw_name] = max(1, target_rows)

    table_row_counts = dict(raw_counts)
    for raw_name, staging_names in raw_to_staging.items():
        for staging_name in staging_names:
            table_row_counts[staging_name] = raw_counts[raw_name]

    for dimension_name in dimensions:
        source_counts = [
            table_row_counts[source]
            for source in lineage.get(dimension_name, [])
            if source in table_row_counts
        ]
        table_row_counts[dimension_name] = max(source_counts) if source_counts else max(1, int(math.ceil(base_rows * 0.60)))

    for fact_name in facts:
        primary_source = pipeline_plan.get("primary_sources", {}).get(fact_name)
        if primary_source in table_row_counts:
            table_row_counts[fact_name] = table_row_counts[primary_source]
        else:
            source_counts = [
                table_row_counts[source]
                for source in lineage.get(fact_name, [])
                if source in table_row_counts and source in staging_tables
            ]
            table_row_counts[fact_name] = source_counts[0] if source_counts else base_rows

    for table in model.tables:
        table_row_counts.setdefault(table.name, base_rows)
        capacity = _unique_capacity(table)
        if capacity is not None:
            table_row_counts[table.name] = min(table_row_counts[table.name], capacity)

    relationships = []
    for child_name in staging_tables:
        child_table = tables[child_name]
        child_raw = _resolve_raw_source(child_name, pipeline_plan)
        if not child_raw:
            continue
        for fk in child_table.foreign_keys:
            parent_raw = _resolve_raw_source(fk.parent_table, pipeline_plan)
            if not parent_raw or parent_raw == child_raw:
                continue
            relationships.append({
                "child_raw_table": child_raw,
                "parent_raw_table": parent_raw,
                "child_staging_table": child_name,
                "parent_table": fk.parent_table,
                "child_columns": list(fk.child_columns),
                "parent_columns": list(fk.parent_columns),
                "one_to_one": _fk_is_one_to_one(child_table, fk),
                "require_reuse": (
                    raw_counts.get(child_raw, 0) > raw_counts.get(parent_raw, 0)
                    and not _fk_is_one_to_one(child_table, fk)
                ),
            })

    return {
        "base_event_rows": base_rows,
        "date_span_days": max(30, min(365, base_rows * 4)),
        "raw_table_row_counts": raw_counts,
        "table_row_counts": table_row_counts,
        "table_profiles": table_profiles,
        "relationships": relationships,
        "quality_targets": {
            "reuse_parent_entities": True,
            "non_uniform_parent_distribution": True,
            "multiple_children_per_parent_when_allowed": True,
            "reconcile_derived_measures": True,
            "respect_all_ddl_constraints": True,
        },
    }
