from model_intent_detector import detect_model_intent


def test_reporting_yaml_infers_analytical_data_warehouse():
    data = {
        "business_description": "FreshCart wants analytics for customers, products, and stores.",
        "model_purpose": "Create reporting dashboards and KPI analysis.",
        "reporting_requirements": ["Sales analysis by store and product"],
        "expected_output": ["SQL DDL", "Data Dictionary"],
    }
    intent = detect_model_intent(data)
    assert intent["model_type"] == "analytical_data_warehouse"
    assert intent["modeling_style"] == "dimensional_model"
    assert "fact" in intent["required_layers"]


def test_operational_only_yaml_infers_operational_model():
    data = {
        "business_description": "Application CRUD storage for customer records.",
        "model_purpose": "Support transactional application storage.",
        "reporting_requirements": [],
        "expected_output": ["SQL DDL"],
    }
    intent = detect_model_intent(data)
    assert intent["model_type"] == "operational_model"
    assert intent["required_layers"] == ["operational"]


def test_explicit_target_model_type_is_respected():
    intent = detect_model_intent({"target_model_type": "operational_model", "reporting_requirements": ["Dashboard"]})
    assert intent["model_type"] == "operational_model"


def test_missing_optional_fields_do_not_fail():
    intent = detect_model_intent({"business_description": "Small app"})
    assert intent["model_type"] in {"operational_model", "analytical_data_warehouse"}
