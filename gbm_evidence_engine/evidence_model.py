"""
evidence_model.py
==================

The single most important file in this codebase.

Every fact the system ever shows a researcher — a hazard ratio, a p-value,
a "this compound is BBB-penetrant", a "the AI thinks this is worth testing" —
must be wrapped in an `EvidenceRecord`. Nothing reaches a `Dossier` unless it
carries a tier, a source, and enough provenance for an independent
bioinformatician to reproduce it by hand.

Design rule (see docs/ARCHITECTURE.md, "Evidence model"):
    The AI layer is only allowed to CITE EvidenceRecords that already exist.
    It is never allowed to construct one from its own reasoning. If a claim
    doesn't have a record, it doesn't go in the dossier as fact — at most it
    goes in as an explicitly-labeled AI_INFERENCE record (see EvidenceTier).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class EvidenceTier(str, Enum):
    """
    The seven evidence classes the product brief requires us to keep visually
    and structurally distinct. Order here is NOT a confidence ranking —
    tiers are different in kind, not just in strength (an OBSERVED_DATA
    record from a 12-patient subgroup can be weaker than a well-powered
    STATISTICAL_ASSOCIATION from another cohort).
    """
    OBSERVED_DATA = "observed_data"                     # a value read directly off a dataset
    STATISTICAL_ASSOCIATION = "statistical_association"  # a test we ran (survival, dependency, enrichment)
    COMPUTATIONAL_PREDICTION = "computational_prediction"  # a model's output (e.g. BBB permeability classifier)
    LITERATURE_SUPPORTED_CLAIM = "literature_supported_claim"  # a claim from a specific cited paper
    CONFLICTING_EVIDENCE = "conflicting_evidence"        # two+ records that disagree — auto-generated, never hidden
    MECHANISTIC_HYPOTHESIS = "mechanistic_hypothesis"    # a proposed biological mechanism, not yet directly tested
    AI_GENERATED_INFERENCE = "ai_generated_inference"    # the AI layer's own suggestion — always the weakest tier


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INSUFFICIENT_DATA = "insufficient_data"


class AccessTier(str, Enum):
    """How the underlying source dataset may legally/technically be reached.
    See docs/ARCHITECTURE.md > Privacy/legal for why this distinction matters:
    it controls whether we may re-serve raw rows or only derived statistics."""
    OPEN_LIVE_API = "open_live_api"                 # no registration; queried live (e.g. Open Targets, Europe PMC)
    OPEN_BULK_DOWNLOAD = "open_bulk_download"        # no registration; periodic snapshot ingestion (e.g. Ivy GAP, DepMap public)
    REGISTRATION_GATED = "registration_gated"        # free account / DUA required (e.g. CGGA, GLASS via Synapse)
    DEMO_REFERENCE_VALUE = "demo_reference_value"    # a value taken from a cited publication for this prototype's demo
    SYNTHETIC_ILLUSTRATIVE = "synthetic_illustrative"  # NOT real data — illustrates a method only, always flagged loudly


@dataclass
class Provenance:
    source_dataset: str            # e.g. "TCGA-GBM (via cBioPortal)", "GLASS v3", "DepMap 24Q2"
    dataset_version: str           # release/version string
    access_tier: AccessTier
    accession_ids: list[str] = field(default_factory=list)   # sample/study/GEO/DOI ids touched
    method: str = ""                # human-readable method name
    parameters: dict[str, Any] = field(default_factory=dict)
    sample_size: Optional[int] = None
    citation: Optional[str] = None  # short citation string, never a full reproduced excerpt
    citation_url: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EvidenceRecord:
    claim_text: str
    tier: EvidenceTier
    provenance: Provenance
    statistic_name: Optional[str] = None
    statistic_value: Optional[float] = None
    p_value: Optional[float] = None
    corrected_p_value: Optional[float] = None
    effect_size: Optional[float] = None
    confidence_interval: Optional[tuple[float, float]] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    caveats: list[str] = field(default_factory=list)   # e.g. "EGFR amplification is known to be lost in adherent culture"
    additional_stats: dict[str, float] = field(default_factory=dict)  # supplementary numbers referenced in claim_text
    id: str = field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:10]}")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tier"] = self.tier.value
        d["confidence"] = self.confidence.value
        d["provenance"]["access_tier"] = self.provenance.access_tier.value
        return d


@dataclass
class Dossier:
    """The full, exportable result of one research question."""
    query: str
    target: str                              # gene symbol / pathway / gene-set label
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence: list[EvidenceRecord] = field(default_factory=list)
    ai_synthesis: Optional[str] = None       # grounded prose — see orchestrator/synthesizer.py
    ai_synthesis_grounding_ok: Optional[bool] = None
    warnings: list[str] = field(default_factory=list)   # scientific safeguards (batch effects, small n, etc.)
    session_id: str = field(default_factory=lambda: f"session_{uuid.uuid4().hex[:12]}")

    def add(self, record: EvidenceRecord) -> EvidenceRecord:
        self.evidence.append(record)
        return record

    def by_tier(self, tier: EvidenceTier) -> list[EvidenceRecord]:
        return [e for e in self.evidence if e.tier == tier]

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "target": self.target,
            "generated_at": self.generated_at,
            "session_id": self.session_id,
            "evidence": [e.to_dict() for e in self.evidence],
            "ai_synthesis": self.ai_synthesis,
            "ai_synthesis_grounding_ok": self.ai_synthesis_grounding_ok,
            "warnings": self.warnings,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)
