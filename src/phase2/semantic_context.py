from dataclasses import dataclass, field
import re

GENERIC_STOPWORDS = {
    "and", "the", "for", "with", "from", "that", "this", "into", "over", "under",
    "business", "data", "model", "models", "analytics", "reporting", "dashboard",
    "system", "platform", "table", "tables", "entity", "entities", "attribute", "attributes",
    "requirement", "requirements", "process", "processes", "manage", "track", "analysis",
}

SEMANTIC_TOKEN_MAP = {
    "email": {"email", "e_mail"},
    "phone": {"phone", "mobile", "telephone", "contact_number"},
    "address": {"address", "street"},
    "city": {"city"},
    "country": {"country"},
    "state": {"state", "province"},
    "postal_code": {"postal", "postcode", "zip"},
    "person_name": {"person_name", "customer_name", "employee_name", "patient_name", "member_name", "contact_name", "first_name", "last_name"},
    "company_name": {"company", "organization", "organisation", "vendor", "supplier", "employer"},
    "product_or_service": {"product", "item", "service", "offering"},
    "brand": {"brand", "maker"},
    "status": {"status", "state_code"},
    "category": {"category", "type", "segment", "class"},
    "method": {"method", "channel", "mode"},
    "amount": {"amount", "total", "revenue", "balance", "salary", "premium"},
    "price": {"price", "cost", "fee", "rate"},
    "quantity": {"quantity", "count", "number", "units"},
    "percentage": {"percentage", "percent", "ratio", "score"},
    "date": {"date", "day"},
    "timestamp": {"time", "timestamp", "created_at", "updated_at", "loaded_at"},
    "boolean": {"flag", "is", "has", "active"},
    "lineage": {"source", "batch", "file", "ingestion"},
    "json": {"payload", "metadata", "config", "preferences"},
}


@dataclass
class ColumnSemantic:
    table_name: str
    column_name: str
    semantic_type: str
    confidence: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class SemanticContext:
    business_name: str = ""
    business_type: str = ""
    business_description: str = ""
    domain_terms: list[str] = field(default_factory=list)
    entity_terms: list[str] = field(default_factory=list)
    table_roles: dict[str, str] = field(default_factory=dict)
    column_semantics: dict[tuple[str, str], ColumnSemantic] = field(default_factory=dict)

    def semantic_for(self, table_name, column_name):
        return self.column_semantics.get((table_name, column_name))


def _flatten_text(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {_flatten_text(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _tokens(text):
    return [token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", text or "")]


def _important_terms(text, limit=12):
    seen = []
    for token in _tokens(text):
        if token in GENERIC_STOPWORDS or token in seen:
            continue
        seen.append(token)
        if len(seen) >= limit:
            break
    return seen


def _table_role(table_name):
    name = table_name.lower()
    if name.startswith("load_") or ".load_" in name:
        return "raw_load"
    if name.startswith("stg_") or ".stg_" in name:
        return "staging"
    if name.startswith("dim_") or ".dim_" in name:
        return "dimension"
    if name.startswith("fact_") or ".fact_" in name:
        return "fact"
    return "operational"


def _infer_semantic_type(table, column):
    name = column.name.lower()
    dtype = column.data_type.lower()
    parts = set(name.split("_")) | {name}
    reasons = []

    if column.is_primary_key:
        reasons.append("primary key")
        if name == "date_key" or name.endswith("_date_key"):
            return "date_key", 0.99, reasons
        if name.endswith("_id"):
            return "business_key", 0.95, reasons
        return "surrogate_key", 0.95, reasons
    if any(fk_col == column.name for fk in table.foreign_keys for fk_col in fk.child_columns):
        reasons.append("foreign key")
        return "foreign_key", 0.95, reasons
    if "json" in dtype:
        return "json", 0.95, ["json data type"]
    if name == "date_key" or name.endswith("_date_key"):
        return "date_key", 0.95, ["date key name"]
    if name.endswith("_id"):
        return "business_key", 0.9, ["business id suffix"]

    for semantic_type, tokens in SEMANTIC_TOKEN_MAP.items():
        if name in tokens or parts.intersection(tokens) or any(token in name for token in tokens if len(token) > 3):
            return semantic_type, 0.85, [f"matched {semantic_type} token"]

    if any(token in dtype for token in ["numeric", "decimal", "double", "float", "real"]):
        return "amount", 0.55, ["numeric data type"]
    if any(token in dtype for token in ["int", "serial"]):
        return "integer", 0.55, ["integer data type"]
    if "bool" in dtype:
        return "boolean", 0.8, ["boolean data type"]
    if "date" in dtype:
        return "date", 0.8, ["date data type"]
    if "timestamp" in dtype or "time" in dtype:
        return "timestamp", 0.8, ["time data type"]
    if any(token in dtype for token in ["char", "text"]):
        return "text", 0.45, ["text data type"]
    return "unknown", 0.2, ["no strong semantic match"]


def build_semantic_context(business_input, model):
    business_input = business_input or {}
    business_name = str(business_input.get("business_name") or "")
    business_type = str(business_input.get("business_type") or "")
    description = " ".join([
        str(business_input.get("business_description") or ""),
        str(business_input.get("model_purpose") or ""),
        _flatten_text(business_input.get("business_processes")),
        _flatten_text(business_input.get("reporting_requirements")),
    ])
    entity_text = _flatten_text(business_input.get("entities")) + " " + _flatten_text(business_input.get("relationships"))
    context = SemanticContext(
        business_name=business_name,
        business_type=business_type,
        business_description=description,
        domain_terms=_important_terms(" ".join([business_name, business_type, description])),
        entity_terms=_important_terms(entity_text),
    )
    for table in model.tables:
        context.table_roles[table.name] = _table_role(table.name)
        for column in table.columns:
            semantic_type, confidence, reasons = _infer_semantic_type(table, column)
            context.column_semantics[(table.name, column.name)] = ColumnSemantic(
                table_name=table.name,
                column_name=column.name,
                semantic_type=semantic_type,
                confidence=confidence,
                reasons=reasons,
            )
    return context


class SemanticGenerationProvider:
    """Extensible hook for future optional AI-assisted semantic generation.

    The default implementation is intentionally offline and deterministic. A
    future adapter can implement this interface without changing the generator.
    """

    def generate_text(self, semantic_type, context, table_name, column_name, index):
        return None
