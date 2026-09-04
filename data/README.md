# Data provenance — read this before trusting any number in a demo run

This engine is designed to run against **live and periodically-ingested real
data** (see `gbm_evidence_engine/connectors/base.py::SOURCE_REGISTRY`). The
sandbox this V1 was built in has **no network egress** (confirmed: `pip
install` and outbound HTTP both fail here), so the bundled demo cannot pull
live TCGA/CGGA/GLASS/Ivy GAP/DepMap data. Rather than fake that limitation
away, every file in this directory is labeled below with exactly what it is.

| File | Status | Notes |
|---|---|---|
| `b3db_reference_subset.csv` | **Real, cited** | Small hand-curated subset (7 compounds) of real, published, citation-backed blood-brain-barrier penetration findings for EGFR-pathway drugs in the GBM literature. Not the full downloaded B3DB file (7,807 compounds) — that requires a network fetch from `github.com/theochem/B3DB`, which this sandbox cannot perform. Every row is individually citable. |
| `reference_literature_facts.json` | **Real, cited** | Verbatim-paraphrased (never quoted) facts pulled from real papers found via live web search during this session: EGFR amplification frequency, EGFRvIII frequency, the 32-study/4,208-patient meta-analysis pooled hazard ratios (overall and by region), and the EGFR-culture-instability literature. Every entry has a real source. |
| `synthetic_cohort_survival_*.csv` | **Synthetic, calibrated** | Per-patient time/event/covariate tables generated to be broadly consistent with published GBM survival statistics (median OS ~12-15 months, event rates, HR ballpark from the meta-analysis above) — but these are NOT real TCGA/CGGA/GLASS patient rows. Used only to demonstrate that `analysis/survival.py`'s Cox/log-rank/meta-analysis code runs correctly end-to-end and correctly flags cross-cohort heterogeneity when it is present. |
| `synthetic_depmap_effect_scores.csv` | **Synthetic, calibrated** | Illustrative per-cell-line CRISPR effect scores, not real DepMap Chronos scores (no network access to the real DepMap release in this sandbox). Demonstrates `analysis/dependency.py`'s selective-dependency test and pan-essential-gene safeguard. |
| `synthetic_ivygap_zone_expression.csv` | **Synthetic, calibrated** | Illustrative per-zone expression values, not real Ivy GAP RNA-seq. Demonstrates `analysis/spatial.py`'s anatomic-enrichment test. |

**What changes in a networked deployment:** every connector in
`gbm_evidence_engine/connectors/` is written against the real, documented API
of its source (see docstrings for exact endpoints). Point `base.http_get_json`
/ the GraphQL POST helper at a machine with outbound network access and the
same code ingests real data — nothing about the analysis layer changes.
CGGA and GLASS additionally require completing each consortium's free
registration / data-use agreement before ingestion (see `SOURCE_REGISTRY`);
that is a one-time compliance step for a team member, not a code change.
