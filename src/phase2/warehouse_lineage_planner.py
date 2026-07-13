from dataclasses import dataclass, field

from .lineage_mapper import analyze_lineage, business_key_columns, entity_name, table_layer


GENERIC_EVENT_TOKENS = {"order", "item", "line", "transaction", "payment", "delivery", "booking", "trip", "event", "sale", "sales"}
MEASURE_TOKENS = {"amount", "quantity", "count", "price", "total", "duration", "revenue", "cost", "fee"}


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
    fact_sources: dict = field(default_factory=dict)

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
            "lineage_fact_sources": [f"{fact} <- {source.name}" for fact, source in sorted(self.fact_sources.items())],
        }


def _tokens(name):
    return {token for token in name.lower().replace("_", " ").split() if token}


def _measure_columns(table):
    return {
        column.name for column in table.columns
        if any(token in column.name.lower() for token in MEASURE_TOKENS)
    }


def _score_fact_source(fact, staging, dimensions):
    fact_tokens = _tokens(entity_name(fact.name)) | _tokens(fact.name)
    staging_tokens = _tokens(entity_name(staging.name)) | _tokens(staging.name)
    fact_columns = set(fact.column_names())
    staging_columns = set(staging.column_names())
    score = len(fact_tokens & staging_tokens) * 4
    score += len((fact_tokens & GENERIC_EVENT_TOKENS) & staging_tokens) * 3
    score += len(fact_columns & staging_columns) * 3
    score += len(_measure_columns(fact) & _measure_columns(staging)) * 4
    staging_business_keys = set(business_key_columns(staging))
    for dimension in dimensions:
        dim_business_keys = set(business_key_columns(dimension))
        if dim_business_keys & staging_business_keys and any(key.replace("_id", "_key") in fact_columns for key in dim_business_keys):
            score += 5
    return score


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
    dimensions = plan.dimension_tables
    for fact in plan.fact_tables:
        scored = [( _score_fact_source(fact, staging, dimensions), staging) for staging in plan.staging_tables]
        scored = [(score, staging) for score, staging in scored if score > 0]
        if scored:
            scored.sort(key=lambda item: item[0], reverse=True)
            plan.fact_sources[fact.name] = scored[0][1]
    return plan
