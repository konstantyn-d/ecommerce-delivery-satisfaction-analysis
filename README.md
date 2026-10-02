# Late Deliveries, Lost Customers

Business analysis of customer dissatisfaction on the Olist Brazilian e-commerce marketplace.

> **Status: work in progress.** Data understanding and data quality review are complete.
> Findings, dashboard and recommendations will be added as the analysis progresses: [TBD].

## Business question

*Why do customers give bad reviews, how much does it cost the business, and what should management fix first?*

Framed as a request from Olist's Head of Operations.

## Repository structure

```
data/raw/         raw CSV files (not committed, see "How to reproduce")
data/processed/   DuckDB database and model exports (built by the scripts)
sql/              load, model and KPI queries, numbered in run order
notebooks/        exploration scripts, numbered
review_coding/    codebook, sample and coded results of the qualitative review analysis
dashboard/        Power BI file and screenshots
deck/             slide deck (PDF)
docs/             data dictionary, profiling report, metric definitions, decision log
```

## Documentation

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
3. Build the database and the generated reports:
   ```
   python run_sql.py
   python notebooks/00_data_profiling.py
   python notebooks/01_data_quality_checks.py
   ```

## Data source and licence

Data: *Brazilian E-Commerce Public Dataset by Olist*, published on Kaggle by Olist under the
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) licence.
This project is non-commercial and for educational purposes. The raw data is not redistributed here.
