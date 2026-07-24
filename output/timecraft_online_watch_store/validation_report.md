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

### Checked FK Relationships

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

### FK-like Columns Skipped Because No Parsed FK Exists

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

- Checked values: 1149
- No semantic placeholder errors.

## Row Count Summary

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

## Unsupported Calculation Rules

- None

## Lineage Validation

Status: **passed**
- No lineage errors.

### Lineage Warnings

- stg_customer: no comparable business-key columns found in raw/load sources.
- stg_brand: no comparable business-key columns found in raw/load sources.
- stg_collection: no comparable business-key columns found in raw/load sources.
- stg_watch_product: no comparable business-key columns found in raw/load sources.
- stg_warehouse: no comparable business-key columns found in raw/load sources.
- stg_inventory: no comparable business-key columns found in raw/load sources.
- stg_order: no comparable business-key columns found in raw/load sources.
- stg_order_item: no comparable business-key columns found in raw/load sources.
- stg_payment: no comparable business-key columns found in raw/load sources.
- stg_shipment: no comparable business-key columns found in raw/load sources.
- stg_return_request: no comparable business-key columns found in raw/load sources.
- stg_warranty_claim: no comparable business-key columns found in raw/load sources.
- dim_date: no staging lineage source available for validation.

### Lineage Checks

- dim_customer.customer_id values exist in staging sources stg_customer.
- dim_brand.brand_id values exist in staging sources stg_brand.
- dim_collection.collection_id values exist in staging sources stg_collection.
- dim_product.product_id values exist in staging sources stg_watch_product.
- dim_warehouse.warehouse_id values exist in staging sources stg_warehouse.
- dim_order.order_id values exist in staging sources stg_order.
- fact_sales.order_key resolves to dimension dim_order.
- fact_sales.customer_key resolves to dimension dim_customer.
- fact_sales.product_key resolves to dimension dim_product.
- fact_sales.warehouse_key resolves to dimension dim_warehouse.
- fact_sales.order_date_key resolves to dimension dim_date.
- fact_inventory.product_key resolves to dimension dim_product.
- fact_inventory.warehouse_key resolves to dimension dim_warehouse.
- fact_inventory.inventory_date_key resolves to dimension dim_date.
- fact_payment.order_key resolves to dimension dim_order.
- fact_payment.customer_key resolves to dimension dim_customer.
- fact_payment.payment_date_key resolves to dimension dim_date.
- fact_delivery.order_key resolves to dimension dim_order.
- fact_delivery.customer_key resolves to dimension dim_customer.
- fact_delivery.warehouse_key resolves to dimension dim_warehouse.
- fact_delivery.shipment_date_key resolves to dimension dim_date.
- fact_delivery.promised_delivery_date_key resolves to dimension dim_date.
- fact_delivery.actual_delivery_date_key resolves to dimension dim_date.
- fact_return.order_key resolves to dimension dim_order.
- fact_return.customer_key resolves to dimension dim_customer.
- fact_return.product_key resolves to dimension dim_product.
- fact_return.requested_date_key resolves to dimension dim_date.
- fact_return.approved_date_key resolves to dimension dim_date.
- fact_return.refund_date_key resolves to dimension dim_date.
- fact_claim.order_key resolves to dimension dim_order.
- fact_claim.customer_key resolves to dimension dim_customer.
- fact_claim.product_key resolves to dimension dim_product.
- fact_claim.claim_date_key resolves to dimension dim_date.
- fact_claim.service_start_date_key resolves to dimension dim_date.
- fact_claim.service_completion_date_key resolves to dimension dim_date.

## Data Realism Validation

Status: **passed**
- Check: Temporal span: 146 days across 11 distinct dates.
- Check: stg_collection -> stg_brand: 6 child rows, 6 referenced parents, 0 reused parents.
- Check: stg_watch_product -> stg_brand: 5 child rows, 5 referenced parents, 0 reused parents.
- Check: stg_watch_product -> stg_collection: 5 child rows, 5 referenced parents, 0 reused parents.
- Check: stg_inventory -> stg_watch_product: 10 child rows, 5 referenced parents, 5 reused parents.
- Check: stg_inventory -> stg_warehouse: 10 child rows, 5 referenced parents, 3 reused parents.
- Check: stg_order -> stg_customer: 10 child rows, 5 referenced parents, 2 reused parents.
- Check: stg_order_item -> stg_order: 30 child rows, 10 referenced parents, 10 reused parents.
- Check: stg_order_item -> stg_watch_product: 30 child rows, 5 referenced parents, 5 reused parents.
- Check: stg_order_item -> stg_warehouse: 30 child rows, 5 referenced parents, 5 reused parents.
- Check: stg_payment -> stg_order: 10 child rows, 10 referenced parents, 0 reused parents.
- Check: stg_shipment -> stg_order: 10 child rows, 10 referenced parents, 0 reused parents.
- Check: stg_shipment -> stg_warehouse: 10 child rows, 5 referenced parents, 3 reused parents.
- Check: stg_return_request -> stg_order_item: 10 child rows, 10 referenced parents, 0 reused parents.
- Check: stg_warranty_claim -> stg_order_item: 10 child rows, 10 referenced parents, 0 reused parents.
- Check: dim_collection -> dim_brand: 6 child rows, 6 referenced parents, 0 reused parents.
- Check: dim_product -> dim_brand: 5 child rows, 5 referenced parents, 0 reused parents.
- Check: dim_product -> dim_collection: 5 child rows, 5 referenced parents, 0 reused parents.
- Check: dim_order -> dim_customer: 10 child rows, 5 referenced parents, 2 reused parents.
- Check: dim_order -> dim_date: 10 child rows, 6 referenced parents, 4 reused parents.
- Check: fact_sales -> dim_order: 10 child rows, 10 referenced parents, 0 reused parents.
- Check: fact_sales -> dim_customer: 10 child rows, 5 referenced parents, 2 reused parents.
- Check: fact_sales -> dim_product: 10 child rows, 4 referenced parents, 3 reused parents.
- Check: fact_sales -> dim_warehouse: 10 child rows, 5 referenced parents, 3 reused parents.
- Check: fact_sales -> dim_date: 10 child rows, 6 referenced parents, 4 reused parents.
- Check: fact_inventory -> dim_product: 10 child rows, 5 referenced parents, 5 reused parents.
- Check: fact_inventory -> dim_warehouse: 10 child rows, 5 referenced parents, 3 reused parents.
- Check: fact_inventory -> dim_date: 10 child rows, 6 referenced parents, 4 reused parents.
- Check: fact_payment -> dim_order: 10 child rows, 10 referenced parents, 0 reused parents.
- Check: fact_payment -> dim_customer: 10 child rows, 5 referenced parents, 2 reused parents.
- Check: fact_payment -> dim_date: 10 child rows, 6 referenced parents, 4 reused parents.
- Check: fact_delivery -> dim_order: 10 child rows, 10 referenced parents, 0 reused parents.
- Check: fact_delivery -> dim_customer: 10 child rows, 5 referenced parents, 2 reused parents.
- Check: fact_delivery -> dim_warehouse: 10 child rows, 5 referenced parents, 3 reused parents.
- Check: fact_delivery -> dim_date: 10 child rows, 6 referenced parents, 4 reused parents.
- Check: fact_delivery -> dim_date: 10 child rows, 5 referenced parents, 4 reused parents.
- Check: fact_delivery -> dim_date: 10 child rows, 5 referenced parents, 3 reused parents.
- Check: fact_return -> fact_sales: 10 child rows, 10 referenced parents, 0 reused parents.
- Check: fact_return -> dim_order: 10 child rows, 10 referenced parents, 0 reused parents.
- Check: fact_return -> dim_customer: 10 child rows, 5 referenced parents, 2 reused parents.
- Check: fact_return -> dim_product: 10 child rows, 4 referenced parents, 3 reused parents.
- Check: fact_return -> dim_date: 10 child rows, 4 referenced parents, 2 reused parents.
- Check: fact_return -> dim_date: 10 child rows, 4 referenced parents, 1 reused parents, 5 nullable FK row(s) skipped.
- Check: fact_return -> dim_date: 10 child rows, 3 referenced parents, 0 reused parents, 7 nullable FK row(s) skipped.
- Check: fact_claim -> fact_sales: 10 child rows, 10 referenced parents, 0 reused parents.
- Check: fact_claim -> dim_order: 10 child rows, 10 referenced parents, 0 reused parents.
- Check: fact_claim -> dim_customer: 10 child rows, 5 referenced parents, 2 reused parents.
- Check: fact_claim -> dim_product: 10 child rows, 4 referenced parents, 3 reused parents.
- Check: fact_claim -> dim_date: 10 child rows, 4 referenced parents, 2 reused parents.
- Check: fact_claim -> dim_date: 10 child rows, 3 referenced parents, 0 reused parents, 7 nullable FK row(s) skipped.
- Check: fact_claim -> dim_date: 10 child rows, 2 referenced parents, 0 reused parents, 8 nullable FK row(s) skipped.

## PostgreSQL Validation

Status: **passed**

- No validation errors.
