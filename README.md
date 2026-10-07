# Late Deliveries, Lost Customers

Business analysis of customer dissatisfaction on the Olist Brazilian e-commerce marketplace.

> **Status: work in progress.** Data model, metric definitions and the hypothesis-driven analysis are complete.
> Analysis, review coding and the what-if scenario are done. The dashboard is specified and being built; the deck is still to come. The final summary of findings is [TBD]
> until those are done; the current findings are in [docs/analysis_findings.md](docs/analysis_findings.md).

## Business question

*Why do customers give bad reviews, how much does it cost the business, and what should management fix first?*

Framed as a request from Olist's Head of Operations.

## Repository structure

```
data/raw/         raw CSV files (not committed, see "How to reproduce")
data/processed/   DuckDB database and Parquet exports for Power BI (not committed, built by the scripts)
sql/              load, model and KPI queries, numbered in run order
notebooks/        exploration scripts, numbered
review_coding/    codebook, sample and coded results of the qualitative review analysis
dashboard/        Power BI file and screenshots
deck/             slide deck (PDF)
docs/             data dictionary, decision log, data model, metric definitions, findings, charts
```

## Data model

A star schema in DuckDB: two fact tables at different grains sharing the date and geography dimensions.
Field definitions and design reasons are in [docs/data_model.md](docs/data_model.md).

```mermaid
erDiagram
    dim_date      ||--o{ fact_orders      : "purchase_date"
    dim_geography ||--o{ fact_orders      : "customer_state"
    dim_customer  ||--|{ fact_orders      : "customer_unique_id"
    dim_date      ||--o{ fact_order_items : "purchase_date"
    dim_geography ||--o{ fact_order_items : "customer_state"
    dim_product   ||--o{ fact_order_items : "product_id"
    dim_seller    ||--o{ fact_order_items : "seller_id"
```

- `fact_orders` (one row per order): delivery outcome, delay, order value, review score
- `fact_order_items` (one row per unit sold): seller, product, price, freight

## Documentation

- [Dashboard](dashboard/README.md): page specifications, DAX measures, theme and reference values for Power BI
- [Scenario](docs/scenario.md): what fixing late deliveries and incomplete orders could achieve, with assumptions and low / base / high ranges
- [Review coding findings](review_coding/findings.md): what customers complain about in 300 coded reviews, with quotes
- [Review coding files](review_coding/README.md): codebook, sampling method, coding and consistency check
- [Analysis findings](docs/analysis_findings.md): issue tree, 12 hypotheses with test, result and conclusion, charts
- [Analysis results](docs/analysis_results.md): the generated tables behind the findings
- [Metric definitions](docs/metric_definitions.md): business definition, formula, grain, filters and caveats of every KPI
- [KPI baseline](docs/kpi_baseline.md): generated reference values, total and by month
- [Data model](docs/data_model.md): star schema, derived field definitions, Power BI relationships
- [Model validation report](docs/model_validation_report.md): 37 tests reconciling the model with the raw data
- [Data dictionary](docs/data_dictionary.md): tables, grain, relationships, columns and known issues
- [Profiling report](docs/profiling_report.md): generated row counts, nulls, keys and relationship checks
- [Decision log](docs/decision_log.md): every data quality issue, rows affected, decision and reason
- [Data quality report](docs/data_quality_report.md): the generated counts behind the decision log

## How to reproduce

1. Download the dataset from Kaggle:
   [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
   and unzip the 9 CSV files into `data/raw/`.
2. Create the environment (Python 3.13):
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Build the database, the star schema, the KPI views and the Parquet exports (runs every file in `sql/` in order):
   ```
   python run_sql.py
   ```
4. Regenerate the reports in `docs/`:
   ```
   python notebooks/00_data_profiling.py
   python notebooks/01_data_quality_checks.py
   python notebooks/02_model_validation.py
   python notebooks/03_kpi_baseline.py
   python notebooks/04_hypothesis_analysis.py
   python notebooks/05_review_sample.py
   ```
5. Compute the review coding results from `review_coding/coding.csv`, then the scenario:
   ```
   python notebooks/06_review_coding_results.py
   python notebooks/07_scenario.py
   python notebooks/08_dashboard_reference.py
   ```

## Data source and licence

Data: *Brazilian E-Commerce Public Dataset by Olist*, published on Kaggle by Olist under the
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) licence.
This project is non-commercial and for educational purposes. The raw data is not redistributed here.
