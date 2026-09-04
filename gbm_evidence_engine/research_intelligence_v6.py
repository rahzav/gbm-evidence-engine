"""V6 discovery layer for GBM Gene Analysis.

V6 deliberately shifts the product from evidence aggregation toward research
question generation. It preserves the validated V4/V5 target-priority score and
adds transparent, non-scoring discovery functions:

* cross-source research-opportunity detection;
* falsifiable mechanistic hypotheses;
* uncertainty-reduction experiment prioritization;
* pairwise target-combination rationale analysis;
* researcher-provided expression-signature interpretation;
* live LINCS/L1000 perturbational reversal and drug-combination hypotheses.

None of these layers are clinical prediction models. Numeric values in V6 are
heuristics for research triage unless they directly reproduce a source statistic.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from math import isfinite
from typing import Iterable

from gbm_evidence_engine.research_intelligence import ResearchProfile
from gbm_evidence_engine.research_intelligence_v5 import build_research_profile as build_v5_profile
from gbm_evidence_engine.connectors import l1000cds2


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def _dimension(profile: ResearchProfile, name: str) -> float | None:
    item = profile.score.dimensions.get(name)
    if item is None or item.score is None:
        return None
    return float(item.score)


def _normal_brain_pressure(profile: ResearchProfile) -> float | None:
    hpa = profile.live.get("normal_tissue_context", {})
    value = hpa.get("normal_brain_max_expression")
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(value):
        return None
    # This is intentionally a contextual pressure score rather than a toxicity
    # prediction. HPA expression alone cannot establish therapeutic index.
    return _clamp(value / 100.0 * 100.0)


def _research_opportunities(profile: ResearchProfile) -> list[dict]:
    """Detect cross-source patterns that are easy to miss in manual review."""
    opportunities: list[dict] = []
    genomic = _dimension(profile, "GBM genomic signal")
    dependency = _dimension(profile, "Functional dependency")
    druggability = _dimension(profile, "Druggability")
    clinical = _dimension(profile, "Clinical translation")
    spatial = _dimension(profile, "Spatial context signal")
    human = _dimension(profile, "Independent human validation")
    recurrence = _dimension(profile, "Longitudinal recurrence signal")
    dep = profile.live.get("depmap", {})
    ivy = profile.live.get("ivy_gap", {})
    cgg = profile.live.get("cgga", {})
    bbb = profile.live.get("bbb_candidates", {})
    brain_pressure = _normal_brain_pressure(profile)

    def add(kind: str, priority: float, title: str, signal: str, experiment: str, caution: str) -> None:
        opportunities.append({
            "type": kind,
            "priority": round(_clamp(priority), 1),
            "title": title,
            "signal": signal,
            "recommended_test": experiment,
            "caution": caution,
        })

    if dependency is not None and genomic is not None and dependency >= 60 and genomic <= 35:
        add(
            "functional_without_genomic_selection",
            0.65 * dependency + 0.35 * (100 - genomic),
            "Functional vulnerability exceeds genomic selection",
            f"Functional dependency score {dependency:.1f} is substantially stronger than the TCGA genomic signal ({genomic:.1f}).",
            f"Perturb {profile.gene} in genomically diverse patient-derived IDH-wildtype GBM models and test whether dependency persists without the canonical alteration.",
            "A functional dependency can be real without recurrent genomic alteration, but it may also reflect culture-state biology or a broad fitness requirement.",
        )

    if genomic is not None and dependency is not None and genomic >= 60 and dependency <= 30:
        add(
            "altered_but_not_functionally_selective",
            0.60 * genomic + 0.40 * (100 - dependency),
            "Genomic selection is not matched by selective dependency",
            f"TCGA genomic signal is {genomic:.1f}, while the DepMap dependency score is {dependency:.1f}.",
            f"Use alteration-matched isogenic or patient-derived models to test whether {profile.gene} dependency is genotype- or state-specific rather than lineage-wide.",
            "Standard DepMap conditions may miss microenvironmental or state-specific dependencies.",
        )

    if druggability is not None and clinical is not None and druggability >= 60 and clinical <= 30:
        add(
            "translational_whitespace",
            0.60 * druggability + 0.40 * (100 - clinical),
            "Druggability exceeds current GBM clinical translation",
            f"Druggability score {druggability:.1f} is high relative to clinical translation ({clinical:.1f}).",
            f"Prioritize CNS exposure, target-engagement, and orthotopic GBM testing for the most credible {profile.gene}-directed compounds before expanding clinical interpretation.",
            "The gap may reflect biological failure, CNS delivery, toxicity, or simply an immature development landscape.",
        )

    if recurrence is not None and recurrence >= 55 and (clinical is None or clinical < 45):
        add(
            "recurrence_specific_whitespace",
            recurrence,
            "Recurrence-associated signal has limited clinical development",
            f"Longitudinal recurrence score is {recurrence:.1f}, with weaker current clinical translation.",
            f"Validate {profile.gene} in matched primary/recurrent patient-derived models and test perturbation specifically in the recurrent state.",
            "Longitudinal expression change is not proof of recurrence-specific dependence.",
        )

    if spatial is not None and spatial >= 55 and ivy.get("ok"):
        zone = str(ivy.get("top_zone") or "the highest-expression Ivy GAP compartment").replace("_", " ")
        add(
            "niche_specificity",
            spatial,
            "Anatomic niche may condition target biology",
            f"Ivy GAP spatial score is {spatial:.1f}; highest median expression occurs in {zone}.",
            f"Recreate the {zone} state in organoid/spheroid or co-culture models and compare {profile.gene} perturbation with standard bulk culture.",
            "Spatial expression enrichment does not establish niche-specific dependency.",
        )

    if human is not None and human >= 55 and dependency is not None and dependency < 35:
        meta = cgg.get("meta_analysis") or {}
        add(
            "prognostic_functional_disconnect",
            0.55 * human + 0.45 * (100 - dependency),
            "Human prognostic association is not matched by functional dependency",
            f"External human-validation score is {human:.1f}, while functional dependency is {dependency:.1f}; pooled HR is {meta.get('pooled_hr', 'N/A')} when available.",
            f"Test whether {profile.gene} is a marker of a high-risk cell state rather than a driver by perturbing it while tracking the associated transcriptional program.",
            "Survival association is observational and may be confounded by tumor state, purity, or treatment context.",
        )

    if druggability is not None and druggability >= 50 and bbb.get("ok") and bbb.get("matched_count", 0) == 0:
        add(
            "cns_delivery_bottleneck",
            druggability,
            "Target tractability may be limited by CNS-delivery evidence",
            "Target-directed candidates exist, but B3DB returned no matched experimental BBB records for the candidates checked.",
            "Prioritize direct BBB/brain-exposure measurements for the leading chemical matter before interpreting target tractability as GBM tractability.",
            "Absence of a B3DB match is a data gap, not evidence that a compound cannot enter the brain.",
        )

    if brain_pressure is not None and brain_pressure >= 50 and dependency is not None and dependency >= 50:
        add(
            "therapeutic_window_pressure",
            0.55 * dependency + 0.45 * brain_pressure,
            "Normal-brain expression raises therapeutic-window questions",
            f"The target has a meaningful GBM dependency signal and comparatively high displayed normal-brain expression in HPA.",
            f"Include differentiated human neural/glial controls and dose-response rescue experiments when validating {profile.gene} dependency.",
            "Normal expression does not equal on-target toxicity; this is a safety-context flag only.",
        )

    missing = [name for name, item in profile.score.dimensions.items() if item.score is None]
    if missing:
        add(
            "coverage_gap",
            min(85.0, 35.0 + 8.0 * len(missing)),
            "A major conclusion is limited by missing scored evidence",
            "Missing score dimensions: " + ", ".join(missing) + ".",
            "Resolve the highest-weight missing evidence layer before treating the scalar priority score as stable.",
            "Source unavailability is not negative biological evidence.",
        )

    opportunities.sort(key=lambda row: row["priority"], reverse=True)
    return opportunities[:8]


def _mechanistic_hypotheses(profile: ResearchProfile) -> list[dict]:
    """Generate falsifiable hypotheses from observed cross-source structure."""
    hypotheses: list[dict] = []
    network = profile.live.get("interaction_network", {})
    dep = profile.live.get("depmap", {})
    ivy = profile.live.get("ivy_gap", {})
    gla = profile.live.get("glass", {})

    partners = [p.get("gene") for p in (network.get("partners") or []) if p.get("gene")]
    enrich = [e for e in (network.get("enrichment") or []) if e.get("description") or e.get("term")]

    if dep.get("ok") and partners:
        partner_text = ", ".join(partners[:4])
        hypotheses.append({
            "hypothesis": f"{profile.gene} dependency is maintained by a specific interaction-network state rather than by gene abundance alone.",
            "supporting_observations": [
                f"DepMap median GBM Chronos: {dep.get('median_effect_gbm')}",
                f"High-confidence STRING neighbors include {partner_text}",
            ],
            "falsification_test": f"Perturb {profile.gene} and the top network partners individually and in rescue/epistasis experiments across multiple GBM cell states; reject the hypothesis if dependency is invariant to network state.",
            "status": "hypothesis, not causal inference",
        })

    if ivy.get("ok"):
        zone = str(ivy.get("top_zone") or "highest-expression compartment").replace("_", " ")
        hypotheses.append({
            "hypothesis": f"{profile.gene} contributes preferentially to a GBM program enriched in the {zone} niche.",
            "supporting_observations": [
                f"Ivy GAP highest-expression compartment: {zone}",
                f"Spatial median-expression range: {ivy.get('median_range')}",
                f"Kruskal p value: {ivy.get('p_value')}",
            ],
            "falsification_test": f"Measure perturbation response in niche-matched versus standard conditions and reject the hypothesis if {profile.gene} dependence and downstream programs are unchanged across states.",
            "status": "spatial-expression hypothesis",
        })

    if gla.get("ok") and gla.get("gbm_specific"):
        direction = "increases" if float(gla.get("median_delta") or 0) > 0 else "decreases"
        hypotheses.append({
            "hypothesis": f"A {profile.gene}-linked program is remodeled during GBM recurrence rather than remaining static from diagnosis.",
            "supporting_observations": [
                f"Median recurrent-minus-primary change {direction}: {gla.get('median_delta')}",
                f"Clinically verified pairs: {gla.get('n_pairs')}",
                f"Paired p value: {gla.get('p_value')}",
            ],
            "falsification_test": f"Profile matched primary/recurrent models before and after {profile.gene} perturbation and reject the hypothesis if the recurrence-associated program is not reproducible or perturbation-insensitive.",
            "status": "longitudinal hypothesis",
        })

    for item in enrich[:2]:
        desc = item.get("description") or item.get("term")
        genes = item.get("genes")
        hypotheses.append({
            "hypothesis": f"The {profile.gene} phenotype may be mediated through the enriched network program: {desc}.",
            "supporting_observations": [
                f"STRING enrichment category: {item.get('category')}",
                f"FDR: {item.get('fdr')}",
                f"Network genes: {genes}",
            ],
            "falsification_test": f"After {profile.gene} perturbation, quantify pathway activity and rescue the phenotype downstream; reject mediation if pathway activity and phenotype dissociate.",
            "status": "network-derived hypothesis",
        })

    return hypotheses[:5]


def _experiment_portfolio(profile: ResearchProfile) -> list[dict]:
    """Rank experiments by how much unresolved evidence they could clarify."""
    mapping = {
        "GBM genomic signal": (
            "Genotype-specific causal test",
            f"Engineer or select alteration-matched and alteration-negative GBM models, perturb {profile.gene}, and compare rescue-normalized phenotypes.",
        ),
        "GBM disease relevance": (
            "Disease-context validation",
            f"Test {profile.gene} across molecularly distinct IDH-wildtype GBM states and non-neoplastic neural controls.",
        ),
        "Druggability": (
            "Target-engagement study",
            f"Confirm on-target modulation, dose-response, rescue, and pharmacologically achievable exposure for the best {profile.gene}-directed modality.",
        ),
        "Clinical translation": (
            "Translational feasibility study",
            "Measure CNS/brain exposure, target engagement, and efficacy in an orthotopic GBM model before interpreting trial scarcity or presence.",
        ),
        "Literature/context depth": (
            "Focused evidence audit",
            f"Systematically review and reproduce the most decision-relevant {profile.gene} GBM claims rather than adding publication count alone.",
        ),
        "Functional dependency": (
            "Orthogonal dependency validation",
            f"Validate {profile.gene} with independent CRISPR guides or CRISPRi, rescue, and matched non-neoplastic controls in patient-derived GBM models.",
        ),
        "Spatial context signal": (
            "Niche-conditioned perturbation",
            f"Recreate the highest-signal Ivy GAP niche and test whether {profile.gene} perturbation effects differ from standard culture.",
        ),
        "Independent human validation": (
            "Independent-cohort mechanism check",
            f"Re-estimate {profile.gene} association with covariate adjustment and molecular-state stratification in an independent GBM cohort.",
        ),
        "Longitudinal recurrence signal": (
            "Matched recurrence experiment",
            f"Test {profile.gene} in matched primary/recurrent GBM models and determine whether the recurrent phenotype is perturbation-sensitive.",
        ),
    }

    conflict_names: set[str] = set()
    for opportunity in profile.live.get("research_opportunities", []):
        kind = opportunity.get("type")
        if kind == "functional_without_genomic_selection" or kind == "altered_but_not_functionally_selective":
            conflict_names.update({"GBM genomic signal", "Functional dependency"})
        elif kind == "prognostic_functional_disconnect":
            conflict_names.update({"Independent human validation", "Functional dependency"})
        elif kind == "translational_whitespace" or kind == "cns_delivery_bottleneck":
            conflict_names.update({"Druggability", "Clinical translation"})
        elif kind == "recurrence_specific_whitespace":
            conflict_names.add("Longitudinal recurrence signal")

    portfolio: list[dict] = []
    for name, dimension in profile.score.dimensions.items():
        experiment_name, design = mapping.get(name, (f"Resolve {name}", f"Design an orthogonal experiment addressing {name}."))
        if dimension.score is None:
            uncertainty = 100.0
            reason = "This scored evidence dimension is missing."
        else:
            # Mid-range results are intrinsically more decision-ambiguous than
            # clear high/low results. Conflict signals increase priority.
            ambiguity = 100.0 - min(100.0, abs(float(dimension.score) - 50.0) * 2.0)
            uncertainty = 35.0 + 0.45 * ambiguity
            reason = f"Current dimension score is {float(dimension.score):.1f}/100."
        if name in conflict_names:
            uncertainty += 25.0
            reason += " Cross-source evidence is discordant or creates a translational gap."
        weight_factor = 0.65 + min(0.35, float(dimension.weight) / 0.18 * 0.35)
        priority = _clamp(uncertainty * weight_factor)
        portfolio.append({
            "experiment": experiment_name,
            "priority": round(priority, 1),
            "addresses": name,
            "rationale": reason,
            "design": design,
            "interpretation": "Priority is a transparent uncertainty-reduction heuristic, not an expected statistical information-gain estimate.",
        })

    portfolio.sort(key=lambda row: row["priority"], reverse=True)
    return portfolio[:7]


def build_research_profile(gene: str) -> ResearchProfile:
    profile = build_v5_profile(gene)
    profile.live["research_opportunities"] = _research_opportunities(profile)
    # Experiment ranking can use opportunity flags.
    profile.live["mechanistic_hypotheses"] = _mechanistic_hypotheses(profile)
    profile.live["experiment_portfolio"] = _experiment_portfolio(profile)
    profile.source_status["V6 discovery layer"] = (
        f"{len(profile.live['research_opportunities'])} cross-source opportunities; "
        f"{len(profile.live['mechanistic_hypotheses'])} falsifiable hypotheses"
    )
    return profile


def _network_gene_set(profile: ResearchProfile) -> set[str]:
    out = {profile.gene.upper()}
    for row in profile.live.get("interaction_network", {}).get("partners") or []:
        gene = row.get("gene")
        if gene:
            out.add(str(gene).upper())
    return out


def evaluate_gene_pair(gene_a: str, gene_b: str) -> dict:
    """Evaluate research rationale for a two-target combination.

    This explicitly does not predict pharmacologic synergy. It asks whether the
    two targets cover complementary evidence/state constraints worth testing.
    """
    a_raw, b_raw = gene_a.strip(), gene_b.strip()
    if not a_raw or not b_raw:
        raise ValueError("Enter two gene symbols.")
    if a_raw.upper() == b_raw.upper():
        raise ValueError("Combination analysis requires two different genes.")

    # Keep external-source pressure bounded while still parallelizing two full profiles.
    with ThreadPoolExecutor(max_workers=2) as ex:
        fa = ex.submit(build_research_profile, a_raw)
        fb = ex.submit(build_research_profile, b_raw)
        a, b = fa.result(), fb.result()

    score_a = float(a.score.overall or 0.0)
    score_b = float(b.score.overall or 0.0)
    target_quality = (score_a + score_b) / 2.0

    dep_a, dep_b = a.live.get("depmap", {}), b.live.get("depmap", {})
    da = _dimension(a, "Functional dependency")
    db = _dimension(b, "Functional dependency")
    if da is None or db is None:
        functional = None
    else:
        functional = (da + db) / 2.0
        if dep_a.get("pan_essential") or dep_b.get("pan_essential"):
            functional *= 0.65

    set_a, set_b = _network_gene_set(a), _network_gene_set(b)
    union = set_a | set_b
    intersection = set_a & set_b
    jaccard = len(intersection) / len(union) if union else 1.0
    network_complementarity = 100.0 * (1.0 - jaccard)
    direct_interaction = b.gene.upper() in set_a or a.gene.upper() in set_b
    if direct_interaction:
        # Direct interaction can support mechanistic coherence, but extremely
        # overlapping networks may simply represent redundant blockade.
        network_complementarity = min(100.0, network_complementarity + 10.0)

    ivy_a, ivy_b = a.live.get("ivy_gap", {}), b.live.get("ivy_gap", {})
    if ivy_a.get("ok") and ivy_b.get("ok"):
        zone_a = ivy_a.get("top_zone")
        zone_b = ivy_b.get("top_zone")
        spatial_complementarity = 80.0 if zone_a and zone_b and zone_a != zone_b else 45.0
    else:
        spatial_complementarity = None

    rec_a, rec_b = _dimension(a, "Longitudinal recurrence signal"), _dimension(b, "Longitudinal recurrence signal")
    recurrence_coverage = None if rec_a is None and rec_b is None else max(x for x in [rec_a, rec_b] if x is not None)

    bbb_a = a.live.get("bbb_candidates", {})
    bbb_b = b.live.get("bbb_candidates", {})
    feasible_a = bool(a.live.get("open_targets", {}).get("known_drug_count", 0))
    feasible_b = bool(b.live.get("open_targets", {}).get("known_drug_count", 0))
    bbb_support = int(bbb_a.get("bbb_positive_count", 0)) + int(bbb_b.get("bbb_positive_count", 0))
    translation = (50.0 * feasible_a + 50.0 * feasible_b)
    if bbb_support:
        translation = min(100.0, translation + 10.0)

    components = {
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
    available = [(components[k], weights[k]) for k in components if components[k] is not None]
    covered_weight = sum(weight for _, weight in available)
    rationale_score = (
        sum(float(value) * weight for value, weight in available) / covered_weight
        if covered_weight else None
    )

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
    if not feasible_a or not feasible_b:
        risks.append("At least one target lacks a clear target-directed candidate in the current Open Targets output.")
    if dep_a.get("pan_essential") or dep_b.get("pan_essential"):
        risks.append("At least one target is pan-essential in DepMap, increasing therapeutic-window concern.")
    if network_complementarity < 30:
        risks.append("The targets occupy highly overlapping interaction neighborhoods; the pair may be mechanistically redundant.")

    return {
        "gene_a": a.gene,
        "gene_b": b.gene,
        "combination_rationale_score": None if rationale_score is None else round(_clamp(rationale_score), 1),
        "evidence_coverage_pct": round(100.0 * covered_weight / sum(weights.values()), 1),
        "components": {k: (None if v is None else round(float(v), 1)) for k, v in components.items()},
        "direct_string_interaction": direct_interaction,
        "network_jaccard": round(jaccard, 3),
        "why_test_it": reasons or ["The current evidence does not yet provide a strong complementary-target rationale."],
        "risks": risks,
        "validation_sequence": [
            "Measure single-agent dose-response and on-target engagement in at least two patient-derived IDH-wildtype GBM models plus non-neoplastic neural controls.",
            "Test the pair in a dose matrix and quantify interaction with a prespecified synergy model; do not infer synergy from this heuristic score.",
            "Repeat in state- or niche-matched spheroid/organoid conditions and assess whether the pair covers distinct resistant populations.",
            "Only after reproducible in-vitro interaction, test CNS exposure, tolerability, and orthotopic efficacy.",
        ],
        "profiles": {a.gene: a.to_dict(), b.gene: b.to_dict()},
        "caveat": "Combination Rationale Score prioritizes experiments; it is not a synergy, efficacy, or safety prediction.",
    }


def analyze_researcher_signature(
    genes: Iterable[str],
    values: Iterable[float],
    *,
    profile_limit: int = 4,
    l1000_results: int = 15,
) -> dict:
    """Interpret a researcher-generated signed gene signature in GBM context."""
    cleaned: list[tuple[str, float]] = []
    seen: set[str] = set()
    for gene_raw, value_raw in zip(genes, values):
        gene = str(gene_raw).strip().upper()
        if not gene or gene in seen:
            continue
        try:
            value = float(value_raw)
        except (TypeError, ValueError):
            continue
        if not isfinite(value) or value == 0:
            continue
        seen.add(gene)
        cleaned.append((gene, value))
    if len(cleaned) < 6:
        raise ValueError("Upload at least 6 genes with non-zero signed values.")

    cleaned.sort(key=lambda pair: abs(pair[1]), reverse=True)
    top_for_profiles = cleaned[: max(1, min(int(profile_limit), 6))]
    profiles = [build_research_profile(gene) for gene, _ in top_for_profiles]

    max_abs = max(abs(value) for _, value in cleaned) or 1.0
    rows: list[dict] = []
    value_by_gene = dict(cleaned)
    for profile in profiles:
        signed_value = value_by_gene.get(profile.gene, 0.0)
        signal_strength = abs(signed_value) / max_abs * 100.0
        evidence_score = float(profile.score.overall or 0.0)
        discovery_priority = 0.40 * signal_strength + 0.60 * evidence_score
        rows.append({
            "gene": profile.gene,
            "uploaded_value": signed_value,
            "signal_strength": round(signal_strength, 1),
            "target_priority_score": profile.score.overall,
            "discovery_priority": round(_clamp(discovery_priority), 1),
            "top_opportunity": (profile.live.get("research_opportunities") or [{}])[0].get("title"),
            "evidence_coverage_pct": profile.score.evidence_coverage_pct,
        })
    rows.sort(key=lambda row: row["discovery_priority"], reverse=True)

    l1000 = l1000cds2.reverse_weighted_signature(
        [gene for gene, _ in cleaned],
        [value for _, value in cleaned],
        combinations=True,
        max_results=l1000_results,
    )

    return {
        "ok": True,
        "n_input_genes": len(cleaned),
        "top_genes_profiled": rows,
        "up_genes": [gene for gene, value in cleaned if value > 0][:50],
        "down_genes": [gene for gene, value in cleaned if value < 0][:50],
        "l1000_reversal": l1000,
        "interpretation": (
            "Discovery Priority combines the magnitude of the researcher-provided signed signal with the existing GBM Target Priority Score. "
            "It ranks follow-up candidates within this uploaded signature and is not a differential-expression significance test."
        ),
    }


def rank_gene_list(genes: list[str], max_workers: int = 2) -> list[ResearchProfile]:
    cleaned = list(dict.fromkeys(g.strip() for g in genes if g.strip()))
    if not cleaned:
        return []
    workers = max(1, min(int(max_workers), 2))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        profiles = list(ex.map(build_research_profile, cleaned))
    return sorted(profiles, key=lambda p: (p.score.overall is not None, p.score.overall or -1), reverse=True)
