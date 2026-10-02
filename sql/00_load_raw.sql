-- 00_load_raw.sql
-- Purpose: load the 9 Olist CSV files into DuckDB exactly as delivered (no cleaning, no filtering).
-- Every later query reads from the raw schema, so the CSV files are touched in one place only.
-- Run with: python run_sql.py   (paths are relative to the repository root)
--
-- Type decisions (everything else is auto-detected by DuckDB):
--   * zip code prefixes -> VARCHAR. They are codes, not numbers: "01037" must keep its leading zero.
--   * money columns     -> DECIMAL(10,2). Avoids floating-point rounding noise when summing.
--     Checked beforehand: no value in the source has more than 2 decimal places.

CREATE SCHEMA IF NOT EXISTS raw;

CREATE OR REPLACE TABLE raw.orders AS
SELECT * FROM read_csv('data/raw/olist_orders_dataset.csv', header = true);

CREATE OR REPLACE TABLE raw.order_items AS
SELECT * FROM read_csv('data/raw/olist_order_items_dataset.csv', header = true,
    types = {'price': 'DECIMAL(10,2)', 'freight_value': 'DECIMAL(10,2)'});

CREATE OR REPLACE TABLE raw.order_payments AS
SELECT * FROM read_csv('data/raw/olist_order_payments_dataset.csv', header = true,
    types = {'payment_value': 'DECIMAL(10,2)'});

-- Review comments contain line breaks and quotes inside the text; DuckDB handles quoted
-- multi-line fields, and the row count is cross-checked against pandas in the profiling step.
CREATE OR REPLACE TABLE raw.order_reviews AS
SELECT * FROM read_csv('data/raw/olist_order_reviews_dataset.csv', header = true);

CREATE OR REPLACE TABLE raw.customers AS
SELECT * FROM read_csv('data/raw/olist_customers_dataset.csv', header = true,
    types = {'customer_zip_code_prefix': 'VARCHAR'});

CREATE OR REPLACE TABLE raw.sellers AS
SELECT * FROM read_csv('data/raw/olist_sellers_dataset.csv', header = true,
    types = {'seller_zip_code_prefix': 'VARCHAR'});

-- Column names "product_name_lenght" / "product_description_lenght" are misspelled in the source.
-- They are kept as-is here and renamed in the model layer (Phase 2).
CREATE OR REPLACE TABLE raw.products AS
SELECT * FROM read_csv('data/raw/olist_products_dataset.csv', header = true);

CREATE OR REPLACE TABLE raw.geolocation AS
SELECT * FROM read_csv('data/raw/olist_geolocation_dataset.csv', header = true,
    types = {'geolocation_zip_code_prefix': 'VARCHAR'});

CREATE OR REPLACE TABLE raw.category_translation AS
SELECT * FROM read_csv('data/raw/product_category_name_translation.csv', header = true);
