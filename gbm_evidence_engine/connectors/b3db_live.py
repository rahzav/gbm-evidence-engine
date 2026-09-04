"""Live B3DB blood-brain barrier matching for target-directed candidate drugs."""
from __future__ import annotations

import io
import re
import urllib.request
from typing import Any

import pandas as pd

from .base import USER_AGENT

CLASSIFICATION_URL = "https://raw.githubusercontent.com/theochem/B3DB/main/B3DB/B3DB_classification.tsv"
REGRESSION_URL = "https://raw.githubusercontent.com/theochem/B3DB/main/B3DB/B3DB_regression.tsv"
_classification_cache: pd.DataFrame | None = None
_regression_cache: pd.DataFrame | None = None


def _download_tsv(url: str) -> pd.DataFrame | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        return pd.read_csv(io.StringIO(text), sep="\t", low_memory=False)
    except Exception:
        return None


def _norm(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def _column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    normalized = {_norm(c): c for c in df.columns}
    for candidate in candidates:
        key = _norm(candidate)
        if key in normalized:
            return normalized[key]
    for col in df.columns:
        n = _norm(col)
        if any(_norm(c) in n or n in _norm(c) for c in candidates):
            return col
    return None


def _load() -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    global _classification_cache, _regression_cache
    if _classification_cache is None:
        _classification_cache = _download_tsv(CLASSIFICATION_URL)
    if _regression_cache is None:
        _regression_cache = _download_tsv(REGRESSION_URL)
    return _classification_cache, _regression_cache


def _match_rows(df: pd.DataFrame | None, drug: str) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    name_col = _column(df, ["compound_name", "compound name", "name"])
    iupac_col = _column(df, ["IUPAC_name", "IUPAC name"])
    target = _norm(drug)
    if not target:
        return None
    mask = pd.Series(False, index=df.index)
    if name_col:
        mask = mask | df[name_col].astype(str).map(_norm).eq(target)
    if iupac_col:
        mask = mask | df[iupac_col].astype(str).map(_norm).eq(target)
    rows = df[mask]
    return rows if not rows.empty else None


def lookup_candidates(drug_names: list[str], max_candidates: int = 20) -> dict:
    names = list(dict.fromkeys(str(x).strip() for x in drug_names if str(x).strip()))[:max_candidates]
    if not names:
        return {"ok": True, "candidates_checked": 0, "matches": [], "source": "B3DB"}
    classification, regression = _load()
    if classification is None and regression is None:
        return {"ok": False, "error": "B3DB source files unavailable.", "matches": []}

    class_label_col = _column(classification, ["BBB+/BBB-", "BBB", "label", "class"]) if classification is not None else None
    class_name_col = _column(classification, ["compound_name", "compound name", "name"]) if classification is not None else None
    reg_log_col = _column(regression, ["logBB", "log BB"]) if regression is not None else None
    reg_name_col = _column(regression, ["compound_name", "compound name", "name"]) if regression is not None else None
    matches = []

    for drug in names:
        class_rows = _match_rows(classification, drug)
        reg_rows = _match_rows(regression, drug)
        if class_rows is None and reg_rows is None:
            continue
        bbb_class = None
        matched_name = drug
        if class_rows is not None:
            row = class_rows.iloc[0]
            if class_label_col:
                bbb_class = row.get(class_label_col)
            if class_name_col and row.get(class_name_col):
                matched_name = str(row.get(class_name_col))
        logbb = None
        if reg_rows is not None:
            row = reg_rows.iloc[0]
            if reg_log_col:
                try:
                    logbb = float(row.get(reg_log_col))
                except (TypeError, ValueError):
                    pass
            if reg_name_col and row.get(reg_name_col):
                matched_name = str(row.get(reg_name_col))
        matches.append({
            "candidate": drug,
            "matched_compound": matched_name,
            "bbb_class": str(bbb_class) if bbb_class is not None else None,
            "logBB": logbb,
            "evidence_type": "experimental database match",
        })

    permeable = sum(1 for r in matches if str(r.get("bbb_class") or "").upper().replace(" ", "") in {"BBB+", "+", "1", "TRUE"})
    impermeable = sum(1 for r in matches if str(r.get("bbb_class") or "").upper().replace(" ", "") in {"BBB-", "-", "0", "FALSE"})
    return {
        "ok": True,
        "candidates_checked": len(names),
        "matched_count": len(matches),
        "bbb_positive_count": permeable,
        "bbb_negative_count": impermeable,
        "matches": matches,
        "source": "B3DB",
        "source_url": "https://github.com/theochem/B3DB",
        "interpretation": "B3DB matches are experimental BBB-permeability records for compounds with resolvable names. A missing match means no exact name match was found, not that a compound cannot cross the BBB.",
    }
