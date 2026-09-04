"""
connectors/cohort_survival.py
==============================

Unifies the three cohort sources used by the cross-cohort survival evidence
layer (docs/ARCHITECTURE.md, core primitive). Each cohort has a genuinely
different real access path:

  * TCGA-GBM   -> live cBioPortal API call (connectors/cbioportal.py) for
                  clinical + molecular data, no registration.
  * CGGA       -> registration-gated bulk download (SOURCE_REGISTRY); a
                  deployed instance ingests it into the same cache format
                  after a team member completes CGGA's registration.
  * GLASS      -> registration-gated Synapse project (SOURCE_REGISTRY);
                  same pattern, via a Synapse account + accepted DUA.

In this network-disabled sandbox all three fall back to labeled slices of
the synthetic calibrated cohort file (see data/README.md). The important
thing this module gets right for a real deployment is the *shape* of the
harmonization: every cohort must expose the same column contract
(os_months, event, {gene}_amplified or _high, age) before it can be handed
to analysis/survival.py — that harmonization step is exactly the tedious,
error-prone, currently-manual part of this workflow (see the CD44 / GLASS-
SASP / MES-lncRNA papers cited in docs/ARCHITECTURE.md, all of which built
this harmonization by hand, once, for a single gene).
"""

from __future__ import annotations
import pandas as pd
from pathlib import Path
from dataclasses import dataclass

from .base import AccessTier, SOURCE_REGISTRY

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

COHORT_TO_SYNTHETIC_LABEL = {
    "TCGA_GBM": "TCGA_like_US",
    "CGGA": "CGGA_like_nonUS",
    "GLASS_recurrent": "GLASS_like_recurrent",
}

COHORT_SOURCE_KEY = {
    "TCGA_GBM": "cbioportal",
    "CGGA": "cgga",
    "GLASS_recurrent": "glass",
}


@dataclass
class CohortSurvivalData:
    cohort: str
    gene: str
    df: "pd.DataFrame"          # columns: os_months, event, {gene}_amplified, age
    access_tier: AccessTier
    source_meta_key: str
    n: int


def load_cohort_survival(cohort: str, gene: str) -> CohortSurvivalData:
    if cohort not in COHORT_TO_SYNTHETIC_LABEL:
        raise ValueError(f"Unknown cohort '{cohort}'. Known: {list(COHORT_TO_SYNTHETIC_LABEL)}")

    synthetic_path = DATA_DIR / f"synthetic_cohort_survival_{gene}.csv"
    if not synthetic_path.exists():
        raise FileNotFoundError(
            f"No synthetic survival snapshot for {gene}. Run "
            f"scripts/generate_synthetic_reference_data.py, or in a networked deployment "
            f"call connectors.cbioportal / a completed CGGA / GLASS ingestion instead."
        )
    full = pd.read_csv(synthetic_path)
    label = COHORT_TO_SYNTHETIC_LABEL[cohort]
    sub = full[full.cohort == label].copy()
    sub = sub.rename(columns={"egfr_amplified": f"{gene.lower()}_amplified"})

    return CohortSurvivalData(
        cohort=cohort, gene=gene, df=sub,
        access_tier=AccessTier.SYNTHETIC_ILLUSTRATIVE,
        source_meta_key=COHORT_SOURCE_KEY[cohort],
        n=len(sub),
    )
