"""
connectors/literature_reference.py
====================================

Loads data/reference_literature_facts.json — REAL facts gathered via live
web search during this build session (see data/README.md), used as a stand-
in for connectors/europepmc.py's live query in this network-disabled
sandbox. Every fact here was independently verified against a real,
identifiable source at build time; connectors/europepmc.py is what a
deployed instance would call instead for a fresh, up-to-date literature
pull on an arbitrary gene (this static file only covers EGFR).
"""
from __future__ import annotations
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def load_reference_facts(gene: str) -> dict:
    path = DATA_DIR / "reference_literature_facts.json"
    with open(path) as f:
        data = json.load(f)
    if data.get("gene", "").upper() != gene.upper():
        return {"gene": gene, "facts": []}
    return data
