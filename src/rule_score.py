from validator import is_present

SCORING_WEIGHTS = [
    ("business_name", 5),
    ("business_type", 5),
    ("business_description", 10),
    ("model_purpose", 10),
    ("main_business_processes", 10),
    ("key_business_entities", 15),
    ("business_relationships", 15),
    ("entity_attributes", 15),
    ("reporting_requirements", 5),
    ("expected_output", 5),
]

TARGET_DATABASE_FIELDS = ["target_database", "target_operational_database", "target_database_selection"]
TARGET_DATABASE_LABEL = "target_database / target_operational_database / target_database_selection"


def calculate_rule_based_score(data):
    score = 0
    missing_sections = []

    for field, points in SCORING_WEIGHTS:
        if is_present(data.get(field)):
            score += points
        else:
            missing_sections.append(field)

    if any(is_present(data.get(field)) for field in TARGET_DATABASE_FIELDS):
        score += 5
    else:
        missing_sections.append(TARGET_DATABASE_LABEL)

    return {
        "rule_based_score": score,
        "missing_sections": missing_sections,
        "scoring_formula": "Presence-based weighted score out of 100",
    }
