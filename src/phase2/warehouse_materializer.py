from .lineage_mapper import business_key_columns, shared_columns


TECHNICAL_TOKENS = {
    "load_id", "source_load_id", "batch_id", "loaded_at", "created_at", "updated_at",
    "ingestion_timestamp", "validation_status", "data_quality_status", "row_hash",
}


def is_technical_column(column_name):
    lowered = column_name.lower()
    return lowered in TECHNICAL_TOKENS or lowered.endswith("_hash") or lowered.startswith("audit_")


def materialize_lineage_row(table, row, index, generated, plan, stats, finalize_row, apply_derivation):
    """Apply deterministic warehouse materialization before a row is stored."""
    apply_derivation(table, row, index, generated, {
        "entities": plan.entities,
        "raw_to_staging": plan.raw_to_staging,
        "staging_to_dimension": plan.staging_to_dimension,
        "fact_to_dimension": plan.fact_to_dimension,
    }, stats)
    finalize_row(table, row, index, stats)
    return row
