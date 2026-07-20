ANALYTICAL_KEYWORDS = [
    "reporting", "analytics", "dashboard", "kpi", "trend", "performance", "sales analysis",
    "demand analysis", "customer behavior", "payment analysis", "delivery analysis", "star schema",
    "dimensional model", "fact table", "dimension table", "staging table", "load table",
    "warehouse", "data warehouse", "data mart", "bi",
]
OPERATIONAL_KEYWORDS = ["crud", "transaction storage", "application", "operational", "oltp", "transactional"]
WAREHOUSE_LAYERS = ["raw_load", "staging", "dimension", "fact", "reporting"]


def _flatten(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {_flatten(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return str(value)


def _normalize_model_type(value):
    normalized = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "analytics": "analytical_data_warehouse",
        "analytical": "analytical_data_warehouse",
        "warehouse": "analytical_data_warehouse",
        "data_warehouse": "analytical_data_warehouse",
        "dimensional": "dimensional_model",
        "star": "star_schema",
        "oltp": "operational_model",
        "operational": "operational_model",
    }
    return aliases.get(normalized, normalized or None)


def _as_layers(value, default):
    if not value:
        return list(default)
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return list(default)


def detect_model_intent(data):
    explicit_model_type = _normalize_model_type(data.get("target_model_type"))
    explicit_style = data.get("modeling_style")
    explicit_layers = data.get("required_layers")

    text = " ".join(
        _flatten(data.get(field))
        for field in [
            "business_description", "model_purpose", "main_business_processes", "key_business_entities",
            "business_relationships", "reporting_requirements", "expected_output",
        ]
    ).lower()
    reporting_present = bool(data.get("reporting_requirements"))
    analytical_match = any(keyword in text for keyword in ANALYTICAL_KEYWORDS)
    operational_match = any(keyword in text for keyword in OPERATIONAL_KEYWORDS)

    if explicit_model_type:
        model_type = explicit_model_type
        reason = "target_model_type was explicitly provided."
        confidence = "high"
    elif analytical_match or reporting_present:
        model_type = "analytical_data_warehouse"
        reason = "Reporting and analytics requirements are present."
        confidence = "high" if analytical_match else "medium"
    elif operational_match:
        model_type = "operational_model"
        reason = "Input appears focused on transactional storage."
        confidence = "medium"
    else:
        model_type = "operational_model"
        reason = "No analytical/reporting intent was detected; preserving operational behavior."
        confidence = "low"

    if model_type in {"analytical_data_warehouse", "dimensional_model", "star_schema"}:
        modeling_style = explicit_style or ("star_schema" if model_type == "star_schema" else "dimensional_model")
        required_layers = _as_layers(explicit_layers, WAREHOUSE_LAYERS)
        fact_dimension_required = data.get("fact_dimension_inference_required", True)
    else:
        modeling_style = explicit_style or "normalized_relational"
        required_layers = _as_layers(explicit_layers, ["operational"])
        fact_dimension_required = data.get("fact_dimension_inference_required", False)

    return {
        "model_type": model_type,
        "modeling_style": modeling_style,
        "required_layers": required_layers,
        "fact_dimension_inference_required": bool(fact_dimension_required),
        "confidence": confidence,
        "reason": reason,
    }
