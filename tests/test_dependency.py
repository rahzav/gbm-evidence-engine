"""
tests/test_dependency.py
=========================
Run with: PYTHONPATH=. python3 tests/test_dependency.py
"""
import sys
import numpy as np
sys.path.insert(0, ".")
from gbm_evidence_engine.analysis.dependency import selective_dependency_test


def test_detects_genuine_selective_dependency():
    rng = np.random.default_rng(10)
    gbm = rng.normal(-1.2, 0.2, size=30)     # strongly dependent in GBM
    other = rng.normal(-0.1, 0.3, size=700)  # not dependent elsewhere
    result = selective_dependency_test("FAKE_SELECTIVE_GENE", gbm, other)
    assert result.p_value < 0.001, result.p_value
    assert result.median_effect_gbm < result.median_effect_other
    assert not result.pan_essential, "should not be flagged pan-essential -- it's selective, not universal"
    print(f"PASS: genuine selective dependency detected (p={result.p_value:.2e}, "
          f"pan_essential={result.pan_essential})")


def test_flags_pan_essential_gene():
    rng = np.random.default_rng(11)
    gbm = rng.normal(-1.3, 0.1, size=30)     # very negative everywhere
    other = rng.normal(-1.25, 0.1, size=700)  # equally negative in every other lineage
    result = selective_dependency_test("FAKE_PANESSENTIAL_GENE", gbm, other)
    assert result.pan_essential, "a gene essential in ~everything must be flagged pan-essential"
    print(f"PASS: pan-essential gene correctly flagged (fraction below threshold triggers flag)")


def test_no_selectivity_when_truly_equal():
    rng = np.random.default_rng(12)
    gbm = rng.normal(0.0, 0.3, size=30)
    other = rng.normal(0.0, 0.3, size=700)
    result = selective_dependency_test("FAKE_NULL_GENE", gbm, other)
    assert result.p_value > 0.05, result.p_value
    print(f"PASS: no false-positive selectivity when distributions genuinely match (p={result.p_value:.3f})")


if __name__ == "__main__":
    test_detects_genuine_selective_dependency()
    test_flags_pan_essential_gene()
    test_no_selectivity_when_truly_equal()
    print("\nALL dependency.py TESTS PASSED")
