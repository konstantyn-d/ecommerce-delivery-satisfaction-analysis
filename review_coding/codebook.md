# Codebook: complaint categories for 1–2 star reviews

**Purpose.** The numbers show *that* customers are unhappy (14.6% of reviewed orders get 1–2 stars) and that
57.3% of those bad reviews come from orders delivered on time. They cannot show *what* those customers
complain about. This codebook turns the Portuguese review texts into countable complaint categories.

**Coder.** The author of this project, a native Portuguese speaker. Single coder; consistency is tested by re-coding (section 6).

**Version.** 1.0, developed on a pilot set of 60 reviews ([`pilot.csv`](pilot.csv)) that are not part of the
sample. All example phrases below are quoted from that pilot set with their original spelling.

## 1. What is coded

| | |
|---|---|
| Unit | One review = comment title + comment message, read together |
| Sample | 300 reviews, see [`sampling_report.md`](sampling_report.md) |
| Primary category | Mandatory. Exactly one per review: the main complaint |
| Secondary category | Optional. A second, different complaint in the same review |
| Blind coding | The coding sheet shows only the score and the text. Whether the order was late is not shown, so that it cannot influence the coding |

## 2. Categories

| # | Category | Definition | Include | Do not include | Example (Portuguese) | Meaning |
|---|---|---|---|---|---|---|
| 1 | **Not received** | The customer says the order, or all of it, has not arrived | "still waiting", "not delivered", tracking says delivered but the customer has nothing | Only part is missing (→ 3). Arrived, but late (→ 2) | *"Não recebi o produto até hoje !!!"* | I have not received the product to this day |
| 2 | **Late delivery** | The complaint is about a missed deadline or a long wait, and the text does not say the order is still missing | Arrived after the promised date; "took too long"; blaming the carrier for slowness | The text says it has still not arrived (→ 1) | *"Tudo certo com a loja, mas 1 mês esperando os COrreios entregarem."* | The shop was fine, but one month waiting for the post office to deliver |
| 3 | **Incomplete order** | Only part of what was bought arrived | Fewer units than ordered; one of several products missing; a missing part or accessory | Nothing arrived at all (→ 1) | *"recebi apenas uma unidade e compramos duas"* | I received only one unit and we bought two |
| 4 | **Wrong item** | A different article than the one ordered was delivered | Other product, other model, other colour or size variant | The right article that looks different from the photo (→ 6) | *"venho outro modelo de relógio casio, diferente do relógio que comprei."* | Another Casio watch model came, different from the one I bought |
| 5 | **Damaged or defective** | The right product arrived but is broken, damaged or does not work | Broken in transit; does not switch on; a function does not work | Works, but feels cheap (→ 6) | *"Não funciona a tecla do Netflix, não recomendo"* | The Netflix button does not work, I do not recommend it |
| 6 | **Poor quality or not as described** | The right product arrived and works, but quality, look or specifications are below what the listing promised | Thin or weak material; colour differs from the photo; measurements differ from the listing; suspected counterfeit | Does not work at all (→ 5). A different article (→ 4) | *"As toalhas sao muito finas, nao enxugam!!!"* | The towels are very thin, they do not dry |
| 7 | **Seller service and refunds** | The complaint is about contact, cancellation, return, refund or invoice, and no product or delivery problem is stated as its cause | Order cancelled against the customer's will; cannot cancel; refund not received; no reply; no invoice | A service complaint that follows another problem: code that problem as primary and this as secondary | *"estou aguardando o estorno desta compra, gostaria de saber porque estar demorando tanto para isso ser feito"* | I am waiting for the refund of this purchase and would like to know why it takes so long |
| 8 | **Other or unclear** | None of the above can be decided from the text | Too vague ("terrible service"); about something else (price, website); not a complaint | Anything that fits 1–7, even loosely | *"Serviço péssimo."* | Terrible service |

## 3. Decision rules

1. **Code what the text says, not what you suspect.** If the review says "I have not received it", it is
   *Not received*, even if you guess that it probably arrived later.
2. **Primary = the first thing that went wrong.** When a review contains several complaints, the primary
   category is the problem without which the others would not exist. The rest goes into the secondary category.

   | Review says | Primary | Secondary |
   |---|---|---|
   | Wrong product arrived, asked for a refund, no answer | Wrong item | Seller service and refunds |
   | Nothing arrived, wants the money back | Not received | Seller service and refunds |
   | Wrong product arrived and it is broken | Wrong item | Damaged or defective |
   | Bought two, one arrived, and it came late | Incomplete order | Late delivery |

3. **Not received vs Late delivery.** The test is one question: *according to the text, does the customer have
   the product now?* No → *Not received*. Yes, or the text does not say → *Late delivery*.
4. **Not received vs Incomplete order.** *Did anything from this order arrive?* Nothing → *Not received*.
   Something → *Incomplete order*.
5. **Wrong item vs Poor quality or not as described.** *Is it the article that was ordered?* A different article
   → *Wrong item*. The ordered article, but disappointing → *Poor quality or not as described*.
6. **"Other or unclear" is a last resort.** Use it only when the text really does not allow a decision. Write
   the reason in the notes column.
7. **Positive or neutral text with a low score** → *Other or unclear*, with a note.
8. **Company names in the texts** such as *lannister*, *stark*, *targaryen* or *baratheon* are placeholders:
   Olist replaced the names of shops and partners to anonymise the data. Treat them as "the shop".

## 4. Procedure

1. Read sections 2 and 3 once more, then code the 60 pilot reviews in your head or on paper as a warm-up.
   If a pilot review fits no category, raise it **before** starting the sample.
2. Open [`coding_sheet.xlsx`](coding_sheet.xlsx). For each row: read title and message, choose the
   primary category from the drop-down list, add a secondary category only if there is a second complaint.
3. Mark `good_quote` with an `x` when a comment is short, clear and typical of its category. These are the
   candidates for the 4–6 quotes in the deck. No names, addresses or order numbers in a quote.
4. Code in two or three sessions of at most one hour. Tired coders drift.
5. **Do not change the codebook during coding.** If a rule turns out to be unworkable, stop, write down the
   problem and the row numbers affected, change the rule, and re-code those rows. Every change is recorded in
   section 7.
6. Save the file under the same name, then run `python notebooks/06_review_coding_results.py`.

## 5. What the results can and cannot show

- They describe **customers who gave 1–2 stars and chose to write a comment**: 10,636 reviews, about three
  quarters of all bad reviews in the period. Customers who gave a low score without text are not represented.
- The sample is 300 reviews. A category with a share of 20% has a 95% confidence interval of roughly
  16% to 25%; for one delivery group alone (43 to 126 reviews) the intervals are much wider. Differences of a
  few points between categories are not meaningful.
- A complaint is what the customer wrote at the moment of the survey. A parcel "not received" may have arrived
  the next day.
- One coder. Another person might draw the lines between categories slightly differently.

## 6. Consistency check (intra-coder reliability)

At least **three days after finishing** the main coding, and without looking at the first results, code the 30
reviews in [`recode_sheet.xlsx`](recode_sheet.xlsx). The results script then compares both codings and reports:

- **Percent agreement:** share of the 30 reviews with the same primary category both times.
- **Cohen's kappa:** agreement corrected for the agreement expected by chance. Common reading: above 0.60 is
  substantial, above 0.80 is almost perfect.

ASSUMPTION: agreement on these 30 reviews is representative of the consistency of the whole coding.
If agreement is below 80%, the disagreements are reviewed, the rule that caused them is clarified, and the
affected category is re-coded.

## 7. Change log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-10-02 | First version, developed on the pilot set |
