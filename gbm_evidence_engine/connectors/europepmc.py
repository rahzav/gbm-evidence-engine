"""
connectors/europepmc.py
========================

Live REST client for Europe PMC (no registration required). Used for the
literature-evidence layer: co-mention counts and top abstracts for a
gene + GBM-context query, so the dossier can show "N papers support this,
M discuss it as unresolved/controversial" rather than a single vibe-based
LLM summary of "what the literature says".

Real endpoint (confirmed against Europe PMC's documented RESTful API):
    GET https://www.ebi.ac.uk/europepmc/webservices/rest/search
        ?query=...&resultType=core&pageSize=...&format=json
"""

from __future__ import annotations
from typing import Optional
from .base import http_get_json, SOURCE_REGISTRY
import urllib.parse

BASE = SOURCE_REGISTRY["europepmc"].base_url


def search(query: str, page_size: int = 10) -> Optional[dict]:
    q = urllib.parse.quote_plus(query)
    url = f"{BASE}/search?query={q}&resultType=core&pageSize={page_size}&format=json"
    return http_get_json(url)


def co_mention_count(gene: str, context: str = "glioblastoma") -> Optional[int]:
    """Rough literature-support signal: how many indexed articles mention both terms."""
    result = search(f'"{gene}" AND "{context}"', page_size=1)
    if result is None:
        return None
    return result.get("hitCount")
