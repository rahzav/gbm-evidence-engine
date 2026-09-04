"""
analysis/dependency.py
=======================

Tests whether a gene is a *selective* dependency in GBM-lineage cell lines
relative to the rest of the DepMap panel — i.e. "would knocking this out
plausibly kill GBM cells more than it kills a random cell line".

Two safeguards a naive script (or a generic tool-calling agent) typically
skips, both encoded deterministically rather than left to an LLM's judgment:

1. Pan-essential flag: a gene essential in ~every lineage (ribosomal
   proteins, spliceosome components, etc.) is not a useful cancer target
   even with a "significant" p-value — flag it so it isn't mis-sold as
   GBM-selective.
2. Culture-instability flag: some GBM-relevant genes (EGFR is the classic
   case) are well documented to be lost/altered during adherent cell-line
   culture, which can make DepMap screens systematically underestimate
   their true in-tumor importance. See knowledge/culture_instability_flags.py.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy import stats


@dataclass
class DependencyResult:
    gene: str
    median_effect_gbm: float
    median_effect_other: float
    u_statistic: float
    p_value: float
    rank_biserial_effect_size: float
    n_gbm_lines: int
    n_other_lines: int
    pan_essential: bool


PAN_ESSENTIAL_EFFECT_THRESHOLD = -0.5  # Chronos-scale: below this in >90% of ALL lineages => pan-essential
PAN_ESSENTIAL_FRACTION_THRESHOLD = 0.9


def selective_dependency_test(
    gene: str,
    gbm_effect_scores: np.ndarray,
    other_lineage_effect_scores: np.ndarray,
) -> DependencyResult:
    gbm = np.asarray(gbm_effect_scores, dtype=float)
    other = np.asarray(other_lineage_effect_scores, dtype=float)

    u_stat, p_value = stats.mannwhitneyu(gbm, other, alternative="less")  # "less" = GBM more dependent (more negative)
    n1, n2 = len(gbm), len(other)
    rank_biserial = 1 - (2 * u_stat) / (n1 * n2)

    all_scores = np.concatenate([gbm, other])
    fraction_essential = float(np.mean(all_scores < PAN_ESSENTIAL_EFFECT_THRESHOLD))
    pan_essential = fraction_essential >= PAN_ESSENTIAL_FRACTION_THRESHOLD

    return DependencyResult(
        gene=gene,
        median_effect_gbm=float(np.median(gbm)),
        median_effect_other=float(np.median(other)),
        u_statistic=float(u_stat),
        p_value=float(p_value),
        rank_biserial_effect_size=float(rank_biserial),
        n_gbm_lines=n1,
        n_other_lines=n2,
        pan_essential=pan_essential,
    )
