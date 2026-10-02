# Review coding

Qualitative analysis of what customers write in 1-2 star reviews: 300 Portuguese reviews coded into 8
complaint categories.

**Start here:** [`findings.md`](findings.md).

**Method.** A stratified random sample of 300 reviews was read in the original Portuguese and coded with the
codebook, blind to the delivery outcome of the order. 30 reviews were coded a second time as a consistency
check.

| File | What it is |
|---|---|
| [`findings.md`](findings.md) | Interpretation of the results, translated quotes, limitations |
| [`results.md`](results.md) | Category shares, split by delivery outcome, confidence intervals, consistency check (generated) |
| [`codebook.md`](codebook.md) | The 8 complaint categories: definition, inclusion rules, examples, decision rules |
| [`categories.csv`](categories.csv) | The category list in machine-readable form |
| [`sampling_report.md`](sampling_report.md) | How the 300 reviews were drawn: frame, stratification, seed, checks (generated) |
| [`sample.csv`](sample.csv) | The 300 sampled reviews: score and text only |
| [`sample_key.csv`](sample_key.csv) | Delivery information of the sampled reviews, kept apart so that the coding is blind |
| [`coding.csv`](coding.csv) | The coding: primary and secondary category per review, with notes |
| [`recode_set.csv`](recode_set.csv) | The 30 reviews selected for the second coding pass |
| [`recoding.csv`](recoding.csv) | The second coding pass of those 30 reviews |
| [`coded_reviews.csv`](coded_reviews.csv) | Coding, text and delivery information joined in one file (generated) |
| [`pilot.csv`](pilot.csv) | 60 other reviews used to develop the codebook; none of them is in the sample |

Scripts: [`notebooks/05_review_sample.py`](../notebooks/05_review_sample.py) draws the sample;
[`notebooks/06_review_coding_results.py`](../notebooks/06_review_coding_results.py) checks the coding and
computes the results.
