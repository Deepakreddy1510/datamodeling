from model_blueprint_builder import build_model_blueprint
from model_intent_detector import detect_model_intent


def freshcart_data():
    return {
        "business_description": "FreshCart retail analytics.",
        "model_purpose": "Create reporting and analytics data warehouse.",
        "key_business_entities": ["Customer", "Product", "Store", "Order", "Payment", "Delivery"],
        "entity_attributes": {
            "Order": ["order_id", "order_date", "quantity", "unit_price"],
            "Payment": ["payment_id", "payment_amount"],
        },
        "reporting_requirements": ["Sales, payment, and delivery performance dashboards"],
        "expected_output": ["SQL DDL", "Fact Tables", "Dimension Tables"],
    }


def test_freshcart_blueprint_infers_layers_dimensions_and_facts():
    data = freshcart_data()
    intent = detect_model_intent(data)
    blueprint = build_model_blueprint(data, intent)
    assert "load_customer_raw" in blueprint["inferred_load_tables"]
    assert "stg_customer" in blueprint["inferred_staging_tables"]
    assert "dim_customer" in blueprint["inferred_dimension_tables"]
    assert "dim_product" in blueprint["inferred_dimension_tables"]
    assert "dim_store" in blueprint["inferred_dimension_tables"]
    assert "dim_date" in blueprint["inferred_dimension_tables"]
    assert "fact_sales" in blueprint["inferred_fact_tables"]
    assert "fact_payment" in blueprint["inferred_fact_tables"]
    assert "fact_delivery" in blueprint["inferred_fact_tables"]


def test_operational_blueprint_does_not_force_warehouse_layers():
    data = {"key_business_entities": ["Customer", "Order"], "target_model_type": "operational_model"}
    intent = detect_model_intent(data)
    blueprint = build_model_blueprint(data, intent)
    assert blueprint["model_type"] == "operational_model"
    assert "inferred_fact_tables" not in blueprint
