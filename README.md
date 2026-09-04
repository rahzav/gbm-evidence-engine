# GBM Evidence Engine — live-first research target intelligence

A provenance-tracked glioblastoma research tool built for **Rutgers Gray for Glioblastoma**.

Enter a gene (for example `EGFR`, `PTEN`, `TERT`, `CDK6`) and the app assembles a live research profile from public sources, then answers four practical questions:

1. **How strong is the current GBM evidence footprint?**
2. **How translationally mature/druggable is the target?**
3. **What evidence is missing or contradictory?**
4. **What experiment or analysis is most useful next?**

The target-priority signal is a transparent **research-triage heuristic**, not a clinical/prognostic model.

## Live sources

- **cBioPortal / TCGA-GBM** — mutation, high-level CNA, expression layers when exposed by the selected study
- **Open Targets Platform** — target identity, GBM association evidence, tractability and known drugs/candidates
- **ClinicalTrials.gov API v2** — GBM trials matching the gene and top target-directed drugs
- **Europe PMC** — literature volume, top matching papers and GBM-context coverage (recurrence, IDH, MGMT, single-cell, spatial, treatment resistance, BBB)

## Deliberately not scored yet

The repo still contains the V1 statistical methods and labeled synthetic demonstration files used to validate survival, dependency, spatial and grounding logic. **Synthetic values never increase the live target score.**

The remaining high-value integrations are:

- real **DepMap** CRISPR dependency release ingestion
- real **Ivy GAP** spatial/anatomic expression ingestion
- **CGGA** external validation after registration/data-use setup
- **GLASS** longitudinal primary/recurrent data after Synapse/DUA setup

Until those are integrated, the score exposes a `Cross-cohort functional validation` dimension as missing and reduces evidence coverage accordingly.

## Run the standalone app

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
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
```

Deployment-only network check:

```bash
PYTHONPATH=. python3 scripts/live_smoke_test.py
```

## Core design rule

Every quantitative claim presented as evidence is wrapped in an `EvidenceRecord` with source, access tier, method, retrieval timestamp and confidence. Missing sources are shown as missing; they are not silently substituted with synthetic values.

See `docs/ARCHITECTURE.md` and `docs/VALIDATION_REPORT.md` for the V1 statistical architecture and validation history.
