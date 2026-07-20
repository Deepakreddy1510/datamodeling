# Business Input Summary

TimeCraft Online Watch Store requires a PostgreSQL dimensional warehouse for sales, customer, product, inventory, payment, shipment, return, refund, and warranty analytics. The mandatory lineage is raw_load -> staging -> dimension/fact -> reporting. All data and brand names used for demonstrations must be fictional.

# Conceptual Data Model

Core master entities are Customer, Brand, Collection, Watch Product, and Warehouse. Transaction and event entities are Inventory, Order, Order Item, Payment, Shipment, Return Request, and Warranty Claim. Customers place orders; orders contain items and have payments and shipments; products belong to brands and collections; warehouses hold inventory and fulfil items and shipments; delivered items may have returns and warranty claims.

# Logical Data Model

The warehouse uses conformed dimensions for date, customer, brand, collection, product, and warehouse. Facts have these grains:

| Fact | Grain | Principal Measures |
|---|---|---|
| fact_sales | One row per order item | quantity, unit price, gross, discount, net |
| fact_inventory_snapshot | One product, warehouse, and inventory date | on hand, reserved, available, reorder level |
| fact_payment | One payment transaction or attempt | payment amount |
| fact_shipment | One shipment | delivery delay days |
| fact_return | One return request | return quantity, refund amount |
| fact_warranty_claim | One warranty claim | service cost, resolution days |

Orders are retained as a degenerate dimension on relevant facts through order_id. Product contains denormalized brand and collection keys for efficient star-schema reporting while separate brand and collection dimensions remain available.

# Physical PostgreSQL Data Model

| Layer | Tables |
|---|---|
| raw_load | load_customer_raw, load_brand_raw, load_collection_raw, load_watch_product_raw, load_warehouse_raw, load_inventory_raw, load_order_raw, load_order_item_raw, load_payment_raw, load_shipment_raw, load_return_request_raw, load_warranty_claim_raw |
| staging | Matching stg_customer, stg_brand, stg_collection, stg_watch_product, stg_warehouse, stg_inventory, stg_order, stg_order_item, stg_payment, stg_shipment, stg_return_request, stg_warranty_claim |
| dimension | dim_date, dim_customer, dim_brand, dim_collection, dim_product, dim_warehouse |
| fact | fact_sales, fact_inventory_snapshot, fact_payment, fact_shipment, fact_return, fact_warranty_claim |
| reporting | Nine vw_* reporting views |

# SQL DDL

```sql
CREATE SCHEMA IF NOT EXISTS raw_load;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dimensional;
CREATE SCHEMA IF NOT EXISTS reporting;

CREATE TABLE raw_load.load_customer_raw (
 customer_id bigint NOT NULL, customer_name varchar(200) NOT NULL, email varchar(320) NOT NULL,
 phone varchar(40), city varchar(100), region varchar(100), customer_segment varchar(50) NOT NULL,
 signup_date date NOT NULL, is_active boolean NOT NULL, source_file varchar(500),
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY (customer_id)
);
CREATE TABLE raw_load.load_brand_raw (
 brand_id bigint NOT NULL, brand_name varchar(150) NOT NULL, country_of_origin varchar(100),
 brand_tier varchar(30) NOT NULL, is_active boolean NOT NULL, source_file varchar(500),
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY (brand_id)
);
CREATE TABLE raw_load.load_collection_raw (
 collection_id bigint NOT NULL, brand_id bigint NOT NULL, collection_name varchar(150) NOT NULL,
 launch_year integer, collection_status varchar(30) NOT NULL, source_file varchar(500),
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY (collection_id)
);
CREATE TABLE raw_load.load_watch_product_raw (
 product_id bigint NOT NULL, brand_id bigint NOT NULL, collection_id bigint NOT NULL,
 sku varchar(80) NOT NULL, product_name varchar(200) NOT NULL, watch_category varchar(60) NOT NULL,
 gender_category varchar(40), movement_type varchar(60), strap_material varchar(60), dial_color varchar(60),
 case_size_mm numeric(6,2), water_resistance_metres integer, unit_price numeric(14,2) NOT NULL,
 warranty_months integer NOT NULL, product_status varchar(30) NOT NULL, source_file varchar(500),
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY (product_id)
);
CREATE TABLE raw_load.load_warehouse_raw (
 warehouse_id bigint NOT NULL, warehouse_name varchar(150) NOT NULL, city varchar(100), region varchar(100),
 warehouse_type varchar(50) NOT NULL, is_active boolean NOT NULL, source_file varchar(500),
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY (warehouse_id)
);
CREATE TABLE raw_load.load_inventory_raw (
 inventory_id bigint NOT NULL, product_id bigint NOT NULL, warehouse_id bigint NOT NULL,
 inventory_date date NOT NULL, on_hand_quantity integer NOT NULL, reserved_quantity integer NOT NULL,
 available_quantity integer NOT NULL, reorder_level integer NOT NULL, inventory_status varchar(30) NOT NULL,
 source_file varchar(500), loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY (inventory_id)
);
CREATE TABLE raw_load.load_order_raw (
 order_id bigint NOT NULL, customer_id bigint NOT NULL, order_date date NOT NULL, order_status varchar(30) NOT NULL,
 order_channel varchar(30) NOT NULL, gross_order_amount numeric(14,2) NOT NULL,
 discount_amount numeric(14,2) NOT NULL, net_order_amount numeric(14,2) NOT NULL,
 source_file varchar(500), loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY (order_id)
);
CREATE TABLE raw_load.load_order_item_raw (
 order_item_id bigint NOT NULL, order_id bigint NOT NULL, product_id bigint NOT NULL, warehouse_id bigint NOT NULL,
 quantity integer NOT NULL, unit_price numeric(14,2) NOT NULL, gross_line_amount numeric(14,2) NOT NULL,
 line_discount_amount numeric(14,2) NOT NULL, line_net_amount numeric(14,2) NOT NULL,
 source_file varchar(500), loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY (order_item_id)
);
CREATE TABLE raw_load.load_payment_raw (
 payment_id bigint NOT NULL, order_id bigint NOT NULL, payment_date date NOT NULL,
 payment_method varchar(40) NOT NULL, payment_transaction_type varchar(30) NOT NULL,
 payment_status varchar(30) NOT NULL, payment_amount numeric(14,2) NOT NULL,
 transaction_reference varchar(150) NOT NULL, source_file varchar(500),
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY (payment_id)
);
CREATE TABLE raw_load.load_shipment_raw (
 shipment_id bigint NOT NULL, order_id bigint NOT NULL, warehouse_id bigint NOT NULL,
 tracking_number varchar(150) NOT NULL, courier_partner varchar(100) NOT NULL, shipment_date date NOT NULL,
 promised_delivery_date date NOT NULL, actual_delivery_date date, shipment_status varchar(30) NOT NULL,
 delivery_delay_days integer NOT NULL, source_file varchar(500),
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY (shipment_id)
);
CREATE TABLE raw_load.load_return_request_raw (
 return_id bigint NOT NULL, order_item_id bigint NOT NULL, return_quantity integer NOT NULL,
 return_reason varchar(200) NOT NULL, return_status varchar(30) NOT NULL, requested_date date NOT NULL,
 approved_date date, refund_date date, refund_amount numeric(14,2) NOT NULL,
 source_file varchar(500), loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY (return_id)
);
CREATE TABLE raw_load.load_warranty_claim_raw (
 warranty_claim_id bigint NOT NULL, order_item_id bigint NOT NULL, claim_reason varchar(200) NOT NULL,
 claim_status varchar(30) NOT NULL, claim_date date NOT NULL, service_start_date date,
 service_completion_date date, service_cost_amount numeric(14,2) NOT NULL,
 resolution_description text, source_file varchar(500),
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY (warranty_claim_id)
);

CREATE TABLE staging.stg_customer (LIKE raw_load.load_customer_raw INCLUDING ALL);
CREATE TABLE staging.stg_brand (LIKE raw_load.load_brand_raw INCLUDING ALL);
CREATE TABLE staging.stg_collection (LIKE raw_load.load_collection_raw INCLUDING ALL);
CREATE TABLE staging.stg_watch_product (LIKE raw_load.load_watch_product_raw INCLUDING ALL);
CREATE TABLE staging.stg_warehouse (LIKE raw_load.load_warehouse_raw INCLUDING ALL);
CREATE TABLE staging.stg_inventory (LIKE raw_load.load_inventory_raw INCLUDING ALL);
CREATE TABLE staging.stg_order (LIKE raw_load.load_order_raw INCLUDING ALL);
CREATE TABLE staging.stg_order_item (LIKE raw_load.load_order_item_raw INCLUDING ALL);
CREATE TABLE staging.stg_payment (LIKE raw_load.load_payment_raw INCLUDING ALL);
CREATE TABLE staging.stg_shipment (LIKE raw_load.load_shipment_raw INCLUDING ALL);
CREATE TABLE staging.stg_return_request (LIKE raw_load.load_return_request_raw INCLUDING ALL);
CREATE TABLE staging.stg_warranty_claim (LIKE raw_load.load_warranty_claim_raw INCLUDING ALL);

ALTER TABLE staging.stg_brand ADD CONSTRAINT uq_stg_brand_name UNIQUE (brand_name);
ALTER TABLE staging.stg_customer ADD CONSTRAINT uq_stg_customer_email UNIQUE (email);
ALTER TABLE staging.stg_collection ADD CONSTRAINT fk_stg_collection_brand FOREIGN KEY (brand_id) REFERENCES staging.stg_brand(brand_id);
ALTER TABLE staging.stg_collection ADD CONSTRAINT uq_stg_collection UNIQUE (brand_id, collection_name);
ALTER TABLE staging.stg_watch_product ADD CONSTRAINT fk_stg_product_brand FOREIGN KEY (brand_id) REFERENCES staging.stg_brand(brand_id);
ALTER TABLE staging.stg_watch_product ADD CONSTRAINT fk_stg_product_collection FOREIGN KEY (collection_id) REFERENCES staging.stg_collection(collection_id);
ALTER TABLE staging.stg_watch_product ADD CONSTRAINT uq_stg_product_sku UNIQUE (sku);
ALTER TABLE staging.stg_watch_product ADD CONSTRAINT ck_stg_product_values CHECK (unit_price >= 0 AND warranty_months >= 0 AND case_size_mm > 0 AND water_resistance_metres >= 0);
ALTER TABLE staging.stg_inventory ADD CONSTRAINT fk_stg_inventory_product FOREIGN KEY (product_id) REFERENCES staging.stg_watch_product(product_id);
ALTER TABLE staging.stg_inventory ADD CONSTRAINT fk_stg_inventory_warehouse FOREIGN KEY (warehouse_id) REFERENCES staging.stg_warehouse(warehouse_id);
ALTER TABLE staging.stg_inventory ADD CONSTRAINT uq_stg_inventory UNIQUE (product_id, warehouse_id, inventory_date);
ALTER TABLE staging.stg_inventory ADD CONSTRAINT ck_stg_inventory CHECK (on_hand_quantity >= 0 AND reserved_quantity >= 0 AND available_quantity >= 0 AND reorder_level >= 0 AND available_quantity = on_hand_quantity - reserved_quantity);
ALTER TABLE staging.stg_order ADD CONSTRAINT fk_stg_order_customer FOREIGN KEY (customer_id) REFERENCES staging.stg_customer(customer_id);
ALTER TABLE staging.stg_order ADD CONSTRAINT ck_stg_order_amounts CHECK (gross_order_amount >= 0 AND discount_amount >= 0 AND net_order_amount = gross_order_amount - discount_amount);
ALTER TABLE staging.stg_order_item ADD CONSTRAINT fk_stg_item_order FOREIGN KEY (order_id) REFERENCES staging.stg_order(order_id);
ALTER TABLE staging.stg_order_item ADD CONSTRAINT fk_stg_item_product FOREIGN KEY (product_id) REFERENCES staging.stg_watch_product(product_id);
ALTER TABLE staging.stg_order_item ADD CONSTRAINT fk_stg_item_warehouse FOREIGN KEY (warehouse_id) REFERENCES staging.stg_warehouse(warehouse_id);
ALTER TABLE staging.stg_order_item ADD CONSTRAINT ck_stg_item_amounts CHECK (quantity > 0 AND unit_price >= 0 AND gross_line_amount = quantity * unit_price AND line_discount_amount >= 0 AND line_net_amount = gross_line_amount - line_discount_amount);
ALTER TABLE staging.stg_payment ADD CONSTRAINT fk_stg_payment_order FOREIGN KEY (order_id) REFERENCES staging.stg_order(order_id);
ALTER TABLE staging.stg_payment ADD CONSTRAINT uq_stg_payment_reference UNIQUE (transaction_reference);
ALTER TABLE staging.stg_payment ADD CONSTRAINT ck_stg_payment_amount CHECK (payment_amount >= 0);
ALTER TABLE staging.stg_shipment ADD CONSTRAINT fk_stg_shipment_order FOREIGN KEY (order_id) REFERENCES staging.stg_order(order_id);
ALTER TABLE staging.stg_shipment ADD CONSTRAINT fk_stg_shipment_warehouse FOREIGN KEY (warehouse_id) REFERENCES staging.stg_warehouse(warehouse_id);
ALTER TABLE staging.stg_shipment ADD CONSTRAINT uq_stg_tracking UNIQUE (tracking_number);
ALTER TABLE staging.stg_shipment ADD CONSTRAINT ck_stg_shipment_dates CHECK (promised_delivery_date >= shipment_date AND actual_delivery_date IS NULL OR actual_delivery_date >= shipment_date);
ALTER TABLE staging.stg_shipment ADD CONSTRAINT ck_stg_shipment_delivery CHECK (delivery_delay_days >= 0 AND ((shipment_status = 'delivered' AND actual_delivery_date IS NOT NULL) OR (shipment_status <> 'delivered' AND actual_delivery_date IS NULL)));
ALTER TABLE staging.stg_return_request ADD CONSTRAINT fk_stg_return_item FOREIGN KEY (order_item_id) REFERENCES staging.stg_order_item(order_item_id);
ALTER TABLE staging.stg_return_request ADD CONSTRAINT ck_stg_return CHECK (return_quantity > 0 AND refund_amount >= 0 AND (approved_date IS NULL OR approved_date >= requested_date) AND (refund_date IS NULL OR refund_date >= requested_date));
ALTER TABLE staging.stg_warranty_claim ADD CONSTRAINT fk_stg_claim_item FOREIGN KEY (order_item_id) REFERENCES staging.stg_order_item(order_item_id);
ALTER TABLE staging.stg_warranty_claim ADD CONSTRAINT ck_stg_claim CHECK (service_cost_amount >= 0 AND (service_start_date IS NULL OR service_start_date >= claim_date) AND (service_completion_date IS NULL OR service_start_date IS NOT NULL AND service_completion_date >= service_start_date));

CREATE TABLE dimensional.dim_date (
 date_key integer PRIMARY KEY, full_date date NOT NULL UNIQUE, day_of_week smallint NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
 day_name varchar(10) NOT NULL, month_number smallint NOT NULL CHECK (month_number BETWEEN 1 AND 12),
 month_name varchar(10) NOT NULL, quarter_number smallint NOT NULL CHECK (quarter_number BETWEEN 1 AND 4),
 calendar_year integer NOT NULL, is_weekend boolean NOT NULL
);
CREATE TABLE dimensional.dim_customer (
 customer_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, customer_id bigint NOT NULL UNIQUE,
 customer_name varchar(200) NOT NULL, email varchar(320) NOT NULL, phone varchar(40), city varchar(100),
 region varchar(100), customer_segment varchar(50) NOT NULL, signup_date date NOT NULL, is_active boolean NOT NULL
);
CREATE TABLE dimensional.dim_brand (
 brand_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, brand_id bigint NOT NULL UNIQUE,
 brand_name varchar(150) NOT NULL UNIQUE, country_of_origin varchar(100), brand_tier varchar(30) NOT NULL, is_active boolean NOT NULL
);
CREATE TABLE dimensional.dim_collection (
 collection_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, collection_id bigint NOT NULL UNIQUE,
 brand_key bigint NOT NULL REFERENCES dimensional.dim_brand(brand_key), collection_name varchar(150) NOT NULL,
 launch_year integer, collection_status varchar(30) NOT NULL, UNIQUE (brand_key, collection_name)
);
CREATE TABLE dimensional.dim_product (
 product_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, product_id bigint NOT NULL UNIQUE,
 brand_key bigint NOT NULL REFERENCES dimensional.dim_brand(brand_key),
 collection_key bigint NOT NULL REFERENCES dimensional.dim_collection(collection_key), sku varchar(80) NOT NULL UNIQUE,
 product_name varchar(200) NOT NULL, watch_category varchar(60) NOT NULL, gender_category varchar(40),
 movement_type varchar(60), strap_material varchar(60), dial_color varchar(60), case_size_mm numeric(6,2),
 water_resistance_metres integer, list_unit_price numeric(14,2) NOT NULL CHECK (list_unit_price >= 0),
 warranty_months integer NOT NULL CHECK (warranty_months >= 0), product_status varchar(30) NOT NULL
);
CREATE TABLE dimensional.dim_warehouse (
 warehouse_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, warehouse_id bigint NOT NULL UNIQUE,
 warehouse_name varchar(150) NOT NULL, city varchar(100), region varchar(100), warehouse_type varchar(50) NOT NULL,
 is_active boolean NOT NULL
);

CREATE TABLE dimensional.fact_sales (
 sales_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, order_item_id bigint NOT NULL UNIQUE,
 order_id bigint NOT NULL, order_date_key integer NOT NULL REFERENCES dimensional.dim_date(date_key),
 customer_key bigint NOT NULL REFERENCES dimensional.dim_customer(customer_key),
 product_key bigint NOT NULL REFERENCES dimensional.dim_product(product_key),
 warehouse_key bigint NOT NULL REFERENCES dimensional.dim_warehouse(warehouse_key),
 order_status varchar(30) NOT NULL, order_channel varchar(30) NOT NULL, quantity integer NOT NULL CHECK (quantity > 0),
 unit_price numeric(14,2) NOT NULL CHECK (unit_price >= 0), gross_line_amount numeric(14,2) NOT NULL,
 line_discount_amount numeric(14,2) NOT NULL, line_net_amount numeric(14,2) NOT NULL,
 CHECK (gross_line_amount = quantity * unit_price AND line_net_amount = gross_line_amount - line_discount_amount)
);
CREATE TABLE dimensional.fact_inventory_snapshot (
 inventory_snapshot_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, inventory_id bigint NOT NULL UNIQUE,
 inventory_date_key integer NOT NULL REFERENCES dimensional.dim_date(date_key),
 product_key bigint NOT NULL REFERENCES dimensional.dim_product(product_key),
 warehouse_key bigint NOT NULL REFERENCES dimensional.dim_warehouse(warehouse_key),
 on_hand_quantity integer NOT NULL, reserved_quantity integer NOT NULL, available_quantity integer NOT NULL,
 reorder_level integer NOT NULL, inventory_status varchar(30) NOT NULL,
 UNIQUE (inventory_date_key, product_key, warehouse_key),
 CHECK (on_hand_quantity >= 0 AND reserved_quantity >= 0 AND available_quantity = on_hand_quantity - reserved_quantity AND reorder_level >= 0)
);
CREATE TABLE dimensional.fact_payment (
 payment_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, payment_id bigint NOT NULL UNIQUE, order_id bigint NOT NULL,
 payment_date_key integer NOT NULL REFERENCES dimensional.dim_date(date_key),
 customer_key bigint NOT NULL REFERENCES dimensional.dim_customer(customer_key), payment_method varchar(40) NOT NULL,
 payment_transaction_type varchar(30) NOT NULL, payment_status varchar(30) NOT NULL,
 payment_amount numeric(14,2) NOT NULL CHECK (payment_amount >= 0), transaction_reference varchar(150) NOT NULL UNIQUE,
 order_channel varchar(30) NOT NULL
);
CREATE TABLE dimensional.fact_shipment (
 shipment_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, shipment_id bigint NOT NULL UNIQUE, order_id bigint NOT NULL,
 shipment_date_key integer NOT NULL REFERENCES dimensional.dim_date(date_key),
 promised_date_key integer NOT NULL REFERENCES dimensional.dim_date(date_key),
 actual_delivery_date_key integer REFERENCES dimensional.dim_date(date_key),
 customer_key bigint NOT NULL REFERENCES dimensional.dim_customer(customer_key),
 warehouse_key bigint NOT NULL REFERENCES dimensional.dim_warehouse(warehouse_key),
 tracking_number varchar(150) NOT NULL UNIQUE, courier_partner varchar(100) NOT NULL,
 shipment_status varchar(30) NOT NULL, delivery_delay_days integer NOT NULL CHECK (delivery_delay_days >= 0)
);
CREATE TABLE dimensional.fact_return (
 return_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, return_id bigint NOT NULL UNIQUE,
 order_item_id bigint NOT NULL, order_id bigint NOT NULL, requested_date_key integer NOT NULL REFERENCES dimensional.dim_date(date_key),
 approved_date_key integer REFERENCES dimensional.dim_date(date_key), refund_date_key integer REFERENCES dimensional.dim_date(date_key),
 customer_key bigint NOT NULL REFERENCES dimensional.dim_customer(customer_key),
 product_key bigint NOT NULL REFERENCES dimensional.dim_product(product_key),
 return_quantity integer NOT NULL CHECK (return_quantity > 0), return_reason varchar(200) NOT NULL,
 return_status varchar(30) NOT NULL, refund_amount numeric(14,2) NOT NULL CHECK (refund_amount >= 0)
);
CREATE TABLE dimensional.fact_warranty_claim (
 warranty_claim_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, warranty_claim_id bigint NOT NULL UNIQUE,
 order_item_id bigint NOT NULL, order_id bigint NOT NULL, claim_date_key integer NOT NULL REFERENCES dimensional.dim_date(date_key),
 service_start_date_key integer REFERENCES dimensional.dim_date(date_key),
 service_completion_date_key integer REFERENCES dimensional.dim_date(date_key),
 customer_key bigint NOT NULL REFERENCES dimensional.dim_customer(customer_key),
 product_key bigint NOT NULL REFERENCES dimensional.dim_product(product_key), claim_reason varchar(200) NOT NULL,
 claim_status varchar(30) NOT NULL, service_cost_amount numeric(14,2) NOT NULL CHECK (service_cost_amount >= 0),
 resolution_days integer CHECK (resolution_days >= 0), resolution_description text
);

CREATE INDEX ix_sales_date ON dimensional.fact_sales(order_date_key);
CREATE INDEX ix_sales_customer ON dimensional.fact_sales(customer_key);
CREATE INDEX ix_sales_product ON dimensional.fact_sales(product_key);
CREATE INDEX ix_sales_order ON dimensional.fact_sales(order_id);
CREATE INDEX ix_inventory_product_date ON dimensional.fact_inventory_snapshot(product_key, inventory_date_key);
CREATE INDEX ix_inventory_warehouse_date ON dimensional.fact_inventory_snapshot(warehouse_key, inventory_date_key);
CREATE INDEX ix_payment_date_status ON dimensional.fact_payment(payment_date_key, payment_status);
CREATE INDEX ix_payment_method_channel ON dimensional.fact_payment(payment_method, order_channel);
CREATE INDEX ix_shipment_date_status ON dimensional.fact_shipment(shipment_date_key, shipment_status);
CREATE INDEX ix_shipment_courier ON dimensional.fact_shipment(courier_partner);
CREATE INDEX ix_return_product_date ON dimensional.fact_return(product_key, requested_date_key);
CREATE INDEX ix_claim_product_date ON dimensional.fact_warranty_claim(product_key, claim_date_key);

CREATE VIEW reporting.vw_daily_watch_sales AS
SELECT d.full_date, count(DISTINCT f.order_id) AS order_count, sum(f.quantity) AS quantity_sold,
 sum(f.gross_line_amount) AS gross_sales, sum(f.line_discount_amount) AS discounts,
 sum(f.line_net_amount) AS net_sales,
 sum(f.line_net_amount) / NULLIF(count(DISTINCT f.order_id),0) AS average_order_value
FROM dimensional.fact_sales f JOIN dimensional.dim_date d ON d.date_key=f.order_date_key GROUP BY d.full_date;

CREATE VIEW reporting.vw_product_performance AS
SELECT p.product_id,p.product_name,b.brand_name,c.collection_name,p.watch_category,p.movement_type,p.strap_material,p.dial_color,
 sum(s.quantity) AS units_sold,sum(s.line_net_amount) AS revenue,
 sum(s.line_net_amount)/NULLIF(sum(s.quantity),0) AS average_selling_price,
 coalesce(sum(r.return_quantity),0)::numeric/NULLIF(sum(s.quantity),0) AS return_rate
FROM dimensional.fact_sales s JOIN dimensional.dim_product p ON p.product_key=s.product_key
JOIN dimensional.dim_brand b ON b.brand_key=p.brand_key JOIN dimensional.dim_collection c ON c.collection_key=p.collection_key
LEFT JOIN (SELECT product_key,sum(return_quantity) return_quantity FROM dimensional.fact_return GROUP BY product_key) r ON r.product_key=p.product_key
GROUP BY p.product_id,p.product_name,b.brand_name,c.collection_name,p.watch_category,p.movement_type,p.strap_material,p.dial_color,r.return_quantity;

CREATE VIEW reporting.vw_customer_segment AS
SELECT c.customer_segment,c.city,c.region,count(DISTINCT c.customer_id) AS customer_count,
 count(DISTINCT s.order_id) AS orders,sum(s.line_net_amount) AS revenue,
 sum(s.line_net_amount)/NULLIF(count(DISTINCT s.order_id),0) AS average_order_value,
 count(DISTINCT s.order_id)-count(DISTINCT c.customer_id) AS repeat_purchases
FROM dimensional.fact_sales s JOIN dimensional.dim_customer c ON c.customer_key=s.customer_key
GROUP BY c.customer_segment,c.city,c.region;

CREATE VIEW reporting.vw_brand_collection AS
SELECT b.brand_name,c.collection_name,sum(s.quantity) units_sold,sum(s.line_net_amount) revenue,
 sum(s.line_net_amount)/NULLIF(sum(s.quantity),0) average_selling_price,
 coalesce(r.returned,0)::numeric/NULLIF(sum(s.quantity),0) return_rate,
 coalesce(w.claims,0)::numeric/NULLIF(sum(s.quantity),0) warranty_claim_rate
FROM dimensional.fact_sales s JOIN dimensional.dim_product p ON p.product_key=s.product_key
JOIN dimensional.dim_brand b ON b.brand_key=p.brand_key JOIN dimensional.dim_collection c ON c.collection_key=p.collection_key
LEFT JOIN (SELECT p.brand_key,p.collection_key,sum(f.return_quantity) returned FROM dimensional.fact_return f JOIN dimensional.dim_product p ON p.product_key=f.product_key GROUP BY p.brand_key,p.collection_key) r ON r.brand_key=b.brand_key AND r.collection_key=c.collection_key
LEFT JOIN (SELECT p.brand_key,p.collection_key,count(*) claims FROM dimensional.fact_warranty_claim f JOIN dimensional.dim_product p ON p.product_key=f.product_key GROUP BY p.brand_key,p.collection_key) w ON w.brand_key=b.brand_key AND w.collection_key=c.collection_key
GROUP BY b.brand_name,c.collection_name,r.returned,w.claims;

CREATE VIEW reporting.vw_inventory_availability AS
SELECT d.full_date,p.product_name,w.warehouse_name,i.on_hand_quantity,i.reserved_quantity,i.available_quantity,
 i.reorder_level,(i.available_quantity<=i.reorder_level) AS reorder_risk,i.inventory_status
FROM dimensional.fact_inventory_snapshot i JOIN dimensional.dim_date d ON d.date_key=i.inventory_date_key
JOIN dimensional.dim_product p ON p.product_key=i.product_key JOIN dimensional.dim_warehouse w ON w.warehouse_key=i.warehouse_key;

CREATE VIEW reporting.vw_payment_status AS
SELECT d.full_date,p.payment_method,p.order_channel,
 count(*) FILTER (WHERE p.payment_status='successful') successful_transactions,
 count(*) FILTER (WHERE p.payment_status='failed') failed_transactions,
 count(*) FILTER (WHERE p.payment_status='pending') pending_transactions,
 count(*) FILTER (WHERE p.payment_status='refunded') refunded_transactions,sum(p.payment_amount) payment_amount
FROM dimensional.fact_payment p JOIN dimensional.dim_date d ON d.date_key=p.payment_date_key
GROUP BY d.full_date,p.payment_method,p.order_channel;

CREATE VIEW reporting.vw_shipment_performance AS
SELECT d.full_date,s.courier_partner,count(*) shipment_count,
 count(*) FILTER (WHERE s.shipment_status='delivered') delivered_shipments,
 count(*) FILTER (WHERE s.delivery_delay_days>0) delayed_shipments,avg(s.delivery_delay_days) average_delivery_delay
FROM dimensional.fact_shipment s JOIN dimensional.dim_date d ON d.date_key=s.shipment_date_key
GROUP BY d.full_date,s.courier_partner;

CREATE VIEW reporting.vw_return_analysis AS
SELECT p.product_name,b.brand_name,p.watch_category,r.return_reason,count(*) return_count,
 sum(r.return_quantity) returned_quantity,sum(r.refund_amount) refund_amount,
 sum(r.return_quantity)::numeric/NULLIF((SELECT sum(s.quantity) FROM dimensional.fact_sales s WHERE s.product_key=p.product_key),0) return_rate
FROM dimensional.fact_return r JOIN dimensional.dim_product p ON p.product_key=r.product_key
JOIN dimensional.dim_brand b ON b.brand_key=p.brand_key
GROUP BY p.product_key,p.product_name,b.brand_name,p.watch_category,r.return_reason;

CREATE VIEW reporting.vw_warranty_claim AS
SELECT p.product_name,b.brand_name,w.claim_reason,w.claim_status,count(*) claim_count,
 sum(w.service_cost_amount) service_cost,avg(w.resolution_days) average_resolution_days
FROM dimensional.fact_warranty_claim w JOIN dimensional.dim_product p ON p.product_key=w.product_key
JOIN dimensional.dim_brand b ON b.brand_key=p.brand_key
GROUP BY p.product_name,b.brand_name,w.claim_reason,w.claim_status;
```

# Transformation Plan

Each staging table is refreshed only from its identically named raw source:

```sql
TRUNCATE staging.stg_customer, staging.stg_brand, staging.stg_collection, staging.stg_watch_product,
 staging.stg_warehouse, staging.stg_inventory, staging.stg_order, staging.stg_order_item,
 staging.stg_payment, staging.stg_shipment, staging.stg_return_request, staging.stg_warranty_claim;
INSERT INTO staging.stg_customer SELECT * FROM raw_load.load_customer_raw;
INSERT INTO staging.stg_brand SELECT * FROM raw_load.load_brand_raw;
INSERT INTO staging.stg_collection SELECT * FROM raw_load.load_collection_raw;
INSERT INTO staging.stg_watch_product SELECT * FROM raw_load.load_watch_product_raw;
INSERT INTO staging.stg_warehouse SELECT * FROM raw_load.load_warehouse_raw;
INSERT INTO staging.stg_inventory SELECT * FROM raw_load.load_inventory_raw;
INSERT INTO staging.stg_order SELECT * FROM raw_load.load_order_raw;
INSERT INTO staging.stg_order_item SELECT * FROM raw_load.load_order_item_raw;
INSERT INTO staging.stg_payment SELECT * FROM raw_load.load_payment_raw;
INSERT INTO staging.stg_shipment SELECT * FROM raw_load.load_shipment_raw;
INSERT INTO staging.stg_return_request SELECT * FROM raw_load.load_return_request_raw;
INSERT INTO staging.stg_warranty_claim SELECT * FROM raw_load.load_warranty_claim_raw;
```

Dimensions are loaded from staging master data in dependency order: date, customer, brand, collection, product, warehouse. Facts are loaded from staging transactions by resolving business IDs to surrogate keys. ETL must reject product/collection brand mismatches, order dates before signup, payment or shipment dates before order date, excess successful payments, order-header/line-total mismatches, orders without items, returns exceeding purchased quantity or refund limits, returns and claims without delivered items, and claims outside warranty periods. These multirow and cross-table rules are ETL validation rules because PostgreSQL CHECK constraints cannot reference other rows or tables.

# Relationships and Cardinality

| Parent | Child | Cardinality |
|---|---|---|
| raw_load.load_*_raw | matching staging.stg_* | 1:1 lineage by source row |
| dim_brand | dim_collection | 1:M |
| dim_brand | dim_product | 1:M |
| dim_collection | dim_product | 1:M |
| dim_customer | fact_sales/payment/shipment/return/warranty_claim | 1:M |
| dim_product | fact_sales/inventory_snapshot/return/warranty_claim | 1:M |
| dim_warehouse | fact_sales/inventory_snapshot/shipment | 1:M |
| dim_date | every dated fact role | 1:M |
| order_id | fact_sales/payment/shipment/return/warranty_claim | one order to many events |
| order_item_id | fact_return/fact_warranty_claim | one item to zero or many events |

# Data Dictionary

| Table Group | Business Keys / Primary Key | Purpose |
|---|---|---|
| load_*_raw | Source entity ID | Immutable landing representation plus source_file and loaded_at audit fields |
| stg_* | Source entity ID | Typed, constrained, deduplicated source records preserving all business and foreign keys |
| dim_date | date_key / full_date | Continuous calendar attributes |
| dim_customer | customer_key / customer_id | Customer reporting attributes |
| dim_brand | brand_key / brand_id | Fictional brand reporting attributes |
| dim_collection | collection_key / collection_id | Collection and owning-brand attributes |
| dim_product | product_key / product_id / sku | Product catalogue and classification attributes |
| dim_warehouse | warehouse_key / warehouse_id | Fulfilment-location attributes |
| fact_sales | sales_key / order_item_id | Order-item sales measures |
| fact_inventory_snapshot | inventory_snapshot_key / inventory_id | Daily stock snapshot measures |
| fact_payment | payment_key / payment_id | Payment attempt and transaction measures |
| fact_shipment | shipment_key / shipment_id | Shipment and delivery performance |
| fact_return | return_key / return_id | Return and refund events |
| fact_warranty_claim | warranty_claim_key / warranty_claim_id | Warranty service events |
| reporting.vw_* | No stored key | Aggregated reporting interfaces |

# Synthetic Data Generation Support

Generate at least 15 fictional rows per source table using en_GB formats and a date range of at least twelve months. Use meaningful invented brand, collection, product, customer, warehouse, and courier names; never use real watch companies or numbered placeholders. Reuse customers, products, brands, collections, and warehouses. Most orders should have multiple items; some orders should have multiple payment attempts and multi-warehouse shipments. Only delivered items may receive returns or claims; returns must be a minority and claims a smaller minority. Generate a continuous dim_date range covering signup, order, payment, shipment, delivery, return, refund, claim, and service dates. Preserve every arithmetic, cardinality, status, warranty, chronology, and foreign-key rule represented in the DDL and ETL validations.

# Excel Output with Sample Synthetic Data

Produce an .xlsx workbook with one worksheet per raw entity using the exact unqualified raw table name as the sheet name and columns in DDL order. Add Data_Dictionary and Load_Control worksheets. Use ISO dates, decimal currency values, TRUE/FALSE booleans, and explicitly label the workbook as fictional synthetic demonstration data. The workbook is loaded into raw_load tables; derived staging, dimensions, facts, and views are generated by PostgreSQL transformations rather than duplicated as independent spreadsheet inputs.

# PostgreSQL Loading and Orchestration Plan

1. Execute schemas, raw tables, staging tables, dimensions, facts, indexes, and views in DDL order.
2. Load workbook sheets or CSV exports with COPY into raw_load.load_*_raw in parent-first order: customer, brand, collection, watch_product, warehouse, inventory, order, order_item, payment, shipment, return_request, warranty_claim.
3. Run raw quality checks, then refresh matching staging tables in the same dependency order.
4. Populate dim_date for the complete date interval; upsert customer, brand, collection, product, and warehouse dimensions from staging.
5. Load fact_sales and fact_inventory_snapshot, followed by fact_payment, fact_shipment, fact_return, and fact_warranty_claim.
6. Execute reconciliation checks, ANALYZE dimensional tables, and expose reporting views.
7. Reconcile source-to-staging counts, unresolved dimension keys, order totals, payment totals, delivery status, returns, refunds, claims, and fact-to-source counts. Reject the batch on mandatory-rule failures.

# AI Additions / Assumptions

| Added Item | Type | Reason | Mandatory / Optional |
|---|---|---|---|
| Four PostgreSQL schemas | table namespace | Makes the required warehouse layers explicit and validation-ready | mandatory |
| dim_date | table | Supports continuous calendar reporting and role-playing dates | mandatory |
| Surrogate dimension and fact keys | key | Implements dimensional joins independently of source identifiers | mandatory |
| Source audit columns | attribute | Supports file-level lineage and load auditing | mandatory |
| SCD Type 1 dimensions | assumption | No dimension-history requirements or tracked attribute changes were specified | optional |
| Degenerate order_id and order_item_id | key | Preserves transaction traceability without unnecessary order dimensions | mandatory |
| Resolution days | attribute | Supports warranty resolution-time reporting | mandatory |
| Product brand and collection keys | relationship | Enables efficient brand and collection analysis from product facts | mandatory |
| ETL cross-row validation rules | constraint | Several business rules cannot be enforced with row-level CHECK constraints | mandatory |
| Excel raw-input workbook convention | assumption | Provides portable synthetic-data loading while retaining one authoritative transformation path | optional |
