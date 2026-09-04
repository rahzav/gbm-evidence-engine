#!/usr/bin/env python3
"""Strict wrapper for the GBmap compact-reference build.

Uses the authors' explicit annotation hierarchy:
- annotation_level_1: Neoplastic vs Non-neoplastic
- annotation_level_3: biologically interpretable GBM cell states/types
- patient: patient identifier

This wrapper exists so ambiguous substring matching can never classify
"Non-neoplastic" as malignant.
"""
from __future__ import annotations

import sys

import build_gbmap_reference as base


def _strict_classify_state(state: str, class_value: str | None) -> str:
    value = str(class_value or "").strip().lower().replace("_", "-")
    if value in {"non-neoplastic", "nonneoplastic", "non-neoplastic cell", "nonneoplastic cell"}:
        return "microenvironment"
    if value in {"neoplastic", "malignant", "tumor", "tumour", "cancer"}:
        return "malignant"
    # Only fall back to canonical malignant state labels when the explicit class
    # annotation is genuinely absent. Never use the word "neoplastic" as a
    # substring heuristic.
    state_text = str(state or "").strip().lower()
    canonical = ("ac-like", "mes-like", "npc-like", "opc-like")
    if any(label in state_text for label in canonical):
        return "malignant"
    return "microenvironment"


base._classify_state = _strict_classify_state

if __name__ == "__main__":
    # The published GBmap construction notebooks define these exact annotation
    # fields. Supply them unless a caller has intentionally overridden them.
    defaults = [
        ("--state-column", "annotation_level_3"),
        ("--patient-column", "patient"),
        ("--class-column", "annotation_level_1"),
    ]
    for flag, value in defaults:
        if flag not in sys.argv:
            sys.argv.extend([flag, value])
    base.main()
