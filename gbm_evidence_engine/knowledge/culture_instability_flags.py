"""
knowledge/culture_instability_flags.py
=======================================

A small, deliberately human-curated registry of genes/alterations with
documented instability in standard 2D adherent cell culture — meaning a
DepMap-style dependency screen can systematically UNDERESTIMATE their
importance, because the cell lines in the screen may have already lost the
alteration that made the gene matter in the patient's tumor.

This is exactly the kind of disease-specific domain curation that a generic
tool-calling agent (one that just calls the DepMap API and reports the
number) has no mechanism to apply — it requires someone to have actually
read the cell-culture-model literature for this disease. It is intentionally
NOT AI-inferred: every entry here must cite a real paper, and the system
raises this as a `caveats` entry on the relevant EvidenceRecord rather than
silently adjusting any number.

Adding an entry: cite at least one primary study. Do not add a gene here
from general plausibility — this list is only useful if it is trustworthy.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class CultureInstabilityFlag:
    gene: str
    alteration: str
    note: str
    citations: tuple[str, ...]


CULTURE_INSTABILITY_REGISTRY: dict[str, CultureInstabilityFlag] = {
    "EGFR": CultureInstabilityFlag(
        gene="EGFR",
        alteration="EGFR gene amplification / EGFRvIII",
        note=(
            "EGFR amplification is well documented to be rapidly lost during standard "
            "adherent (serum-containing) cell-line culture, and is far better preserved in "
            "xenografts, patient-derived spheroid/stem-cell cultures, or serum-free EGF-restricted "
            "conditions. A DepMap CRISPR dependency score for EGFR computed from long-established "
            "adherent GBM lines may therefore understate EGFR's true importance in EGFR-amplified "
            "patient tumors; cross-check against xenograft/PDX-based functional studies before "
            "concluding EGFR is 'not a dependency' in GBM."
        ),
        citations=(
            "Bigner et al., Cancer Res 1990 (PMID varies by index) — cultured lines from "
            "EGFR-amplified biopsies lost the amplification in vitro while xenografts retained it.",
            "Pandita et al., Genes Chromosomes Cancer 2004 / follow-up culture studies — EGFR "
            "amplification lost progressively in adherent culture, preserved in spheroid culture.",
            "PMC5608330 (2017) — EGFR copy number can be maintained in vitro only under serum-free, "
            "EGF-modulated conditions.",
        ),
    ),
}


def get_flag(gene: str) -> CultureInstabilityFlag | None:
    return CULTURE_INSTABILITY_REGISTRY.get(gene.upper())
