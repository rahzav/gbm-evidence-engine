# GBM Evidence Engine — research-grade target intelligence

A provenance-tracked glioblastoma research tool built for **Rutgers Gray for Glioblastoma**.

Enter a gene (for example `EGFR`, `PTEN`, `TERT`, `CDK6`) and V3 assembles a GBM-specific research profile across genomics, functional dependency, spatial biology, external human cohorts, druggability, clinical translation and literature. It is designed to answer:

1. **How strong and selective is the current GBM evidence footprint?**
2. **Where does the target sit in GBM anatomy and independent patient cohorts?**
3. **How translationally mature/druggable is it?**
4. **What evidence is missing, contradictory, or most useful to test next?**

The target-priority signal is a transparent **research-triage heuristic**, not a clinical prediction model and not evidence of treatment benefit.

## Evidence sources

- **cBioPortal / TCGA-GBM** — mutation and high-level copy-number evidence
- **Open Targets Platform** — GBM association evidence, tractability and target-directed candidates
- **DepMap Breadbox / Chronos** — live CRISPR dependency for the strict OncoTree subtype `Glioblastoma, IDH-Wildtype` versus the remaining DepMap panel, with a pan-essential safeguard
- **Ivy Glioblastoma Atlas Project** — official normalized RNA-seq across seven laser-microdissection GBM anatomic zones; source ZIP is cached locally and genes are streamed on demand
- **CGGA mRNAseq_693 + mRNAseq_325** — two independent public patient cohorts; survival models are restricted to adult, primary, WHO-IV histologic GBM, IDH-wildtype and meta-analysed when both cohorts are usable
- **ClinicalTrials.gov API v2** — GBM trials matching the gene and target-directed candidates
- **Europe PMC** — literature volume, papers and GBM-context coverage
- **GLASS / Synapse** — controlled longitudinal TPM ingestion via `SYNAPSE_AUTH_TOKEN`; paired primary/recurrent diffuse-glioma context is deliberately excluded from the GBM priority score until subtype-specific controlled clinical filtering is available

## Scoring model

V3 exposes eight independent score dimensions rather than collapsing unlike evidence into one hidden model:

| Dimension | Weight |
|---|---:|
| TCGA GBM genomic signal | 18% |
| Open Targets GBM disease relevance | 14% |
| Druggability | 14% |
| Clinical translation | 12% |
| Literature/context depth | 10% |
| DepMap functional dependency | 16% |
| Ivy GAP spatial context signal | 8% |
| Independent CGGA human validation | 8% |

Missing sources reduce **evidence coverage** rather than being converted into negative evidence. Synthetic V1 files remain only for deterministic method testing and **never increase a live V3 score**.

## Data handling

Large Ivy/CGGA source files are downloaded from the upstream resource into `data/_cache/` at runtime and are git-ignored. Controlled GLASS files are only requested after authorized Synapse authentication. Raw external matrices are not committed or re-hosted.

## Run the app

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

For authorized GLASS access, configure the deployment secret/environment variable:

```bash
SYNAPSE_AUTH_TOKEN=<authorized-personal-access-token>
```

## API

```bash
uvicorn api.app:app --reload
```

- `POST /profile` with `{"gene":"EGFR"}`
- `POST /profile/batch` with `{"genes":["EGFR","PTEN","TERT"]}`
- `GET /health`

## Tests

```bash
PYTHONPATH=. python3 tests/test_survival.py
PYTHONPATH=. python3 tests/test_dependency.py
PYTHONPATH=. python3 tests/test_evidence_model.py
PYTHONPATH=. python3 tests/test_grounding_validator.py
PYTHONPATH=. python3 tests/test_research_intelligence.py
PYTHONPATH=. python3 tests/test_research_intelligence_v3.py
```

## Core design rule

Every quantitative claim presented as evidence is wrapped in an `EvidenceRecord` with source, access tier, method, retrieval timestamp and confidence. A source outage, controlled-access barrier, missing gene, or insufficient cohort is shown explicitly; no placeholder statistic is substituted.
