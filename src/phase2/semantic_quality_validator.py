import re

PLACEHOLDER_RE = re.compile(r"^(?:[A-Z][A-Za-z_]*(?:\s+[A-Z][A-Za-z_]*)?|Record|Value|Entity|Unknown)\s+\d{3,6}$")
SEMANTIC_BLOCKLIST_ROLES = {
    "person_name", "company_name", "organization_name", "product_name", "service_name",
    "product_or_service", "date", "birth_date", "timestamp", "country", "nationality",
    "city", "region", "status", "category", "type", "method", "role", "position",
    "amount", "price", "quantity", "count", "score", "rank", "percentage", "boolean", "description",
}
ALLOWED_IDENTIFIER_ROLES = {"identifier", "business_key", "surrogate_key", "foreign_key", "date_key"}


def is_semantic_placeholder(value):
    return isinstance(value, str) and bool(PLACEHOLDER_RE.fullmatch(value.strip()))


def validate_semantic_quality(model, data, semantic_context=None):
    errors = []
    checked = 0
    for table in model.tables:
        for column in table.columns:
            semantic = semantic_context.semantic_for(table.name, column.name) if semantic_context else None
            role = semantic.semantic_type if semantic else ""
            name = column.name.lower()
            role_is_semantic = role in SEMANTIC_BLOCKLIST_ROLES or any(t in name for t in ["name", "date", "status", "category", "type", "method", "country", "city", "role", "position", "amount", "price", "quantity", "count", "description"])
            if role in ALLOWED_IDENTIFIER_ROLES or not role_is_semantic:
                continue
            for idx, row in enumerate(data.get(table.name, []), start=1):
                checked += 1
                value = row.get(column.name)
                if is_semantic_placeholder(value):
                    errors.append(f"{table.name}.{column.name} row {idx}: semantic placeholder value {value!r} is not allowed.")
                    break
    return {"status": "failed" if errors else "passed", "errors": errors, "checked_values": checked}
