# %% [markdown]
# # 09 - Numbers for the deck (Phase 8)
#
# Goal: compute every figure that appears on a slide in one place, so that the deck contains no
# hand-typed number. The deck builder (deck/build_deck.js) reads the JSON written here.
#
# Input : data/processed/olist.duckdb, review_coding/coded_reviews.csv
# Output: deck/deck_data.json (generated - do not edit by hand)
#
# The definitions are the same as in sql/05_kpis.sql, notebooks/04, 06 and 07; the values must equal
# those in docs/kpi_baseline.md, docs/analysis_results.md, review_coding/results.md and
# docs/scenario_results.md.

# %%
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

import duckdb

sys.stdout.reconfigure(encoding="utf-8")

try:
    ROOT = Path(__file__).resolve().parents[1]
except NameError:
    ROOT = Path.cwd() if (Path.cwd() / "sql").exists() else Path.cwd().parent

con = duckdb.connect(str(ROOT / "data" / "processed" / "olist.duckdb"), read_only=True)
OUT = ROOT / "deck" / "deck_data.json"


def row(sql: str) -> dict:
    cur = con.execute(sql)
    return dict(zip([c[0] for c in cur.description], cur.fetchone()))


def rows(sql: str) -> list:
    cur = con.execute(sql)
    names = [c[0] for c in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def num(d):
    """Make DuckDB values JSON-friendly (Decimal -> float)."""
    if isinstance(d, dict):
        return {k: num(v) for k, v in d.items()}
    if isinstance(d, list):
        return [num(v) for v in d]
    if hasattr(d, "__float__") and not isinstance(d, (int, float, bool)):
        return float(d)
    return d


def wilson(successes: int, total: int) -> list:
    z = 1.96
    p = successes / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return [centre - half, centre + half]


data = {}

# %% [markdown]
# ## Baseline KPIs

# %%
k = row("SELECT * FROM model.kpi_orders WHERE period = 'Total'")
data["baseline"] = {key: k[key] for key in [
    "orders", "gmv", "on_time_rate", "late_rate", "not_delivered_rate", "avg_review_score", "low_score_rate",
    "low_score_orders", "reviewed_orders", "delivered_orders", "late_orders", "not_delivered_orders",
    "median_delivery_days"]}

# %% [markdown]
# ## Finding 1: delivery outcome and bad reviews

# %%
data["delay_bands"] = rows(
    """
    SELECT delay_band, count(*) AS orders,
           count(*) FILTER (WHERE is_low_score) / count(*) FILTER (WHERE has_review) AS low_share
    FROM model.fact_orders WHERE delay_band <> 'Unknown'
    GROUP BY delay_band, delay_band_sort ORDER BY delay_band_sort
    """
)
data["outcomes"] = rows(
    """
    SELECT delivery_outcome, count(*) AS orders,
           count(*) / sum(count(*)) OVER () AS share_of_orders,
           count(*) FILTER (WHERE is_low_score) AS low_orders,
           count(*) FILTER (WHERE is_low_score) / sum(count(*) FILTER (WHERE is_low_score)) OVER () AS share_of_low,
           count(*) FILTER (WHERE is_low_score) / count(*) FILTER (WHERE has_review) AS low_share
    FROM model.fact_orders WHERE delivery_outcome <> 'Unknown'
    GROUP BY delivery_outcome, delivery_outcome_sort ORDER BY delivery_outcome_sort
    """
)
problem = [o for o in data["outcomes"] if o["delivery_outcome"] in ("Late", "Not delivered")]
data["problem_share_of_orders"] = sum(o["share_of_orders"] for o in problem)
data["problem_share_of_low"] = sum(o["share_of_low"] for o in problem)
gaps = rows(
    """
    SELECT g.region,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late' AND f.is_low_score)
               / count(*) FILTER (WHERE f.delivery_outcome = 'Late' AND f.has_review)
         - count(*) FILTER (WHERE f.delivery_outcome = 'On time' AND f.is_low_score)
               / count(*) FILTER (WHERE f.delivery_outcome = 'On time' AND f.has_review) AS gap
    FROM model.fact_orders f JOIN model.dim_geography g ON g.state_code = f.customer_state
    GROUP BY g.region
    """
)
data["gap_by_region_min"] = min(g["gap"] for g in gaps)
data["gap_by_region_max"] = max(g["gap"] for g in gaps)
data["monthly_correlation"] = row(
    "SELECT corr(late_rate, low_score_rate) AS c FROM model.kpi_orders WHERE period <> 'Total'")["c"]
data["worst_months"] = rows(
    """SELECT period, late_rate, low_score_rate FROM model.kpi_orders WHERE period <> 'Total'
       ORDER BY late_rate DESC LIMIT 3"""
)

# %% [markdown]
# ## Finding 2: where the delivery problem sits

# %%
national = data["baseline"]["late_rate"]
data["states"] = rows(
    f"""
    SELECT g.state_name, f.customer_state AS state, count(*) AS orders,
           count(*) / (SELECT count(*) FROM model.fact_orders) AS share_of_orders,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late') AS late_orders,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late') / count(*) FILTER (WHERE f.is_delivered) AS late_rate,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late')
               / (SELECT count(*) FROM model.fact_orders WHERE delivery_outcome = 'Late') AS share_of_late,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late')
               - count(*) FILTER (WHERE f.is_delivered) * {national} AS excess_late
    FROM model.fact_orders f JOIN model.dim_geography g ON g.state_code = f.customer_state
    GROUP BY g.state_name, f.customer_state
    HAVING count(*) >= 300
    ORDER BY late_rate DESC
    """
)
data["transit"] = rows(
    """
    SELECT delivery_outcome, median(transit_days) AS median_transit_days, median(handling_days) AS median_handling_days,
           median(promised_days) AS median_promised_days,
           count(*) FILTER (WHERE is_seller_handover_late) / count(is_seller_handover_late) AS handed_over_late_share
    FROM model.fact_orders WHERE is_delivered GROUP BY delivery_outcome ORDER BY delivery_outcome DESC
    """
)
data["worst_sellers"] = row(
    """
    WITH s AS (
        SELECT seller_id, count(DISTINCT order_id) AS orders,
               count(DISTINCT order_id) FILTER (WHERE is_delivered) AS delivered,
               count(DISTINCT order_id) FILTER (WHERE delivery_outcome = 'Late') AS late
        FROM model.fact_order_items GROUP BY seller_id HAVING count(DISTINCT order_id) >= 30),
    r AS (SELECT *, ntile(10) OVER (ORDER BY late / delivered DESC, seller_id) AS decile FROM s)
    SELECT count(*) FILTER (WHERE decile = 1) AS sellers,
           sum(orders) FILTER (WHERE decile = 1) / sum(orders) AS share_of_orders,
           sum(late) FILTER (WHERE decile = 1) / sum(late) AS share_of_late
    FROM r
    """
)
data["same_state"] = rows(
    """
    SELECT is_same_state, median(delivery_days) AS median_delivery_days,
           count(*) FILTER (WHERE delivery_outcome = 'Late') / count(*) FILTER (WHERE is_delivered) AS late_rate
    FROM model.fact_orders WHERE has_items GROUP BY is_same_state ORDER BY is_same_state DESC
    """
)

# %% [markdown]
# ## Finding 3: what customers complain about (review coding)

# %%
with open(ROOT / "review_coding" / "coded_reviews.csv", encoding="utf-8-sig") as handle:
    coded = list(csv.DictReader(handle))
FAMILY = {
    "Not received": "Not received or late", "Late delivery": "Not received or late",
    "Incomplete order": "Part of the order missing",
    "Wrong item": "Wrong, damaged or poor product", "Damaged or defective": "Wrong, damaged or poor product",
    "Poor quality or not as described": "Wrong, damaged or poor product",
    "Seller service and refunds": "Service or unclear", "Other or unclear": "Service or unclear",
}
FAMILIES = ["Not received or late", "Part of the order missing", "Wrong, damaged or poor product", "Service or unclear"]
GROUPS = ["Late", "Not delivered", "On time, several items", "On time, single item"]
coding = {"families": FAMILIES, "groups": []}
for g in GROUPS:
    members = [r for r in coded if r["delivery_group"] == g]
    counts = Counter(FAMILY[r["primary_category"]] for r in members)
    coding["groups"].append({
        "group": g, "reviews": len(members),
        "shares": [counts[f] / len(members) for f in FAMILIES],
        "counts": [counts[f] for f in FAMILIES],
    })


def key_share(group: str, categories: set) -> dict:
    members = [r for r in coded if r["delivery_group"] == group]
    hits = sum(r["primary_category"] in categories for r in members)
    return {"hits": hits, "total": len(members), "share": hits / len(members), "ci": wilson(hits, len(members))}


coding["late_not_received"] = key_share("Late", {"Not received"})
coding["not_delivered_not_received"] = key_share("Not delivered", {"Not received"})
coding["several_incomplete"] = key_share("On time, several items", {"Incomplete order"})
coding["single_product"] = key_share("On time, single item",
                                     {"Incomplete order", "Wrong item", "Damaged or defective",
                                      "Poor quality or not as described"})
coding["sample_size"] = len(coded)
coding["frame_size"] = row(
    """
    SELECT count(DISTINCT r.review_id) AS n FROM stg.reviews r JOIN model.fact_orders f USING (order_id)
    WHERE r.review_score <= 2 AND r.review_comment_message IS NOT NULL AND f.delivery_outcome <> 'Unknown'
    """
)["n"]
mentioned_service = sum("Seller service and refunds" in (r["primary_category"], r["secondary_category"]) for r in coded)
coding["service_mentioned_share"] = mentioned_service / len(coded)
data["coding"] = coding
data["order_size"] = rows(
    """
    SELECT order_size, count(*) AS orders, count(*) FILTER (WHERE is_low_score) AS low_orders,
           count(*) FILTER (WHERE is_low_score) / count(*) FILTER (WHERE has_review) AS low_share
    FROM model.fact_orders WHERE delivery_outcome = 'On time' GROUP BY order_size ORDER BY order_size
    """
)

# %% [markdown]
# ## Scenario (same method and assumptions as notebooks/07_scenario.py)

# %%
CASES = {"low": 0.50, "base": 0.75, "high": 1.00}
N_STATES = 5
b = data["baseline"]
state_rows = rows(
    f"""
    SELECT f.customer_state AS state,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late')
               - count(*) FILTER (WHERE f.is_delivered) * {national} AS excess_late,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late') AS late,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late' AND f.has_review) AS late_reviewed,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late' AND f.is_low_score) AS late_low,
           count(*) FILTER (WHERE f.delivery_outcome = 'On time' AND f.has_review) AS on_reviewed,
           count(*) FILTER (WHERE f.delivery_outcome = 'On time' AND f.is_low_score) AS on_low
    FROM model.fact_orders f GROUP BY f.customer_state ORDER BY excess_late DESC
    """
)
target = state_rows[:N_STATES]
total = {key: sum(float(s[key]) for s in target) for key in ["excess_late", "late", "late_reviewed", "late_low", "on_reviewed", "on_low"]}
a_moved = total["excess_late"] * total["late_reviewed"] / total["late"]
a_gap = total["late_low"] / total["late_reviewed"] - total["on_low"] / total["on_reviewed"]
multi = row(
    """
    SELECT count(*) FILTER (WHERE item_count >= 2 AND has_review) AS multi_reviewed,
           count(*) FILTER (WHERE item_count >= 2 AND is_low_score) AS multi_low,
           count(*) FILTER (WHERE item_count = 1 AND has_review) AS single_reviewed,
           count(*) FILTER (WHERE item_count = 1 AND is_low_score) AS single_low
    FROM model.fact_orders WHERE delivery_outcome = 'On time'
    """
)
b_gap = multi["multi_low"] / multi["multi_reviewed"] - multi["single_low"] / multi["single_reviewed"]
scenario = {"cases": CASES, "target_states": [s["state"] for s in target], "orders_moved_a": total["excess_late"],
            "reviews_moved_b": multi["multi_reviewed"], "a": {}, "b": {}, "ab": {}}
for case, factor in CASES.items():
    a = a_moved * a_gap * factor
    bb = multi["multi_reviewed"] * b_gap * factor
    for name, avoided in (("a", a), ("b", bb), ("ab", a + bb)):
        scenario[name][case] = {
            "avoided": avoided,
            "share_of_all_bad": avoided / b["low_score_orders"],
            "new_low_share": (b["low_score_orders"] - avoided) / b["reviewed_orders"],
        }
late_all = row(
    """
    SELECT count(*) FILTER (WHERE delivery_outcome = 'Late' AND has_review) AS late_reviewed,
           count(*) FILTER (WHERE delivery_outcome = 'Late' AND is_low_score) AS late_low,
           count(*) FILTER (WHERE delivery_outcome = 'On time' AND has_review) AS on_reviewed,
           count(*) FILTER (WHERE delivery_outcome = 'On time' AND is_low_score) AS on_low
    FROM model.fact_orders
    """
)
ceiling = late_all["late_reviewed"] * (late_all["late_low"] / late_all["late_reviewed"] - late_all["on_low"] / late_all["on_reviewed"])
scenario["ceiling_avoided"] = ceiling
scenario["ceiling_share_of_all_bad"] = ceiling / b["low_score_orders"]
data["scenario"] = scenario

# %% [markdown]
# ## Not-delivered orders (the third lever, outside the scenario)

# %%
data["not_delivered_by_status"] = rows(
    """
    SELECT order_status, count(*) AS orders, count(*) FILTER (WHERE is_low_score) AS low_orders
    FROM model.fact_orders WHERE delivery_outcome = 'Not delivered' GROUP BY order_status ORDER BY orders DESC
    """
)
data["repeat"] = rows(
    """
    SELECT f.delivery_outcome, count(*) AS customers, count(*) FILTER (WHERE c.is_repeat_customer) AS repeat_customers
    FROM model.fact_orders f JOIN model.dim_customer c USING (customer_unique_id)
    WHERE f.customer_order_number = 1 AND f.delivery_outcome IN ('On time', 'Late')
    GROUP BY f.delivery_outcome
    ORDER BY min(f.delivery_outcome_sort)
    """
)

# %%
OUT.write_text(json.dumps(num(data), indent=2), encoding="utf-8")
con.close()
s = data["scenario"]
print(f"written: {OUT.relative_to(ROOT)}")
print("check: problem share of orders {:.1%}, of bad reviews {:.1%}".format(
    data["problem_share_of_orders"], data["problem_share_of_low"]))
print("check: scenario base A {:.0f}, B {:.0f}, A+B {:.0f}; new share {:.2%}".format(
    s["a"]["base"]["avoided"], s["b"]["base"]["avoided"], s["ab"]["base"]["avoided"], s["ab"]["base"]["new_low_share"]))
print("check: several-item incomplete {:.0%}, late not received {:.0%}".format(
    coding["several_incomplete"]["share"], coding["late_not_received"]["share"]))
