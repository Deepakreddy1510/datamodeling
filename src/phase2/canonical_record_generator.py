from .warehouse_lineage_planner import build_warehouse_lineage_plan
from .lineage_mapper import business_key_columns, shared_columns


class CanonicalRecordGenerator:
    """Builds canonical source-record groups from already generated source layers.

    This class is intentionally metadata-driven: it groups records by normalized
    entity name and preserves source/raw rows as the canonical records that later
    layers derive from.
    """

    def __init__(self, model):
        self.plan = build_warehouse_lineage_plan(model)

    def from_generated_sources(self, data):
        canonical = {}
        for entity, layers in self.plan.entities.items():
            source = layers.get("raw") or layers.get("staging") or layers.get("dimension")
            if source is not None:
                canonical[entity] = [dict(row) for row in data.get(source.name, [])]
        return canonical
