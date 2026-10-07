# Power BI dashboard: specification and build guide

Three pages for Olist's Head of Operations: where delivery fails, how it shows up in reviews, and what
customers complain about.

| File | What it is |
|---|---|
| `README.md` | This page: design rules, page specifications, step-by-step build guide |
| [`measures.dax`](measures.dax) | Every DAX measure, with an explanation and the number format to set |
| [`theme.json`](theme.json) | Colours and fonts; import it once and every visual follows the design rules |
| [`reference_values.md`](reference_values.md) | The numbers each visual must show with no filter applied (generated) |
| `olist_delivery_dashboard.pbix` | The Power BI file [TBD: to be built] |
| `screenshots/` | One PNG per page [TBD: to be added] |

## 1. Design rules

| Rule | How |
|---|---|
| One colour for "good / reference", one accent for "problem" | Blue `#2a78d6` = on time, reference. Orange `#eb6834` = late, not delivered, above average. Grey `#a8a7a0` = context. Nothing else |
| Titles state findings | Every page and every visual has a sentence as title ("Bad reviews jump once an order is 4 days late"), not a topic ("Reviews by delay") |
| Consistent number formats | Percentages with 1 decimal (`14.6%`); counts with thousands separator (`6,531`); money as `R$` with no decimals in cards; scores with 2 decimals (`4.09`) |
| No decoration | No 3D, no shadows, no pie chart with more than 3 slices, no dual-axis chart |
| Filters in one place | Slicers in one row at the top of each page, the same on every page |
| Readable at a glance | At most 6 cards and 4 charts per page; every bar labelled with its value or a clear axis |

Canvas: 16:9 (1280 × 720), white background.

## 2. Page specifications

The page titles describe the data without any filter. They are what the screenshots show.

### Page 1. Executive overview

**Page title:** *Late and undelivered orders are 9.5% of orders but account for 43% of all bad reviews*

```
+------------------------------------------------------------------------------------------+
| PAGE TITLE                                                  [Year v] [Region v]           |
+--------------+--------------+--------------+--------------+--------------+---------------+
|   Orders     |     GMV      | On-time Rate | Not-delivered|  Avg Review  | Low Score     |
|   99,092     |  R$ 13.5M    |    93.2%     |  Rate 2.9%   |  Score 4.09  | Share 14.6%   |
+--------------+--------------+--------------+--------------+--------------+---------------+
| [A] Orders by month (columns)               | [B] Late rate and 1-2 star share by month   |
|                                             |     (two lines, one % axis)                 |
+---------------------------------------------+---------------------------------------------+
| [C] Share of orders vs share of 1-2 star reviews, by delivery outcome (clustered bars)    |
+------------------------------------------------------------------------------------------+
```

| Visual | Type | Fields | Settings | Title |
|---|---|---|---|---|
| Cards | Card (6×) | `Orders`, `GMV`, `On-time Rate`, `Not-delivered Rate`, `Avg Review Score`, `Low Score Share` | Category label on; GMV display units: millions | (label only) |
| A | Clustered column chart | X: `dim_date[year_month]`; Y: `Orders` | Colour grey; data labels off; X axis type: categorical | *Monthly orders grew from 800 in January 2017 to more than 6,000 in every month of 2018* |
| B | Line chart | X: `dim_date[year_month]`; Y: `Late Rate`, `Low Score Share` | Late Rate orange, Low Score Share blue; Y axis 0–30%; markers off; legend top | *Bad reviews peak in the same three months as late deliveries* |
| C | Clustered bar chart | Y: `fact_orders[delivery_outcome]`; X: `Share of Orders`, `Share of Low Score Reviews` | Filter: delivery_outcome is not `Unknown`; Share of Orders blue, Share of Low Score Reviews orange; data labels on | *Late and undelivered orders: 9.5% of orders, 43% of bad reviews* |

### Page 2. Delivery performance

**Page title:** *Rio de Janeiro has 13% of orders but 23% of late deliveries; most delays arise after the seller has shipped*

```
+------------------------------------------------------------------------------------------+
| PAGE TITLE                                                  [Year v] [Region v]           |
+-----------------+-----------------+-----------------+-----------------+------------------+
|   Late Rate     |   Late Orders   | Median Delivery |  Avg Delay      | Late orders      |
|     6.8%        |     6,531       |   Days 10       |  (Late) 10.6    | handed over late |
|                 |                 |                 |                 | by seller 27.7%  |
+-----------------+-----------------+-----------------+-----------------+------------------+
| [A] Late rate by customer state             | [B] Late orders by delay band               |
|     (bars, national line)                   |     (columns)                               |
|                                             +---------------------------------------------+
|                                             | [C] Seller ranking (table, 30+ orders)      |
+---------------------------------------------+---------------------------------------------+
```

| Visual | Type | Fields | Settings | Title |
|---|---|---|---|---|
| Cards | Card (5×) | `Late Rate`, `Late Orders`, `Median Delivery Days`, `Avg Delay (Late)`, `Late Orders Handed Over Late by Seller` | — | (label only) |
| A | Clustered bar chart | Y: `dim_geography[state_name]`; X: `Late Rate` | Visual filter: `Orders` is greater than or equal to 300 (21 states). Sort by Late Rate, descending. Bar colour: fx > Field value > `Colour Late Rate`. Analytics pane: constant line with value fx `Late Rate (All States)`, label "National". Data labels on | *Late rates are highest in the Northeast; Rio de Janeiro combines a high rate with high volume* |
| B | Clustered column chart | X: `fact_orders[delay_band]`; Y: `Orders` | Visual filter: delay_band is `Late 1-3 days`, `Late 4-7 days`, `Late 8-14 days`, `Late 15+ days`. Colour orange. Data labels on | *Late orders are spread fairly evenly from 1 to more than 15 days late* |
| C | Table | `dim_seller[seller_short]`, `dim_seller[seller_state]`, `Item Orders`, `Item Late Orders`, `Item Late Rate`, `Item Low Score Share` | Visual filter: `Item Orders` ≥ 30. Sort by Item Late Orders, descending. Conditional formatting: data bars on Item Late Orders (orange); background colour scale on Item Late Rate (white → orange) | *The sellers with the most late orders are large São Paulo sellers, not small outliers* |

Before writing the title of visual B and C, check them against the numbers your dashboard shows; they are
based on the tables in `reference_values.md` (sections 4 and 5).

### Page 3. Customer satisfaction

**Page title:** *On-time orders with several items get 1-2 stars more than three times as often as single-item orders; most of those customers report missing items*

```
+------------------------------------------------------------------------------------------+
| PAGE TITLE                                                  [Year v] [Region v]           |
+----------------------+----------------------+----------------------+---------------------+
|  Avg Review Score    |  Low Score Share     |  Comment Share       |  Coded Reviews      |
|       4.09           |      14.6%           |     41.2%            |       300           |
+----------------------+----------------------+----------------------+---------------------+
| [A] 1-2 star share by delay band            | [B] 1-2 star share by delivery outcome      |
|     (columns)                               |     and order size (clustered bars)         |
+---------------------------------------------+---------------------------------------------+
| [C] Complaint categories by delivery group  | [D] Category matrix: GMV vs 1-2 star share  |
|     (matrix with colour scale)              |     (scatter)                               |
+---------------------------------------------+---------------------------------------------+
```

| Visual | Type | Fields | Settings | Title |
|---|---|---|---|---|
| Cards | Card (4×) | `Avg Review Score`, `Low Score Share`, `Comment Share`, `Coded Reviews` | — | (label only) |
| A | Clustered column chart | X: `fact_orders[delay_band]`; Y: `Low Score Share` | Visual filter: delay_band is not `Unknown`. Columns: fx > Field value > `Colour Delivery`. Y axis 0–100%. Data labels on | *Bad reviews jump from 9% for on-time orders to 68% once an order is 4–7 days late* |
| B | Clustered bar chart | Y: `fact_orders[delivery_outcome]`; X: `Low Score Share`; Legend: `fact_orders[order_size]` | Visual filter: delivery_outcome is not `Unknown`; order_size is not `No items`. Single item blue, Several items orange. Data labels on | *Even when delivered on time, orders with several items get 25% bad reviews, against 7.5% for single items* |
| C | Matrix | Rows: `coded_reviews[primary_category]`; Columns: `coded_reviews[delivery_group]`; Values: `Complaint Share` | Conditional formatting > Background colour > Gradient, white (0%) → orange (max). Row subtotals off; column total on (shows "all reviews"). Add a text box below: "Sample of 300 coded 1–2 star reviews; not affected by the slicers" | *81% of complaints about on-time several-item orders are about a missing part of the order* |
| D | Scatter chart | Values: `dim_product[category_en]`; X: `Item GMV`; Y: `Item Low Score Share` | Visual filter: `Item Orders` ≥ 500 and category_en is not `unknown`. Analytics: Y-axis constant line, fx `Low Score Share (All Categories)`. Markers grey; category labels on | *Office furniture is the category with the highest share of bad reviews; large categories sit close to the average* |

The table `coded_reviews` has no relationship to the rest of the model, so the Year and Region slicers do not
change visual C. To make that explicit, select the slicer, go to Format > Edit interactions and set visual C to
"None".

## 3. Build guide, step by step

### Step 0. Prepare the data

From the repository folder, build the model and the Parquet files:

```
.venv\Scripts\python.exe run_sql.py
.venv\Scripts\python.exe notebooks\06_review_coding_results.py
```

You now have 7 Parquet files in `data\processed\` and `review_coding\coded_reviews.csv`.

### Step 1. Switch off automatic relationships

Power BI guesses relationships from column names and would connect the two fact tables through `order_id`,
which is wrong for this model.

File > Options and settings > Options > **Current file** > Data load > untick **"Autodetect new relationships
after data is loaded"**. Do this in a new, empty report before loading anything.

### Step 2. Load the tables

Home > Get data > More… > **Parquet** > Connect. In the URL / path box, paste the full path of the file, for
example:

```
C:\Users\ACER\Desktop\ecommerce-delivery-satisfaction-analysis\data\processed\fact_orders.parquet
```

Click OK, then **Transform data** (not Load) so you can check the types. If the Parquet connector does not
accept a local path, use Get data > Blank query > Advanced editor and paste
`let Source = Parquet.Document(File.Contents("C:\...\fact_orders.parquet")) in Source` with the full path. Repeat for all seven files:
`fact_orders`, `fact_order_items`, `dim_customer`, `dim_seller`, `dim_product`, `dim_date`, `dim_geography`.
Rename each query to the file name without `.parquet`.

Then Home > New source > Text/CSV > `review_coding\coded_reviews.csv`. File origin: **65001: Unicode (UTF-8)**,
delimiter: comma. Rename the query to `coded_reviews`.

**Check the column types in Power Query** (icon left of each column name):

| Column type in the files | Must be in Power BI | Examples |
|---|---|---|
| Dates | Date | `purchase_date`, `date_day`, `first_purchase_date` |
| true / false | True/False | `is_delivered`, `is_low_score`, `has_review`, `is_repeat_customer` |
| Money | Decimal number or Fixed decimal number | `items_value`, `price`, `freight_value` |
| Counts and days | Whole number | `delay_days`, `item_count`, `review_score` |
| Ids and labels | Text | `order_id`, `customer_state`, `seller_short` |

Home > Close & Apply.

### Step 3. Create the relationships

Model view (third icon on the left). Drag each dimension column onto the fact column:

| From (one side) | To (many side) |
|---|---|
| `dim_date[date_day]` | `fact_orders[purchase_date]` |
| `dim_geography[state_code]` | `fact_orders[customer_state]` |
| `dim_customer[customer_unique_id]` | `fact_orders[customer_unique_id]` |
| `dim_date[date_day]` | `fact_order_items[purchase_date]` |
| `dim_geography[state_code]` | `fact_order_items[customer_state]` |
| `dim_product[product_id]` | `fact_order_items[product_id]` |
| `dim_seller[seller_id]` | `fact_order_items[seller_id]` |

Double-click each line and check: cardinality **Many to one (\*:1)**, cross-filter direction **Single**.
There must be **no** line between `fact_orders` and `fact_order_items`, and **no** line to `coded_reviews`.

### Step 4. Model settings

1. **Date table:** select `dim_date` > Table tools > Mark as date table > column `date_day`.
2. **Sort orders** (select the column in Data view > Column tools > Sort by column):

   | Column | Sort by |
   |---|---|
   | `fact_orders[delivery_outcome]` | `fact_orders[delivery_outcome_sort]` |
   | `fact_orders[delay_band]` | `fact_orders[delay_band_sort]` |
   | `dim_date[month_name]` | `dim_date[month_number]` |
   | `coded_reviews[delivery_group]` | `coded_reviews[delivery_group_sort]` |

3. **Hide technical columns** (right-click > Hide in report view): all `_sort` columns and all id columns in
   the fact tables. Fewer fields in the list means fewer mistakes.
4. **Stop accidental sums:** for `review_score`, `delay_days`, `delivery_days`, `item_count` set
   Column tools > Summarization > **Don't summarize**. Every number on the dashboard comes from a measure.

### Step 5. Add the measures

1. Home > Enter data > name the table `_Measures` > Load. (Delete its empty column after the first measure exists.)
2. Select `_Measures`, then Modeling > New measure. Paste one measure from [`measures.dax`](measures.dax),
   press Enter. Repeat for every measure.
3. Set the format of each measure (Measure tools > Format) as written in the comment above it.

### Step 6. Apply the theme

View > Themes > Browse for themes > `dashboard\theme.json`. The default colours of every new visual now follow
the design rules.

### Step 7. Build the three pages

Follow section 2. For every visual:

- Turn the title on and type the finding from the specification table.
- Remove what does not carry information: gridlines you do not need, axis titles that repeat the title,
  legends with a single series.
- Put the slicers (Year from `dim_date[year]`, Region from `dim_geography[region]`) in the top-right of every
  page. Use View > Sync slicers so that a selection on one page applies to all three.

### Step 8. Check the numbers

Clear all slicers and compare with [`reference_values.md`](reference_values.md):

- [ ] Every card equals section 1 of the reference file.
- [ ] Page 1 chart B: March 2018 shows Late Rate 19.0% and Low Score Share 22.8%.
- [ ] Page 1 chart C: Late = 6.6% of orders and 27.7% of bad reviews.
- [ ] Page 2 chart A: Alagoas 21.5% at the top; 21 states shown.
- [ ] Page 2 table: first row `4a3ca931`, SP, 1,806 orders, 172 late orders.
- [ ] Page 3 chart A: On time 9.2%, Late 4-7 days 67.7%.
- [ ] Page 3 chart B: On time, Several items 24.6%.
- [ ] Page 3 matrix: Incomplete order × On time, several items = 81%.
- [ ] Page 3 scatter: reference line at 14.2%.

If a number differs, the cause is almost always one of three things: a relationship in the wrong direction or
missing, a column with the wrong type (a true/false column loaded as text), or a measure that uses `COUNTROWS`
on `fact_order_items` instead of `DISTINCTCOUNT` of `order_id`.

### Step 9. Save and export

1. Save as `dashboard\olist_delivery_dashboard.pbix`.
2. For each page, with all slicers cleared, take a screenshot of the full page with Win + Shift + S and save
   it as `dashboard\screenshots\01_executive_overview.png`, `02_delivery_performance.png` and
   `03_customer_satisfaction.png`.
3. Check the size of the `.pbix` file. Files above 50 MB are slow on GitHub; above 100 MB they are refused.
