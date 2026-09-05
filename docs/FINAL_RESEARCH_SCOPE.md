# GBM Gene Analysis: Final Research Scope

This document freezes the scientific/product scope required before the tool can credibly be described as a differentiated GBM molecular-research decision-support system.

## Product identity

GBM Gene Analysis remains focused on one workflow:

**gene or processed researcher result -> GBM evidence -> biological context -> contradictions -> testable hypothesis -> highest-value experiment**

The product is not a clinical decision system, generic AI scientist, raw sequencing pipeline, imaging platform, pathology system, or broad oncology portal.

## Final six requirements

1. **Native GBM cell-state intelligence**
   - Quantitative GBmap-derived cell-type/state context.
   - Patient prevalence, malignant-versus-microenvironment context, expression breadth, and state/niche concentration.
   - Runtime uses a compact precomputed reference; it must not download the full atlas per query.

2. **Explicit confidence and uncertainty**
   - Every major conclusion receives a confidence grade with transparent reasons.
   - Confidence reflects replication, sample size, evidence type, model relevance, statistical support, consistency, and missing evidence.
   - Hypotheses remain distinct from observed/statistical evidence.

3. **Deep processed-signature interpretation**
   - Researchers may upload processed differential-expression/signature tables, not raw FASTQ/count matrices.
   - Use effect size plus optional p-value/FDR, pathway enrichment, GBM evidence prioritization, contradiction detection, and perturbational reversal.

4. **Model-relevance grading**
   - Functional evidence is explicitly graded by how biologically representative the available model systems are.
   - Conventional adherent cell lines, patient-derived models, 3D/organoid contexts, and in-vivo/human evidence must not be treated as equivalent.

5. **State-aware combination reasoning**
   - Pair analysis deepens the existing rationale-for-testing workflow.
   - It evaluates functional support, network redundancy/complementarity, cell-state coverage, spatial coverage, recurrence relevance, CNS feasibility, and model limitations.
   - It never labels a pair synergistic without direct synergy data.

6. **Retrospective/prospective benchmark framework**
   - The system must be evaluated against a frozen benchmark of known positive, negative, and context-specific GBM research cases.
   - Benchmark outputs include rank, coverage, false-positive behavior, and whether the system surfaces the correct uncertainty.
   - Historical claims require frozen evidence snapshots or date-bounded sources; live-data reruns must never be presented as true retrospective validation.

## Explicit non-goals

Do not add features merely to broaden the product:

- patient treatment recommendations
- prognosis prediction
- radiology or pathology image analysis
- full raw RNA-seq processing
- generic chat assistant
- automatic manuscript writing
- arbitrary omics modalities without a demonstrated decision-support need
- additional databases solely to increase source count
- increasingly complex single master scores

## Definition of done

The product reaches its intended final form when all six requirements above are implemented, scientifically guarded, tested, and usable without destabilizing the production app. Future additions require evidence that they materially improve this same workflow rather than expand scope.