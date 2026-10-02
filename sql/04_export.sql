-- 04_export.sql
-- Purpose: export the star schema to Parquet files for Power BI (Get data -> Parquet).
-- Parquet keeps the column types (dates stay dates, numbers stay numbers), unlike CSV.

COPY model.fact_orders       TO 'data/processed/fact_orders.parquet'       (FORMAT parquet);
COPY model.fact_order_items  TO 'data/processed/fact_order_items.parquet'  (FORMAT parquet);
COPY model.dim_customer      TO 'data/processed/dim_customer.parquet'      (FORMAT parquet);
COPY model.dim_seller        TO 'data/processed/dim_seller.parquet'        (FORMAT parquet);
COPY model.dim_product       TO 'data/processed/dim_product.parquet'       (FORMAT parquet);
COPY model.dim_date          TO 'data/processed/dim_date.parquet'          (FORMAT parquet);
COPY model.dim_geography     TO 'data/processed/dim_geography.parquet'     (FORMAT parquet);
