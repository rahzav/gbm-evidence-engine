# GBM Evidence Engine (V1 prototype)

A cross-cohort, cross-modality, provenance-tracked evidence dossier
generator for glioblastoma research — built as the first vertical slice of
a research platform for **Rutgers Gray for Glioblastoma** (rutgersg4g.org).

Given a gene, it deterministically computes and cross-validates survival
association (across TCGA-GBM, CGGA, and GLASS-recurrent), anatomic/spatial
enrichment (Ivy GAP), GBM-selective dependency (DepMap), known compounds
and blood-brain-barrier evidence (Open Targets, B3DB), trial landscape
(ClinicalTrials.gov), and literature support (Europe PMC) — then produces a
structured, confidence-tiered dossier plus a numerically-grounded natural-
language synthesis that cannot state a statistic it didn't actually compute
(enforced by an automated validator, not just a system-prompt request).

**Read `docs/ARCHITECTURE.md` for the full design and `docs/
VALIDATION_REPORT.md` before trusting any specific number this prototype
prints** — it documents exactly which parts ran against real, cited data
versus clearly-labeled synthetic placeholders, and why (this prototype was
built in a network-disabled sandbox; see that report for specifics).

## Quickstart

```bash
pip install -r requirements.txt   # numpy/pandas/scipy already sufficient
                                    # for everything except api/app.py
PYTHONPATH=. python3 scripts/generate_synthetic_reference_data.py  # rebuild demo data (already included)
PYTHONPATH=. python3 scripts/run_demo_dossier.py EGFR               # -> out/EGFR_dossier.json, out/EGFR_report.md
PYTHONPATH=. python3 scripts/run_batch_demo.py                      # 4-gene batch triage with BH-FDR correction

# Tests (pytest not required -- each file also runs standalone):
PYTHONPATH=. python3 tests/test_survival.py
PYTHONPATH=. python3 tests/test_dependency.py
PYTHONPATH=. python3 tests/test_evidence_model.py
PYTHONPATH=. python3 tests/test_grounding_validator.py

# API (requires `pip install fastapi uvicorn` on a machine with network access):
uvicorn api.app:app --reload
```

## Layout

```
gbm_evidence_engine/
  evidence_model.py       # EvidenceRecord / Dossier / EvidenceTier / Provenance
  connectors/              # one module per data source, real endpoints, see base.py::SOURCE_REGISTRY
  analysis/                 # deterministic statistics -- survival, dependency, spatial, multiple-testing
  knowledge/                # curated, citation-backed domain safeguards (e.g. culture-instability flags)
  orchestrator/            # planner (query -> tasks), build_dossier (the pipeline), synthesizer (grounded AI prose)
api/app.py                  # FastAPI wrapper (real code, not executable in this offline sandbox)
data/                        # demo datasets -- see data/README.md for real-vs-synthetic labeling of every file
scripts/                     # generate_synthetic_reference_data.py, run_demo_dossier.py, run_batch_demo.py
tests/                        # plain-assert test scripts, no pytest dependency
docs/ARCHITECTURE.md        # full Phase 4 product/technical specification
docs/VALIDATION_REPORT.md   # what was actually tested, what broke and was fixed, known limitations
```

## What this is not (yet)

This is a V1 vertical slice, not the full platform described in
`docs/ARCHITECTURE.md`'s roadmap. It proves the core primitive (harmonized
cross-cohort, cross-modality evidence assembly with enforced provenance and
hallucination-resistant synthesis) works end to end on one real, well-
documented example (EGFR) and generalizes to a small batch. It does not yet
have live network connectivity wired up in a deployed environment, a web
front-end, real CGGA/GLASS ingestion (registration pending), or the V2+
free-text/scRNA/longitudinal-recurrence features on the roadmap.
