"""
orchestrator/build_dossier.py
===============================

The QUERY -> COMPUTE -> CROSS-VALIDATE -> INTERPRET -> CHALLENGE -> TRACE ->
EXPORT pipeline the product brief asks for, wired end to end for the V1
"single-gene evidence dossier" primitive. Every step below either (a) calls
a connector and wraps a real/labeled-synthetic value in an EvidenceRecord,
or (b) calls a deterministic analysis function and wraps ITS output in an
EvidenceRecord. The AI layer (orchestrator/synthesizer.py) only touches the
Dossier after every EvidenceRecord already exists.
"""

from __future__ import annotations
import numpy as np

from gbm_evidence_engine.evidence_model import (
    Dossier, EvidenceRecord, EvidenceTier, ConfidenceLevel, Provenance, AccessTier,
)
from gbm_evidence_engine.connectors.base import SOURCE_REGISTRY
from gbm_evidence_engine.connectors import cohort_survival, ivygap, depmap, b3db, literature_reference
from gbm_evidence_engine.analysis.survival import cox_ph, cross_cohort_meta_analysis
from gbm_evidence_engine.analysis.spatial import anatomic_enrichment_test
from gbm_evidence_engine.analysis.dependency import selective_dependency_test
from gbm_evidence_engine.knowledge.culture_instability_flags import get_flag
from gbm_evidence_engine.orchestrator.planner import plan_single_gene_dossier, TaskType


def _confidence_from_n(n: int, access_tier: AccessTier = AccessTier.OPEN_LIVE_API) -> ConfidenceLevel:
    """Confidence reflects real-world trustworthiness, not just statistical power:
    a large-n result computed on SYNTHETIC or literature-derived demo data is
    capped at MODERATE no matter how tight the p-value looks, because the
    number's reliability is limited by what it was computed FROM, not just its
    sample size. This matters here specifically because this V1 demo run
    computes several "n=300+"-scale statistics on the calibrated synthetic
    cohort described in data/README.md — those should never be displayed as
    'high confidence' the way a real TCGA pull would be."""
    base = (ConfidenceLevel.HIGH if n >= 150 else
            ConfidenceLevel.MODERATE if n >= 50 else
            ConfidenceLevel.LOW if n > 0 else
            ConfidenceLevel.INSUFFICIENT_DATA)
    if access_tier in (AccessTier.SYNTHETIC_ILLUSTRATIVE, AccessTier.DEMO_REFERENCE_VALUE) and base == ConfidenceLevel.HIGH:
        return ConfidenceLevel.MODERATE
    return base


def _run_cross_cohort_survival(dossier: Dossier, gene: str, cohorts: list[str]) -> list[dict]:
    per_cohort_for_meta = []
    cohort_hrs = []
    for cohort in cohorts:
        data = cohort_survival.load_cohort_survival(cohort, gene)
        df = data.df
        gene_col = f"{gene.lower()}_amplified"
        result = cox_ph(
            durations=df["os_months"].to_numpy(),
            events=df["event"].to_numpy(),
            covariates={gene_col: df[gene_col].to_numpy(), "age": df["age"].to_numpy()},
        )
        hr = result.hazard_ratios[gene_col]
        se = result.standard_errors[gene_col]
        p = result.p_values[gene_col]
        ci = result.log_hr_ci95[gene_col]
        ci_hr = (float(np.exp(ci[0])), float(np.exp(ci[1]))) if ci[0] is not None else (None, None)

        src_key = cohort_survival.COHORT_SOURCE_KEY[cohort]
        meta = SOURCE_REGISTRY[src_key]
        rec = dossier.add(EvidenceRecord(
            claim_text=f"{gene} amplification/high-expression status association with overall survival in {cohort}",
            tier=EvidenceTier.STATISTICAL_ASSOCIATION,
            provenance=Provenance(
                source_dataset=meta.name, dataset_version=data.access_tier.value,
                access_tier=data.access_tier, sample_size=data.n,
                method="Cox proportional hazards (Efron ties correction), adjusted for age",
                parameters={"covariates": [gene_col, "age"]},
                citation=meta.license_note,
            ),
            statistic_name="hazard_ratio", statistic_value=hr, p_value=p,
            confidence_interval=ci_hr,
            confidence=_confidence_from_n(data.n, data.access_tier),
        ))
        per_cohort_for_meta.append({"cohort": cohort, "log_hr": result.coefficients[gene_col],
                                     "se": se if se else 1e-6, "n": data.n})
        cohort_hrs.append((cohort, hr, p, data.n))

    meta_result = cross_cohort_meta_analysis(per_cohort_for_meta)
    dossier.add(EvidenceRecord(
        claim_text=f"Cross-cohort meta-analysis of {gene} survival association ({meta_result.model}-effects model)",
        tier=EvidenceTier.STATISTICAL_ASSOCIATION,
        provenance=Provenance(
            source_dataset=f"Pooled: {', '.join(cohorts)}", dataset_version="computed in this session",
            access_tier=AccessTier.SYNTHETIC_ILLUSTRATIVE,
            method="Inverse-variance meta-analysis; DerSimonian-Laird random-effects if I^2 > 50%",
            parameters={"heterogeneity_model_threshold_pct": 50},
            sample_size=sum(c[3] for c in cohort_hrs),
        ),
        statistic_name="pooled_hazard_ratio", statistic_value=meta_result.pooled_hr,
        p_value=meta_result.pooled_p_value, confidence_interval=meta_result.pooled_ci95,
        effect_size=meta_result.i_squared,
        confidence=ConfidenceLevel.MODERATE if meta_result.i_squared < 50 else ConfidenceLevel.LOW,
        caveats=([f"High cross-cohort heterogeneity (I^2={meta_result.i_squared:.0f}%) — "
                  f"do NOT treat the pooled estimate as a single reliable number; report per-cohort "
                  f"results separately."] if meta_result.i_squared > 50 else []),
    ))

    if meta_result.i_squared > 50:
        dossier.warnings.append(
            f"Cross-cohort heterogeneity for {gene} survival association is high (I^2="
            f"{meta_result.i_squared:.0f}%) — cohorts disagree on effect size/direction enough that "
            f"pooling them into one number would be misleading."
        )
        worst = min(cohort_hrs, key=lambda c: 0 if c[2] and c[2] < 0.05 else 1)
        best = max(cohort_hrs, key=lambda c: 0 if c[2] and c[2] < 0.05 else 1)
        dossier.add(EvidenceRecord(
            claim_text=(f"{gene} survival association is significant in some cohorts but not others "
                        f"(computed in this session on calibrated demo data): "
                        + "; ".join(f"{c[0]}: HR={c[1]:.2f}, p={c[2]:.3f}, n={c[3]}" for c in cohort_hrs)),
            tier=EvidenceTier.CONFLICTING_EVIDENCE,
            provenance=Provenance(
                source_dataset="Cross-cohort comparison (this session)", dataset_version="computed",
                access_tier=AccessTier.SYNTHETIC_ILLUSTRATIVE,
                method="Direct comparison of per-cohort Cox p-values at alpha=0.05",
            ),
            confidence=ConfidenceLevel.MODERATE,
        ))
    return cohort_hrs


def _run_spatial_enrichment(dossier: Dossier, gene: str):
    data = ivygap.load_zone_expression(gene)
    result = anatomic_enrichment_test(gene, data.zone_expression)
    meta = SOURCE_REGISTRY["ivygap"]
    dossier.add(EvidenceRecord(
        claim_text=f"{gene} expression varies across GBM anatomic/histologic zones; highest in {result.top_zone}",
        tier=EvidenceTier.STATISTICAL_ASSOCIATION,
        provenance=Provenance(
            source_dataset=meta.name, dataset_version=data.dataset_version,
            access_tier=data.access_tier, sample_size=result.n_samples_total,
            method="Kruskal-Wallis H-test across 7 laser-microdissected anatomic zones",
            parameters={"zones": result.zones},
        ),
        statistic_name="H_statistic", statistic_value=result.h_statistic, p_value=result.p_value,
        confidence=_confidence_from_n(result.n_samples_total, data.access_tier),
        caveats=["Demo run on SYNTHETIC calibrated zone data, not the real Ivy GAP release — "
                 "see data/README.md. Do not treat 'top_zone' as a real biological claim about this gene."],
    ))


def _run_dependency(dossier: Dossier, gene: str):
    data = depmap.load_gene_effect_scores(gene)
    result = selective_dependency_test(gene, data.gbm_scores.to_numpy(), data.other_scores.to_numpy())
    meta = SOURCE_REGISTRY["depmap"]
    caveats = []
    flag = get_flag(gene)
    if flag:
        caveats.append(flag.note)
    if result.pan_essential:
        caveats.append("Flagged as broadly pan-essential across lineages in this data — a low p-value "
                        "here would NOT indicate GBM-selective vulnerability; interpret with caution.")
    dossier.add(EvidenceRecord(
        claim_text=(f"{gene} dependency (CRISPR gene-effect score) in GBM-lineage lines "
                    f"vs. other lineages: median {result.median_effect_gbm:.2f} vs {result.median_effect_other:.2f}"),
        tier=EvidenceTier.STATISTICAL_ASSOCIATION,
        provenance=Provenance(
            source_dataset=meta.name, dataset_version=data.dataset_version,
            access_tier=data.access_tier,
            sample_size=result.n_gbm_lines + result.n_other_lines,
            method="One-sided Mann-Whitney U test (GBM more dependent), rank-biserial effect size",
            parameters={"n_gbm_lines": result.n_gbm_lines, "n_other_lines": result.n_other_lines},
        ),
        statistic_name="U_statistic", statistic_value=result.u_statistic, p_value=result.p_value,
        effect_size=result.rank_biserial_effect_size,
        confidence=_confidence_from_n(result.n_gbm_lines, data.access_tier),
        caveats=caveats,
        additional_stats={"median_effect_gbm": result.median_effect_gbm,
                           "median_effect_other": result.median_effect_other},
    ))
    if flag:
        dossier.warnings.append(f"{gene}: {flag.note}")


def _run_bbb_and_drugs(dossier: Dossier, gene: str):
    # Known GBM-relevant compounds for this demo's gene (EGFR pathway) — see data/b3db_reference_subset.csv
    compounds = ["Temozolomide", "Osimertinib", "Erlotinib", "Gefitinib", "Lapatinib", "Afatinib", "JCN037"]
    meta = SOURCE_REGISTRY["b3db"]
    for compound in compounds:
        result = b3db.lookup_compound(compound)
        if not result.found:
            continue
        dossier.add(EvidenceRecord(
            claim_text=f"{compound}: {result.evidence_note}",
            tier=EvidenceTier.LITERATURE_SUPPORTED_CLAIM,
            provenance=Provenance(
                source_dataset=meta.name, dataset_version="hand-curated real subset, see data/README.md",
                access_tier=meta.access_tier, citation=result.citation,
            ),
            confidence=ConfidenceLevel.MODERATE,
        ))


def _run_literature(dossier: Dossier, gene: str):
    data = literature_reference.load_reference_facts(gene)
    for fact in data.get("facts", []):
        is_conflict = "CONFLICTING" in fact["claim"]
        ci = tuple(fact["confidence_interval"]) if "confidence_interval" in fact else None
        dossier.add(EvidenceRecord(
            claim_text=fact["claim"],
            tier=EvidenceTier.CONFLICTING_EVIDENCE if is_conflict else EvidenceTier.LITERATURE_SUPPORTED_CLAIM,
            provenance=Provenance(
                source_dataset="Literature (Europe PMC-indexed sources, retrieved via live web search this session)",
                dataset_version="see source_urls", access_tier=AccessTier.OPEN_LIVE_API,
                citation=fact["citation"], citation_url=fact["source_urls"][0] if fact.get("source_urls") else None,
                sample_size=fact.get("sample_size"),
            ),
            statistic_name=fact.get("statistic_name"), statistic_value=fact.get("statistic_value"),
            p_value=fact.get("p_value"), confidence_interval=ci,
            confidence=ConfidenceLevel.HIGH,
        ))


def _run_ai_inference(dossier: Dossier, gene: str):
    flag = get_flag(gene)
    if flag:
        dossier.add(EvidenceRecord(
            claim_text=(f"Given documented in-vitro instability of {flag.alteration}, prioritize "
                        f"validating {gene}-targeted compounds in patient-derived xenograft or "
                        f"serum-free spheroid models over long-established adherent cell lines."),
            tier=EvidenceTier.AI_GENERATED_INFERENCE,
            provenance=Provenance(
                source_dataset="AI synthesis layer (this session)", dataset_version="n/a",
                access_tier=AccessTier.SYNTHETIC_ILLUSTRATIVE,
                method="Rule-triggered suggestion: culture-instability flag present for this gene",
            ),
            confidence=ConfidenceLevel.LOW,
        ))


def build_single_gene_dossier(gene: str, cohorts: list[str] | None = None) -> Dossier:
    plan = plan_single_gene_dossier(gene, cohorts)
    dossier = Dossier(query=f"Evidence dossier for {gene} in glioblastoma", target=gene)

    if TaskType.CROSS_COHORT_SURVIVAL in plan.tasks:
        _run_cross_cohort_survival(dossier, gene, plan.cohorts)
    if TaskType.SPATIAL_ENRICHMENT in plan.tasks:
        _run_spatial_enrichment(dossier, gene)
    if TaskType.DEPENDENCY_SELECTIVITY in plan.tasks:
        _run_dependency(dossier, gene)
    if TaskType.BBB_LOOKUP in plan.tasks:
        _run_bbb_and_drugs(dossier, gene)
    if TaskType.LITERATURE_SUPPORT in plan.tasks:
        _run_literature(dossier, gene)
    _run_ai_inference(dossier, gene)

    return dossier
