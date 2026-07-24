# Codex Data Model Generation

You are a Senior Enterprise Data Architect.

Use this prompt only because Python calculated final_score >= 90.
Generate only the sections requested in expected_output from the canonical input JSON.

Return strict JSON only. Do not include markdown code fences, commentary, or explanations outside JSON.

## Canonical Business Input JSON

```json
{
  "business_description": "TimeCraft is an online watch shopping platform where customers browse watches, compare brands and collections, place orders, make payments, receive shipments, request returns, and raise warranty claims. The business wants better visibility into sales, customer behaviour, product demand, inventory availability, payment outcomes, shipment performance, returns, refunds, and warranty service.\n",
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
    "Fact foreign keys must resolve to valid dimension records"
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
    "PostgreSQL loading support"
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
  "model_purpose": "Create a data model that helps the business analyse customer orders, watch product sales, brand and collection performance, inventory availability, payment status, shipment outcomes, returns, refunds, and warranty claims. The model should support business reporting, operational analysis, synthetic data generation, Excel output, and PostgreSQL loading.\n",
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

## Final Readiness Score JSON

```json
{
  "ai_review_score": 87,
  "decision": "ready_for_generation",
  "final_score": 96.1,
  "formula": "final_score = 0.70 * rule_based_score + 0.30 * ai_review_score",
  "rule_based_score": 100
}
```

## Model Intent JSON

```json
{
  "confidence": "high",
  "fact_dimension_inference_required": true,
  "model_type": "analytical_data_warehouse",
  "modeling_style": "dimensional_model",
  "reason": "Reporting and analytics requirements are present.",
  "required_layers": [
    "raw_load",
    "staging",
    "dimension",
    "fact",
    "reporting"
  ]
}
```

## Model Blueprint JSON

```json
{
  "assumptions": [
    "Technical warehouse tables are inferred from business entities and reporting requirements.",
    "Surrogate keys are recommended for dimensions and facts should reference dimensions by keys."
  ],
  "fact_grains": {
    "fact_claim": "one row per claim",
    "fact_delivery": "one row per delivery record",
    "fact_payment": "one row per payment transaction",
    "fact_return": "one row per return transaction",
    "fact_sales": "one row per order item",
    "fact_transaction": "one row per transaction"
  },
  "inferred_dimension_tables": [
    "dim_customer",
    "dim_store",
    "dim_product",
    "dim_location",
    "dim_date"
  ],
  "inferred_fact_tables": [
    "fact_sales",
    "fact_payment",
    "fact_delivery",
    "fact_return",
    "fact_claim",
    "fact_transaction"
  ],
  "inferred_load_tables": [
    "load_entity_name_customer_description_a_person_who_registers_on_the_time_craft_website_and_places_watch_orders_raw",
    "load_entity_name_brand_description_a_fictional_watch_brand_sold_through_the_online_store_raw",
    "load_entity_name_collection_description_a_watch_collection_or_product_series_belonging_to_a_brand_raw",
    "load_entity_name_watch_product_description_a_watch_item_available_for_customers_to_purchase_raw",
    "load_entity_name_warehouse_description_a_fulfilment_location_that_stores_watches_and_dispatches_shipments_raw",
    "load_entity_name_inventory_description_product_stock_availability_recorded_for_a_warehouse_on_a_specific_date_raw",
    "load_entity_name_order_description_a_purchase_request_placed_by_a_customer_raw",
    "load_entity_name_order_item_description_a_watch_product_line_item_inside_an_order_raw",
    "load_entity_name_payment_description_a_payment_transaction_related_to_an_order_raw",
    "load_entity_name_shipment_description_shipment_and_delivery_tracking_information_for_an_order_raw",
    "load_entity_name_return_request_description_a_customer_request_to_return_part_or_all_of_an_order_item_raw",
    "load_entity_name_warranty_claim_description_a_warranty_service_claim_raised_for_a_purchased_watch_raw"
  ],
  "inferred_staging_tables": [
    "stg_entity_name_customer_description_a_person_who_registers_on_the_time_craft_website_and_places_watch_orders",
    "stg_entity_name_brand_description_a_fictional_watch_brand_sold_through_the_online_store",
    "stg_entity_name_collection_description_a_watch_collection_or_product_series_belonging_to_a_brand",
    "stg_entity_name_watch_product_description_a_watch_item_available_for_customers_to_purchase",
    "stg_entity_name_warehouse_description_a_fulfilment_location_that_stores_watches_and_dispatches_shipments",
    "stg_entity_name_inventory_description_product_stock_availability_recorded_for_a_warehouse_on_a_specific_date",
    "stg_entity_name_order_description_a_purchase_request_placed_by_a_customer",
    "stg_entity_name_order_item_description_a_watch_product_line_item_inside_an_order",
    "stg_entity_name_payment_description_a_payment_transaction_related_to_an_order",
    "stg_entity_name_shipment_description_shipment_and_delivery_tracking_information_for_an_order",
    "stg_entity_name_return_request_description_a_customer_request_to_return_part_or_all_of_an_order_item",
    "stg_entity_name_warranty_claim_description_a_warranty_service_claim_raised_for_a_purchased_watch"
  ],
  "model_type": "analytical_data_warehouse",
  "modeling_style": "dimensional_model",
  "required_layers": [
    "raw_load",
    "staging",
    "dimension",
    "fact",
    "reporting"
  ],
  "source_to_target_mapping_summary": [
    "{'entity_name': 'Customer', 'description': 'A person who registers on the TimeCraft website and places watch orders.'} -> load_entity_name_customer_description_a_person_who_registers_on_the_time_craft_website_and_places_watch_orders_raw -> stg_entity_name_customer_description_a_person_who_registers_on_the_time_craft_website_and_places_watch_orders",
    "{'entity_name': 'Brand', 'description': 'A fictional watch brand sold through the online store.'} -> load_entity_name_brand_description_a_fictional_watch_brand_sold_through_the_online_store_raw -> stg_entity_name_brand_description_a_fictional_watch_brand_sold_through_the_online_store",
    "{'entity_name': 'Collection', 'description': 'A watch collection or product series belonging to a brand.'} -> load_entity_name_collection_description_a_watch_collection_or_product_series_belonging_to_a_brand_raw -> stg_entity_name_collection_description_a_watch_collection_or_product_series_belonging_to_a_brand",
    "{'entity_name': 'Watch Product', 'description': 'A watch item available for customers to purchase.'} -> load_entity_name_watch_product_description_a_watch_item_available_for_customers_to_purchase_raw -> stg_entity_name_watch_product_description_a_watch_item_available_for_customers_to_purchase",
    "{'entity_name': 'Warehouse', 'description': 'A fulfilment location that stores watches and dispatches shipments.'} -> load_entity_name_warehouse_description_a_fulfilment_location_that_stores_watches_and_dispatches_shipments_raw -> stg_entity_name_warehouse_description_a_fulfilment_location_that_stores_watches_and_dispatches_shipments",
    "{'entity_name': 'Inventory', 'description': 'Product stock availability recorded for a warehouse on a specific date.'} -> load_entity_name_inventory_description_product_stock_availability_recorded_for_a_warehouse_on_a_specific_date_raw -> stg_entity_name_inventory_description_product_stock_availability_recorded_for_a_warehouse_on_a_specific_date",
    "{'entity_name': 'Order', 'description': 'A purchase request placed by a customer.'} -> load_entity_name_order_description_a_purchase_request_placed_by_a_customer_raw -> stg_entity_name_order_description_a_purchase_request_placed_by_a_customer",
    "{'entity_name': 'Order Item', 'description': 'A watch product line item inside an order.'} -> load_entity_name_order_item_description_a_watch_product_line_item_inside_an_order_raw -> stg_entity_name_order_item_description_a_watch_product_line_item_inside_an_order",
    "{'entity_name': 'Payment', 'description': 'A payment transaction related to an order.'} -> load_entity_name_payment_description_a_payment_transaction_related_to_an_order_raw -> stg_entity_name_payment_description_a_payment_transaction_related_to_an_order",
    "{'entity_name': 'Shipment', 'description': 'Shipment and delivery tracking information for an order.'} -> load_entity_name_shipment_description_shipment_and_delivery_tracking_information_for_an_order_raw -> stg_entity_name_shipment_description_shipment_and_delivery_tracking_information_for_an_order",
    "{'entity_name': 'Return Request', 'description': 'A customer request to return part or all of an order item.'} -> load_entity_name_return_request_description_a_customer_request_to_return_part_or_all_of_an_order_item_raw -> stg_entity_name_return_request_description_a_customer_request_to_return_part_or_all_of_an_order_item",
    "{'entity_name': 'Warranty Claim', 'description': 'A warranty service claim raised for a purchased watch.'} -> load_entity_name_warranty_claim_description_a_warranty_service_claim_raised_for_a_purchased_watch_raw -> stg_entity_name_warranty_claim_description_a_warranty_service_claim_raised_for_a_purchased_watch"
  ],
  "suggested_dimension_keys": [
    "customer_key",
    "store_key",
    "product_key",
    "location_key",
    "date_key"
  ],
  "suggested_measures": [
    "quantity",
    "unit_price",
    "payment_amount",
    "amount",
    "price",
    "order_total_amount"
  ]
}
```

## Possible Requested Sections

Business Input Summary
Conceptual Data Model
Logical Data Model
Physical Data Model
ER Diagram
SQL DDL
Data Dictionary
Relationships
Cardinality
Primary Keys
Foreign Keys
Constraints
Indexes
Views
Materialized Views
Fact Tables
Dimension Tables
Transformation Plan
Orchestration Plan


## Model Intent Instructions

If model_intent.model_type is analytical_data_warehouse, dimensional_model, or star_schema:

- Do not generate only operational OLTP tables.
- Generate a layered analytical warehouse model.
- Use the model_blueprint as guidance.
- YAML does not need to explicitly list every final technical table.
- Infer technical tables from business context.

For analytical warehouse output, generate:

1. Raw load tables using load_ prefix
2. Staging tables using stg_ prefix
3. Dimension tables using dim_ prefix
4. Fact tables using fact_ prefix
5. Fact grain for every fact table
6. Primary keys
7. Foreign keys
8. UNIQUE constraints where useful
9. CHECK constraints for numeric/status quality rules
10. Indexes for joins and reporting filters
11. PostgreSQL SQL DDL for all generated tables
12. Data dictionary for all generated tables
13. Relationships and cardinality
14. Synthetic data generation rules for every table
15. PostgreSQL loading order
16. AI Additions / Assumptions

For facts:

- Clearly state the grain.
- Include foreign keys to dimensions.
- Include measurable metrics.
- Infer facts from business processes, transactions, events, and reporting requirements.

For dimensions:

- Use descriptive/master entities as dimensions.
- Add surrogate keys.
- Keep natural/business keys where useful.
- Add SCD-style fields only when appropriate.
- If adding SCD fields, list them under AI Additions / Assumptions.

If model_intent.model_type is operational_model:

- Preserve normal operational relational modeling behavior.
- Do not force dimensional warehouse layers.


## Phase 2 DDL-Only Synthetic Data Generation Compatibility

Do not include any machine-readable synthetic value JSON sections or synthetic value markers in final_output_markdown. Phase 2 generates synthetic data from PostgreSQL DDL only.

To support Phase 2, the generated SQL DDL must be complete and executable PostgreSQL-oriented DDL with clear table names, column names, data types, primary keys, foreign keys, UNIQUE constraints, NOT NULL constraints, useful CHECK constraints, defaults where appropriate, and reporting views where relevant.

For analytical warehouse outputs, continue generating raw/load, staging, dimension, fact, and reporting structures even when the user YAML is business-friendly and does not list those technical tables explicitly.

## Critical AI Additions Rule

If you add anything not explicitly present in the input, list it under this markdown heading in final_output_markdown:

# AI Additions / Assumptions

Use this table:

| Added Item | Type | Reason | Mandatory / Optional |
|---|---|---|---|

## Required JSON Response

{
  "status": "generated",
  "final_output_markdown": "",
  "ai_additions_and_assumptions": [
    {
      "added_item": "",
      "item_type": "entity | attribute | relationship | key | constraint | index | table | view | assumption",
      "reason": "",
      "mandatory_or_optional": "mandatory | optional"
    }
  ]
}
