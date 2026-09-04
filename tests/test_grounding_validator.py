"""
tests/test_grounding_validator.py
====================================

This is the concrete test behind the product brief's requirement to
"test hallucination resistance" before claiming success. It does not just
check that the validator passes on good text (see test_passes_on_correctly_
grounded_synthesis) -- it constructs a synthesis paragraph containing a
statistic that was NEVER computed anywhere in the dossier, and asserts the
validator flags it. If this test ever goes green without genuinely checking
anything, that's a bug in the test, not a passing feature -- read it
carefully before trusting it.

Run with: PYTHONPATH=. python3 tests/test_grounding_validator.py
"""
import sys
sys.path.insert(0, ".")
from gbm_evidence_engine.evidence_model import (
    Dossier, EvidenceRecord, EvidenceTier, Provenance, AccessTier
)
from gbm_evidence_engine.orchestrator.synthesizer import (
    generate_synthesis, validate_numeric_grounding
)


def _sample_dossier() -> Dossier:
    dossier = Dossier(query="test", target="TESTGENE")
    dossier.add(EvidenceRecord(
        claim_text="TESTGENE association with survival in Cohort A",
        tier=EvidenceTier.STATISTICAL_ASSOCIATION,
        provenance=Provenance("Cohort A", "v1", AccessTier.OPEN_LIVE_API, sample_size=200),
        statistic_name="hazard_ratio", statistic_value=1.45, p_value=0.02,
    ))
    return dossier


def test_passes_on_correctly_grounded_synthesis():
    dossier = _sample_dossier()
    synthesis = generate_synthesis(dossier)
    check = validate_numeric_grounding(synthesis, dossier)
    assert check.ok, f"Correctly-grounded synthesis was wrongly rejected: {check.unmatched_numbers}"
    print("PASS: validator accepts a synthesis whose numbers are all real")


def test_rejects_fabricated_statistic():
    dossier = _sample_dossier()
    # A REAL failure mode: an LLM (or a careless template) states a specific,
    # plausible-sounding hazard ratio that was never actually computed --
    # here 2.91, which does not appear anywhere in the dossier's evidence.
    fabricated_synthesis = (
        "TESTGENE shows a hazard ratio of 2.91 (p=0.02) for survival in Cohort A, "
        "indicating a very strong prognostic effect."
    )
    check = validate_numeric_grounding(fabricated_synthesis, dossier)
    assert not check.ok, "Validator FAILED to catch a fabricated hazard ratio -- this is a real bug"
    assert "2.91" in check.unmatched_numbers
    print(f"PASS: validator correctly rejects fabricated statistic 2.91 "
          f"(unmatched: {check.unmatched_numbers})")


def test_rejects_fabricated_sample_size():
    dossier = _sample_dossier()
    fabricated_synthesis = "TESTGENE was tested in a cohort of 9999 patients (HR=1.45, p=0.02)."
    check = validate_numeric_grounding(fabricated_synthesis, dossier)
    assert not check.ok
    assert "9999" in check.unmatched_numbers
    print(f"PASS: validator correctly rejects a fabricated sample size "
          f"(unmatched: {check.unmatched_numbers})")


def test_accepts_real_number_at_different_rounding():
    dossier = _sample_dossier()
    # 1.4 is a standard rounding of the stored value 1.45 -- should be accepted;
    # (note: due to binary floating-point representation, 1.45 is stored as
    # slightly less than 1.45, so it rounds DOWN to 1.4, not up to 1.5 -- this
    # test intentionally checks the rounding the implementation actually
    # produces rather than asserting a human "should round to" expectation).
    synthesis = "TESTGENE hazard ratio was approximately 1.4 (p=0.02)."
    check = validate_numeric_grounding(synthesis, dossier)
    assert check.ok, check.unmatched_numbers
    print("PASS: validator tolerates reasonable rounding of a real statistic")


if __name__ == "__main__":
    test_passes_on_correctly_grounded_synthesis()
    test_rejects_fabricated_statistic()
    test_rejects_fabricated_sample_size()
    test_accepts_real_number_at_different_rounding()
    print("\nALL grounding_validator TESTS PASSED -- fabricated statistics are genuinely caught, not just assumed to be")
