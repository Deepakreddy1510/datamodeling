# Conceptual data model

TimeCraft uses a layered analytical warehouse covering customer registration, catalogue management, inventory, ordering, payments, fulfilment, returns, refunds, and warranty servicing.

| Subject Area | Core Entities | Analytical Outcome |
|---|---|---|
| Customer | Customer, Order | Customer behaviour, segmentation, repeat purchasing |
| Catalogue | Brand, Collection, Watch Product | Product, brand, and collection performance |
| Inventory | Warehouse, Inventory, Watch Product | Availability, reservation, and reorder analysis |
| Sales | Order, Order Item | Orders, units, gross sales, discounts, and net sales |
| Payments | Order, Payment | Payment attempts, success, failure, pending, and refund analysis |
| Fulfilment | Order, Shipment, Warehouse | Delivery timeliness and courier performance |
| Returns | Order Item, Return Request | Return rates, reasons, quantities, and refunds |
| Warranty | Order Item, Warranty Claim | Claim rates, service cost, status, and resolution time |

# Logical data model

The warehouse contains raw-load, staging, dimension, fact, and reporting layers. Raw tables retain source records as JSONB. Staging tables retain validated, typed business records. Dimensions contain descriptive reporting context and surrogate keys. Facts represent measurable business events.

| Layer | Tables | Purpose |
|---|---|---|
| Raw load | load_customer_raw, load_brand_raw, load_collection_raw, load_watch_product_raw, load_warehouse_raw, load_inventory_raw, load_order_raw, load_order_item_raw, load_payment_raw, load_shipment_raw, load_return_request_raw, load_warranty_claim_raw | Immutable source ingestion and auditability |
| Staging | stg_customer, stg_brand, stg_collection, stg_watch_product, stg_warehouse, stg_inventory, stg_order, stg_order_item, stg_payment, stg_shipment, stg_return_request, stg_warranty_claim | Typed validation and source-key preservation |
| Dimensions | dim_date, dim_customer, dim_brand, dim_collection, dim_product, dim_warehouse, dim_order | Conformed reporting context |
| Facts | fact_sales, fact_inventory, fact_payment, fact_delivery, fact_return, fact_claim | Additive and event-level measures |
| Reporting | vw_daily_watch_sales, vw_product_performance, vw_inventory_availability, vw_payment_status, vw_shipment_performance, vw_return_analysis, vw_warranty_claim_analysis | Reusable reporting datasets |

Fact grains:

| Fact | Grain | Measures |
|---|---|---|
| fact_sales | One row per order item | quantity, unit price, gross line amount, discount, net line amount |
| fact_inventory | One product, warehouse, and inventory date | on-hand, reserved, available, reorder level |
| fact_payment | One payment transaction or attempt | payment amount |
| fact_delivery | One shipment | shipment count, delivered indicator, delayed indicator, delay days |
| fact_return | One return request | return quantity, refund amount |
| fact_claim | One warranty claim | service cost, resolution days |

# Physical PostgreSQL data model

All objects are created in the timecraft_dw schema. BIGINT identity columns are used for warehouse surrogate keys. Business identifiers remain UNIQUE where appropriate. Monetary values use NUMERIC(14,2), dates use DATE, ingestion timestamps use TIMESTAMPTZ, and raw source documents use JSONB. Dimensions use Type 1 behaviour in this design. The date dimension uses an integer YYYYMMDD key.

Data dictionary:

| Table Group | Key Columns | Descriptive Columns | Measure Columns |
|---|---|---|---|
| Raw tables | load_id | source_system, source_record_id, payload, loaded_at | None |
| stg_customer | customer_id | name, contact, geography, segment, signup date, status | None |
| stg_brand / stg_collection | brand_id, collection_id | names, origin, tier, launch year, status | None |
| stg_watch_product | product_id | SKU and watch characteristics | unit price, warranty months |
| stg_warehouse | warehouse_id | name, geography, type, status | None |
| stg_inventory | inventory_id | product, warehouse, date, status | stock quantities and reorder level |
| stg_order / stg_order_item | order_id, order_item_id | customer, channel, status, fulfilment keys | order and line amounts, quantity |
| stg_payment | payment_id | method, type, status, reference, date | payment amount |
| stg_shipment | shipment_id | tracking, courier, dates, status | delivery delay days |
| stg_return_request | return_id | reason, status, lifecycle dates | quantity, refund amount |
| stg_warranty_claim | warranty_claim_id | reason, status, service dates, resolution | service cost |
| Dimensions | surrogate key plus business key | Conformed descriptive attributes | None |
| Facts | surrogate fact key plus dimension keys | Event identifiers and statuses | Event-specific measures |

# SQL DDL scripts

```sql
CREATE SCHEMA IF NOT EXISTS timecraft_dw;
SET search_path TO timecraft_dw, public;

CREATE TABLE load_customer_raw (load_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_system text NOT NULL DEFAULT 'synthetic', source_record_id text NOT NULL, payload jsonb NOT NULL CHECK (jsonb_typeof(payload)='object'), loaded_at timestamptz NOT NULL DEFAULT now(), UNIQUE(source_system,source_record_id));
CREATE TABLE load_brand_raw (LIKE load_customer_raw INCLUDING ALL);
CREATE TABLE load_collection_raw (LIKE load_customer_raw INCLUDING ALL);
CREATE TABLE load_watch_product_raw (LIKE load_customer_raw INCLUDING ALL);
CREATE TABLE load_warehouse_raw (LIKE load_customer_raw INCLUDING ALL);
CREATE TABLE load_inventory_raw (LIKE load_customer_raw INCLUDING ALL);
CREATE TABLE load_order_raw (LIKE load_customer_raw INCLUDING ALL);
CREATE TABLE load_order_item_raw (LIKE load_customer_raw INCLUDING ALL);
CREATE TABLE load_payment_raw (LIKE load_customer_raw INCLUDING ALL);
CREATE TABLE load_shipment_raw (LIKE load_customer_raw INCLUDING ALL);
CREATE TABLE load_return_request_raw (LIKE load_customer_raw INCLUDING ALL);
CREATE TABLE load_warranty_claim_raw (LIKE load_customer_raw INCLUDING ALL);

CREATE TABLE stg_customer (
 customer_id bigint PRIMARY KEY, customer_name text NOT NULL, email text NOT NULL, phone text,
 city text NOT NULL, region text NOT NULL, customer_segment text NOT NULL,
 signup_date date NOT NULL, is_active boolean NOT NULL, UNIQUE(email)
);
CREATE TABLE stg_brand (
 brand_id bigint PRIMARY KEY, brand_name text NOT NULL UNIQUE, country_of_origin text NOT NULL,
 brand_tier text NOT NULL, is_active boolean NOT NULL
);
CREATE TABLE stg_collection (
 collection_id bigint PRIMARY KEY, brand_id bigint NOT NULL REFERENCES stg_brand(brand_id),
 collection_name text NOT NULL, launch_year smallint NOT NULL CHECK (launch_year BETWEEN 1900 AND 2200),
 collection_status text NOT NULL CHECK (collection_status IN ('PLANNED','ACTIVE','DISCONTINUED')),
 UNIQUE(brand_id,collection_name), UNIQUE(collection_id,brand_id)
);
CREATE TABLE stg_watch_product (
 product_id bigint PRIMARY KEY, brand_id bigint NOT NULL REFERENCES stg_brand(brand_id),
 collection_id bigint NOT NULL, sku text NOT NULL UNIQUE, product_name text NOT NULL,
 watch_category text NOT NULL, gender_category text NOT NULL, movement_type text NOT NULL,
 strap_material text NOT NULL, dial_color text NOT NULL,
 case_size_mm numeric(5,2) NOT NULL CHECK (case_size_mm > 0),
 water_resistance_metres integer NOT NULL CHECK (water_resistance_metres >= 0),
 unit_price numeric(14,2) NOT NULL CHECK (unit_price >= 0),
 warranty_months integer NOT NULL CHECK (warranty_months >= 0),
 product_status text NOT NULL CHECK (product_status IN ('PLANNED','ACTIVE','DISCONTINUED')),
 FOREIGN KEY (collection_id,brand_id) REFERENCES stg_collection(collection_id,brand_id)
);
CREATE TABLE stg_warehouse (
 warehouse_id bigint PRIMARY KEY, warehouse_name text NOT NULL UNIQUE, city text NOT NULL,
 region text NOT NULL, warehouse_type text NOT NULL, is_active boolean NOT NULL
);
CREATE TABLE stg_inventory (
 inventory_id bigint PRIMARY KEY, product_id bigint NOT NULL REFERENCES stg_watch_product(product_id),
 warehouse_id bigint NOT NULL REFERENCES stg_warehouse(warehouse_id), inventory_date date NOT NULL,
 on_hand_quantity integer NOT NULL CHECK (on_hand_quantity >= 0),
 reserved_quantity integer NOT NULL CHECK (reserved_quantity >= 0),
 available_quantity integer NOT NULL CHECK (available_quantity >= 0),
 reorder_level integer NOT NULL CHECK (reorder_level >= 0), inventory_status text NOT NULL,
 CHECK (available_quantity = on_hand_quantity - reserved_quantity),
 UNIQUE(product_id,warehouse_id,inventory_date)
);
CREATE TABLE stg_order (
 order_id bigint PRIMARY KEY, customer_id bigint NOT NULL REFERENCES stg_customer(customer_id),
 order_date date NOT NULL, order_status text NOT NULL,
 order_channel text NOT NULL CHECK (order_channel IN ('WEB','MOBILE_WEB','APP')),
 gross_order_amount numeric(14,2) NOT NULL CHECK (gross_order_amount >= 0),
 discount_amount numeric(14,2) NOT NULL CHECK (discount_amount >= 0),
 net_order_amount numeric(14,2) NOT NULL CHECK (net_order_amount >= 0),
 CHECK (net_order_amount = gross_order_amount - discount_amount)
);
CREATE TABLE stg_order_item (
 order_item_id bigint PRIMARY KEY, order_id bigint NOT NULL REFERENCES stg_order(order_id),
 product_id bigint NOT NULL REFERENCES stg_watch_product(product_id),
 warehouse_id bigint NOT NULL REFERENCES stg_warehouse(warehouse_id),
 quantity integer NOT NULL CHECK (quantity > 0), unit_price numeric(14,2) NOT NULL CHECK (unit_price >= 0),
 gross_line_amount numeric(14,2) NOT NULL CHECK (gross_line_amount = quantity * unit_price),
 line_discount_amount numeric(14,2) NOT NULL CHECK (line_discount_amount BETWEEN 0 AND gross_line_amount),
 line_net_amount numeric(14,2) NOT NULL CHECK (line_net_amount = gross_line_amount-line_discount_amount)
);
CREATE TABLE stg_payment (
 payment_id bigint PRIMARY KEY, order_id bigint NOT NULL REFERENCES stg_order(order_id),
 payment_date date NOT NULL, payment_method text NOT NULL,
 payment_transaction_type text NOT NULL CHECK (payment_transaction_type IN ('AUTHORISATION','CAPTURE','SALE','REFUND','VOID')),
 payment_status text NOT NULL CHECK (payment_status IN ('PENDING','SUCCESSFUL','FAILED','REFUNDED','CANCELLED')),
 payment_amount numeric(14,2) NOT NULL CHECK (payment_amount >= 0), transaction_reference text NOT NULL UNIQUE
);
CREATE TABLE stg_shipment (
 shipment_id bigint PRIMARY KEY, order_id bigint NOT NULL REFERENCES stg_order(order_id),
 warehouse_id bigint NOT NULL REFERENCES stg_warehouse(warehouse_id), tracking_number text NOT NULL UNIQUE,
 courier_partner text NOT NULL, shipment_date date NOT NULL, promised_delivery_date date NOT NULL,
 actual_delivery_date date, shipment_status text NOT NULL CHECK (shipment_status IN ('CREATED','DISPATCHED','IN_TRANSIT','DELIVERED','LOST','RETURNED','CANCELLED')),
 delivery_delay_days integer NOT NULL DEFAULT 0 CHECK (delivery_delay_days >= 0),
 CHECK (promised_delivery_date >= shipment_date),
 CHECK ((shipment_status='DELIVERED' AND actual_delivery_date IS NOT NULL) OR (shipment_status<>'DELIVERED' AND actual_delivery_date IS NULL))
);
CREATE TABLE stg_return_request (
 return_id bigint PRIMARY KEY, order_item_id bigint NOT NULL REFERENCES stg_order_item(order_item_id),
 return_quantity integer NOT NULL CHECK (return_quantity > 0), return_reason text NOT NULL,
 return_status text NOT NULL CHECK (return_status IN ('REQUESTED','APPROVED','REJECTED','RECEIVED','REFUNDED','CANCELLED')),
 requested_date date NOT NULL, approved_date date, refund_date date,
 refund_amount numeric(14,2) NOT NULL DEFAULT 0 CHECK (refund_amount >= 0),
 CHECK (approved_date IS NULL OR approved_date >= requested_date),
 CHECK (refund_date IS NULL OR (approved_date IS NOT NULL AND refund_date >= approved_date))
);
CREATE TABLE stg_warranty_claim (
 warranty_claim_id bigint PRIMARY KEY, order_item_id bigint NOT NULL REFERENCES stg_order_item(order_item_id),
 claim_reason text NOT NULL, claim_status text NOT NULL CHECK (claim_status IN ('OPEN','ASSESSED','IN_SERVICE','RESOLVED','REJECTED','CLOSED')),
 claim_date date NOT NULL, service_start_date date, service_completion_date date,
 service_cost_amount numeric(14,2) NOT NULL DEFAULT 0 CHECK (service_cost_amount >= 0),
 resolution_description text,
 CHECK (service_start_date IS NULL OR service_start_date >= claim_date),
 CHECK (service_completion_date IS NULL OR (service_start_date IS NOT NULL AND service_completion_date >= service_start_date))
);

CREATE TABLE dim_date (
 date_key integer PRIMARY KEY, full_date date NOT NULL UNIQUE, day_of_week smallint NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
 day_name text NOT NULL, week_of_year smallint NOT NULL, month_number smallint NOT NULL CHECK (month_number BETWEEN 1 AND 12),
 month_name text NOT NULL, quarter_number smallint NOT NULL CHECK (quarter_number BETWEEN 1 AND 4),
 calendar_year smallint NOT NULL, is_weekend boolean NOT NULL
);
CREATE TABLE dim_customer (
 customer_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, customer_id bigint NOT NULL UNIQUE,
 customer_name text NOT NULL, email text NOT NULL, phone text, city text NOT NULL, region text NOT NULL,
 customer_segment text NOT NULL, signup_date date NOT NULL, is_active boolean NOT NULL
);
CREATE TABLE dim_brand (
 brand_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, brand_id bigint NOT NULL UNIQUE,
 brand_name text NOT NULL, country_of_origin text NOT NULL, brand_tier text NOT NULL, is_active boolean NOT NULL
);
CREATE TABLE dim_collection (
 collection_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, collection_id bigint NOT NULL UNIQUE,
 brand_key bigint NOT NULL REFERENCES dim_brand(brand_key), collection_name text NOT NULL,
 launch_year smallint NOT NULL, collection_status text NOT NULL
);
CREATE TABLE dim_product (
 product_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, product_id bigint NOT NULL UNIQUE,
 brand_key bigint NOT NULL REFERENCES dim_brand(brand_key), collection_key bigint NOT NULL REFERENCES dim_collection(collection_key),
 sku text NOT NULL UNIQUE, product_name text NOT NULL, watch_category text NOT NULL,
 gender_category text NOT NULL, movement_type text NOT NULL, strap_material text NOT NULL,
 dial_color text NOT NULL, case_size_mm numeric(5,2) NOT NULL CHECK (case_size_mm > 0),
 water_resistance_metres integer NOT NULL CHECK (water_resistance_metres >= 0),
 catalogue_unit_price numeric(14,2) NOT NULL CHECK (catalogue_unit_price >= 0),
 warranty_months integer NOT NULL CHECK (warranty_months >= 0), product_status text NOT NULL
);
CREATE TABLE dim_warehouse (
 warehouse_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, warehouse_id bigint NOT NULL UNIQUE,
 warehouse_name text NOT NULL, city text NOT NULL, region text NOT NULL, warehouse_type text NOT NULL, is_active boolean NOT NULL
);
CREATE TABLE dim_order (
 order_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, order_id bigint NOT NULL UNIQUE,
 customer_key bigint NOT NULL REFERENCES dim_customer(customer_key), order_date_key integer NOT NULL REFERENCES dim_date(date_key),
 order_status text NOT NULL, order_channel text NOT NULL,
 gross_order_amount numeric(14,2) NOT NULL CHECK (gross_order_amount >= 0),
 discount_amount numeric(14,2) NOT NULL CHECK (discount_amount >= 0),
 net_order_amount numeric(14,2) NOT NULL CHECK (net_order_amount = gross_order_amount-discount_amount)
);

CREATE TABLE fact_sales (
 sales_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, order_item_id bigint NOT NULL UNIQUE,
 order_key bigint NOT NULL REFERENCES dim_order(order_key), customer_key bigint NOT NULL REFERENCES dim_customer(customer_key),
 product_key bigint NOT NULL REFERENCES dim_product(product_key), warehouse_key bigint NOT NULL REFERENCES dim_warehouse(warehouse_key),
 order_date_key integer NOT NULL REFERENCES dim_date(date_key), quantity integer NOT NULL CHECK (quantity > 0),
 unit_price numeric(14,2) NOT NULL CHECK (unit_price >= 0),
 gross_line_amount numeric(14,2) NOT NULL CHECK (gross_line_amount = quantity*unit_price),
 line_discount_amount numeric(14,2) NOT NULL CHECK (line_discount_amount BETWEEN 0 AND gross_line_amount),
 line_net_amount numeric(14,2) NOT NULL CHECK (line_net_amount = gross_line_amount-line_discount_amount)
);
CREATE TABLE fact_inventory (
 inventory_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, inventory_id bigint NOT NULL UNIQUE,
 product_key bigint NOT NULL REFERENCES dim_product(product_key), warehouse_key bigint NOT NULL REFERENCES dim_warehouse(warehouse_key),
 inventory_date_key integer NOT NULL REFERENCES dim_date(date_key), on_hand_quantity integer NOT NULL CHECK (on_hand_quantity >= 0),
 reserved_quantity integer NOT NULL CHECK (reserved_quantity >= 0), available_quantity integer NOT NULL CHECK (available_quantity >= 0),
 reorder_level integer NOT NULL CHECK (reorder_level >= 0), inventory_status text NOT NULL,
 CHECK (available_quantity = on_hand_quantity-reserved_quantity), UNIQUE(product_key,warehouse_key,inventory_date_key)
);
CREATE TABLE fact_payment (
 payment_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, payment_id bigint NOT NULL UNIQUE,
 order_key bigint NOT NULL REFERENCES dim_order(order_key), customer_key bigint NOT NULL REFERENCES dim_customer(customer_key),
 payment_date_key integer NOT NULL REFERENCES dim_date(date_key), payment_method text NOT NULL,
 payment_transaction_type text NOT NULL, payment_status text NOT NULL,
 payment_amount numeric(14,2) NOT NULL CHECK (payment_amount >= 0), transaction_reference text NOT NULL UNIQUE
);
CREATE TABLE fact_delivery (
 delivery_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, shipment_id bigint NOT NULL UNIQUE,
 order_key bigint NOT NULL REFERENCES dim_order(order_key), customer_key bigint NOT NULL REFERENCES dim_customer(customer_key),
 warehouse_key bigint NOT NULL REFERENCES dim_warehouse(warehouse_key), shipment_date_key integer NOT NULL REFERENCES dim_date(date_key),
 promised_delivery_date_key integer NOT NULL REFERENCES dim_date(date_key), actual_delivery_date_key integer REFERENCES dim_date(date_key),
 tracking_number text NOT NULL UNIQUE, courier_partner text NOT NULL, shipment_status text NOT NULL,
 shipment_count smallint NOT NULL DEFAULT 1 CHECK (shipment_count=1), delivered_count smallint NOT NULL CHECK (delivered_count IN (0,1)),
 delayed_count smallint NOT NULL CHECK (delayed_count IN (0,1)), delivery_delay_days integer NOT NULL CHECK (delivery_delay_days >= 0)
);
CREATE TABLE fact_return (
 return_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, return_id bigint NOT NULL UNIQUE,
 sales_key bigint NOT NULL REFERENCES fact_sales(sales_key), order_key bigint NOT NULL REFERENCES dim_order(order_key),
 customer_key bigint NOT NULL REFERENCES dim_customer(customer_key), product_key bigint NOT NULL REFERENCES dim_product(product_key),
 requested_date_key integer NOT NULL REFERENCES dim_date(date_key), approved_date_key integer REFERENCES dim_date(date_key),
 refund_date_key integer REFERENCES dim_date(date_key), return_reason text NOT NULL, return_status text NOT NULL,
 return_quantity integer NOT NULL CHECK (return_quantity > 0), refund_amount numeric(14,2) NOT NULL CHECK (refund_amount >= 0)
);
CREATE TABLE fact_claim (
 claim_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, warranty_claim_id bigint NOT NULL UNIQUE,
 sales_key bigint NOT NULL REFERENCES fact_sales(sales_key), order_key bigint NOT NULL REFERENCES dim_order(order_key),
 customer_key bigint NOT NULL REFERENCES dim_customer(customer_key), product_key bigint NOT NULL REFERENCES dim_product(product_key),
 claim_date_key integer NOT NULL REFERENCES dim_date(date_key), service_start_date_key integer REFERENCES dim_date(date_key),
 service_completion_date_key integer REFERENCES dim_date(date_key), claim_reason text NOT NULL, claim_status text NOT NULL,
 service_cost_amount numeric(14,2) NOT NULL CHECK (service_cost_amount >= 0), resolution_days integer CHECK (resolution_days >= 0),
 resolution_description text
);

CREATE INDEX ix_stg_inventory_product_warehouse_date ON stg_inventory(product_id,warehouse_id,inventory_date);
CREATE INDEX ix_stg_order_customer_date ON stg_order(customer_id,order_date);
CREATE INDEX ix_stg_order_item_order ON stg_order_item(order_id);
CREATE INDEX ix_stg_order_item_product ON stg_order_item(product_id);
CREATE INDEX ix_stg_payment_order_date ON stg_payment(order_id,payment_date);
CREATE INDEX ix_stg_shipment_order_date ON stg_shipment(order_id,shipment_date);
CREATE INDEX ix_stg_return_order_item ON stg_return_request(order_item_id);
CREATE INDEX ix_stg_claim_order_item ON stg_warranty_claim(order_item_id);
CREATE INDEX ix_fact_sales_date_product ON fact_sales(order_date_key,product_key);
CREATE INDEX ix_fact_sales_customer_date ON fact_sales(customer_key,order_date_key);
CREATE INDEX ix_fact_inventory_date_product ON fact_inventory(inventory_date_key,product_key);
CREATE INDEX ix_fact_payment_date_status ON fact_payment(payment_date_key,payment_status);
CREATE INDEX ix_fact_delivery_date_courier ON fact_delivery(shipment_date_key,courier_partner);
CREATE INDEX ix_fact_return_product_date ON fact_return(product_key,requested_date_key);
CREATE INDEX ix_fact_claim_product_date ON fact_claim(product_key,claim_date_key);

CREATE VIEW vw_daily_watch_sales AS
SELECT d.full_date, COUNT(DISTINCT o.order_id) AS order_count, SUM(s.quantity) AS quantity_sold,
 SUM(s.gross_line_amount) AS gross_sales, SUM(s.line_discount_amount) AS discounts,
 SUM(s.line_net_amount) AS net_sales,
 SUM(s.line_net_amount)/NULLIF(COUNT(DISTINCT o.order_id),0) AS average_order_value
FROM fact_sales s JOIN dim_date d ON d.date_key=s.order_date_key JOIN dim_order o ON o.order_key=s.order_key
GROUP BY d.full_date;

CREATE VIEW vw_product_performance AS
SELECT p.product_id,p.product_name,b.brand_name,c.collection_name,p.watch_category,p.movement_type,p.strap_material,p.dial_color,
 SUM(s.quantity) AS units_sold,SUM(s.line_net_amount) AS revenue,
 SUM(s.line_net_amount)/NULLIF(SUM(s.quantity),0) AS average_selling_price,
 COALESCE(SUM(r.return_quantity),0)::numeric/NULLIF(SUM(s.quantity),0) AS return_rate
FROM fact_sales s JOIN dim_product p ON p.product_key=s.product_key
JOIN dim_brand b ON b.brand_key=p.brand_key JOIN dim_collection c ON c.collection_key=p.collection_key
LEFT JOIN fact_return r ON r.sales_key=s.sales_key
GROUP BY p.product_id,p.product_name,b.brand_name,c.collection_name,p.watch_category,p.movement_type,p.strap_material,p.dial_color;

CREATE VIEW vw_inventory_availability AS
SELECT d.full_date,p.sku,p.product_name,w.warehouse_name,i.on_hand_quantity,i.reserved_quantity,i.available_quantity,
 i.reorder_level,(i.available_quantity<=i.reorder_level) AS reorder_risk,i.inventory_status
FROM fact_inventory i JOIN dim_date d ON d.date_key=i.inventory_date_key
JOIN dim_product p ON p.product_key=i.product_key JOIN dim_warehouse w ON w.warehouse_key=i.warehouse_key;

CREATE VIEW vw_payment_status AS
SELECT d.full_date,p.payment_method,o.order_channel,p.payment_status,COUNT(*) AS transaction_count,SUM(p.payment_amount) AS payment_amount
FROM fact_payment p JOIN dim_date d ON d.date_key=p.payment_date_key JOIN dim_order o ON o.order_key=p.order_key
GROUP BY d.full_date,p.payment_method,o.order_channel,p.payment_status;

CREATE VIEW vw_shipment_performance AS
SELECT d.full_date,f.courier_partner,COUNT(*) AS shipment_count,SUM(f.delivered_count) AS delivered_shipments,
 SUM(f.delayed_count) AS delayed_shipments,AVG(f.delivery_delay_days) AS average_delivery_delay
FROM fact_delivery f JOIN dim_date d ON d.date_key=f.shipment_date_key GROUP BY d.full_date,f.courier_partner;

CREATE VIEW vw_return_analysis AS
SELECT p.product_name,b.brand_name,p.watch_category,r.return_reason,COUNT(*) AS return_count,
 SUM(r.return_quantity) AS returned_quantity,SUM(r.refund_amount) AS refund_amount
FROM fact_return r JOIN dim_product p ON p.product_key=r.product_key JOIN dim_brand b ON b.brand_key=p.brand_key
GROUP BY p.product_name,b.brand_name,p.watch_category,r.return_reason;

CREATE VIEW vw_warranty_claim_analysis AS
SELECT p.product_name,b.brand_name,c.claim_reason,c.claim_status,COUNT(*) AS claim_count,
 SUM(c.service_cost_amount) AS service_cost,AVG(c.resolution_days) AS average_resolution_days
FROM fact_claim c JOIN dim_product p ON p.product_key=c.product_key JOIN dim_brand b ON b.brand_key=p.brand_key
GROUP BY p.product_name,b.brand_name,c.claim_reason,c.claim_status;
```

Cross-row rules must be enforced during staging transformation or by deferred validation procedures: customer signup date must not exceed order date; an order must contain at least one item; order totals must equal aggregated line totals; successful payments must not exceed the order net amount; payment and shipment dates must not precede order date; returns and claims require delivered order items; return quantity cannot exceed purchased quantity; refund cannot exceed returned quantity multiplied by unit price; and claim date must fall within the purchased product warranty period.

# Table relationships

| Parent | Child | Cardinality | Foreign Key |
|---|---|---|---|
| stg_brand | stg_collection | 1:M | brand_id |
| stg_brand and stg_collection | stg_watch_product | 1:M | brand_id and collection_id |
| stg_customer | stg_order | 1:M | customer_id |
| stg_order | stg_order_item | 1:M | order_id |
| stg_watch_product | stg_inventory, stg_order_item | 1:M | product_id |
| stg_warehouse | stg_inventory, stg_order_item, stg_shipment | 1:M | warehouse_id |
| stg_order | stg_payment, stg_shipment | 1:M | order_id |
| stg_order_item | stg_return_request, stg_warranty_claim | 1:M | order_item_id |
| dim_brand | dim_collection, dim_product | 1:M | brand_key |
| dim_collection | dim_product | 1:M | collection_key |
| dim_customer | dim_order and transaction facts | 1:M | customer_key |
| dim_order | fact_sales, fact_payment, fact_delivery, fact_return, fact_claim | 1:M | order_key |
| dim_product | fact_sales, fact_inventory, fact_return, fact_claim | 1:M | product_key |
| dim_warehouse | fact_sales, fact_inventory, fact_delivery | 1:M | warehouse_key |
| fact_sales | fact_return, fact_claim | 1:M | sales_key |
| dim_date | all dated dimensions and facts | 1:M per date role | date_key |

# Fact and dimension design

Dimensions are conformed across facts. Customer, product, brand, collection, warehouse, order, and date keys allow consistent slicing across reports. Brand and collection remain separate dimensions while dim_product references both, enabling direct brand and collection reporting without repeating their full descriptive attributes in every fact. dim_order stores order-level status, channel, and totals; fact_sales remains at order-item grain to prevent mixed-grain measures.

Facts use transaction-specific natural identifiers as UNIQUE lineage keys. Quantity and monetary measures in sales and inventory are additive over compatible dimensions. Inventory balances are semi-additive over time and should use the latest snapshot for point-in-time reporting. Rates and averages must be calculated from summed numerators and denominators rather than averaged row-level percentages.

# Synthetic data generation support

All generated values must be explicitly identified as fictional demonstration data. Use en_GB formatting and create at least 15 rows per business table; fact tables may contain more rows to preserve realistic cardinalities.

| Table | Generation Rules |
|---|---|
| Raw tables | One JSON object per generated source record; unique source record identifiers; retain corresponding typed values |
| stg_customer | Meaningful fictional British-style names and contact data; reuse customers across orders; signup dates precede orders |
| stg_brand | Fictional names only; varied countries and tiers; no real watch companies |
| stg_collection | Reuse brands; meaningful collection names; valid launch years and statuses |
| stg_watch_product | Reuse brands and collections; ensure product brand matches collection brand; unique SKU; plausible attributes, price, and warranty |
| stg_warehouse | Meaningful fictional fulfilment-centre names and UK locations; reuse warehouses |
| stg_inventory | Multiple products, warehouses, and dates; nonnegative balances; available equals on-hand minus reserved |
| stg_order | Reuse customers; span at least twelve months; compute totals from items; include multiple channels and statuses |
| stg_order_item | Generate multiple items for most orders; reuse products; positive quantities; calculate line amounts exactly |
| stg_payment | Multiple attempts for selected orders; chronological dates; varied outcomes and methods; successful total within order net amount |
| stg_shipment | Generate multiple shipments for selected multi-warehouse orders; use fictional couriers; maintain chronological delivery dates |
| stg_return_request | Generate only for a minority of delivered items; quantity within purchased quantity; refund within allowed maximum |
| stg_warranty_claim | Generate for a smaller minority of delivered items; claim within warranty; chronological service dates and nonnegative costs |
| dim_date | Continuous daily coverage from the earliest signup or transaction date through the latest refund or service-completion date |
| Dimensions | Derive one row per current natural key; do not create unchanged history |
| Facts | Derive from validated staging rows at the declared grains; every dimension key must resolve |

# Excel output with sample synthetic data

Create one workbook named `timecraft_synthetic_demo.xlsx`. Use one worksheet per staging table and one worksheet per dimension and fact table. Worksheet names should be shortened to Excel's 31-character limit. The first row contains exact PostgreSQL column names. Dates use `YYYY-MM-DD`, timestamps use ISO 8601 UTC, booleans use TRUE/FALSE, identifiers remain unformatted integers, and monetary values use two decimal places. Include a `README` worksheet stating that all records are fictional synthetic demonstration data, documenting table grains, row counts, generation period, and loading order. Validate every workbook row against the DDL before database loading.

# PostgreSQL loading support

Recommended loading sequence:

1. Create schema, tables, constraints, indexes, and views by running the DDL.
2. Load all load_*_raw tables using JSONB records and record the ingestion timestamp.
3. Parse, type, standardise, deduplicate, and validate raw records into staging tables in this order: brand, collection, watch product, customer, warehouse, inventory, order, order item, payment, shipment, return request, warranty claim.
4. Populate dim_date for the complete required date range.
5. Upsert dim_customer, dim_brand, dim_collection, dim_product, dim_warehouse, and dim_order using their natural keys.
6. Load fact_sales, fact_inventory, fact_payment, fact_delivery, fact_return, and fact_claim after resolving every surrogate foreign key.
7. Execute reconciliation checks for orphan keys, row counts, order totals, successful payment totals, inventory equations, delivery eligibility, return limits, and warranty dates.
8. Run `ANALYZE` on dimension and fact tables before reporting.

For Excel or CSV ingestion, use PostgreSQL `COPY` into temporary import tables, then use explicit INSERT statements with casts into staging. Run each subject-area load in a transaction and reject invalid rows into a separately governed error table rather than disabling constraints.

# AI Additions / Assumptions

| Added Item | Type | Reason | Mandatory / Optional |
|---|---|---|---|
| timecraft_dw schema | table namespace | Isolates warehouse objects | Optional |
| Raw JSONB ingestion metadata | attribute | Supports replay, lineage, and source auditing | Mandatory |
| dim_date | table | Required for continuous calendar reporting and role-playing dates | Mandatory |
| dim_order | table | Provides conformed order channel, status, and order-level totals | Mandatory |
| dim_brand and dim_collection | table | Blueprint omitted these but reporting explicitly requires both | Mandatory |
| dim_warehouse | table | Replaces ambiguous store/location dimensions with the stated fulfilment entity | Mandatory |
| fact_inventory | table | Inventory availability is a required analytical process | Mandatory |
| Surrogate dimension and fact keys | key | Supports dimensional joins independently of source identifiers | Mandatory |
| Type 1 dimension handling | assumption | No historical attribute-change requirements were supplied | Optional |
| Transaction fact omitted | assumption | No independent generic transaction process exists beyond sales, payment, return, delivery, and claim facts | Optional |
| Delivery indicators and shipment count | attribute | Supports additive shipment reporting | Mandatory |
| Claim resolution days | attribute | Supports required warranty resolution-time reporting | Mandatory |
| Cross-row ETL validations | constraint | PostgreSQL CHECK constraints cannot safely enforce aggregate or multi-table rules | Mandatory |
| Reporting views | view | Provides reusable datasets for requested reports | Optional |
| Excel README worksheet | assumption | Documents synthetic status, grains, and loading sequence | Optional |
