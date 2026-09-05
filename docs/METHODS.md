# Methods — GBM Gene Analysis 7.0.0

## Purpose

GBM Gene Analysis is a glioblastoma molecular research decision-support system for evidence synthesis, target prioritization, processed-result interpretation, target-pair evaluation, and experimental planning. It is not a clinical decision-support system.

## Production workflows

The shipped application contains four research workflows:

1. **Gene Analysis** — builds a provenance-tracked dossier for a single gene.
2. **Target Pair Analysis** — evaluates whether two target profiles justify a combination experiment.
3. **Researcher Data** — interprets processed gene-level signed effects with optional p-values/FDR values.
4. **Gene Set Comparison** — compares a bounded set of genes using the same profile architecture.

## Target Priority Score

The Target Priority Score is a transparent research-prioritization heuristic integrating nine scored dimensions:

- TCGA/cBioPortal GBM genomic signal;
- Open Targets disease relevance;
- druggability;
- clinical translation;
- literature/context depth;
- DepMap functional dependency;
- Ivy GAP spatial context;
- independent CGGA human validation;
- GLASS longitudinal recurrence when authorized evidence is available.

Missing sources lower Evidence Coverage. Missing data are not treated as negative biology.

## Evidence Confidence

Evidence Confidence is computed separately from Target Priority. It summarizes the strength and replication of available evidence and is not interpreted as a probability that a target will succeed therapeutically.

## Model Relevance

Functional Model Relevance describes how closely the available dependency systems approximate GBM biology. Conventional cell-line support is distinguished from available next-generation/3D model context. Model relevance does not convert in-vitro dependency into patient-efficacy evidence.

## Native GBmap cell-state reference

The interactive application uses a compact offline-derived reference rather than loading the full Core GBmap atlas per query. The production reference was built from the published Core GBmap asset and contains patient-aware state summaries for 338,564 cells from 110 patients across 20 annotated states and 27,625 unique gene labels.

For each gene/state, the reference records patient prevalence, fraction expressing, mean published expression, and across-state expression enrichment. Duplicate gene labels are preserved as explicit ambiguity rather than silently collapsed.

Cell-state expression is contextual evidence. It does not establish dependency, causality, drug response, or clinical utility.

## Target-pair reasoning

The Combination Rationale Score preserves the established pair heuristic and evaluates individual target quality, functional support, interaction-network complementarity, Ivy GAP spatial complementarity, recurrence coverage, and translational feasibility. GBmap malignant-state complementarity, pair confidence, and model relevance are reported as explicit contextual layers.

The score prioritizes a pair for experimental testing. It is not a synergy, efficacy, safety, or clinical prediction.

## Processed researcher signatures

The Researcher Data workflow accepts processed gene-level signed effects with optional p-values and FDR/q-values. It validates/deduplicates genes, prioritizes supported signals, profiles top genes against the GBM evidence stack, performs STRING pathway enrichment, and can query L1000CDS2 for perturbational reversal hypotheses.

L1000/LINCS results are historical cell-line perturbational hypotheses and do not establish GBM efficacy, CNS exposure, synergy, safety, or patient benefit.

## Provenance and failure behavior

Quantitative evidence records retain source/method metadata, access tier, retrieval information, confidence, and citation fields. External-source failures are surfaced as source gaps and reduced coverage rather than replaced with synthetic evidence.

## Validation terminology

Deterministic scientific/statistical tests, production interaction tests, and current-data benchmark cases validate software behavior and scientific guardrails. They do not establish biological utility.

The bundled benchmark is explicitly a current-data regression benchmark. Retrospective claims require frozen historical evidence snapshots. Prospective claims require hypotheses to be registered before later evidence becomes available.

External researcher evaluation is required before claiming demonstrated research utility. See `docs/RELEASE_VALIDATION.md`.
