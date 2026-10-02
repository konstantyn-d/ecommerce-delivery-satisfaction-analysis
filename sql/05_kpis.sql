-- 05_kpis.sql
-- Purpose: the official formula of every KPI, written once.
-- The business definitions are in docs/metric_definitions.md; this file is their SQL implementation.
-- The dashboard (DAX) and the deck must reproduce the numbers of these views.
--
-- Rule for all rates: a rate is "sum of numerators / sum of denominators" (a ratio of totals),
-- never an average of per-order ratios. The numerator and denominator are kept as columns so that
-- every rate can be recomputed by hand.

-- ---------------------------------------------------------------------------------------------
-- model.kpi_orders: order-based KPIs, one row per month plus one row for the whole period.
-- GROUPING SETS computes both levels with the same formulas, so month and total cannot diverge.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW model.kpi_orders AS
SELECT
    coalesce(d.year_month, 'Total')                                       AS period,

    -- volume and value
    count(*)                                                              AS orders,
    count(*) FILTER (WHERE f.has_items)                                   AS orders_with_items,
    sum(f.items_value)                                                    AS gmv,
    sum(f.items_value) / count(*) FILTER (WHERE f.has_items)              AS avg_order_value,
    sum(f.freight_value)                                                  AS freight_total,
    sum(f.freight_value) / sum(f.order_total)                             AS freight_share,

    -- delivery
    count(*) FILTER (WHERE f.is_delivered)                                AS delivered_orders,
    count(*) FILTER (WHERE f.delivery_outcome = 'On time')                AS on_time_orders,
    count(*) FILTER (WHERE f.delivery_outcome = 'Late')                   AS late_orders,
    count(*) FILTER (WHERE f.delivery_outcome = 'Not delivered')          AS not_delivered_orders,
    count(*) FILTER (WHERE f.delivery_outcome = 'On time')
        / count(*) FILTER (WHERE f.is_delivered)                          AS on_time_rate,
    count(*) FILTER (WHERE f.delivery_outcome = 'Late')
        / count(*) FILTER (WHERE f.is_delivered)                          AS late_rate,
    count(*) FILTER (WHERE f.delivery_outcome = 'Not delivered') / count(*) AS not_delivered_rate,
    avg(f.delay_days)    FILTER (WHERE f.delivery_outcome = 'Late')       AS avg_delay_days_late,
    median(f.delay_days) FILTER (WHERE f.delivery_outcome = 'Late')       AS median_delay_days_late,
    avg(f.delivery_days)                                                  AS avg_delivery_days,
    median(f.delivery_days)                                               AS median_delivery_days,

    -- satisfaction
    count(*) FILTER (WHERE f.has_review)                                  AS reviewed_orders,
    avg(f.review_score)                                                   AS avg_review_score,
    count(*) FILTER (WHERE f.is_low_score)                                AS low_score_orders,
    count(*) FILTER (WHERE f.is_low_score) / count(*) FILTER (WHERE f.has_review) AS low_score_rate,
    count(*) FILTER (WHERE f.has_comment)                                 AS commented_orders,
    count(*) FILTER (WHERE f.has_comment) / count(*) FILTER (WHERE f.has_review)  AS comment_rate
FROM model.fact_orders f
JOIN model.dim_date d ON d.date_day = f.purchase_date
GROUP BY GROUPING SETS ((d.year_month), ());


-- ---------------------------------------------------------------------------------------------
-- model.kpi_customers: customer-based KPIs for the whole period (one row).
-- A repeat purchase rate per month would be misleading: a customer needs time to come back.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW model.kpi_customers AS
SELECT
    count(*)                                              AS customers,
    count(*) FILTER (WHERE is_repeat_customer)            AS repeat_customers,
    count(*) FILTER (WHERE is_repeat_customer) / count(*) AS repeat_purchase_rate
FROM model.dim_customer;
