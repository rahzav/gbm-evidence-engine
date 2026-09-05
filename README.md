# GBM Gene Analysis

A provenance-tracked molecular research decision-support system for glioblastoma, developed for **Rutgers Gray for Glioblastoma**.

**Software release: 7.0.0**

GBM Gene Analysis is designed to help researchers move from fragmented evidence to a defensible next experiment. It accepts a gene, a two-target combination, a gene set, or a processed researcher-generated signature and integrates GBM-specific genomic, functional, spatial, human-cohort, longitudinal, translational, literature, tissue, network, blood-brain-barrier, perturbational, and cell-state context.

The system is for **research prioritization and hypothesis development only**. It does not provide clinical recommendations, predict patient benefit, or replace experimental validation.

## Core research workflow

**Evidence → context → contradictions → hypothesis → experiment**

For a gene such as `EGFR`, `PTEN`, `TERT`, or `CDK4`, the system asks:

1. How strong is the current GBM evidence?
2. How confident should a researcher be in that evidence?
3. Does the signal reproduce across independent human and functional datasets?
4. Which GBM cell states and anatomic compartments carry the signal?
5. Does the evidence change at recurrence?
6. Are target-directed compounds or GBM trials already present?
7. Is there measured blood-brain-barrier evidence for resolvable compounds?
8. Where do the evidence layers disagree or leave an important gap?
9. What falsifiable hypothesis follows from that gap?
10. Which experiment would most efficiently reduce the remaining uncertainty?

## Production capabilities

### Gene Analysis

A full gene profile integrates the scored evidence model with contextual and discovery layers. Key outputs include:

- **Target Priority Score** — transparent research-prioritization heuristic
- **Evidence Coverage** — how much of the scored model is currently available
- **Evidence Confidence** — separate assessment of evidence strength and replication
- **Research Opportunities** — cross-source gaps or discordances worth investigating
- **Guarded Mechanistic Hypotheses** — hypotheses shown only when their premises are supported
- **Experiment Prioritization** — follow-up studies ranked by unresolved uncertainty
- **Model Relevance** — distinguishes conventional dependency models from available 3D/next-generation context
- **Cell-State Context** — native compact GBmap reference derived from the published Core GBmap atlas

### Target Pair Analysis

Evaluates whether two targets justify a combination experiment using exactly two complete target profiles. It considers:

- individual target evidence;
- functional-dependency support;
- network overlap/complementarity;
- Ivy GAP spatial complementarity;
- GBmap malignant-state complementarity;
- recurrence coverage;
- translational and CNS feasibility;
- evidence confidence and model relevance.

The **Combination Rationale Score** prioritizes experiments. It is not a pharmacologic-synergy, efficacy, safety, or clinical prediction.

### Researcher Data

Accepts **processed gene-level results**, not raw sequencing files. Supported inputs include a signed effect such as log2 fold-change, model coefficient, or differential CRISPR effect, with optional p-values and FDR values.

The workflow:

1. validates and deduplicates genes;
2. combines effect magnitude with optional statistical support;
3. deeply profiles the highest-priority signals against the GBM evidence stack;
4. reports Target Priority, Evidence Confidence, cell-state context, and Model Relevance;
5. performs STRING pathway enrichment for supported up/down gene programs;
6. queries L1000CDS2 for perturbations predicted to reverse the submitted molecular state;
7. returns perturbational combination hypotheses when the source supplies them.

LINCS/L1000 results are historical cell-line perturbational hypotheses. They do not establish GBM efficacy, CNS exposure, synergy, safety, or patient benefit.

Researcher uploads are processed for the requested analysis and are not written to the repository or an application database by this codebase. Do not upload PHI, PII, controlled raw genomic data, secrets, or restricted material without an approved deployment environment. See `docs/RESEARCHER_DATA_HANDLING.md` for the full boundary.

### Gene Set Comparison

Compares a bounded set of genes through the same production profile architecture while keeping public-source and deployment resource pressure controlled.

### Research Assistant

Provides an evidence-grounded conversational layer over the production workflows. The assistant can build gene dossiers, run target-pair and gene-set analyses, inspect analysis already present in the current session, and retrieve live biomedical publications. Important factual claims are tied to evidence, publication, analysis, or session-context references, and quantitative output is checked against values returned by the underlying tools. The assistant does not redefine production scores or convert hypotheses into evidence.

The assistant uses Groq through its OpenAI-compatible Responses API with function calling. Configure `GROQ_API_KEY`; `GROQ_MODEL` is optional and defaults to `openai/gpt-oss-120b`. The application handles Groq rate-limit responses without falling back to paid usage.

## Scored evidence model

The production release preserves the validated nine-dimension score. Contextual and discovery additions do not silently alter the scalar Target Priority Score.

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

Missing or inaccessible sources lower **Evidence Coverage** rather than being interpreted as negative biology.

## Data sources

### Scored layers

- **cBioPortal / TCGA-GBM** — mutation, recurrent protein-change, and high-level copy-number evidence
- **Open Targets** — GBM association evidence, tractability, and target-directed candidates
- **ClinicalTrials.gov API v2** — GBM trials matching genes and resolved target-directed candidates
- **Europe PMC** — GBM literature volume, contextual coverage, and linked publications
- **DepMap / Chronos** — dependency in strict IDH-wildtype GBM models versus the remaining DepMap panel, with pan-essential safeguards
- **Ivy Glioblastoma Atlas Project** — expression across seven laser-microdissected GBM anatomic structures
- **CGGA mRNAseq_693 + mRNAseq_325** — independent survival validation restricted to adult primary IDH-wildtype GBM
- **GLASS / Synapse** — clinically verified IDH-wildtype GBM primary-to-recurrent expression when authorized data access is configured

### Contextual/non-scoring layers

- **MyGene.info** — canonical human gene and alias resolution
- **Human Protein Atlas** — normal-tissue and normal-brain context
- **STRING** — high-confidence interaction partners and pathway enrichment
- **B3DB** — experimental blood-brain-barrier records for resolvable compounds
- **DepMap model context** — conventional versus available next-generation/3D model metadata
- **GBmap / CELLxGENE** — patient-aware malignant and microenvironment cell-state expression from a compact offline-derived Core GBmap reference
- **L1000CDS2 / LINCS** — perturbational reversal hypotheses for researcher-generated signatures

## Native GBmap architecture

The published Core GBmap H5AD contains hundreds of thousands of cells and is several gigabytes. The interactive application never downloads or materializes that atlas per query.

`scripts/build_gbmap_reference_v3.py` is an offline build step that reads only the published annotation and expression structures needed for production and generates a compact gene-by-state reference containing:

- malignant versus microenvironment class;
- harmonized GBM cell state;
- cells represented in each state;
- patients represented in each state;
- patients with detectable expression of each gene;
- gene-specific patient prevalence within each state;
- fraction of cells expressing the gene;
- mean published expression;
- across-state expression enrichment.

The production asset includes 338,564 cells from 110 patients across 20 annotated states and 27,625 unique gene labels. Duplicate gene labels are preserved as explicit ambiguity rather than silently collapsed. The runtime connector reads only this compact derived reference.

Cell-state expression does not establish dependency, causality, drug response, or clinical utility.

## Scientific guardrails

- Evidence types are not treated as interchangeable.
- Missing data never become negative biology.
- Hypotheses are separated from observed/statistical evidence.
- Selective-dependency hypotheses require actual selective dependency support.
- Pan-essential targets are explicitly flagged.
- Survival associations are not represented as causal effects.
- Combination rationale is not represented as synergy.
- Blood-brain-barrier database absence is not represented as BBB-negative evidence.
- Controlled GLASS data are not scored without authorized, clinically filtered access.
- Current live-data benchmarks are never mislabeled as retrospective prediction.
- Quantitative claims in the evidence dossier retain source, method, access tier, retrieval metadata, confidence, and citation information.

## Reliability and failure behavior

External sources can be unavailable or change independently of this repository. Network calls use bounded retry handling for transient server errors, truncated responses, rate limits, timeouts, and connection resets. Source failure is reported as an evidence gap and reduced coverage rather than substituted with synthetic evidence.

The Streamlit entrypoint executes the single production UI on every rerun, preventing Python module caching from blanking the interface after widget interactions.

## Exports

Gene profiles can be exported as:

- full structured JSON;
- Markdown research summary with evidence gaps, source status, generation time, and linked publications.

Structured production outputs carry software release identifier `7.0.0` so exported dossiers can be traced to the shipped software version.

## API

Run locally:

```bash
uvicorn api.app:app --reload
```

Endpoints:

- `POST /profile`
- `POST /profile/batch`
- `POST /combination`
- `POST /signature`
- `GET /health`

The API reports version `7.0.0` and imports the same production research facade used by the Streamlit application.

## Run the Streamlit app

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

For authorized GLASS access:

```bash
SYNAPSE_AUTH_TOKEN=<authorized-personal-access-token>
```

## Validation

The repository includes deterministic tests for:

- survival/statistical calculations;
- dependency selectivity and pan-essential behavior;
- evidence serialization and provenance;
- fabricated-statistic grounding rejection;
- score coverage behavior;
- strict GBM/IDH-wildtype cohort filtering;
- GLASS safeguards;
- contextual research layers;
- discovery and hypothesis guardrails;
- confidence, model relevance, patient-aware cell-state semantics, publication links, and pair execution efficiency;
- Streamlit rerun behavior;
- API and release contracts.

Pre-release production audits additionally exercise live publication links, representative target profiles, target-pair analysis, researcher-signature/L1000 analysis, benchmark controls, and production UI/API contracts.

A successful software test does not establish biological validity. The bundled benchmark is a current-data regression benchmark, not retrospective prediction evidence. See `docs/RELEASE_VALIDATION.md` for the release gate and the external researcher-validation protocol.

## License and citation

The repository is released under the **MIT License**. Citation metadata are provided in `CITATION.cff` for research use.

## Scope

**GBM molecular research decision support.**

The project intentionally does not expand into clinical treatment recommendations, prognosis prediction, radiology interpretation, pathology-image analysis, raw sequencing pipelines, or generic chatbot functionality. The objective is depth and traceability within GBM molecular target discovery rather than breadth across unrelated clinical workflows.
