# Review coding

Qualitative analysis of what customers write in 1-2 star reviews. The reviews are in Portuguese and are read
and coded by hand by the author, a native speaker.

**Status:** codebook and sample are ready; the manual coding is in progress. Results: [TBD].

| File | What it is |
|---|---|
| [`codebook.md`](codebook.md) | The 8 complaint categories: definition, inclusion rules, examples, decision rules, procedure |
| [`categories.csv`](categories.csv) | The category list in machine-readable form (source of the drop-down lists and of the validation) |
| [`sampling_report.md`](sampling_report.md) | How the 300 reviews were drawn: frame, stratification, seed, checks (generated) |
| [`sample.csv`](sample.csv) | The 300 sampled reviews: score and text only |
| [`sample_key.csv`](sample_key.csv) | Delivery information of the sampled reviews, kept apart so that the coding is blind |
| [`pilot.csv`](pilot.csv) | 60 other reviews used to develop the codebook; none of them is in the sample |
| `coding_sheet.xlsx` | The sheet in which the 300 reviews are coded |
| `recode_sheet.xlsx` | 30 of the 300 reviews, coded a second time later to test consistency |
| `coded_reviews.csv` | The finished coding as a plain file (created by the results script) |
| `results.md` | Category shares, split by delivery outcome, consistency check (created by the results script) |

Scripts: [`notebooks/05_review_sample.py`](../notebooks/05_review_sample.py) draws the sample and builds the
sheets; [`notebooks/06_review_coding_results.py`](../notebooks/06_review_coding_results.py) validates the coding
and computes the results.
