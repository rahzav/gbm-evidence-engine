"""Research-grade GBM intelligence layer.

V3 preserves the validated live-first V2 core and adds three new scored layers:
DepMap functional dependency, Ivy GAP spatial expression, and independent CGGA
human-cohort validation. GLASS longitudinal expression is operational behind
controlled Synapse access but is not allowed to affect the GBM score until a
GBM-specific clinical/subtype filter is available.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from math import log10, log
from typing import Any

from gbm_evidence_engine.evidence_model import (
    AccessTier,
    ConfidenceLevel,
    EvidenceRecord,
    EvidenceTier,
    Provenance,
)
from gbm_evidence_engine.research_intelligence import (
    ResearchProfile,
    ScoreDimension,
    TargetPriorityScore,
    build_research_profile as build_v2_profile,
)
from gbm_evidence_engine.connectors import depmap, ivygap, cgga, glass


def _clamp(x: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(x)))


def _advanced_dimensions(base: ResearchProfile, dep: dict, ivy: dict, cgg: dict) -> dict[str, ScoreDimension]:
    old = base.score.dimensions
    dims: dict[str, ScoreDimension] = {}
    remap = [
        ("GBM genomic signal", 0.18),
        ("GBM disease relevance", 0.14),
        ("Druggability", 0.14),
        ("Clinical translation", 0.12),
        ("Literature/context depth", 0.10),
    ]
    for name, weight in remap:
        prior = old.get(name)
        if prior:
            dims[name] = ScoreDimension(prior.score, weight, prior.rationale, prior.source)
        else:
            dims[name] = ScoreDimension(None, weight, "V2 source dimension unavailable.", "V2 live evidence")

    if dep.get("ok"):
        if dep.get("pan_essential"):
            dep_score = 5.0
            rationale = (
                f"Strict GBM median Chronos={dep['median_effect_gbm']:.2f} across n={dep['n_gbm']}, but the target is "
                "pan-essential across the broader DepMap panel; therapeutic selectivity is therefore poor."
            )
        else:
            delta = float(dep.get("median_selectivity_delta") or 0.0)
            rbe = float(dep.get("rank_biserial_effect_size") or 0.0)
            gbm_essential = float(dep.get("gbm_fraction_below_minus_0_5") or 0.0)
            delta_component = _clamp(delta / 0.60 * 100.0)
            effect_component = _clamp(rbe * 100.0)
            essential_component = _clamp(gbm_essential * 100.0)
            dep_score = 0.45 * delta_component + 0.35 * effect_component + 0.20 * essential_component
            if int(dep.get("n_gbm") or 0) < 8:
                dep_score *= max(0.4, int(dep.get("n_gbm") or 0) / 8.0)
            rationale = (
                f"Strict IDH-wildtype GBM n={dep['n_gbm']}: median Chronos {dep['median_effect_gbm']:.2f} vs "
                f"{dep['median_effect_other']:.2f} outside GBM; selectivity delta {delta:.2f}, rank-biserial {rbe:.2f}."
            )
        dims["Functional dependency"] = ScoreDimension(_clamp(dep_score), 0.16, rationale, "DepMap Breadbox / Chronos")
    else:
        dims["Functional dependency"] = ScoreDimension(None, 0.16, dep.get("error", "DepMap dependency unavailable."), "DepMap")

    if ivy.get("ok"):
        spread = float(ivy.get("median_range") or 0.0)
        p = max(float(ivy.get("p_value") or 1.0), 1e-300)
        gradient = _clamp(spread / 2.0 * 100.0)
        significance = _clamp((-log10(p)) / 6.0 * 100.0)
        spatial_score = 0.65 * gradient + 0.35 * significance
        dims["Spatial context signal"] = ScoreDimension(
            _clamp(spatial_score), 0.08,
            f"Ivy GAP n={ivy['n_samples']}; top zone {ivy['top_zone'].replace('_', ' ')}; median log2(FPKM+1) range {spread:.2f}; Kruskal p={p:.2g}.",
            "Ivy Glioblastoma Atlas Project",
        )
    else:
        dims["Spatial context signal"] = ScoreDimension(None, 0.08, ivy.get("error", "Ivy GAP spatial data unavailable."), "Ivy GAP")

    if cgg.get("ok"):
        meta = cgg.get("meta_analysis")
        usable = int(cgg.get("n_usable_cohorts") or 0)
        if meta:
            p = max(float(meta.get("pooled_p_value") or 1.0), 1e-300)
            magnitude = _clamp(abs(float(meta.get("pooled_log_hr") or 0.0)) / log(1.8) * 100.0)
            significance = _clamp((-log10(p)) / 3.0 * 100.0)
            consistency = 100.0 if cgg.get("direction_consistent") else 20.0
            human_score = 0.30 * magnitude + 0.45 * significance + 0.25 * consistency
            rationale = (
                f"{usable} strict adult primary IDH-wildtype GBM cohorts; pooled HR per 1-SD expression="
                f"{meta['pooled_hr']:.2f}, p={p:.2g}, I²={meta['i_squared']:.0f}%; direction "
                f"{'consistent' if cgg.get('direction_consistent') else 'discordant'}."
            )
        else:
            row = next((r for r in cgg.get("cohorts", []) if r.get("ok")), {})
            p = max(float(row.get("p_value") or 1.0), 1e-300)
            magnitude = _clamp(abs(float(row.get("log_hr_per_sd") or 0.0)) / log(1.8) * 100.0)
            significance = _clamp((-log10(p)) / 3.0 * 100.0)
            human_score = 0.60 * (0.55 * magnitude + 0.45 * significance)
            rationale = f"Only {usable} strict CGGA GBM cohort was usable; this is partial external validation, not replication."
        dims["Independent human validation"] = ScoreDimension(_clamp(human_score), 0.08, rationale, "CGGA 693 + 325")
    else:
        dims["Independent human validation"] = ScoreDimension(None, 0.08, "; ".join(cgg.get("errors") or []) or "CGGA validation unavailable.", "CGGA")

    return dims


def _score_from_dimensions(dims: dict[str, ScoreDimension]) -> TargetPriorityScore:
    total_weight = sum(d.weight for d in dims.values())
    available = [(d.score, d.weight) for d in dims.values() if d.score is not None]
    covered_weight = sum(weight for _, weight in available)
    coverage = 100.0 * covered_weight / total_weight if total_weight else 0.0
    if not available:
        overall = None
    else:
        raw = sum(float(score) * weight for score, weight in available) / covered_weight
        # Coverage discount is deliberately mild: missing sources reduce confidence,
        # but a source outage is not biological negative evidence.
        adjusted = raw * (0.82 + 0.18 * coverage / 100.0)
        overall = round(_clamp(adjusted), 1)
    if overall is None:
        label = "Insufficient live evidence"
    elif overall >= 75:
        label = "High-priority research signal"
    elif overall >= 55:
        label = "Promising / context-dependent"
    elif overall >= 35:
        label = "Mixed evidence"
    else:
        label = "Low current prioritisation signal"
    return TargetPriorityScore(
        overall=overall,
        evidence_coverage_pct=round(coverage, 1),
        dimensions=dims,
        label=label,
        caveat=(
            "Research-prioritisation heuristic only. Functional, spatial and survival signals are not interchangeable: "
            "the score ranks evidence density/selectivity and does not predict patient benefit or establish causality."
        ),
    )


def _add_advanced_evidence(profile: ResearchProfile, dep: dict, ivy: dict, cgg: dict, gla: dict) -> None:
    dossier = profile.dossier
    gene = profile.gene
    if dep.get("ok"):
        dossier.add(EvidenceRecord(
            claim_text=f"{gene} selective CRISPR dependency in strict IDH-wildtype GBM models versus the remaining DepMap panel",
            tier=EvidenceTier.STATISTICAL_ASSOCIATION,
            provenance=Provenance(
                source_dataset="DepMap Breadbox — Chronos_Combined",
                dataset_version="live public dataset",
                access_tier=AccessTier.OPEN_LIVE_API,
                sample_size=int(dep.get("n_gbm") or 0),
                method="One-sided Mann-Whitney U: GBM Chronos gene effect < non-GBM; pan-essential safeguard",
                parameters={"gbm_subtype": dep.get("gbm_definition"), "n_other": dep.get("n_other")},
                citation_url="https://depmap.org/portal/",
            ),
            statistic_name="median_chronos_gbm",
            statistic_value=float(dep["median_effect_gbm"]),
            p_value=float(dep["p_value"]),
            effect_size=float(dep["rank_biserial_effect_size"]),
            additional_stats={
                "median_chronos_other": float(dep["median_effect_other"]),
                "median_selectivity_delta": float(dep["median_selectivity_delta"]),
                "gbm_fraction_effect_below_minus_0_5": float(dep["gbm_fraction_below_minus_0_5"]),
            },
            confidence=ConfidenceLevel.HIGH if int(dep.get("n_gbm") or 0) >= 10 else ConfidenceLevel.MODERATE,
            caveats=(["Pan-essential target: broad viability effects sharply limit therapeutic-selectivity interpretation."] if dep.get("pan_essential") else []),
        ))

    if ivy.get("ok"):
        dossier.add(EvidenceRecord(
            claim_text=f"{gene} expression differs across Ivy GAP GBM anatomic compartments; highest median in {ivy['top_zone'].replace('_', ' ')}",
            tier=EvidenceTier.STATISTICAL_ASSOCIATION,
            provenance=Provenance(
                source_dataset="Ivy Glioblastoma Atlas Project normalized RNA-seq",
                dataset_version="official normalized FPKM snapshot / download 305873915",
                access_tier=AccessTier.OPEN_BULK_DOWNLOAD,
                sample_size=int(ivy.get("n_samples") or 0),
                method="Kruskal-Wallis across seven laser-microdissection anatomic zones on log2(FPKM+1)",
                citation_url="https://glioblastoma.alleninstitute.org/",
            ),
            statistic_name="kruskal_h",
            statistic_value=float(ivy["kruskal_h"]),
            p_value=float(ivy["p_value"]),
            effect_size=float(ivy.get("median_range") or 0.0),
            confidence=ConfidenceLevel.MODERATE,
            caveats=["Spatial enrichment is contextual evidence, not proof that the target is therapeutically actionable; Ivy samples include marker-guided LMD regions."],
        ))

    for row in cgg.get("cohorts", []):
        if not row.get("ok"):
            continue
        dossier.add(EvidenceRecord(
            claim_text=f"{gene} continuous-expression survival association in {row['cohort']} strict adult primary IDH-wildtype GBM",
            tier=EvidenceTier.STATISTICAL_ASSOCIATION,
            provenance=Provenance(
                source_dataset=row["cohort"],
                dataset_version="CGGA 2020-05-06 RSEM/clinical snapshot",
                access_tier=AccessTier.OPEN_BULK_DOWNLOAD,
                sample_size=int(row["n"]),
                method="Univariable Cox PH, log2(FPKM+1) standardized; HR per 1 SD",
                parameters={"subset": row.get("subset"), "events": row.get("events")},
                citation_url="https://www.cgga.org.cn/download.jsp",
            ),
            statistic_name="hazard_ratio_per_sd_expression",
            statistic_value=float(row["hr_per_sd"]),
            p_value=float(row["p_value"]) if row.get("p_value") is not None else None,
            effect_size=float(row["log_hr_per_sd"]),
            confidence_interval=tuple(row["ci95_hr"]) if row.get("ci95_hr") else None,
            confidence=ConfidenceLevel.MODERATE,
            caveats=["Prognostic association does not establish target causality, drug sensitivity, or treatment benefit."],
        ))
    meta = cgg.get("meta_analysis")
    if meta:
        dossier.add(EvidenceRecord(
            claim_text=f"Cross-cohort CGGA meta-analysis of {gene} expression and survival in strict adult primary IDH-wildtype GBM",
            tier=EvidenceTier.STATISTICAL_ASSOCIATION,
            provenance=Provenance(
                source_dataset="CGGA mRNAseq_693 + mRNAseq_325",
                dataset_version="2020-05-06 snapshots",
                access_tier=AccessTier.OPEN_BULK_DOWNLOAD,
                method=f"Inverse-variance {meta['model']}-effect meta-analysis of per-cohort Cox log-HRs",
                parameters={"i_squared": meta["i_squared"], "direction_consistent": cgg.get("direction_consistent")},
                citation_url="https://www.cgga.org.cn/download.jsp",
            ),
            statistic_name="pooled_hazard_ratio_per_sd_expression",
            statistic_value=float(meta["pooled_hr"]),
            p_value=float(meta["pooled_p_value"]),
            effect_size=float(meta["pooled_log_hr"]),
            confidence_interval=tuple(meta["pooled_ci95"]),
            confidence=ConfidenceLevel.MODERATE,
            caveats=["This is external prognostic replication, not evidence that perturbing the target changes survival."],
        ))

    if gla.get("ok"):
        dossier.add(EvidenceRecord(
            claim_text=f"{gene} paired primary-to-recurrent expression change in authorized GLASS diffuse-glioma samples",
            tier=EvidenceTier.STATISTICAL_ASSOCIATION,
            provenance=Provenance(
                source_dataset="GLASS gene TPM matrix",
                dataset_version=f"{gla.get('entity_id')} v{gla.get('entity_version')}",
                access_tier=AccessTier.REGISTRATION_GATED,
                sample_size=int(gla.get("n_pairs") or 0),
                method="Paired Wilcoxon signed-rank on log2(TPM+1), TP vs first recurrence",
                citation_url="https://www.synapse.org/",
            ),
            statistic_name="median_recurrent_minus_primary_log2_tpm",
            statistic_value=float(gla.get("median_delta") or 0.0),
            p_value=float(gla.get("p_value") or 1.0),
            confidence=ConfidenceLevel.MODERATE,
            caveats=["Current GLASS matrix result is diffuse-glioma-wide and is therefore shown as longitudinal context but excluded from the GBM priority score until subtype-specific clinical filtering is added."],
        ))


def _augment_gaps_and_experiments(profile: ResearchProfile, dep: dict, ivy: dict, cgg: dict, gla: dict) -> None:
    profile.evidence_gaps = [g for g in profile.evidence_gaps if "Real DepMap dependency" not in g]
    if not dep.get("ok"):
        profile.evidence_gaps.append(f"DepMap functional dependency unavailable: {dep.get('error', 'unknown error')}")
    elif dep.get("pan_essential"):
        profile.evidence_gaps.append("DepMap flags the target as pan-essential, so a tumor-selective therapeutic window remains unproven.")
    if not ivy.get("ok"):
        profile.evidence_gaps.append(f"Ivy GAP spatial-expression layer unavailable: {ivy.get('error', 'unknown error')}")
    if not cgg.get("ok"):
        profile.evidence_gaps.append("Independent CGGA GBM validation could not be estimated in either cohort.")
    elif int(cgg.get("n_usable_cohorts") or 0) < 2:
        profile.evidence_gaps.append("Only one CGGA cohort yielded a usable strict-GBM survival estimate; replication remains incomplete.")
    elif (cgg.get("meta_analysis") or {}).get("i_squared", 0) > 50:
        profile.evidence_gaps.append("CGGA cross-cohort survival estimates are heterogeneous (I² > 50%); cohort-specific biology or technical effects need resolution.")
    if gla.get("status") == "credentials_required":
        profile.evidence_gaps.append("GLASS longitudinal ingestion is implemented but controlled-access data are disabled until an authorized SYNAPSE_AUTH_TOKEN is configured.")
    elif gla.get("ok"):
        profile.evidence_gaps.append("GLASS longitudinal expression is currently diffuse-glioma-wide; a controlled GBM-specific clinical filter is still required before scoring it.")

    ideas = list(profile.next_experiments)
    if dep.get("ok") and not dep.get("pan_essential") and float(dep.get("median_selectivity_delta") or 0) > 0.15:
        ideas.insert(0, f"Validate the DepMap-selective {profile.gene} dependency in IDH-wildtype patient-derived GBM stem-like models with perturbation/rescue and non-neoplastic neural controls.")
    if ivy.get("ok"):
        ideas.append(f"Test whether the {profile.gene} dependency is retained in models that reproduce the Ivy GAP {ivy['top_zone'].replace('_', ' ')} niche, rather than only standard bulk culture.")
    if cgg.get("meta_analysis"):
        ideas.append(f"Separate prognostic correlation from mechanism for {profile.gene}: stratify perturbation effects by the molecular covariates represented in CGGA instead of treating the pooled survival HR as causal evidence.")
    profile.next_experiments = list(dict.fromkeys(ideas))[:7]


def build_research_profile(gene: str) -> ResearchProfile:
    gene = gene.strip().upper()
    with ThreadPoolExecutor(max_workers=5) as ex:
        f_base = ex.submit(build_v2_profile, gene)
        f_dep = ex.submit(depmap.summarize_gene_dependency, gene)
        f_ivy = ex.submit(ivygap.summarize_spatial_expression, gene)
        f_cgga = ex.submit(cgga.summarize_external_validation, gene)
        f_glass = ex.submit(glass.summarize_longitudinal_expression, gene)
        base = f_base.result()
        dep = f_dep.result()
        ivy = f_ivy.result()
        cgg = f_cgga.result()
        gla = f_glass.result()

    _add_advanced_evidence(base, dep, ivy, cgg, gla)
    base.score = _score_from_dimensions(_advanced_dimensions(base, dep, ivy, cgg))
    _augment_gaps_and_experiments(base, dep, ivy, cgg, gla)
    base.live.update({"depmap": dep, "ivy_gap": ivy, "cgga": cgg, "glass": gla})
    base.source_status.update({
        "DepMap": "live Breadbox" if dep.get("ok") else "unavailable",
        "Ivy GAP": "public normalized RNA-seq snapshot" if ivy.get("ok") else "unavailable",
        "CGGA": f"{cgg.get('n_usable_cohorts', 0)}/2 public cohorts usable" if cgg.get("ok") else "unavailable",
        "GLASS": ("authorized longitudinal context" if gla.get("ok") else "credentials required" if gla.get("status") == "credentials_required" else gla.get("status", "unavailable")),
    })
    return base


def rank_gene_list(genes: list[str], max_workers: int = 2) -> list[ResearchProfile]:
    cleaned = list(dict.fromkeys(g.strip().upper() for g in genes if g.strip()))
    workers = max(1, min(int(max_workers), 2))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        profiles = list(ex.map(build_research_profile, cleaned))
    return sorted(profiles, key=lambda p: (p.score.overall is not None, p.score.overall or -1), reverse=True)
