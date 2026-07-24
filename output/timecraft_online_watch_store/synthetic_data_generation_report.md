# Synthetic Data Generation Report

- Final status: **passed_with_warnings**
- YAML input: `input/timecraft_online_watch_store.yaml`
- Phase 1 output: `/home/deepak/projects/datamodelling-accelerator-v3-production/output/timecraft_online_watch_store/final_output.md`
- Excel output: `/home/deepak/projects/datamodelling-accelerator-v3-production/output/timecraft_online_watch_store/timecraft_online_watch_store_synthetic_data.xlsx`
- Excel written in this run: True
- Rows per table: 10

## DDL Extraction Summary

- Extracted DDL characters: 15071
- Tables parsed: 37

## Parsed Tables

| Table | Columns | Primary Key | Foreign Keys |
|---|---:|---|---:|
| load_customer_raw | 5 | load_id | 0 |
| load_brand_raw | 5 | load_id | 0 |
| load_collection_raw | 5 | load_id | 0 |
| load_watch_product_raw | 5 | load_id | 0 |
| load_warehouse_raw | 5 | load_id | 0 |
| load_inventory_raw | 5 | load_id | 0 |
| load_order_raw | 5 | load_id | 0 |
| load_order_item_raw | 5 | load_id | 0 |
| load_payment_raw | 5 | load_id | 0 |
| load_shipment_raw | 5 | load_id | 0 |
| load_return_request_raw | 5 | load_id | 0 |
| load_warranty_claim_raw | 5 | load_id | 0 |
| stg_customer | 9 | customer_id | 0 |
| stg_brand | 5 | brand_id | 0 |
| stg_collection | 5 | collection_id | 1 |
| stg_watch_product | 15 | product_id | 2 |
| stg_warehouse | 6 | warehouse_id | 0 |
| stg_inventory | 9 | inventory_id | 2 |
| stg_order | 8 | order_id | 1 |
| stg_order_item | 9 | order_item_id | 3 |
| stg_payment | 8 | payment_id | 1 |
| stg_shipment | 10 | shipment_id | 2 |
| stg_return_request | 9 | return_id | 1 |
| stg_warranty_claim | 9 | warranty_claim_id | 1 |
| dim_date | 10 | date_key | 0 |
| dim_customer | 10 | customer_key | 0 |
| dim_brand | 6 | brand_key | 0 |
| dim_collection | 6 | collection_key | 1 |
| dim_product | 16 | product_key | 2 |
| dim_warehouse | 7 | warehouse_key | 0 |
| dim_order | 9 | order_key | 2 |
| fact_sales | 12 | sales_key | 5 |
| fact_inventory | 10 | inventory_key | 3 |
| fact_payment | 10 | payment_key | 3 |
| fact_delivery | 15 | delivery_key | 6 |
| fact_return | 13 | return_key | 7 |
| fact_claim | 14 | claim_key | 7 |

## Warehouse Pipeline Classification

- Raw/load tables: load_customer_raw, load_brand_raw, load_collection_raw, load_watch_product_raw, load_warehouse_raw, load_inventory_raw, load_order_raw, load_order_item_raw, load_payment_raw, load_shipment_raw, load_return_request_raw, load_warranty_claim_raw
- Staging tables: stg_customer, stg_brand, stg_collection, stg_watch_product, stg_warehouse, stg_inventory, stg_order, stg_order_item, stg_payment, stg_shipment, stg_return_request, stg_warranty_claim
- Dimension tables: dim_date, dim_customer, dim_brand, dim_collection, dim_product, dim_warehouse, dim_order
- Fact tables: fact_sales, fact_inventory, fact_payment, fact_delivery, fact_return, fact_claim
- Other tables: None

## Warehouse Lineage Plan

- stg_customer: load_customer_raw
- stg_brand: load_brand_raw
- stg_collection: load_collection_raw
- stg_watch_product: load_watch_product_raw
- stg_warehouse: load_warehouse_raw
- stg_inventory: load_inventory_raw
- stg_order: load_order_raw
- stg_order_item: load_order_item_raw
- stg_payment: load_payment_raw
- stg_shipment: load_shipment_raw
- stg_return_request: load_return_request_raw
- stg_warranty_claim: load_warranty_claim_raw
- dim_date: None
- dim_customer: stg_customer
- dim_brand: stg_brand
- dim_collection: stg_collection
- dim_product: stg_watch_product
- dim_warehouse: stg_warehouse
- dim_order: stg_order
- fact_sales: dim_order, dim_customer, dim_product, dim_warehouse, dim_date, stg_warranty_claim, stg_order_item
- fact_inventory: dim_product, dim_warehouse, dim_date, stg_inventory, stg_watch_product, stg_warehouse
- fact_payment: dim_order, dim_customer, dim_date, stg_payment, stg_order
- fact_delivery: dim_order, dim_customer, dim_warehouse, dim_date, stg_shipment, stg_order, stg_warehouse
- fact_return: dim_order, dim_customer, dim_product, dim_date, stg_return_request, stg_order_item
- fact_claim: dim_order, dim_customer, dim_product, dim_date, stg_warranty_claim, stg_order_item

### Pipeline Plan Warnings

- No likely staging source inferred for dimension table dim_date.

## Realistic Generation Profile

- Main business-event target: 10
- Target date span: 40 days

| Raw/Load Table | Category | Target Rows | Mapped Staging |
|---|---|---:|---|
| load_customer_raw | master | 5 | stg_customer |
| load_brand_raw | master | 6 | stg_brand |
| load_collection_raw | master | 6 | stg_collection |
| load_watch_product_raw | master | 5 | stg_watch_product |
| load_warehouse_raw | master | 5 | stg_warehouse |
| load_inventory_raw | event | 10 | stg_inventory |
| load_order_raw | event | 10 | stg_order |
| load_order_item_raw | detail | 30 | stg_order_item |
| load_payment_raw | event | 10 | stg_payment |
| load_shipment_raw | event | 10 | stg_shipment |
| load_return_request_raw | event | 10 | stg_return_request |
| load_warranty_claim_raw | event | 10 | stg_warranty_claim |
- Relationship reuse rules: 14

## Codex ELT Assumptions

- All records are fictional synthetic demonstration data.
- Raw identity load_id values are omitted so PostgreSQL generates them.
- The six required dim_date rows cover every date referenced by dimensions and facts while spanning 40 calendar days inclusively.
- Fact sales uses one designated representative order item per order to satisfy the specified 10-row fact_sales target; all 30 order-item rows remain available in staging and all order totals reconcile to them.
- Each generated return and warranty claim references a delivered order's designated fact-sales item so required fact foreign keys resolve.
- The mandated profile requires ten return rows and ten warranty-claim rows despite the narrative preference that these events be minorities; exact requested table counts take precedence.
- Successful payment amounts equal their associated order net amounts and do not exceed them.

## Codex SQL Artifact

- `/home/deepak/projects/datamodelling-accelerator-v3-production/output/timecraft_online_watch_store/codex_generated_data/warehouse_elt_sql.json`

## ELT Execution Summary

- SQL execution status: passed
- Transaction status: committed

### Raw/Load Inserted Rows

| Table | Rows |
|---|---:|
| load_customer_raw | 5 |
| load_brand_raw | 6 |
| load_collection_raw | 6 |
| load_watch_product_raw | 5 |
| load_warehouse_raw | 5 |
| load_inventory_raw | 10 |
| load_order_raw | 10 |
| load_order_item_raw | 30 |
| load_payment_raw | 10 |
| load_shipment_raw | 10 |
| load_return_request_raw | 10 |
| load_warranty_claim_raw | 10 |

### Final Row Counts by Table

| Table | Rows |
|---|---:|
| load_customer_raw | 5 |
| load_brand_raw | 6 |
| load_collection_raw | 6 |
| load_watch_product_raw | 5 |
| load_warehouse_raw | 5 |
| load_inventory_raw | 10 |
| load_order_raw | 10 |
| load_order_item_raw | 30 |
| load_payment_raw | 10 |
| load_shipment_raw | 10 |
| load_return_request_raw | 10 |
| load_warranty_claim_raw | 10 |
| stg_customer | 5 |
| stg_brand | 6 |
| stg_collection | 6 |
| stg_watch_product | 5 |
| stg_warehouse | 5 |
| stg_inventory | 10 |
| stg_order | 10 |
| stg_order_item | 30 |
| stg_payment | 10 |
| stg_shipment | 10 |
| stg_return_request | 10 |
| stg_warranty_claim | 10 |
| dim_date | 6 |
| dim_customer | 5 |
| dim_brand | 6 |
| dim_collection | 6 |
| dim_product | 5 |
| dim_warehouse | 5 |
| dim_order | 10 |
| fact_sales | 10 |
| fact_inventory | 10 |
| fact_payment | 10 |
| fact_delivery | 10 |
| fact_return | 10 |
| fact_claim | 10 |

## Lineage Validation Summary

- Status: **passed**
- No lineage errors.

## Ignored Constraints / Warnings

- load_customer_raw: CHECK: payload CHECK (jsonb_typeof(payload)='object')
- load_brand_raw: CHECK: payload CHECK (jsonb_typeof(payload)='object')
- load_collection_raw: CHECK: payload CHECK (jsonb_typeof(payload)='object')
- load_watch_product_raw: CHECK: payload CHECK (jsonb_typeof(payload)='object')
- load_warehouse_raw: CHECK: payload CHECK (jsonb_typeof(payload)='object')
- load_inventory_raw: CHECK: payload CHECK (jsonb_typeof(payload)='object')
- load_order_raw: CHECK: payload CHECK (jsonb_typeof(payload)='object')
- load_order_item_raw: CHECK: payload CHECK (jsonb_typeof(payload)='object')
- load_payment_raw: CHECK: payload CHECK (jsonb_typeof(payload)='object')
- load_shipment_raw: CHECK: payload CHECK (jsonb_typeof(payload)='object')
- load_return_request_raw: CHECK: payload CHECK (jsonb_typeof(payload)='object')
- load_warranty_claim_raw: CHECK: payload CHECK (jsonb_typeof(payload)='object')
- stg_inventory: CHECK: CHECK (available_quantity = on_hand_quantity - reserved_quantity)
- stg_order: CHECK: CHECK (net_order_amount = gross_order_amount - discount_amount)
- stg_order_item: CHECK: gross_line_amount CHECK (gross_line_amount = quantity * unit_price)
- stg_order_item: CHECK: line_discount_amount CHECK (line_discount_amount BETWEEN 0 AND gross_line_amount)
- stg_order_item: CHECK: line_net_amount CHECK (line_net_amount = gross_line_amount-line_discount_amount)
- stg_shipment: CHECK: CHECK (promised_delivery_date >= shipment_date)
- stg_shipment: CHECK: CHECK ((shipment_status='DELIVERED' AND actual_delivery_date IS NOT NULL) OR (shipment_status<>'DELIVERED' AND actual_delivery_date IS NULL))
- stg_return_request: CHECK: CHECK (approved_date IS NULL OR approved_date >= requested_date)
- stg_return_request: CHECK: CHECK (refund_date IS NULL OR (approved_date IS NOT NULL AND refund_date >= approved_date))
- stg_warranty_claim: CHECK: CHECK (service_start_date IS NULL OR service_start_date >= claim_date)
- stg_warranty_claim: CHECK: CHECK (service_completion_date IS NULL OR (service_start_date IS NOT NULL AND service_completion_date >= service_start_date))
- dim_order: CHECK: net_order_amount CHECK (net_order_amount = gross_order_amount-discount_amount)
- fact_sales: CHECK: gross_line_amount CHECK (gross_line_amount = quantity*unit_price)
- fact_sales: CHECK: line_discount_amount CHECK (line_discount_amount BETWEEN 0 AND gross_line_amount)
- fact_sales: CHECK: line_net_amount CHECK (line_net_amount = gross_line_amount-line_discount_amount)
- fact_inventory: CHECK: CHECK (available_quantity = on_hand_quantity-reserved_quantity)
- fact_delivery: CHECK: shipment_count CHECK (shipment_count=1)

### Parser Warnings

- Unsupported CHECK constraint ignored safely for column payload.
- Unsupported CHECK constraint ignored safely for column payload.
- Unsupported CHECK constraint ignored safely for column payload.
- Unsupported CHECK constraint ignored safely for column payload.
- Unsupported CHECK constraint ignored safely for column payload.
- Unsupported CHECK constraint ignored safely for column payload.
- Unsupported CHECK constraint ignored safely for column payload.
- Unsupported CHECK constraint ignored safely for column payload.
- Unsupported CHECK constraint ignored safely for column payload.
- Unsupported CHECK constraint ignored safely for column payload.
- Unsupported CHECK constraint ignored safely for column payload.
- Unsupported CHECK constraint ignored safely for column payload.
- Unsupported CHECK constraint ignored safely: CHECK (available_quantity = on_hand_quantity - reserved_quantity)
- Unsupported CHECK constraint ignored safely: CHECK (net_order_amount = gross_order_amount - discount_amount)
- Unsupported CHECK constraint ignored safely for column gross_line_amount.
- Unsupported CHECK constraint ignored safely for column line_discount_amount.
- Unsupported CHECK constraint ignored safely for column line_net_amount.
- Unsupported CHECK constraint ignored safely: CHECK (promised_delivery_date >= shipment_date)
- Unsupported CHECK constraint ignored safely: CHECK ((shipment_status='DELIVERED' AND actual_delivery_date IS NOT NULL) OR (shipment_status<>'DELIVERED' AND actual_delivery_date IS NULL))
- Unsupported CHECK constraint ignored safely: CHECK (approved_date IS NULL OR approved_date >= requested_date)
- Unsupported CHECK constraint ignored safely: CHECK (refund_date IS NULL OR (approved_date IS NOT NULL AND refund_date >= approved_date))
- Unsupported CHECK constraint ignored safely: CHECK (service_start_date IS NULL OR service_start_date >= claim_date)
- Unsupported CHECK constraint ignored safely: CHECK (service_completion_date IS NULL OR (service_start_date IS NOT NULL AND service_completion_date >= service_start_date))
- Unsupported CHECK constraint ignored safely for column net_order_amount.
- Unsupported CHECK constraint ignored safely for column gross_line_amount.
- Unsupported CHECK constraint ignored safely for column line_discount_amount.
- Unsupported CHECK constraint ignored safely for column line_net_amount.
- Unsupported CHECK constraint ignored safely: CHECK (available_quantity = on_hand_quantity-reserved_quantity)
- Unsupported CHECK constraint ignored safely for column shipment_count.

## Column Length Rules

- No varchar length limits parsed.
- Generated-short/truncated value count: 0

## Numeric Precision / Scale Rules

- stg_watch_product.case_size_mm numeric(5,2)
- stg_watch_product.unit_price numeric(14,2)
- stg_order.gross_order_amount numeric(14,2)
- stg_order.discount_amount numeric(14,2)
- stg_order.net_order_amount numeric(14,2)
- stg_order_item.unit_price numeric(14,2)
- stg_order_item.gross_line_amount numeric(14,2)
- stg_order_item.line_discount_amount numeric(14,2)
- stg_order_item.line_net_amount numeric(14,2)
- stg_payment.payment_amount numeric(14,2)
- stg_return_request.refund_amount numeric(14,2)
- stg_warranty_claim.service_cost_amount numeric(14,2)
- dim_product.case_size_mm numeric(5,2)
- dim_product.catalogue_unit_price numeric(14,2)
- dim_order.gross_order_amount numeric(14,2)
- dim_order.discount_amount numeric(14,2)
- dim_order.net_order_amount numeric(14,2)
- fact_sales.unit_price numeric(14,2)
- fact_sales.gross_line_amount numeric(14,2)
- fact_sales.line_discount_amount numeric(14,2)
- fact_sales.line_net_amount numeric(14,2)
- fact_payment.payment_amount numeric(14,2)
- fact_return.refund_amount numeric(14,2)
- fact_claim.service_cost_amount numeric(14,2)
- Numeric bounded value count: 0

## CHECK IN Value Source Summary

- No CHECK IN constrained columns generated in this run.

## Foreign Key Relationships

### Parsed

- stg_collection(brand_id) -> stg_brand(brand_id)
- stg_watch_product(brand_id) -> stg_brand(brand_id)
- stg_watch_product(collection_id, brand_id) -> stg_collection(collection_id, brand_id)
- stg_inventory(product_id) -> stg_watch_product(product_id)
- stg_inventory(warehouse_id) -> stg_warehouse(warehouse_id)
- stg_order(customer_id) -> stg_customer(customer_id)
- stg_order_item(order_id) -> stg_order(order_id)
- stg_order_item(product_id) -> stg_watch_product(product_id)
- stg_order_item(warehouse_id) -> stg_warehouse(warehouse_id)
- stg_payment(order_id) -> stg_order(order_id)
- stg_shipment(order_id) -> stg_order(order_id)
- stg_shipment(warehouse_id) -> stg_warehouse(warehouse_id)
- stg_return_request(order_item_id) -> stg_order_item(order_item_id)
- stg_warranty_claim(order_item_id) -> stg_order_item(order_item_id)
- dim_collection(brand_key) -> dim_brand(brand_key)
- dim_product(brand_key) -> dim_brand(brand_key)
- dim_product(collection_key) -> dim_collection(collection_key)
- dim_order(customer_key) -> dim_customer(customer_key)
- dim_order(order_date_key) -> dim_date(date_key)
- fact_sales(order_key) -> dim_order(order_key)
- fact_sales(customer_key) -> dim_customer(customer_key)
- fact_sales(product_key) -> dim_product(product_key)
- fact_sales(warehouse_key) -> dim_warehouse(warehouse_key)
- fact_sales(order_date_key) -> dim_date(date_key)
- fact_inventory(product_key) -> dim_product(product_key)
- fact_inventory(warehouse_key) -> dim_warehouse(warehouse_key)
- fact_inventory(inventory_date_key) -> dim_date(date_key)
- fact_payment(order_key) -> dim_order(order_key)
- fact_payment(customer_key) -> dim_customer(customer_key)
- fact_payment(payment_date_key) -> dim_date(date_key)
- fact_delivery(order_key) -> dim_order(order_key)
- fact_delivery(customer_key) -> dim_customer(customer_key)
- fact_delivery(warehouse_key) -> dim_warehouse(warehouse_key)
- fact_delivery(shipment_date_key) -> dim_date(date_key)
- fact_delivery(promised_delivery_date_key) -> dim_date(date_key)
- fact_delivery(actual_delivery_date_key) -> dim_date(date_key)
- fact_return(sales_key) -> fact_sales(sales_key)
- fact_return(order_key) -> dim_order(order_key)
- fact_return(customer_key) -> dim_customer(customer_key)
- fact_return(product_key) -> dim_product(product_key)
- fact_return(requested_date_key) -> dim_date(date_key)
- fact_return(approved_date_key) -> dim_date(date_key)
- fact_return(refund_date_key) -> dim_date(date_key)
- fact_claim(sales_key) -> fact_sales(sales_key)
- fact_claim(order_key) -> dim_order(order_key)
- fact_claim(customer_key) -> dim_customer(customer_key)
- fact_claim(product_key) -> dim_product(product_key)
- fact_claim(claim_date_key) -> dim_date(date_key)
- fact_claim(service_start_date_key) -> dim_date(date_key)
- fact_claim(service_completion_date_key) -> dim_date(date_key)

### Validated

- stg_collection(brand_id) -> stg_brand(brand_id)
- stg_watch_product(brand_id) -> stg_brand(brand_id)
- stg_watch_product(collection_id, brand_id) -> stg_collection(collection_id, brand_id)
- stg_inventory(product_id) -> stg_watch_product(product_id)
- stg_inventory(warehouse_id) -> stg_warehouse(warehouse_id)
- stg_order(customer_id) -> stg_customer(customer_id)
- stg_order_item(order_id) -> stg_order(order_id)
- stg_order_item(product_id) -> stg_watch_product(product_id)
- stg_order_item(warehouse_id) -> stg_warehouse(warehouse_id)
- stg_payment(order_id) -> stg_order(order_id)
- stg_shipment(order_id) -> stg_order(order_id)
- stg_shipment(warehouse_id) -> stg_warehouse(warehouse_id)
- stg_return_request(order_item_id) -> stg_order_item(order_item_id)
- stg_warranty_claim(order_item_id) -> stg_order_item(order_item_id)
- dim_collection(brand_key) -> dim_brand(brand_key)
- dim_product(brand_key) -> dim_brand(brand_key)
- dim_product(collection_key) -> dim_collection(collection_key)
- dim_order(customer_key) -> dim_customer(customer_key)
- dim_order(order_date_key) -> dim_date(date_key)
- fact_sales(order_key) -> dim_order(order_key)
- fact_sales(customer_key) -> dim_customer(customer_key)
- fact_sales(product_key) -> dim_product(product_key)
- fact_sales(warehouse_key) -> dim_warehouse(warehouse_key)
- fact_sales(order_date_key) -> dim_date(date_key)
- fact_inventory(product_key) -> dim_product(product_key)
- fact_inventory(warehouse_key) -> dim_warehouse(warehouse_key)
- fact_inventory(inventory_date_key) -> dim_date(date_key)
- fact_payment(order_key) -> dim_order(order_key)
- fact_payment(customer_key) -> dim_customer(customer_key)
- fact_payment(payment_date_key) -> dim_date(date_key)
- fact_delivery(order_key) -> dim_order(order_key)
- fact_delivery(customer_key) -> dim_customer(customer_key)
- fact_delivery(warehouse_key) -> dim_warehouse(warehouse_key)
- fact_delivery(shipment_date_key) -> dim_date(date_key)
- fact_delivery(promised_delivery_date_key) -> dim_date(date_key)
- fact_delivery(actual_delivery_date_key) -> dim_date(date_key)
- fact_return(sales_key) -> fact_sales(sales_key)
- fact_return(order_key) -> dim_order(order_key)
- fact_return(customer_key) -> dim_customer(customer_key)
- fact_return(product_key) -> dim_product(product_key)
- fact_return(requested_date_key) -> dim_date(date_key)
- fact_return(approved_date_key) -> dim_date(date_key)
- fact_return(refund_date_key) -> dim_date(date_key)
- fact_claim(sales_key) -> fact_sales(sales_key)
- fact_claim(order_key) -> dim_order(order_key)
- fact_claim(customer_key) -> dim_customer(customer_key)
- fact_claim(product_key) -> dim_product(product_key)
- fact_claim(claim_date_key) -> dim_date(date_key)
- fact_claim(service_start_date_key) -> dim_date(date_key)
- fact_claim(service_completion_date_key) -> dim_date(date_key)

### FK-like Columns Skipped Because No FK Exists in DDL

- load_customer_raw.source_record_id
- load_brand_raw.source_record_id
- load_collection_raw.source_record_id
- load_watch_product_raw.source_record_id
- load_warehouse_raw.source_record_id
- load_inventory_raw.source_record_id
- load_order_raw.source_record_id
- load_order_item_raw.source_record_id
- load_payment_raw.source_record_id
- load_shipment_raw.source_record_id
- load_return_request_raw.source_record_id
- load_warranty_claim_raw.source_record_id
- dim_customer.customer_id
- dim_brand.brand_id
- dim_collection.collection_id
- dim_product.product_id
- dim_warehouse.warehouse_id
- dim_order.order_id
- fact_sales.order_item_id
- fact_inventory.inventory_id
- fact_payment.payment_id
- fact_delivery.shipment_id
- fact_return.return_id
- fact_claim.warranty_claim_id

## Semantic Inference Summary

- Context terms: None
- Generated semantic types:

## Reference Data Matching Summary

- No YAML reference_data matches were applied.

## Entity Reuse Summary

- No cross-layer entity reuse events were needed.

## Relationship Generation Summary

- No parsed FK relationships were used.

## DDL-Only Generation Strategy

- Columns generated using DDL/name inference: 0
- Columns generated from CHECK IN allowed values: 0
- Fallback-to-DDL inference count: 0
- DDL type corrections: 0
- VARCHAR length corrections: 0
- Incompatible reuse corrections: 0
- Calculation corrections: 0
- FK-safe unique adjustments: 0
- Composite unique adjustments: 0
- Placeholder warning count: 0
- Semantic placeholder validation status: passed
- Semantic placeholder checked values: 1149
- Calculation warning count: 0

## Pre-load Validation

Status: **passed_with_warnings**

- No validation errors.
