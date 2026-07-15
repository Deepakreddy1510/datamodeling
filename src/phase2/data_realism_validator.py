from __future__ import annotations

from collections import Counter
from datetime import date, datetime


TECHNICAL_COLUMNS = {
    "batch_id", "load_id", "load_row_id", "source_payload", "source_file",
    "source_file_name", "source_system", "loaded_at", "staged_at", "created_at", "updated_at",
}


def _normalized(value):
    if isinstance(value, datetime):
        return value.date()
    return value


def validate_data_realism(model, data: dict, generation_profile: dict | None = None) -> dict:
    """Run generic realism checks without encoding any business-domain names."""
    errors = []
    warnings = []
    checks = []
    profile = generation_profile or {}

    # Date diversity across the generated warehouse.
    dates = []
    for table in model.tables:
        for row in data.get(table.name, []):
            for column in table.columns:
                value = _normalized(row.get(column.name))
                if isinstance(value, date):
                    dates.append(value)
    if dates:
        span = (max(dates) - min(dates)).days
        checks.append(f"Temporal span: {span} days across {len(set(dates))} distinct dates.")
        requested_span = int(profile.get("date_span_days", 0) or 0)
        minimum = min(requested_span, 30) if requested_span else 7
        if span < minimum and len(dates) >= 10:
            warnings.append(f"Generated dates span only {span} days; target was at least {minimum} days.")

    tables = {table.name: table for table in model.tables}
    for table in model.tables:
        rows = data.get(table.name, [])
        for fk in table.foreign_keys:
            parent = tables.get(fk.parent_table)
            if parent is None or not rows:
                continue
            parent_rows = data.get(parent.name, [])
            raw_child_values = [
                tuple(row.get(column) for column in fk.child_columns)
                for row in rows
            ]
            # PostgreSQL MATCH SIMPLE semantics: a foreign key is not checked when
            # any component is NULL. Nullable date/role keys (for example an
            # actual-date key for an in-progress event) are therefore valid and
            # must not be reported as unresolved relationships.
            child_values = [
                value
                for value in raw_child_values
                if not any(component in (None, "") for component in value)
            ]
            nullable_count = len(raw_child_values) - len(child_values)
            parent_values = {
                tuple(row.get(column) for column in fk.parent_columns)
                for row in parent_rows
            }
            missing = [value for value in child_values if value not in parent_values]
            if missing:
                errors.append(
                    f"{table.name} has {len(missing)} rows whose FK {', '.join(fk.child_columns)} "
                    f"does not resolve to {parent.name}."
                )
                continue
            counts = Counter(child_values)
            repeated = sum(1 for count in counts.values() if count > 1)
            nullable_note = (
                f", {nullable_count} nullable FK row(s) skipped"
                if nullable_count
                else ""
            )
            checks.append(
                f"{table.name} -> {parent.name}: {len(rows)} child rows, "
                f"{len(counts)} referenced parents, {repeated} reused parents"
                f"{nullable_note}."
            )
            if len(child_values) > len(parent_rows) and repeated == 0:
                warnings.append(
                    f"{table.name} has more rows than {parent.name} but no parent key is reused; "
                    "the relationship looks artificially one-to-one."
                )

    # Flag suspiciously identical row counts across every analytical layer.
    nonempty_counts = [len(data.get(table.name, [])) for table in model.tables if data.get(table.name)]
    if len(nonempty_counts) >= 4 and len(set(nonempty_counts)) == 1 and nonempty_counts[0] > 1:
        warnings.append(
            "Every non-empty table has the same row count. This commonly indicates a trivial "
            "one-record-per-entity pattern instead of realistic relationship cardinality."
        )

    status = "failed" if errors else ("passed_with_warnings" if warnings else "passed")
    return {"status": status, "errors": errors, "warnings": warnings, "checks": checks}
