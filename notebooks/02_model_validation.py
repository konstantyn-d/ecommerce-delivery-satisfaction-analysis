# %% [markdown]
# # 02 - Model validation (Phase 2)
#
# Goal: prove that the star schema is correct before any analysis is built on it.
# Each test compares an EXPECTED value (computed independently from the raw tables, or a fixed
# rule such as "0 duplicates") with the ACTUAL value in the model. A test passes when they match.
#
# Input : data/processed/olist.duckdb (built by `python run_sql.py`)
# Output: docs/model_validation_report.md (generated - do not edit by hand)
#
# The script stops with an error if any test fails.

# %%
import sys
from decimal import Decimal
from pathlib import Path

import duckdb

# Windows consoles default to a legacy code page; force UTF-8 so the report prints safely.
sys.stdout.reconfigure(encoding="utf-8")

try:
    ROOT = Path(__file__).resolve().parents[1]
except NameError:  # running cell by cell: fall back to the working directory
    ROOT = Path.cwd() if (Path.cwd() / "sql").exists() else Path.cwd().parent

DB_PATH = ROOT / "data" / "processed" / "olist.duckdb"
REPORT_PATH = ROOT / "docs" / "model_validation_report.md"

con = duckdb.connect(str(DB_PATH), read_only=True)
report = []


# %%
def fmt(value) -> str:
    """Format a value for a markdown table cell."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, (float, Decimal)):
        return f"{value:,.2f}"
    return str(value).replace("|", "/")


def md_table(headers, rows) -> list:
    """Build a markdown table from a header list and a list of rows."""
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in rows]
    return lines + [""]


def scalar(sql: str):
    """Run a query that returns one single value."""
    return con.execute(sql).fetchone()[0]


# The analysis period, written once so that every "expected" query uses the same filter.
IN_PERIOD = (
    "order_purchase_timestamp >= TIMESTAMP '2017-01-01' "
    "AND order_purchase_timestamp < TIMESTAMP '2018-09-01'"
)
RAW_ORDERS_IN_PERIOD = f"(SELECT * FROM raw.orders WHERE {IN_PERIOD})"

# %% [markdown]
# ## Tests
# Each test = (group, description, SQL for the expected value, SQL for the actual value).
# A plain number as "expected" means a fixed rule (for example 0 duplicates).

# %%
TESTS = [
    # ---- 1. Row counts: the model contains exactly the orders and items of the analysis period
    ("Row counts", "fact_orders rows = raw orders in the analysis period",
     f"SELECT count(*) FROM {RAW_ORDERS_IN_PERIOD}",
     "SELECT count(*) FROM model.fact_orders"),
    ("Row counts", "fact_order_items rows = raw item rows of in-period orders",
     f"SELECT count(*) FROM raw.order_items i JOIN {RAW_ORDERS_IN_PERIOD} o USING (order_id)",
     "SELECT count(*) FROM model.fact_order_items"),
    ("Row counts", "dim_customer rows = distinct people with an in-period order",
     f"SELECT count(DISTINCT c.customer_unique_id) FROM {RAW_ORDERS_IN_PERIOD} o JOIN raw.customers c USING (customer_id)",
     "SELECT count(*) FROM model.dim_customer"),
    ("Row counts", "dim_customer order_count adds up to fact_orders rows",
     "SELECT count(*) FROM model.fact_orders",
     "SELECT sum(order_count)::BIGINT FROM model.dim_customer"),
    ("Row counts", "dim_date has one row per day from 2017-01-01 to 2018-08-31",
     "SELECT date_diff('day', DATE '2017-01-01', DATE '2018-08-31') + 1",
     "SELECT count(*) FROM model.dim_date"),

    # ---- 2. Keys: every table has exactly one row per key
    ("Unique keys", "fact_orders: duplicate order_id", 0,
     "SELECT count(*) - count(DISTINCT order_id) FROM model.fact_orders"),
    ("Unique keys", "fact_order_items: duplicate (order_id, order_item_id)", 0,
     "SELECT count(*) - (SELECT count(*) FROM (SELECT DISTINCT order_id, order_item_id FROM model.fact_order_items)) FROM model.fact_order_items"),
    ("Unique keys", "dim_customer: duplicate customer_unique_id", 0,
     "SELECT count(*) - count(DISTINCT customer_unique_id) FROM model.dim_customer"),
    ("Unique keys", "dim_seller: duplicate seller_id", 0,
     "SELECT count(*) - count(DISTINCT seller_id) FROM model.dim_seller"),
    ("Unique keys", "dim_product: duplicate product_id", 0,
     "SELECT count(*) - count(DISTINCT product_id) FROM model.dim_product"),
    ("Unique keys", "dim_date: duplicate date_day", 0,
     "SELECT count(*) - count(DISTINCT date_day) FROM model.dim_date"),
    ("Unique keys", "dim_geography: duplicate state_code", 0,
     "SELECT count(*) - count(DISTINCT state_code) FROM model.dim_geography"),

    # ---- 3. Relationships: every fact row finds its dimension row
    ("Relationships", "fact_orders rows without a dim_customer row", 0,
     "SELECT count(*) FROM model.fact_orders f ANTI JOIN model.dim_customer d USING (customer_unique_id)"),
    ("Relationships", "fact_orders rows without a dim_date row", 0,
     "SELECT count(*) FROM model.fact_orders f ANTI JOIN model.dim_date d ON d.date_day = f.purchase_date"),
    ("Relationships", "fact_orders rows without a dim_geography row", 0,
     "SELECT count(*) FROM model.fact_orders f ANTI JOIN model.dim_geography d ON d.state_code = f.customer_state"),
    ("Relationships", "fact_order_items rows without a fact_orders row", 0,
     "SELECT count(*) FROM model.fact_order_items i ANTI JOIN model.fact_orders f USING (order_id)"),
    ("Relationships", "fact_order_items rows without a dim_product row", 0,
     "SELECT count(*) FROM model.fact_order_items i ANTI JOIN model.dim_product d USING (product_id)"),
    ("Relationships", "fact_order_items rows without a dim_seller row", 0,
     "SELECT count(*) FROM model.fact_order_items i ANTI JOIN model.dim_seller d USING (seller_id)"),
    ("Relationships", "dim_seller rows without a region", 0,
     "SELECT count(*) FROM model.dim_seller WHERE seller_region IS NULL"),
    ("Relationships", "dim_product rows without an English category", 0,
     "SELECT count(*) FROM model.dim_product WHERE category_en IS NULL"),

    # ---- 4. Values: totals in the model equal totals in the raw data
    ("Value reconciliation", "sum of item price: fact_order_items = raw",
     f"SELECT sum(i.price) FROM raw.order_items i JOIN {RAW_ORDERS_IN_PERIOD} o USING (order_id)",
     "SELECT sum(price) FROM model.fact_order_items"),
    ("Value reconciliation", "sum of item price: fact_orders = raw",
     f"SELECT sum(i.price) FROM raw.order_items i JOIN {RAW_ORDERS_IN_PERIOD} o USING (order_id)",
     "SELECT sum(items_value) FROM model.fact_orders"),
    ("Value reconciliation", "sum of freight: fact_orders = raw",
     f"SELECT sum(i.freight_value) FROM raw.order_items i JOIN {RAW_ORDERS_IN_PERIOD} o USING (order_id)",
     "SELECT sum(freight_value) FROM model.fact_orders"),
    ("Value reconciliation", "sum of item_count in fact_orders = fact_order_items rows",
     "SELECT count(*) FROM model.fact_order_items",
     "SELECT sum(item_count)::BIGINT FROM model.fact_orders"),
    ("Value reconciliation", "orders without items = raw in-period orders without item rows",
     f"SELECT count(*) FROM {RAW_ORDERS_IN_PERIOD} o WHERE NOT EXISTS (SELECT 1 FROM raw.order_items i WHERE i.order_id = o.order_id)",
     "SELECT count(*) FROM model.fact_orders WHERE NOT has_items"),

    # ---- 5. Reviews: one score per order, nothing lost
    ("Reviews", "orders with a review = raw in-period orders that have at least one review",
     f"SELECT count(DISTINCT r.order_id) FROM raw.order_reviews r JOIN {RAW_ORDERS_IN_PERIOD} o USING (order_id)",
     "SELECT count(*) FROM model.fact_orders WHERE has_review"),
    ("Reviews", "review score missing although has_review is true", 0,
     "SELECT count(*) FROM model.fact_orders WHERE has_review AND review_score IS NULL"),
    ("Reviews", "review score present although has_review is false", 0,
     "SELECT count(*) FROM model.fact_orders WHERE NOT has_review AND review_score IS NOT NULL"),
    ("Reviews", "review scores outside 1-5", 0,
     "SELECT count(*) FROM model.fact_orders WHERE review_score NOT BETWEEN 1 AND 5"),

    # ---- 6. Delivery logic: the derived fields agree with each other and with the raw data
    ("Delivery logic", "delivered orders with a delivery date = raw",
     f"SELECT count(*) FROM {RAW_ORDERS_IN_PERIOD} WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL",
     "SELECT count(*) FROM model.fact_orders WHERE is_delivered"),
    ("Delivery logic", "late orders = raw (delivery calendar date after estimated calendar date)",
     f"""SELECT count(*) FROM {RAW_ORDERS_IN_PERIOD} WHERE order_status = 'delivered'
         AND order_delivered_customer_date::DATE > order_estimated_delivery_date::DATE""",
     "SELECT count(*) FROM model.fact_orders WHERE delivery_outcome = 'Late'"),
    ("Delivery logic", "'On time' + 'Late' = delivered orders with a delivery date",
     "SELECT count(*) FROM model.fact_orders WHERE is_delivered",
     "SELECT count(*) FROM model.fact_orders WHERE delivery_outcome IN ('On time', 'Late')"),
    ("Delivery logic", "is_on_time filled for an order that is not measurable", 0,
     "SELECT count(*) FROM model.fact_orders WHERE NOT is_delivered AND is_on_time IS NOT NULL"),
    ("Delivery logic", "is_on_time disagrees with delivery_outcome", 0,
     """SELECT count(*) FROM model.fact_orders WHERE is_delivered
        AND is_on_time <> (delivery_outcome = 'On time')"""),
    ("Delivery logic", "negative delivery_days, handling_days or transit_days", 0,
     "SELECT count(*) FROM model.fact_orders WHERE delivery_days < 0 OR handling_days < 0 OR transit_days < 0"),
    ("Delivery logic", "delivery_outcome 'Not delivered' = raw in-period orders with another status",
     f"SELECT count(*) FROM {RAW_ORDERS_IN_PERIOD} WHERE order_status <> 'delivered'",
     "SELECT count(*) FROM model.fact_orders WHERE delivery_outcome = 'Not delivered'"),
]

# %%
results = []
for group, label, expected_sql, actual_sql in TESTS:
    expected = expected_sql if isinstance(expected_sql, int) else scalar(expected_sql)
    actual = scalar(actual_sql)
    results.append((group, label, expected, actual, "PASS" if expected == actual else "FAIL"))

failed = [r for r in results if r[4] == "FAIL"]

report += [
    "# Model validation report",
    "",
    "Generated by `notebooks/02_model_validation.py` from `data/processed/olist.duckdb` "
    f"(DuckDB {duckdb.__version__}). Do not edit by hand: re-run the script instead.",
    "",
    f"**{len(results) - len(failed)} of {len(results)} tests passed.**",
    "",
    "## 1. Tests",
    "",
    "*Expected* is computed independently from the raw tables or is a fixed rule (0 = none allowed). "
    "*Actual* is read from the model.",
    "",
]
report += md_table(["group", "test", "expected", "actual", "result"], results)

# %% [markdown]
# ## What the model contains
# Not tests: a factual summary of the model, used as the reference for later phases.

# %%
report += ["## 2. Model contents", "", "### Tables", ""]
report += md_table(
    ["table", "rows", "grain"],
    [
        ("model.fact_orders", scalar("SELECT count(*) FROM model.fact_orders"), "one order"),
        ("model.fact_order_items", scalar("SELECT count(*) FROM model.fact_order_items"), "one unit sold"),
        ("model.dim_customer", scalar("SELECT count(*) FROM model.dim_customer"), "one person"),
        ("model.dim_seller", scalar("SELECT count(*) FROM model.dim_seller"), "one seller"),
        ("model.dim_product", scalar("SELECT count(*) FROM model.dim_product"), "one product"),
        ("model.dim_date", scalar("SELECT count(*) FROM model.dim_date"), "one calendar day"),
        ("model.dim_geography", scalar("SELECT count(*) FROM model.dim_geography"), "one state"),
    ],
)

report += ["### Orders by delivery outcome and delay band", ""]
report += md_table(
    ["delivery_outcome", "delay_band", "orders", "with review", "with items"],
    con.execute(
        """
        SELECT delivery_outcome, delay_band, count(*),
               count(*) FILTER (WHERE has_review), count(*) FILTER (WHERE has_items)
        FROM model.fact_orders
        GROUP BY delivery_outcome, delay_band, delay_band_sort
        ORDER BY delay_band_sort
        """
    ).fetchall(),
)

report += ["### Filled values in fact_orders (rows where the column is not NULL)", ""]
columns = [row[0] for row in con.execute("DESCRIBE model.fact_orders").fetchall()]
filled = con.execute(
    "SELECT " + ", ".join(f'count("{c}")' for c in columns) + " FROM model.fact_orders"
).fetchone()
total = scalar("SELECT count(*) FROM model.fact_orders")
report += md_table(
    ["column", "filled rows", "NULL rows"],
    [(c, n, total - n) for c, n in zip(columns, filled)],
)

report += ["### Customers: two ways to count a repeat customer", ""]
report += md_table(
    ["definition", "people"],
    [
        ("people in dim_customer", scalar("SELECT count(*) FROM model.dim_customer")),
        ("more than one order (order_count > 1)", scalar("SELECT count(*) FROM model.dim_customer WHERE order_count > 1")),
        ("orders on more than one day (is_repeat_customer)", scalar("SELECT count(*) FROM model.dim_customer WHERE is_repeat_customer")),
    ],
)

report += ["### Seller handover, same-state shipments and multi-seller orders (orders with items)", ""]
report += md_table(
    ["flag", "true", "false", "NULL"],
    con.execute(
        """
        SELECT 'is_seller_handover_late', count(*) FILTER (WHERE is_seller_handover_late),
               count(*) FILTER (WHERE NOT is_seller_handover_late), count(*) FILTER (WHERE is_seller_handover_late IS NULL)
        FROM model.fact_orders WHERE has_items
        UNION ALL
        SELECT 'is_same_state', count(*) FILTER (WHERE is_same_state),
               count(*) FILTER (WHERE NOT is_same_state), count(*) FILTER (WHERE is_same_state IS NULL)
        FROM model.fact_orders WHERE has_items
        UNION ALL
        SELECT 'more than one seller (seller_count > 1)', count(*) FILTER (WHERE seller_count > 1),
               count(*) FILTER (WHERE seller_count = 1), count(*) FILTER (WHERE seller_count IS NULL)
        FROM model.fact_orders WHERE has_items
        """
    ).fetchall(),
)

# %%
REPORT_PATH.write_text("\n".join(report), encoding="utf-8")
con.close()
print("\n".join(report))
print(f"\nReport written to {REPORT_PATH.relative_to(ROOT)}")

if failed:
    sys.exit(f"{len(failed)} model test(s) FAILED - fix the model before continuing.")
