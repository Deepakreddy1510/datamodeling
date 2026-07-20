# Synthetic Data Generation Report

- Final status: **passed_with_warnings**
- YAML input: `input/timecraft_online_watch_store.yaml`
- Phase 1 output: `/home/deepak/projects/datamodeling/output/timecraft_online_watch_store/final_output.md`
- Excel output: `/home/deepak/projects/datamodeling/output/timecraft_online_watch_store/timecraft_online_watch_store_synthetic_data.xlsx`
- Excel written in this run: True
- Rows per table: 10

## DDL Extraction Summary

- Extracted DDL characters: 13527
- Tables parsed: 36

## Parsed Tables

| Table | Columns | Primary Key | Foreign Keys |
|---|---:|---|---:|
| raw_load.load_customer_raw | 11 | customer_id | 0 |
| raw_load.load_brand_raw | 7 | brand_id | 0 |
| raw_load.load_collection_raw | 7 | collection_id | 0 |
| raw_load.load_watch_product_raw | 17 | product_id | 0 |
| raw_load.load_warehouse_raw | 8 | warehouse_id | 0 |
| raw_load.load_inventory_raw | 11 | inventory_id | 0 |
| raw_load.load_order_raw | 10 | order_id | 0 |
| raw_load.load_order_item_raw | 11 | order_item_id | 0 |
| raw_load.load_payment_raw | 10 | payment_id | 0 |
| raw_load.load_shipment_raw | 12 | shipment_id | 0 |
| raw_load.load_return_request_raw | 11 | return_id | 0 |
| raw_load.load_warranty_claim_raw | 11 | warranty_claim_id | 0 |
| staging.stg_customer | 11 | customer_id | 0 |
| staging.stg_brand | 7 | brand_id | 0 |
| staging.stg_collection | 7 | collection_id | 0 |
| staging.stg_watch_product | 17 | product_id | 0 |
| staging.stg_warehouse | 8 | warehouse_id | 0 |
| staging.stg_inventory | 11 | inventory_id | 0 |
| staging.stg_order | 10 | order_id | 0 |
| staging.stg_order_item | 11 | order_item_id | 0 |
| staging.stg_payment | 10 | payment_id | 0 |
| staging.stg_shipment | 12 | shipment_id | 0 |
| staging.stg_return_request | 11 | return_id | 0 |
| staging.stg_warranty_claim | 11 | warranty_claim_id | 0 |
| dimensional.dim_date | 9 | date_key | 0 |
| dimensional.dim_customer | 10 | customer_key | 0 |
| dimensional.dim_brand | 6 | brand_key | 0 |
| dimensional.dim_collection | 6 | collection_key | 1 |
| dimensional.dim_product | 16 | product_key | 2 |
| dimensional.dim_warehouse | 7 | warehouse_key | 0 |
| dimensional.fact_sales | 14 | sales_key | 4 |
| dimensional.fact_inventory_snapshot | 10 | inventory_snapshot_key | 3 |
| dimensional.fact_payment | 11 | payment_key | 2 |
| dimensional.fact_shipment | 12 | shipment_key | 5 |
| dimensional.fact_return | 13 | return_key | 5 |
| dimensional.fact_warranty_claim | 14 | warranty_claim_key | 5 |

## Warehouse Pipeline Classification

- Raw/load tables: load_customer_raw, load_brand_raw, load_collection_raw, load_watch_product_raw, load_warehouse_raw, load_inventory_raw, load_order_raw, load_order_item_raw, load_payment_raw, load_shipment_raw, load_return_request_raw, load_warranty_claim_raw
- Staging tables: stg_customer, stg_brand, stg_collection, stg_watch_product, stg_warehouse, stg_inventory, stg_order, stg_order_item, stg_payment, stg_shipment, stg_return_request, stg_warranty_claim
- Dimension tables: dim_date, dim_customer, dim_brand, dim_collection, dim_product, dim_warehouse
- Fact tables: fact_sales, fact_inventory_snapshot, fact_payment, fact_shipment, fact_return, fact_warranty_claim
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
- fact_sales: dim_date, dim_customer, dim_product, dim_warehouse, stg_order_item
- fact_inventory_snapshot: dim_date, dim_product, dim_warehouse, stg_inventory
- fact_payment: dim_date, dim_customer, stg_payment
- fact_shipment: dim_date, dim_customer, dim_warehouse, stg_shipment
- fact_return: dim_date, dim_customer, dim_product, stg_return_request
- fact_warranty_claim: dim_date, dim_customer, dim_product, stg_warranty_claim

### Pipeline Plan Warnings

- No likely staging source inferred for dimension table dim_date.

## Realistic Generation Profile

- Main business-event target: 10
- Target date span: 40 days

| Raw/Load Table | Category | Target Rows | Mapped Staging |
|---|---|---:|---|
| load_customer_raw | master | 6 | stg_customer |
| load_brand_raw | master | 6 | stg_brand |
| load_collection_raw | master | 6 | stg_collection |
| load_watch_product_raw | master | 6 | stg_watch_product |
| load_warehouse_raw | master | 6 | stg_warehouse |
| load_inventory_raw | event | 10 | stg_inventory |
| load_order_raw | event | 10 | stg_order |
| load_order_item_raw | detail | 30 | stg_order_item |
| load_payment_raw | event | 10 | stg_payment |
| load_shipment_raw | event | 10 | stg_shipment |
| load_return_request_raw | event | 10 | stg_return_request |
| load_warranty_claim_raw | event | 10 | stg_warranty_claim |
- Relationship reuse rules: 0

## Codex ELT Assumptions

- All records are fictional synthetic demonstration data.
- The six distinct calendar dates used by events span 40 days inclusively from 2026-05-01 through 2026-06-10 and produce exactly six dim_date rows.
- Exact requested raw-table and downstream table counts take precedence over the narrative preference that returns and warranty claims represent only a minority of order items.
- Each order has three order-item rows; customers, products, warehouses, brands, and collections are reused non-uniformly.
- Order totals are reconciled from order-item gross amounts, discounts, and net amounts.
- All referenced return and warranty order items belong to orders whose generated shipment status is Delivered.
- Successful payment amounts equal and therefore do not exceed their related order net amounts.
- Surrogate identity columns are omitted from dimension and fact INSERT column lists so PostgreSQL generates them.
- Transformation statements assume execution in staging_sql order, then dimension_sql order, then fact_sql order against initially empty target tables.

## Codex SQL Artifact

- `/home/deepak/projects/datamodeling/output/timecraft_online_watch_store/codex_generated_data/warehouse_elt_sql.json`

## ELT Execution Summary

- SQL execution status: passed
- Transaction status: committed

### Raw/Load Inserted Rows

| Table | Rows |
|---|---:|
| load_customer_raw | 6 |
| load_brand_raw | 6 |
| load_collection_raw | 6 |
| load_watch_product_raw | 6 |
| load_warehouse_raw | 6 |
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
| load_customer_raw | 6 |
| load_brand_raw | 6 |
| load_collection_raw | 6 |
| load_watch_product_raw | 6 |
| load_warehouse_raw | 6 |
| load_inventory_raw | 10 |
| load_order_raw | 10 |
| load_order_item_raw | 30 |
| load_payment_raw | 10 |
| load_shipment_raw | 10 |
| load_return_request_raw | 10 |
| load_warranty_claim_raw | 10 |
| stg_customer | 6 |
| stg_brand | 6 |
| stg_collection | 6 |
| stg_watch_product | 6 |
| stg_warehouse | 6 |
| stg_inventory | 10 |
| stg_order | 10 |
| stg_order_item | 30 |
| stg_payment | 10 |
| stg_shipment | 10 |
| stg_return_request | 10 |
| stg_warranty_claim | 10 |
| dim_date | 6 |
| dim_customer | 6 |
| dim_brand | 6 |
| dim_collection | 6 |
| dim_product | 6 |
| dim_warehouse | 6 |
| fact_sales | 30 |
| fact_inventory_snapshot | 10 |
| fact_payment | 10 |
| fact_shipment | 10 |
| fact_return | 10 |
| fact_warranty_claim | 10 |

## Lineage Validation Summary

- Status: **passed**
- No lineage errors.

## Ignored Constraints / Warnings

- dimensional.fact_sales: CHECK: CHECK (gross_line_amount = quantity * unit_price AND line_net_amount = gross_line_amount - line_discount_amount)
- dimensional.fact_inventory_snapshot: CHECK: CHECK (on_hand_quantity >= 0 AND reserved_quantity >= 0 AND available_quantity = on_hand_quantity - reserved_quantity AND reorder_level >= 0)

### Parser Warnings

- Unsupported CHECK constraint ignored safely: CHECK (gross_line_amount = quantity * unit_price AND line_net_amount = gross_line_amount - line_discount_amount)
- Unsupported CHECK constraint ignored safely: CHECK (on_hand_quantity >= 0 AND reserved_quantity >= 0 AND available_quantity = on_hand_quantity - reserved_quantity AND reorder_level >= 0)

## Column Length Rules

- load_customer_raw.customer_name <= 200
- load_customer_raw.email <= 320
- load_customer_raw.phone <= 40
- load_customer_raw.city <= 100
- load_customer_raw.region <= 100
- load_customer_raw.customer_segment <= 50
- load_customer_raw.source_file <= 500
- load_brand_raw.brand_name <= 150
- load_brand_raw.country_of_origin <= 100
- load_brand_raw.brand_tier <= 30
- load_brand_raw.source_file <= 500
- load_collection_raw.collection_name <= 150
- load_collection_raw.collection_status <= 30
- load_collection_raw.source_file <= 500
- load_watch_product_raw.sku <= 80
- load_watch_product_raw.product_name <= 200
- load_watch_product_raw.watch_category <= 60
- load_watch_product_raw.gender_category <= 40
- load_watch_product_raw.movement_type <= 60
- load_watch_product_raw.strap_material <= 60
- load_watch_product_raw.dial_color <= 60
- load_watch_product_raw.product_status <= 30
- load_watch_product_raw.source_file <= 500
- load_warehouse_raw.warehouse_name <= 150
- load_warehouse_raw.city <= 100
- load_warehouse_raw.region <= 100
- load_warehouse_raw.warehouse_type <= 50
- load_warehouse_raw.source_file <= 500
- load_inventory_raw.inventory_status <= 30
- load_inventory_raw.source_file <= 500
- load_order_raw.order_status <= 30
- load_order_raw.order_channel <= 30
- load_order_raw.source_file <= 500
- load_order_item_raw.source_file <= 500
- load_payment_raw.payment_method <= 40
- load_payment_raw.payment_transaction_type <= 30
- load_payment_raw.payment_status <= 30
- load_payment_raw.transaction_reference <= 150
- load_payment_raw.source_file <= 500
- load_shipment_raw.tracking_number <= 150
- load_shipment_raw.courier_partner <= 100
- load_shipment_raw.shipment_status <= 30
- load_shipment_raw.source_file <= 500
- load_return_request_raw.return_reason <= 200
- load_return_request_raw.return_status <= 30
- load_return_request_raw.source_file <= 500
- load_warranty_claim_raw.claim_reason <= 200
- load_warranty_claim_raw.claim_status <= 30
- load_warranty_claim_raw.source_file <= 500
- stg_customer.customer_name <= 200
- stg_customer.email <= 320
- stg_customer.phone <= 40
- stg_customer.city <= 100
- stg_customer.region <= 100
- stg_customer.customer_segment <= 50
- stg_customer.source_file <= 500
- stg_brand.brand_name <= 150
- stg_brand.country_of_origin <= 100
- stg_brand.brand_tier <= 30
- stg_brand.source_file <= 500
- stg_collection.collection_name <= 150
- stg_collection.collection_status <= 30
- stg_collection.source_file <= 500
- stg_watch_product.sku <= 80
- stg_watch_product.product_name <= 200
- stg_watch_product.watch_category <= 60
- stg_watch_product.gender_category <= 40
- stg_watch_product.movement_type <= 60
- stg_watch_product.strap_material <= 60
- stg_watch_product.dial_color <= 60
- stg_watch_product.product_status <= 30
- stg_watch_product.source_file <= 500
- stg_warehouse.warehouse_name <= 150
- stg_warehouse.city <= 100
- stg_warehouse.region <= 100
- stg_warehouse.warehouse_type <= 50
- stg_warehouse.source_file <= 500
- stg_inventory.inventory_status <= 30
- stg_inventory.source_file <= 500
- stg_order.order_status <= 30
- stg_order.order_channel <= 30
- stg_order.source_file <= 500
- stg_order_item.source_file <= 500
- stg_payment.payment_method <= 40
- stg_payment.payment_transaction_type <= 30
- stg_payment.payment_status <= 30
- stg_payment.transaction_reference <= 150
- stg_payment.source_file <= 500
- stg_shipment.tracking_number <= 150
- stg_shipment.courier_partner <= 100
- stg_shipment.shipment_status <= 30
- stg_shipment.source_file <= 500
- stg_return_request.return_reason <= 200
- stg_return_request.return_status <= 30
- stg_return_request.source_file <= 500
- stg_warranty_claim.claim_reason <= 200
- stg_warranty_claim.claim_status <= 30
- stg_warranty_claim.source_file <= 500
- dim_date.day_name <= 10
- dim_date.month_name <= 10
- dim_customer.customer_name <= 200
- dim_customer.email <= 320
- dim_customer.phone <= 40
- dim_customer.city <= 100
- dim_customer.region <= 100
- dim_customer.customer_segment <= 50
- dim_brand.brand_name <= 150
- dim_brand.country_of_origin <= 100
- dim_brand.brand_tier <= 30
- dim_collection.collection_name <= 150
- dim_collection.collection_status <= 30
- dim_product.sku <= 80
- dim_product.product_name <= 200
- dim_product.watch_category <= 60
- dim_product.gender_category <= 40
- dim_product.movement_type <= 60
- dim_product.strap_material <= 60
- dim_product.dial_color <= 60
- dim_product.product_status <= 30
- dim_warehouse.warehouse_name <= 150
- dim_warehouse.city <= 100
- dim_warehouse.region <= 100
- dim_warehouse.warehouse_type <= 50
- fact_sales.order_status <= 30
- fact_sales.order_channel <= 30
- fact_inventory_snapshot.inventory_status <= 30
- fact_payment.payment_method <= 40
- fact_payment.payment_transaction_type <= 30
- fact_payment.payment_status <= 30
- fact_payment.transaction_reference <= 150
- fact_payment.order_channel <= 30
- fact_shipment.tracking_number <= 150
- fact_shipment.courier_partner <= 100
- fact_shipment.shipment_status <= 30
- fact_return.return_reason <= 200
- fact_return.return_status <= 30
- fact_warranty_claim.claim_reason <= 200
- fact_warranty_claim.claim_status <= 30
- Generated-short/truncated value count: 0

## Numeric Precision / Scale Rules

- load_watch_product_raw.case_size_mm numeric(6,2)
- load_watch_product_raw.unit_price numeric(14,2)
- load_order_raw.gross_order_amount numeric(14,2)
- load_order_raw.discount_amount numeric(14,2)
- load_order_raw.net_order_amount numeric(14,2)
- load_order_item_raw.unit_price numeric(14,2)
- load_order_item_raw.gross_line_amount numeric(14,2)
- load_order_item_raw.line_discount_amount numeric(14,2)
- load_order_item_raw.line_net_amount numeric(14,2)
- load_payment_raw.payment_amount numeric(14,2)
- load_return_request_raw.refund_amount numeric(14,2)
- load_warranty_claim_raw.service_cost_amount numeric(14,2)
- stg_watch_product.case_size_mm numeric(6,2)
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
- dim_product.case_size_mm numeric(6,2)
- dim_product.list_unit_price numeric(14,2)
- fact_sales.unit_price numeric(14,2)
- fact_sales.gross_line_amount numeric(14,2)
- fact_sales.line_discount_amount numeric(14,2)
- fact_sales.line_net_amount numeric(14,2)
- fact_payment.payment_amount numeric(14,2)
- fact_return.refund_amount numeric(14,2)
- fact_warranty_claim.service_cost_amount numeric(14,2)
- Numeric bounded value count: 0

## CHECK IN Value Source Summary

- No CHECK IN constrained columns generated in this run.

## Foreign Key Relationships

### Parsed

- dim_collection(brand_key) -> dim_brand(brand_key)
- dim_product(brand_key) -> dim_brand(brand_key)
- dim_product(collection_key) -> dim_collection(collection_key)
- fact_sales(order_date_key) -> dim_date(date_key)
- fact_sales(customer_key) -> dim_customer(customer_key)
- fact_sales(product_key) -> dim_product(product_key)
- fact_sales(warehouse_key) -> dim_warehouse(warehouse_key)
- fact_inventory_snapshot(inventory_date_key) -> dim_date(date_key)
- fact_inventory_snapshot(product_key) -> dim_product(product_key)
- fact_inventory_snapshot(warehouse_key) -> dim_warehouse(warehouse_key)
- fact_payment(payment_date_key) -> dim_date(date_key)
- fact_payment(customer_key) -> dim_customer(customer_key)
- fact_shipment(shipment_date_key) -> dim_date(date_key)
- fact_shipment(promised_date_key) -> dim_date(date_key)
- fact_shipment(actual_delivery_date_key) -> dim_date(date_key)
- fact_shipment(customer_key) -> dim_customer(customer_key)
- fact_shipment(warehouse_key) -> dim_warehouse(warehouse_key)
- fact_return(requested_date_key) -> dim_date(date_key)
- fact_return(approved_date_key) -> dim_date(date_key)
- fact_return(refund_date_key) -> dim_date(date_key)
- fact_return(customer_key) -> dim_customer(customer_key)
- fact_return(product_key) -> dim_product(product_key)
- fact_warranty_claim(claim_date_key) -> dim_date(date_key)
- fact_warranty_claim(service_start_date_key) -> dim_date(date_key)
- fact_warranty_claim(service_completion_date_key) -> dim_date(date_key)
- fact_warranty_claim(customer_key) -> dim_customer(customer_key)
- fact_warranty_claim(product_key) -> dim_product(product_key)

### Validated

- dim_collection(brand_key) -> dim_brand(brand_key)
- dim_product(brand_key) -> dim_brand(brand_key)
- dim_product(collection_key) -> dim_collection(collection_key)
- fact_sales(order_date_key) -> dim_date(date_key)
- fact_sales(customer_key) -> dim_customer(customer_key)
- fact_sales(product_key) -> dim_product(product_key)
- fact_sales(warehouse_key) -> dim_warehouse(warehouse_key)
- fact_inventory_snapshot(inventory_date_key) -> dim_date(date_key)
- fact_inventory_snapshot(product_key) -> dim_product(product_key)
- fact_inventory_snapshot(warehouse_key) -> dim_warehouse(warehouse_key)
- fact_payment(payment_date_key) -> dim_date(date_key)
- fact_payment(customer_key) -> dim_customer(customer_key)
- fact_shipment(shipment_date_key) -> dim_date(date_key)
- fact_shipment(promised_date_key) -> dim_date(date_key)
- fact_shipment(actual_delivery_date_key) -> dim_date(date_key)
- fact_shipment(customer_key) -> dim_customer(customer_key)
- fact_shipment(warehouse_key) -> dim_warehouse(warehouse_key)
- fact_return(requested_date_key) -> dim_date(date_key)
- fact_return(approved_date_key) -> dim_date(date_key)
- fact_return(refund_date_key) -> dim_date(date_key)
- fact_return(customer_key) -> dim_customer(customer_key)
- fact_return(product_key) -> dim_product(product_key)
- fact_warranty_claim(claim_date_key) -> dim_date(date_key)
- fact_warranty_claim(service_start_date_key) -> dim_date(date_key)
- fact_warranty_claim(service_completion_date_key) -> dim_date(date_key)
- fact_warranty_claim(customer_key) -> dim_customer(customer_key)
- fact_warranty_claim(product_key) -> dim_product(product_key)

### FK-like Columns Skipped Because No FK Exists in DDL

- load_collection_raw.brand_id
- load_watch_product_raw.brand_id
- load_watch_product_raw.collection_id
- load_inventory_raw.product_id
- load_inventory_raw.warehouse_id
- load_order_raw.customer_id
- load_order_item_raw.order_id
- load_order_item_raw.product_id
- load_order_item_raw.warehouse_id
- load_payment_raw.order_id
- load_shipment_raw.order_id
- load_shipment_raw.warehouse_id
- load_return_request_raw.order_item_id
- load_warranty_claim_raw.order_item_id
- stg_collection.brand_id
- stg_watch_product.brand_id
- stg_watch_product.collection_id
- stg_inventory.product_id
- stg_inventory.warehouse_id
- stg_order.customer_id
- stg_order_item.order_id
- stg_order_item.product_id
- stg_order_item.warehouse_id
- stg_payment.order_id
- stg_shipment.order_id
- stg_shipment.warehouse_id
- stg_return_request.order_item_id
- stg_warranty_claim.order_item_id
- dim_customer.customer_id
- dim_brand.brand_id
- dim_collection.collection_id
- dim_product.product_id
- dim_warehouse.warehouse_id
- fact_sales.order_item_id
- fact_sales.order_id
- fact_inventory_snapshot.inventory_id
- fact_payment.payment_id
- fact_payment.order_id
- fact_shipment.shipment_id
- fact_shipment.order_id
- fact_return.return_id
- fact_return.order_item_id
- fact_return.order_id
- fact_warranty_claim.warranty_claim_id
- fact_warranty_claim.order_item_id
- fact_warranty_claim.order_id

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
- Semantic placeholder checked values: 2000
- Calculation warning count: 0

## Pre-load Validation

Status: **passed_with_warnings**

- No validation errors.
