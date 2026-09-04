"""Deterministic tests for V6 discovery logic."""
from gbm_evidence_engine.evidence_model import Dossier
from gbm_evidence_engine.research_intelligence import ResearchProfile, ScoreDimension, TargetPriorityScore
from gbm_evidence_engine.research_intelligence_v6 import (
    _research_opportunities,
    _mechanistic_hypotheses,
    _experiment_portfolio,
)
from gbm_evidence_engine.connectors.l1000cds2 import _summarize_response


def _profile():
    dims = {
        "GBM genomic signal": ScoreDimension(20.0, 0.169, "low genomic", "TCGA"),
        "GBM disease relevance": ScoreDimension(72.0, 0.132, "disease", "OT"),
        "Druggability": ScoreDimension(78.0, 0.132, "drugs", "OT"),
        "Clinical translation": ScoreDimension(18.0, 0.113, "few trials", "CTG"),
        "Literature/context depth": ScoreDimension(55.0, 0.094, "literature", "EPMC"),
        "Functional dependency": ScoreDimension(82.0, 0.150, "selective", "DepMap"),
        "Spatial context signal": ScoreDimension(70.0, 0.075, "spatial", "Ivy"),
        "Independent human validation": ScoreDimension(60.0, 0.075, "human", "CGGA"),
        "Longitudinal recurrence signal": ScoreDimension(None, 0.060, "missing", "GLASS"),
    }
    score = TargetPriorityScore(
        overall=61.0,
        evidence_coverage_pct=94.0,
        dimensions=dims,
        label="Moderate-high research priority",
    )
    return ResearchProfile(
        gene="GENEX",
        dossier=Dossier(query="GENEX", target="GENEX"),
        score=score,
        live={
            "depmap": {
                "ok": True,
                "pan_essential": False,
                "median_effect_gbm": -0.9,
                "median_selectivity_delta": 0.5,
            },
            "ivy_gap": {
                "ok": True,
                "top_zone": "microvascular_proliferation",
                "median_range": 1.7,
                "p_value": 0.001,
            },
            "cgga": {"ok": True, "meta_analysis": {"pooled_hr": 1.5}},
            "glass": {"ok": False, "status": "credentials_required"},
            "bbb_candidates": {"ok": True, "matched_count": 0},
            "normal_tissue_context": {"ok": True, "normal_brain_max_expression": 65.0},
            "interaction_network": {
                "ok": True,
                "partners": [{"gene": "A"}, {"gene": "B"}],
                "enrichment": [{"category": "Reactome", "description": "Test pathway", "fdr": 0.01, "genes": ["GENEX", "A"]}],
            },
            "open_targets": {"known_drug_count": 3},
        },
        context_map={},
        evidence_gaps=[],
        next_experiments=[],
        source_status={},
    )


def test_opportunity_engine_detects_cross_source_whitespace():
    p = _profile()
    rows = _research_opportunities(p)
    kinds = {row["type"] for row in rows}
    assert "functional_without_genomic_selection" in kinds
    assert "translational_whitespace" in kinds
    assert "niche_specificity" in kinds
    assert "cns_delivery_bottleneck" in kinds
    assert "coverage_gap" in kinds
    assert all(0 <= row["priority"] <= 100 for row in rows)
    assert p.score.overall == 61.0


def test_hypotheses_are_explicitly_falsifiable():
    rows = _mechanistic_hypotheses(_profile())
    assert rows
    for row in rows:
        assert row["hypothesis"]
        assert row["falsification_test"]
        assert "hypothesis" in row["status"].lower()


def test_experiment_portfolio_prioritizes_missing_or_conflicted_layers():
    p = _profile()
    p.live["research_opportunities"] = _research_opportunities(p)
    rows = _experiment_portfolio(p)
    assert rows
    assert rows == sorted(rows, key=lambda row: row["priority"], reverse=True)
    recurrence = next(row for row in rows if row["addresses"] == "Longitudinal recurrence signal")
    assert recurrence["priority"] >= 60
    assert "heuristic" in recurrence["interpretation"].lower()


def test_l1000_parser_aggregates_drugs_and_maps_combinations():
    raw = {
        "topMeta": [
            {"pert_desc": "DrugA", "sig_id": "s1", "score": 0.8, "cell_id": "A172"},
            {"pert_desc": "DrugA", "sig_id": "s2", "score": 0.7, "cell_id": "U87"},
            {"pert_desc": "DrugB", "sig_id": "s3", "score": 0.9, "cell_id": "A172"},
        ],
        "combinations": [{"X1": "s1", "X2": "s3", "value": 0.95}],
    }
    out = _summarize_response(raw, max_results=10)
    assert out["ok"]
    drugs = {row["drug"]: row for row in out["top_drugs"]}
    assert drugs["DrugA"]["supporting_signatures"] == 2
    assert out["combinations"][0]["drug_1"] == "DrugA"
    assert out["combinations"][0]["drug_2"] == "DrugB"


if __name__ == "__main__":
    test_opportunity_engine_detects_cross_source_whitespace()
    test_hypotheses_are_explicitly_falsifiable()
    test_experiment_portfolio_prioritizes_missing_or_conflicted_layers()
    test_l1000_parser_aggregates_drugs_and_maps_combinations()
    print("ALL V6 DISCOVERY TESTS PASSED")
