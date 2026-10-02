# %% [markdown]
# # 04 - Hypothesis-driven analysis (Phase 4)
#
# Goal: test every branch of the issue tree "Why are customers unhappy?" with data.
# Each section tests one branch: delivery, product, seller, geography, price, plus the effect on
# repeat purchases and a robustness check.
#
# Input : data/processed/olist.duckdb (star schema in schema `model`)
# Output: docs/analysis_results.md (generated tables - do not edit by hand)
#         docs/charts/*.png        (charts with action titles)
#
# The interpretation of these tables is written by hand in docs/analysis_findings.md.
# Everything here is observational: the tables show associations, not proven causes.

# %%
import math
import sys
import textwrap
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")  # draw to files, no window needed
import matplotlib.pyplot as plt

# Windows consoles default to a legacy code page; force UTF-8 so the report prints safely.
sys.stdout.reconfigure(encoding="utf-8")

try:
    ROOT = Path(__file__).resolve().parents[1]
except NameError:  # running cell by cell: fall back to the working directory
    ROOT = Path.cwd() if (Path.cwd() / "sql").exists() else Path.cwd().parent

DB_PATH = ROOT / "data" / "processed" / "olist.duckdb"
REPORT_PATH = ROOT / "docs" / "analysis_results.md"
CHART_DIR = ROOT / "docs" / "charts"
CHART_DIR.mkdir(exist_ok=True)

con = duckdb.connect(str(DB_PATH), read_only=True)
report = []


# %% [markdown]
# ## Helpers: formatting, queries, chart style

# %%
def n(value) -> str:      # whole number with thousands separator
    return "" if value is None else f"{value:,.0f}"


def pct(value) -> str:    # rate as a percentage with one decimal
    return "" if value is None else f"{value:.1%}"


def dec(value) -> str:    # plain number with two decimals
    return "" if value is None else f"{value:.2f}"


def md_table(headers, rows) -> list:
    """Build a markdown table from a header list and a list of already formatted rows."""
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]
    return lines + [""]


def rows(sql: str) -> list:
    """Run a query and return all rows."""
    return con.execute(sql).fetchall()


def scalar(sql: str):
    """Run a query that returns one single value."""
    return con.execute(sql).fetchone()[0]


# The same six measures are needed for almost every cut of fact_orders, so they are written once.
ORDER_MEASURES = """
    count(*)                                                        AS orders,
    count(*) FILTER (WHERE delivery_outcome = 'Late')
        / nullif(count(*) FILTER (WHERE is_delivered), 0)           AS late_rate,
    count(*) FILTER (WHERE has_review)                              AS reviewed,
    avg(review_score)                                               AS avg_score,
    count(*) FILTER (WHERE is_low_score)                            AS low_reviews,
    count(*) FILTER (WHERE is_low_score)
        / nullif(count(*) FILTER (WHERE has_review), 0)             AS low_share
"""
ORDER_HEADERS = ["orders", "late rate", "reviewed orders", "avg score", "1-2 star reviews", "1-2 star share"]


def orders_by(group_sql: str, where: str = "TRUE", order_by: str = "1") -> list:
    """Group fact_orders by one expression and return the standard measures."""
    return rows(
        f"""
        SELECT {group_sql} AS grp, {ORDER_MEASURES}
        FROM model.fact_orders
        WHERE {where}
        GROUP BY grp
        ORDER BY {order_by}
        """
    )


def format_orders(result) -> list:
    """Format the rows returned by orders_by() for a markdown table."""
    return [(r[0], n(r[1]), pct(r[2]), n(r[3]), dec(r[4]), n(r[5]), pct(r[6])) for r in result]


def section(title: str, text: str = "") -> None:
    """Start a new section in the report."""
    report.extend([f"## {title}", ""] + ([text, ""] if text else []))


def table(title: str, headers, body) -> None:
    """Add a titled table to the report."""
    report.extend([f"### {title}", ""] + md_table(headers, body))


# Chart style: one colour for "good / reference", one accent colour for "problem", grey for context.
BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#a8a7a0"
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SOURCE_NOTE = "Source: Olist public dataset, orders purchased Jan 2017 - Aug 2018."

plt.rcParams.update(
    {
        "font.family": ["Segoe UI", "DejaVu Sans"],
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_2,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
    }
)


def new_figure(title: str, subtitle: str, width: float = 9, height: float = 5, ncols: int = 1):
    """Create a figure with a left-aligned action title (the finding) and a subtitle (what is shown)."""
    fig, axes = plt.subplots(1, ncols, figsize=(width, height), dpi=150, sharey=ncols > 1)
    fig.patch.set_facecolor(SURFACE)
    wrapped = textwrap.fill(title, int(width * 9.5))
    title_lines = wrapped.count("\n") + 1
    # Positions are computed in inches so that the layout works for any figure height.
    title_y = 1 - 0.15 / height
    subtitle_y = title_y - (0.30 * title_lines) / height
    fig.text(0.03, title_y, wrapped, ha="left", va="top", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.03, subtitle_y, subtitle, ha="left", va="top", fontsize=9.5, color=INK_2)
    fig.subplots_adjust(top=subtitle_y - 0.45 / height, bottom=0.75 / height, left=0.09, right=0.96)
    for ax in (axes if ncols > 1 else [axes]):
        ax.set_facecolor(SURFACE)
        ax.set_axisbelow(True)
    return fig, axes


def save(fig, name: str, note: str = "") -> None:
    """Add the source note and save the chart as PNG."""
    fig.text(0.03, 0.02, (SOURCE_NOTE + " " + note).strip(), ha="left", va="bottom", fontsize=8, color=MUTED)
    fig.savefig(CHART_DIR / name, facecolor=SURFACE)
    plt.close(fig)
    print(f"chart saved: docs/charts/{name}")


def percent_axis(ax, axis: str = "y") -> None:
    """Format an axis as percentages and draw hairline gridlines across it."""
    formatter = matplotlib.ticker.PercentFormatter(xmax=1, decimals=0)
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(formatter)
    ax.grid(axis=axis, color=GRID, linewidth=0.8)


report += [
    "# Analysis results",
    "",
    "Generated by `notebooks/04_hypothesis_analysis.py` from the star schema "
    f"(DuckDB {duckdb.__version__}). Do not edit by hand: re-run the script instead.",
    "",
    "Interpretation: [`analysis_findings.md`](analysis_findings.md). "
    "Metric definitions: [`metric_definitions.md`](metric_definitions.md).",
    "",
    "Reading guide: *late rate* = late orders / delivered orders. *1-2 star share* = orders with a review "
    "score of 1 or 2 / orders with a review. All tables are observational: they show associations, "
    "not proven causes.",
    "",
]

TOTAL_ORDERS = scalar("SELECT count(*) FROM model.fact_orders")
TOTAL_LOW = scalar("SELECT count(*) FROM model.fact_orders WHERE is_low_score")
OVERALL_LOW_SHARE = scalar("SELECT low_score_rate FROM model.kpi_orders WHERE period = 'Total'")
OVERALL_LATE_RATE = scalar("SELECT late_rate FROM model.kpi_orders WHERE period = 'Total'")


# %% [markdown]
# ## A. Delivery branch
# Hypothesis: customers punish orders that arrive late or not at all.

# %%
section("A. Delivery")

# A1 - the headline comparison, with each group's share of all orders and of all bad reviews
a1 = rows(
    f"""
    SELECT delivery_outcome, {ORDER_MEASURES},
           count(*) / {TOTAL_ORDERS}                                  AS share_of_orders,
           count(*) FILTER (WHERE is_low_score) / {TOTAL_LOW}         AS share_of_low_reviews
    FROM model.fact_orders
    GROUP BY delivery_outcome
    ORDER BY orders DESC
    """
)
table(
    "A1. Review outcome by delivery outcome",
    ["delivery outcome"] + ORDER_HEADERS[:1] + ORDER_HEADERS[2:] + ["share of all orders", "share of all 1-2 star reviews"],
    [(r[0], n(r[1]), n(r[3]), dec(r[4]), n(r[5]), pct(r[6]), pct(r[7]), pct(r[8])) for r in a1],
)

# A2 - dose-response: does the share of bad reviews grow with the length of the delay?
a2 = rows(
    f"""
    SELECT delay_band, {ORDER_MEASURES}
    FROM model.fact_orders
    GROUP BY delay_band, delay_band_sort
    ORDER BY delay_band_sort
    """
)
table(
    "A2. Review outcome by delay band",
    ["delay band"] + ORDER_HEADERS[:1] + ORDER_HEADERS[2:],
    [(r[0], n(r[1]), n(r[3]), dec(r[4]), n(r[5]), pct(r[6])) for r in a2],
)

# A3 - what kind of failure is "not delivered"?
a3 = orders_by("order_status", where="delivery_outcome = 'Not delivered'", order_by="orders DESC")
table(
    "A3. Not-delivered orders by order status",
    ["order status"] + ORDER_HEADERS[:1] + ORDER_HEADERS[2:],
    [(r[0], n(r[1]), n(r[3]), dec(r[4]), n(r[5]), pct(r[6])) for r in a3],
)

# A4 - late orders: was the review written while the customer was still waiting?
a4 = orders_by(
    "CASE WHEN review_before_delivery THEN 'review answered BEFORE the delivery' "
    "ELSE 'review answered AFTER the delivery' END",
    where="delivery_outcome = 'Late' AND has_review",
)
table(
    "A4. Late orders: review answered before or after the parcel arrived",
    ["late orders"] + ORDER_HEADERS[:1] + ORDER_HEADERS[3:],
    [(r[0], n(r[1]), dec(r[4]), n(r[5]), pct(r[6])) for r in a4],
)

# A5 - slow but on time: among orders that kept the promise, does a longer wait still hurt?
DELIVERY_BAND = """CASE WHEN delivery_days <= 7  THEN '0-7 days'
                        WHEN delivery_days <= 14 THEN '8-14 days'
                        WHEN delivery_days <= 21 THEN '15-21 days'
                        WHEN delivery_days <= 28 THEN '22-28 days'
                        ELSE '29+ days' END"""
a5_all = orders_by(DELIVERY_BAND, where="delivery_outcome = 'On time'", order_by="min(delivery_days)")
a5_single = orders_by(DELIVERY_BAND, where="delivery_outcome = 'On time' AND item_count = 1", order_by="min(delivery_days)")
table(
    "A5. On-time orders by delivery time",
    ["delivery time", "orders", "1-2 star share", "orders (single-item only)", "1-2 star share (single-item only)"],
    [(a[0], n(a[1]), pct(a[6]), n(s[1]), pct(s[6])) for a, s in zip(a5_all, a5_single)],
)

# A6 - where is the time lost? promise vs seller handling vs carrier transit
a6 = rows(
    """
    SELECT delivery_outcome, count(*),
           median(promised_days), median(delivery_days), median(handling_days), median(transit_days),
           count(*) FILTER (WHERE is_seller_handover_late),
           count(*) FILTER (WHERE is_seller_handover_late) / count(is_seller_handover_late)
    FROM model.fact_orders
    WHERE is_delivered
    GROUP BY delivery_outcome
    ORDER BY delivery_outcome DESC
    """
)
table(
    "A6. On-time vs late orders: promised time, seller handling time and carrier transit time (medians, days)",
    ["delivery outcome", "orders", "promised days", "delivery days", "handling days (seller)",
     "transit days (carrier)", "orders handed over late by the seller", "share handed over late"],
    [(r[0], n(r[1]), n(r[2]), n(r[3]), n(r[4]), n(r[5]), n(r[6]), pct(r[7])) for r in a6],
)

# A7 - over time: do bad reviews move together with late deliveries?
a7 = rows(
    """
    SELECT period, orders, late_rate, not_delivered_rate, low_score_rate, avg_review_score
    FROM model.kpi_orders WHERE period <> 'Total' ORDER BY period
    """
)
month_corr = scalar("SELECT corr(late_rate, low_score_rate) FROM model.kpi_orders WHERE period <> 'Total'")
table(
    "A7. Late rate and 1-2 star share by purchase month",
    ["month", "orders", "late rate", "not-delivered rate", "1-2 star share", "avg score"],
    [(r[0], n(r[1]), pct(r[2]), pct(r[3]), pct(r[4]), dec(r[5])) for r in a7],
)
report += [
    f"Correlation between the monthly late rate and the monthly 1-2 star share: **{month_corr:.2f}** "
    f"({len(a7)} months). A correlation of monthly aggregates, not of individual orders.",
    "",
]

# %%
# Chart 1 - share of bad reviews by delay band
bands = [r for r in a2 if r[0] != "Unknown"]
labels = [r[0].replace("Late ", "").replace(" days", "\ndays late") if r[0].startswith("Late") else r[0] for r in bands]
values = [r[6] for r in bands]
on_time_share = values[0]
band_4_7 = next(r[6] for r in bands if r[0] == "Late 4-7 days")

fig, ax = new_figure(
    f"Bad reviews jump from {on_time_share:.0%} for on-time orders to {band_4_7:.0%} "
    "once an order is 4-7 days late",
    "Share of reviewed orders with a 1-2 star review, by delivery outcome",
)
colours = [BLUE] + [ORANGE] * (len(bands) - 1)
ax.bar(range(len(bands)), values, width=0.42, color=colours)
for x, v in enumerate(values):
    ax.text(x, v + 0.015, f"{v:.0%}", ha="center", va="bottom", fontsize=10, color=INK)
ax.set_xticks(range(len(bands)), labels)
ax.set_ylim(0, 1)
percent_axis(ax)
ax.legend(
    handles=[plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)],
    labels=["Promise kept", "Promise broken"], loc="upper left", frameon=False, ncols=2,
)
save(fig, "01_low_score_by_delay_band.png", f"n = {sum(r[3] for r in bands):,} reviewed orders.")

# Chart 2 - where do the bad reviews come from?
groups = [r for r in a1 if r[0] != "Unknown"]
fig, ax = new_figure(
    f"Late and undelivered orders are {sum(r[7] for r in groups if r[0] != 'On time'):.1%} of orders "
    f"but account for {sum(r[8] for r in groups if r[0] != 'On time'):.0%} of all bad reviews",
    "Each delivery outcome's share of all orders vs its share of all 1-2 star reviews",
    height=4.2,
)
y = range(len(groups))
ax.barh([i - 0.19 for i in y], [r[7] for r in groups], height=0.34, color=BLUE, label="Share of all orders")
ax.barh([i + 0.19 for i in y], [r[8] for r in groups], height=0.34, color=ORANGE, label="Share of all 1-2 star reviews")
for i, r in enumerate(groups):
    ax.text(r[7] + 0.01, i - 0.19, f"{r[7]:.1%}", va="center", fontsize=9.5, color=INK)
    ax.text(r[8] + 0.01, i + 0.19, f"{r[8]:.1%}", va="center", fontsize=9.5, color=INK)
ax.set_yticks(list(y), [r[0] for r in groups])
ax.invert_yaxis()
ax.set_xlim(0, 1.05)
percent_axis(ax, "x")
ax.legend(loc="lower right", frameon=False)
fig.subplots_adjust(left=0.14)
save(fig, "02_bad_reviews_by_delivery_outcome.png", f"n = {TOTAL_LOW:,} orders with a 1-2 star review.")

# Chart 3 - monthly late rate and bad review share (both are percentages: one shared axis)
months = [r[0] for r in a7]
fig, ax = new_figure(
    "Bad reviews rise and fall with late deliveries: the three worst months for delays "
    "are the three worst months for reviews",
    f"Late rate and share of 1-2 star reviews by purchase month (correlation of the monthly values: {month_corr:.2f})",
)
ax.plot(months, [r[4] for r in a7], color=BLUE, linewidth=2, label="Share of 1-2 star reviews")
ax.plot(months, [r[2] for r in a7], color=ORANGE, linewidth=2, label="Late rate")
worst = sorted(a7, key=lambda r: r[2], reverse=True)[:3]
for r in worst:
    ax.plot(r[0], r[2], "o", color=ORANGE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.plot(r[0], r[4], "o", color=BLUE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.annotate(f"{r[4]:.0%}", (r[0], r[4]), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=9, color=INK)
    ax.annotate(f"{r[2]:.0%}", (r[0], r[2]), textcoords="offset points", xytext=(10, -4), ha="left", fontsize=9, color=INK)
ax.set_ylim(0, 0.30)
percent_axis(ax)
ax.set_xticks(months[::2], months[::2], rotation=0, fontsize=8.5)
ax.legend(loc="upper left", frameon=False, ncols=2)
save(fig, "03_monthly_late_rate_vs_bad_reviews.png")


# %% [markdown]
# ## B. Product branch
# Hypotheses: (1) orders with several items disappoint more often; (2) some categories are structurally worse.

# %%
section("B. Product and order composition")

con.execute(
    """
    CREATE OR REPLACE TEMP VIEW order_composition AS
    SELECT order_id,
           CASE WHEN count(*) = 1                   THEN '1 item'
                WHEN count(DISTINCT seller_id) > 1  THEN '2+ items from different sellers'
                WHEN count(DISTINCT product_id) = 1 THEN '2+ units of the same product'
                ELSE '2+ different products, one seller' END AS composition,
           CASE WHEN count(*) = 1                   THEN 1
                WHEN count(DISTINCT seller_id) > 1  THEN 4
                WHEN count(DISTINCT product_id) = 1 THEN 2
                ELSE 3 END AS composition_sort
    FROM model.fact_order_items
    GROUP BY order_id
    """
)
b1 = rows(
    f"""
    SELECT c.composition, {ORDER_MEASURES},
           count(*) FILTER (WHERE delivery_outcome = 'On time')                              AS on_time_orders,
           count(*) FILTER (WHERE delivery_outcome = 'On time' AND is_low_score)             AS on_time_low,
           count(*) FILTER (WHERE delivery_outcome = 'On time' AND is_low_score)
               / count(*) FILTER (WHERE delivery_outcome = 'On time' AND has_review)         AS on_time_low_share
    FROM model.fact_orders f
    JOIN order_composition c USING (order_id)
    GROUP BY c.composition, c.composition_sort
    ORDER BY c.composition_sort
    """
)
table(
    "B1. Review outcome by order composition",
    ["order composition", "orders", "late rate", "1-2 star share (all)", "on-time orders",
     "1-2 star reviews (on-time)", "1-2 star share (on-time)"],
    [(r[0], n(r[1]), pct(r[2]), pct(r[6]), n(r[7]), n(r[8]), pct(r[9])) for r in b1],
)
multi_on_time_low = sum(r[8] for r in b1[1:])
on_time_low_total = scalar("SELECT count(*) FROM model.fact_orders WHERE delivery_outcome = 'On time' AND is_low_score")
report += [
    f"On-time orders with two or more items: {n(sum(r[7] for r in b1[1:]))} orders "
    f"({pct(sum(r[7] for r in b1[1:]) / sum(r[7] for r in b1))} of on-time orders with items) and "
    f"{n(multi_on_time_low)} of the {n(on_time_low_total)} bad reviews of on-time orders "
    f"({pct(multi_on_time_low / on_time_low_total)}).",
    "",
]

# B2 - categories. An order is counted once per category it contains (distinct orders).
con.execute(
    """
    CREATE OR REPLACE TEMP VIEW category_stats AS
    SELECT p.category_en,
           sum(i.price)                                                                   AS gmv,
           sum(i.price) / (SELECT sum(price) FROM model.fact_order_items)                 AS gmv_share,
           count(DISTINCT i.order_id)                                                     AS orders,
           count(DISTINCT i.order_id) FILTER (WHERE i.delivery_outcome = 'Late')
               / count(DISTINCT i.order_id) FILTER (WHERE i.is_delivered)                 AS late_rate,
           count(DISTINCT i.order_id) FILTER (WHERE i.is_low_score)
               / count(DISTINCT i.order_id) FILTER (WHERE i.has_review)                   AS low_share,
           -- the "clean" comparison: one item, delivered on time -> delivery and order size are held constant
           count(DISTINCT i.order_id) FILTER (WHERE i.is_low_score AND i.delivery_outcome = 'On time' AND f.item_count = 1)
               / nullif(count(DISTINCT i.order_id) FILTER (WHERE i.has_review AND i.delivery_outcome = 'On time' AND f.item_count = 1), 0)
                                                                                          AS low_share_clean
    FROM model.fact_order_items i
    JOIN model.dim_product p USING (product_id)
    JOIN model.fact_orders f USING (order_id)
    GROUP BY p.category_en
    """
)
CATEGORY_HEADERS = ["category", "GMV (BRL)", "share of GMV", "orders", "late rate", "1-2 star share",
                    "1-2 star share (single-item, on-time orders)"]


def format_categories(result) -> list:
    return [(r[0], n(r[1]), pct(r[2]), n(r[3]), pct(r[4]), pct(r[5]), pct(r[6])) for r in result]


table("B2. The 15 largest categories by GMV", CATEGORY_HEADERS,
      format_categories(rows("SELECT * FROM category_stats ORDER BY gmv DESC LIMIT 15")))
table("B3. The 10 categories with the highest 1-2 star share (at least 500 orders)", CATEGORY_HEADERS,
      format_categories(rows("SELECT * FROM category_stats WHERE orders >= 500 ORDER BY low_share DESC LIMIT 10")))
category_count = scalar("SELECT count(*) FROM category_stats")
category_500 = scalar("SELECT count(*) FROM category_stats WHERE orders >= 500")
clean_range = rows(
    "SELECT min(low_share_clean), median(low_share_clean), max(low_share_clean) FROM category_stats WHERE orders >= 500"
)[0]
report += [
    f"{category_count} categories in total, {category_500} with at least 500 orders. Among these, the 1-2 star "
    f"share of single-item on-time orders ranges from {pct(clean_range[0])} to {pct(clean_range[2])} "
    f"(median {pct(clean_range[1])}).",
    "",
]

# %%
# Chart 4 - order composition (on-time orders only, so that delivery is held constant)
fig, ax = new_figure(
    f"Even when delivered on time, orders with several items get {b1[1][9] / b1[0][9]:.0f}-{b1[3][9] / b1[0][9]:.0f}x "
    "more bad reviews than single-item orders",
    "Share of 1-2 star reviews among on-time orders, by what the order contains",
    height=4.2,
)
ax.barh(range(len(b1)), [r[9] for r in b1], height=0.42, color=[BLUE] + [ORANGE] * (len(b1) - 1))
for i, r in enumerate(b1):
    ax.text(r[9] + 0.008, i, f"{r[9]:.0%}   ({r[7]:,} orders)", va="center", fontsize=9.5, color=INK)
ax.set_yticks(range(len(b1)), [r[0] for r in b1])
ax.invert_yaxis()
ax.set_xlim(0, 0.65)
percent_axis(ax, "x")
fig.subplots_adjust(left=0.30)
save(fig, "04_bad_reviews_by_order_composition.png", "On-time orders only.")

# Chart 5 - category matrix: sales volume vs bad review share
cats = rows(
    """
    SELECT category_en, gmv, low_share, gmv_share FROM category_stats
    WHERE orders >= 500 AND category_en <> 'unknown'   -- "unknown" is a missing label, not a category
    ORDER BY gmv DESC
    """
)
flagged = [c for c in cats if c[3] >= 0.03 and c[2] > OVERALL_LOW_SHARE]   # large AND worse than average
worst_cat = max(cats, key=lambda c: c[2])
fig, ax = new_figure(
    f"{len(flagged)} large categories combine high sales with above-average bad reviews; "
    f"{worst_cat[0].replace('_', ' ')} has the highest share ({worst_cat[2]:.0%})",
    f"Categories with at least 500 orders: GMV vs share of 1-2 star reviews. Highlighted: at least 3% of GMV "
    f"and above the overall share of {OVERALL_LOW_SHARE:.1%}",
    height=5.6,
)
for name, gmv, low, share in cats:
    highlight = (name, gmv, low, share) in flagged or name == worst_cat[0]
    ax.plot(float(gmv) / 1000, low, "o", markersize=9, color=ORANGE if highlight else GREY,
            markeredgecolor=SURFACE, markeredgewidth=2)
    if highlight:
        # labels sit above-right of the dot, except where that would collide with a neighbour
        offset = {"computers_accessories": (0, -16), "watches_gifts": (-8, 8)}.get(name, (8, 4))
        ax.annotate(name.replace("_", " "), (float(gmv) / 1000, low), textcoords="offset points",
                    xytext=offset, ha="center" if offset[0] == 0 else ("right" if offset[0] < 0 else "left"),
                    fontsize=9, color=INK)
ax.axhline(OVERALL_LOW_SHARE, color=AXIS, linewidth=1)
ax.text(ax.get_xlim()[0] + 8, OVERALL_LOW_SHARE + 0.002, f"overall {OVERALL_LOW_SHARE:.1%}", ha="left", fontsize=8.5, color=MUTED)
percent_axis(ax)
ax.grid(axis="x", color=GRID, linewidth=0.8)
ax.set_xlabel("GMV, thousand BRL")
ax.set_ylabel("Share of 1-2 star reviews")
ax.xaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
save(fig, "05_category_matrix.png", f"{len(cats)} categories shown; products without a category excluded.")


# %% [markdown]
# ## C. Seller branch
# Hypothesis: a small group of bad sellers causes most of the problem.

# %%
section(
    "C. Sellers",
    "An order with items from two sellers counts once for each seller, so seller-level order totals are "
    "slightly higher than the number of orders.",
)

con.execute(
    """
    CREATE OR REPLACE TEMP VIEW seller_stats AS
    SELECT seller_id,
           count(DISTINCT order_id)                                               AS orders,
           count(DISTINCT order_id) FILTER (WHERE is_delivered)                   AS delivered,
           count(DISTINCT order_id) FILTER (WHERE delivery_outcome = 'Late')      AS late,
           count(DISTINCT order_id) FILTER (WHERE has_review)                     AS reviewed,
           count(DISTINCT order_id) FILTER (WHERE is_low_score)                   AS low
    FROM model.fact_order_items
    GROUP BY seller_id
    """
)
c1 = rows(
    """
    SELECT count(*), median(orders), sum(orders), sum(late), sum(low),
           count(*) FILTER (WHERE orders >= 30),
           sum(orders) FILTER (WHERE orders >= 30) / sum(orders),
           sum(late)   FILTER (WHERE orders >= 30) / sum(late),
           sum(low)    FILTER (WHERE orders >= 30) / sum(low)
    FROM seller_stats
    """
)[0]
table(
    "C1. Seller base",
    ["figure", "value"],
    [
        ("Sellers with at least one order in the period", n(c1[0])),
        ("Median number of orders per seller", n(c1[1])),
        ("Sellers with at least 30 orders", n(c1[5])),
        ("Their share of all seller-orders", pct(c1[6])),
        ("Their share of all late seller-orders", pct(c1[7])),
        ("Their share of all 1-2 star seller-orders", pct(c1[8])),
    ],
)

# C2 - is the problem simply where the volume is? Top 10% of sellers by number of orders.
c2 = rows(
    """
    WITH ranked AS (SELECT *, ntile(10) OVER (ORDER BY orders DESC, seller_id) AS decile FROM seller_stats)
    SELECT decile, count(*), sum(orders),
           sum(orders) / (SELECT sum(orders) FROM seller_stats),
           sum(late)   / (SELECT sum(late)   FROM seller_stats),
           sum(low)    / (SELECT sum(low)    FROM seller_stats)
    FROM ranked GROUP BY decile ORDER BY decile
    """
)
table(
    "C2. Sellers ranked by number of orders (decile 1 = the largest 10% of sellers)",
    ["decile", "sellers", "orders", "share of orders", "share of late orders", "share of 1-2 star orders"],
    [(r[0], n(r[1]), n(r[2]), pct(r[3]), pct(r[4]), pct(r[5])) for r in c2],
)

# C3 / C4 - the worst performers. Only sellers with at least 30 orders: a rate on 3 orders is noise.
c3 = rows(
    """
    WITH ranked AS (
        SELECT *, ntile(10) OVER (ORDER BY late / delivered DESC, seller_id) AS decile
        FROM seller_stats WHERE orders >= 30)
    SELECT decile, count(*), sum(orders),
           sum(orders) / (SELECT sum(orders) FROM seller_stats WHERE orders >= 30),
           sum(late),
           sum(late)   / (SELECT sum(late)   FROM seller_stats WHERE orders >= 30),
           sum(late) / sum(delivered)
    FROM ranked GROUP BY decile ORDER BY decile
    """
)
table(
    "C3. Sellers with at least 30 orders, ranked by late rate (decile 1 = the worst 10%)",
    ["decile", "sellers", "orders", "share of orders", "late orders", "share of late orders", "late rate"],
    [(r[0], n(r[1]), n(r[2]), pct(r[3]), n(r[4]), pct(r[5]), pct(r[6])) for r in c3],
)
c4 = rows(
    """
    WITH ranked AS (
        SELECT *, ntile(10) OVER (ORDER BY low / reviewed DESC, seller_id) AS decile
        FROM seller_stats WHERE orders >= 30)
    SELECT decile, count(*), sum(orders),
           sum(orders) / (SELECT sum(orders) FROM seller_stats WHERE orders >= 30),
           sum(low),
           sum(low)    / (SELECT sum(low)    FROM seller_stats WHERE orders >= 30),
           sum(low) / sum(reviewed),
           sum(late) / sum(delivered)
    FROM ranked GROUP BY decile ORDER BY decile
    """
)
table(
    "C4. Sellers with at least 30 orders, ranked by 1-2 star share (decile 1 = the worst 10%)",
    ["decile", "sellers", "orders", "share of orders", "1-2 star orders", "share of 1-2 star orders",
     "1-2 star share", "late rate"],
    [(r[0], n(r[1]), n(r[2]), pct(r[3]), n(r[4]), pct(r[5]), pct(r[6]), pct(r[7])) for r in c4],
)

# C5 - who owns the delay: the seller (late handover to the carrier) or the carrier (transit)?
c5 = rows(
    """
    SELECT CASE WHEN is_seller_handover_late THEN 'seller handed over AFTER the shipping deadline'
                ELSE 'seller handed over in time' END AS handover,
           count(*), count(*) FILTER (WHERE delivery_outcome = 'Late'),
           count(*) FILTER (WHERE delivery_outcome = 'Late') / count(*),
           count(*) FILTER (WHERE delivery_outcome = 'Late')
               / (SELECT count(*) FROM model.fact_orders WHERE delivery_outcome = 'Late' AND is_seller_handover_late IS NOT NULL),
           count(*) FILTER (WHERE is_low_score) / count(*) FILTER (WHERE has_review)
    FROM model.fact_orders
    WHERE is_delivered AND is_seller_handover_late IS NOT NULL
    GROUP BY handover ORDER BY handover DESC
    """
)
table(
    "C5. Delivered orders: did the seller hand the parcel to the carrier in time?",
    ["seller handover", "delivered orders", "late orders", "late rate", "share of all late orders", "1-2 star share"],
    [(r[0], n(r[1]), n(r[2]), pct(r[3]), pct(r[4]), pct(r[5])) for r in c5],
)

# %%
# Chart 6 - seller concentration
fig, ax = new_figure(
    f"Late deliveries are spread across sellers: the worst 10% of sellers account for only {c3[0][5]:.0%} of late orders",
    "Sellers with at least 30 orders, in ten equal groups ranked by late rate (1 = worst)",
)
x = range(len(c3))
ax.bar([i - 0.19 for i in x], [r[3] for r in c3], width=0.34, color=BLUE, label="Share of orders")
ax.bar([i + 0.19 for i in x], [r[5] for r in c3], width=0.34, color=ORANGE, label="Share of late orders")
ax.text(0 + 0.19, c3[0][5] + 0.006, f"{c3[0][5]:.0%}", ha="center", fontsize=9.5, color=INK)
ax.text(0 - 0.19, c3[0][3] + 0.006, f"{c3[0][3]:.0%}", ha="center", fontsize=9.5, color=INK)
ax.set_xticks(list(x), [str(r[0]) for r in c3])
ax.set_xlabel("Seller group, ranked by late rate (1 = worst 10%, 10 = best 10%)")
percent_axis(ax)
ax.legend(loc="upper right", frameon=False)
save(fig, "06_seller_concentration.png", f"{n(c1[5])} sellers with 30+ orders, {pct(c1[6])} of all seller-orders.")


# %% [markdown]
# ## D. Geography branch
# Hypothesis: the problem is concentrated in certain states and grows with distance.

# %%
section("D. Geography")

d1 = rows(
    f"""
    SELECT g.region, {ORDER_MEASURES}, median(delivery_days)
    FROM model.fact_orders f
    JOIN model.dim_geography g ON g.state_code = f.customer_state
    GROUP BY g.region ORDER BY orders DESC
    """
)
table(
    "D1. By customer region",
    ["region", "orders", "median delivery days", "late rate", "avg score", "1-2 star share"],
    [(r[0], n(r[1]), n(r[7]), pct(r[2]), dec(r[4]), pct(r[6])) for r in d1],
)

# D2 - by customer state, with "excess late orders": how many late orders the state has beyond what it
# would have at the national late rate. This is the size of the prize if the state reached the average.
d2 = rows(
    f"""
    SELECT f.customer_state, g.state_name, count(*) AS orders,
           count(*) / {TOTAL_ORDERS}                                            AS share_of_orders,
           median(f.delivery_days)                                              AS median_days,
           count(*) FILTER (WHERE f.is_delivered)                               AS delivered,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late')                  AS late,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late') / count(*) FILTER (WHERE f.is_delivered) AS late_rate,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late')
               / (SELECT count(*) FROM model.fact_orders WHERE delivery_outcome = 'Late') AS share_of_late,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late')
               - count(*) FILTER (WHERE f.is_delivered) * {OVERALL_LATE_RATE}   AS excess_late,
           count(*) FILTER (WHERE f.is_low_score) / count(*) FILTER (WHERE f.has_review) AS low_share
    FROM model.fact_orders f
    JOIN model.dim_geography g ON g.state_code = f.customer_state
    GROUP BY f.customer_state, g.state_name
    ORDER BY late_rate DESC
    """
)
table(
    "D2. By customer state, ranked by late rate",
    ["state", "name", "orders", "share of orders", "median delivery days", "late orders", "late rate",
     "share of all late orders", "late orders above national rate", "1-2 star share"],
    [(r[0], r[1], n(r[2]), pct(r[3]), n(r[4]), n(r[6]), pct(r[7]), pct(r[8]), n(r[9]), pct(r[10])) for r in d2],
)

d3 = rows(
    """
    SELECT s.seller_state, count(DISTINCT i.order_id) AS orders,
           count(DISTINCT i.order_id) FILTER (WHERE i.delivery_outcome = 'Late')
               / count(DISTINCT i.order_id) FILTER (WHERE i.is_delivered),
           count(DISTINCT i.order_id) FILTER (WHERE i.is_low_score)
               / count(DISTINCT i.order_id) FILTER (WHERE i.has_review)
    FROM model.fact_order_items i
    JOIN model.dim_seller s USING (seller_id)
    GROUP BY s.seller_state
    HAVING count(DISTINCT i.order_id) >= 300
    ORDER BY orders DESC
    """
)
table(
    "D3. By seller state (states with at least 300 orders)",
    ["seller state", "orders", "late rate", "1-2 star share"],
    [(r[0], n(r[1]), pct(r[2]), pct(r[3])) for r in d3],
)

d4 = rows(
    f"""
    SELECT CASE WHEN is_same_state THEN 'seller and customer in the same state'
                ELSE 'seller and customer in different states' END AS shipment,
           {ORDER_MEASURES}, median(delivery_days)
    FROM model.fact_orders
    WHERE has_items
    GROUP BY shipment ORDER BY shipment DESC
    """
)
table(
    "D4. Distance proxy: same-state vs cross-state shipments",
    ["shipment", "orders", "median delivery days", "late rate", "avg score", "1-2 star share"],
    [(r[0], n(r[1]), n(r[7]), pct(r[2]), dec(r[4]), pct(r[6])) for r in d4],
)

# %%
# Chart 7 - late rate and number of late orders by state (states with at least 300 orders)
states = sorted([r for r in d2 if r[2] >= 300], key=lambda r: r[7])
top_excess = max(d2, key=lambda r: r[9])
fig, (ax_rate, ax_count) = new_figure(
    f"{top_excess[1]} is where the problem is biggest: {top_excess[3]:.0%} of orders but "
    f"{top_excess[8]:.0%} of all late deliveries",
    f"Customer states with at least 300 orders. Vertical line: national late rate of {OVERALL_LATE_RATE:.1%}",
    height=7, ncols=2,
)
names = [r[1] for r in states]
colours = [ORANGE if r[0] == top_excess[0] else GREY for r in states]
ax_rate.barh(names, [r[7] for r in states], height=0.55, color=colours)
for i, r in enumerate(states):
    ax_rate.text(r[7] + 0.004, i, f"{r[7]:.1%}", va="center", fontsize=8.5, color=INK, zorder=3,
                 bbox={"facecolor": SURFACE, "edgecolor": "none", "pad": 1})
ax_rate.axvline(OVERALL_LATE_RATE, color=INK_2, linewidth=1, zorder=1)
ax_rate.set_xlim(0, 0.27)
ax_rate.set_title("Late rate", loc="left", fontsize=10, color=INK_2)
percent_axis(ax_rate, "x")
ax_count.barh(names, [r[6] for r in states], height=0.55, color=colours)
for i, r in enumerate(states):
    ax_count.text(r[6] + 25, i, f"{r[6]:,}", va="center", fontsize=8.5, color=INK)
ax_count.set_xlim(0, 2200)
ax_count.set_title("Number of late orders", loc="left", fontsize=10, color=INK_2)
ax_count.grid(axis="x", color=GRID, linewidth=0.8)
ax_count.xaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
fig.subplots_adjust(left=0.19, wspace=0.12)
save(fig, "07_late_deliveries_by_state.png", f"{len(states)} of 27 states shown.")


# %% [markdown]
# ## E. Price branch
# Hypotheses: expensive orders and orders with a high freight cost get worse reviews.

# %%
section("E. Price and freight")

VALUE_BAND = """CASE WHEN items_value < 50  THEN 'under 50 BRL'
                     WHEN items_value < 100 THEN '50-100 BRL'
                     WHEN items_value < 200 THEN '100-200 BRL'
                     WHEN items_value < 500 THEN '200-500 BRL'
                     ELSE '500+ BRL' END"""
e1_all = orders_by(VALUE_BAND, where="has_items", order_by="min(items_value)")
e1_clean = orders_by(VALUE_BAND, where="delivery_outcome = 'On time' AND item_count = 1", order_by="min(items_value)")
table(
    "E1. By order value",
    ["order value", "orders", "late rate", "1-2 star share (all orders)",
     "orders (single-item, on-time)", "1-2 star share (single-item, on-time)"],
    [(a[0], n(a[1]), pct(a[2]), pct(a[6]), n(c[1]), pct(c[6])) for a, c in zip(e1_all, e1_clean)],
)

FREIGHT_BAND = """CASE WHEN freight_value / items_value < 0.10 THEN 'freight under 10% of price'
                       WHEN freight_value / items_value < 0.20 THEN 'freight 10-20% of price'
                       WHEN freight_value / items_value < 0.40 THEN 'freight 20-40% of price'
                       ELSE 'freight 40%+ of price' END"""
e2_all = orders_by(FREIGHT_BAND, where="has_items", order_by="min(freight_value / items_value)")
e2_clean = orders_by(FREIGHT_BAND, where="delivery_outcome = 'On time' AND item_count = 1",
                     order_by="min(freight_value / items_value)")
table(
    "E2. By freight cost relative to the price of the items (per-order ratio)",
    ["freight vs price", "orders", "late rate", "1-2 star share (all orders)",
     "orders (single-item, on-time)", "1-2 star share (single-item, on-time)"],
    [(a[0], n(a[1]), pct(a[2]), pct(a[6]), n(c[1]), pct(c[6])) for a, c in zip(e2_all, e2_clean)],
)


# %% [markdown]
# ## F. Consequence: do customers with a bad first experience come back?
# Small numbers: the result is reported with a 95% confidence interval.

# %%
section(
    "F. Repeat purchase by first-order experience",
    "Repeat customer = orders on more than one calendar day. The confidence interval (Wilson, 95%) shows "
    "how uncertain each rate is given the number of customers.",
)


def wilson(successes: int, total: int) -> tuple:
    """95% Wilson confidence interval for a proportion."""
    if total == 0:
        return (None, None)
    z = 1.96
    p = successes / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return (centre - half, centre + half)


def repeat_table(group_sql: str, where: str = "TRUE") -> list:
    """Repeat purchase rate of customers, grouped by a property of their FIRST order."""
    result = rows(
        f"""
        SELECT {group_sql} AS grp, count(*) AS customers, count(*) FILTER (WHERE c.is_repeat_customer) AS repeat
        FROM model.fact_orders f
        JOIN model.dim_customer c USING (customer_unique_id)
        WHERE f.customer_order_number = 1 AND {where}
        GROUP BY grp ORDER BY customers DESC
        """
    )
    return [(g, customers, repeat, repeat / customers, *wilson(repeat, customers)) for g, customers, repeat in result]


REPEAT_HEADERS = ["first order", "customers", "repeat customers", "repeat purchase rate", "95% CI low", "95% CI high"]


def format_repeat(result) -> list:
    return [(r[0], n(r[1]), n(r[2]), f"{r[3]:.2%}", f"{r[4]:.2%}", f"{r[5]:.2%}") for r in result]


f1 = repeat_table("f.delivery_outcome", where="f.delivery_outcome <> 'Unknown'")
table("F1. By delivery outcome of the first order", REPEAT_HEADERS, format_repeat(f1))
f2 = repeat_table("f.delivery_outcome", where="f.delivery_outcome <> 'Unknown' AND f.purchase_date < DATE '2018-01-01'")
table("F2. Same, only customers whose first order was in 2017 (at least 8 months to come back)",
      REPEAT_HEADERS, format_repeat(f2))
f3 = repeat_table(
    "CASE WHEN f.review_score <= 2 THEN '1-2 stars' WHEN f.review_score = 3 THEN '3 stars' ELSE '4-5 stars' END",
    where="f.has_review",
)
table("F3. By review score of the first order", REPEAT_HEADERS, format_repeat(f3))

# %%
# Chart 8 - repeat purchase rate with confidence intervals
order = ["On time", "Late", "Not delivered"]
f1_sorted = sorted(f1, key=lambda r: order.index(r[0]))
late_row = next(r for r in f1_sorted if r[0] == "Late")
on_time_row = next(r for r in f1_sorted if r[0] == "On time")
fig, ax = new_figure(
    f"Customers whose first order was late come back less often ({late_row[3]:.1%} vs {on_time_row[3]:.1%}), "
    f"but the evidence rests on only {late_row[2]} returning customers",
    "Repeat purchase rate by delivery outcome of the first order, with 95% confidence intervals",
    height=4.4,
)
xs = range(len(f1_sorted))
rates = [r[3] for r in f1_sorted]
ax.bar(xs, rates, width=0.36, color=[BLUE, ORANGE, GREY])
ax.errorbar(xs, rates, yerr=[[r[3] - r[4] for r in f1_sorted], [r[5] - r[3] for r in f1_sorted]],
            fmt="none", ecolor=INK_2, elinewidth=1.2, capsize=4)
for x, r in zip(xs, f1_sorted):
    ax.text(x + 0.22, r[3], f"{r[3]:.1%}\n{r[2]:,} of {r[1]:,}", va="center", fontsize=9, color=INK)
ax.set_xticks(list(xs), [r[0] for r in f1_sorted])
ax.set_xlim(-0.5, 2.9)
ax.set_ylim(0, 0.04)
ax.set_yticks([0, 0.01, 0.02, 0.03, 0.04])
percent_axis(ax)
save(fig, "08_repeat_rate_by_first_order.png", "Repeat = orders on more than one day.")


# %% [markdown]
# ## G. Robustness: is the "late" effect just something else in disguise?
# If late orders only looked bad because they are, for example, mostly from one region or mostly large
# orders, the gap would shrink inside each group. This table checks that.

# %%
section(
    "G. Robustness check: late vs on-time inside comparable groups",
    "Share of 1-2 star reviews for on-time and late orders within each group. A gap that stays the same in "
    "every group means the groups do not explain it. It does not prove causation: only factors that are in "
    "the data can be checked.",
)


def gap_table(group_sql: str, join: str = "", order_by: str = "1") -> list:
    result = rows(
        f"""
        SELECT {group_sql} AS grp,
               count(*) FILTER (WHERE f.delivery_outcome = 'On time' AND f.has_review)                    AS on_time_n,
               count(*) FILTER (WHERE f.delivery_outcome = 'On time' AND f.is_low_score)
                   / count(*) FILTER (WHERE f.delivery_outcome = 'On time' AND f.has_review)              AS on_time_low,
               count(*) FILTER (WHERE f.delivery_outcome = 'Late' AND f.has_review)                       AS late_n,
               count(*) FILTER (WHERE f.delivery_outcome = 'Late' AND f.is_low_score)
                   / count(*) FILTER (WHERE f.delivery_outcome = 'Late' AND f.has_review)                 AS late_low
        FROM model.fact_orders f {join}
        WHERE f.is_delivered AND f.has_items
        GROUP BY grp ORDER BY {order_by}
        """
    )
    return [(r[0], n(r[1]), pct(r[2]), n(r[3]), pct(r[4]), f"{(r[4] - r[2]) * 100:.1f} pp") for r in result]


GAP_HEADERS = ["group", "on-time reviewed orders", "1-2 star share (on time)", "late reviewed orders",
               "1-2 star share (late)", "gap"]
table("G1. Within customer region", GAP_HEADERS,
      gap_table("g.region", join="JOIN model.dim_geography g ON g.state_code = f.customer_state"))
table("G2. Within order size", GAP_HEADERS,
      gap_table("CASE WHEN f.item_count = 1 THEN '1 item' ELSE '2+ items' END"))
table("G3. Within order value", GAP_HEADERS,
      gap_table(VALUE_BAND.replace("items_value", "f.items_value"), order_by="min(f.items_value)"))
table("G4. Within purchase year", GAP_HEADERS, gap_table("year(f.purchase_date)::VARCHAR"))


# %%
REPORT_PATH.write_text("\n".join(report), encoding="utf-8")
con.close()
print(f"\nReport written to {REPORT_PATH.relative_to(ROOT)}")
