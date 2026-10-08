# %% [markdown]
# # 10 - One-page summary (Phase 9)
#
# Goal: one A4 page that gives the answer, the three findings, the recommendations and the limits of the
# analysis. Every figure is read from deck/deck_data.json, the same file the deck is built from, so the
# page, the deck and the reports cannot show different numbers.
#
# Input : deck/deck_data.json (written by notebooks/09_deck_data.py)
# Output: docs/one_page_summary.html   the page as HTML (generated - do not edit by hand)
#         docs/one_page_summary.pdf    the same page printed to PDF by Edge or Chrome
#
# How the PDF is made: the script writes an HTML page sized to A4 and asks the browser, started without
# a window, to print it to PDF. If no browser is found, open the HTML file and print it to PDF by hand.

# %%
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

try:
    ROOT = Path(__file__).resolve().parents[1]
except NameError:
    ROOT = Path.cwd() if (Path.cwd() / "sql").exists() else Path.cwd().parent

D = json.loads((ROOT / "deck" / "deck_data.json").read_text(encoding="utf-8"))
HTML = ROOT / "docs" / "one_page_summary.html"
PDF = ROOT / "docs" / "one_page_summary.pdf"

AUTHOR = "Kostiantyn Dolyna"
REPO = "github.com/konstantyn-d/ecommerce-delivery-satisfaction-analysis"

# Counts of project documents, not of data. Sources: docs/decision_log.md (decisions),
# docs/model_validation_report.md (tests), docs/metric_definitions.md (KPIs), docs/analysis_findings.md
# (hypotheses), review_coding/codebook.md (complaint categories).
DECISIONS, TESTS, KPIS, HYPOTHESES, CATEGORIES = 32, 37, 13, 12, 8
MONTHS = 20   # analysis period: January 2017 to August 2018

# Same colours as the charts and the deck: blue = reference, orange = problem.
INK, DARK, MUTED, SOFT, TINT, RULE = "#1B1F23", "#16202A", "#6B7280", "#4B5563", "#F3F4F6", "#E1E0D9"
BLUE, ORANGE = "#2A78D6", "#EB6834"


# %%
def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}%"


def num(x: float) -> str:
    return f"{round(x):,}"


def about(x: float) -> str:
    """Round to the nearest hundred for 'about ...' statements."""
    return f"{round(x, -2):,.0f}"


def b_(text: str) -> str:
    """Bold, for the key figure of a sentence."""
    return f"<b>{text}</b>"


b = D["baseline"]
S = D["scenario"]
C = D["coding"]
outcome = {o["delivery_outcome"]: o for o in D["outcomes"]}
band = {d["delay_band"]: d for d in D["delay_bands"]}
size = {o["order_size"]: o for o in D["order_size"]}
transit = {t["delivery_outcome"]: t for t in D["transit"]}
rj = next(s for s in D["states"] if s["state"] == "RJ")


# %% [markdown]
# ## Charts
# Two small charts drawn as SVG, so they stay sharp in the PDF. Values are written on the marks; the text
# is always in the text colour, the colour of a mark only says which group it belongs to.

# %%
def column_chart() -> str:
    """Share of 1-2 star reviews by delivery outcome: one column per delay band."""
    bands = D["delay_bands"]
    width, top, base, bar = 340, 18, 176, 24
    slot = width / len(bands)
    scale = (base - top) / max(d["low_share"] for d in bands)
    two_lines = {
        "On time": ("On time", ""), "Late 1-3 days": ("Late", "1–3 days"), "Late 4-7 days": ("Late", "4–7 days"),
        "Late 8-14 days": ("Late", "8–14 days"), "Late 15+ days": ("Late", "15+ days"),
        "Not delivered": ("Not", "delivered"),
    }
    parts = []
    for i, d in enumerate(bands):
        x = i * slot + (slot - bar) / 2
        y = base - d["low_share"] * scale
        colour = BLUE if d["delay_band"] == "On time" else ORANGE
        # column with a rounded top and a square foot on the baseline
        parts.append(
            f'<path d="M{x:.1f},{base} V{y + 4:.1f} Q{x:.1f},{y:.1f} {x + 4:.1f},{y:.1f} H{x + bar - 4:.1f} '
            f'Q{x + bar:.1f},{y:.1f} {x + bar:.1f},{y + 4:.1f} V{base} Z" fill="{colour}"/>')
        mid = x + bar / 2
        parts.append(f'<text x="{mid:.1f}" y="{y - 5:.1f}" class="val">{pct(d["low_share"], 0)}</text>')
        first, second = two_lines[d["delay_band"]]
        parts.append(f'<text x="{mid:.1f}" y="{base + 13}" class="cat">{first}</text>')
        parts.append(f'<text x="{mid:.1f}" y="{base + 24}" class="cat">{second}</text>')
    parts.append(f'<line x1="0" y1="{base}" x2="{width}" y2="{base}" stroke="#C9C8C2" stroke-width="1"/>')
    return (f'<svg viewBox="0 0 {width} {base + 28}" role="img" '
            f'aria-label="Share of 1-2 star reviews by delivery outcome">{"".join(parts)}</svg>')


def range_chart() -> str:
    """Bad reviews avoided per scenario: bar = base case, line = low to high case."""
    rows = [("On-time delivery in the five worst states", S["a"]),
            ("Complete orders with several items", S["b"]),
            ("Both together", S["ab"])]
    width, plot, step, bar = 340, 215, 42, 14
    scale = plot / max(r["high"]["avoided"] for _, r in rows)
    parts = []
    for i, (label, r) in enumerate(rows):
        y = i * step
        low, base, high = (r[c]["avoided"] * scale for c in ("low", "base", "high"))
        top, mid = y + 15, y + 15 + bar / 2
        parts.append(f'<text x="0" y="{y + 10}" class="row">{label}</text>')
        parts.append(
            f'<path d="M0,{top} H{base - 4:.1f} Q{base:.1f},{top} {base:.1f},{top + 4} V{top + bar - 4} '
            f'Q{base:.1f},{top + bar} {base - 4:.1f},{top + bar} H0 Z" fill="{BLUE}"/>')
        parts.append(f'<path d="M{low:.1f},{mid} H{high:.1f} M{low:.1f},{mid - 4} v8 M{high:.1f},{mid - 4} v8" '
                     f'stroke="{INK}" stroke-width="1.2" fill="none"/>')
        parts.append(
            f'<text x="{high + 7:.1f}" y="{mid + 3.5}" class="end"><tspan class="b">{num(r["base"]["avoided"])}</tspan>'
            f' ({num(r["low"]["avoided"])}–{num(r["high"]["avoided"])})</text>')
    return (f'<svg viewBox="0 0 {width} {len(rows) * step - 8}" role="img" '
            f'aria-label="Bad reviews avoided per scenario">{"".join(parts)}</svg>')


# %% [markdown]
# ## Text
# Wording follows the deck: "driver" and "account for", never "cause". The limits are on the page itself.

# %%
late, on_time, not_delivered = outcome["Late"], outcome["On time"], outcome["Not delivered"]
several, single = size["Several items"], size["Single item"]
ci = C["several_incomplete"]["ci"]

answer = (
    f"Broken delivery promises and incomplete orders account for the avoidable bad reviews. Orders that arrive "
    f"late or not at all are {pct(D['problem_share_of_orders'])} of orders but {pct(D['problem_share_of_low'])} of "
    f"all 1–2 star reviews, and orders with several items often arrive incomplete. Complete orders and on-time "
    f"delivery in the five worst states could remove about {about(S['ab']['base']['avoided'])} bad reviews, "
    f"{pct(S['ab']['base']['share_of_all_bad'], 0)} of the total."
)

findings = [
    ("A broken delivery promise is the strongest driver of bad reviews",
     f"{b_(pct(late['low_share']))} of late orders and {b_(pct(not_delivered['low_share']))} of orders that never "
     f"arrive get 1–2 stars, against {b_(pct(on_time['low_share']))} of on-time orders."),
    ("The delay arises in transit on specific routes, not with a few bad sellers",
     f"Rio de Janeiro has {b_(pct(rj['share_of_orders']))} of orders but {b_(pct(rj['share_of_late']))} of late "
     f"deliveries. {pct(1 - transit['Late']['handed_over_late_share'], 0)} of late orders left the seller in time, "
     f"then spent a median {transit['Late']['median_transit_days']:.0f} days in transit, against "
     f"{transit['On time']['median_transit_days']:.0f} days."),
    ("Orders with several items arrive on time, but often incomplete",
     f"{b_(pct(several['low_share']))} get 1–2 stars, against {b_(pct(single['low_share']))} of single-item orders. "
     f"In {C['sample_size']} coded reviews, {b_(pct(C['several_incomplete']['share'], 0))} of the complaints in "
     f"this group (95% CI {ci[0] * 100:.0f}–{ci[1] * 100:.0f}%) say part of the order is missing."),
]

recommendations = [
    ("Make every order complete, and measure it",
     f"About {b_(num(S['b']['base']['avoided']))} fewer bad reviews ({num(S['b']['low']['avoided'])}–"
     f"{num(S['b']['high']['avoided'])}). First step: audit 100 several-item orders marked as delivered. Sent "
     f"later, or never sent?"),
    ("Fix transit on the worst routes",
     f"About {b_(num(S['a']['base']['avoided']))} fewer bad reviews ({num(S['a']['low']['avoided'])}–"
     f"{num(S['a']['high']['avoided'])}). First step: a carrier scorecard for Rio de Janeiro and the Northeast, "
     f"and a review of the promised dates there."),
    ("Warn customers before a missed promise",
     f"Not quantified: needs a test. Bad reviews go from {pct(band['Late 1-3 days']['low_share'], 0)} at 1–3 days "
     f"late to {pct(band['Late 4-7 days']['low_share'], 0)} at 4–7 days: the first days after the promised date "
     f"are the window to act."),
]

method = (
    f"{num(b['orders'])} orders, January 2017 to August 2018. SQL star schema in DuckDB from 9 raw tables, with "
    f"{DECISIONS} documented data quality decisions, {TESTS} validation tests and {KPIS} KPI definitions. "
    f"{HYPOTHESES} hypotheses from an issue tree, each tested with data. A stratified random sample of "
    f"{C['sample_size']} bad reviews, coded with a codebook of {CATEGORIES} complaint types. A scenario with low, "
    f"base and high cases. Power BI dashboard and 10-slide deck built from the same numbers."
)

limits = (
    "Observational data: the findings are strong associations, not proven effects, and the scenario is an "
    "estimate, not a forecast. The review survey is sent around the promised date, so most late customers "
    "answer while still waiting. Impact is counted in reviews, not in money: costs are not in the data. The "
    "reviews were coded by one coder; only customers who wrote a comment are represented."
)


# %% [markdown]
# ## Page

# %%
CSS = f":root {{ --ink: {INK}; --dark: {DARK}; --muted: {MUTED}; --soft: {SOFT}; --tint: {TINT}; --rule: {RULE}; }}" + """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font-family: Calibri, Carlito, "Segoe UI", Arial, sans-serif; font-size: 9.6pt; line-height: 1.32;
       color: var(--ink); -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { width: 210mm; height: 297mm; display: flex; flex-direction: column; overflow: hidden; background: #fff; }
header { background: var(--dark); color: #fff; padding: 10mm 15mm 8mm; display: flex;
         justify-content: space-between; align-items: flex-end; gap: 8mm; }
.kicker { font-size: 8pt; letter-spacing: .14em; text-transform: uppercase; font-weight: 700; color: #D1D5DB; }
h1 { font-family: Cambria, Georgia, serif; font-size: 23pt; line-height: 1.1; margin: 2.2mm 0 1.6mm;
     white-space: nowrap; }
.sub { font-size: 11.5pt; color: #D1D5DB; }
.hero { text-align: right; flex: none; }
.hero .n { font-family: Cambria, Georgia, serif; font-size: 34pt; font-weight: 700; line-height: 1; }
.hero .l { font-size: 8.8pt; line-height: 1.25; color: #D1D5DB; width: 40mm; margin: 1.2mm 0 0 auto; }
main { padding: 7mm 15mm 5mm; flex: 1; display: flex; flex-direction: column; justify-content: space-between; }
.answer { font-family: Cambria, Georgia, serif; font-size: 12.4pt; line-height: 1.3; margin: 0; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 9mm; }
h2 { font-size: 8pt; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); font-weight: 700;
     margin: 0 0 3mm; padding-bottom: 1.3mm; border-bottom: .3mm solid var(--rule); }
.item { display: grid; grid-template-columns: 6mm 1fr; gap: 2.6mm; margin-bottom: 3.2mm; }
.item:last-child { margin-bottom: 0; }
.badge { width: 6mm; height: 6mm; border-radius: 50%; background: var(--dark); color: #fff; font-weight: 700;
         font-size: 9pt; display: flex; align-items: center; justify-content: center; }
.item .h { font-family: Cambria, Georgia, serif; font-size: 11pt; font-weight: 700; line-height: 1.2;
           margin-bottom: .7mm; }
figure { margin: 0; }
figcaption { font-size: 9.4pt; font-weight: 700; line-height: 1.25; margin-bottom: 1.2mm; }
.key { font-size: 8.5pt; color: var(--soft); margin-bottom: 1mm; }
.key i { display: inline-block; width: 2.6mm; height: 2.6mm; border-radius: .6mm; margin: 0 1.2mm 0 0;
         vertical-align: -0.3mm; }
.key i + span { margin-right: 4mm; }
svg { display: block; width: 100%; height: auto; }
svg text { font-family: Calibri, Carlito, "Segoe UI", Arial, sans-serif; fill: var(--ink); }
svg .val { font-size: 11px; font-weight: 700; text-anchor: middle; }
svg .cat { font-size: 9.5px; fill: var(--soft); text-anchor: middle; }
svg .row { font-size: 10.5px; }
svg .end { font-size: 10.5px; fill: var(--soft); }
svg .end .b { font-weight: 700; fill: var(--ink); }
.note { font-size: 8.5pt; line-height: 1.3; color: var(--soft); }
.shift { display: grid; grid-template-columns: auto 1fr; gap: 3.5mm; align-items: center; background: var(--tint);
         border-radius: 2mm; padding: 2.4mm 3.5mm; margin-top: 2.5mm; }
.shift .v { font-family: Cambria, Georgia, serif; font-size: 15pt; font-weight: 700; white-space: nowrap; }
.shift .l { font-size: 8.5pt; line-height: 1.25; color: var(--soft); }
footer { margin: 0 15mm; padding: 2.8mm 0 7mm; border-top: .3mm solid var(--rule); font-size: 8pt;
         color: var(--muted); display: flex; justify-content: space-between; gap: 8mm; white-space: nowrap; }
footer b { color: var(--ink); }
footer a { color: inherit; text-decoration: none; }
"""


def items(pairs) -> str:
    return "".join(
        f'<div class="item"><div class="badge">{i}</div><div><div class="h">{head}</div>{body}</div></div>'
        for i, (head, body) in enumerate(pairs, start=1))


page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Late Deliveries, Lost Customers: one-page summary</title>
<meta name="author" content="{AUTHOR}">
<style>{CSS}</style>
</head>
<body>
<div class="page">
  <header>
    <div>
      <div class="kicker">Business analysis case study &middot; Olist, Brazilian e-commerce marketplace</div>
      <h1>Late Deliveries, Lost Customers</h1>
      <div class="sub">Why customers give bad reviews, and what to fix first</div>
    </div>
    <div class="hero">
      <div class="n">{pct(b["low_score_rate"])}</div>
      <div class="l">of reviewed orders get a 1–2 star review ({num(b["low_score_orders"])} of {num(b["reviewed_orders"])})</div>
    </div>
  </header>
  <main>
    <p class="answer">{answer}</p>
    <div class="cols">
      <section>
        <h2>What the data shows</h2>
        {items(findings)}
      </section>
      <section>
        <h2>Bad reviews by delivery outcome</h2>
        <figure>
          <figcaption>Share of reviewed orders with a 1–2 star review</figcaption>
          <div class="key"><i style="background:{BLUE}"></i><span>promise kept</span><i style="background:{ORANGE}"></i><span>promise broken</span></div>
          {column_chart()}
        </figure>
      </section>
    </div>
    <div class="cols">
      <section>
        <h2>What to do first</h2>
        {items(recommendations)}
      </section>
      <section>
        <h2>What fixing it could achieve</h2>
        <figure>
          <figcaption>Estimated 1–2 star reviews avoided over {MONTHS} months, of {num(b["low_score_orders"])}</figcaption>
          {range_chart()}
        </figure>
        <div class="note" style="margin-top:1.5mm">Bar: base case, {S["cases"]["base"] * 100:.0f}% of the observed difference between the groups
        is a real effect. Line: low case ({S["cases"]["low"] * 100:.0f}%) to high case ({S["cases"]["high"] * 100:.0f}%).</div>
        <div class="shift">
          <div class="v">{pct(b["low_score_rate"])} &rarr; {pct(S["ab"]["base"]["new_low_share"])}</div>
          <div class="l">share of 1–2 star reviews if both are done, base case</div>
        </div>
      </section>
    </div>
    <div class="cols">
      <section>
        <h2>How it was done</h2>
        <div class="note">{method}</div>
      </section>
      <section>
        <h2>What to keep in mind</h2>
        <div class="note">{limits}</div>
      </section>
    </div>
  </main>
  <footer>
    <div><b>{AUTHOR}</b> &middot; <a href="https://{REPO}">{REPO}</a></div>
    <div>Data: Olist public dataset (Kaggle), CC BY-NC-SA 4.0</div>
  </footer>
</div>
</body>
</html>
"""

HTML.write_text(page, encoding="utf-8", newline="\n")
print(f"written: {HTML.relative_to(ROOT)}")


# %% [markdown]
# ## PDF
# Edge and Chrome can print a page to PDF without opening a window. The page size comes from the CSS (A4).

# %%
def find_browser():
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    for name in ("msedge", "google-chrome", "chromium", "chromium-browser", "chrome"):
        if shutil.which(name):
            return shutil.which(name)
    return None


browser = find_browser()
if browser is None:
    print("No Edge or Chrome found: open the HTML file in a browser and print it to PDF (A4, no margins).")
else:
    PDF.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        subprocess.run(
            [browser, "--headless", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
             f"--user-data-dir={profile}", f"--print-to-pdf={PDF}", HTML.as_uri()],
            check=True, timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # the browser can return a moment before the file is on disk
        for _ in range(60):
            if PDF.exists():
                break
            time.sleep(0.5)
    if not PDF.exists():
        sys.exit("The browser did not write the PDF: open the HTML file and print it to PDF by hand.")
    data = PDF.read_bytes()
    pages = data.count(b"/Type /Page") - data.count(b"/Type /Pages")
    print(f"written: {PDF.relative_to(ROOT)} ({pages} page)")
    if pages != 1:
        sys.exit("The summary no longer fits on one page: shorten the text.")
