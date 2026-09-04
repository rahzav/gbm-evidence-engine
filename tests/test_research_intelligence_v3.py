"""Deterministic tests for V3 advanced evidence/scoring. No network required."""
from __future__ import annotations

import pandas as pd

from gbm_evidence_engine.evidence_model import Dossier
from gbm_evidence_engine.research_intelligence import ResearchProfile, ScoreDimension, TargetPriorityScore
from gbm_evidence_engine.research_intelligence_v3 import _advanced_dimensions, _score_from_dimensions
from gbm_evidence_engine.connectors.ivygap import _zone_from_structure
from gbm_evidence_engine.connectors.glass import _sample_identity
from gbm_evidence_engine.connectors.cgga import _strict_gbm_frame


def base_profile():
    dims = {
        "GBM genomic signal": ScoreDimension(70, .20, "x", "cBioPortal"),
        "GBM disease relevance": ScoreDimension(80, .20, "x", "Open Targets"),
        "Druggability": ScoreDimension(65, .20, "x", "Open Targets"),
        "Clinical translation": ScoreDimension(55, .15, "x", "CT.gov"),
        "Literature/context depth": ScoreDimension(75, .10, "x", "Europe PMC"),
        "Cross-cohort functional validation": ScoreDimension(None, .15, "old", "old"),
    }
    return ResearchProfile(
        gene="EGFR",
        dossier=Dossier(query="test", target="EGFR"),
        score=TargetPriorityScore(68, 85, dims, "test"),
        live={}, context_map={}, evidence_gaps=[], next_experiments=[], source_status={},
    )


def strong_sources():
    dep = {
        "ok": True, "n_gbm": 14, "n_other": 1100, "median_effect_gbm": -0.95,
        "median_effect_other": -0.12, "median_selectivity_delta": 0.83,
        "rank_biserial_effect_size": 0.78, "gbm_fraction_below_minus_0_5": 0.79,
        "pan_essential": False, "p_value": 1e-6,
    }
    ivy = {"ok": True, "n_samples": 270, "top_zone": "cellular_tumor", "median_range": 2.2, "p_value": 1e-8}
    cgg = {
        "ok": True, "n_usable_cohorts": 2, "direction_consistent": True,
        "meta_analysis": {"pooled_log_hr": 0.42, "pooled_hr": 1.52, "pooled_p_value": 0.001, "i_squared": 12.0},
        "cohorts": [],
    }
    return dep, ivy, cgg


def test_v3_full_coverage_and_advanced_signal():
    dep, ivy, cgg = strong_sources()
    dims = _advanced_dimensions(base_profile(), dep, ivy, cgg)
    score = _score_from_dimensions(dims)
    assert score.evidence_coverage_pct == 100.0
    assert dims["Functional dependency"].score > 70
    assert dims["Spatial context signal"].score > 70
    assert dims["Independent human validation"].score > 50
    print(f"PASS: V3 full advanced coverage={score.evidence_coverage_pct}% score={score.overall}")


def test_pan_essential_safeguard():
    dep, ivy, cgg = strong_sources()
    dep["pan_essential"] = True
    dims = _advanced_dimensions(base_profile(), dep, ivy, cgg)
    assert dims["Functional dependency"].score == 5.0
    print("PASS: pan-essential DepMap target is sharply down-weighted")


def test_missing_advanced_layers_reduce_coverage_not_base_scores():
    missing = {"ok": False, "error": "source unavailable"}
    dims = _advanced_dimensions(base_profile(), missing, missing, missing)
    score = _score_from_dimensions(dims)
    assert score.evidence_coverage_pct == 68.0
    assert dims["GBM genomic signal"].score == 70
    assert dims["Functional dependency"].score is None
    print("PASS: source outage lowers coverage without fabricating negative advanced evidence")


def test_ivygap_structure_mapping():
    expected = {
        "LE-reference-histology": "leading_edge",
        "IT-reference-histology": "infiltrating_tumor",
        "CT-CD44": "cellular_tumor",
        "CTpnz-CD44": "perinecrotic_zone",
        "CTpan-PDPN": "pseudopalisading_cells_around_necrosis",
        "CTmvp-ITGA6": "microvascular_proliferation",
        "CThbv-POSTN": "hyperplastic_blood_vessels",
    }
    for source, target in expected.items():
        assert _zone_from_structure(source) == target
    print("PASS: all seven Ivy GAP anatomic structure prefixes map correctly")


def test_glass_timepoint_parser():
    assert _sample_identity("GLSS-ABC-001-TP-01") == ("GLSS-ABC-001", "TP")
    assert _sample_identity("GLSS-ABC-001-R1-01") == ("GLSS-ABC-001", "R1")
    assert _sample_identity("not-a-glass-timepoint") is None
    print("PASS: GLASS TP/R# parser is deterministic")


def test_cgga_strict_adult_primary_idh_wt_filter():
    clinical = pd.DataFrame([
        {"CGGA_ID":"A","PRS_type":"Primary","Histology":"GBM","Grade":"WHO IV","Age":"55","OS":"300","Censor (alive=0; dead=1)":"1","IDH_mutation_status":"Wildtype"},
        {"CGGA_ID":"B","PRS_type":"Recurrent","Histology":"rGBM","Grade":"WHO IV","Age":"55","OS":"200","Censor (alive=0; dead=1)":"1","IDH_mutation_status":"Wildtype"},
        {"CGGA_ID":"C","PRS_type":"Primary","Histology":"GBM","Grade":"WHO IV","Age":"11","OS":"400","Censor (alive=0; dead=1)":"1","IDH_mutation_status":"Wildtype"},
        {"CGGA_ID":"D","PRS_type":"Primary","Histology":"GBM","Grade":"WHO IV","Age":"45","OS":"500","Censor (alive=0; dead=1)":"1","IDH_mutation_status":"Mutant"},
    ])
    out = _strict_gbm_frame(clinical, {"A":10,"B":20,"C":30,"D":40})
    assert out["CGGA_ID"].tolist() == ["A"]
    print("PASS: CGGA filter excludes recurrent, pediatric and IDH-mutant gliomas")


if __name__ == "__main__":
    test_v3_full_coverage_and_advanced_signal()
    test_pan_essential_safeguard()
    test_missing_advanced_layers_reduce_coverage_not_base_scores()
    test_ivygap_structure_mapping()
    test_glass_timepoint_parser()
    test_cgga_strict_adult_primary_idh_wt_filter()
    print("\nALL research_intelligence_v3 TESTS PASSED")
