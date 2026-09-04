"""Deterministic tests for the frozen V7 research scope."""
from __future__ import annotations

import csv
import gzip
import tempfile
from pathlib import Path

from gbm_evidence_engine.benchmarking import evaluate_case
from gbm_evidence_engine.connectors.gbmap import summarize_gene_cell_states, state_vector
from gbm_evidence_engine.connectors.europepmc import publication_url
from gbm_evidence_engine.evidence_model import Dossier
from gbm_evidence_engine.research_intelligence import ResearchProfile, ScoreDimension, TargetPriorityScore
from gbm_evidence_engine.research_intelligence_v7 import (
    _clean_signature,
    _dimension_confidence,
    _model_relevance,
    _state_complementarity,
)


def _profile():
    dims = {
        "GBM genomic signal": ScoreDimension(75.0, 0.169, "strong", "TCGA"),
        "GBM disease relevance": ScoreDimension(72.0, 0.132, "disease", "OT"),
        "Druggability": ScoreDimension(65.0, 0.132, "drugs", "OT"),
        "Clinical translation": ScoreDimension(50.0, 0.113, "trials", "CTG"),
        "Literature/context depth": ScoreDimension(60.0, 0.094, "literature", "EPMC"),
        "Functional dependency": ScoreDimension(70.0, 0.150, "selective", "DepMap"),
        "Spatial context signal": ScoreDimension(65.0, 0.075, "spatial", "Ivy"),
        "Independent human validation": ScoreDimension(62.0, 0.075, "human", "CGGA"),
        "Longitudinal recurrence signal": ScoreDimension(55.0, 0.060, "recurrence", "GLASS"),
    }
    return ResearchProfile(
        gene="GENEX",
        dossier=Dossier(query="GENEX", target="GENEX"),
        score=TargetPriorityScore(66.0, 100.0, dims, "High research priority"),
        live={
            "cbioportal": {"ok": True, "n_samples": 400, "mutation": {"n_profiled": 400}},
            "open_targets": {"ok": True, "gbm_association_score": 0.8, "known_drug_count": 4},
            "clinical_trials": {"ok": True, "total": 3},
            "literature": {"ok": True, "gbm_publication_count": 150},
            "depmap": {
                "ok": True,
                "n_gbm": 30,
                "p_value": 0.002,
                "median_selectivity_delta": 0.4,
                "pan_essential": False,
                "nextgen_model_context": {
                    "metadata_available": True,
                    "n_nextgen_3d_gbm": 4,
                    "n_conventional_gbm": 26,
                },
            },
            "ivy_gap": {"ok": True, "n_samples": 270, "p_value": 0.001},
            "cgga": {
                "ok": True,
                "n_usable_cohorts": 2,
                "direction_consistent": True,
                "meta_analysis": {"pooled_p_value": 0.01, "i_squared": 15.0},
            },
            "glass": {"ok": True, "gbm_specific": True, "n_pairs": 25, "p_value": 0.01},
            "evidence_consistency": {"flags": []},
        },
        context_map={}, evidence_gaps=[], next_experiments=[], source_status={},
    )


def test_confidence_is_separate_from_priority_score():
    p = _profile()
    before = p.score.overall
    conf = _dimension_confidence(p)
    assert conf["GBM genomic signal"]["level"] in {"moderate", "high"}
    assert conf["Functional dependency"]["level"] in {"moderate", "high"}
    assert p.score.overall == before


def test_model_relevance_rewards_3d_context_without_claiming_efficacy():
    result = _model_relevance(_profile())
    assert result["level"] == "high"
    assert result["score"] >= 80
    assert "does not" in result["limitation"].lower()


def test_signature_significance_changes_input_priority():
    rows = _clean_signature(
        ["A", "B", "C", "D", "E", "F"],
        [2, 2, 1, -1, -2, -2],
        p_values=[0.5, 1e-8, 0.01, 0.01, 0.2, 1e-6],
        fdr_values=[0.5, 1e-6, 0.02, 0.02, 0.3, 1e-5],
    )
    by_gene = {r["gene"]: r for r in rows}
    assert by_gene["B"]["statistical_weight"] > by_gene["A"]["statistical_weight"]


def test_gbmap_compact_reference_is_patient_aware_and_state_aware():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "gbmap.csv.gz"
        with gzip.open(path, "wt", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "gene", "state", "state_class", "n_cells", "n_state_patients", "n_expressing_patients", "patient_prevalence",
                "fraction_expressing", "mean_expression", "expression_z_across_states",
            ])
            writer.writerow(["GENEX", "MES-like", "malignant", 1000, 20, 10, 0.50, 0.70, 3.0, 1.2])
            writer.writerow(["GENEX", "OPC-like", "malignant", 800, 10, 3, 0.30, 0.30, 1.0, -0.2])
            writer.writerow(["GENEX", "Macrophage", "microenvironment", 1500, 25, 15, 0.60, 0.60, 2.0, 0.4])
            writer.writerow(["GENEY", "MES-like", "malignant", 1000, 20, 4, 0.20, 0.20, 0.5, -0.5])
            writer.writerow(["GENEY", "OPC-like", "malignant", 800, 25, 20, 0.80, 0.80, 4.0, 1.5])
        x = summarize_gene_cell_states("GENEX", path=path)
        y = summarize_gene_cell_states("GENEY", path=path)
        assert x["ok"] and y["ok"]
        assert x["top_malignant_state"]["state"] == "MES-like"
        assert x["malignant_patient_prevalence"] == 0.5
        assert x["top_malignant_state"]["n_expressing_patients"] == 10
        comp = _state_complementarity(x, y)
        assert comp is not None and comp > 50
        assert abs(sum(state_vector(x).values()) - 1.0) < 1e-9



def test_publication_urls_are_clickable_and_stable():
    assert publication_url({"doi": "10.1000/example"}) == "https://doi.org/10.1000/example"
    assert publication_url({"pmid": "12345"}) == "https://pubmed.ncbi.nlm.nih.gov/12345/"
    assert publication_url({"pmcid": "PMC123"}) == "https://pmc.ncbi.nlm.nih.gov/articles/PMC123/"
    assert publication_url({"title": "A GBM paper"}).startswith("https://europepmc.org/search?query=")


def test_pair_analysis_builds_each_target_once():
    import copy
    import gbm_evidence_engine.research_intelligence_v7 as v7
    a = _profile()
    b = copy.deepcopy(a)
    a.gene, b.gene = "GENEA", "GENEB"
    for profile, partner in ((a, "GENEB"), (b, "GENEA")):
        profile.live["interaction_network"] = {"partners": [{"gene": partner}]}
        profile.live["bbb_candidates"] = {"bbb_positive_count": 1}
        profile.live["gbmap_cell_state"] = {"ok": False}
        profile.live["model_relevance"] = {"level": "high", "score": 85}
        profile.live["overall_evidence_confidence"] = {"level": "high", "score": 82}
    calls = []
    original = v7.build_research_profile
    try:
        def fake(gene):
            calls.append(gene.upper())
            return a if gene.upper() == "GENEA" else b
        v7.build_research_profile = fake
        result = v7.evaluate_gene_pair("GENEA", "GENEB")
    finally:
        v7.build_research_profile = original
    assert calls == ["GENEA", "GENEB"], calls
    assert result["gene_a"] == "GENEA" and result["gene_b"] == "GENEB"
    assert "pair_evidence_confidence" in result

def test_benchmark_framework_refuses_to_call_live_case_retrospective():
    p = _profile()
    case = {
        "id": "synthetic",
        "gene": "GENEX",
        "mode": "current_behavior_regression",
        "expectations": [{"path": "score.overall", "operator": "gte", "value": 60}],
    }
    result = evaluate_case(p, case)
    assert result["passed"]
    assert result["temporal_validity"] == "current_data_only_not_retrospective"


if __name__ == "__main__":
    test_confidence_is_separate_from_priority_score()
    test_model_relevance_rewards_3d_context_without_claiming_efficacy()
    test_signature_significance_changes_input_priority()
    test_gbmap_compact_reference_is_patient_aware_and_state_aware()
    test_publication_urls_are_clickable_and_stable()
    test_pair_analysis_builds_each_target_once()
    test_benchmark_framework_refuses_to_call_live_case_retrospective()
    print("ALL V7 FINAL-SCOPE TESTS PASSED")
