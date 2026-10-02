# Decision log: data quality and cleaning

Every data quality issue found in the raw Olist data, how many rows it touches, and what was decided.
Row counts come from two generated reports: [`profiling_report.md`](profiling_report.md) (checks marked *P*)
and [`data_quality_report.md`](data_quality_report.md) (checks marked with their id, for example *B11*).

Principles:

- **Raw data is never edited.** Decisions are applied in the SQL model layer (Phase 2), where they can be read
  and reversed.
- **Keep and flag before exclude.** A row is only excluded when it cannot be measured or would distort a metric.
- **One population for all metrics**, so that numbers on different slides reconcile.

Decision types: **Exclude** (row leaves the analysis), **Fix** (value is corrected or derived),
**Keep and flag** (row stays, marked with a flag column), **Keep** (no action needed), **Not used** (column or
table is outside the scope of the business question).

## 1. Decisions that shape the results

These four choices change headline numbers. They are judgement calls, not technical necessities.

| # | Issue | Rows affected | Decision | Reason |
|---|---|---|---|---|
| 1 | Incomplete months at both ends of the period (2016-09 to 2016-12 and 2018-09 to 2018-10) | 349 of 99,441 orders (0.35%): 329 before 2017-01-01, 20 from 2018-09-01 (*A3, A4*) | **Exclude.** Analysis period = orders purchased 2017-01-01 to 2018-08-31: 99,092 orders (*A5*) | 2016 has 329 orders spread over three months with one month missing; the last two months hold 20 orders, none delivered. They would create false drops in every monthly trend and add nothing to the totals. |
| 2 | Orders that were never delivered (shipped, canceled, unavailable, invoiced, processing, created, approved) | 2,963 of 99,441 orders (2.98%) (*A2*) | **Keep and flag** as delivery outcome `not_delivered`. Excluded only from delivery-time and on-time metrics, which need a delivery date. | They are 3% of orders but carry 2,221 of the 14,494 low-score reviews (15.3%) (*A8, A9*). Dropping them, as most analyses of this dataset do, would hide one of the main sources of bad reviews. |
| 3 | Definition of "late": the promised date has no time of day (always 00:00) | 1,292 delivered orders arrived on the promised calendar day (*B11*). Late orders: 6,534 by calendar day vs 7,826 by timestamp (*B12, B13*) | **Fix.** Compare calendar dates: `delay_days = delivery date − estimated date`; late means `delay_days > 0`. Delivery on the promised day is on time. | The customer was promised a day, not an hour. A timestamp comparison would count every delivery made during the promised day as late and inflate the late count by 20%. |
| 4 | Several reviews for the same order | 547 orders; in 202 of them the scores differ (*D3, D4*) | **Fix.** Keep one review per order: the most recently answered one. 551 review rows are dropped (*D5*). | Order-level metrics need exactly one score per order, otherwise these orders are counted twice. The latest answer is the customer's final opinion. |

## 2. Orders and timestamps

| # | Issue | Rows affected | Decision | Reason |
|---|---|---|---|---|
| 5 | Status `delivered` but no customer delivery date | 8 orders (*B1*) | **Keep and flag.** Counted as orders; delivery outcome is unknown, so they are left out of on-time and delay metrics. | Delay cannot be computed. Eight rows do not justify guessing a date. |
| 6 | Status not `delivered` but a customer delivery date exists | 6 orders, all `canceled` (*B2, P*) | **Keep.** The status wins: treated as `not_delivered`; the date is ignored. | A canceled order is a failed order for the customer whatever the date says. |
| 7 | Delivered to the customer before handover to the carrier | 23 orders (*B4*) | **Keep.** The carrier date is not used for delivery time or delay. | The carrier timestamp is the unreliable one; purchase, delivery and estimate are consistent (*B3, B8* = 0). |
| 8 | Handed to the carrier before purchase or before payment approval | 166 and 1,359 orders (*B5, B6*) | **Keep and flag.** If seller handling time is analysed, negative intervals are set to NULL. | Same cause as #7. Does not affect the core delivery metrics. |
| 9 | Delivered orders without payment approval date or carrier date | 14 and 1 orders (*B9, B10*) | **Keep.** | Neither column feeds a core metric. |
| 10 | Very long deliveries and very long delays | 298 orders took more than 60 days; 345 were more than 30 days late; maximum 210 days (*B14, B15*) | **Keep.** Report medians and delay bands next to averages. | These are real service failures and exactly the subject of the analysis, not measurement errors. Averages alone would be dominated by them. |
| 11 | Deliveries far ahead of the promised date | Median delay is −12 days; 1st percentile −36 days | **Keep.** | Not an error: the promised dates are conservative. Relevant finding for the analysis, noted for Phase 4. |

## 3. Reviews

| # | Issue | Rows affected | Decision | Reason |
|---|---|---|---|---|
| 12 | One `review_id` linked to several orders | 789 `review_id` values, 1,603 review rows (*D6, D7*) | **Keep** at order level: each order keeps the score. **Fix** for the text sample (Phase 5): one row per `review_id`, which reduces the sampling frame from 10,890 to 10,759 (*P, D13*). | Checked: the rows always share the same score and text, and the orders always belong to the same person (*D8, D9* = 0). It is one customer reviewing several orders at once, so the score is valid for each order, but the same text must not be coded twice. |
| 13 | Orders without any review | 768 orders (*D11*) | **Exclude** from satisfaction metrics only. | No score exists. Non-response is not random: 2.34% of late orders have no review vs 0.55% of on-time orders. The effect is small but is stated as a limitation. |
| 14 | Comment message containing only spaces | 9 review rows (*D10*) | **Fix.** Treated as "no comment". | They carry no text. |
| 15 | Review answered before the order was delivered | 4,653 delivered orders, 4,473 of them late: 70.1% of all reviewed late orders (*D12*) | **Keep and flag** (`review_before_delivery`). | Not an error. It is how the survey works: for on-time orders it is sent 0–1 days after delivery (86,867 of 89,443, *D14, D15*); for late orders it is sent 0–3 days after the *promised* date (5,560 of 6,381, *D16, D17*), in 4,751 cases before the parcel arrived (*D18*). Consequence for interpretation: most reviews of late orders rate the experience of waiting, not the product. |
| 16 | Comment title almost always empty | 87,656 of 99,224 rows are null (*P*) | **Not used.** | Too sparse to analyse. |

## 4. Prices, freight and payments

| # | Issue | Rows affected | Decision | Reason |
|---|---|---|---|---|
| 17 | Very high item prices | 123 item rows above 2,000 BRL; maximum 6,735 BRL (*C4*) | **Keep.** Report medians next to averages. | Plausible: the five most expensive rows are housewares, computers, art and small appliances, all in delivered orders. No zero or negative prices (*C1*). |
| 18 | Freight of zero | 383 item rows (*C2*) | **Keep.** | ASSUMPTION: zero freight is free shipping, not a missing value. 0.3% of item rows. |
| 19 | Freight higher than the item price | 4,124 item rows (*C3*) | **Keep.** | Plausible for cheap items. This is a possible driver of dissatisfaction, tested in Phase 4. |
| 20 | Item total differs from payment total | 303 of 98,665 orders by more than 0.01 BRL; 249 by more than 1.00 BRL (*C5–C7*) | **Fix by definition.** Order value and GMV are computed from the item table (price, with freight shown separately). The payment table is not used. | The item table is complete for every order that has items. ASSUMPTION: the differences come from vouchers and instalment interest; not verified, because payments are outside the business question. |
| 21 | Payment anomalies: value 0, type `not_defined`, 0 instalments, one order without payment | 9, 3, 2 rows and 1 order (*C8, C9, P*) | **Not used.** | Follows from #20. |
| 22 | Orders without item rows | 775 orders: 603 unavailable, 164 canceled, 8 other (*P*) | **Keep and flag.** Counted as orders and in satisfaction metrics; no order value, seller or category. Excluded from GMV and average order value. | They are non-delivered orders that still produce reviews (see #2). |

## 5. Products, sellers, customers and geography

| # | Issue | Rows affected | Decision | Reason |
|---|---|---|---|---|
| 23 | Products without a category | 610 products, 1,603 item rows, 1.32% of item value (*P, E2*) | **Fix.** Category set to `unknown`. | Keeps totals complete; too small to distort the category ranking. |
| 24 | Categories without an English translation | 2 categories, 24 item rows (*P, E3*) | **Fix.** Translated by hand: `pc_gamer` → `pc_gamer`; `portateis_cozinha_e_preparadores_de_alimentos` → `portable_kitchen_food_preparers`. | Trivial for a Portuguese speaker. |
| 25 | An order can contain several sellers or several categories | 1,278 orders with more than one seller; 786 with more than one category (*E4, E5*) | **Keep.** Seller and category analysis runs on an item-level fact table; the order's review score is attached to each of its items. | ASSUMPTION: the score applies to every item of the order. For multi-seller orders this can blame the wrong seller; they are 1.3% of orders, stated as a limitation. |
| 26 | `customer_id` is issued per order, not per person | 99,441 `customer_id` values for 96,096 people (*P*) | **Fix.** People are counted with `customer_unique_id`. | Otherwise every customer looks like a first-time buyer and the repeat purchase rate is zero. |
| 27 | Same person, orders delivered to different states | 39 people (*E6*) | **Keep.** Geography is taken from the delivery address of each order, not from the person. | A delivery problem belongs to the place the parcel was sent to. |
| 28 | Geolocation table: duplicates, points outside Brazil, missing zip prefixes | 261,831 duplicate rows; 42 rows outside Brazil; 278 customer rows and 7 sellers without a match (*P, E7, E8*) | **Not used.** Geography is analysed by state; distance is approximated by "seller and customer in the same state or not". | State is complete for every customer and seller (*E9, E10* = 0). Cleaning one million coordinate rows would not change the recommendation. To be revisited only if Phase 4 shows that the state-level view is not enough. |
| 29 | Implausible `shipping_limit_date` | 4 item rows dated after 2018-12-31 (*P*) | **Not used.** | The column is not needed. |
| 30 | Product weight of zero, missing dimensions | 4 and 2 products (*P*) | **Not used.** | Weight and dimensions are outside the scope. |
| 31 | Misspelled source columns (`product_name_lenght`, `product_description_lenght`) | 2 columns | **Fix** if the columns are used: renamed in the model. | Readability. |

## 6. What was checked and found clean

| Check | Result |
|---|---|
| Duplicate primary keys in orders, order items, payments, customers, sellers, products | none (*P*) |
| Orphan records: items, payments or reviews pointing to an order that does not exist | none (*P*) |
| Orphan records: items pointing to a product or seller that does not exist | none (*P*) |
| Delivery before purchase, payment approval before purchase, promised date before purchase | none (*B3, B7, B8*) |
| Missing customer or seller state | none (*E9, E10*) |
| Review scores outside 1–5, missing scores | none (*P*) |
