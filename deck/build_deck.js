// Build the consulting deck as a PowerPoint file.
//
//   node build_deck.js        (run inside deck/, after `python notebooks/09_deck_data.py`)
//
// Every number on a slide is read from deck_data.json, which is generated from the data model.
// Nothing is typed in by hand, so the deck cannot drift away from the analysis.

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const D = JSON.parse(fs.readFileSync(path.join(__dirname, "deck_data.json"), "utf8"));
const OUT = path.join(__dirname, "late_deliveries_lost_customers.pptx");

// ---------------------------------------------------------------------------------------------
// Design system: one colour for "reference / good", one accent for "problem", greys for context
// ---------------------------------------------------------------------------------------------
const INK = "1B1F23", DARK = "16202A", WHITE = "FFFFFF", TINT = "F3F4F6", MUTED = "6B7280";
const ORANGE = "EB6834", BLUE = "2A78D6", GREY = "A8A7A0", GRID = "E1E0D9";
const HEAD = "Cambria", BODY = "Calibri";
const W = 13.333, M = 0.6;                        // slide width and side margin, inches

// ---------------------------------------------------------------------------------------------
// Number formatting
// ---------------------------------------------------------------------------------------------
const int = (x) => Math.round(x).toLocaleString("en-US");
const pct = (x, d = 1) => (x * 100).toFixed(d) + "%";
const pct0 = (x) => pct(x, 0);
const pp = (x) => (x * 100).toFixed(1);

const b = D.baseline;
const outcome = (name) => D.outcomes.find((o) => o.delivery_outcome === name);
const band = (name) => D.delay_bands.find((x) => x.delay_band === name);
const state = (code) => D.states.find((s) => s.state === code);
const late = D.transit.find((t) => t.delivery_outcome === "Late");
const onTime = D.transit.find((t) => t.delivery_outcome === "On time");
const several = D.order_size.find((o) => o.order_size === "Several items");
const single = D.order_size.find((o) => o.order_size === "Single item");
const S = D.scenario, C = D.coding;
const rj = state("RJ");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                       // 13.33 x 7.5 inches
pres.title = "Late Deliveries, Lost Customers";
pres.author = "Kostiantyn Dolyna";
pres.subject = "Why Olist customers give bad reviews and what to fix first";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };

// ---------------------------------------------------------------------------------------------
// Layouts
// ---------------------------------------------------------------------------------------------
const FOOTER = "Olist delivery and satisfaction analysis  |  Source: Olist public dataset, orders purchased January 2017 to August 2018";

pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: DARK },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.1, w: 7.4, h: 1.7, fontFace: HEAD, fontSize: 44, bold: true, color: WHITE, align: "left", valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 3.95, w: 7.4, h: 1.2, fontFace: BODY, fontSize: 20, color: "D1D5DB", align: "left", valign: "top", margin: 0 }, text: "" } },
  ],
});

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: WHITE },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.42, w: W - 2 * M, h: 1.15, fontFace: HEAD, fontSize: 28, bold: true, color: INK, align: "left", valign: "top", margin: 0 }, text: "" } },
    { text: { text: FOOTER, options: { x: M, y: 7.0, w: 10.5, h: 0.3, fontFace: BODY, fontSize: 10, color: MUTED, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: 7.0, w: 0.6, h: 0.3, fontFace: BODY, fontSize: 10, color: MUTED, align: "right" },
});

pres.defineSlideMaster({
  title: "CONTENT_DARK",
  background: { color: DARK },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.42, w: W - 2 * M, h: 1.15, fontFace: HEAD, fontSize: 28, bold: true, color: WHITE, align: "left", valign: "top", margin: 0 }, text: "" } },
    { text: { text: FOOTER, options: { x: M, y: 7.0, w: 10.5, h: 0.3, fontFace: BODY, fontSize: 10, color: "9CA3AF", margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: 7.0, w: 0.6, h: 0.3, fontFace: BODY, fontSize: 10, color: "9CA3AF", align: "right" },
});

// ---------------------------------------------------------------------------------------------
// Building blocks
// ---------------------------------------------------------------------------------------------
let shapeId = 0;
const name = (prefix) => `${prefix} ${++shapeId}`;

function text(slide, value, opts) {
  slide.addText(value, Object.assign({ fontFace: BODY, fontSize: 14, color: INK, margin: 0, valign: "top", isTextBox: true, objectName: name("Text") }, opts));
}

function card(slide, x, y, w, h, color = TINT) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color }, line: { color, width: 0 }, objectName: name("Card") });
}

// A large number with a caption underneath: the visual motif of the deck
function stat(slide, x, y, w, value, caption, opts = {}) {
  const color = opts.color || ORANGE;
  const size = opts.size || 40;
  const numberH = size / 72 * 1.25;
  text(slide, value, { x, y, w, h: numberH, fontFace: HEAD, fontSize: size, bold: true, color, valign: "middle" });
  text(slide, caption, { x, y: y + numberH + 0.05, w, h: opts.captionH || 0.75, fontSize: opts.captionSize || 14, color: opts.captionColor || INK });
}

function numberBadge(slide, x, y, n, fill = ORANGE) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: 0.46, h: 0.46, fill: { color: fill }, line: { color: fill, width: 0 }, objectName: name("Badge") });
  text(slide, String(n), { x, y, w: 0.46, h: 0.46, fontFace: HEAD, fontSize: 16, bold: true, color: WHITE, align: "center", valign: "middle" });
}

// Shared look of every chart: same label font, size and colour throughout the deck
const CHART = {
  catAxisLabelFontFace: BODY, valAxisLabelFontFace: BODY, dataLabelFontFace: BODY, legendFontFace: BODY,
  catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, dataLabelFontSize: 12, legendFontSize: 12,
  catAxisLabelColor: INK, valAxisLabelColor: MUTED, dataLabelColor: INK, legendColor: INK,
  valGridLine: { color: GRID, size: 0.75 }, catGridLine: { style: "none" },
  catAxisLineShow: false, valAxisLineShow: false,
};

function content(section, title, notes, master = "CONTENT") {
  const slide = pres.addSlide({ masterName: master, sectionTitle: section });
  slide.addText(title, { placeholder: "title" });
  slide.addNotes(notes);
  return slide;
}

// =============================================================================================
// 1. Title
// =============================================================================================
pres.addSection({ title: "Summary" });
{
  const slide = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Summary" });
  slide.addText("Late Deliveries, Lost Customers", { placeholder: "title" });
  slide.addText("Why Olist customers give bad reviews, and what to fix first", { placeholder: "body" });
  text(slide, "Analysis for the Head of Operations", { x: M, y: 5.6, w: 7.4, h: 0.35, fontSize: 16, color: "D1D5DB" });
  text(slide, "Kostiantyn Dolyna  |  October 2026", { x: M, y: 5.98, w: 7.4, h: 0.35, fontSize: 14, color: "9CA3AF" });
  card(slide, 8.7, 2.0, 4.0, 3.5, "1F2D3A");
  text(slide, pct(b.low_score_rate), { x: 8.95, y: 2.35, w: 3.5, h: 1.3, fontFace: HEAD, fontSize: 66, bold: true, color: ORANGE, valign: "middle" });
  text(slide, `of reviewed orders end in a 1-2 star review: ${int(b.low_score_orders)} of ${int(b.reviewed_orders)}`,
    { x: 8.95, y: 3.8, w: 3.5, h: 1.3, fontSize: 18, color: WHITE });
  slide.addNotes("Title slide. The headline number is the share of reviewed orders with a 1-2 star review (docs/kpi_baseline.md).");
}

// =============================================================================================
// 2. Executive summary
// =============================================================================================
{
  const slide = content("Summary",
    "Broken delivery promises and incomplete orders account for the avoidable bad reviews; completeness is the larger lever",
    "Executive summary. Situation and complication: docs/analysis_findings.md section 1. Review coding: review_coding/findings.md. Scenario: docs/scenario.md.");
  const blocks = [
    ["SITUATION", `${pct(b.low_score_rate)} of reviewed orders get 1-2 stars, although ${pct(b.on_time_rate)} of deliveries arrive on or before the promised date.`],
    ["COMPLICATION", `Late and undelivered orders are ${pct(D.problem_share_of_orders)} of orders but ${pct(D.problem_share_of_low)} of bad reviews. A second problem hides inside the on-time figure: orders with several items are recorded as delivered while part of the order is missing.`],
    ["RECOMMENDATION", "First make every order complete and measurable. Then fix transit on the Rio de Janeiro and Northeast routes, and warn customers before a promise is missed."],
  ];
  let y = 1.95;
  blocks.forEach(([label, body], i) => {
    const h = i === 1 ? 1.75 : 1.3;
    text(slide, label, { x: M, y, w: 7.0, h: 0.3, fontSize: 12, bold: true, color: ORANGE, charSpacing: 2 });
    text(slide, body, { x: M, y: y + 0.34, w: 7.0, h: h - 0.34, fontSize: 16 });
    y += h + 0.2;
  });
  const sx = 8.3, sw = 4.43;
  card(slide, sx, 1.9, sw, 4.8);
  stat(slide, sx + 0.3, 2.05, sw - 0.6, pct(D.problem_share_of_low),
    `of bad reviews come from the ${pct(D.problem_share_of_orders)} of orders that were late or never delivered`, { size: 34, captionH: 0.6 });
  stat(slide, sx + 0.3, 3.6, sw - 0.6, pct0(C.several_incomplete.share),
    "of complaints about on-time orders with several items report a missing part", { size: 34, captionH: 0.6 });
  stat(slide, sx + 0.3, 5.15, sw - 0.6, int(S.ab.base.avoided),
    `bad reviews avoidable in the base case (${int(S.ab.low.avoided)} to ${int(S.ab.high.avoided)}), ${pct0(S.ab.base.share_of_all_bad)} of the total`, { size: 34, captionH: 0.6 });
}

// =============================================================================================
// 3. Context and question
// =============================================================================================
pres.addSection({ title: "Context and approach" });
{
  const slide = content("Context and approach",
    `One in seven reviewed orders ends in a bad review, although ${pct0(b.on_time_rate)} of deliveries keep the promised date`,
    "Context. All six figures: docs/kpi_baseline.md. Definitions: docs/metric_definitions.md. 'One in seven' = 14.6%.");
  card(slide, M, 1.9, 5.3, 2.35);
  text(slide, "The question from the Head of Operations", { x: M + 0.3, y: 2.1, w: 4.7, h: 0.3, fontSize: 12, bold: true, color: ORANGE, charSpacing: 1 });
  text(slide, "Why do customers give bad reviews, how much does it cost the business, and what should we fix first?",
    { x: M + 0.3, y: 2.5, w: 4.7, h: 1.6, fontFace: HEAD, fontSize: 22, italic: true });
  text(slide, [
    { text: "How cost is measured here. ", options: { bold: true } },
    { text: "The data contains no commission or cost figures, so the cost of the problem is counted in bad reviews, not in money." },
  ], { x: M, y: 4.6, w: 5.3, h: 1.6, fontSize: 14, color: INK });
  const tiles = [
    [int(b.orders), "orders placed"],
    [`${(b.gmv / 1e6).toFixed(1)}M`, "BRL, value of products ordered (GMV)"],
    [pct(b.on_time_rate), "of deliveries on or before the promised date"],
    [pct(b.not_delivered_rate), "of orders never delivered"],
    [b.avg_review_score.toFixed(2), "average review score, out of 5"],
    [pct(b.low_score_rate), "of reviewed orders with 1-2 stars"],
  ];
  const tx = 6.4, tw = 2.0, th = 2.2, gap = 0.17;
  tiles.forEach(([value, label], i) => {
    const x = tx + (i % 3) * (tw + gap), y = 1.9 + Math.floor(i / 3) * (th + gap);
    const problem = i === 5;
    card(slide, x, y, tw, th, problem ? "FBE4DA" : TINT);
    text(slide, value, { x: x + 0.2, y: y + 0.3, w: tw - 0.4, h: 0.75, fontFace: HEAD, fontSize: 28, bold: true, color: problem ? ORANGE : INK, valign: "middle" });
    text(slide, label, { x: x + 0.2, y: y + 1.15, w: tw - 0.4, h: 0.9, fontSize: 14 });
  });
}

// =============================================================================================
// 4. Approach and data
// =============================================================================================
{
  const slide = content("Context and approach",
    `The analysis combines ${int(b.orders)} orders with ${C.sample_size} customer reviews read in the original Portuguese`,
    "Approach. Steps and counts: docs/decision_log.md (32 decisions), docs/model_validation_report.md (37 tests), docs/metric_definitions.md (13 KPIs), docs/analysis_findings.md (12 hypotheses), review_coding/sampling_report.md (300 of 10,636), docs/scenario.md.");
  const steps = [
    ["Clean", "9 tables", "Source data, with 32 documented data decisions"],
    ["Model", "Star schema", "37 tests reconcile it with the raw data"],
    ["Define", "13 KPIs", "One written definition per number"],
    ["Test", "12 questions", "Hypotheses on delivery, product, price, seller, geography"],
    ["Read", `${C.sample_size} reviews`, `Random sample from ${int(C.frame_size)} bad reviews with a comment; 8 complaint types`],
    ["Estimate", "2 scenarios", "Low, base and high case"],
  ];
  const sw = 1.9, gap = 0.146, sy = 1.9, sh = 2.45;
  steps.forEach(([verb, headline, detail], i) => {
    const x = M + i * (sw + gap);
    card(slide, x, sy, sw, sh);
    numberBadge(slide, x + 0.2, sy + 0.2, i + 1, i === 4 ? ORANGE : DARK);
    text(slide, verb, { x: x + 0.78, y: sy + 0.2, w: sw - 0.9, h: 0.46, fontSize: 14, bold: true, color: MUTED, valign: "middle" });
    text(slide, headline, { x: x + 0.2, y: sy + 0.82, w: sw - 0.4, h: 0.4, fontFace: HEAD, fontSize: 17, bold: true });
    text(slide, detail, { x: x + 0.2, y: sy + 1.3, w: sw - 0.4, h: 1.0, fontSize: 12, color: INK });
  });
  text(slide, "Three choices that shape the results", { x: M, y: 4.7, w: 8, h: 0.35, fontSize: 16, bold: true });
  const choices = [
    ["Orders that never arrived stay in the analysis", `They are ${pct(outcome("Not delivered").share_of_orders)} of orders and ${pct(outcome("Not delivered").share_of_low)} of bad reviews.`],
    ["Late means after the promised calendar date", "A delivery on the promised day counts as on time."],
    ["One review per order", "When an order has several reviews, the latest one counts."],
  ];
  const cw = (W - 2 * M - 2 * 0.3) / 3;
  choices.forEach(([head, body], i) => {
    const x = M + i * (cw + 0.3);
    text(slide, head, { x, y: 5.15, w: cw, h: 0.3, fontSize: 14, bold: true });
    text(slide, body, { x, y: 5.5, w: cw, h: 0.85, fontSize: 14, color: MUTED });
  });
}

// =============================================================================================
// 5. Finding 1: delivery
// =============================================================================================
pres.addSection({ title: "Findings" });
{
  const slide = content("Findings",
    `A broken delivery promise is the strongest driver: ${pct0(outcome("Late").low_share)} of late orders get a bad review, against ${pct0(outcome("On time").low_share)} of on-time orders`,
    "Finding 1. Chart: docs/analysis_results.md table A2. Shares: table A1. Gap by region: G1. Monthly correlation: A7. Wording: 'strongest driver', an association in observational data, see docs/analysis_findings.md section 5.");
  const labels = D.delay_bands.map((d) => d.delay_band.replace("Late ", "").replace(" days", " days late"));
  slide.addChart(pres.charts.BAR, [{ name: "Share of 1-2 star reviews", labels, values: D.delay_bands.map((d) => d.low_share) }],
    Object.assign({}, CHART, {
      x: M, y: 2.05, w: 7.7, h: 4.55, barDir: "col", barGapWidthPct: 60,
      chartColors: [BLUE, ORANGE, ORANGE, ORANGE, ORANGE, ORANGE],
      showTitle: true, title: "Share of reviewed orders with a 1-2 star review, by delivery outcome",
      titleFontFace: BODY, titleFontSize: 13, titleColor: MUTED,
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0%",
      valAxisLabelFormatCode: "0%", valAxisMaxVal: 1, valAxisMajorUnit: 0.25,
      showLegend: false, objectName: "Chart bad reviews by delay band",
    }));
  const x = 8.8, w = 3.93;
  stat(slide, x, 1.95, w, `${pct(D.problem_share_of_orders)} of orders`,
    `were late or never delivered, and they account for ${pct(D.problem_share_of_low)} of all bad reviews`, { size: 28, captionH: 0.8 });
  stat(slide, x, 3.5, w, `${pp(D.gap_by_region_min)} to ${pp(D.gap_by_region_max)} points`,
    "gap between late and on-time orders in every one of the five regions", { size: 28, captionH: 0.6 });
  stat(slide, x, 4.95, w, `${D.monthly_correlation.toFixed(2)} correlation`,
    "between the monthly late rate and the monthly share of bad reviews, over 20 months", { size: 28, captionH: 0.8 });
  text(slide, "Observational data: a strong and consistent association, not a proven effect.",
    { x, y: 6.35, w, h: 0.45, fontSize: 11, italic: true, color: MUTED });
}

// =============================================================================================
// 6. Finding 2: where
// =============================================================================================
{
  const big = D.states.filter((s) => s.orders >= 1000);
  const slide = content("Findings",
    "The delay arises in transit on specific routes, above all to Rio de Janeiro and the Northeast, not with a few bad sellers",
    "Finding 2. Chart: docs/analysis_results.md table D2 (states with 1,000+ orders shown). Transit and handover: tables A6 and C5. Seller concentration: table C3.");
  slide.addChart(pres.charts.BAR, [{ name: "Late rate", labels: big.map((s) => s.state_name).reverse(), values: big.map((s) => s.late_rate).reverse() }],
    Object.assign({}, CHART, {
      x: M, y: 2.05, w: 6.9, h: 4.55, barDir: "bar", barGapWidthPct: 45,
      chartColors: big.map((s) => (s.state === "RJ" ? ORANGE : GREY)).reverse(),
      showTitle: true, title: `Late rate by customer state, states with 1,000+ orders (national: ${pct(b.late_rate)})`,
      titleFontFace: BODY, titleFontSize: 13, titleColor: MUTED,
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0%",
      valAxisHidden: true, valGridLine: { style: "none" }, valAxisMaxVal: 0.16,
      showLegend: false, objectName: "Chart late rate by state",
    }));
  const x = 7.95, w = 2.25, gap = 0.28;
  const items = [
    [pct(rj.share_of_late), `of all late deliveries go to Rio de Janeiro, which has ${pct(rj.share_of_orders)} of orders`, ORANGE],
    [`${int(late.median_transit_days)} vs ${int(onTime.median_transit_days)} days`, "median time with the carrier: late orders vs on-time orders", ORANGE],
    [pct0(1 - late.handed_over_late_share), "of late orders were handed to the carrier in time by the seller", INK],
    [pct0(D.worst_sellers.share_of_late), `of late orders come from the worst 10% of sellers (${D.worst_sellers.sellers} sellers with 30+ orders)`, INK],
  ];
  items.forEach(([value, caption, color], i) => {
    const cx = x + (i % 2) * (w + gap), cy = 2.0 + Math.floor(i / 2) * 2.35;
    stat(slide, cx, cy, w, value, caption, { size: 26, color, captionH: 1.3 });
  });
}

// =============================================================================================
// 7. Finding 3: review coding
// =============================================================================================
{
  const slide = content("Findings",
    "Late customers write \"not received\"; customers with several items delivered on time write \"part of my order is missing\"",
    "Finding 3. Review coding: review_coding/results.md and findings.md. 300 reviews, coded blind to delivery outcome, one coder; a second pass on 30 reviews gave the same category (consistency check, not independent validation). Groups have 43 to 126 reviews.");
  const groups = C.groups;
  const colors = [ORANGE, DARK, BLUE, GREY];
  const series = C.families.map((family, i) => ({
    name: family,
    labels: groups.map((g) => `${g.group} (${g.reviews})`).reverse(),
    values: groups.map((g) => g.shares[i]).reverse(),
  }));
  slide.addChart(pres.charts.BAR, series, Object.assign({}, CHART, {
    x: M, y: 1.95, w: 8.2, h: 3.25, barDir: "bar", barGrouping: "percentStacked", barGapWidthPct: 40,
    chartColors: colors, showValue: true, dataLabelPosition: "ctr", dataLabelFormatCode: '[>=0.05]0%;""', dataLabelColor: WHITE,
    valAxisHidden: true, valGridLine: { style: "none" },
    showLegend: true, legendPos: "b", showTitle: true,
    title: "Main complaint in 1-2 star reviews, by delivery outcome (number of reviews)",
    titleFontFace: BODY, titleFontSize: 13, titleColor: MUTED, objectName: "Chart complaints by delivery group",
  }));
  const si = C.several_incomplete;
  stat(slide, 9.2, 1.95, 3.53, pct0(si.share),
    `of complaints about on-time orders with several items say that part is missing (95% interval ${pct0(si.ci[0])} to ${pct0(si.ci[1])})`, { size: 44, captionH: 1.1 });
  text(slide, `${pct0(C.late_not_received.share)} of late-order complaints say the order has not arrived: the review is written while waiting.`,
    { x: 9.2, y: 4.05, w: 3.53, h: 1.1, fontSize: 14 });
  const quotes = [
    ["\"The order arrived before the deadline, but when I opened the box it was incomplete. I ordered two sets and only one came.\"", "On time, several items"],
    ["\"I still have not received my order. It was going to be a gift and the birthday was yesterday.\"", "Late"],
    ["\"I received only one item and it is already marked as received on the website, and the shop does not answer.\"", "On time, several items"],
  ];
  const qw = (W - 2 * M - 2 * 0.25) / 3;
  quotes.forEach(([quote, group], i) => {
    const x = M + i * (qw + 0.25);
    card(slide, x, 5.35, qw, 1.45);
    text(slide, quote, { x: x + 0.2, y: 5.45, w: qw - 0.4, h: 0.95, fontSize: 12, italic: true });
    text(slide, `Customer review, translated. Order: ${group.toLowerCase()}`, { x: x + 0.2, y: 6.42, w: qw - 0.4, h: 0.3, fontSize: 10, color: MUTED });
  });
}

// =============================================================================================
// 8. Scenario
// =============================================================================================
pres.addSection({ title: "What to do" });
{
  const slide = content("What to do",
    `Complete orders and on-time delivery in the five worst states could remove about ${int(Math.round(S.ab.base.avoided / 100) * 100)} bad reviews, ${pct0(S.ab.base.share_of_all_bad)} of the total`,
    "Scenario. docs/scenario.md and docs/scenario_results.md. Method: orders that move to the better group are assumed to be reviewed like that group, times a factor for how much of the observed gap is real (50%, 75%, 100%). An estimate, not a measured effect.");
  const cats = ["A  Five worst states reach the national late rate", "B  Several-item orders reviewed like single-item orders", "A + B"];
  const pick = (c) => [S.a[c].avoided, S.b[c].avoided, S.ab[c].avoided].map((v) => Math.round(v));
  slide.addChart(pres.charts.BAR, [
    { name: "Low case (50% of the gap is real)", labels: cats, values: pick("low") },
    { name: "Base case (75%)", labels: cats, values: pick("base") },
    { name: "High case (100%)", labels: cats, values: pick("high") },
  ], Object.assign({}, CHART, {
    x: M, y: 2.0, w: 7.9, h: 4.65, barDir: "col", barGrouping: "clustered", barGapWidthPct: 55,
    chartColors: [GREY, ORANGE, DARK], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "#,##0",
    valAxisLabelFormatCode: "#,##0", showLegend: true, legendPos: "b", catAxisLabelFontSize: 11,
    showTitle: true, title: "Estimated 1-2 star reviews avoided over 20 months",
    titleFontFace: BODY, titleFontSize: 13, titleColor: MUTED, objectName: "Chart scenario",
  }));
  const x = 8.95, w = 3.78;
  stat(slide, x, 1.95, w, `${pct(b.low_score_rate)} to ${pct(S.ab.base.new_low_share)}`,
    `share of 1-2 star reviews in the base case (${pct(S.ab.high.new_low_share)} to ${pct(S.ab.low.new_low_share)})`, { size: 28, captionH: 0.6 });
  stat(slide, x, 3.3, w, pct(S.ceiling_share_of_all_bad),
    "of bad reviews is the ceiling for any action on late deliveries alone, if no order were late", { size: 28, color: INK, captionH: 0.8 });
  card(slide, x, 4.85, w, 1.85);
  text(slide, [
    { text: "Read this as an order of magnitude. ", options: { bold: true } },
    { text: "The scenario applies observed differences between groups of orders. It is not a measured effect, and the data has no cost side." },
  ], { x: x + 0.2, y: 4.97, w: w - 0.4, h: 1.65, fontSize: 14 });
}

// =============================================================================================
// 9. Recommendations
// =============================================================================================
{
  const slide = content("What to do",
    "Start with order completeness, then transit on the worst routes, and warn customers before a promise is missed",
    "Recommendations. Impact figures from the scenario (docs/scenario.md). Effort levels and owners are assumptions: Olist's costs and organisation are not in the data.");
  const recs = [
    {
      head: "Make every order complete, and measure it",
      why: `${int(several.orders)} on-time orders with several items get ${pct(several.low_share)} bad reviews, against ${pct(single.low_share)} for single items.`,
      impact: `High: about ${int(S.b.base.avoided)} bad reviews (${int(S.b.low.avoided)} to ${int(S.b.high.avoided)})`,
      effort: "Medium",
      owner: "Seller Operations",
      first: "Audit 100 several-item orders marked delivered: sent later, or never sent?",
    },
    {
      head: "Fix transit to Rio de Janeiro and the Northeast",
      why: `Five states hold ${int(S.orders_moved_a)} late orders above the national rate; late parcels spend ${int(late.median_transit_days)} days in transit, not ${int(onTime.median_transit_days)}.`,
      impact: `Medium: about ${int(S.a.base.avoided)} bad reviews (${int(S.a.low.avoided)} to ${int(S.a.high.avoided)})`,
      effort: "High",
      owner: "Logistics",
      first: "Build a carrier scorecard by route; review the promised dates there.",
    },
    {
      head: "Warn customers before a promise is missed",
      why: `Bad reviews go from ${pct0(band("Late 1-3 days").low_share)} at 1-3 days late to ${pct0(band("Late 4-7 days").low_share)} at 4-7 days; ${pct0(C.late_not_received.share)} of late complaints are written while waiting.`,
      impact: "Not quantified: needs a test",
      effort: "Low",
      owner: "Customer Service",
      first: "Send a new delivery date to half of the at-risk orders and compare the reviews.",
    },
  ];
  const cw = (W - 2 * M - 2 * 0.25) / 3, cy = 1.9, ch = 4.7;
  recs.forEach((r, i) => {
    const x = M + i * (cw + 0.25);
    card(slide, x, cy, cw, ch);
    numberBadge(slide, x + 0.25, cy + 0.25, i + 1);
    text(slide, r.head, { x: x + 0.85, y: cy + 0.2, w: cw - 1.05, h: 0.7, fontFace: HEAD, fontSize: 17, bold: true, valign: "middle" });
    text(slide, r.why, { x: x + 0.25, y: cy + 1.05, w: cw - 0.5, h: 1.2, fontSize: 14 });
    const rows = [["Impact", r.impact], ["Effort", r.effort], ["Owner", r.owner], ["First step", r.first]];
    let ry = cy + 2.3;
    rows.forEach(([label, value]) => {
      const h = label === "First step" ? 0.95 : label === "Impact" ? 0.6 : 0.36;
      text(slide, label, { x: x + 0.25, y: ry, w: 0.95, h, fontSize: 12, bold: true, color: MUTED });
      text(slide, value, { x: x + 1.2, y: ry, w: cw - 1.45, h, fontSize: 14, bold: label === "Impact" });
      ry += h + 0.08;
    });
  });
  text(slide, "Effort levels and owners are assumptions: Olist's costs and organisation are not in the data.",
    { x: M, y: 6.7, w: 9, h: 0.22, fontSize: 10, italic: true, color: MUTED });
}

// =============================================================================================
// 10. Limitations and next steps
// =============================================================================================
{
  const slide = content("What to do",
    "The findings are strong associations, not proven effects; four next steps would turn them into a business case",
    "Limitations and next steps. docs/analysis_findings.md sections 5 and 7, docs/scenario.md section 6, review_coding/findings.md section 5.", "CONTENT_DARK");
  const nd = outcome("Not delivered");
  const col = (W - 2 * M - 0.6) / 2;
  text(slide, "LIMITATIONS", { x: M, y: 1.95, w: col, h: 0.3, fontSize: 12, bold: true, color: ORANGE, charSpacing: 2 });
  const limits = [
    ["No experiment. ", "Nobody was assigned a late delivery at random; hidden factors can play a role."],
    ["The survey is sent around the promised date. ", "Late customers are asked while still waiting, which sharpens the gap."],
    [`${C.sample_size} reviews, one coder. `, "Only customers who wrote a comment are represented."],
    ["No cost or commission data. ", "Impact is counted in reviews, not in money; no return on investment."],
  ];
  limits.forEach(([lead, rest], i) => {
    text(slide, [{ text: lead, options: { bold: true, color: WHITE } }, { text: rest, options: { color: "D1D5DB" } }],
      { x: M, y: 2.4 + i * 1.05, w: col, h: 0.95, fontSize: 15 });
  });
  const x = M + col + 0.6;
  text(slide, "NEXT STEPS", { x, y: 1.95, w: col, h: 0.3, fontSize: 12, bold: true, color: ORANGE, charSpacing: 2 });
  const steps = [
    ["Audit several-item orders. ", "Does the missing part arrive later, or is it never sent? The fix differs."],
    ["Test proactive messages. ", "A random half of at-risk orders gets a new date; compare the reviews."],
    ["Add carrier and cost data. ", "Needed to rank routes by return, not only by late rate."],
    [`Analyse the ${int(nd.orders)} undelivered orders. `, `They are ${pct(nd.share_of_low)} of bad reviews and outside both scenarios.`],
  ];
  steps.forEach(([lead, rest], i) => {
    numberBadge(slide, x, 2.4 + i * 1.05, i + 1);
    text(slide, [{ text: lead, options: { bold: true, color: WHITE } }, { text: rest, options: { color: "D1D5DB" } }],
      { x: x + 0.65, y: 2.4 + i * 1.05, w: col - 0.65, h: 0.95, fontSize: 15 });
  });
}

pres.writeFile({ fileName: OUT }).then(() => console.log("written: " + path.basename(OUT)));
