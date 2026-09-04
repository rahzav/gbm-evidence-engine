"""
connectors/b3db.py
===================

B3DB (github.com/theochem/B3DB) is a static, open, citation-requested
compilation of ~7,800 compounds with BBB permeability labels/logBB values —
no registration, no live API (it's a flat file). This demo ships a small,
real, individually-cited subset (data/b3db_reference_subset.csv) rather than
the full file, since downloading the actual GitHub release requires network
access this sandbox does not have. See data/README.md.
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from .base import AccessTier

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_df_cache: Optional["pd.DataFrame"] = None


def _load() -> "pd.DataFrame":
    global _df_cache
    if _df_cache is None:
        _df_cache = pd.read_csv(DATA_DIR / "b3db_reference_subset.csv")
    return _df_cache


@dataclass
class BBBLookupResult:
    compound: str
    found: bool
    bbb_class: Optional[str] = None
    evidence_note: Optional[str] = None
    citation: Optional[str] = None
    access_tier: AccessTier = AccessTier.OPEN_BULK_DOWNLOAD


def lookup_compound(compound_name: str) -> BBBLookupResult:
    df = _load()
    match = df[df.compound.str.lower() == compound_name.lower()]
    if match.empty:
        return BBBLookupResult(compound=compound_name, found=False)
    row = match.iloc[0]
    return BBBLookupResult(
        compound=compound_name, found=True,
        bbb_class=row.bbb_class, evidence_note=row.evidence_note, citation=row.citation,
    )
