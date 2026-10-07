# %% [markdown]
# # 06 - Results of the review coding (Phase 5)
#
# Goal: turn the coded reviews into a results table.
#
# Input : review_coding/coding.csv             one row per sampled review: primary and secondary category
#         review_coding/sample.csv             the review texts
#         review_coding/sample_key.csv         delivery information, joined here for the first time
#         review_coding/categories.csv         the valid categories
#         review_coding/recoding.csv           30 of the reviews coded a second time (consistency check)
# Output: review_coding/coded_reviews.csv      coding + text + delivery information in one file
#         review_coding/results.md             generated - do not edit by hand
#
# The script stops with a clear message if the coding is incomplete or contains an unknown category.
#
# Usage: python notebooks/06_review_coding_results.py [folder]
#        folder = where the coding files are; default: review_coding/

# %%
import csv
import math
import sys
from collections import Counter
from pathlib import Path

# Windows consoles default to a legacy code page; force UTF-8 so Portuguese text prints safely.
sys.stdout.reconfigure(encoding="utf-8")

try:
    ROOT = Path(__file__).resolve().parents[1]
except NameError:  # running cell by cell: fall back to the working directory
    ROOT = Path.cwd() if (Path.cwd() / "sql").exists() else Path.cwd().parent

FOLDER = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else ROOT / "review_coding"


# %% [markdown]
# ## 1. Read and validate the coding

# %%
def read_csv(path: Path) -> list:
    """Read a CSV file as a list of dictionaries; empty cells become None."""
    with open(path, encoding="utf-8-sig") as handle:
        return [{k: (v.strip() or None) for k, v in row.items()} for row in csv.DictReader(handle)]


CATEGORIES = [row["category"] for row in read_csv(FOLDER / "categories.csv")]
GROUP_ORDER = ["On time, single item", "On time, several items", "Late", "Not delivered"]
coded = read_csv(FOLDER / "coding.csv")
texts = {int(row["sample_id"]): row for row in read_csv(FOLDER / "sample.csv")}
key = {int(row["sample_id"]): row for row in read_csv(FOLDER / "sample_key.csv")}

problems = []
for row in coded:
    sid = row["sample_id"]
    if row["primary_category"] is None:
        problems.append(f"sample_id {sid}: primary_category is empty")
    elif row["primary_category"] not in CATEGORIES:
        problems.append(f"sample_id {sid}: unknown primary_category '{row['primary_category']}'")
    if row["secondary_category"] is not None and row["secondary_category"] not in CATEGORIES:
        problems.append(f"sample_id {sid}: unknown secondary_category '{row['secondary_category']}'")
    if row["secondary_category"] is not None and row["secondary_category"] == row["primary_category"]:
        problems.append(f"sample_id {sid}: secondary_category repeats the primary_category")
if sorted(int(r["sample_id"]) for r in coded) != sorted(key):
    problems.append(f"coding.csv has {len(coded)} rows, the sample has {len(key)}, or the ids do not match")

if problems:
    print(f"The coding is not ready: {len(problems)} problem(s).")
    for line in problems[:25]:
        print("  -", line)
    sys.exit(1)

# join text and delivery information (kept apart until now, so the coding was blind)
for row in coded:
    sid = int(row["sample_id"])
    row["review_id"] = key[sid]["review_id"]
    row["review_score"] = texts[sid]["review_score"]
    row["review_comment_message"] = texts[sid]["review_comment_message"]
    row["delivery_group"] = key[sid]["delivery_group"]
    row["delivery_outcome"] = key[sid]["delivery_outcome"]
    row["delivery_group_sort"] = GROUP_ORDER.index(row["delivery_group"]) + 1   # display order for charts

with open(FOLDER / "coded_reviews.csv", "w", newline="", encoding="utf-8-sig") as handle:
    columns = ["sample_id", "review_id", "review_score", "primary_category", "secondary_category",
               "notes", "delivery_outcome", "delivery_group", "delivery_group_sort", "review_comment_message"]
    writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(coded)


# %% [markdown]
# ## 2. Helper functions

# %%
def wilson(successes: int, total: int) -> tuple:
    """95% Wilson confidence interval for a proportion."""
    z = 1.96
    p = successes / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return (max(0.0, centre - half), min(1.0, centre + half))


def md_table(headers, rows) -> list:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]
    return lines + [""]


def cohen_kappa(first: list, second: list) -> float:
    """Agreement between two codings of the same items, corrected for chance agreement."""
    total = len(first)
    observed = sum(a == b for a, b in zip(first, second)) / total
    count_1, count_2 = Counter(first), Counter(second)
    expected = sum(count_1[c] * count_2[c] for c in set(first) | set(second)) / (total * total)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def share_columns(rows_by_group: dict, groups: list) -> list:
    """Category shares inside each group (column percentages), with the number of reviews."""
    body = []
    for category in CATEGORIES:
        line = [category]
        for group in groups:
            members = rows_by_group[group]
            hits = sum(r["primary_category"] == category for r in members)
            line.append(f"{hits / len(members):.0%} ({hits})")
        body.append(line)
    body.append(["**Reviews**"] + [f"**{len(rows_by_group[g])}**" for g in groups])
    return body


# %% [markdown]
# ## 3. Results

# %%
total = len(coded)
primary = Counter(r["primary_category"] for r in coded)
mentioned = Counter()
for r in coded:
    mentioned.update({r["primary_category"], r["secondary_category"]} - {None})

report = [
    "# Review coding results",
    "",
    "Generated by `notebooks/06_review_coding_results.py` from `coding.csv`. "
    "Do not edit by hand: re-run the script instead.",
    "",
    f"Sample: {total} reviews with 1-2 stars and a written comment "
    "([`sampling_report.md`](sampling_report.md)). Categories and coding method: [`codebook.md`](codebook.md). "
    "The reviews were coded without knowing whether the order was late.",
    "",
    "## 1. What customers complain about",
    "",
    "*Primary* = the main complaint of the review (each review counted once). "
    "*Mentioned* = primary or secondary complaint. The confidence interval (Wilson, 95%) belongs to the primary share.",
    "",
]
report += md_table(
    ["category", "reviews (primary)", "share", "95% CI", "reviews (mentioned)", "share mentioned"],
    [
        (c, primary[c], f"{primary[c] / total:.1%}",
         "{:.0%} - {:.0%}".format(*wilson(primary[c], total)),
         mentioned[c], f"{mentioned[c] / total:.1%}")
        for c in sorted(CATEGORIES, key=lambda c: primary[c], reverse=True)
    ],
)

# Two broader groupings used in the storyline
DELIVERY = {"Not received", "Late delivery"}
CONTENT = {"Incomplete order", "Wrong item", "Damaged or defective", "Poor quality or not as described"}
family = Counter(
    "Delivery (not received, late)" if r["primary_category"] in DELIVERY
    else "What arrived (incomplete, wrong, damaged, poor quality)" if r["primary_category"] in CONTENT
    else "Service and other"
    for r in coded
)
report += ["### Grouped", ""]
report += md_table(
    ["group of categories", "reviews (primary)", "share", "95% CI"],
    [(g, c, f"{c / total:.1%}", "{:.0%} - {:.0%}".format(*wilson(c, total))) for g, c in family.most_common()],
)

outcomes = ["On time", "Late", "Not delivered"]
by_outcome = {o: [r for r in coded if r["delivery_outcome"] == o] for o in outcomes}
report += [
    "## 2. By delivery outcome",
    "",
    "Share of each primary category inside the group (number of reviews in brackets). "
    "Groups are small: read differences of less than about 15 points as noise.",
    "",
]
report += md_table(["category"] + outcomes, share_columns(by_outcome, outcomes))

groups = GROUP_ORDER
by_group = {g: [r for r in coded if r["delivery_group"] == g] for g in groups}
report += ["## 3. On-time orders split by order size", ""]
report += md_table(["category"] + groups, share_columns(by_group, groups))

# The shares the storyline relies on, each with its confidence interval (the groups are small)
def key_share(label: str, members: list, categories: set) -> tuple:
    hits = sum(r["primary_category"] in categories for r in members)
    low, high = wilson(hits, len(members))
    return (label, f"{hits} of {len(members)}", f"{hits / len(members):.0%}", f"{low:.0%} - {high:.0%}")


report += ["### Key shares with 95% confidence intervals", ""]
report += md_table(
    ["statement", "reviews", "share", "95% CI"],
    [
        key_share("On time, several items: complaint is 'Incomplete order'",
                  by_group["On time, several items"], {"Incomplete order"}),
        key_share("On time, single item: complaint is about what arrived (incomplete, wrong, damaged, poor quality)",
                  by_group["On time, single item"], CONTENT),
        key_share("On time (all): complaint is about what arrived", by_outcome["On time"], CONTENT),
        key_share("On time (all): complaint is 'Not received'", by_outcome["On time"], {"Not received"}),
        key_share("Late: complaint is 'Not received'", by_outcome["Late"], {"Not received"}),
        key_share("Late: complaint is about delivery (not received or late)", by_outcome["Late"], DELIVERY),
        key_share("Not delivered: complaint is 'Not received'", by_outcome["Not delivered"], {"Not received"}),
    ],
)

# Recurring details: the coder marked some reviews with a standard tag in the notes column
tags = Counter()
tag_by_group = {}
for r in coded:
    for part in (r["notes"] or "").split(";"):
        part = part.strip()
        if part.startswith("tag: "):
            tags[part[5:]] += 1
            tag_by_group.setdefault(part[5:], Counter())[r["delivery_group"]] += 1
report += [
    "## 4. Recurring details noted during coding",
    "",
    "Not categories: details that came up repeatedly and were tagged in the notes. Counts are small and "
    "only indicative.",
    "",
]
report += md_table(
    ["detail", "reviews", "by delivery group"],
    [(t, c, ", ".join(f"{g}: {k}" for g, k in tag_by_group[t].most_common())) for t, c in tags.most_common()],
)

# %% [markdown]
# ## 5. Consistency check: 30 reviews coded a second time

# %%
report += [
    "## 5. Consistency check (second coding pass)",
    "",
    "30 of the 300 reviews, selected by hash and presented in a different order (`recode_set.csv`), were "
    "coded a second time with the codebook. The table compares the primary category of both passes.",
    "",
]
recode_path = FOLDER / "recoding.csv"
recoded = read_csv(recode_path) if recode_path.exists() else []
if not recoded:
    report += ["Not done yet: `recoding.csv` is missing. [TBD]", ""]
else:
    unknown = [r for r in recoded if r["primary_category"] not in CATEGORIES]
    if unknown:
        sys.exit(f"recoding.csv contains {len(unknown)} unknown categories - fix them and re-run.")
    first_by_id = {int(r["sample_id"]): r["primary_category"] for r in coded}
    first = [first_by_id[int(r["sample_id"])] for r in recoded]
    second = [r["primary_category"] for r in recoded]
    same = sum(a == b for a, b in zip(first, second))
    report += md_table(
        ["measure", "value"],
        [
            ("Reviews coded twice", len(recoded)),
            ("Same primary category in both passes", f"{same} ({same / len(recoded):.0%})"),
            ("Cohen's kappa", f"{cohen_kappa(first, second):.2f}"),
        ],
    )
    disagreements = [(r["sample_id"], a, b) for r, a, b in zip(recoded, first, second) if a != b]
    if disagreements:
        report += ["Disagreements:", ""]
        report += md_table(["sample_id", "first pass", "second pass"], disagreements)
    report += [
        "How to read this: both passes were made by the same coder with the same codebook, shortly after each "
        "other. The check shows that the rules are applied consistently. It is not an independent validation: "
        "a second coder could draw the lines between categories differently.",
        "",
    ]

# %% [markdown]
# ## 6. Quote candidates (Portuguese originals)

# %%
quotes = [r for r in coded if r["good_quote"] is not None]
report += ["## 6. Quote candidates (Portuguese originals)", ""]
report += md_table(
    ["sample_id", "category", "delivery group", "original comment"],
    [(r["sample_id"], r["primary_category"], r["delivery_group"],
      " ".join(str(r["review_comment_message"]).split()).replace("|", "/")) for r in quotes],
)

(FOLDER / "results.md").write_text("\n".join(report), encoding="utf-8")
print("\n".join(report))
print(f"\nwritten: {FOLDER / 'results.md'}\nwritten: {FOLDER / 'coded_reviews.csv'}")
