from .warehouse_lineage_planner import build_warehouse_lineage_plan


class CanonicalRecordGenerator:
    """Generates canonical source/event records before warehouse materialization."""

    def __init__(self, model, plan=None):
        self.model = model
        self.plan = plan or build_warehouse_lineage_plan(model)

    def generate(self, rows_per_table, value_factory, finalize_row):
        canonical = {}
        for entity, layers in self.plan.entities.items():
            source = layers.get("raw") or layers.get("staging") or layers.get("dimension")
            if source is None:
                continue
            canonical[entity] = self._generate_for_table(source, rows_per_table, value_factory, finalize_row)
        for fact_name, source in self.plan.fact_sources.items():
            entity = source.name.lower()
            if entity not in canonical:
                canonical[entity] = self._generate_for_table(source, rows_per_table, value_factory, finalize_row)
        return canonical

    def from_codex_payload(self, payload):
        records = payload.get("canonical_records") if isinstance(payload, dict) else None
        if not isinstance(records, dict):
            raise ValueError("Codex JSON must contain a 'canonical_records' object.")
        return {str(entity): [dict(row) for row in rows if isinstance(row, dict)] for entity, rows in records.items() if isinstance(rows, list)}

    def from_python_generation(self, data):
        canonical = {}
        for entity, layers in self.plan.entities.items():
            source = layers.get("raw") or layers.get("staging") or layers.get("dimension")
            if source is not None:
                canonical[entity] = [dict(row) for row in data.get(source.name, [])]
        return canonical

    def _generate_for_table(self, table, rows_per_table, value_factory, finalize_row):
        rows = []
        for index in range(1, rows_per_table + 1):
            row = {column.name: value_factory(table, column, index) for column in table.columns}
            finalize_row(table, row, index)
            rows.append(row)
        return rows
