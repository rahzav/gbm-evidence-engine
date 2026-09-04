"""
analysis/multiple_testing.py
=============================

Benjamini-Hochberg FDR correction. Applied automatically any time a dossier
covers more than one gene (see high-value capability test #5 — the 20-gene
batch triage case) or more than one statistical test on the same cohort.
A dossier that skips this is exactly the kind of quiet statistical error the
product brief's "scientific safeguards" section asks us to prevent.
"""

from __future__ import annotations
import numpy as np


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    p = np.asarray(p_values, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    corrected = ranked * n / (np.arange(n) + 1)
    # enforce monotonicity (standard BH step-up correction)
    corrected = np.minimum.accumulate(corrected[::-1])[::-1]
    corrected = np.clip(corrected, 0, 1)
    out = np.empty(n)
    out[order] = corrected
    return out.tolist()
