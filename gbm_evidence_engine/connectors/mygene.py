"""Canonical human gene identity resolution through MyGene.info."""
from __future__ import annotations

import urllib.parse
from typing import Any

from .base import http_get_json

BASE = "https://mygene.info/v3"


def _aliases(hit: dict[str, Any]) -> list[str]:
    value = hit.get("alias")
    if isinstance(value, list):
        return [str(x) for x in value if x]
    if value:
        return [str(value)]
    return []


def _ensembl_gene(hit: dict[str, Any]) -> str | None:
    value = hit.get("ensembl")
    if isinstance(value, dict):
        gene = value.get("gene")
        return str(gene) if gene else None
    if isinstance(value, list):
        for row in value:
            if isinstance(row, dict) and row.get("gene"):
                return str(row["gene"])
    return None


def resolve_gene(query: str) -> dict:
    """Resolve a user-entered human gene symbol or alias to a canonical symbol.

    Failure is non-fatal because the rest of the profile can still attempt to
    resolve the supplied symbol independently through cBioPortal/Open Targets.
    """
    raw = query.strip()
    if not raw:
        return {"ok": False, "query": query, "error": "Gene symbol is empty."}
    q = raw.upper()
    params = urllib.parse.urlencode({
        "q": q,
        "species": "human",
        "fields": "symbol,name,alias,entrezgene,ensembl.gene,taxid",
        "size": 10,
    })
    response = http_get_json(f"{BASE}/query?{params}", timeout=15)
    if not isinstance(response, dict):
        return {"ok": False, "query": q, "status": "unavailable", "error": "MyGene.info unavailable."}
    hits = [h for h in (response.get("hits") or []) if int(h.get("taxid") or 9606) == 9606]
    if not hits:
        return {"ok": False, "query": q, "status": "not_found", "error": "No human gene match was found."}

    exact_symbol = next((h for h in hits if str(h.get("symbol") or "").upper() == q), None)
    exact_alias = next((h for h in hits if q in {a.upper() for a in _aliases(h)}), None)
    hit = exact_symbol or exact_alias or hits[0]
    symbol = str(hit.get("symbol") or "").upper()
    if not symbol:
        return {"ok": False, "query": q, "status": "ambiguous", "error": "Gene match did not include a canonical symbol."}

    matched_by = "symbol" if exact_symbol is hit else "alias" if exact_alias is hit else "best_match"
    aliases = sorted(set(a for a in _aliases(hit) if a.upper() != symbol))
    return {
        "ok": True,
        "query": q,
        "symbol": symbol,
        "name": hit.get("name"),
        "aliases": aliases[:30],
        "entrez_gene_id": hit.get("entrezgene"),
        "ensembl_gene_id": _ensembl_gene(hit),
        "matched_by": matched_by,
        "was_normalized": symbol != q,
        "source": "MyGene.info",
    }
