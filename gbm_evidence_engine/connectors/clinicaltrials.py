"""
connectors/clinicaltrials.py
=============================

Live connector for the ClinicalTrials.gov API v2
(https://clinicaltrials.gov/api/v2). Used for the trial-landscape evidence
layer: "is anyone currently testing a compound against this target in GBM,
and at what phase". No API key required.
"""

from __future__ import annotations
from typing import Optional
import urllib.parse
from .base import http_get_json, SOURCE_REGISTRY

BASE = SOURCE_REGISTRY["clinicaltrials"].base_url


def search_trials(condition: str = "glioblastoma", intervention: Optional[str] = None,
                   page_size: int = 20) -> Optional[dict]:
    params = {
        "query.cond": condition,
        "pageSize": str(page_size),
        "format": "json",
    }
    if intervention:
        params["query.intr"] = intervention
    qs = urllib.parse.urlencode(params)
    return http_get_json(f"{BASE}/studies?{qs}")
