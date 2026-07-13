import re

LAYER_PREFIXES = ("load_", "raw_", "stg_", "dim_", "fact_")


def table_layer(table_name):
    name = table_name.lower()
    if name.startswith("load_") or name.startswith("raw_") or name.endswith("_raw"):
        return "raw"
    if name.startswith("stg_"):
        return "staging"
    if name.startswith("dim_"):
        return "dimension"
    if name.startswith("fact_"):
        return "fact"
    return "other"


def entity_name(table_name):
    name = table_name.lower()
    for prefix in LAYER_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    if name.endswith("_raw"):
        name = name[:-4]
    return name


def business_key_columns(table):
    return [
        column.name for column in table.columns
        if column.name.lower().endswith("_id") and not column.name.lower().endswith("_key")
    ]


def surrogate_key_columns(table):
    return [column.name for column in table.columns if column.name.lower().endswith("_key")]


def shared_columns(left, right, include_keys=True):
    right_names = set(right.column_names())
    shared = []
    for column in left.columns:
        name = column.name
        lowered = name.lower()
        if name not in right_names:
            continue
        if not include_keys and (lowered.endswith("_key") or lowered.endswith("_id")):
            continue
        shared.append(name)
    return shared


def analyze_lineage(model):
    entities = {}
    facts = []
    for table in model.tables:
        layer = table_layer(table.name)
        if layer == "fact":
            facts.append(table)
            continue
        entities.setdefault(entity_name(table.name), {})[layer] = table
    mappings = {
        "entities": entities,
        "raw_to_staging": [],
        "staging_to_dimension": [],
        "fact_to_dimension": [],
    }
    for entity, layers in entities.items():
        raw = layers.get("raw")
        staging = layers.get("staging")
        dimension = layers.get("dimension")
        if raw and staging:
            mappings["raw_to_staging"].append({"entity": entity, "source": raw, "target": staging})
        if staging and dimension:
            mappings["staging_to_dimension"].append({"entity": entity, "source": staging, "target": dimension})
    dimensions = [layers["dimension"] for layers in entities.values() if "dimension" in layers]
    for fact in facts:
        fact_columns = set(fact.column_names())
        for dimension in dimensions:
            dim_entity = entity_name(dimension.name)
            for dim_key in surrogate_key_columns(dimension):
                if dim_key in fact_columns:
                    dimension_business_keys = business_key_columns(dimension)
                    business_keys = [key for key in dimension_business_keys if key in fact_columns]
                    mappings["fact_to_dimension"].append({
                        "fact": fact,
                        "dimension": dimension,
                        "dimension_key": dim_key,
                        "business_keys": business_keys,
                        "dimension_business_keys": dimension_business_keys,
                        "entity": dim_entity,
                    })
    return mappings
