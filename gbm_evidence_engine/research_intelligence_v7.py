"""Final-scope V7 intelligence for GBM Gene Analysis.

V7 deepens the existing molecular-research workflow without broadening its
scope. It adds:
- native GBmap cell-state context;
- explicit conclusion confidence/uncertainty;
- model-relevance grading;
- significance-aware processed-signature interpretation;
- state-aware target-pair reasoning.

All V7 additions are non-clinical. GBmap, confidence grades, model-relevance
labels, pathway enrichment and pair-rationale components do not alter the
validated V4/V5 Target Priority Score.
"""
from __future__ import annotations

import math
from math import isfinite
from typing import Iterable

from gbm_evidence_engine.research_intelligence import ResearchProfile
from gbm_evidence_engine import research_discovery as v6
from gbm_evidence_engine.connectors import gbmap, l1000cds2, stringdb


def _num(value):
    try:
        value = float(value)
        return value if isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _confidence_label(score: float | None) -> str:
    if score is None:
        return "insufficient"
    if score >= 80:
        return "high"
    if score >= 60:
        return "moderate"
    if score >= 40:
        return "low"
    return "very low"


def _confidence(score: float | None, reasons: list[str], changes: list[str]) -> dict:
    return {
        "score": None if score is None else round(max(0.0, min(100.0, score)), 1),
        "level": _confidence_label(score),
        "reasons": reasons,
        "what_would_change_it": changes,
    }


def _dimension_confidence(profile: ResearchProfile) -> dict[str, dict]:
    """Estimate decision confidence for each scored evidence dimension.

    Confidence is intentionally separate from the evidence score. A strong
    biological signal from a small or single dataset may have a high score but
    only moderate confidence.
    """
    live = profile.live
    cbio = live.get("cbioportal", {})
    ot = live.get("open_targets", {})
    trials = live.get("clinical_trials", {})
    lit = live.get("literature", {})
    dep = live.get("depmap", {})
    ivy = live.get("ivy_gap", {})
    cgg = live.get("cgga", {})
    gla = live.get("glass", {})
    consistency = live.get("evidence_consistency", {})
    out: dict[str, dict] = {}

    # Genomics: TCGA is human tumor evidence, but usually one principal cohort.
    n_mut = _num((cbio.get("mutation") or {}).get("n_profiled")) or _num(cbio.get("n_samples"))
    genomic = 55.0 if cbio.get("ok") else None
    reasons = []
    if genomic is not None:
        reasons.append("Human TCGA-GBM tumor data are available.")
        if n_mut and n_mut >= 100:
            genomic += 15
            reasons.append(f"Genomic profiling includes approximately {int(n_mut)} samples.")
        reasons.append("The principal genomic signal is not an independent multi-cohort replication by itself.")
    out["GBM genomic signal"] = _confidence(
        genomic,
        reasons,
        ["Independent genomic replication or multiregional clonality evidence would increase confidence."],
    )

    association = _num(ot.get("gbm_association_score"))
    disease = None if association is None else 55 + min(20, association * 20)
    out["GBM disease relevance"] = _confidence(
        disease,
        ["Open Targets integrates multiple disease-evidence classes."] if disease is not None else [],
        ["Independent direct GBM functional evidence would increase confidence in disease relevance."],
    )

    known_drugs = int(ot.get("known_drug_count") or 0)
    drug_conf = 45 + min(30, known_drugs * 4) if ot.get("ok") else None
    out["Druggability"] = _confidence(
        drug_conf,
        [f"Open Targets reports {known_drugs} target-directed candidate(s)."] if drug_conf is not None else [],
        ["Direct target engagement, CNS exposure and modality-specific evidence would increase confidence."],
    )

    n_trials = int(trials.get("total") or 0)
    clinical_conf = (50 + min(30, n_trials * 3)) if trials.get("ok") else None
    out["Clinical translation"] = _confidence(
        clinical_conf,
        [f"ClinicalTrials.gov returned {n_trials} matching GBM trial record(s)."] if clinical_conf is not None else [],
        ["Completed trials with interpretable target engagement and efficacy data would increase confidence."],
    )

    pub_count = int(lit.get("hit_count") or lit.get("gbm_publication_count") or lit.get("total") or 0)
    literature_conf = (45 + min(35, math.log10(max(pub_count, 1) + 1) * 20)) if lit.get("ok") else None
    out["Literature/context depth"] = _confidence(
        literature_conf,
        [f"The literature layer identified {pub_count} GBM-context publication(s)."] if literature_conf is not None else [],
        ["Independent replication matters more than additional publication count alone."],
    )

    if dep.get("ok"):
        n_gbm = int(dep.get("n_gbm") or 0)
        p = _num(dep.get("p_value"))
        delta = _num(dep.get("median_selectivity_delta"))
        dep_conf = 45 + min(20, n_gbm / 3)
        dep_reasons = [f"Strict IDH-wildtype GBM dependency panel includes {n_gbm} model(s)."]
        if p is not None and p < 0.05 and delta is not None and delta > 0:
            dep_conf += 15
            dep_reasons.append("GBM-selective dependency is statistically supported in the current panel.")
        elif p is not None:
            dep_reasons.append("The current panel does not show statistically supported GBM-selective dependency.")
        if dep.get("pan_essential"):
            dep_conf -= 15
            dep_reasons.append("Pan-essential behavior limits target-selective interpretation.")
    else:
        dep_conf, dep_reasons = None, []
    out["Functional dependency"] = _confidence(
        dep_conf,
        dep_reasons,
        ["Patient-derived/3D replication and orthogonal perturbation-rescue experiments would increase confidence."],
    )

    if ivy.get("ok"):
        n = int(ivy.get("n_samples") or 0)
        p = _num(ivy.get("p_value"))
        spatial_conf = 45 + min(20, n / 10)
        spatial_reasons = [f"Ivy GAP contributes {n} laser-microdissected anatomic samples."]
        if p is not None and p < 0.05:
            spatial_conf += 10
            spatial_reasons.append("Expression differs significantly across sampled anatomic compartments.")
    else:
        spatial_conf, spatial_reasons = None, []
    out["Spatial context signal"] = _confidence(
        spatial_conf,
        spatial_reasons,
        ["Independent spatial transcriptomic replication at patient level would increase confidence."],
    )

    if cgg.get("ok"):
        n_cohorts = int(cgg.get("n_usable_cohorts") or 0)
        meta = cgg.get("meta_analysis") or {}
        p = _num(meta.get("pooled_p_value"))
        i2 = _num(meta.get("i_squared"))
        human_conf = 45 + n_cohorts * 15
        human_reasons = [f"{n_cohorts} independent strict-GBM CGGA cohort(s) are usable."]
        if p is not None and p < 0.05:
            human_conf += 10
        if i2 is not None and i2 > 60:
            human_conf -= 15
            human_reasons.append(f"Between-cohort heterogeneity is substantial (I²={i2:.1f}%).")
        if cgg.get("direction_consistent") is False:
            human_conf -= 10
            human_reasons.append("Cohort effect directions are discordant.")
    else:
        human_conf, human_reasons = None, []
    out["Independent human validation"] = _confidence(
        human_conf,
        human_reasons,
        ["Additional independent cohorts with covariate-adjusted replication would increase confidence."],
    )

    if gla.get("ok") and gla.get("gbm_specific"):
        pairs = int(gla.get("n_pairs") or 0)
        p = _num(gla.get("p_value"))
        recurrence_conf = 40 + min(30, pairs * 1.5)
        recurrence_reasons = [f"GLASS includes {pairs} clinically verified primary/recurrent pair(s)."]
        if p is not None and p < 0.05:
            recurrence_conf += 10
    else:
        recurrence_conf, recurrence_reasons = None, []
    out["Longitudinal recurrence signal"] = _confidence(
        recurrence_conf,
        recurrence_reasons,
        ["More clinically verified matched pairs and independent longitudinal replication would increase confidence."],
    )

    # Penalize confidence, not biology, when the cross-source consistency layer
    # explicitly reports contradictions.
    n_flags = len(consistency.get("flags") or [])
    if n_flags:
        for item in out.values():
            if item["score"] is not None:
                item["score"] = round(max(0.0, item["score"] - min(15.0, n_flags * 3.0)), 1)
                item["level"] = _confidence_label(item["score"])
                item["reasons"].append("Cross-source consistency review identified unresolved discordance.")
    return out


def _overall_confidence(profile: ResearchProfile, dimensions: dict[str, dict]) -> dict:
    weighted = []
    for name, dim in profile.score.dimensions.items():
        conf = dimensions.get(name, {}).get("score")
        if conf is not None and dim.score is not None:
            weighted.append((float(conf), float(dim.weight)))
    if not weighted:
        return _confidence(None, [], ["Resolve missing scored evidence layers."])
    denom = sum(weight for _, weight in weighted)
    score = sum(value * weight for value, weight in weighted) / denom
    return _confidence(
        score,
        ["Aggregates confidence in available scored dimensions; it does not measure probability that the target will succeed."],
        ["Independent replication, physiologic model validation and resolution of discordant evidence would increase confidence."],
    )


def _model_relevance(profile: ResearchProfile) -> dict:
    dep = profile.live.get("depmap", {})
    if not dep.get("ok"):
        return {
            "level": "unknown",
            "score": None,
            "reasons": ["Functional dependency data are unavailable."],
            "limitation": "No model-relevance inference can be made.",
        }
    nextgen = dep.get("nextgen_model_context") or {}
    n3d = int(nextgen.get("n_nextgen_3d_gbm") or 0)
    conventional = int(nextgen.get("n_conventional_gbm") or dep.get("n_gbm") or 0)
    pan = bool(dep.get("pan_essential"))
    if n3d >= 3:
        score = 82.0
        level = "high"
        reasons = [f"Dependency evidence includes {n3d} next-generation 3D GBM model(s)."]
    elif n3d >= 1:
        score = 68.0
        level = "moderate"
        reasons = [f"Dependency evidence includes {n3d} next-generation 3D GBM model(s), but coverage remains limited."]
    elif conventional >= 8:
        score = 48.0
        level = "limited"
        reasons = [f"Dependency evidence is primarily from {conventional} conventional GBM cell-line model(s)."]
    else:
        score = 35.0
        level = "low"
        reasons = ["Only a small conventional-model set is represented."]
    if pan:
        score = max(0.0, score - 10)
        reasons.append("Pan-essential behavior reduces disease-specific interpretability.")
    return {
        "level": level,
        "score": round(score, 1),
        "reasons": reasons,
        "limitation": (
            "Model relevance describes how well the available dependency systems approximate GBM biology. "
            "It does not convert an in-vitro dependency into evidence of patient efficacy."
        ),
    }


def _augment_cell_state_opportunities(profile: ResearchProfile):
    summary = profile.live.get("gbmap_cell_state", {})
    if not summary.get("ok"):
        return
    top = summary.get("top_malignant_state") or {}
    prevalence = _num(summary.get("malignant_patient_prevalence"))
    fraction = _num(summary.get("malignant_fraction_expressing"))
    if prevalence is not None and prevalence < 0.35 and top.get("state"):
        profile.live.setdefault("research_opportunities", []).append({
            "type": "cell_state_restriction",
            "priority": round(70 + (0.35 - prevalence) * 50, 1),
            "title": "Target signal may be restricted to a malignant subpopulation",
            "signal": f"GBmap-derived malignant-state patient prevalence is {prevalence:.1%}; the strongest malignant state is {top.get('state')}.",
            "recommended_test": f"Quantify {profile.gene} dependency and response across GBM cell states and determine whether a complementary vulnerability covers low-expression/resistant populations.",
            "caution": "Cell-state expression restriction does not establish state-specific dependency or resistance.",
        })
    if fraction is not None and fraction < 0.25:
        profile.evidence_gaps.append("GBmap suggests limited malignant-cell expression breadth; state-specific functional validation is needed before assuming broad target coverage.")
    profile.live["research_opportunities"] = sorted(
        profile.live.get("research_opportunities", []),
        key=lambda row: float(row.get("priority") or 0),
        reverse=True,
    )[:8]


def build_research_profile(gene: str) -> ResearchProfile:
    profile = v6.build_research_profile(gene)
    profile.live["gbmap_cell_state"] = gbmap.summarize_gene_cell_states(profile.gene)
    profile.live["model_relevance"] = _model_relevance(profile)
    confidence = _dimension_confidence(profile)
    profile.live["confidence_by_dimension"] = confidence
    profile.live["overall_evidence_confidence"] = _overall_confidence(profile, confidence)
    _augment_cell_state_opportunities(profile)
    gbm = profile.live["gbmap_cell_state"]
    if gbm.get("ok"):
        profile.source_status["GBmap cell-state reference"] = (
            f"native compact reference; {gbm.get('n_states')} states; "
            f"top malignant state={((gbm.get('top_malignant_state') or {}).get('state') or 'N/A')}"
        )
    else:
        profile.source_status["GBmap cell-state reference"] = gbm.get("status") or "unavailable"
    profile.source_status["V7 confidence/model relevance"] = "active; contextual and non-scoring"
    return profile


def rank_gene_list(genes: list[str], max_workers: int = 1) -> list[ResearchProfile]:
    # Resource safety takes precedence over batch latency on Community Cloud.
    profiles = [build_research_profile(g) for g in dict.fromkeys(x.strip() for x in genes if x.strip())]
    return sorted(profiles, key=lambda p: (p.score.overall is not None, p.score.overall or -1), reverse=True)


def _state_complementarity(a: dict, b: dict) -> float | None:
    va = gbmap.state_vector(a, malignant_only=True)
    vb = gbmap.state_vector(b, malignant_only=True)
    if not va or not vb:
        return None
    states = set(va) | set(vb)
    # Total-variation distance: 0=same normalized state pattern, 100=maximally distinct.
    return 100.0 * 0.5 * sum(abs(va.get(s, 0.0) - vb.get(s, 0.0)) for s in states)


def evaluate_gene_pair(gene_a: str, gene_b: str) -> dict:
    """Evaluate a two-target experiment from exactly two V7 profiles.

    This is a rationale-for-testing heuristic, not a pharmacologic-synergy,
    efficacy, safety, or clinical prediction.
    """
    a_raw, b_raw = gene_a.strip(), gene_b.strip()
    if not a_raw or not b_raw:
        raise ValueError("Enter two gene symbols.")
    if a_raw.upper() == b_raw.upper():
        raise ValueError("Combination analysis requires two different genes.")

    # Each complete target profile is built exactly once. Sequential execution
    # keeps peak Community Cloud resource pressure bounded.
    a = build_research_profile(a_raw)
    b = build_research_profile(b_raw)

    def dim(profile, name):
        value = profile.score.dimensions.get(name)
        return _num(getattr(value, "score", None)) if value is not None else None

    score_a = float(a.score.overall or 0.0)
    score_b = float(b.score.overall or 0.0)
    target_quality = (score_a + score_b) / 2.0

    dep_a, dep_b = a.live.get("depmap", {}), b.live.get("depmap", {})
    da, db = dim(a, "Functional dependency"), dim(b, "Functional dependency")
    if da is None or db is None:
        functional = None
    else:
        functional = (da + db) / 2.0
        if dep_a.get("pan_essential") or dep_b.get("pan_essential"):
            functional *= 0.65

    def network_set(profile):
        out = {profile.gene.upper()}
        for row in profile.live.get("interaction_network", {}).get("partners") or []:
            gene = row.get("gene")
            if gene:
                out.add(str(gene).upper())
        return out

    set_a, set_b = network_set(a), network_set(b)
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

    rec_a = dim(a, "Longitudinal recurrence signal")
    rec_b = dim(b, "Longitudinal recurrence signal")
    recurrence_values = [x for x in (rec_a, rec_b) if x is not None]
    recurrence_coverage = max(recurrence_values) if recurrence_values else None

    feasible_a = bool(a.live.get("open_targets", {}).get("known_drug_count", 0))
    feasible_b = bool(b.live.get("open_targets", {}).get("known_drug_count", 0))
    bbb_support = int(a.live.get("bbb_candidates", {}).get("bbb_positive_count", 0)) + int(b.live.get("bbb_candidates", {}).get("bbb_positive_count", 0))
    translation = 50.0 * feasible_a + 50.0 * feasible_b
    if bbb_support:
        translation = min(100.0, translation + 10.0)

    state_comp = _state_complementarity(a.live.get("gbmap_cell_state", {}), b.live.get("gbmap_cell_state", {}))
    model_a, model_b = a.live.get("model_relevance", {}), b.live.get("model_relevance", {})
    conf_a = _num((a.live.get("overall_evidence_confidence") or {}).get("score"))
    conf_b = _num((b.live.get("overall_evidence_confidence") or {}).get("score"))
    pair_confidence = None if conf_a is None or conf_b is None else (conf_a + conf_b) / 2.0

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
    rationale_score = sum(float(value) * weight for value, weight in available) / covered_weight if covered_weight else None

    components = dict(scored_components)
    components["malignant_cell_state_complementarity"] = state_comp
    components["pair_evidence_confidence"] = pair_confidence

    reasons, risks = [], []
    if functional is not None and functional >= 55:
        reasons.append("Both targets retain meaningful functional-dependency support after pan-essential safeguards.")
    if network_complementarity >= 60:
        reasons.append("The targets occupy relatively non-overlapping high-confidence interaction neighborhoods, supporting a complementary-pathway test.")
    if direct_interaction:
        reasons.append("The targets are directly connected in the retrieved STRING neighborhood, providing a mechanistic relationship to test.")
    if spatial_complementarity is not None and spatial_complementarity >= 70:
        reasons.append("The genes peak in different Ivy GAP anatomic compartments, raising a testable hypothesis of complementary niche coverage.")
    if state_comp is not None and state_comp >= 55:
        reasons.append("The targets show meaningfully different patient-weighted malignant-state expression patterns in GBmap, supporting a complementary-state experiment.")
    if recurrence_coverage is not None and recurrence_coverage >= 55:
        reasons.append("At least one target carries a meaningful recurrence-associated signal.")

    if not feasible_a or not feasible_b:
        risks.append("At least one target lacks a clear target-directed candidate in the current Open Targets output.")
    if dep_a.get("pan_essential") or dep_b.get("pan_essential"):
        risks.append("At least one target is pan-essential in DepMap, increasing therapeutic-window concern.")
    if network_complementarity < 30:
        risks.append("The targets occupy highly overlapping interaction neighborhoods; the pair may be mechanistically redundant.")
    if state_comp is not None and state_comp < 25:
        risks.append("The targets show highly overlapping malignant-state expression patterns; apparent combination value may reflect redundant state coverage.")
    if any((x.get("level") in {"limited", "low", "unknown", "very low"}) for x in (model_a, model_b)):
        risks.append("At least one target is supported mainly by limited model systems; validate the pair in patient-derived/3D GBM models before interpreting combination rationale.")

    return {
        "gene_a": a.gene,
        "gene_b": b.gene,
        "combination_rationale_score": None if rationale_score is None else round(max(0.0, min(100.0, rationale_score)), 1),
        "evidence_coverage_pct": round(100.0 * covered_weight / sum(weights.values()), 1),
        "components": {k: (None if v is None else round(float(v), 1)) for k, v in components.items()},
        "direct_string_interaction": direct_interaction,
        "network_jaccard": round(jaccard, 3),
        "model_relevance": {a.gene: model_a, b.gene: model_b},
        "cell_state_context": {
            a.gene: a.live.get("gbmap_cell_state", {}),
            b.gene: b.live.get("gbmap_cell_state", {}),
            "complementarity_score": None if state_comp is None else round(state_comp, 1),
        },
        "pair_evidence_confidence": _confidence(
            pair_confidence,
            ["Pair confidence summarizes confidence in the two underlying target profiles; it is separate from combination rationale."],
            ["Direct state-specific perturbation and dose-matrix experiments would materially increase confidence."],
        ),
        "why_test_it": reasons or ["The current evidence does not yet provide a strong complementary-target rationale."],
        "risks": risks,
        "validation_sequence": [
            "Measure single-agent dose-response and on-target engagement in at least two patient-derived IDH-wildtype GBM models plus non-neoplastic neural controls.",
            "Test the pair in a dose matrix and quantify interaction with a prespecified synergy model; do not infer synergy from this heuristic score.",
            "Repeat in state- or niche-matched spheroid/organoid conditions and assess whether the pair covers distinct resistant populations.",
            "Only after reproducible in-vitro interaction, test CNS exposure, tolerability, and orthotopic efficacy.",
        ],
        "caveat": "Combination Rationale prioritizes a pair for experimental testing. Cell-state complementarity, network structure and individual target evidence do not establish pharmacologic synergy, efficacy or safety.",
    }

def _clean_signature(
    genes: Iterable[str],
    values: Iterable[float],
    p_values: Iterable[float | None] | None = None,
    fdr_values: Iterable[float | None] | None = None,
) -> list[dict]:
    genes = list(genes)
    values = list(values)
    pvals = list(p_values) if p_values is not None else [None] * len(genes)
    fdrs = list(fdr_values) if fdr_values is not None else [None] * len(genes)
    rows: list[dict] = []
    seen: set[str] = set()
    for idx, (g_raw, v_raw) in enumerate(zip(genes, values)):
        gene = str(g_raw).strip().upper()
        value = _num(v_raw)
        if not gene or value is None or value == 0 or gene in seen:
            continue
        seen.add(gene)
        p = _num(pvals[idx]) if idx < len(pvals) else None
        q = _num(fdrs[idx]) if idx < len(fdrs) else None
        if q is not None and 0 < q <= 1:
            stat_strength = 0.35 + 0.65 * min(1.0, max(0.0, -math.log10(q) / 5.0))
        elif p is not None and 0 < p <= 1:
            stat_strength = 0.30 + 0.60 * min(1.0, max(0.0, -math.log10(p) / 5.0))
        else:
            stat_strength = 0.60
        rows.append({"gene": gene, "value": value, "p_value": p, "fdr": q, "statistical_weight": stat_strength})
    return rows


def analyze_researcher_signature(
    genes: Iterable[str],
    values: Iterable[float],
    *,
    p_values: Iterable[float | None] | None = None,
    fdr_values: Iterable[float | None] | None = None,
    profile_limit: int = 4,
    l1000_results: int = 15,
) -> dict:
    rows = _clean_signature(genes, values, p_values=p_values, fdr_values=fdr_values)
    if len(rows) < 6:
        raise ValueError("Upload at least 6 unique genes with non-zero signed effect values.")
    max_abs = max(abs(r["value"]) for r in rows) or 1.0
    for row in rows:
        row["signal_strength"] = abs(row["value"]) / max_abs * 100.0
        row["input_priority"] = row["signal_strength"] * row["statistical_weight"]
    rows.sort(key=lambda r: r["input_priority"], reverse=True)

    selected = rows[: max(1, min(int(profile_limit), 6))]
    profile_rows = []
    for row in selected:
        profile = build_research_profile(row["gene"])
        evidence_score = float(profile.score.overall or 0.0)
        confidence_score = _num((profile.live.get("overall_evidence_confidence") or {}).get("score")) or 0.0
        discovery_priority = (
            0.30 * row["signal_strength"]
            + 0.15 * row["statistical_weight"] * 100.0
            + 0.40 * evidence_score
            + 0.15 * confidence_score
        )
        profile_rows.append({
            "gene": profile.gene,
            "uploaded_effect": row["value"],
            "p_value": row["p_value"],
            "fdr": row["fdr"],
            "signal_strength": round(row["signal_strength"], 1),
            "target_priority_score": profile.score.overall,
            "evidence_confidence": round(confidence_score, 1),
            "discovery_priority": round(max(0.0, min(100.0, discovery_priority)), 1),
            "top_research_opportunity": (profile.live.get("research_opportunities") or [{}])[0].get("title"),
            "top_malignant_state": ((profile.live.get("gbmap_cell_state") or {}).get("top_malignant_state") or {}).get("state"),
            "model_relevance": (profile.live.get("model_relevance") or {}).get("level"),
            "evidence_coverage_pct": profile.score.evidence_coverage_pct,
        })
    profile_rows.sort(key=lambda r: r["discovery_priority"], reverse=True)

    significant = [
        r for r in rows
        if (r["fdr"] is not None and r["fdr"] <= 0.05)
        or (r["fdr"] is None and r["p_value"] is not None and r["p_value"] <= 0.01)
    ]
    enrichment_pool = significant if len(significant) >= 3 else rows[: min(100, len(rows))]
    up = [r["gene"] for r in enrichment_pool if r["value"] > 0]
    down = [r["gene"] for r in enrichment_pool if r["value"] < 0]
    up_enrichment = stringdb.enrich_gene_set(up, limit=12) if len(up) >= 3 else {"ok": False, "error": "Fewer than 3 upregulated genes available."}
    down_enrichment = stringdb.enrich_gene_set(down, limit=12) if len(down) >= 3 else {"ok": False, "error": "Fewer than 3 downregulated genes available."}

    l1000 = l1000cds2.reverse_weighted_signature(
        [r["gene"] for r in rows[:300]],
        [r["value"] for r in rows[:300]],
        combinations=True,
        max_results=l1000_results,
    )
    return {
        "ok": True,
        "n_input_genes": len(rows),
        "n_statistically_supported": len(significant),
        "statistics_provided": any(r["p_value"] is not None or r["fdr"] is not None for r in rows),
        "top_genes_profiled": profile_rows,
        "up_pathway_enrichment": up_enrichment,
        "down_pathway_enrichment": down_enrichment,
        "l1000_reversal": l1000,
        "interpretation": (
            "Discovery Priority combines the researcher-provided effect magnitude, optional statistical support, existing GBM target evidence and evidence confidence. "
            "It prioritizes follow-up within the uploaded processed result; it is not a new differential-expression test and does not replace the experiment's original statistical model."
        ),
    }
