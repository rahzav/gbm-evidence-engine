# GBM Evidence Engine — Architecture & Product Specification

*Built for Rutgers Gray for Glioblastoma (rutgersg4g.org). This document is
Phase 4 of the product brief; see the top-level chat response for Phases
1-3 (landscape research, finalist selection, adversarial elimination) and
`VALIDATION_REPORT.md` for Phase 5's validation results.*

## Core research primitive

**A harmonized, cross-cohort, cross-modality, provenance-tracked evidence
dossier for any GBM gene/pathway.** Given a target, the engine deterministically
computes and cross-validates statistical, computational, and curated
evidence across independent GBM data resources, and returns a structured,
confidence-tiered dossier plus a grounded natural-language synthesis that
cites only evidence that was actually computed — never invented.

This is the operation that is difficult today only because it requires a
person to (a) know all seven-plus relevant resources exist, (b) know each
one's access model and quirks, (c) hand-harmonize sample-level covariates
(subtype, IDH status, primary/recurrent timing) across them, (d) run the
right statistical test per resource, (e) notice when results disagree, and
(f) remember to check a cell-culture-artifact literature caveat before
trusting a dependency score. Every one of those six sub-steps is a real,
separately-citable failure point in current practice (see landscape verdict).

## V1 — implemented in this repository

Single-gene query → seven evidence layers, all real connector code, four of
seven demonstrated against real cited data in this session (see
`VALIDATION_REPORT.md` for exactly which):

1. Cross-cohort survival (TCGA-GBM / CGGA / GLASS-recurrent) — Cox PH per
   cohort + inverse-variance meta-analysis with automatic heterogeneity
   detection (`analysis/survival.py`, `orchestrator/build_dossier.py`).
2. Anatomic/spatial enrichment (Ivy GAP, 7 laser-microdissected zones) —
   Kruskal-Wallis (`analysis/spatial.py`).
3. GBM-selective dependency (DepMap CRISPR effect scores) — Mann-Whitney
   with pan-essential-gene and culture-instability safeguards
   (`analysis/dependency.py`, `knowledge/culture_instability_flags.py`).
4. Known compounds / BBB penetration (Open Targets + B3DB) —
   (`connectors/opentargets.py`, `connectors/b3db.py`).
5. Trial landscape (ClinicalTrials.gov v2) — (`connectors/clinicaltrials.py`).
6. Literature support/contradiction (Europe PMC) —
   (`connectors/europepmc.py`, `connectors/literature_reference.py`).
7. AI-generated follow-up suggestions, always tagged as inference, never
   fact (`orchestrator/build_dossier.py::_run_ai_inference`).

V1 is not a cosmetic demo: `scripts/run_demo_dossier.py EGFR` produces a
22-record dossier with real hazard ratios, a correctly-triggered cross-
cohort heterogeneity warning, a correctly-triggered pan-essential/culture-
instability caveat, and a numerically-grounded AI synthesis — all covered
by passing unit tests (see `VALIDATION_REPORT.md`).

## V2 – V4 roadmap

- **V2**: real live ingestion (point `connectors/*` at a networked host;
  complete CGGA/GLASS registration; replace the from-scratch survival
  module with `lifelines`); scRNA/spatial cell-state layer via CELLxGENE/
  HTAN (Neftel et al. 4-state GBM classifier overlap); free-text hypothesis
  input parsed by an LLM into the same structured `QueryPlan` primitives.
- **V3**: primary→recurrent longitudinal evolution as a first-class evidence
  layer (GLASS-specific paired testing, not just a third "cohort"); gene-set
  and pathway-level queries (Reactome/STRING network context); imaging-
  genomics linkage (TCIA/BraTS radiomic features correlated with the same
  evidence dossier); shareable, versioned "research sessions" with a public
  API for other labs to query programmatically.
- **V4**: federate with general-purpose biomedical tool ecosystems (e.g.
  expose our GBM-specific connectors as MCP tools consumable by ToolUniverse/
  TxAgent-style agents, and consume their broader tool library for anything
  outside GBM-specific harmonization) rather than re-implementing everything;
  institutional collaborator accounts; multi-disease expansion using the same
  harmonization architecture for other CNS tumors.

## Data architecture

Every source is registered once in `connectors/base.py::SOURCE_REGISTRY`
with an explicit `AccessTier` (open live API / open bulk download /
registration-gated) — see that file for the full table and
`data/README.md` for exactly what is real vs. synthetic-for-demo in this
build. Real deployment ingestion pattern: live APIs are queried on demand
and cached with a TTL; bulk-download sources (Ivy GAP, DepMap, CGGA once
registered, GLASS once registered) are ingested on a versioned schedule
into `data/_cache/`, with the exact release/version string stored on every
`EvidenceRecord.provenance.dataset_version` this produces — this is what
makes a cross-cohort comparison reproducible six months later even after
upstream releases move on.

## Computational layer (deterministic, in `analysis/`)

- Survival: Kaplan-Meier, log-rank, Cox PH (Efron ties correction),
  inverse-variance cross-cohort meta-analysis with automatic fixed-vs-
  random-effects selection on I² > 50%.
- Dependency: one-sided Mann-Whitney selectivity test, rank-biserial effect
  size, pan-essential-gene flag.
- Spatial: Kruskal-Wallis across anatomic zones.
- Multiple testing: Benjamini-Hochberg FDR, applied automatically to any
  multi-gene batch query.

None of this is delegated to an LLM. See `analysis/survival.py`'s docstring
for the one honest caveat: it's a from-scratch implementation (no network
to install `lifelines` in the build sandbox), validated in
`tests/test_survival.py` against hand-computed and simulation-ground-truth
cases — production should swap in `lifelines`/`scikit-survival`.

## AI layer — what it does and does not do

**Does:** query decomposition (`orchestrator/planner.py` — deterministic in
V1, LLM-based from V2 once free-text queries need it, but still only
selecting among the same fixed task primitives, never inventing new ones);
evidence synthesis into prose (`orchestrator/synthesizer.py`); flagging
follow-up experiments (always tagged `AI_GENERATED_INFERENCE`, the weakest
evidence tier that exists).

**Does not:** run or approximate any statistic, invent a citation, or state
a number absent from the dossier. This is enforced, not just requested:
`synthesizer.py::validate_numeric_grounding()` re-parses every AI-authored
sentence and rejects any numeric token that cannot be traced to a real
`EvidenceRecord`. `tests/test_grounding_validator.py` proves this rejection
actually fires on a deliberately fabricated hazard ratio and a fabricated
sample size — see `VALIDATION_REPORT.md`.

In this network-disabled build sandbox, `generate_synthesis()` is a
deterministic template renderer standing in for what should be a real
Claude API call in production (system prompt drafted and included in
`synthesizer.py::CLAUDE_SYNTHESIS_SYSTEM_PROMPT`). The grounding validator
is architected to sit in front of *either* implementation identically —
swapping in the real API call does not weaken the enforcement.

## Evidence model

`evidence_model.py` defines the required distinction from the product
brief as a real, enforced type (`EvidenceTier`): observed data, statistical
association, computational prediction, literature-supported claim,
conflicting evidence, mechanistic hypothesis, AI-generated inference. Every
`EvidenceRecord` carries a `Provenance` (source, version, access tier,
accession IDs, method, parameters, sample size, citation) and a
`ConfidenceLevel` that is explicitly *capped* when the underlying access
tier is synthetic/demo-only — a large-n result on placeholder data is never
allowed to display as "high confidence" (see `build_dossier.py::
_confidence_from_n`, added after the first version of this demo initially
over-stated confidence on synthetic data — see `VALIDATION_REPORT.md`).

## Researcher UX

V1 ships two renderings of the same `Dossier`: machine-readable JSON
(`*_dossier.json`, for programmatic reuse / a future web UI) and a
human-readable Markdown report (`*_report.md`) with per-evidence-tier
sections, inline caveats, and a methods/citation trail suitable for pasting
into a manuscript's methods section. No gamification, no consumer-style
chrome — a researcher should be able to screenshot a section of this
directly into a lab-meeting slide. `api/app.py` exposes the same dossier
over HTTP for a future web front-end without changing any scientific logic.

## Scientific safeguards (implemented, not just described)

- Multiple-testing correction on batch queries (`analysis/multiple_testing.py`,
  exercised in `scripts/run_batch_demo.py`).
- Cross-cohort heterogeneity detection (I² statistic) that actively refuses
  to over-trust a pooled estimate and instead auto-generates a
  `CONFLICTING_EVIDENCE` record (`build_dossier.py::_run_cross_cohort_survival`).
- Pan-essential-gene flag so a "significant" dependency score isn't sold as
  GBM-selective when it isn't (`analysis/dependency.py`).
- Curated, citation-backed cell-culture-artifact flags
  (`knowledge/culture_instability_flags.py`) — deliberately human-curated,
  not AI-inferred, because trusting this list requires trusting that
  someone actually read the primary literature.
- Confidence levels capped by data-access-tier, not just sample size (see
  Evidence model above).
- Every synthetic-data caveat is attached to the specific `EvidenceRecord`
  it affects, not buried in a single disclaimer footer.

## Privacy / legal

All V1 data sources are public and de-identified (no PHI). Two sources
(CGGA, GLASS) require a one-time free registration/data-use agreement per
`SOURCE_REGISTRY` — a compliance task for a named team member, not a
technical blocker. Registration-gated and bulk-download sources are ingested
and cached internally; the engine is designed to re-serve only *derived
statistics* (a hazard ratio, a p-value) from those sources, never raw
patient-level rows, consistent with typical academic data-use terms — see
`SOURCE_REGISTRY[...].license_note` for the specific constraint per source.
Before any public launch, a Rutgers G4G faculty advisor should independently
re-verify each consortium's current data-use terms; this document is not
legal advice.
