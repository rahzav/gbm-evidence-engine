"""Deterministic release-edge tests for malformed researcher inputs and live-source benchmarks."""
from __future__ import annotations

from gbm_evidence_engine.benchmarking import evaluate_case
from gbm_evidence_engine.evidence_model import Dossier
from gbm_evidence_engine.research_intelligence import ResearchProfile, ScoreDimension, TargetPriorityScore
from gbm_evidence_engine.research_intelligence_v7 import analyze_researcher_signature


def _minimal_profile() -> ResearchProfile:
    dims = {"GBM genomic signal": ScoreDimension(50.0, 1.0, "available", "test")}
    return ResearchProfile(
        gene="GENEX",
        dossier=Dossier(query="GENEX", target="GENEX"),
        score=TargetPriorityScore(50.0, 50.0, dims, "Moderate research priority"),
        live={"cbioportal": {"ok": False, "status": "unavailable"}},
        context_map={},
        evidence_gaps=["TCGA/cBioPortal unavailable"],
        next_experiments=[],
        source_status={"cBioPortal": "unavailable"},
    )


def test_malformed_processed_signature_fails_before_external_queries():
    try:
        analyze_researcher_signature(["EGFR", "PTEN"], [2.0, -1.0])
    except ValueError as exc:
        assert "at least 6 unique genes" in str(exc).lower()
    else:
        raise AssertionError("A processed signature with fewer than six usable genes must be rejected.")


def test_unavailable_live_source_is_not_scored_as_benchmark_pass_or_failure():
    case = {
        "id": "source_limited",
        "gene": "GENEX",
        "case_class": "context_specific",
        "mode": "current_behavior_regression",
        "expectations": [
            {
                "path": "live.cbioportal.mutation.frequency",
                "operator": "gte",
                "value": 0.05,
                "when": {"path": "live.cbioportal.ok", "operator": "eq", "value": True},
            },
            {"path": "score.overall", "operator": "gte", "value": 40},
        ],
    }
    result = evaluate_case(_minimal_profile(), case)
    assert result["passed"] is True
    assert result["not_evaluable_checks"] == 1
    assert result["evaluable_checks"] == 1
    assert result["checks"][0]["status"] == "not_evaluable"
    assert result["checks"][0]["passed"] is None
    assert result["checks"][1]["status"] == "passed"


if __name__ == "__main__":
    test_malformed_processed_signature_fails_before_external_queries()
    test_unavailable_live_source_is_not_scored_as_benchmark_pass_or_failure()
    print("ALL RELEASE EDGE-CASE TESTS PASSED")
