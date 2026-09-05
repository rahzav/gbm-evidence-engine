"""Deterministic tests for production V6 scientific guardrails."""
from gbm_evidence_engine.evidence_model import Dossier
from gbm_evidence_engine.research_intelligence import ResearchProfile, ScoreDimension, TargetPriorityScore
from gbm_evidence_engine.research_discovery import _safe_mechanistic_hypotheses


def _profile(dependency_score: float, delta: float, p_value: float):
    dims = {
        "Functional dependency": ScoreDimension(dependency_score, 0.15, "dep", "DepMap"),
        "Spatial context signal": ScoreDimension(75.0, 0.075, "spatial", "Ivy GAP"),
    }
    score = TargetPriorityScore(
        overall=50.0,
        evidence_coverage_pct=100.0,
        dimensions=dims,
        label="Research priority",
    )
    return ResearchProfile(
        gene="GENEX",
        dossier=Dossier(query="GENEX", target="GENEX"),
        score=score,
        live={
            "depmap": {
                "ok": True,
                "pan_essential": False,
                "median_effect_gbm": -0.7,
                "median_selectivity_delta": delta,
                "p_value": p_value,
            },
            "ivy_gap": {
                "ok": True,
                "top_zone": "infiltrating_tumor",
                "median_range": 1.5,
                "p_value": 0.002,
            },
            "glass": {"ok": False},
            "interaction_network": {
                "ok": True,
                "partners": [{"gene": "A"}, {"gene": "B"}],
                "enrichment": [
                    {"category": "Process", "description": "Example pathway", "fdr": 0.01, "genes": ["GENEX", "A"]}
                ],
            },
        },
        context_map={},
        evidence_gaps=[],
        next_experiments=[],
        source_status={},
    )


def test_weak_or_nonselective_dependency_cannot_generate_dependency_mechanism():
    rows = _safe_mechanistic_hypotheses(_profile(5.0, -0.15, 0.99))
    assert not any("Selective GENEX dependency" in row["hypothesis"] for row in rows)
    assert any("infiltrating tumor" in row["hypothesis"] for row in rows)


def test_selective_dependency_can_generate_guarded_network_hypothesis():
    rows = _safe_mechanistic_hypotheses(_profile(80.0, 0.45, 0.001))
    dep_rows = [row for row in rows if "Selective GENEX dependency" in row["hypothesis"]]
    assert len(dep_rows) == 1
    assert "not causal inference" in dep_rows[0]["status"]
    assert dep_rows[0]["falsification_test"]


def test_all_guarded_hypotheses_remain_falsifiable_and_caveated():
    rows = _safe_mechanistic_hypotheses(_profile(80.0, 0.45, 0.001))
    assert rows
    for row in rows:
        assert row["falsification_test"]
        assert "hypothesis" in row["status"]


if __name__ == "__main__":
    test_weak_or_nonselective_dependency_cannot_generate_dependency_mechanism()
    test_selective_dependency_can_generate_guarded_network_hypothesis()
    test_all_guarded_hypotheses_remain_falsifiable_and_caveated()
    print("ALL V6 DISCOVERY-GUARDRAIL TESTS PASSED")
