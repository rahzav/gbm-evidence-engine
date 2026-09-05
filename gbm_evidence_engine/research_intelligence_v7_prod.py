"""Production facade for the final GBM Gene Analysis research scope.

The scientific behavior is delegated to the validated V7 research layer, while
this facade keeps production-specific execution bounded and attaches a stable
software release identifier to non-profile outputs.
"""
from __future__ import annotations

from gbm_evidence_engine import research_intelligence_v7 as v7

SOFTWARE_VERSION = "7.0.0"


def build_research_profile(gene: str):
    return v7.build_research_profile(gene)


def rank_gene_list(genes: list[str], max_workers: int = 1):
    return v7.rank_gene_list(genes, max_workers=max_workers)


def analyze_researcher_signature(
    genes: list[str] | tuple[str, ...],
    values: list[float] | tuple[float, ...],
    *,
    p_values=None,
    fdr_values=None,
    **kwargs,
):
    result = v7.analyze_researcher_signature(
        genes,
        values,
        p_values=p_values,
        fdr_values=fdr_values,
        **kwargs,
    )
    if isinstance(result, dict):
        result.setdefault("software_version", SOFTWARE_VERSION)
    return result


def _dimension(profile, name: str) -> float | None:
    item = profile.score.dimensions.get(name)
    return None if item is None or item.score is None else float(item.score)


def _network_gene_set(profile) -> set[str]:
    out = {profile.gene.upper()}
    for row in profile.live.get("interaction_network", {}).get("partners") or []:
        gene = row.get("gene")
        if gene:
            out.add(str(gene).upper())
    return out


def evaluate_gene_pair(gene_a: str, gene_b: str) -> dict:
    a_raw, b_raw = gene_a.strip(), gene_b.strip()
    if not a_raw or not b_raw:
        raise ValueError("Enter two gene symbols.")
    if a_raw.upper() == b_raw.upper():
        raise ValueError("Combination analysis requires two different genes.")

    # Deliberately sequential on the public Streamlit deployment: each profile
    # already performs bounded source-level concurrency, so parallel full profiles
    # would amplify upstream/API and memory pressure.
    a = build_research_profile(a_raw)
    b = build_research_profile(b_raw)

    score_a = float(a.score.overall or 0.0)
    score_b = float(b.score.overall or 0.0)
    target_quality = (score_a + score_b) / 2.0

    dep_a, dep_b = a.live.get("depmap", {}), b.live.get("depmap", {})
    da, db = _dimension(a, "Functional dependency"), _dimension(b, "Functional dependency")
    if da is None or db is None:
        functional = None
    else:
        functional = (da + db) / 2.0
        if dep_a.get("pan_essential") or dep_b.get("pan_essential"):
            functional *= 0.65

    set_a, set_b = _network_gene_set(a), _network_gene_set(b)
    union, intersection = set_a | set_b, set_a & set_b
    jaccard = len(intersection) / len(union) if union else 1.0
    network_complementarity = 100.0 * (1.0 - jaccard)
    direct_interaction = b.gene.upper() in set_a or a.gene.upper() in set_b
    if direct_interaction:
        network_complementarity = min(100.0, network_complementarity + 10.0)

    ivy_a, ivy_b = a.live.get("ivy_gap", {}), b.live.get("ivy_gap", {})
    if ivy_a.get("ok") and ivy_b.get("ok"):
        zone_a, zone_b = ivy_a.get("top_zone"), ivy_b.get("top_zone")
        spatial_complementarity = 80.0 if zone_a and zone_b and zone_a != zone_b else 45.0
    else:
        spatial_complementarity = None

    rec_a = _dimension(a, "Longitudinal recurrence signal")
    rec_b = _dimension(b, "Longitudinal recurrence signal")
    recurrence_coverage = None if rec_a is None and rec_b is None else max(x for x in (rec_a, rec_b) if x is not None)

    feasible_a = bool(a.live.get("open_targets", {}).get("known_drug_count", 0))
    feasible_b = bool(b.live.get("open_targets", {}).get("known_drug_count", 0))
    bbb_a, bbb_b = a.live.get("bbb_candidates", {}), b.live.get("bbb_candidates", {})
    bbb_support = int(bbb_a.get("bbb_positive_count", 0)) + int(bbb_b.get("bbb_positive_count", 0))
    translation = 50.0 * feasible_a + 50.0 * feasible_b
    if bbb_support:
        translation = min(100.0, translation + 10.0)

    state_comp = v7._state_complementarity(
        a.live.get("gbmap_cell_state", {}),
        b.live.get("gbmap_cell_state", {}),
    )
    model_a, model_b = a.live.get("model_relevance", {}), b.live.get("model_relevance", {})
    conf_a = v7._num((a.live.get("overall_evidence_confidence") or {}).get("score"))
    conf_b = v7._num((b.live.get("overall_evidence_confidence") or {}).get("score"))
    pair_confidence = None if conf_a is None or conf_b is None else (conf_a + conf_b) / 2.0

    # Preserve the established V6 rationale score so cell-state/confidence
    # context does not silently redefine a pre-existing heuristic. New context
    # is displayed separately and affects rationale/risk text directly.
    scored_components = {
        "individual_target_quality": target_quality,
        "functional_support": functional,
        "network_complementarity": network_complementarity,
        "spatial_complementarity": spatial_complementarity,
        "recurrence_coverage": recurrence_coverage,
        "translational_feasibility": translation,
    }
    weights = {
        "individual_target_quality": 0.24,
        "functional_support": 0.24,
        "network_complementarity": 0.18,
        "spatial_complementarity": 0.12,
        "recurrence_coverage": 0.10,
        "translational_feasibility": 0.12,
    }
    available = [(scored_components[k], weights[k]) for k in scored_components if scored_components[k] is not None]
    covered_weight = sum(weight for _, weight in available)
    rationale = None if not covered_weight else sum(float(v) * w for v, w in available) / covered_weight

    components = dict(scored_components)
    components["malignant_cell_state_complementarity"] = state_comp
    components["pair_evidence_confidence"] = pair_confidence

    reasons: list[str] = []
    risks: list[str] = []
    if functional is not None and functional >= 55:
        reasons.append("Both targets retain meaningful functional-dependency support after pan-essential safeguards.")
    if network_complementarity >= 60:
        reasons.append("The targets occupy relatively non-overlapping high-confidence interaction neighborhoods, supporting a complementary-pathway test.")
    if direct_interaction:
        reasons.append("The targets are directly connected in the retrieved STRING neighborhood, providing a mechanistic relationship to test.")
    if spatial_complementarity is not None and spatial_complementarity >= 70:
        reasons.append("The genes peak in different Ivy GAP anatomic compartments, raising a testable hypothesis of complementary niche coverage.")
    if recurrence_coverage is not None and recurrence_coverage >= 55:
        reasons.append("At least one target carries a meaningful recurrence-associated signal.")
    if state_comp is not None and state_comp >= 55:
        reasons.append("The targets show meaningfully different normalized malignant-state expression patterns in the GBmap reference, supporting a complementary-state experiment.")
    if not feasible_a or not feasible_b:
        risks.append("At least one target lacks a clear target-directed candidate in the current Open Targets output.")
    if dep_a.get("pan_essential") or dep_b.get("pan_essential"):
        risks.append("At least one target is pan-essential in DepMap, increasing therapeutic-window concern.")
    if network_complementarity < 30:
        risks.append("The targets occupy highly overlapping interaction neighborhoods; the pair may be mechanistically redundant.")
    if state_comp is not None and state_comp < 25:
        risks.append("The targets show highly overlapping malignant-state expression patterns; apparent combination value may reflect redundant state coverage.")
    if any(x.get("level") in {"limited", "low", "unknown"} for x in (model_a, model_b)):
        risks.append("At least one target is supported mainly by limited model systems; validate the pair in patient-derived/3D GBM models before interpreting combination rationale.")

    return {
        "software_version": SOFTWARE_VERSION,
        "gene_a": a.gene,
        "gene_b": b.gene,
        "combination_rationale_score": None if rationale is None else round(max(0.0, min(100.0, rationale)), 1),
        "evidence_coverage_pct": round(100.0 * covered_weight / sum(weights.values()), 1),
        "components": {k: (None if value is None else round(float(value), 1)) for k, value in components.items()},
        "direct_string_interaction": direct_interaction,
        "network_jaccard": round(jaccard, 3),
        "pair_evidence_confidence": v7._confidence(
            pair_confidence,
            ["Pair confidence summarizes confidence in the two underlying target profiles; it is separate from combination rationale."],
            ["Direct state-specific perturbation and dose-matrix combination experiments would materially increase confidence."],
        ),
        "model_relevance": {a.gene: model_a, b.gene: model_b},
        "cell_state_context": {
            a.gene: a.live.get("gbmap_cell_state", {}),
            b.gene: b.live.get("gbmap_cell_state", {}),
            "complementarity_score": None if state_comp is None else round(state_comp, 1),
        },
        "why_test_it": reasons or ["The current evidence does not yet provide a strong complementary-target rationale."],
        "risks": risks,
        "validation_sequence": [
            "Measure single-agent dose-response and on-target engagement in at least two patient-derived IDH-wildtype GBM models plus non-neoplastic neural controls.",
            "Test the pair in a prespecified dose matrix and quantify interaction with an explicit synergy model; do not infer synergy from this rationale score.",
            "Repeat in state- or niche-matched spheroid/organoid conditions and test whether the pair covers distinct resistant populations.",
            "Only after reproducible in-vitro interaction, evaluate CNS exposure, tolerability and orthotopic efficacy.",
        ],
        "caveat": "Combination Rationale prioritizes a pair for experimental testing. Cell-state complementarity, network structure and individual target evidence do not establish pharmacologic synergy, efficacy or safety.",
    }
