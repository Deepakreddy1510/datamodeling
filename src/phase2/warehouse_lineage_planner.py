from dataclasses import dataclass, field

from .lineage_mapper import analyze_lineage, business_key_columns, entity_name, surrogate_key_columns, table_layer


@dataclass
class WarehouseLineagePlan:
    raw_tables: list = field(default_factory=list)
    staging_tables: list = field(default_factory=list)
    dimension_tables: list = field(default_factory=list)
    fact_tables: list = field(default_factory=list)
    entities: dict = field(default_factory=dict)
    raw_to_staging: list = field(default_factory=list)
    staging_to_dimension: list = field(default_factory=list)
    fact_to_dimension: list = field(default_factory=list)

    def stats(self):
        return {
            "warehouse_generation_mode": "lineage-aware",
            "lineage_entities": sorted(self.entities.keys()),
            "lineage_raw_tables": [table.name for table in self.raw_tables],
            "lineage_staging_tables": [table.name for table in self.staging_tables],
            "lineage_dimension_tables": [table.name for table in self.dimension_tables],
            "lineage_fact_tables": [table.name for table in self.fact_tables],
            "lineage_raw_to_staging": [f"{item['source'].name} -> {item['target'].name}" for item in self.raw_to_staging],
            "lineage_staging_to_dimension": [f"{item['source'].name} -> {item['target'].name}" for item in self.staging_to_dimension],
            "lineage_fact_to_dimension": [f"{item['fact'].name}.{item['dimension_key']} -> {item['dimension'].name}.{item['dimension_key']}" for item in self.fact_to_dimension],
        }


def build_warehouse_lineage_plan(model):
    mappings = analyze_lineage(model)
    plan = WarehouseLineagePlan(
        entities=mappings["entities"],
        raw_to_staging=mappings["raw_to_staging"],
        staging_to_dimension=mappings["staging_to_dimension"],
        fact_to_dimension=mappings["fact_to_dimension"],
    )
    for table in model.tables:
        layer = table_layer(table.name)
        if layer == "raw":
            plan.raw_tables.append(table)
        elif layer == "staging":
            plan.staging_tables.append(table)
        elif layer == "dimension":
            plan.dimension_tables.append(table)
        elif layer == "fact":
            plan.fact_tables.append(table)
    return plan
