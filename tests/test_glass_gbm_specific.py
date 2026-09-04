"""Deterministic tests for strict GLASS GBM longitudinal integration."""
import pandas as pd

from gbm_evidence_engine.connectors.glass import (
    _sample_barcode,
    _verified_gbm_samples,
)
from gbm_evidence_engine.research_intelligence_v4 import _glass_dimension


def test_sample_barcode_parser():
    assert _sample_barcode("GLSS-MD-0137-TP-01D-RNA-ABC") == "GLSS-MD-0137-TP"
    assert _sample_barcode("GLSS-MD-0137-R1-01D-RNA-XYZ") == "GLSS-MD-0137-R1"
    assert _sample_barcode("not-a-glass-sample") is None


def test_strict_clinical_filter():
    clinical = pd.DataFrame([
        {"case_barcode": "GLSS-A-0001", "sample_barcode": "GLSS-A-0001-TP", "histology": "GBM", "grade": "IV", "idh_status": "IDHwt"},
        {"case_barcode": "GLSS-A-0001", "sample_barcode": "GLSS-A-0001-R1", "histology": "Glioblastoma", "grade": "IV", "idh_status": "wildtype"},
        {"case_barcode": "GLSS-A-0002", "sample_barcode": "GLSS-A-0002-TP", "histology": "GBM", "grade": "IV", "idh_status": "IDHmut"},
        {"case_barcode": "GLSS-A-0003", "sample_barcode": "GLSS-A-0003-TP", "histology": "Oligodendroglioma", "grade": "III", "idh_status": "IDHwt"},
    ])
    verified, mapping = _verified_gbm_samples(clinical)
    assert verified == {"GLSS-A-0001-TP", "GLSS-A-0001-R1"}
    assert mapping["GLSS-A-0001-TP"] == "GLSS-A-0001"


def test_glass_never_scores_unverified_data():
    missing = _glass_dimension({"ok": False, "status": "credentials_required", "gbm_specific": False})
    assert missing.score is None

    diffuse = _glass_dimension({
        "ok": True,
        "gbm_specific": False,
        "n_pairs": 50,
        "median_delta": 2.0,
        "p_value": 1e-8,
        "fraction_increased": 0.9,
    })
    assert diffuse.score is None


def test_verified_glass_scores():
    strict = _glass_dimension({
        "ok": True,
        "gbm_specific": True,
        "n_pairs": 30,
        "median_delta": 0.9,
        "p_value": 0.001,
        "fraction_increased": 0.8,
    })
    assert strict.score is not None
    assert 0 < strict.score <= 100
    assert strict.weight == 0.06


if __name__ == "__main__":
    test_sample_barcode_parser()
    test_strict_clinical_filter()
    test_glass_never_scores_unverified_data()
    test_verified_glass_scores()
    print("ALL GLASS GBM-SPECIFIC TESTS PASSED")
