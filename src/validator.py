REQUIRED_FIELDS = [
    "business_name",
    "business_type",
    "business_description",
    "model_purpose",
    "main_business_processes",
    "key_business_entities",
    "business_relationships",
    "expected_output",
]

TARGET_DATABASE_FIELDS = [
    "target_database",
    "target_operational_database",
    "target_database_selection",
]


def is_present(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def validate_required_fields(data):
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in data or not is_present(data.get(field)):
            errors.append({"field": field, "message": "Required field is missing or empty."})

    if not any(is_present(data.get(field)) for field in TARGET_DATABASE_FIELDS):
        errors.append({
            "field": "target_database / target_operational_database / target_database_selection",
            "message": "At least one target database field is required and must be non-empty.",
        })

    return {"status": "valid" if not errors else "validation_failed", "errors": errors, "is_valid": not errors}
