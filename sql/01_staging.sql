-- 01_staging.sql
-- Purpose: apply the cleaning decisions from docs/decision_log.md in ONE place.
-- The staging tables are the cleaned version of the raw tables; the star schema (02, 03) is built
-- only from staging, never from raw. Numbers in comments (#n) refer to rows of the decision log.

CREATE SCHEMA IF NOT EXISTS stg;

-- ---------------------------------------------------------------------------------------------
-- stg.orders: one row per order in the analysis period, with all delivery fields derived.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE stg.orders AS
WITH base AS (
    SELECT
        o.order_id,
        c.customer_unique_id,                                  -- #26 the person, not the per-order customer_id
        c.customer_state,                                      -- #27 geography = delivery address of this order
        o.order_status,
        o.order_purchase_timestamp,
        o.order_delivered_carrier_date,
        o.order_delivered_customer_date,
        o.order_purchase_timestamp::DATE       AS purchase_date,
        o.order_delivered_carrier_date::DATE   AS carrier_date,
        o.order_delivered_customer_date::DATE  AS delivered_date,
        o.order_estimated_delivery_date::DATE  AS estimated_date,
        -- #5, #6 a delivery can only be measured when the status is 'delivered' AND a date exists
        (o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL) AS is_delivered
    FROM raw.orders o
    JOIN raw.customers c USING (customer_id)
    -- #1 analysis period: complete months only
    WHERE o.order_purchase_timestamp >= TIMESTAMP '2017-01-01'
      AND o.order_purchase_timestamp <  TIMESTAMP '2018-09-01'
)
SELECT
    order_id,
    customer_unique_id,
    customer_state,
    order_status,
    order_purchase_timestamp,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    purchase_date,
    carrier_date,
    delivered_date,
    estimated_date,
    is_delivered,

    -- days promised to the customer at purchase
    date_diff('day', purchase_date, estimated_date) AS promised_days,

    -- calendar days from purchase to delivery
    CASE WHEN is_delivered THEN date_diff('day', purchase_date, delivered_date) END AS delivery_days,

    -- #3 calendar days between the promised date and the delivery: positive = late, 0 or negative = on time
    CASE WHEN is_delivered THEN date_diff('day', estimated_date, delivered_date) END AS delay_days,

    -- #7, #8 the carrier timestamp is unreliable: intervals that would be negative are set to NULL
    CASE WHEN order_delivered_carrier_date >= order_purchase_timestamp
         THEN date_diff('day', purchase_date, carrier_date) END AS handling_days,   -- purchase -> handover to carrier
    CASE WHEN is_delivered AND order_delivered_customer_date >= order_delivered_carrier_date
         THEN date_diff('day', carrier_date, delivered_date) END AS transit_days    -- handover -> customer
FROM base;


-- ---------------------------------------------------------------------------------------------
-- stg.reviews: exactly one review per order (#4: the most recently answered one).
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE stg.reviews AS
SELECT
    r.order_id,
    r.review_id,                                               -- #12 not unique: one review can cover several orders
    r.review_score,
    nullif(trim(r.review_comment_message), '') AS review_comment_message,   -- #14 spaces only = no comment
    r.review_creation_date::DATE AS survey_sent_date,
    r.review_answer_timestamp
FROM raw.order_reviews r
JOIN stg.orders o USING (order_id)                             -- keep reviews of in-period orders only
QUALIFY row_number() OVER (PARTITION BY r.order_id
                           ORDER BY r.review_answer_timestamp DESC, r.review_id DESC) = 1;


-- ---------------------------------------------------------------------------------------------
-- stg.order_items: one row per unit sold, for in-period orders, with seller and category attached.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE stg.order_items AS
SELECT
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    s.seller_state,
    i.shipping_limit_date,
    i.price,
    i.freight_value
FROM raw.order_items i
JOIN stg.orders o USING (order_id)
JOIN raw.sellers s USING (seller_id);
