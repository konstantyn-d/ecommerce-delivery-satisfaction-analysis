-- 02_dimensions.sql
-- Purpose: the dimension tables of the star schema ("who, what, where, when").
-- Each dimension has exactly one row per key; the keys are the natural ids of the source data.

CREATE SCHEMA IF NOT EXISTS model;

-- ---------------------------------------------------------------------------------------------
-- dim_geography: one row per Brazilian state (26 states + Federal District), with its region.
-- Reference data typed by hand: the source only contains the 2-letter codes.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE model.dim_geography AS
SELECT * FROM (VALUES
    ('AC', 'Acre',                'North'),
    ('AP', 'Amapa',               'North'),
    ('AM', 'Amazonas',            'North'),
    ('PA', 'Para',                'North'),
    ('RO', 'Rondonia',            'North'),
    ('RR', 'Roraima',             'North'),
    ('TO', 'Tocantins',           'North'),
    ('AL', 'Alagoas',             'Northeast'),
    ('BA', 'Bahia',               'Northeast'),
    ('CE', 'Ceara',               'Northeast'),
    ('MA', 'Maranhao',            'Northeast'),
    ('PB', 'Paraiba',             'Northeast'),
    ('PE', 'Pernambuco',          'Northeast'),
    ('PI', 'Piaui',               'Northeast'),
    ('RN', 'Rio Grande do Norte', 'Northeast'),
    ('SE', 'Sergipe',             'Northeast'),
    ('DF', 'Distrito Federal',    'Central-West'),
    ('GO', 'Goias',               'Central-West'),
    ('MT', 'Mato Grosso',         'Central-West'),
    ('MS', 'Mato Grosso do Sul',  'Central-West'),
    ('ES', 'Espirito Santo',      'Southeast'),
    ('MG', 'Minas Gerais',        'Southeast'),
    ('RJ', 'Rio de Janeiro',      'Southeast'),
    ('SP', 'Sao Paulo',           'Southeast'),
    ('PR', 'Parana',              'South'),
    ('RS', 'Rio Grande do Sul',   'South'),
    ('SC', 'Santa Catarina',      'South')
) AS t (state_code, state_name, region);


-- ---------------------------------------------------------------------------------------------
-- dim_date: one row per calendar day of the analysis period (purchase dates).
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE model.dim_date AS
SELECT
    d::DATE                          AS date_day,
    year(d)                          AS year,
    quarter(d)                       AS quarter,
    month(d)                         AS month_number,
    strftime(d, '%b')                AS month_name,        -- Jan, Feb, ...
    strftime(d, '%Y-%m')             AS year_month,        -- 2017-01: sorts correctly as text
    date_trunc('month', d)::DATE     AS month_start,
    isodow(d)                        AS weekday_number,    -- 1 = Monday ... 7 = Sunday
    strftime(d, '%a')                AS weekday_name,
    isodow(d) >= 6                   AS is_weekend
FROM generate_series(DATE '2017-01-01', DATE '2018-08-31', INTERVAL 1 DAY) AS t (d);


-- ---------------------------------------------------------------------------------------------
-- dim_product: one row per product, with a usable English category.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE model.dim_product AS
SELECT
    p.product_id,
    coalesce(p.product_category_name, 'unknown') AS category_pt,            -- decision #23
    CASE
        WHEN p.product_category_name IS NULL THEN 'unknown'
        WHEN t.product_category_name_english IS NOT NULL THEN t.product_category_name_english
        -- decision #24: two categories are missing in the translation file, translated by hand
        WHEN p.product_category_name = 'pc_gamer' THEN 'pc_gamer'
        WHEN p.product_category_name = 'portateis_cozinha_e_preparadores_de_alimentos'
            THEN 'portable_kitchen_food_preparers'
    END AS category_en
FROM raw.products p
LEFT JOIN raw.category_translation t USING (product_category_name);


-- ---------------------------------------------------------------------------------------------
-- dim_seller: one row per seller, with state and region.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE model.dim_seller AS
SELECT
    s.seller_id,
    left(s.seller_id, 8) AS seller_short,                      -- readable label for tables and charts
    s.seller_city,
    s.seller_state,
    g.region AS seller_region
FROM raw.sellers s
LEFT JOIN model.dim_geography g ON g.state_code = s.seller_state;


-- ---------------------------------------------------------------------------------------------
-- dim_customer: one row per real person (customer_unique_id) with at least one order in the period.
-- "First order" means the first order inside the analysis period.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE model.dim_customer AS
WITH ranked AS (
    SELECT
        *,
        row_number() OVER (PARTITION BY customer_unique_id
                           ORDER BY order_purchase_timestamp, order_id) AS order_number
    FROM stg.orders
)
SELECT
    customer_unique_id,
    min(purchase_date)                                        AS first_purchase_date,
    max(customer_state) FILTER (WHERE order_number = 1)       AS first_order_state,
    count(*)                                                  AS order_count,
    -- several orders placed on the same day are one shopping occasion, not a repeat purchase
    count(DISTINCT purchase_date)                             AS purchase_day_count,
    count(DISTINCT purchase_date) > 1                         AS is_repeat_customer
FROM ranked
GROUP BY customer_unique_id;
