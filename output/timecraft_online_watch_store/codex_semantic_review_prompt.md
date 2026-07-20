# Codex Semantic Review

You are a Senior Enterprise Data Architect.

Review the canonical business input JSON and evaluate whether it is semantically complete enough to generate a conceptual, logical, and physical data model.

Do NOT generate the data model in this step.

Return strict JSON only. Do not include markdown code fences, commentary, or explanations outside JSON.

## Canonical Business Input JSON

```json
{
  "business_description": "TimeCraft is an online watch shopping platform where customers browse watches, compare brands and collections, place orders, make payments, receive shipments, request returns, and raise warranty claims. The business wants better visibility into sales, customer behaviour, product demand, inventory availability, payment outcomes, shipment performance, returns, refunds, and warranty service.\n\n\nThe physical PostgreSQL data warehouse must include a complete raw/load layer.\nFor every source business entity, create a raw load table using the pattern load_<entity>_raw.\nThe model must include these layers in order: load/raw tables, staging tables, dimension tables, fact tables, and reporting views.\nEvery staging table must be sourced from a matching load_<entity>_raw table.\nDo not skip the raw/load layer.\nDo not create only staging, dimension, and fact tables.",
  "business_name": "TimeCraft Online Watch Store",
  "business_relationships": [
    {
      "description": "One customer can place many orders.",
      "relationship_name": "Customer places Orders"
    },
    {
      "description": "One brand can have many collections.",
      "relationship_name": "Brand has Collections"
    },
    {
      "description": "One brand can have many watch products.",
      "relationship_name": "Brand has Watch Products"
    },
    {
      "description": "One collection can contain many watch products.",
      "relationship_name": "Collection has Watch Products"
    },
    {
      "description": "One warehouse can store inventory for many watch products.",
      "relationship_name": "Warehouse stores Inventory"
    },
    {
      "description": "One watch product can have inventory records across warehouses and dates.",
      "relationship_name": "Watch Product has Inventory"
    },
    {
      "description": "One order can contain many order items.",
      "relationship_name": "Order contains Order Items"
    },
    {
      "description": "One watch product can appear in many order items.",
      "relationship_name": "Watch Product appears in Order Items"
    },
    {
      "description": "One warehouse can fulfil many order items.",
      "relationship_name": "Warehouse fulfils Order Items"
    },
    {
      "description": "One order can have multiple payment transactions or attempts.",
      "relationship_name": "Order has Payments"
    },
    {
      "description": "One order can have one or more shipments.",
      "relationship_name": "Order has Shipments"
    },
    {
      "description": "One warehouse can dispatch many shipments.",
      "relationship_name": "Warehouse dispatches Shipments"
    },
    {
      "description": "One delivered order item can have zero or more return requests.",
      "relationship_name": "Order Item can have Return Requests"
    },
    {
      "description": "One delivered order item can have zero or more warranty claims.",
      "relationship_name": "Order Item can have Warranty Claims"
    }
  ],
  "business_rules": [
    "Every collection must belong to a valid brand",
    "Every watch product must belong to a valid brand and collection",
    "A watch product brand must match the brand of its collection",
    "Every inventory record must belong to a valid watch product and warehouse",
    "Available inventory quantity must equal on hand quantity minus reserved quantity",
    "Inventory quantities must not be negative",
    "Every order must belong to a valid customer",
    "Customer signup date must be on or before the order date",
    "Every order must contain at least one order item",
    "Every order item must belong to a valid order, watch product, and warehouse",
    "Order item quantity must be greater than zero",
    "Gross line amount must equal quantity multiplied by unit price",
    "Line net amount must equal gross line amount minus line discount amount",
    "Gross order amount must equal the sum of gross line amounts for the order",
    "Discount amount must equal the sum of line discount amounts for the order",
    "Net order amount must equal the sum of line net amounts for the order",
    "Successful payment transactions must not exceed the order net amount",
    "Payment date must be on or after the order date",
    "Shipment date must be on or after the order date",
    "Promised delivery date must be on or after the shipment date",
    "Delivered shipments must have an actual delivery date",
    "Undelivered shipments should have a null actual delivery date",
    "Delivery delay days must be zero or positive",
    "Return requests can only relate to delivered order items",
    "Return quantity must be greater than zero and must not exceed purchased quantity",
    "Refund amount must not exceed the returned quantity multiplied by unit price",
    "Warranty claims can only relate to delivered order items",
    "Warranty claim date must be within the product warranty period",
    "Service completion date cannot be earlier than service start date",
    "Warranty service cost must not be negative",
    "Active status fields must be boolean values",
    "All child records must resolve to valid parent records",
    "Fact foreign keys must resolve to valid dimension records",
    "Raw/load tables are mandatory for warehouse validation.",
    "Staging tables must preserve business keys and foreign keys from raw/load tables.",
    "The generated warehouse must support raw/load to staging to dimension/fact lineage validation."
  ],
  "business_type": "Online Watch Retail and E-Commerce",
  "entity_attributes": {
    "Brand": [
      "brand_id",
      "brand_name",
      "country_of_origin",
      "brand_tier",
      "is_active"
    ],
    "Collection": [
      "collection_id",
      "brand_id",
      "collection_name",
      "launch_year",
      "collection_status"
    ],
    "Customer": [
      "customer_id",
      "customer_name",
      "email",
      "phone",
      "city",
      "region",
      "customer_segment",
      "signup_date",
      "is_active"
    ],
    "Inventory": [
      "inventory_id",
      "product_id",
      "warehouse_id",
      "inventory_date",
      "on_hand_quantity",
      "reserved_quantity",
      "available_quantity",
      "reorder_level",
      "inventory_status"
    ],
    "Order": [
      "order_id",
      "customer_id",
      "order_date",
      "order_status",
      "order_channel",
      "gross_order_amount",
      "discount_amount",
      "net_order_amount"
    ],
    "Order Item": [
      "order_item_id",
      "order_id",
      "product_id",
      "warehouse_id",
      "quantity",
      "unit_price",
      "gross_line_amount",
      "line_discount_amount",
      "line_net_amount"
    ],
    "Payment": [
      "payment_id",
      "order_id",
      "payment_date",
      "payment_method",
      "payment_transaction_type",
      "payment_status",
      "payment_amount",
      "transaction_reference"
    ],
    "Return Request": [
      "return_id",
      "order_item_id",
      "return_quantity",
      "return_reason",
      "return_status",
      "requested_date",
      "approved_date",
      "refund_date",
      "refund_amount"
    ],
    "Shipment": [
      "shipment_id",
      "order_id",
      "warehouse_id",
      "tracking_number",
      "courier_partner",
      "shipment_date",
      "promised_delivery_date",
      "actual_delivery_date",
      "shipment_status",
      "delivery_delay_days"
    ],
    "Warehouse": [
      "warehouse_id",
      "warehouse_name",
      "city",
      "region",
      "warehouse_type",
      "is_active"
    ],
    "Warranty Claim": [
      "warranty_claim_id",
      "order_item_id",
      "claim_reason",
      "claim_status",
      "claim_date",
      "service_start_date",
      "service_completion_date",
      "service_cost_amount",
      "resolution_description"
    ],
    "Watch Product": [
      "product_id",
      "brand_id",
      "collection_id",
      "sku",
      "product_name",
      "watch_category",
      "gender_category",
      "movement_type",
      "strap_material",
      "dial_color",
      "case_size_mm",
      "water_resistance_metres",
      "unit_price",
      "warranty_months",
      "product_status"
    ]
  },
  "expected_output": [
    "Conceptual data model",
    "Logical data model",
    "Physical PostgreSQL data model",
    "SQL DDL scripts",
    "Table relationships",
    "Fact and dimension design",
    "Synthetic data generation support",
    "Excel output with sample synthetic data",
    "PostgreSQL loading support",
    "Raw/load PostgreSQL tables using load_<entity>_raw naming",
    "Staging tables sourced directly from matching raw/load tables",
    "Dimension tables loaded from staging master data",
    "Fact tables loaded from staging transaction data",
    "Reporting views built from dimensions and facts",
    "Validation-ready warehouse with raw_load, staging, dimension, fact, and reporting layers"
  ],
  "key_business_entities": [
    {
      "description": "A person who registers on the TimeCraft website and places watch orders.",
      "entity_name": "Customer"
    },
    {
      "description": "A fictional watch brand sold through the online store.",
      "entity_name": "Brand"
    },
    {
      "description": "A watch collection or product series belonging to a brand.",
      "entity_name": "Collection"
    },
    {
      "description": "A watch item available for customers to purchase.",
      "entity_name": "Watch Product"
    },
    {
      "description": "A fulfilment location that stores watches and dispatches shipments.",
      "entity_name": "Warehouse"
    },
    {
      "description": "Product stock availability recorded for a warehouse on a specific date.",
      "entity_name": "Inventory"
    },
    {
      "description": "A purchase request placed by a customer.",
      "entity_name": "Order"
    },
    {
      "description": "A watch product line item inside an order.",
      "entity_name": "Order Item"
    },
    {
      "description": "A payment transaction related to an order.",
      "entity_name": "Payment"
    },
    {
      "description": "Shipment and delivery tracking information for an order.",
      "entity_name": "Shipment"
    },
    {
      "description": "A customer request to return part or all of an order item.",
      "entity_name": "Return Request"
    },
    {
      "description": "A warranty service claim raised for a purchased watch.",
      "entity_name": "Warranty Claim"
    }
  ],
  "main_business_processes": [
    "Customer registration and profile management",
    "Brand and collection management",
    "Watch product catalogue management",
    "Inventory availability tracking",
    "Order placement",
    "Order item fulfilment",
    "Payment processing",
    "Shipment and delivery tracking",
    "Return and refund processing",
    "Warranty claim tracking",
    "Customer purchase history analysis",
    "Sales and product performance reporting"
  ],
  "model_purpose": "Create a data model that helps the business analyse customer orders, watch product sales, brand and collection performance, inventory availability, payment status, shipment outcomes, returns, refunds, and warranty claims. The model should support business reporting, operational analysis, synthetic data generation, Excel output, and PostgreSQL loading.\n\n\nThe physical PostgreSQL data warehouse must include a complete raw/load layer.\nFor every source business entity, create a raw load table using the pattern load_<entity>_raw.\nThe model must include these layers in order: load/raw tables, staging tables, dimension tables, fact tables, and reporting views.\nEvery staging table must be sourced from a matching load_<entity>_raw table.\nDo not skip the raw/load layer.\nDo not create only staging, dimension, and fact tables.",
  "physical_model_requirements": [
    "Create raw/load tables for every source entity using load_<entity>_raw naming.",
    "Create staging tables using stg_<entity> naming.",
    "Create dimension tables using dim_<entity> naming.",
    "Create fact tables using fact_<process> naming.",
    "Create reporting views for business reports.",
    "Every stg_ table must have a matching load_ raw table source.",
    "The DDL must contain load_ tables, stg_ tables, dim_ tables, fact_ tables, and reporting views.",
    "Do not omit the raw/load layer from the PostgreSQL DDL."
  ],
  "reporting_requirements": [
    {
      "description": "Show daily order count, quantity sold, gross sales, discounts, net sales, and average order value.",
      "report_name": "Daily Watch Sales Report"
    },
    {
      "description": "Show units sold, revenue, average selling price, and return rate by product, brand, collection, category, movement type, strap material, and dial color.",
      "report_name": "Product Performance Report"
    },
    {
      "description": "Show customer count, orders, revenue, average order value, and repeat purchases by customer segment, city, and region.",
      "report_name": "Customer Segment Report"
    },
    {
      "description": "Show revenue, units sold, average selling price, return rate, and warranty claim rate by brand and collection.",
      "report_name": "Brand and Collection Report"
    },
    {
      "description": "Show on hand, reserved, and available quantities, reorder risk, and inventory status by product, warehouse, and inventory date.",
      "report_name": "Inventory Availability Report"
    },
    {
      "description": "Show successful, failed, pending, and refunded payment transactions by payment method and order channel.",
      "report_name": "Payment Status Report"
    },
    {
      "description": "Show shipment count, delivered shipments, delayed shipments, average delivery delay, and courier performance.",
      "report_name": "Shipment Performance Report"
    },
    {
      "description": "Show return count, returned quantity, return reasons, refund amount, and return rate by product, brand, and category.",
      "report_name": "Return Analysis Report"
    },
    {
      "description": "Show claim count, claim reasons, service cost, resolution time, and claim status by product and brand.",
      "report_name": "Warranty Claim Report"
    }
  ],
  "synthetic_data_requirements": {
    "generation_engine": "codex-cli",
    "locale": "en_GB",
    "rows_per_table": 15,
    "value_quality_rules": [
      "Generate meaningful fictional customers, watch brands, collections, products, warehouses, couriers, and transaction values",
      "Do not use real watch companies or make factual claims about real brands",
      "Do not use placeholders such as Customer 001, Product 001, Brand 001, or Warehouse 001",
      "Reuse customers across multiple orders",
      "Reuse brands and collections across multiple products",
      "Generate multiple order items for most orders",
      "Reuse products across many order items",
      "Generate inventory records for products across multiple warehouses and dates",
      "Generate multiple payment attempts for some orders",
      "Generate multiple shipments for some multi warehouse orders",
      "Generate returns for only a minority of delivered order items",
      "Generate warranty claims for only a smaller minority of delivered order items",
      "Generate transactions across at least twelve months",
      "Keep payment, shipment, delivery, return, refund, and warranty dates in chronological order",
      "Keep related values logically consistent",
      "Avoid one to one patterns between master and transaction tables",
      "Do not create duplicate dimension history when tracked attributes have not changed",
      "Generate a continuous date dimension covering all required dates",
      "Clearly treat generated records as fictional synthetic demonstration data"
    ]
  },
  "target_database": "PostgreSQL"
}
```

## Rule-Based Score JSON

```json
{
  "missing_sections": [],
  "rule_based_score": 100,
  "scoring_formula": "Presence-based weighted score out of 100"
}
```

## Review Checklist

Check all of the following:

1. Are the key business entities enough?
2. Are any important domain entities missing?
3. Are relationships correct and clear?
4. Are many-to-many relationships resolved using bridge/intersection entities?
5. Are reporting requirements supported by entities and relationships?
6. Are business rules clear enough?
7. Are platform/database requirements clear enough?
8. Are entity attributes detailed enough?
9. Are data quality, security, audit, and privacy needs mentioned where required?
10. Are expected outputs clearly listed?
11. Are analytics requirements clear if reporting, facts, dimensions, or metrics are requested?
12. Are there ambiguities that would force AI to guess?
13. If reporting requirements are present, can facts and dimensions be inferred?
14. Are business events clear enough to infer fact tables?
15. Are descriptive entities clear enough to infer dimension tables?
16. Is target database clear?
17. Is expected modeling style clear or inferable?
18. If fact/dimension output is requested, can it be inferred without requiring the user to manually list all fact and dimension tables?
19. Does the YAML remain business-friendly rather than forcing technical table lists?
20. Is there enough business context to infer useful DDL constraints, keys, relationships, reporting metrics, and data quality rules for DDL-only Phase 2 synthetic generation?
21. Can status, segment, category, type, method, amount, quantity, date, flag, relationship, and calculated-column behavior be represented through DDL, constraints, and assumptions where appropriate?

## Scoring Rubric

- 0 to 59: Poor input
- 60 to 69: Weak input
- 70 to 79: Medium input
- 80 to 89: Good input but still needs improvements
- 90 to 100: Ready input

## Strict Scoring Rules

Be strict.
Do not score above 90 unless entities are mostly complete.
Do not score above 90 unless relationships are clear.
Do not score above 90 unless major many-to-many relationships are resolved.
Do not score above 90 unless reporting requirements are supported.
Do not score above 90 unless expected outputs are clear.
Do not score above 90 unless target platform/database is clear.
If physical model, SQL DDL, schema, or data dictionary are requested, entity attributes are important.
If analytics outputs are requested, reporting grain, metrics, facts, and dimensions should be evaluated. Do not reject business-friendly YAML only because dim_, fact_, stg_, or load_ tables are not explicitly listed; the accelerator should infer data-engineering layers and DDL constraints when context is sufficient.
If entity attributes are missing, score should usually be below 90 unless expected output is conceptual model only.

## Required JSON Response

{
  "ai_review_score": 0,
  "readiness_level": "Low | Medium | High | Ready",
  "semantic_status": "needs_improvement | ready_for_generation",
  "missing_items": [
    {
      "section": "",
      "issue": "",
      "priority": "Low | Medium | High | Critical",
      "recommendation": ""
    }
  ],
  "relationship_review": {
    "are_relationships_clear": false,
    "many_to_many_issues": [],
    "missing_relationships": []
  },
  "entity_review": {
    "are_entities_enough": false,
    "missing_entities": [],
    "weak_entities": []
  },
  "reporting_review": {
    "are_reporting_requirements_supported": false,
    "missing_reporting_details": []
  },
  "business_rule_review": {
    "are_business_rules_clear": false,
    "missing_business_rules": []
  },
  "platform_review": {
    "is_platform_clear": false,
    "missing_platform_details": []
  },
  "suggestions": [],
  "assumptions_needed": []
}
