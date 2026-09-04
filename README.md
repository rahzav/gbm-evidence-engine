# GBM Gene Analysis

A provenance-tracked glioblastoma research system built for **Rutgers Gray for Glioblastoma**.

The core workflow begins with a gene such as `EGFR`, `PTEN`, `TERT`, or `CDK6`, but V6 is designed to go beyond target lookup. It integrates GBM evidence, detects cross-source research opportunities, generates falsifiable mechanistic hypotheses, prioritizes experiments that could resolve the largest uncertainties, evaluates two-target combinations, and interprets researcher-provided signed gene signatures against GBM evidence and LINCS perturbational data.

## What V6 is designed to answer

1. **How strong and selective is the current GBM evidence for this gene?**
2. **Where do independent evidence layers agree, conflict, or leave translational whitespace?**
3. **What biological mechanism is worth testing next, and what result would falsify it?**
4. **Which experiment would most reduce uncertainty before additional resources are committed?**
5. **Do two targets provide a defensible complementary-target experiment?**
6. **Which genes and perturbations are most interesting in a researcher's own expression signature?**

The Target Priority Score remains a transparent research-prioritization heuristic. V6 discovery outputs are kept separate from that score unless they directly reproduce a validated scored evidence layer.

## Scored evidence sources

- **cBioPortal / TCGA-GBM**: mutation, recurrent protein-change, and high-level copy-number evidence
- **Open Targets**: GBM association evidence, tractability, and target-directed candidates
- **DepMap / Chronos**: CRISPR dependency in strict IDH-wildtype GBM models versus the remaining DepMap panel, with a pan-essential safeguard
- **Ivy Glioblastoma Atlas Project**: normalized RNA-seq across seven laser-microdissection GBM anatomic zones
- **CGGA mRNAseq_693 + mRNAseq_325**: independent survival validation restricted to adult primary IDH-wildtype GBM
- **ClinicalTrials.gov API v2**: GBM trials matching the gene and target-directed candidates
- **Europe PMC**: literature volume, publications, and GBM-context coverage
- **GLASS / Synapse**: clinically verified IDH-wildtype GBM primary-to-recurrent expression when authorized controlled data are available

## Contextual research layers

These layers are displayed separately and do **not** alter the validated Target Priority Score:

- **MyGene.info**: canonical human gene-symbol and alias resolution
- **Human Protein Atlas**: normal-tissue, normal-brain, single-cell, and single-nuclei brain context
- **STRING**: high-confidence protein interaction partners and pathway enrichment
- **B3DB**: experimental blood-brain barrier records for resolvable target-directed compounds
- **DepMap NextGen context**: 3D/organoid/spheroid model-format context when the live model metadata exposes it
- **GBmap**: direct access to the public IDH-wildtype GBM single-cell and spatial reference collection
- **Evidence consistency review**: source-level discordance and interpretation flags

## V6 discovery capabilities

### Cross-source research opportunities

The engine looks for patterns that are often more useful than a high scalar score alone, including:

- strong functional dependency with weak recurrent genomic selection;
- strong genomic selection without matching selective dependency;
- high druggability with weak GBM clinical translation;
- recurrence-associated signal with limited development;
- spatially localized signal suggesting niche-conditioned biology;
- prognostic association without matching functional dependency;
- target-directed compounds with little matched BBB evidence;
- normal-brain expression that raises therapeutic-window questions;
- missing high-weight evidence that makes the current conclusion unstable.

Each opportunity includes the signal that triggered it, a specific validation experiment, and a caveat explaining what the observation does **not** establish.

### Falsifiable mechanistic hypotheses

Dependency, spatial, longitudinal, STRING-network, and pathway-enrichment observations are converted into explicit hypotheses with a defined falsification test. These are hypothesis-generation outputs and are not represented as causal conclusions.

### Experiment prioritization

V6 ranks follow-up experiments according to unresolved evidence, cross-source contradiction, and the weight of the affected evidence dimension. The resulting **Experiment Priority** is an uncertainty-reduction heuristic, not a formal expected-information-gain estimate.

### Target Pair Analysis

Researchers can evaluate two genes together. The **Combination Rationale Score** summarizes:

- individual target evidence;
- functional-dependency support;
- network complementarity;
- spatial/niche complementarity;
- recurrence coverage;
- translational feasibility.

This score prioritizes whether a pair is worth experimentally testing. It is explicitly **not** a pharmacologic synergy, efficacy, or safety prediction.

### Researcher Signature Analysis

Researchers can upload or paste a signed gene-level result such as log2 fold-change, a model coefficient, a CRISPR differential effect, or another signed statistic. V6 then:

1. identifies the strongest signals;
2. builds full GBM profiles for the leading genes;
3. combines uploaded-signal magnitude with existing GBM evidence into a within-signature Discovery Priority;
4. submits the signed signature to the public **L1000CDS2** endpoint;
5. returns LINCS-derived perturbations predicted to reverse the state;
6. surfaces L1000 pairwise drug-combination hypotheses when returned by the source.

LINCS/L1000 outputs are perturbational hypotheses derived from cell-line signatures. They require GBM-specific validation and do not establish CNS exposure, efficacy, clinical benefit, or true drug synergy.

## Scoring model

V6 preserves the nine V4/V5 scored dimensions without adding the discovery layers to the scalar score.

| Dimension | Weight |
|---|---:|
| TCGA GBM genomic signal | 16.9% |
| Open Targets GBM disease relevance | 13.2% |
| Druggability | 13.2% |
| Clinical translation | 11.3% |
| Literature/context depth | 9.4% |
| DepMap functional dependency | 15.0% |
| Ivy GAP spatial context | 7.5% |
| Independent CGGA human validation | 7.5% |
| GLASS longitudinal recurrence | 6.0% |

Missing sources reduce **evidence coverage** rather than being converted into negative biological evidence.

## Single-cell infrastructure

GBmap is publicly available through CELLxGENE and contains a large harmonized IDH-wildtype GBM single-cell/spatial collection. The public Streamlit deployment currently links GBmap rather than downloading the full >1M-cell atlas during each query. A production-grade native single-cell layer should use a compact precomputed/queryable GBmap service so cell-state and spatial gene statistics are reproducible without destabilizing the public app.

## Data handling

Large Ivy and CGGA source files are downloaded from upstream resources into `data/_cache/` at runtime and are git-ignored. Controlled GLASS files are requested only after authorized Synapse authentication. B3DB is read from its public upstream dataset. Researcher-uploaded signatures are processed in the running Streamlit session and are not committed to the repository.

## Run the app

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

For authorized GLASS access:

```bash
SYNAPSE_AUTH_TOKEN=<authorized-personal-access-token>
```

## API

```bash
uvicorn api.app:app --reload
```

- `POST /profile` with `{"gene":"EGFR"}`
- `POST /profile/batch` with `{"genes":["EGFR","PTEN","TERT"]}`
- `POST /combination` with `{"gene_a":"EGFR","gene_b":"CDK4"}`
- `POST /signature` with `{"genes":[...],"values":[...]}`
- `GET /health`

## Tests

```bash
PYTHONPATH=. python3 tests/test_survival.py
PYTHONPATH=. python3 tests/test_dependency.py
PYTHONPATH=. python3 tests/test_evidence_model.py
PYTHONPATH=. python3 tests/test_grounding_validator.py
PYTHONPATH=. python3 tests/test_research_intelligence.py
PYTHONPATH=. python3 tests/test_research_intelligence_v3.py
PYTHONPATH=. python3 tests/test_glass_gbm_specific.py
PYTHONPATH=. python3 tests/test_research_intelligence_v5.py
PYTHONPATH=. python3 tests/test_research_intelligence_v6.py
```

## Core design rule

Every quantitative claim presented as scored evidence is source-tracked with method, access tier, retrieval metadata, and confidence. A source outage, controlled-access barrier, missing gene, or insufficient cohort is shown explicitly. V6 discovery heuristics are labeled as heuristics and kept separate from directly observed or statistically estimated evidence. No placeholder statistic is substituted for missing live evidence.
