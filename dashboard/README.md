# Power BI dashboard

Three pages for Olist's Head of Operations: where delivery fails, how it shows up in reviews, and what
customers complain about.

The dashboard is a **Power BI Project (PBIP)** generated from code by [`build_pbip.py`](build_pbip.py): the data
model (tables, relationships, measures) is written in TMDL and the report (pages, visuals, titles, filters) in
PBIR, both plain-text formats that Power BI Desktop opens directly. Every element can be reviewed in Git and the
whole dashboard is rebuilt with one command.

| File | What it is |
|---|---|
| `olist_delivery_dashboard.pbip` | Open this file in Power BI Desktop |
| `olist_delivery_dashboard.SemanticModel/` | Data model: 8 tables, 7 relationships, 44 measures (TMDL) |
| `olist_delivery_dashboard.Report/` | Report: 3 pages, 34 visuals (PBIR) |
| [`build_pbip.py`](build_pbip.py) | Generates the two folders above and `measures.dax` |
| [`measures.dax`](measures.dax) | All measures in one readable file, with description and format (generated) |
| [`theme.json`](theme.json) | Colours and fonts used by the report |
| [`reference_values.md`](reference_values.md) | The numbers each visual must show with no filter applied (generated) |
| `screenshots/` | One PNG per page [TBD] |

## 1. Open the dashboard

1. Build the data: `python run_sql.py` and `python notebooks/06_review_coding_results.py` (from the repository root).
2. Build the project: `python dashboard/build_pbip.py`.
3. Open `dashboard/olist_delivery_dashboard.pbip` in Power BI Desktop (version of 2025 or later).
4. The first time, the yellow bar says *"Some of the tables have incomplete or no data"*: click **Refresh now**.
   The model loads about 344,000 rows from the Parquet and CSV files in a few seconds.

The data location is the Power Query parameter **DataFolder** (Transform data > Manage parameters). It is set to
the folder of the repository on the machine where the project was built; change it if you cloned the
repository elsewhere.

## 2. Design rules

| Rule | How it is applied |
|---|---|
| One colour for "good / reference", one accent for "problem" | Blue `#2a78d6` = on time, single item, share of orders. Orange `#eb6834` = late, not delivered, above the national rate. Grey `#a8a7a0` = context |
| Titles state findings | Every page and every chart has a sentence as title, and a subtitle that says what is plotted |
| Consistent number formats | Set once on each measure: percentages with 1 decimal, counts with thousands separator, scores with 2 decimals |
| No decoration | No 3D, no pie charts, no dual-axis charts |
| Filters in one place | Year and customer region slicers in the top-right of every page, synchronised across pages |
| Readable at a glance | At most 6 cards and 4 charts per page |

## 3. Pages

The page titles describe the data without any filter; they are what the screenshots show.

### Page 1. Executive overview

*Late and undelivered orders are 9.5% of orders but account for 43% of all bad reviews*

| Visual | Type | Content | Title |
|---|---|---|---|
| 6 cards | Card | Orders, GMV (millions), On-time Rate, Not-delivered Rate, Avg Review Score, Low Score Share | — |
| Orders by month | Column chart | `Orders` by `dim_date[year_month]` | *Monthly orders grew from 800 in January 2017 to more than 6,000 in every month of 2018* |
| Late rate and bad reviews by month | Line chart | `Late Rate` (orange) and `Low Score Share` (blue) by month, one % axis | *Bad reviews peak in the same three months as late deliveries* |
| Share by delivery outcome | Clustered bar chart | `Share of Orders` (blue) and `Share of Low Score Reviews` (orange) by `delivery_outcome` | *Late and undelivered orders: 9.5% of orders, 43% of bad reviews* |

### Page 2. Delivery performance

*Rio de Janeiro has 13% of orders but 23% of late deliveries; most delays arise after the seller has shipped*

| Visual | Type | Content | Title |
|---|---|---|---|
| 5 cards | Card | Late Rate, Late Orders, Median Delivery Days, Avg Delay (Late), Late Orders Handed Over Late by Seller | — |
| Late rate by state | Bar chart | `Late Rate` by `state_name`, states with 300+ orders, sorted descending; bar colour from the measure `Colour Late Rate` (orange above the national rate) | *Late rates are highest in the Northeast; Rio de Janeiro combines a high rate with high volume* |
| Late orders by delay band | Column chart | `Orders` by `delay_band`, late bands only | *Late orders are spread fairly evenly from 1 to more than 15 days late* |
| Seller ranking | Table | Seller, state, orders, late orders, late rate, 1-2 star share; sellers with 30+ orders, sorted by late orders | *The sellers with the most late orders are large São Paulo sellers, not small outliers* |

### Page 3. Customer satisfaction

*On-time orders with several items get 1-2 stars more than three times as often as single-item orders*

| Visual | Type | Content | Title |
|---|---|---|---|
| 4 cards | Card | Avg Review Score, Low Score Share, Comment Share, Coded Reviews | — |
| Bad reviews by delay band | Column chart | `Low Score Share` by `delay_band`; colour from `Colour Delivery` (blue on time, orange otherwise) | *Bad reviews jump from 9% for on-time orders to 68% once an order is 4-7 days late* |
| Bad reviews by order size | Clustered bar chart | `Low Score Share Single Item` (blue) and `Low Score Share Several Items` (orange) by `delivery_outcome` | *Even when delivered on time, orders with several items get 25% bad reviews, against 7.5% for single items* |
| Complaint matrix | Matrix | `Complaint Share` by complaint category (rows) and delivery group (columns), white-to-orange background | *81% of complaints about on-time orders with several items are about a missing part* |
| Category matrix | Scatter chart | `Item GMV` (x) vs `Item Low Score Share` (y) per category, categories with 500+ orders | *Office furniture has the highest share of bad reviews; large categories sit close to the average* |

The complaint matrix uses the table `coded_reviews` (300 coded reviews). It is deliberately not related to the
rest of the model, and the slicers are set not to filter it: slicing 300 reviews by month or state would give
numbers too small to read.

## 4. The model

| Table | Rows | Role |
|---|---|---|
| `fact_orders` | 99,092 | one row per order; order, delivery and satisfaction measures |
| `fact_order_items` | 112,279 | one row per unit sold; seller and category measures |
| `dim_customer`, `dim_seller`, `dim_product`, `dim_date`, `dim_geography` | 95,774 / 3,095 / 32,951 / 608 / 27 | dimensions |
| `coded_reviews` | 300 | review coding sample, not related |

Relationships are one-to-many and single-direction from each dimension to the facts (see
[`docs/data_model.md`](../docs/data_model.md)). There is no relationship between the two fact tables. The model
discourages implicit measures, so every number in a visual comes from a named measure in
[`measures.dax`](measures.dax), and each measure implements a definition from
[`docs/metric_definitions.md`](../docs/metric_definitions.md).

## 5. Checks

With no filter applied the visuals must show the values in [`reference_values.md`](reference_values.md), for
example:

- Cards: Orders 99,092; On-time Rate 93.2%; Not-delivered Rate 2.9%; Avg Review Score 4.09; Low Score Share 14.6%.
- Page 1, share by outcome: Late = 6.6% of orders and 27.7% of bad reviews.
- Page 2, late rate by state: Alagoas 21.5% at the top; 21 states shown.
- Page 3, bad reviews by delay band: On time 9.2%, Late 4-7 days 67.7%.
- Page 3, complaint matrix: Incomplete order × On time, several items = 81%.

All JSON files of the report were validated against Microsoft's published PBIR schemas before the first
opening in Power BI Desktop.
