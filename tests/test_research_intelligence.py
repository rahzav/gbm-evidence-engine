"""Pure tests for V2 scoring/decision logic (no network required)."""
import sys
sys.path.insert(0, ".")
from gbm_evidence_engine.research_intelligence import _score_dimensions, _next_experiments


def test_translationally_mature_target_scores_higher_than_sparse_target():
    mature_cbio = {"ok": True, "mutation": {"frequency": 0.12},
                   "copy_number": {"amplification_frequency": 0.35, "deep_deletion_frequency": 0.0}}
    mature_ot = {"ok": True, "gbm_association_score": 0.78, "max_phase": 3,
                 "known_drug_count": 12, "tractability_positive": 5, "tractability_total": 7}
    mature_lit = {"ok": True, "hit_count": 400,
                  "contexts": {"recurrent": 40, "IDH": 20, "MGMT": 30, "single_cell": 25,
                               "spatial": 10, "blood_brain_barrier": 15, "treatment_resistance": 40}}
    mature_trials = {"ok": True, "total": 8, "active": 3, "max_phase": 2}
    sparse_cbio = {"ok": True, "mutation": {"frequency": 0.005}, "copy_number": None}
    sparse_ot = {"ok": True, "gbm_association_score": 0.05, "max_phase": 0,
                 "known_drug_count": 0, "tractability_positive": 0, "tractability_total": 4}
    sparse_lit = {"ok": True, "hit_count": 2,
                  "contexts": {"recurrent": 0, "IDH": 0, "MGMT": 0, "single_cell": 0,
                               "spatial": 0, "blood_brain_barrier": 0, "treatment_resistance": 0}}
    sparse_trials = {"ok": True, "total": 0, "active": 0, "max_phase": 0}
    a = _score_dimensions(mature_cbio, mature_ot, mature_lit, mature_trials)
    b = _score_dimensions(sparse_cbio, sparse_ot, sparse_lit, sparse_trials)
    assert a.overall > b.overall, (a.overall, b.overall)
    assert a.evidence_coverage_pct == 85.0
    print(f"PASS: mature target {a.overall} > sparse target {b.overall}; coverage={a.evidence_coverage_pct}%")


def test_missing_sources_reduce_coverage_not_silently_become_zero_evidence():
    score = _score_dimensions({"ok": False}, {"ok": False}, {"ok": False}, {"ok": False})
    assert score.overall is None
    assert score.evidence_coverage_pct == 0.0
    print("PASS: unavailable sources produce insufficient-evidence state instead of a misleading low score")


def test_experiment_recommendations_are_decision_oriented():
    ideas = _next_experiments(
        "EGFR",
        {"ok": True, "mutation": {"frequency": 0.1}, "copy_number": {"amplification_frequency": 0.4, "deep_deletion_frequency": 0}},
        {"known_drug_count": 10},
        {"contexts": {"recurrent": 2, "single_cell": 3, "spatial": 1}},
        {"active": 1},
    )
    text = " ".join(ideas).lower()
    assert "crispr" in text and "primary versus recurrent" in text and "cns" in text
    print("PASS: next-step logic covers functional validation, recurrence and CNS exposure")


if __name__ == "__main__":
    test_translationally_mature_target_scores_higher_than_sparse_target()
    test_missing_sources_reduce_coverage_not_silently_become_zero_evidence()
    test_experiment_recommendations_are_decision_oriented()
    print("\nALL research_intelligence.py TESTS PASSED")
