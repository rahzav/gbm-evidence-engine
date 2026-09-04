"""
tests/test_evidence_model.py
==============================
Run with: PYTHONPATH=. python3 tests/test_evidence_model.py
"""
import sys, json
sys.path.insert(0, ".")
from gbm_evidence_engine.evidence_model import (
    Dossier, EvidenceRecord, EvidenceTier, ConfidenceLevel, Provenance, AccessTier
)


def test_evidence_record_round_trips_to_json():
    rec = EvidenceRecord(
        claim_text="Test claim",
        tier=EvidenceTier.STATISTICAL_ASSOCIATION,
        provenance=Provenance(
            source_dataset="TestSource", dataset_version="v1",
            access_tier=AccessTier.OPEN_LIVE_API, sample_size=100,
        ),
        statistic_value=1.5, p_value=0.01,
    )
    d = rec.to_dict()
    assert d["tier"] == "statistical_association"
    assert d["provenance"]["access_tier"] == "open_live_api"
    json.dumps(d)  # must not raise
    print("PASS: EvidenceRecord serializes to valid JSON with enum values as strings")


def test_dossier_by_tier_filters_correctly():
    dossier = Dossier(query="q", target="GENE")
    dossier.add(EvidenceRecord(
        claim_text="a", tier=EvidenceTier.STATISTICAL_ASSOCIATION,
        provenance=Provenance("S", "v1", AccessTier.OPEN_LIVE_API),
    ))
    dossier.add(EvidenceRecord(
        claim_text="b", tier=EvidenceTier.AI_GENERATED_INFERENCE,
        provenance=Provenance("S", "v1", AccessTier.OPEN_LIVE_API),
    ))
    stats = dossier.by_tier(EvidenceTier.STATISTICAL_ASSOCIATION)
    ai = dossier.by_tier(EvidenceTier.AI_GENERATED_INFERENCE)
    assert len(stats) == 1 and stats[0].claim_text == "a"
    assert len(ai) == 1 and ai[0].claim_text == "b"
    print("PASS: Dossier.by_tier correctly separates evidence classes")


def test_full_dossier_serializes_end_to_end():
    dossier = Dossier(query="q", target="GENE")
    dossier.add(EvidenceRecord(
        claim_text="a", tier=EvidenceTier.OBSERVED_DATA,
        provenance=Provenance("S", "v1", AccessTier.OPEN_BULK_DOWNLOAD, sample_size=42),
        confidence=ConfidenceLevel.HIGH,
    ))
    dossier.warnings.append("a warning")
    text = dossier.to_json()
    parsed = json.loads(text)
    assert parsed["target"] == "GENE"
    assert parsed["warnings"] == ["a warning"]
    assert parsed["evidence"][0]["confidence"] == "high"
    print("PASS: full Dossier.to_json round-trips correctly")


if __name__ == "__main__":
    test_evidence_record_round_trips_to_json()
    test_dossier_by_tier_filters_correctly()
    test_full_dossier_serializes_end_to_end()
    print("\nALL evidence_model.py TESTS PASSED")
