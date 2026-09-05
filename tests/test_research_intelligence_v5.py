"""Deterministic tests for V5 researcher-context layers."""
from unittest.mock import patch

from gbm_evidence_engine.evidence_model import Dossier
from gbm_evidence_engine.research_intelligence import ResearchProfile, ScoreDimension, TargetPriorityScore
import gbm_evidence_engine.research_intelligence_v5 as v5
from gbm_evidence_engine.research_intelligence_v5 import _consistency_review, _key_findings
from gbm_evidence_engine.connectors.mygene import _aliases
from gbm_evidence_engine.connectors.b3db_live import _norm
from gbm_evidence_engine.connectors.cbioportal import _summarize_mutation_variants


def _profile():
    dims = {
        "GBM genomic signal": ScoreDimension(80.0, 0.5, "high", "TCGA"),
        "Functional dependency": ScoreDimension(25.0, 0.5, "low", "DepMap"),
    }
    score = TargetPriorityScore(
        overall=52.5,
        evidence_coverage_pct=100.0,
        dimensions=dims,
        label="Moderate research priority",
    )
    return ResearchProfile(
        gene="EGFR",
        dossier=Dossier(query="EGFR", target="EGFR"),
        score=score,
        live={
            "cgga": {"n_usable_cohorts": 2, "direction_consistent": False},
            "depmap": {"ok": True, "pan_essential": True, "median_selectivity_delta": 0.1},
            "glass": {"ok": False},
        },
        context_map={},
        evidence_gaps=[],
        next_experiments=[],
        source_status={},
    )


def test_consistency_review_flags_only_real_interpretation_issues():
    profile = _profile()
    review = _consistency_review(profile)
    assert review["status"] == "Review recommended"
    assert len(review["flags"]) == 2
    assert review["strongest_dimension"]["name"] == "GBM genomic signal"
    assert review["lowest_available_dimension"]["name"] == "Functional dependency"
    assert profile.score.overall == 52.5


def test_key_findings_include_context_without_rescoring():
    profile = _profile()
    findings = _key_findings(
        profile,
        {"ok": True, "normal_brain_max_expression": 42.0},
        {"ok": True, "partners": [{"gene": "GRB2"}, {"gene": "ERBB2"}]},
        {"ok": True, "matched_count": 2},
        {"ok": True, "was_normalized": True, "symbol": "EGFR", "query": "ERBB1"},
    )
    text = " ".join(findings)
    assert "normalized" in text.lower()
    assert "Human Protein Atlas" in text
    assert "GRB2" in text
    assert "B3DB" in text
    assert profile.score.overall == 52.5


def test_identity_and_compound_normalizers_are_deterministic():
    assert _aliases({"alias": "ERBB1"}) == ["ERBB1"]
    assert _aliases({"alias": ["ERBB1", "HER1"]}) == ["ERBB1", "HER1"]
    assert _norm("Osimertinib (AZD-9291)") == "osimertinibazd9291"


def test_recurrent_mutations_count_unique_samples():
    rows = [
        {"sampleId": "S1", "proteinChange": "p.R132H", "mutationType": "Missense_Mutation"},
        {"sampleId": "S1", "proteinChange": "p.R132H", "mutationType": "Missense_Mutation"},
        {"sampleId": "S2", "proteinChange": "p.R132H", "mutationType": "Missense_Mutation"},
        {"sampleId": "S3", "proteinChange": "p.G34R", "mutationType": "Missense_Mutation"},
    ]
    result = _summarize_mutation_variants(rows, denominator=10)
    assert result["top_variants"][0]["protein_change"] == "p.R132H"
    assert result["top_variants"][0]["sample_count"] == 2
    assert result["top_variants"][0]["mutation_records"] == 3
    assert result["top_variants"][0]["frequency_in_profiled_cohort"] == 0.2
    assert result["mutation_types"][0]["sample_count"] == 3


def test_definitively_invalid_gene_is_rejected_before_downstream_queries():
    with patch.object(
        v5.mygene,
        "resolve_gene",
        return_value={
            "ok": False,
            "query": "NOTAREALGENEZZZ",
            "status": "not_found",
            "error": "No human gene match was found.",
        },
    ):
        try:
            v5.build_research_profile("NOTAREALGENEZZZ")
        except ValueError as exc:
            message = str(exc).lower()
            assert "invalid" in message
            assert "no human gene match" in message
        else:
            raise AssertionError("Definitively invalid gene should fail before downstream evidence queries.")


if __name__ == "__main__":
    test_consistency_review_flags_only_real_interpretation_issues()
    test_key_findings_include_context_without_rescoring()
    test_identity_and_compound_normalizers_are_deterministic()
    test_recurrent_mutations_count_unique_samples()
    test_definitively_invalid_gene_is_rejected_before_downstream_queries()
    print("ALL V5 RESEARCH-CONTEXT TESTS PASSED")
