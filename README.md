# GBM Gene Analysis

A provenance-tracked glioblastoma gene research tool built for **Rutgers Gray for Glioblastoma**.

Enter a gene such as `EGFR`, `PTEN`, `TERT`, or `CDK6` to assemble a GBM-specific research profile across tumor genomics, functional dependency, spatial expression, independent patient cohorts, longitudinal recurrence, druggability, clinical trials, literature, normal-tissue context, interaction networks, and available blood-brain barrier evidence for target-directed compounds.

The tool is designed to help researchers answer four practical questions:

1. **How strong and selective is the current GBM evidence for this gene?**
2. **Does the signal reproduce across functional, spatial, and independent human datasets?**
3. **What translational opportunities or liabilities are already visible?**
4. **Which evidence gaps are most important to resolve experimentally?**

The Target Priority Score is a transparent research-prioritization heuristic. It is not a clinical prediction model and does not establish treatment benefit or causality.

## Scored evidence sources

- **cBioPortal / TCGA-GBM**: mutation and high-level copy-number evidence
- **Open Targets**: GBM association evidence, tractability, and target-directed candidates
- **DepMap / Chronos**: CRISPR dependency in strict IDH-wildtype GBM models versus the remaining DepMap panel, with a pan-essential safeguard
- **Ivy Glioblastoma Atlas Project**: normalized RNA-seq across seven laser-microdissection GBM anatomic zones
- **CGGA mRNAseq_693 + mRNAseq_325**: independent patient-cohort survival validation restricted to adult primary IDH-wildtype GBM
- **ClinicalTrials.gov API v2**: GBM trials matching the gene and target-directed candidates
- **Europe PMC**: literature volume, publications, and GBM-context coverage
- **GLASS / Synapse**: clinically verified IDH-wildtype GBM primary-to-recurrent longitudinal expression when authorized controlled data are available

## V5 contextual research layers

These layers are intentionally displayed separately and do **not** change the Target Priority Score:

- **MyGene.info**: canonical human gene-symbol and alias resolution
- **Human Protein Atlas**: normal-tissue, normal-brain, single-cell, and single-nuclei brain expression context
- **STRING**: high-confidence protein interaction partners and pathway enrichment
- **B3DB**: experimental blood-brain barrier records for resolvable target-directed candidate compounds
- **GBmap**: direct access to the public IDH-wildtype glioblastoma single-cell and spatial reference collection
- **Evidence consistency review**: source-level discordance and important interpretation flags without treating unrelated evidence types as interchangeable

## Scoring model

V4/V5 preserve nine independently visible scoring dimensions. V5 does not modify the validated score with the new contextual layers.

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

Missing sources reduce **evidence coverage** rather than being converted into negative biological evidence. Synthetic V1 files remain only for deterministic method testing and never increase a live score.

## Data handling

Large Ivy and CGGA source files are downloaded from upstream resources into `data/_cache/` at runtime and are git-ignored. Controlled GLASS files are requested only after authorized Synapse authentication. B3DB is read from its public upstream dataset and cached in memory during a running process. Raw controlled or external matrices are not committed or re-hosted.

## Run the app

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

For authorized GLASS access, configure:

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
PYTHONPATH=. python3 tests/test_glass_gbm_specific.py
PYTHONPATH=. python3 tests/test_research_intelligence_v5.py
```

## Core design rule

Every quantitative claim presented as scored evidence is source-tracked with method, access tier, retrieval metadata, and confidence. A source outage, controlled-access barrier, missing gene, or insufficient cohort is shown explicitly. No placeholder statistic is substituted for missing live evidence.
