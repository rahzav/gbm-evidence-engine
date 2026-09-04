"""
connectors/depmap.py
=====================

DepMap is distributed as versioned bulk downloads (see SOURCE_REGISTRY),
not a low-latency per-gene REST endpoint, so "ingestion" here means: pull
the quarterly release's CRISPRGeneEffect.csv + Model.csv once, cache them,
and serve gene-level slices out of the cache. This module implements that
loader against a real DepMap file layout; because this sandbox cannot
download the real release, `load_gene_effect_scores` falls back to the
labeled synthetic snapshot in data/ when the real file is not present.
"""

from __future__ import annotations
import pandas as pd
from pathlib import Path
from dataclasses import dataclass

from .base import SOURCE_REGISTRY, AccessTier

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
REAL_EFFECT_FILE = DATA_DIR / "_cache" / "CRISPRGeneEffect.csv"  # where a real deployment would cache it


@dataclass
class GeneEffectData:
    gene: str
    gbm_scores: "pd.Series"
    other_scores: "pd.Series"
    access_tier: AccessTier
    dataset_version: str


def load_gene_effect_scores(gene: str) -> GeneEffectData:
    if REAL_EFFECT_FILE.exists():
        # Real deployment path: a real DepMap CRISPRGeneEffect.csv (genes as columns,
        # ModelID as rows) joined against Model.csv's OncotreeLineage == "CNS/Brain"
        # and a GBM sub-filter. Left as an integration point for a networked deployment.
        raise NotImplementedError(
            "Real DepMap file detected but the join/filter logic for a live deployment "
            "is a deployment-time task (see docs/ARCHITECTURE.md) — not exercised in this demo."
        )

    synthetic_path = DATA_DIR / f"synthetic_depmap_effect_scores_{gene}.csv"
    if not synthetic_path.exists():
        raise FileNotFoundError(
            f"No real DepMap cache and no synthetic snapshot for {gene}. "
            f"Run scripts/generate_synthetic_reference_data.py or deploy with network access."
        )
    df = pd.read_csv(synthetic_path)
    gbm = df.loc[df.lineage == "glioblastoma", "gene_effect_score"]
    other = df.loc[df.lineage == "other", "gene_effect_score"]
    return GeneEffectData(
        gene=gene, gbm_scores=gbm, other_scores=other,
        access_tier=AccessTier.SYNTHETIC_ILLUSTRATIVE,
        dataset_version="SYNTHETIC demo snapshot (see data/README.md) — not a real DepMap release",
    )
