"""
analysis/spatial.py
====================

Tests whether a gene's expression differs across the anatomic/histologic
zones captured by the Ivy Glioblastoma Atlas Project's laser-microdissection
RNA-seq (leading edge, infiltrating tumor, cellular tumor, perinecrotic zone,
pseudopalisading cells around necrosis, microvascular proliferation,
hyperplastic blood vessels). This is the deterministic half of the "which
spatial niche is this gene enriched in" workflow described in the product
brief's high-value capability test #2.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy import stats


IVYGAP_ANATOMIC_ZONES = [
    "leading_edge",
    "infiltrating_tumor",
    "cellular_tumor",
    "perinecrotic_zone",
    "pseudopalisading_cells_around_necrosis",
    "microvascular_proliferation",
    "hyperplastic_blood_vessels",
]


@dataclass
class SpatialEnrichmentResult:
    gene: str
    zones: list[str]
    zone_medians: dict[str, float]
    h_statistic: float
    p_value: float
    top_zone: str
    n_samples_total: int


def anatomic_enrichment_test(gene: str, zone_expression: dict[str, np.ndarray]) -> SpatialEnrichmentResult:
    """zone_expression: {zone_name: array of per-sample expression values (e.g. log2 TPM)}"""
    groups = [np.asarray(v, dtype=float) for v in zone_expression.values() if len(v) > 0]
    zones = [k for k, v in zone_expression.items() if len(v) > 0]
    if len(groups) < 2:
        raise ValueError("Need at least two non-empty anatomic zones to test enrichment.")

    h_stat, p_value = stats.kruskal(*groups)
    medians = {z: float(np.median(g)) for z, g in zip(zones, groups)}
    top_zone = max(medians, key=medians.get)

    return SpatialEnrichmentResult(
        gene=gene,
        zones=zones,
        zone_medians=medians,
        h_statistic=float(h_stat),
        p_value=float(p_value),
        top_zone=top_zone,
        n_samples_total=sum(len(g) for g in groups),
    )
