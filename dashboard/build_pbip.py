"""Build the Power BI dashboard as a Power BI Project (PBIP) from code.

Output (all inside dashboard/):
    olist_delivery_dashboard.pbip                 open this file in Power BI Desktop
    olist_delivery_dashboard.SemanticModel/       the data model in TMDL: tables, relationships, measures
    olist_delivery_dashboard.Report/              the report in PBIR: 3 pages and their visuals
    measures.dax                                  the same measures as a readable DAX file

Why code instead of clicking: every table, relationship, measure, visual and title is written down in one
place, can be reviewed in Git, and the whole dashboard can be rebuilt after the data changes.

Run from the repository root, after `python run_sql.py`:
    python dashboard/build_pbip.py

The model loads the Parquet files in data/processed/ and review_coding/coded_reviews.csv. Their location is
the Power Query parameter `DataFolder` (default: this repository). After opening the project for the first
time, click Refresh in Power BI Desktop to load the data.
"""

import json
import shutil
import uuid
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard"
NAME = "olist_delivery_dashboard"
MODEL_DIR = OUT / f"{NAME}.SemanticModel"
REPORT_DIR = OUT / f"{NAME}.Report"
NAMESPACE = uuid.UUID("6f6c6973-742d-6465-6c69-766572792d31")  # fixed: same ids on every build

BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#a8a7a0"

# Schema versions written into the report files (supported by Power BI Desktop since 2025)
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
VISUAL_SCHEMA = f"{SCHEMA}/item/report/definition/visualContainer/2.4.0/schema.json"
PAGE_SCHEMA = f"{SCHEMA}/item/report/definition/page/2.0.0/schema.json"
REPORT_SCHEMA = f"{SCHEMA}/item/report/definition/report/3.0.0/schema.json"


def tag(*parts) -> str:
    """Deterministic lineage tag / id."""
    return str(uuid.uuid5(NAMESPACE, ".".join(parts)))


def write(path: Path, text: str) -> None:
    """Write UTF-8 without BOM (required by Power BI project files)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, data: dict) -> None:
    write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# =========================================================================================================
# 1. SEMANTIC MODEL
# =========================================================================================================

# Tables loaded from Parquet, in the order they appear in the model
PARQUET_TABLES = ["fact_orders", "fact_order_items", "dim_customer", "dim_seller", "dim_product",
                  "dim_date", "dim_geography"]

# Columns that are only needed by the model (keys, sort orders) are hidden from the field list
HIDDEN = {
    "fact_orders": {"order_id", "customer_unique_id", "purchase_date", "customer_state", "delay_band_sort",
                    "delivery_outcome_sort", "customer_order_number"},
    "fact_order_items": {"order_id", "order_item_id", "product_id", "seller_id", "purchase_date", "customer_state"},
    "dim_customer": {"customer_unique_id"},
    "dim_seller": {"seller_id"},
    "dim_product": {"product_id"},
    "dim_date": {"month_number", "weekday_number"},
    "coded_reviews": {"sample_id", "delivery_group_sort"},
}

# Text columns that must be sorted by another column instead of alphabetically
SORT_BY = {
    ("fact_orders", "delivery_outcome"): "delivery_outcome_sort",
    ("fact_orders", "delay_band"): "delay_band_sort",
    ("dim_date", "month_name"): "month_number",
    ("dim_date", "weekday_name"): "weekday_number",
    ("coded_reviews", "delivery_group"): "delivery_group_sort",
}

RELATIONSHIPS = [  # (many side, one side)
    ("fact_orders.purchase_date", "dim_date.date_day"),
    ("fact_orders.customer_state", "dim_geography.state_code"),
    ("fact_orders.customer_unique_id", "dim_customer.customer_unique_id"),
    ("fact_order_items.purchase_date", "dim_date.date_day"),
    ("fact_order_items.customer_state", "dim_geography.state_code"),
    ("fact_order_items.product_id", "dim_product.product_id"),
    ("fact_order_items.seller_id", "dim_seller.seller_id"),
]

# DuckDB type -> (TMDL data type, Power Query type)
TYPE_MAP = {
    "VARCHAR": ("string", "type text"),
    "BIGINT": ("int64", "Int64.Type"),
    "INTEGER": ("int64", "Int64.Type"),
    "DOUBLE": ("double", "type number"),
    "DATE": ("dateTime", "type date"),
    "BOOLEAN": ("boolean", "type logical"),
}

CODED_REVIEWS_COLUMNS = [("sample_id", "BIGINT"), ("primary_category", "VARCHAR"),
                         ("secondary_category", "VARCHAR"), ("delivery_outcome", "VARCHAR"),
                         ("delivery_group", "VARCHAR"), ("delivery_group_sort", "BIGINT")]

# ---------------------------------------------------------------------------------------------------------
# Measures: (home table, display folder, name, format string, description, DAX)
# Every measure implements a definition from docs/metric_definitions.md.
# ---------------------------------------------------------------------------------------------------------
MEASURES = [
    # --- volume and value
    ("fact_orders", "1 Volume and value", "Orders", "#,0",
     "Number of orders, all statuses.",
     "COUNTROWS ( fact_orders )"),
    ("fact_orders", "1 Volume and value", "GMV", "#,0",
     "Value of the products ordered, in BRL, without freight.",
     "SUM ( fact_orders[items_value] )"),
    ("fact_orders", "1 Volume and value", "Orders with Items", "#,0",
     "Orders that have item rows; the orders without items have no value.",
     "CALCULATE ( [Orders], fact_orders[has_items] = TRUE () )"),
    ("fact_orders", "1 Volume and value", "Average Order Value", "#,0.00",
     "GMV per order that has items.",
     "DIVIDE ( [GMV], [Orders with Items] )"),
    ("fact_orders", "1 Volume and value", "Freight Share", "0.0%",
     "Freight as a share of what the customer pays (products plus freight). A ratio of totals.",
     "DIVIDE ( SUM ( fact_orders[freight_value] ), SUM ( fact_orders[order_total] ) )"),
    # --- delivery
    ("fact_orders", "2 Delivery", "Delivered Orders", "#,0",
     "Orders that reached the customer and have a delivery date.",
     "CALCULATE ( [Orders], fact_orders[is_delivered] = TRUE () )"),
    ("fact_orders", "2 Delivery", "On-time Orders", "#,0",
     "Orders delivered on or before the promised date.",
     "CALCULATE ( [Orders], fact_orders[delivery_outcome] = \"On time\" )"),
    ("fact_orders", "2 Delivery", "Late Orders", "#,0",
     "Orders delivered after the promised date.",
     "CALCULATE ( [Orders], fact_orders[delivery_outcome] = \"Late\" )"),
    ("fact_orders", "2 Delivery", "Not Delivered Orders", "#,0",
     "Orders that did not end as a delivery.",
     "CALCULATE ( [Orders], fact_orders[delivery_outcome] = \"Not delivered\" )"),
    ("fact_orders", "2 Delivery", "On-time Rate", "0.0%",
     "Share of delivered orders that kept the promised date.",
     "DIVIDE ( [On-time Orders], [Delivered Orders] )"),
    ("fact_orders", "2 Delivery", "Late Rate", "0.0%",
     "Share of delivered orders that arrived after the promised date.",
     "DIVIDE ( [Late Orders], [Delivered Orders] )"),
    ("fact_orders", "2 Delivery", "Not-delivered Rate", "0.0%",
     "Share of all orders that were never delivered.",
     "DIVIDE ( [Not Delivered Orders], [Orders] )"),
    ("fact_orders", "2 Delivery", "Avg Delay (Late)", "0.0",
     "Average number of days late, late orders only.",
     "CALCULATE ( AVERAGE ( fact_orders[delay_days] ), fact_orders[delivery_outcome] = \"Late\" )"),
    ("fact_orders", "2 Delivery", "Median Delay (Late)", "0",
     "Median number of days late, late orders only.",
     "CALCULATE ( MEDIAN ( fact_orders[delay_days] ), fact_orders[delivery_outcome] = \"Late\" )"),
    ("fact_orders", "2 Delivery", "Median Delivery Days", "0",
     "Median number of calendar days from purchase to delivery.",
     "MEDIAN ( fact_orders[delivery_days] )"),
    ("fact_orders", "2 Delivery", "Late Orders Handed Over Late by Seller", "0.0%",
     "Of the late orders, the share that the seller handed to the carrier after the shipping deadline.",
     "DIVIDE (\n    CALCULATE ( [Late Orders], fact_orders[is_seller_handover_late] = TRUE () ),\n    [Late Orders]\n)"),
    ("fact_orders", "2 Delivery", "Late Rate (All States)", "0.0%",
     "The national late rate, ignoring any state or region filter.",
     "CALCULATE ( [Late Rate], REMOVEFILTERS ( dim_geography ) )"),
    ("fact_orders", "9 Formatting", "Colour Late Rate", "",
     "Bar colour: accent when the state is above the national late rate, grey otherwise.",
     f"IF ( [Late Rate] > [Late Rate (All States)], \"{ORANGE}\", \"{GREY}\" )"),
    # --- satisfaction
    ("fact_orders", "3 Satisfaction", "Reviewed Orders", "#,0",
     "Orders that have a review.",
     "CALCULATE ( [Orders], fact_orders[has_review] = TRUE () )"),
    ("fact_orders", "3 Satisfaction", "Avg Review Score", "0.00",
     "Average review score from 1 to 5; orders without a review are ignored.",
     "AVERAGE ( fact_orders[review_score] )"),
    ("fact_orders", "3 Satisfaction", "Low Score Orders", "#,0",
     "Orders with a 1-2 star review.",
     "CALCULATE ( [Orders], fact_orders[is_low_score] = TRUE () )"),
    ("fact_orders", "3 Satisfaction", "Low Score Share", "0.0%",
     "Share of reviewed orders with a 1-2 star review: the main outcome metric.",
     "DIVIDE ( [Low Score Orders], [Reviewed Orders] )"),
    ("fact_orders", "3 Satisfaction", "Comment Share", "0.0%",
     "Share of reviews that include a written comment.",
     "DIVIDE ( CALCULATE ( [Orders], fact_orders[has_comment] = TRUE () ), [Reviewed Orders] )"),
    ("fact_orders", "3 Satisfaction", "Share of Orders", "0.0%",
     "Each delivery outcome's share of all orders.",
     "DIVIDE (\n    [Orders],\n    CALCULATE ( [Orders], REMOVEFILTERS ( fact_orders[delivery_outcome], fact_orders[delivery_outcome_sort] ) )\n)"),
    ("fact_orders", "3 Satisfaction", "Share of Low Score Reviews", "0.0%",
     "Each delivery outcome's share of all 1-2 star reviews.",
     "DIVIDE (\n    [Low Score Orders],\n    CALCULATE ( [Low Score Orders], REMOVEFILTERS ( fact_orders[delivery_outcome], fact_orders[delivery_outcome_sort] ) )\n)"),
    ("fact_orders", "3 Satisfaction", "Low Score Share Single Item", "0.0%",
     "Share of 1-2 star reviews of orders with one item.",
     "CALCULATE ( [Low Score Share], fact_orders[order_size] = \"Single item\" )"),
    ("fact_orders", "3 Satisfaction", "Low Score Share Several Items", "0.0%",
     "Share of 1-2 star reviews of orders with two or more items.",
     "CALCULATE ( [Low Score Share], fact_orders[order_size] = \"Several items\" )"),
    ("fact_orders", "9 Formatting", "Colour Delivery", "",
     "Bar colour: reference colour for on-time orders, accent colour otherwise.",
     f"IF ( SELECTEDVALUE ( fact_orders[delivery_outcome] ) = \"On time\", \"{BLUE}\", \"{ORANGE}\" )"),
    ("fact_orders", "9 Formatting", "Title Overview", "",
     "Page 1 headline that updates with the filters.",
     "VAR ProblemOrders =\n    DIVIDE ( [Late Orders] + [Not Delivered Orders], [Orders] )\n"
     "VAR ProblemReviews =\n    DIVIDE (\n        CALCULATE ( [Low Score Orders], fact_orders[delivery_outcome] IN { \"Late\", \"Not delivered\" } ),\n"
     "        [Low Score Orders]\n    )\nRETURN\n"
     "    \"Late and undelivered orders are \" & FORMAT ( ProblemOrders, \"0.0%\" )\n"
     "        & \" of orders but account for \" & FORMAT ( ProblemReviews, \"0%\" )\n"
     "        & \" of all 1-2 star reviews\""),
    # --- customers (whole period)
    ("dim_customer", "4 Customers", "Customers", "#,0",
     "Number of people (customer_unique_id) with an order in the period.",
     "COUNTROWS ( dim_customer )"),
    ("dim_customer", "4 Customers", "Repeat Customers", "#,0",
     "People who ordered on more than one day.",
     "CALCULATE ( [Customers], dim_customer[is_repeat_customer] = TRUE () )"),
    ("dim_customer", "4 Customers", "Repeat Purchase Rate", "0.00%",
     "Share of customers who came back on a later day. Whole period only.",
     "DIVIDE ( [Repeat Customers], [Customers] )"),
    # --- sellers and categories (item level: one order has several rows, so orders are distinct counts)
    ("fact_order_items", "5 Sellers and categories", "Item GMV", "#,0",
     "Value of the items sold, in BRL.",
     "SUM ( fact_order_items[price] )"),
    ("fact_order_items", "5 Sellers and categories", "Item Orders", "#,0",
     "Orders that contain at least one item of the seller or category.",
     "DISTINCTCOUNT ( fact_order_items[order_id] )"),
    ("fact_order_items", "5 Sellers and categories", "Item Delivered Orders", "#,0",
     "Delivered orders that contain the seller or category.",
     "CALCULATE ( [Item Orders], fact_order_items[is_delivered] = TRUE () )"),
    ("fact_order_items", "5 Sellers and categories", "Item Late Orders", "#,0",
     "Late orders that contain the seller or category.",
     "CALCULATE ( [Item Orders], fact_order_items[delivery_outcome] = \"Late\" )"),
    ("fact_order_items", "5 Sellers and categories", "Item Late Rate", "0.0%",
     "Late rate of a seller or category.",
     "DIVIDE ( [Item Late Orders], [Item Delivered Orders] )"),
    ("fact_order_items", "5 Sellers and categories", "Item Reviewed Orders", "#,0",
     "Reviewed orders that contain the seller or category.",
     "CALCULATE ( [Item Orders], fact_order_items[has_review] = TRUE () )"),
    ("fact_order_items", "5 Sellers and categories", "Item Low Score Orders", "#,0",
     "Orders with a 1-2 star review that contain the seller or category.",
     "CALCULATE ( [Item Orders], fact_order_items[is_low_score] = TRUE () )"),
    ("fact_order_items", "5 Sellers and categories", "Item Low Score Share", "0.0%",
     "Share of 1-2 star reviews of a seller or category.",
     "DIVIDE ( [Item Low Score Orders], [Item Reviewed Orders] )"),
    ("fact_order_items", "5 Sellers and categories", "Item Avg Review Score", "0.00",
     "Average score of a seller or category: one score per order, then the average of the orders.",
     "AVERAGEX (\n    VALUES ( fact_order_items[order_id] ),\n    CALCULATE ( MAX ( fact_order_items[review_score] ) )\n)"),
    ("fact_order_items", "5 Sellers and categories", "Low Score Share (All Categories)", "0.0%",
     "The overall share of 1-2 star reviews on item level, ignoring the category.",
     "CALCULATE ( [Item Low Score Share], REMOVEFILTERS ( dim_product ) )"),
    # --- review coding (sample of 300, deliberately not related to the rest of the model)
    ("coded_reviews", "6 Review coding", "Coded Reviews", "#,0",
     "Number of coded 1-2 star reviews in the sample.",
     "COUNTROWS ( coded_reviews )"),
    ("coded_reviews", "6 Review coding", "Complaint Share", "0%",
     "Share of a complaint category inside the delivery group shown.",
     "DIVIDE (\n    [Coded Reviews],\n    CALCULATE ( [Coded Reviews], REMOVEFILTERS ( coded_reviews[primary_category] ) )\n)"),
]


def q(name: str) -> str:
    """Quote a TMDL object name when it contains characters other than letters, digits and underscores."""
    return name if name.replace("_", "").isalnum() else "'" + name.replace("'", "''") + "'"


def table_columns() -> dict:
    """Read column names and types of the exported model tables from DuckDB."""
    con = duckdb.connect(str(ROOT / "data" / "processed" / "olist.duckdb"), read_only=True)
    columns = {}
    for table in PARQUET_TABLES:
        rows = con.execute(f"DESCRIBE model.{table}").fetchall()
        columns[table] = [(r[0], "DOUBLE" if r[1].startswith("DECIMAL") else r[1]) for r in rows]
    con.close()
    columns["coded_reviews"] = CODED_REVIEWS_COLUMNS
    return columns


def m_source(table: str, cols: list) -> str:
    """Power Query (M) expression that loads one table with explicit column types."""
    types = ", ".join(f'{{"{c}", {TYPE_MAP[t][1]}}}' for c, t in cols)
    if table == "coded_reviews":
        names = ", ".join(f'"{c}"' for c, _ in cols)
        return (
            "let\n"
            '    Source = Csv.Document(File.Contents(DataFolder & "review_coding\\coded_reviews.csv"), '
            '[Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),\n'
            "    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),\n"
            "    // the file starts with a byte order mark: name the first column explicitly\n"
            '    FirstColumn = Table.RenameColumns(Headers, {{Table.ColumnNames(Headers){0}, "sample_id"}}),\n'
            f"    Selected = Table.SelectColumns(FirstColumn, {{{names}}}),\n"
            f"    Typed = Table.TransformColumnTypes(Selected, {{{types}}})\n"
            "in\n"
            "    Typed"
        )
    return (
        "let\n"
        f'    Source = Parquet.Document(File.Contents(DataFolder & "data\\processed\\{table}.parquet")),\n'
        f"    Typed = Table.TransformColumnTypes(Source, {{{types}}})\n"
        "in\n"
        "    Typed"
    )


def indent(text: str, tabs: int) -> str:
    return "\n".join(("\t" * tabs + line) if line.strip() else "" for line in text.split("\n"))


def table_tmdl(table: str, cols: list) -> str:
    lines = [f"table {table}", f"\tlineageTag: {tag(table)}", ""]
    if table == "dim_date":
        lines.insert(1, "\tdataCategory: Time")
    for home, folder, name, fmt, desc, dax in MEASURES:
        if home != table:
            continue
        lines.append(f"\t/// {desc}")
        if "\n" in dax:
            lines.append(f"\tmeasure {q(name)} =")
            lines.append(indent(dax, 3))
        else:
            lines.append(f"\tmeasure {q(name)} = {dax}")
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines.append(f"\t\tdisplayFolder: {folder}")
        lines.append(f"\t\tlineageTag: {tag(table, 'measure', name)}")
        lines.append("")
    for col, dtype in cols:
        tmdl_type = TYPE_MAP[dtype][0]
        lines.append(f"\tcolumn {col}")
        lines.append(f"\t\tdataType: {tmdl_type}")
        if tmdl_type == "dateTime":
            lines.append("\t\tformatString: yyyy-mm-dd")
        if table == "dim_date" and col == "date_day":
            lines.append("\t\tisKey")
        if col in HIDDEN.get(table, set()):
            lines.append("\t\tisHidden")
        lines.append(f"\t\tlineageTag: {tag(table, col)}")
        lines.append("\t\tsummarizeBy: none")
        lines.append(f"\t\tsourceColumn: {col}")
        if (table, col) in SORT_BY:
            lines.append(f"\t\tsortByColumn: {SORT_BY[(table, col)]}")
        lines.append("")
        if tmdl_type == "dateTime":
            lines.append("\t\tannotation UnderlyingDateTimeDataType = Date")
            lines.append("")
    lines.append(f"\tpartition {table} = m")
    lines.append("\t\tmode: import")
    lines.append("\t\tsource =")
    lines.append(indent(m_source(table, cols), 4))
    lines.append("")
    lines.append("\tannotation PBI_ResultType = Table")
    lines.append("")
    return "\n".join(lines)


def build_model(columns: dict) -> None:
    if MODEL_DIR.exists():
        # keep the local data cache if there is one, rewrite the definition
        shutil.rmtree(MODEL_DIR / "definition", ignore_errors=True)
    definition = MODEL_DIR / "definition"
    write_json(MODEL_DIR / "definition.pbism", {
        "$schema": f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.0",
        "settings": {},
    })
    write(definition / "database.tmdl", "database\n\tcompatibilityLevel: 1600\n")
    tables = list(columns)
    query_order = json.dumps(["DataFolder"] + tables)
    write(definition / "model.tmdl", "\n".join([
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "\tsourceQueryCulture: en-US",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        f"annotation PBI_QueryOrder = {query_order}",
        "",
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        *[f"ref table {t}" for t in tables],
        "",
    ]))
    data_folder = str(ROOT) + "\\"
    write(definition / "expressions.tmdl", "\n".join([
        f'expression DataFolder = "{data_folder}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
        f"\tlineageTag: {tag('DataFolder')}",
        "",
        "\tannotation PBI_ResultType = Text",
        "",
    ]))
    rel_lines = []
    for many, one in RELATIONSHIPS:
        rel_lines += [f"relationship {tag('rel', many, one)}", f"\tfromColumn: {many}", f"\ttoColumn: {one}", ""]
    write(definition / "relationships.tmdl", "\n".join(rel_lines))
    for table, cols in columns.items():
        write(definition / "tables" / f"{table}.tmdl", table_tmdl(table, cols))


def build_measures_dax() -> None:
    """Write the measures as one readable DAX file (generated from MEASURES)."""
    lines = [
        "// =====================================================================================================",
        "// DAX measures of the Olist delivery and satisfaction dashboard",
        "// Generated by dashboard/build_pbip.py from the same list that builds the semantic model.",
        "// Every measure implements a definition from docs/metric_definitions.md; with no filter applied it must",
        "// show the value in dashboard/reference_values.md.",
        "//",
        "// Rules behind the formulas:",
        "//   1. Rates are DIVIDE(numerator, denominator) of totals, never an average of row-level ratios.",
        "//   2. DIVIDE returns blank instead of an error when the denominator is 0.",
        "//   3. On fact_order_items one order has several rows, so orders are counted with DISTINCTCOUNT.",
        "// =====================================================================================================",
    ]
    current = None
    for home, folder, name, fmt, desc, dax in MEASURES:
        if folder != current:
            lines += ["", f"// ---- {folder[2:]} " + "-" * (90 - len(folder)), ""]
            current = folder
        lines.append(f"// {desc}" + (f"   Format: {fmt}" if fmt else "") + f"   Table: {home}")
        lines.append(f"{name} =" + ("\n" + indent(dax, 1) if "\n" in dax else f" {dax}"))
        lines.append("")
    write(OUT / "measures.dax", "\n".join(lines))


# =========================================================================================================
# 2. REPORT
# =========================================================================================================

MEASURE_HOME = {name: home for home, _, name, _, _, _ in MEASURES}


def lit(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def text(value: str) -> dict:
    return lit("'" + value.replace("'", "''") + "'")


def fld(name: str, table: str = None) -> dict:
    """Field reference: a measure (looked up by name) or a column (table.column)."""
    if table is None and name in MEASURE_HOME:
        return {"Measure": {"Expression": {"SourceRef": {"Entity": MEASURE_HOME[name]}}, "Property": name}}
    table, column = (table, name) if table else name.split(".", 1)
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}}


def proj(name: str, display: str = None) -> dict:
    f = fld(name)
    kind = next(iter(f))
    entity = f[kind]["Expression"]["SourceRef"]["Entity"]
    prop = f[kind]["Property"]
    p = {"field": f, "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}
    if display:
        p["displayName"] = display
    return p


def ref_in_filter(name: str) -> dict:
    """Field reference inside a filter condition (uses the alias of the From clause)."""
    f = fld(name)
    kind = next(iter(f))
    return {kind: {"Expression": {"SourceRef": {"Source": "t"}}, "Property": f[kind]["Property"]}}, \
        f[kind]["Expression"]["SourceRef"]["Entity"]


def filter_min(vname: str, measure: str, minimum: int) -> dict:
    expr, entity = ref_in_filter(measure)
    return {
        "name": f"{vname}_min",
        "field": fld(measure),
        "type": "Advanced",
        "filter": {
            "Version": 2,
            "From": [{"Name": "t", "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"Comparison": {
                "ComparisonKind": 2, "Left": expr, "Right": {"Literal": {"Value": f"{minimum}L"}}}}}],
        },
    }


def filter_exclude(vname: str, column: str, values: list, suffix: str = "excl") -> dict:
    expr, entity = ref_in_filter(column)
    return {
        "name": f"{vname}_{suffix}",
        "field": fld(column),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": "t", "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"Not": {"Expression": {"In": {
                "Expressions": [expr],
                "Values": [[{"Literal": {"Value": "'" + v + "'"}}] for v in values]}}}}}],
        },
    }


def title_objects(title: str, subtitle: str = None) -> dict:
    vco = {"title": [{"properties": {"show": lit("true"), "text": text(title), "titleWrap": lit("true")}}]}
    if subtitle:
        vco["subTitle"] = [{"properties": {"show": lit("true"), "text": text(subtitle)}}]
    return vco


def color(hex_code: str) -> dict:
    return {"solid": {"color": text(hex_code)}}


def series_colors(colors: dict) -> list:
    """dataPoint fill per measure series."""
    out = []
    for measure, hex_code in colors.items():
        f = fld(measure)
        kind = next(iter(f))
        out.append({"properties": {"fill": color(hex_code)},
                    "selector": {"metadata": f"{f[kind]['Expression']['SourceRef']['Entity']}.{measure}"}})
    return out


def measure_color(measure: str) -> list:
    """dataPoint fill taken from a measure that returns a colour code (conditional formatting)."""
    return [{"properties": {"fill": {"solid": {"color": {"expr": fld(measure)}}}},
             "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}]


def sort(name: str, direction: str = "Ascending") -> dict:
    return {"sort": [{"field": fld(name), "direction": direction}], "isDefaultSort": False}


def visual(page: str, vname: str, vtype: str, box: tuple, query: dict = None, objects: dict = None,
           vco: dict = None, sort_def: dict = None, filters: list = None, z: int = 0, sync: str = None) -> None:
    x, y, w, h = box
    v = {"visualType": vtype}
    if query:
        v["query"] = {"queryState": {role: {"projections": projs} for role, projs in query.items()}}
        if sort_def:
            v["query"]["sortDefinition"] = sort_def
    if objects:
        v["objects"] = objects
    if vco:
        v["visualContainerObjects"] = vco
    if sync:
        v["syncGroup"] = {"groupName": sync, "fieldChanges": True, "filterChanges": True}
    v["drillFilterOtherVisuals"] = True
    container = {
        "$schema": VISUAL_SCHEMA,
        "name": vname,
        "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
        "visual": v,
    }
    if filters:
        container["filterConfig"] = {"filters": filters}
    write_json(REPORT_DIR / "definition" / "pages" / page / "visuals" / vname / "visual.json", container)


def textbox(page: str, vname: str, box: tuple, title: str, size: str = "14pt") -> None:
    x, y, w, h = box
    container = {
        "$schema": VISUAL_SCHEMA,
        "name": vname,
        "position": {"x": x, "y": y, "z": 0, "height": h, "width": w, "tabOrder": 0},
        "visual": {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [
                {"textRuns": [{"value": title, "textStyle": {"fontWeight": "bold", "fontSize": size}}]}]}}]},
            "drillFilterOtherVisuals": True,
        },
    }
    write_json(REPORT_DIR / "definition" / "pages" / page / "visuals" / vname / "visual.json", container)


def card(page: str, vname: str, box: tuple, measure: str, label: str = None, millions: bool = False,
         z: int = 1) -> None:
    """One KPI card. Numbers are shown in full unless millions=True (one decimal, e.g. 13.5M)."""
    properties = {"labelDisplayUnits": lit("1000000D"), "labelPrecision": lit("1L")} if millions \
        else {"labelDisplayUnits": lit("1D")}
    visual(page, vname, "card", box, query={"Values": [proj(measure, label)]},
           objects={"labels": [{"properties": properties}]}, z=z)


def slicers(page: str) -> None:
    for i, (vname, column, label) in enumerate([("slicer_year", "dim_date.year", "Year"),
                                                ("slicer_region", "dim_geography.region", "Customer region")]):
        visual(page, vname, "slicer", (930 + i * 170, 4, 160, 54),
               query={"Values": [proj(column, label)]},
               objects={"data": [{"properties": {"mode": text("Dropdown")}}]},
               z=10 + i, sync=vname)


def page(name: str, display: str, no_filter_targets: list = None) -> None:
    """Page file. no_filter_targets: visuals that the slicers must not filter."""
    data = {
        "$schema": PAGE_SCHEMA,
        "name": name,
        "displayName": display,
        "displayOption": "FitToPage",
        "height": 720,
        "width": 1280,
    }
    if no_filter_targets:
        data["visualInteractions"] = [{"source": s, "target": t, "type": "NoFilter"}
                                      for t in no_filter_targets for s in ("slicer_year", "slicer_region")]
    write_json(REPORT_DIR / "definition" / "pages" / name / "page.json", data)


def build_report() -> None:
    shutil.rmtree(REPORT_DIR / "definition", ignore_errors=True)
    shutil.rmtree(REPORT_DIR / "StaticResources", ignore_errors=True)
    write_json(REPORT_DIR / "definition.pbir", {
        "$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
    })
    d = REPORT_DIR / "definition"
    write_json(d / "version.json", {
        "$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })
    theme_name = "OlistTheme.json"
    resources = REPORT_DIR / "StaticResources" / "RegisteredResources"
    resources.mkdir(parents=True, exist_ok=True)
    shutil.copy(OUT / "theme.json", resources / theme_name)
    write_json(d / "report.json", {
        "$schema": REPORT_SCHEMA,
        "themeCollection": {"customTheme": {
            "name": theme_name,
            "reportVersionAtImport": {"visual": "2.4.0", "report": "3.0.0", "page": "2.0.0"},
            "type": "RegisteredResources"}},
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                              "items": [{"name": theme_name, "path": theme_name, "type": "CustomTheme"}]}],
    })
    pages = ["overview", "delivery", "satisfaction"]
    write_json(d / "pages" / "pages.json", {
        "$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": pages,
        "activePageName": pages[0],
    })

    # Layout grid (pixels on a 1280 x 720 page)
    L, GAP, TOP_CARDS, CARD_H, ROW1, ROW1_H, ROW2, ROW2_H = 24, 12, 62, 84, 156, 262, 430, 274
    HALF = (1280 - 2 * L - GAP) // 2

    def cards_row(pg: str, measures: list) -> None:
        n = len(measures)
        width = (1280 - 2 * L - (n - 1) * GAP) // n
        for i, (m, label, millions) in enumerate(measures):
            card(pg, f"card_{i + 1}", (L + i * (width + GAP), TOP_CARDS, width, CARD_H), m, label, millions, z=1 + i)

    # ------------------------------------------------------------------ page 1: executive overview
    pg = "overview"
    page(pg, "Executive overview")
    textbox(pg, "page_title", (L, 10, 890, 46),
            "Late and undelivered orders are 9.5% of orders but account for 43% of all bad reviews")
    slicers(pg)
    cards_row(pg, [("Orders", None, False), ("GMV", "GMV (BRL)", True), ("On-time Rate", None, False),
                   ("Not-delivered Rate", None, False), ("Avg Review Score", None, False),
                   ("Low Score Share", "1-2 star share", False)])
    visual(pg, "orders_by_month", "clusteredColumnChart", (L, ROW1, HALF, ROW1_H),
           query={"Category": [proj("dim_date.year_month", "Purchase month")], "Y": [proj("Orders")]},
           sort_def=sort("dim_date.year_month"),
           objects={"dataPoint": [{"properties": {"fill": color(GREY)}}]},
           vco=title_objects("Monthly orders grew from 800 in January 2017 to more than 6,000 in every month of 2018",
                             "Orders by purchase month"), z=20)
    visual(pg, "late_and_low_by_month", "lineChart", (L + HALF + GAP, ROW1, HALF, ROW1_H),
           query={"Category": [proj("dim_date.year_month", "Purchase month")],
                  "Y": [proj("Late Rate"), proj("Low Score Share", "1-2 star share")]},
           sort_def=sort("dim_date.year_month"),
           objects={"dataPoint": series_colors({"Late Rate": ORANGE, "Low Score Share": BLUE}),
                    "legend": [{"properties": {"show": lit("true"), "position": text("Top")}}]},
           vco=title_objects("Bad reviews peak in the same three months as late deliveries",
                             "Late rate and share of 1-2 star reviews by purchase month"), z=21)
    visual(pg, "share_by_outcome", "clusteredBarChart", (L, ROW2, 1280 - 2 * L, ROW2_H),
           query={"Category": [proj("fact_orders.delivery_outcome", "Delivery outcome")],
                  "Y": [proj("Share of Orders", "Share of all orders"),
                        proj("Share of Low Score Reviews", "Share of all 1-2 star reviews")]},
           sort_def=sort("fact_orders.delivery_outcome"),
           objects={"dataPoint": series_colors({"Share of Orders": BLUE, "Share of Low Score Reviews": ORANGE}),
                    "labels": [{"properties": {"show": lit("true")}}],
                    "legend": [{"properties": {"show": lit("true"), "position": text("Top")}}]},
           vco=title_objects("Late and undelivered orders: 9.5% of orders, 43% of bad reviews",
                             "Each delivery outcome's share of all orders and of all 1-2 star reviews"),
           filters=[filter_exclude("share_by_outcome", "fact_orders.delivery_outcome", ["Unknown"])], z=22)

    # ------------------------------------------------------------------ page 2: delivery performance
    pg = "delivery"
    page(pg, "Delivery performance")
    textbox(pg, "page_title", (L, 10, 890, 46),
            "Rio de Janeiro has 13% of orders but 23% of late deliveries; most delays arise in transit")
    slicers(pg)
    cards_row(pg, [("Late Rate", None, False), ("Late Orders", None, False),
                   ("Median Delivery Days", "Median delivery days", False),
                   ("Avg Delay (Late)", "Avg days late", False),
                   ("Late Orders Handed Over Late by Seller", "Late: seller shipped late", False)])
    visual(pg, "late_rate_by_state", "clusteredBarChart", (L, ROW1, HALF, 720 - ROW1 - 16),
           query={"Category": [proj("dim_geography.state_name", "Customer state")], "Y": [proj("Late Rate")]},
           sort_def=sort("Late Rate", "Descending"),
           objects={"dataPoint": measure_color("Colour Late Rate"),
                    "labels": [{"properties": {"show": lit("true"), "fontSize": lit("8D")}}],
                    "categoryAxis": [{"properties": {"preferredCategoryWidth": lit("10D"), "fontSize": lit("8D"),
                                                     "innerPadding": lit("20D")}}],
                    # the bars are labelled with their value, so the value axis is not needed
                    "valueAxis": [{"properties": {"show": lit("false")}}]},
           vco=title_objects("Late rates are highest in the Northeast and in Rio de Janeiro",
                             "Late rate by customer state, states with 300+ orders. Orange: above the national rate"),
           filters=[filter_min("late_rate_by_state", "Orders", 300)], z=20)
    visual(pg, "late_by_band", "clusteredColumnChart", (L + HALF + GAP, ROW1, HALF, 200),
           query={"Category": [proj("fact_orders.delay_band", "Days late")], "Y": [proj("Orders")]},
           sort_def=sort("fact_orders.delay_band"),
           objects={"dataPoint": [{"properties": {"fill": color(ORANGE)}}],
                    "labels": [{"properties": {"show": lit("true"), "labelDisplayUnits": lit("1D")}}]},
           vco=title_objects("Late orders are spread fairly evenly from 1 to more than 15 days late",
                             "Late orders by number of days after the promised date"),
           filters=[filter_exclude("late_by_band", "fact_orders.delay_band",
                                   ["On time", "Not delivered", "Unknown"])], z=21)
    visual(pg, "seller_ranking", "tableEx", (L + HALF + GAP, ROW1 + 212, HALF, 720 - ROW1 - 212 - 16),
           query={"Values": [proj("dim_seller.seller_short", "Seller"), proj("dim_seller.seller_state", "State"),
                             proj("Item Orders", "Orders"), proj("Item Late Orders", "Late orders"),
                             proj("Item Late Rate", "Late rate"), proj("Item Low Score Share", "1-2 star share")]},
           sort_def=sort("Item Late Orders", "Descending"),
           vco=title_objects("The ten sellers with the most late orders are all large São Paulo sellers",
                             "Sellers with 30+ orders, ranked by number of late orders"),
           filters=[filter_min("seller_ranking", "Item Orders", 30)], z=22)

    # ------------------------------------------------------------------ page 3: customer satisfaction
    pg = "satisfaction"
    # the coded sample is not related to the model, so the slicers must not try to filter it
    page(pg, "Customer satisfaction", no_filter_targets=["complaints"])
    textbox(pg, "page_title", (L, 10, 890, 46),
            "On-time orders with several items get 1-2 stars more than three times as often as single-item orders")
    slicers(pg)
    cards_row(pg, [("Avg Review Score", None, False), ("Low Score Share", "1-2 star share", False),
                   ("Comment Share", None, False), ("Coded Reviews", "Coded reviews (sample)", False)])
    visual(pg, "low_by_band", "clusteredColumnChart", (L, ROW1, HALF, ROW1_H),
           query={"Category": [proj("fact_orders.delay_band", "Delivery outcome")],
                  "Y": [proj("Low Score Share", "1-2 star share")]},
           sort_def=sort("fact_orders.delay_band"),
           objects={"dataPoint": measure_color("Colour Delivery"),
                    "labels": [{"properties": {"show": lit("true")}}]},
           vco=title_objects("Bad reviews jump from 9% for on-time orders to 68% once an order is 4-7 days late",
                             "Share of reviewed orders with a 1-2 star review"),
           filters=[filter_exclude("low_by_band", "fact_orders.delay_band", ["Unknown"])], z=20)
    visual(pg, "low_by_size", "clusteredBarChart", (L + HALF + GAP, ROW1, HALF, ROW1_H),
           query={"Category": [proj("fact_orders.delivery_outcome", "Delivery outcome")],
                  "Y": [proj("Low Score Share Single Item", "Single item"),
                        proj("Low Score Share Several Items", "Several items")]},
           sort_def=sort("fact_orders.delivery_outcome"),
           objects={"dataPoint": series_colors({"Low Score Share Single Item": BLUE,
                                                "Low Score Share Several Items": ORANGE}),
                    "labels": [{"properties": {"show": lit("true")}}],
                    "legend": [{"properties": {"show": lit("true"), "position": text("Top")}}]},
           vco=title_objects("Even when delivered on time, orders with several items get 25% bad reviews, against 7.5% for single items",
                             "Share of 1-2 star reviews by delivery outcome and order size"),
           filters=[filter_exclude("low_by_size", "fact_orders.delivery_outcome", ["Unknown"])], z=21)
    visual(pg, "complaints", "pivotTable", (L, ROW2, HALF, ROW2_H),
           query={"Rows": [proj("coded_reviews.primary_category", "Complaint")],
                  "Columns": [proj("coded_reviews.delivery_group", "Delivery group")],
                  "Values": [proj("Complaint Share")]},
           objects={"values": [{
               "properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {
                   "Input": fld("Complaint Share"),
                   "FillRule": {"linearGradient2": {
                       "min": {"color": {"Literal": {"Value": "'#FFFFFF'"}}},
                       "max": {"color": {"Literal": {"Value": f"'{ORANGE}'"}}},
                       "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}}}}}}}}}},
               "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                            "metadata": "coded_reviews.Complaint Share"}},
               {"properties": {"fontSize": lit("8D")}}],
               "columnHeaders": [{"properties": {"fontSize": lit("8D")}}],
               "rowHeaders": [{"properties": {"fontSize": lit("8D")}}],
               "subTotals": [{"properties": {"rowSubtotals": lit("false"), "columnSubtotals": lit("false")}}]},
           vco=title_objects("Several-item orders delivered on time: 81% of complaints are about a missing part",
                             "Sample of 300 coded 1-2 star reviews; share within each delivery group; slicers do not apply"),
           z=22)
    visual(pg, "category_matrix", "scatterChart", (L + HALF + GAP, ROW2, HALF, ROW2_H),
           query={"Category": [proj("dim_product.category_en", "Category")],
                  "X": [proj("Item GMV", "GMV (BRL)")],
                  "Y": [proj("Item Low Score Share", "1-2 star share")]},
           objects={"dataPoint": [{"properties": {"fill": color(GREY)}}],
                    "categoryLabels": [{"properties": {"show": lit("true")}}]},
           vco=title_objects("Office furniture has the highest share of bad reviews; large categories sit close to the average",
                             "Categories with 500+ orders: GMV vs share of 1-2 star reviews"),
           filters=[filter_min("category_matrix", "Item Orders", 500),
                    filter_exclude("category_matrix", "dim_product.category_en", ["unknown"])], z=23)



def build_project_file() -> None:
    write_json(OUT / f"{NAME}.pbip", {
        "$schema": f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })
    write(OUT / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")


if __name__ == "__main__":
    cols = table_columns()
    build_model(cols)
    build_measures_dax()
    build_report()
    build_project_file()
    print(f"Power BI project written to {OUT.relative_to(ROOT)}\\{NAME}.pbip")
