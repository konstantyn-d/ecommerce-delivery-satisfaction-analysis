# %% [markdown]
# # 07 - "What if" scenario (Phase 6)
#
# Goal: estimate what two improvements could do to the share of 1-2 star reviews and to the average score.
#
#   Scenario A (delivery):     the states with the most excess late orders reach the national late rate.
#   Scenario B (completeness): on-time orders with several items get bad reviews as rarely as on-time
#                              orders with a single item.
#
# Method: orders that would move from the "bad" group to the "good" group are assumed to be reviewed like
# the good group. Because the observed difference between the groups is not a proven causal effect, the
# result is computed for three assumptions about how much of that difference is real: low, base, high.
#
# Input : data/processed/olist.duckdb (star schema in schema `model`)
# Output: docs/scenario_results.md (generated - do not edit by hand)
#         docs/charts/09_scenario.png
#
# This is an estimate built on observed differences. It is not a forecast and not a measured effect.

# %%
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
REPORT_PATH = ROOT / "docs" / "scenario_results.md"
CHART_PATH = ROOT / "docs" / "charts" / "09_scenario.png"

con = duckdb.connect(str(DB_PATH), read_only=True)

# %% [markdown]
# ## Assumptions (change them here; everything below is recomputed)

# %%
N_STATES = 5  # scenario A: number of states, ranked by excess late orders
# Share of the observed difference between the groups that is assumed to be a real effect.
CASES = {"Low": 0.50, "Base": 0.75, "High": 1.00}
MONTHS = 20   # length of the analysis period, to express results per month


# %%
def md_table(headers, rows) -> list:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]
    return lines + [""]


def as_dict(sql: str) -> dict:
    """Run a query that returns one row and give it back as {column name: value}."""
    cursor = con.execute(sql)
    return dict(zip([col[0] for col in cursor.description], cursor.fetchone()))


# %% [markdown]
# ## Baseline: where we are today

# %%
base = as_dict(
    """
    SELECT count(*) FILTER (WHERE is_delivered)                 AS delivered,
           count(*) FILTER (WHERE delivery_outcome = 'Late')    AS late,
           count(*) FILTER (WHERE has_review)                   AS reviewed,
           count(*) FILTER (WHERE is_low_score)                 AS low,
           sum(review_score)                                    AS score_sum
    FROM model.fact_orders
    """
)
NATIONAL_LATE_RATE = base["late"] / base["delivered"]
LOW_SHARE = base["low"] / base["reviewed"]
AVG_SCORE = float(base["score_sum"]) / base["reviewed"]

# %% [markdown]
# ## Scenario A: the worst states reach the national late rate
# "Excess late orders" of a state = its late orders minus the late orders it would have at the national
# late rate. The N states with the largest excess are the target.

# %%
states = con.execute(
    f"""
    SELECT f.customer_state AS state, g.state_name,
           count(*) FILTER (WHERE f.is_delivered)                                    AS delivered,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late')                       AS late,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late')
               - count(*) FILTER (WHERE f.is_delivered) * {NATIONAL_LATE_RATE}       AS excess_late,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late' AND f.has_review)      AS late_reviewed,
           count(*) FILTER (WHERE f.delivery_outcome = 'Late' AND f.is_low_score)    AS late_low,
           sum(f.review_score) FILTER (WHERE f.delivery_outcome = 'Late')            AS late_score_sum,
           count(*) FILTER (WHERE f.delivery_outcome = 'On time' AND f.has_review)   AS on_reviewed,
           count(*) FILTER (WHERE f.delivery_outcome = 'On time' AND f.is_low_score) AS on_low,
           sum(f.review_score) FILTER (WHERE f.delivery_outcome = 'On time')         AS on_score_sum
    FROM model.fact_orders f
    JOIN model.dim_geography g ON g.state_code = f.customer_state
    GROUP BY f.customer_state, g.state_name
    ORDER BY excess_late DESC
    """
).fetchall()
STATE_COLUMNS = ["state", "state_name", "delivered", "late", "excess_late", "late_reviewed", "late_low",
                 "late_score_sum", "on_reviewed", "on_low", "on_score_sum"]
states = [dict(zip(STATE_COLUMNS, row)) for row in states]


def scenario_a(target: list) -> dict:
    """Inputs of scenario A for a list of target states (pooled)."""
    total = {k: sum(float(s[k]) for s in target) for k in STATE_COLUMNS[2:]}
    return {
        "states": ", ".join(s["state"] for s in target),
        "orders_moved": total["excess_late"],                               # late orders that become on time
        "reviewed_share": total["late_reviewed"] / total["late"],           # share of late orders with a review
        "bad_from": total["late_low"] / total["late_reviewed"],             # bad review share of late orders
        "bad_to": total["on_low"] / total["on_reviewed"],                   # ... of on-time orders, same states
        "score_from": total["late_score_sum"] / total["late_reviewed"],
        "score_to": total["on_score_sum"] / total["on_reviewed"],
        "late_rate_before": total["late"] / total["delivered"],
    }


a_main = scenario_a(states[:N_STATES])
a_one = scenario_a(states[:1])
a_all = scenario_a([s for s in states if s["excess_late"] > 0])

# %% [markdown]
# ## Scenario B: on-time orders with several items reviewed like single-item orders

# %%
b = as_dict(
    """
    SELECT count(*) FILTER (WHERE item_count >= 2 AND has_review)              AS multi_reviewed,
           count(*) FILTER (WHERE item_count >= 2 AND is_low_score)            AS multi_low,
           sum(review_score) FILTER (WHERE item_count >= 2)                    AS multi_score_sum,
           count(*) FILTER (WHERE item_count = 1 AND has_review)               AS single_reviewed,
           count(*) FILTER (WHERE item_count = 1 AND is_low_score)             AS single_low,
           sum(review_score) FILTER (WHERE item_count = 1)                     AS single_score_sum
    FROM model.fact_orders
    WHERE delivery_outcome = 'On time'
    """
)
b_inputs = {
    "reviews_moved": b["multi_reviewed"],
    "bad_from": b["multi_low"] / b["multi_reviewed"],
    "bad_to": b["single_low"] / b["single_reviewed"],
    "score_from": float(b["multi_score_sum"]) / b["multi_reviewed"],
    "score_to": float(b["single_score_sum"]) / b["single_reviewed"],
}


# %% [markdown]
# ## The calculation
# avoided bad reviews = reviews that move x (bad share before - bad share after) x case factor

# %%
def effect(reviews_moved: float, inputs: dict, factor: float) -> dict:
    """Effect of moving `reviews_moved` reviewed orders from the bad group to the good group."""
    avoided = reviews_moved * (inputs["bad_from"] - inputs["bad_to"]) * factor
    score_points = reviews_moved * (inputs["score_to"] - inputs["score_from"]) * factor
    return {
        "avoided": avoided,
        "new_low_share": (base["low"] - avoided) / base["reviewed"],
        "new_avg_score": AVG_SCORE + score_points / base["reviewed"],
        "share_of_all_bad": avoided / base["low"],
    }


def effect_a(inputs: dict, factor: float) -> dict:
    return effect(inputs["orders_moved"] * inputs["reviewed_share"], inputs, factor)


def effect_b(factor: float) -> dict:
    return effect(b_inputs["reviews_moved"], b_inputs, factor)


def combined(factor: float) -> dict:
    """A and B concern different orders (late vs on time), so their effects add up."""
    ea, eb = effect_a(a_main, factor), effect_b(factor)
    avoided = ea["avoided"] + eb["avoided"]
    return {
        "avoided": avoided,
        "new_low_share": (base["low"] - avoided) / base["reviewed"],
        "new_avg_score": ea["new_avg_score"] + eb["new_avg_score"] - AVG_SCORE,
        "share_of_all_bad": avoided / base["low"],
    }


# %% [markdown]
# ## Report

# %%
def result_rows(label: str, fn) -> list:
    out = []
    for case, factor in CASES.items():
        e = fn(factor)
        out.append((
            label, case, f"{factor:.0%}", f"{e['avoided']:,.0f}", f"{e['avoided'] / MONTHS:,.0f}",
            f"{e['share_of_all_bad']:.1%}", f"{e['new_low_share']:.2%}",
            f"{(e['new_low_share'] - LOW_SHARE) * 100:+.2f} pp", f"{e['new_avg_score']:.3f}",
            f"{e['new_avg_score'] - AVG_SCORE:+.3f}",
        ))
    return out


RESULT_HEADERS = ["scenario", "case", "share of observed gap assumed real", "bad reviews avoided",
                  "per month", "share of all bad reviews", "new 1-2 star share", "change",
                  "new average score", "change"]

report = [
    "# Scenario results",
    "",
    "Generated by `notebooks/07_scenario.py`. Do not edit by hand: re-run the script instead.",
    "",
    "Assumptions, method and interpretation: [`scenario.md`](scenario.md). "
    "**These are estimates built on observed differences between groups of orders, not measured effects.**",
    "",
    "## 1. Baseline (orders purchased 2017-01 to 2018-08)",
    "",
]
report += md_table(
    ["figure", "value"],
    [
        ("Delivered orders", f"{base['delivered']:,}"),
        ("Late orders", f"{base['late']:,}"),
        ("National late rate", f"{NATIONAL_LATE_RATE:.2%}"),
        ("Reviewed orders", f"{base['reviewed']:,}"),
        ("Orders with a 1-2 star review", f"{base['low']:,}"),
        ("Share of 1-2 star reviews", f"{LOW_SHARE:.2%}"),
        ("Average review score", f"{AVG_SCORE:.3f}"),
    ],
)

report += [
    "## 2. Scenario A: states with the most excess late orders reach the national late rate",
    "",
    "### Target states",
    "",
]
report += md_table(
    ["rank", "state", "delivered orders", "late orders", "late rate", "late orders at national rate", "excess late orders"],
    [
        (i + 1, f"{s['state_name']} ({s['state']})", f"{s['delivered']:,}", f"{s['late']:,}",
         f"{s['late'] / s['delivered']:.1%}", f"{s['delivered'] * NATIONAL_LATE_RATE:,.0f}", f"{float(s['excess_late']):,.0f}")
        for i, s in enumerate(states[:10])
    ],
)
report += ["### Inputs", ""]
report += md_table(
    ["input", f"top {N_STATES} states (main scenario)", "top 1 state", "all states above the national rate"],
    [
        ("States", a_main["states"], a_one["states"], f"{len([s for s in states if s['excess_late'] > 0])} states"),
        ("Late rate today in these states", *[f"{x['late_rate_before']:.1%}" for x in (a_main, a_one, a_all)]),
        ("Late orders that would become on time", *[f"{x['orders_moved']:,.0f}" for x in (a_main, a_one, a_all)]),
        ("Share of late orders that have a review", *[f"{x['reviewed_share']:.1%}" for x in (a_main, a_one, a_all)]),
        ("1-2 star share of late orders", *[f"{x['bad_from']:.1%}" for x in (a_main, a_one, a_all)]),
        ("1-2 star share of on-time orders", *[f"{x['bad_to']:.1%}" for x in (a_main, a_one, a_all)]),
        ("Average score of late orders", *[f"{x['score_from']:.2f}" for x in (a_main, a_one, a_all)]),
        ("Average score of on-time orders", *[f"{x['score_to']:.2f}" for x in (a_main, a_one, a_all)]),
        ("National late rate after the change",
         *[f"{(base['late'] - x['orders_moved']) / base['delivered']:.2%}" for x in (a_main, a_one, a_all)]),
    ],
)
report += ["### Results", ""]
report += md_table(
    RESULT_HEADERS,
    result_rows(f"A: top {N_STATES} states", lambda f: effect_a(a_main, f))
    + result_rows("A: top 1 state", lambda f: effect_a(a_one, f))
    + result_rows("A: all states above national rate", lambda f: effect_a(a_all, f)),
)

report += [
    "## 3. Scenario B: on-time orders with several items are reviewed like single-item orders",
    "",
    "### Inputs",
    "",
]
report += md_table(
    ["input", "value"],
    [
        ("On-time orders with several items that have a review", f"{b_inputs['reviews_moved']:,}"),
        ("Their 1-2 star share today", f"{b_inputs['bad_from']:.1%}"),
        ("1-2 star share of on-time single-item orders", f"{b_inputs['bad_to']:.1%}"),
        ("Their average score today", f"{b_inputs['score_from']:.2f}"),
        ("Average score of on-time single-item orders", f"{b_inputs['score_to']:.2f}"),
    ],
)
report += ["### Results", ""]
report += md_table(RESULT_HEADERS, result_rows("B: order completeness", effect_b))

report += [
    f"## 4. Both together (A with the top {N_STATES} states, plus B)",
    "",
    "The two scenarios concern different orders (late orders vs on-time orders), so their effects add up.",
    "",
]
report += md_table(RESULT_HEADERS, result_rows("A + B", combined))

# reference point: the most that fixing lateness everywhere could achieve
late_all = as_dict(
    """
    SELECT count(*) FILTER (WHERE delivery_outcome = 'Late' AND has_review)      AS late_reviewed,
           count(*) FILTER (WHERE delivery_outcome = 'Late' AND is_low_score)    AS late_low,
           count(*) FILTER (WHERE delivery_outcome = 'On time' AND has_review)   AS on_reviewed,
           count(*) FILTER (WHERE delivery_outcome = 'On time' AND is_low_score) AS on_low
    FROM model.fact_orders
    """
)
ceiling = late_all["late_reviewed"] * (late_all["late_low"] / late_all["late_reviewed"] - late_all["on_low"] / late_all["on_reviewed"])
report += [
    "## 5. Reference point",
    "",
    f"If every late order in the country were on time and the full observed difference were real, "
    f"{ceiling:,.0f} bad reviews would be avoided ({ceiling / base['low']:.1%} of all bad reviews) and the share of "
    f"1-2 star reviews would be {(base['low'] - ceiling) / base['reviewed']:.2%}. This is the ceiling for any "
    "action on late deliveries alone.",
    "",
]

# anchor for the case factors: what if a late order became "on time, but still slow"?
slow = as_dict(
    """
    SELECT count(*) FILTER (WHERE has_review)   AS reviewed,
           count(*) FILTER (WHERE is_low_score) AS low
    FROM model.fact_orders
    WHERE delivery_outcome = 'On time' AND delivery_days >= 22
    """
)
p_late = late_all["late_low"] / late_all["late_reviewed"]
p_on = late_all["on_low"] / late_all["on_reviewed"]
p_slow = slow["low"] / slow["reviewed"]
report += [
    "## 6. Anchor for the case factors",
    "",
    "The low, base and high factors are assumptions. One data point helps to place them: an order that stops "
    "being late does not necessarily become a fast order. On-time orders that took 22 days or more "
    f"({slow['reviewed']:,} reviewed orders) have a 1-2 star share of {p_slow:.1%}, against {p_on:.1%} for all "
    f"on-time orders and {p_late:.1%} for late orders. If former late orders were reviewed like these slow "
    f"on-time orders, {(p_late - p_slow) / (p_late - p_on):.0%} of the full gap would be realised.",
    "",
]

REPORT_PATH.write_text("\n".join(report), encoding="utf-8")
print("\n".join(report))

# %% [markdown]
# ## Chart: both scenarios with their low-high range

# %%
BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#a8a7a0"
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.edgecolor": AXIS, "xtick.color": INK_2, "ytick.color": INK_2,
    "xtick.major.size": 0, "ytick.major.size": 0,
})

bars = [
    (f"A: {N_STATES} worst states reach\nthe national late rate", lambda f: effect_a(a_main, f)),
    ("B: several-item orders reviewed\nlike single-item orders", effect_b),
    ("A + B", combined),
]
values = [(label, fn(CASES["Low"])["avoided"], fn(CASES["Base"])["avoided"], fn(CASES["High"])["avoided"]) for label, fn in bars]
ratio = values[1][2] / values[0][2]

title = (f"Complete orders could avoid about {ratio:.1f}x more bad reviews than fixing late deliveries "
         f"in the {N_STATES} worst states")
subtitle = (f"Estimated 1-2 star reviews avoided over {MONTHS} months. Bar = base case "
            f"({CASES['Base']:.0%} of the observed gap is real); line = low to high case")
width, height = 9, 4.4
fig, ax = plt.subplots(figsize=(width, height), dpi=150)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)
wrapped = textwrap.fill(title, int(width * 9.5))
lines = wrapped.count("\n") + 1
title_y = 1 - 0.15 / height
subtitle_y = title_y - (0.30 * lines) / height
fig.text(0.03, title_y, wrapped, ha="left", va="top", fontsize=13, fontweight="bold", color=INK)
fig.text(0.03, subtitle_y, subtitle, ha="left", va="top", fontsize=9.5, color=INK_2)
fig.subplots_adjust(top=subtitle_y - 0.45 / height, bottom=0.75 / height, left=0.30, right=0.94)

ys = range(len(values))
ax.barh(ys, [v[2] for v in values], height=0.42, color=[ORANGE, ORANGE, GREY])
ax.errorbar([v[2] for v in values], ys,
            xerr=[[v[2] - v[1] for v in values], [v[3] - v[2] for v in values]],
            fmt="none", ecolor=INK_2, elinewidth=1.2, capsize=4)
for y, v in zip(ys, values):
    ax.text(v[3] + 40, y, f"{v[2]:,.0f}  ({v[1]:,.0f} - {v[3]:,.0f})", va="center", fontsize=9.5, color=INK)
ax.set_yticks(list(ys), [v[0] for v in values])
ax.invert_yaxis()
ax.set_xlim(0, max(v[3] for v in values) * 1.45)
ax.set_axisbelow(True)
ax.grid(axis="x", color=GRID, linewidth=0.8)
ax.xaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
fig.text(0.03, 0.02,
         f"Source: Olist public dataset, orders purchased Jan 2017 - Aug 2018. Baseline: {base['low']:,} bad reviews. "
         "Estimate, not a measured effect.",
         ha="left", va="bottom", fontsize=8, color=MUTED)
fig.savefig(CHART_PATH, facecolor=SURFACE)
plt.close(fig)
con.close()
print(f"\nchart saved: {CHART_PATH.relative_to(ROOT)}\nReport written to {REPORT_PATH.relative_to(ROOT)}")
