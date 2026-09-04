"""V4 GBM research intelligence with strict GLASS longitudinal scoring.

V4 extends the validated V3 profile. GLASS contributes only when its controlled
clinical metadata proves that the analyzed primary/recurrent pairs are
IDH-wildtype glioblastoma. Missing credentials or non-GBM longitudinal data
reduce evidence coverage; they are never interpreted as negative biology.
"""
from __future__ import annotations

from math import log10

from gbm_evidence_engine.research_intelligence import ScoreDimension, TargetPriorityScore, ResearchProfile
from gbm_evidence_engine.research_intelligence_v3 import (
    build_research_profile as build_v3_profile,
    rank_gene_list as _rank_v3_unused,
)


def _clamp(x: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(x)))


def _glass_dimension(gla: dict) -> ScoreDimension:
    if not gla.get("ok") or not gla.get("gbm_specific"):
        if gla.get("status") == "credentials_required":
            rationale = "Controlled GLASS GBM longitudinal data require an authorized Synapse token."
        elif gla.get("gbm_specific") and gla.get("status") == "insufficient_gbm_pairs":
            rationale = gla.get("error", "Too few clinically verified GLASS GBM pairs for inference.")
        else:
            rationale = gla.get("error", "Strict GBM-specific GLASS longitudinal evidence unavailable.")
        return ScoreDimension(None, 0.06, rationale, "GLASS / Synapse")

    n = int(gla.get("n_pairs") or 0)
    delta = abs(float(gla.get("median_delta") or 0.0))
    p = max(float(gla.get("p_value") or 1.0), 1e-300)
    fraction = float(gla.get("fraction_increased") or 0.0)

    # Temporal signal is intentionally modest. A large, reproducible change at
    # recurrence raises research priority but does not imply that either
    # direction is therapeutically favorable.
    magnitude = _clamp(delta / 1.5 * 100.0)
    significance = _clamp((-log10(p)) / 3.0 * 100.0)
    direction_consistency = _clamp(max(fraction, 1.0 - fraction) * 100.0)
    sample_reliability = _clamp(n / 30.0 * 100.0)
    score = (
        0.40 * magnitude
        + 0.30 * significance
        + 0.15 * direction_consistency
        + 0.15 * sample_reliability
    )
    return ScoreDimension(
        _clamp(score),
        0.06,
        (
            f"Clinically verified IDH-wildtype GBM primary/recurrent pairs n={n}; "
            f"median |recurrence-primary| change={delta:.2f} log2(TPM+1), "
            f"paired p={p:.2g}, {fraction:.0%} increased at recurrence."
        ),
        "GLASS controlled longitudinal RNA-seq",
    )


def _score_with_glass(profile: ResearchProfile, gla: dict) -> TargetPriorityScore:
    # Reserve 6% of total weight for a strict longitudinal recurrence layer and
    # proportionally retain all V3 evidence weights within the remaining 94%.
    dims: dict[str, ScoreDimension] = {}
    for name, d in profile.score.dimensions.items():
        dims[name] = ScoreDimension(d.score, d.weight * 0.94, d.rationale, d.source)
    dims["Longitudinal recurrence signal"] = _glass_dimension(gla)

    total_weight = sum(d.weight for d in dims.values())
    available = [(d.score, d.weight) for d in dims.values() if d.score is not None]
    covered_weight = sum(weight for _, weight in available)
    coverage = 100.0 * covered_weight / total_weight if total_weight else 0.0
    if not available:
        overall = None
    else:
        raw = sum(float(score) * weight for score, weight in available) / covered_weight
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
            "Research-prioritisation heuristic only. Genomic, dependency, spatial, survival and longitudinal recurrence "
            "signals answer different questions; the combined score does not predict patient benefit or prove causality."
        ),
    )


def _repair_glass_evidence_and_gaps(profile: ResearchProfile, gla: dict) -> None:
    # V3 correctly kept GLASS out of scoring, but its legacy evidence caveat
    # described all authorized results as diffuse-glioma-wide. Replace that
    # wording only when the V4 connector has clinically verified GBM pairs.
    if gla.get("ok") and gla.get("gbm_specific"):
        for record in profile.dossier.evidence:
            if "GLASS" in record.provenance.source_dataset:
                record.claim_text = (
                    f"{profile.gene} paired primary-to-recurrent expression change in clinically verified "
                    "GLASS IDH-wildtype glioblastoma"
                )
                record.caveats = [
                    "Longitudinal expression change is temporal disease-context evidence; it does not establish causal target dependence or treatment benefit."
                ]
        profile.evidence_gaps = [
            g for g in profile.evidence_gaps
            if "GLASS longitudinal expression is currently diffuse-glioma-wide" not in g
            and "GLASS longitudinal ingestion is implemented but controlled-access data are disabled" not in g
        ]
        profile.next_experiments = list(dict.fromkeys([
            *profile.next_experiments,
            (
                f"Test whether the GLASS recurrence-associated {profile.gene} shift is reproduced within matched "
                "patient-derived primary/recurrent GBM models and whether perturbation reverses the recurrent-state phenotype."
            ),
        ]))[:8]
    elif gla.get("status") == "credentials_required":
        # Keep one concise actionable gap instead of inherited duplicate text.
        profile.evidence_gaps = [
            g for g in profile.evidence_gaps
            if "GLASS longitudinal" not in g
        ]
        profile.evidence_gaps.append(
            "GLASS GBM-specific longitudinal scoring is implemented but disabled until an authorized SYNAPSE_AUTH_TOKEN is configured."
        )


def build_research_profile(gene: str) -> ResearchProfile:
    profile = build_v3_profile(gene)
    gla = profile.live.get("glass", {})
    profile.score = _score_with_glass(profile, gla)
    _repair_glass_evidence_and_gaps(profile, gla)
    if gla.get("ok") and gla.get("gbm_specific"):
        profile.source_status["GLASS"] = f"{gla.get('n_pairs', 0)} clinically verified IDH-wildtype GBM pairs"
    elif gla.get("status") == "credentials_required":
        profile.source_status["GLASS"] = "GBM-specific connector ready — credentials required"
    return profile


def rank_gene_list(genes: list[str], max_workers: int = 2) -> list[ResearchProfile]:
    from concurrent.futures import ThreadPoolExecutor

    cleaned = list(dict.fromkeys(g.strip().upper() for g in genes if g.strip()))
    workers = max(1, min(int(max_workers), 2))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        profiles = list(ex.map(build_research_profile, cleaned))
    return sorted(profiles, key=lambda p: (p.score.overall is not None, p.score.overall or -1), reverse=True)
