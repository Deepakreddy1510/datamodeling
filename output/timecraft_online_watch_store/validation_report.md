# Validation Report

- Final status: **passed_with_warnings**
- DDL validation status: **passed**
- Fallback inference count: 0
- Semantic type count: 0
- Placeholder warning count: 0
- Semantic placeholder validation status: **passed**

## Pre-load Validation

Status: **passed_with_warnings**

- No validation errors.

## FK Validation Coverage

### Parsed FK Relationships

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

### Checked FK Relationships

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

### FK-like Columns Skipped Because No Parsed FK Exists

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

## Unique Constraint Adjustments

- FK-safe: None
- Composite: None

## Data Type Validation

- No data type errors.

## Constraint Validation

- No constraint errors.

## Calculation Validation

- No calculation errors.

## Date Rule Validation

- No date rule errors.

## Boolean Rule Validation

- No boolean rule errors.

## Placeholder Validation

- No placeholder warnings.

## Semantic Placeholder Validation

- Checked values: 2000
- No semantic placeholder errors.

## Row Count Summary

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

## Unsupported Calculation Rules

- None

## Lineage Validation

Status: **passed**
- No lineage errors.

### Lineage Warnings

- dim_date: no staging lineage source available for validation.

### Lineage Checks

- stg_customer.customer_id values exist in raw/load sources load_customer_raw.
- stg_customer.customer_name values exist in raw/load sources load_customer_raw.
- stg_customer.email values exist in raw/load sources load_customer_raw.
- stg_customer.phone values exist in raw/load sources load_customer_raw.
- stg_customer.city values exist in raw/load sources load_customer_raw.
- stg_customer.region values exist in raw/load sources load_customer_raw.
- stg_customer.customer_segment values exist in raw/load sources load_customer_raw.
- stg_customer.signup_date values exist in raw/load sources load_customer_raw.
- stg_customer.is_active values exist in raw/load sources load_customer_raw.
- stg_customer.source_file values exist in raw/load sources load_customer_raw.
- stg_customer.loaded_at values exist in raw/load sources load_customer_raw.
- stg_brand.brand_id values exist in raw/load sources load_brand_raw.
- stg_brand.brand_name values exist in raw/load sources load_brand_raw.
- stg_brand.country_of_origin values exist in raw/load sources load_brand_raw.
- stg_brand.brand_tier values exist in raw/load sources load_brand_raw.
- stg_brand.is_active values exist in raw/load sources load_brand_raw.
- stg_brand.source_file values exist in raw/load sources load_brand_raw.
- stg_brand.loaded_at values exist in raw/load sources load_brand_raw.
- stg_collection.brand_id values exist in raw/load sources load_collection_raw.
- stg_watch_product.brand_id values exist in raw/load sources load_watch_product_raw.
- stg_watch_product.collection_id values exist in raw/load sources load_watch_product_raw.
- stg_warehouse.warehouse_id values exist in raw/load sources load_warehouse_raw.
- stg_warehouse.warehouse_name values exist in raw/load sources load_warehouse_raw.
- stg_warehouse.city values exist in raw/load sources load_warehouse_raw.
- stg_warehouse.region values exist in raw/load sources load_warehouse_raw.
- stg_warehouse.warehouse_type values exist in raw/load sources load_warehouse_raw.
- stg_warehouse.is_active values exist in raw/load sources load_warehouse_raw.
- stg_warehouse.source_file values exist in raw/load sources load_warehouse_raw.
- stg_warehouse.loaded_at values exist in raw/load sources load_warehouse_raw.
- stg_inventory.product_id values exist in raw/load sources load_inventory_raw.
- stg_inventory.warehouse_id values exist in raw/load sources load_inventory_raw.
- stg_order.customer_id values exist in raw/load sources load_order_raw.
- stg_order_item.order_id values exist in raw/load sources load_order_item_raw.
- stg_order_item.product_id values exist in raw/load sources load_order_item_raw.
- stg_order_item.warehouse_id values exist in raw/load sources load_order_item_raw.
- stg_payment.order_id values exist in raw/load sources load_payment_raw.
- stg_shipment.order_id values exist in raw/load sources load_shipment_raw.
- stg_shipment.warehouse_id values exist in raw/load sources load_shipment_raw.
- stg_shipment.tracking_number values exist in raw/load sources load_shipment_raw.
- stg_return_request.order_item_id values exist in raw/load sources load_return_request_raw.
- stg_warranty_claim.order_item_id values exist in raw/load sources load_warranty_claim_raw.
- dim_customer.customer_id values exist in staging sources stg_customer.
- dim_brand.brand_id values exist in staging sources stg_brand.
- dim_collection.collection_id values exist in staging sources stg_collection.
- dim_product.product_id values exist in staging sources stg_watch_product.
- dim_warehouse.warehouse_id values exist in staging sources stg_warehouse.
- fact_sales.order_date_key resolves to dimension dim_date.
- fact_sales.customer_key resolves to dimension dim_customer.
- fact_sales.product_key resolves to dimension dim_product.
- fact_sales.warehouse_key resolves to dimension dim_warehouse.
- fact_inventory_snapshot.inventory_date_key resolves to dimension dim_date.
- fact_inventory_snapshot.product_key resolves to dimension dim_product.
- fact_inventory_snapshot.warehouse_key resolves to dimension dim_warehouse.
- fact_payment.payment_date_key resolves to dimension dim_date.
- fact_payment.customer_key resolves to dimension dim_customer.
- fact_shipment.shipment_date_key resolves to dimension dim_date.
- fact_shipment.promised_date_key resolves to dimension dim_date.
- fact_shipment.actual_delivery_date_key resolves to dimension dim_date.
- fact_shipment.customer_key resolves to dimension dim_customer.
- fact_shipment.warehouse_key resolves to dimension dim_warehouse.
- fact_return.requested_date_key resolves to dimension dim_date.
- fact_return.approved_date_key resolves to dimension dim_date.
- fact_return.refund_date_key resolves to dimension dim_date.
- fact_return.customer_key resolves to dimension dim_customer.
- fact_return.product_key resolves to dimension dim_product.
- fact_warranty_claim.claim_date_key resolves to dimension dim_date.
- fact_warranty_claim.service_start_date_key resolves to dimension dim_date.
- fact_warranty_claim.service_completion_date_key resolves to dimension dim_date.
- fact_warranty_claim.customer_key resolves to dimension dim_customer.
- fact_warranty_claim.product_key resolves to dimension dim_product.

## Data Realism Validation

Status: **passed**
- Check: Temporal span: 40 days across 6 distinct dates.
- Check: dim_collection -> dim_brand: 6 child rows, 6 referenced parents, 0 reused parents.
- Check: dim_product -> dim_brand: 6 child rows, 6 referenced parents, 0 reused parents.
- Check: dim_product -> dim_collection: 6 child rows, 6 referenced parents, 0 reused parents.
- Check: fact_sales -> dim_date: 30 child rows, 4 referenced parents, 4 reused parents.
- Check: fact_sales -> dim_customer: 30 child rows, 6 referenced parents, 6 reused parents.
- Check: fact_sales -> dim_product: 30 child rows, 6 referenced parents, 6 reused parents.
- Check: fact_sales -> dim_warehouse: 30 child rows, 6 referenced parents, 5 reused parents.
- Check: fact_inventory_snapshot -> dim_date: 10 child rows, 6 referenced parents, 4 reused parents.
- Check: fact_inventory_snapshot -> dim_product: 10 child rows, 6 referenced parents, 3 reused parents.
- Check: fact_inventory_snapshot -> dim_warehouse: 10 child rows, 6 referenced parents, 3 reused parents.
- Check: fact_payment -> dim_date: 10 child rows, 5 referenced parents, 3 reused parents.
- Check: fact_payment -> dim_customer: 10 child rows, 6 referenced parents, 2 reused parents.
- Check: fact_shipment -> dim_date: 10 child rows, 4 referenced parents, 4 reused parents.
- Check: fact_shipment -> dim_date: 10 child rows, 4 referenced parents, 4 reused parents.
- Check: fact_shipment -> dim_date: 10 child rows, 4 referenced parents, 3 reused parents.
- Check: fact_shipment -> dim_customer: 10 child rows, 6 referenced parents, 2 reused parents.
- Check: fact_shipment -> dim_warehouse: 10 child rows, 3 referenced parents, 2 reused parents.
- Check: fact_return -> dim_date: 10 child rows, 3 referenced parents, 3 reused parents.
- Check: fact_return -> dim_date: 10 child rows, 3 referenced parents, 2 reused parents, 4 nullable FK row(s) skipped.
- Check: fact_return -> dim_date: 10 child rows, 2 referenced parents, 1 reused parents, 7 nullable FK row(s) skipped.
- Check: fact_return -> dim_customer: 10 child rows, 6 referenced parents, 2 reused parents.
- Check: fact_return -> dim_product: 10 child rows, 4 referenced parents, 3 reused parents.
- Check: fact_warranty_claim -> dim_date: 10 child rows, 3 referenced parents, 3 reused parents.
- Check: fact_warranty_claim -> dim_date: 10 child rows, 3 referenced parents, 1 reused parents, 6 nullable FK row(s) skipped.
- Check: fact_warranty_claim -> dim_date: 10 child rows, 2 referenced parents, 1 reused parents, 7 nullable FK row(s) skipped.
- Check: fact_warranty_claim -> dim_customer: 10 child rows, 6 referenced parents, 2 reused parents.
- Check: fact_warranty_claim -> dim_product: 10 child rows, 4 referenced parents, 3 reused parents.

## PostgreSQL Validation

Status: **passed**

- No validation errors.
