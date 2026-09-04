"""
connectors/ivygap.py
=====================

Ivy GAP is distributed as a bulk download / browsable atlas API (270
laser-microdissection RNA-seq samples across 7 anatomic zones, 41 patients),
not a simple per-gene REST call — see SOURCE_REGISTRY. Real deployment: pull
the RNA-seq expression matrix + the anatomic-structure metadata once,
harmonize gene symbols, cache. This demo falls back to the labeled synthetic
snapshot (data/README.md) since the real file cannot be downloaded here.
"""

from __future__ import annotations
import pandas as pd
from pathlib import Path
from dataclasses import dataclass

from .base import AccessTier
from ..analysis.spatial import IVYGAP_ANATOMIC_ZONES

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@dataclass
class ZoneExpressionData:
    gene: str
    zone_expression: dict
    access_tier: AccessTier
    dataset_version: str


def load_zone_expression(gene: str) -> ZoneExpressionData:
    path = DATA_DIR / f"synthetic_ivygap_zone_expression_{gene}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"No synthetic Ivy GAP snapshot for {gene}. Run "
            f"scripts/generate_synthetic_reference_data.py or deploy with network access "
            f"to ingest the real Ivy GAP release."
        )
    df = pd.read_csv(path)
    zone_expression = {
        zone: df.loc[df.anatomic_zone == zone, "log2_expression"].to_numpy()
        for zone in IVYGAP_ANATOMIC_ZONES
    }
    return ZoneExpressionData(
        gene=gene, zone_expression=zone_expression,
        access_tier=AccessTier.SYNTHETIC_ILLUSTRATIVE,
        dataset_version="SYNTHETIC demo snapshot (see data/README.md) — not the real Ivy GAP release",
    )
