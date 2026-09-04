"""Production discovery facade for GBM Gene Analysis V6.

The V6 core deliberately produces broad hypothesis candidates. This facade is
used by the UI/API and applies stricter evidentiary guardrails before hypotheses
are shown to researchers. It also trims large nested pair-analysis payloads.
"""
from __future__ import annotations

from typing import Iterable

from gbm_evidence_engine.research_intelligence import ResearchProfile
from gbm_evidence_engine import research_intelligence_v6 as core

# Capture the validated core callables once. The Streamlit compatibility wrapper
# may replace public module attributes so the existing V6 page imports guarded
# functions; using these private references prevents recursive self-calls.
_CORE_BUILD = core.build_research_profile
_CORE_RANK = core.rank_gene_list
_CORE_PAIR = core.evaluate_gene_pair
_CORE_SIGNATURE = core.analyze_researcher_signature


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_mechanistic_hypotheses(profile: ResearchProfile) -> list[dict]:
    """Return only hypotheses whose premise is supported by the relevant layer."""
    rows: list[dict] = []
    dep = profile.live.get("depmap", {})
    ivy = profile.live.get("ivy_gap", {})
    gla = profile.live.get("glass", {})
    network = profile.live.get("interaction_network", {})
    dep_dimension = profile.score.dimensions.get("Functional dependency")
    spatial_dimension = profile.score.dimensions.get("Spatial context signal")

    partners = [p.get("gene") for p in (network.get("partners") or []) if p.get("gene")]
    dep_score = _number(getattr(dep_dimension, "score", None))
    delta = _number(dep.get("median_selectivity_delta"))
    dep_p = _number(dep.get("p_value"))
    has_selective_dependency = bool(
        dep.get("ok")
        and not dep.get("pan_essential")
        and dep_score is not None
        and dep_score >= 50
        and delta is not None
        and delta > 0
        and dep_p is not None
        and dep_p < 0.05
    )
    if has_selective_dependency and partners:
        partner_text = ", ".join(partners[:4])
        rows.append({
            "hypothesis": f"Selective {profile.gene} dependency may depend on the surrounding interaction-network state.",
            "supporting_observations": [
                f"Functional dependency score: {dep_score:.1f}/100",
                f"DepMap GBM-versus-other selectivity difference: {delta:.3g}",
                f"One-sided dependency p value: {dep_p:.3g}",
                f"High-confidence STRING neighbors include {partner_text}",
            ],
            "falsification_test": (
                f"Perturb {profile.gene} and the leading network partners individually and in rescue/epistasis experiments across multiple GBM states. "
                "Reject the network-conditioned dependency hypothesis if the dependency is reproducible but invariant to partner or pathway state."
            ),
            "status": "selective-dependency hypothesis; not causal inference",
        })

    spatial_score = _number(getattr(spatial_dimension, "score", None))
    ivy_p = _number(ivy.get("p_value"))
    if ivy.get("ok") and spatial_score is not None and spatial_score >= 55 and (ivy_p is None or ivy_p < 0.05):
        zone = str(ivy.get("top_zone") or "highest-expression compartment").replace("_", " ")
        rows.append({
            "hypothesis": f"{profile.gene} expression marks a GBM program preferentially associated with the {zone} niche.",
            "supporting_observations": [
                f"Ivy GAP highest-expression compartment: {zone}",
                f"Spatial score: {spatial_score:.1f}/100",
                f"Median-expression range: {ivy.get('median_range')}",
                f"Kruskal p value: {ivy.get('p_value')}",
            ],
            "falsification_test": (
                f"Confirm the spatial association in an independent spatial/single-cell dataset, then compare {profile.gene} perturbation in niche-matched and standard conditions. "
                "Reject niche-conditioned function if the expression association fails to reproduce or perturbation response is state-invariant."
            ),
            "status": "spatial-association hypothesis; function remains unproven",
        })

    gla_p = _number(gla.get("p_value"))
    if gla.get("ok") and gla.get("gbm_specific") and gla_p is not None and gla_p < 0.05:
        delta_recurrence = _number(gla.get("median_delta")) or 0.0
        direction = "increased" if delta_recurrence > 0 else "decreased"
        rows.append({
            "hypothesis": f"A {profile.gene}-associated expression program is remodeled at GBM recurrence.",
            "supporting_observations": [
                f"Median recurrent-minus-primary expression is {direction}: {delta_recurrence:.3g}",
                f"Clinically verified primary/recurrent pairs: {gla.get('n_pairs')}",
                f"Paired p value: {gla_p:.3g}",
            ],
            "falsification_test": (
                f"Reproduce the direction in an independent matched primary/recurrent cohort and test whether {profile.gene} perturbation changes the recurrence-associated program. "
                "Reject the remodeling hypothesis if the longitudinal signal does not reproduce."
            ),
            "status": "longitudinal-expression hypothesis; recurrence dependency remains unproven",
        })

    enrichment = [e for e in (network.get("enrichment") or []) if e.get("description") or e.get("term")]
    for item in enrichment[:2]:
        desc = item.get("description") or item.get("term")
        rows.append({
            "hypothesis": f"The {profile.gene} interaction neighborhood is functionally linked to the enriched program: {desc}.",
            "supporting_observations": [
                f"STRING enrichment category: {item.get('category')}",
                f"FDR: {item.get('fdr')}",
                f"Network genes: {item.get('genes')}",
            ],
            "falsification_test": (
                f"Perturb {profile.gene} and quantify the enriched program with an orthogonal pathway readout. "
                "Reject a functional link if pathway activity is unchanged despite verified target perturbation."
            ),
            "status": "network-enrichment hypothesis; STRING enrichment is not causal evidence",
        })

    return rows[:5]


def _guard_profile(profile: ResearchProfile) -> ResearchProfile:
    profile.live["mechanistic_hypotheses"] = _safe_mechanistic_hypotheses(profile)
    profile.source_status["V6 discovery layer"] = (
        f"{len(profile.live.get('research_opportunities', []))} cross-source opportunities; "
        f"{len(profile.live.get('mechanistic_hypotheses', []))} guarded falsifiable hypotheses"
    )
    return profile


def build_research_profile(gene: str) -> ResearchProfile:
    return _guard_profile(_CORE_BUILD(gene))


def rank_gene_list(genes: list[str], max_workers: int = 2) -> list[ResearchProfile]:
    return [_guard_profile(profile) for profile in _CORE_RANK(genes, max_workers=max_workers)]


def evaluate_gene_pair(gene_a: str, gene_b: str) -> dict:
    result = _CORE_PAIR(gene_a, gene_b)
    # Full nested profiles make pair results much larger and are unnecessary for
    # the UI/API summary. Researchers can request either profile independently.
    result.pop("profiles", None)
    return result


def analyze_researcher_signature(
    genes: Iterable[str],
    values: Iterable[float],
    *,
    profile_limit: int = 4,
    l1000_results: int = 15,
) -> dict:
    return _CORE_SIGNATURE(
        genes,
        values,
        profile_limit=profile_limit,
        l1000_results=l1000_results,
    )
