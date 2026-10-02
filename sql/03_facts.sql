-- 03_facts.sql
-- Purpose: the two fact tables of the star schema.
--   model.fact_orders       grain: one row per order      -> delivery and satisfaction analysis
--   model.fact_order_items  grain: one row per unit sold  -> seller and category analysis
-- Every derived field is defined in docs/data_model.md.

-- ---------------------------------------------------------------------------------------------
-- fact_orders
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE model.fact_orders AS
WITH item_agg AS (
    -- collapse the items to one row per order BEFORE joining, so the order grain is never multiplied
    SELECT
        i.order_id,
        count(*)                                   AS item_count,
        count(DISTINCT i.seller_id)                AS seller_count,
        sum(i.price)::DECIMAL(12,2)                AS items_value,
        sum(i.freight_value)::DECIMAL(12,2)        AS freight_value,
        max(i.shipping_limit_date)                 AS last_shipping_limit,
        bool_and(i.seller_state = o.customer_state) AS is_same_state
    FROM stg.order_items i
    JOIN stg.orders o USING (order_id)
    GROUP BY i.order_id
)
SELECT
    -- keys
    o.order_id,
    o.customer_unique_id,                                        -- -> dim_customer
    o.purchase_date,                                             -- -> dim_date
    o.customer_state,                                            -- -> dim_geography

    -- delivery
    o.order_status,
    CASE
        WHEN o.is_delivered AND o.delay_days <= 0 THEN 'On time'
        WHEN o.is_delivered AND o.delay_days > 0  THEN 'Late'
        WHEN o.order_status = 'delivered'         THEN 'Unknown'        -- delivered, but no delivery date
        ELSE 'Not delivered'
    END AS delivery_outcome,
    CASE
        WHEN o.is_delivered AND o.delay_days <= 0             THEN 'On time'
        WHEN o.is_delivered AND o.delay_days BETWEEN 1 AND 3  THEN 'Late 1-3 days'
        WHEN o.is_delivered AND o.delay_days BETWEEN 4 AND 7  THEN 'Late 4-7 days'
        WHEN o.is_delivered AND o.delay_days BETWEEN 8 AND 14 THEN 'Late 8-14 days'
        WHEN o.is_delivered AND o.delay_days >= 15            THEN 'Late 15+ days'
        WHEN o.order_status = 'delivered'                     THEN 'Unknown'
        ELSE 'Not delivered'
    END AS delay_band,
    CASE
        WHEN o.is_delivered AND o.delay_days <= 0             THEN 1
        WHEN o.is_delivered AND o.delay_days BETWEEN 1 AND 3  THEN 2
        WHEN o.is_delivered AND o.delay_days BETWEEN 4 AND 7  THEN 3
        WHEN o.is_delivered AND o.delay_days BETWEEN 8 AND 14 THEN 4
        WHEN o.is_delivered AND o.delay_days >= 15            THEN 5
        WHEN o.order_status = 'delivered'                     THEN 7
        ELSE 6
    END AS delay_band_sort,                                      -- sort order for charts
    o.is_delivered,
    CASE WHEN o.is_delivered THEN o.delay_days <= 0 END AS is_on_time,   -- NULL when not measurable
    o.promised_days,
    o.delivery_days,
    o.delay_days,
    o.handling_days,
    o.transit_days,
    -- did the seller hand the order to the carrier after the shipping deadline?
    CASE WHEN o.order_delivered_carrier_date IS NOT NULL AND a.last_shipping_limit IS NOT NULL
         THEN o.order_delivered_carrier_date > a.last_shipping_limit END AS is_seller_handover_late,

    -- value (NULL for the orders without item rows, decision #22)
    a.order_id IS NOT NULL                       AS has_items,
    a.item_count,
    a.seller_count,
    a.items_value,
    a.freight_value,
    (a.items_value + a.freight_value)::DECIMAL(12,2) AS order_total,
    a.is_same_state,                             -- all sellers of the order are in the customer's state

    -- satisfaction (NULL for the orders without a review, decision #13)
    r.order_id IS NOT NULL                       AS has_review,
    r.review_score,
    r.review_score <= 2                          AS is_low_score,
    r.review_comment_message IS NOT NULL         AS has_comment,
    CASE WHEN o.is_delivered AND r.order_id IS NOT NULL
         THEN r.review_answer_timestamp < o.order_delivered_customer_date END AS review_before_delivery,

    -- customer history: 1 = first order of this person in the analysis period
    row_number() OVER (PARTITION BY o.customer_unique_id
                       ORDER BY o.order_purchase_timestamp, o.order_id) AS customer_order_number
FROM stg.orders o
LEFT JOIN item_agg a USING (order_id)
LEFT JOIN stg.reviews r USING (order_id);


-- ---------------------------------------------------------------------------------------------
-- fact_order_items
-- The order-level outcome (delivery, review) is copied onto every item of the order, so that seller
-- and category analysis does not need a fact-to-fact join.
-- ASSUMPTION (decision #25): the review score of an order applies to each of its items.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE model.fact_order_items AS
SELECT
    -- keys
    i.order_id,
    i.order_item_id,
    i.product_id,                                                -- -> dim_product
    i.seller_id,                                                 -- -> dim_seller
    f.purchase_date,                                             -- -> dim_date
    f.customer_state,                                            -- -> dim_geography

    -- value
    i.price,
    i.freight_value,

    -- item-level attributes
    i.seller_state = f.customer_state            AS is_same_state,
    CASE WHEN o.order_delivered_carrier_date IS NOT NULL
         THEN o.order_delivered_carrier_date > i.shipping_limit_date END AS is_seller_handover_late,

    -- copied from the order
    f.seller_count > 1                           AS is_multi_seller_order,
    f.delivery_outcome,
    f.is_delivered,
    f.is_on_time,
    f.delay_days,
    f.has_review,
    f.review_score,
    f.is_low_score
FROM stg.order_items i
JOIN model.fact_orders f USING (order_id)
JOIN stg.orders o USING (order_id);
