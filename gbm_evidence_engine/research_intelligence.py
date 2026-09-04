"""Live-first GBM target intelligence layer.

This module turns the V1 evidence primitives into a researcher-facing target
prioritisation workflow. It never treats the prioritisation score as a
biomarker or clinical prediction: the score is a transparent heuristic for
*what to investigate next*, with source coverage displayed separately.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from math import log1p
from typing import Any

from gbm_evidence_engine.evidence_model import (
    Dossier, EvidenceRecord, EvidenceTier, ConfidenceLevel, Provenance, AccessTier,
)
from gbm_evidence_engine.connectors import cbioportal, opentargets, europepmc, clinicaltrials


@dataclass
class ScoreDimension:
    score: float | None
    weight: float
    rationale: str
    source: str


@dataclass
class TargetPriorityScore:
    overall: float | None
    evidence_coverage_pct: float
    dimensions: dict[str, ScoreDimension]
    label: str
    caveat: str = (
        "Research-prioritisation heuristic only. It ranks evidence density and translational readiness; "
        "it is not a clinical, prognostic, or therapeutic-response model."
    )

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "evidence_coverage_pct": self.evidence_coverage_pct,
            "label": self.label,
            "caveat": self.caveat,
            "dimensions": {k: asdict(v) for k, v in self.dimensions.items()},
        }


@dataclass
class ResearchProfile:
    gene: str
    dossier: Dossier
    score: TargetPriorityScore
    live: dict[str, Any]
    context_map: dict[str, int | None]
    evidence_gaps: list[str]
    next_experiments: list[str]
    source_status: dict[str, str]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "gene": self.gene,
            "generated_at": self.generated_at,
            "score": self.score.to_dict(),
            "live": self.live,
            "context_map": self.context_map,
            "evidence_gaps": self.evidence_gaps,
            "next_experiments": self.next_experiments,
            "source_status": self.source_status,
            "dossier": self.dossier.to_dict(),
        }


PHASE_SCORE = {0: 0.0, 1: 35.0, 2: 55.0, 3: 78.0, 4: 92.0}


def _confidence_for_n(n: int | None) -> ConfidenceLevel:
    if not n:
        return ConfidenceLevel.MODERATE
    if n >= 300:
        return ConfidenceLevel.HIGH
    if n >= 80:
        return ConfidenceLevel.MODERATE
    return ConfidenceLevel.LOW


def _add_live_evidence(dossier: Dossier, cbio: dict, ot: dict, lit: dict, trials: dict) -> None:
    if cbio.get("ok"):
        study = cbio.get("study_id")
        n = cbio.get("n_samples")
        mut = cbio.get("mutation")
        if mut and mut.get("frequency") is not None:
            dossier.add(EvidenceRecord(
                claim_text=f"{dossier.target} mutation prevalence in TCGA-GBM (cBioPortal)",
                tier=EvidenceTier.OBSERVED_DATA,
                provenance=Provenance(
                    source_dataset="cBioPortal — TCGA-GBM PanCancer Atlas",
                    dataset_version=study or "live",
                    access_tier=AccessTier.OPEN_LIVE_API,
                    sample_size=n,
                    method="Unique samples with a reported mutation divided by profiled study samples",
                    parameters={"study_id": study, "profile_id": mut.get("profile_id")},
                    citation_url="https://www.cbioportal.org/",
                ),
                statistic_name="mutation_frequency",
                statistic_value=float(mut["frequency"]),
                confidence=_confidence_for_n(n),
            ))
        cna = cbio.get("copy_number")
        if cna and cna.get("amplification_frequency") is not None:
            dossier.add(EvidenceRecord(
                claim_text=f"{dossier.target} high-level amplification prevalence in TCGA-GBM",
                tier=EvidenceTier.OBSERVED_DATA,
                provenance=Provenance(
                    source_dataset="cBioPortal — TCGA-GBM PanCancer Atlas",
                    dataset_version=study or "live",
                    access_tier=AccessTier.OPEN_LIVE_API,
                    sample_size=cna.get("n") or n,
                    method="GISTIC discrete copy-number value >= 2",
                    parameters={"profile_id": cna.get("profile_id")},
                    citation_url="https://www.cbioportal.org/",
                ),
                statistic_name="amplification_frequency",
                statistic_value=float(cna["amplification_frequency"]),
                confidence=_confidence_for_n(cna.get("n") or n),
            ))
        if cna and cna.get("deep_deletion_frequency") is not None:
            dossier.add(EvidenceRecord(
                claim_text=f"{dossier.target} deep-deletion prevalence in TCGA-GBM",
                tier=EvidenceTier.OBSERVED_DATA,
                provenance=Provenance(
                    source_dataset="cBioPortal — TCGA-GBM PanCancer Atlas",
                    dataset_version=study or "live",
                    access_tier=AccessTier.OPEN_LIVE_API,
                    sample_size=cna.get("n") or n,
                    method="GISTIC discrete copy-number value <= -2",
                    parameters={"profile_id": cna.get("profile_id")},
                    citation_url="https://www.cbioportal.org/",
                ),
                statistic_name="deep_deletion_frequency",
                statistic_value=float(cna["deep_deletion_frequency"]),
                confidence=_confidence_for_n(cna.get("n") or n),
            ))
        expr = cbio.get("expression")
        if expr and expr.get("high_zscore_frequency") is not None:
            dossier.add(EvidenceRecord(
                claim_text=f"{dossier.target} high-expression fraction in the selected TCGA-GBM expression profile",
                tier=EvidenceTier.OBSERVED_DATA,
                provenance=Provenance(
                    source_dataset="cBioPortal — TCGA-GBM PanCancer Atlas",
                    dataset_version=study or "live",
                    access_tier=AccessTier.OPEN_LIVE_API,
                    sample_size=expr.get("n"),
                    method="Expression profile value >= 2 where a z-score profile is available",
                    parameters={"profile_id": expr.get("profile_id")},
                    citation_url="https://www.cbioportal.org/",
                ),
                statistic_name="high_expression_frequency",
                statistic_value=float(expr["high_zscore_frequency"]),
                confidence=_confidence_for_n(expr.get("n")),
            ))

    if ot.get("ok"):
        assoc = ot.get("gbm_association_score")
        if assoc is not None:
            dossier.add(EvidenceRecord(
                claim_text=f"Open Targets integrated target-disease association for {dossier.target} and glioblastoma",
                tier=EvidenceTier.COMPUTATIONAL_PREDICTION,
                provenance=Provenance(
                    source_dataset="Open Targets Platform",
                    dataset_version="live",
                    access_tier=AccessTier.OPEN_LIVE_API,
                    method="Open Targets integrated direct association score",
                    parameters={"ensembl_id": ot.get("ensembl_id")},
                    citation_url="https://platform.opentargets.org/",
                ),
                statistic_name="open_targets_gbm_association_score",
                statistic_value=float(assoc),
                confidence=ConfidenceLevel.MODERATE,
                caveats=["Integrated evidence score is useful for prioritisation, not an effect size."],
            ))
        dossier.add(EvidenceRecord(
            claim_text=f"Drug/clinical-candidate records targeting {dossier.target} in Open Targets",
            tier=EvidenceTier.OBSERVED_DATA,
            provenance=Provenance(
                source_dataset="Open Targets Platform",
                dataset_version="live",
                access_tier=AccessTier.OPEN_LIVE_API,
                method="Count of target-level drugAndClinicalCandidates rows",
                parameters={"ensembl_id": ot.get("ensembl_id")},
                citation_url="https://platform.opentargets.org/",
            ),
            statistic_name="known_drug_count",
            statistic_value=float(ot.get("known_drug_count") or 0),
            additional_stats={},
            confidence=ConfidenceLevel.HIGH,
            caveats=["Clinical stage is scored from ClinicalTrials.gov; Open Targets target-level candidates are provided separately from disease-specific trial phase."],
        ))

    if trials.get("ok"):
        dossier.add(EvidenceRecord(
            claim_text=f"ClinicalTrials.gov glioblastoma studies matching {dossier.target} or top target-directed drugs",
            tier=EvidenceTier.OBSERVED_DATA,
            provenance=Provenance(
                source_dataset="ClinicalTrials.gov",
                dataset_version="live API v2",
                access_tier=AccessTier.OPEN_LIVE_API,
                method="GBM condition query merged across gene symbol and top Open Targets drug names; deduplicated by NCT ID",
                citation_url="https://clinicaltrials.gov/",
            ),
            statistic_name="matching_trial_count",
            statistic_value=float(trials.get("total") or 0),
            additional_stats={
                "active_trial_count": float(trials.get("active") or 0),
                "max_trial_phase": float(trials.get("max_phase") or 0),
            },
            confidence=ConfidenceLevel.HIGH,
        ))

    if lit.get("ok") and lit.get("hit_count") is not None:
        dossier.add(EvidenceRecord(
            claim_text=f"Europe PMC publications co-mentioning {dossier.target} with glioblastoma/GBM",
            tier=EvidenceTier.OBSERVED_DATA,
            provenance=Provenance(
                source_dataset="Europe PMC",
                dataset_version="live index",
                access_tier=AccessTier.OPEN_LIVE_API,
                method="Full-text/metadata search co-mention count",
                citation_url="https://europepmc.org/",
            ),
            statistic_name="literature_hit_count",
            statistic_value=float(lit.get("hit_count") or 0),
            confidence=ConfidenceLevel.MODERATE,
            caveats=["Publication count measures evidence volume, not evidence quality or causal validity."],
        ))


def _score_dimensions(cbio: dict, ot: dict, lit: dict, trials: dict) -> TargetPriorityScore:
    dims: dict[str, ScoreDimension] = {}

    # 1) GBM genomic prevalence: strongest observed alteration signal from mutation/CNA.
    genomic_values = []
    if cbio.get("ok"):
        mut = (cbio.get("mutation") or {}).get("frequency")
        amp = (cbio.get("copy_number") or {}).get("amplification_frequency")
        dele = (cbio.get("copy_number") or {}).get("deep_deletion_frequency")
        genomic_values = [x for x in (mut, amp, dele) if x is not None]
    if genomic_values:
        strongest = max(genomic_values)
        score = min(100.0, strongest * 250.0)  # 40% altered ~= saturation
        dims["GBM genomic signal"] = ScoreDimension(
            score=score, weight=0.20,
            rationale=f"Strongest TCGA-GBM mutation/high-level CNA prevalence is {strongest:.1%}.",
            source="cBioPortal / TCGA-GBM",
        )
    else:
        dims["GBM genomic signal"] = ScoreDimension(None, 0.20, "No usable live TCGA-GBM alteration layer returned.", "cBioPortal")

    assoc = ot.get("gbm_association_score") if ot.get("ok") else None
    dims["GBM disease relevance"] = ScoreDimension(
        score=(max(0.0, min(100.0, float(assoc) * 100.0)) if assoc is not None else None),
        weight=0.20,
        rationale=(f"Open Targets integrated GBM association score: {assoc:.3f}." if assoc is not None
                   else "No direct Open Targets glioblastoma association score resolved."),
        source="Open Targets",
    )

    if ot.get("ok"):
        tract_total = int(ot.get("tractability_total") or 0)
        tract_pos = int(ot.get("tractability_positive") or 0)
        tract_score = (100.0 * tract_pos / tract_total) if tract_total else 0.0
        drug_count = int(ot.get("known_drug_count") or 0)
        density_component = min(100.0, 30.0 * log1p(drug_count))
        # Keep druggability orthogonal to clinical maturity: Open Targets
        # contributes tractability/candidate density; CT.gov contributes phase.
        score = 0.65 * tract_score + 0.35 * density_component
        dims["Druggability"] = ScoreDimension(
            score=score, weight=0.20,
            rationale=f"{drug_count} target-directed drug/clinical-candidate records; {tract_pos}/{tract_total} positive tractability assessments.",
            source="Open Targets",
        )
    else:
        dims["Druggability"] = ScoreDimension(None, 0.20, "Target druggability profile unavailable.", "Open Targets")

    if trials.get("ok"):
        active = int(trials.get("active") or 0)
        total = int(trials.get("total") or 0)
        phase = int(trials.get("max_phase") or 0)
        activity = min(100.0, 40.0 * log1p(active))
        score = 0.65 * activity + 0.35 * PHASE_SCORE.get(min(4, phase), 0.0)
        dims["Clinical translation"] = ScoreDimension(
            score=score, weight=0.15,
            rationale=f"{total} matching GBM trials, {active} active; highest reported phase {phase}.",
            source="ClinicalTrials.gov",
        )
    else:
        dims["Clinical translation"] = ScoreDimension(None, 0.15, "Trial landscape unavailable.", "ClinicalTrials.gov")

    if lit.get("ok") and lit.get("hit_count") is not None:
        count = int(lit.get("hit_count") or 0)
        contexts = lit.get("contexts") or {}
        present = sum(1 for x in contexts.values() if isinstance(x, int) and x > 0)
        volume = min(100.0, 100.0 * log1p(count) / log1p(600)) if count >= 0 else 0.0
        breadth = 100.0 * present / max(1, len(contexts))
        score = 0.65 * volume + 0.35 * breadth
        dims["Literature/context depth"] = ScoreDimension(
            score=score, weight=0.10,
            rationale=f"{count} GBM co-mentions; literature found in {present}/{len(contexts)} high-value GBM contexts.",
            source="Europe PMC",
        )
    else:
        dims["Literature/context depth"] = ScoreDimension(None, 0.10, "Literature layer unavailable.", "Europe PMC")

    # Deliberately left unscored until real bulk/gated datasets are integrated.
    dims["Cross-cohort functional validation"] = ScoreDimension(
        None, 0.15,
        "Requires real DepMap, Ivy GAP, CGGA and/or GLASS integration. Synthetic demo values are never allowed to inflate the live priority score.",
        "DepMap / Ivy GAP / CGGA / GLASS",
    )

    available = [(d.score, d.weight) for d in dims.values() if d.score is not None]
    total_weight = sum(d.weight for d in dims.values())
    covered_weight = sum(w for _, w in available)
    coverage = 100.0 * covered_weight / total_weight if total_weight else 0.0
    if available:
        raw = sum(s * w for s, w in available) / covered_weight
        # Mild evidence-coverage discount prevents a sparse profile from looking definitive.
        adjusted = raw * (0.82 + 0.18 * (coverage / 100.0))
        overall = round(max(0.0, min(100.0, adjusted)), 1)
    else:
        overall = None
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
    return TargetPriorityScore(overall, round(coverage, 1), dims, label)


def _build_gaps(cbio: dict, ot: dict, lit: dict, trials: dict) -> list[str]:
    gaps = []
    if not cbio.get("ok"):
        gaps.append("Live TCGA-GBM genomic prevalence could not be resolved from cBioPortal.")
    if not ot.get("ok") or ot.get("gbm_association_score") is None:
        gaps.append("No direct Open Targets glioblastoma association score was resolved.")
    if not ot.get("ok") or not ot.get("known_drug_count"):
        gaps.append("No target-directed drug/candidate landscape was resolved from Open Targets.")
    if not trials.get("ok") or not trials.get("active"):
        gaps.append("No active GBM trial matched the gene or the top resolved target-directed drugs.")
    contexts = (lit.get("contexts") or {}) if lit.get("ok") else {}
    for key, label in [
        ("recurrent", "paired primary/recurrent disease"),
        ("single_cell", "single-cell resolution"),
        ("spatial", "spatial/anatomic resolution"),
        ("blood_brain_barrier", "blood-brain-barrier/brain exposure"),
    ]:
        if not contexts.get(key):
            gaps.append(f"Little or no indexed GBM literature was found for {label} in this target query.")
    gaps.append("Real DepMap dependency, Ivy GAP spatial expression, CGGA validation and GLASS longitudinal data are not yet integrated into the live score.")
    return gaps


def _next_experiments(gene: str, cbio: dict, ot: dict, lit: dict, trials: dict) -> list[str]:
    ideas = []
    mut = (cbio.get("mutation") or {}).get("frequency") if cbio.get("ok") else None
    amp = (cbio.get("copy_number") or {}).get("amplification_frequency") if cbio.get("ok") else None
    dele = (cbio.get("copy_number") or {}).get("deep_deletion_frequency") if cbio.get("ok") else None
    strongest = max([x for x in (mut, amp, dele) if x is not None] or [0])
    if strongest >= 0.10:
        ideas.append(
            f"Test {gene} alteration-specific dependency in patient-derived GBM models using CRISPRi/knockout plus rescue; compare altered versus wild-type backgrounds."
        )
    else:
        ideas.append(
            f"Establish whether {gene} is a context-dependent vulnerability rather than a frequent genomic driver using a patient-derived GBM model panel."
        )
    if ot.get("known_drug_count"):
        ideas.append(
            "Prioritize target-directed compounds by CNS exposure: verify measured brain/plasma exposure, BBB permeability and efflux liability before efficacy experiments."
        )
    contexts = lit.get("contexts") or {}
    if contexts.get("recurrent"):
        ideas.append(
            f"Compare {gene} state in paired primary versus recurrent GBM and test whether treatment changes dependency or pathway activity."
        )
    else:
        ideas.append(
            f"Generate paired primary/recurrent evidence for {gene}; recurrence-specific behavior is currently an explicit evidence gap."
        )
    if contexts.get("single_cell") or contexts.get("spatial"):
        ideas.append(
            f"Resolve which tumor cell states and microenvironmental compartments carry the {gene} signal using single-cell/spatial data before choosing a model system."
        )
    if trials.get("active"):
        ideas.append(
            "Audit active trial eligibility and biomarker strategy to determine whether target selection is molecularly enriched or empiric; use that gap to define a sharper translational hypothesis."
        )
    # Deduplicate while preserving order and keep the UI focused.
    return list(dict.fromkeys(ideas))[:5]


def build_research_profile(gene: str) -> ResearchProfile:
    gene = gene.strip().upper()
    if not gene or len(gene) > 30 or not all(ch.isalnum() or ch in "-_." for ch in gene):
        raise ValueError("Enter a valid gene symbol, e.g. EGFR, PTEN, TP53, CDK4, TERT.")

    with ThreadPoolExecutor(max_workers=3) as ex:
        f_cbio = ex.submit(cbioportal.summarize_gbm_gene, gene)
        f_ot = ex.submit(opentargets.get_target_profile, gene)
        f_lit = ex.submit(europepmc.summarize_gene_literature, gene)
        cbio = f_cbio.result()
        ot = f_ot.result()
        lit = f_lit.result()

    drugs = [d.get("name") for d in (ot.get("drugs") or []) if d.get("name")]
    trials = clinicaltrials.search_target_landscape(gene, drugs[:4])

    dossier = Dossier(query=f"Live research profile for {gene} in glioblastoma", target=gene)
    _add_live_evidence(dossier, cbio, ot, lit, trials)
    score = _score_dimensions(cbio, ot, lit, trials)
    gaps = _build_gaps(cbio, ot, lit, trials)
    experiments = _next_experiments(gene, cbio, ot, lit, trials)
    source_status = {
        "cBioPortal / TCGA-GBM": "live" if cbio.get("ok") else "unavailable",
        "Open Targets": "live" if ot.get("ok") else "unavailable",
        "Europe PMC": "live" if lit.get("ok") else "unavailable",
        "ClinicalTrials.gov": "live" if trials.get("ok") else "unavailable",
        "DepMap": "bulk integration pending",
        "Ivy GAP": "bulk integration pending",
        "CGGA": "registration-gated integration pending",
        "GLASS": "registration-gated integration pending",
    }
    live = {"cbioportal": cbio, "open_targets": ot, "literature": lit, "clinical_trials": trials}
    return ResearchProfile(
        gene=gene, dossier=dossier, score=score, live=live,
        context_map=lit.get("contexts") or {}, evidence_gaps=gaps,
        next_experiments=experiments, source_status=source_status,
    )


def rank_gene_list(genes: list[str], max_workers: int = 3) -> list[ResearchProfile]:
    cleaned = list(dict.fromkeys(g.strip().upper() for g in genes if g.strip()))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        profiles = list(ex.map(build_research_profile, cleaned))
    return sorted(profiles, key=lambda p: (p.score.overall is not None, p.score.overall or -1), reverse=True)
