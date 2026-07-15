import re

DIMENSION_HINTS = {
    "customer": "dim_customer", "product": "dim_product", "store": "dim_store", "supplier": "dim_supplier",
    "vehicle": "dim_vehicle", "location": "dim_location", "city": "dim_location", "country": "dim_location",
    "campaign": "dim_campaign", "channel": "dim_channel", "payment method": "dim_payment_method",
    "delivery partner": "dim_delivery_partner", "browser": "dim_browser", "device": "dim_device",
}
FACT_HINTS = {
    "order": ("fact_sales", "one row per order item"),
    "order item": ("fact_sales", "one row per order item"),
    "salesorder": ("fact_sales", "one row per order item"),
    "sales order": ("fact_sales", "one row per order item"),
    "payment": ("fact_payment", "one row per payment transaction"),
    "delivery": ("fact_delivery", "one row per delivery record"),
    "web session": ("fact_web_session", "one row per web session"),
    "session": ("fact_web_session", "one row per web session"),
    "lead": ("fact_lead_funnel", "one row per lead/funnel stage event"),
    "funnel": ("fact_lead_funnel", "one row per lead/funnel stage event"),
    "inventory snapshot": ("fact_inventory_snapshot", "one row per product/location/date snapshot"),
    "purchase order": ("fact_purchase_order", "one row per purchase order line"),
    "return": ("fact_return", "one row per return transaction"),
    "claim": ("fact_claim", "one row per claim"),
    "invoice": ("fact_invoice", "one row per invoice"),
    "transaction": ("fact_transaction", "one row per transaction"),
}
MEASURE_HINTS = [
    "quantity", "unit_price", "line_total_amount", "order_total_amount", "payment_amount",
    "delivery_delay_minutes", "session_count", "lead_count", "stock_quantity", "amount", "price", "total",
]


def _snake(name):
    text = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", str(name))
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text or "entity"


def _entities(data):
    entities = data.get("key_business_entities") or []
    if isinstance(entities, dict):
        entities = list(entities.keys())
    return [str(entity) for entity in entities]


def _attributes(data):
    attributes = data.get("entity_attributes") or {}
    if not isinstance(attributes, dict):
        return []
    values = []
    for attrs in attributes.values():
        if isinstance(attrs, list):
            values.extend(str(attr) for attr in attrs)
    return values


def _add_unique(items, item):
    if item not in items:
        items.append(item)


def _infer_dimensions(entities, attributes):
    dimensions = []
    for entity in entities:
        normalized = _snake(entity).replace("_", " ")
        for hint, table in DIMENSION_HINTS.items():
            if hint in normalized:
                _add_unique(dimensions, table)
    if any("date" in attr.lower() or "time" in attr.lower() for attr in attributes):
        _add_unique(dimensions, "dim_date")
    return dimensions


def _infer_facts(entities, text):
    facts = []
    grains = {}
    combined = " ".join([text] + entities).lower()
    for hint, (fact, grain) in FACT_HINTS.items():
        if hint in combined:
            _add_unique(facts, fact)
            grains[fact] = grain
    return facts, grains


def _infer_measures(attributes, reporting_text):
    measures = []
    combined = " ".join(attributes + [reporting_text]).lower()
    for measure in MEASURE_HINTS:
        if measure in combined:
            _add_unique(measures, measure)
    if "sales" in combined:
        _add_unique(measures, "order_total_amount")
    if "payment" in combined:
        _add_unique(measures, "payment_amount")
    return measures or ["record_count"]


def build_model_blueprint(data, model_intent):
    model_type = model_intent.get("model_type", "operational_model")
    modeling_style = model_intent.get("modeling_style", "normalized_relational")
    required_layers = model_intent.get("required_layers", ["operational"])
    entities = _entities(data)
    attributes = _attributes(data)

    if model_type == "operational_model":
        return {
            "model_type": "operational_model",
            "modeling_style": modeling_style,
            "required_layers": required_layers,
            "operational_entities": [_snake(entity) for entity in entities],
            "assumptions": ["Operational model requested or inferred; dimensional warehouse layers were not forced."],
        }

    reporting_text = " ".join(str(item) for item in data.get("reporting_requirements", []))
    all_text = " ".join([reporting_text, str(data.get("model_purpose", "")), " ".join(entities)])
    load_tables = [f"load_{_snake(entity)}_raw" for entity in entities] if "raw_load" in required_layers else []
    staging_tables = [f"stg_{_snake(entity)}" for entity in entities] if "staging" in required_layers else []
    dimensions = _infer_dimensions(entities, attributes)
    facts, grains = _infer_facts(entities, all_text)
    measures = _infer_measures(attributes, reporting_text)
    dimension_keys = [table.replace("dim_", "") + "_key" for table in dimensions]

    return {
        "model_type": model_type,
        "modeling_style": modeling_style,
        "required_layers": required_layers,
        "inferred_load_tables": load_tables,
        "inferred_staging_tables": staging_tables,
        "inferred_dimension_tables": dimensions,
        "inferred_fact_tables": facts,
        "fact_grains": grains,
        "suggested_measures": measures,
        "suggested_dimension_keys": dimension_keys,
        "source_to_target_mapping_summary": [
            f"{entity} -> load_{_snake(entity)}_raw -> stg_{_snake(entity)}" for entity in entities
        ],
        "assumptions": [
            "Technical warehouse tables are inferred from business entities and reporting requirements.",
            "Surrogate keys are recommended for dimensions and facts should reference dimensions by keys.",
        ],
    }
