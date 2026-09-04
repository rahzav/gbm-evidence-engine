"""STRING connector for high-confidence protein interaction and pathway context."""
from __future__ import annotations

import urllib.parse
from typing import Any, Iterable

from .base import http_get_json

BASE = "https://string-db.org/api/json"
SPECIES = 9606


def _partner_from_row(row: dict[str, Any], gene: str) -> str | None:
    a = str(row.get("preferredName_A") or row.get("preferredNameA") or "")
    b = str(row.get("preferredName_B") or row.get("preferredNameB") or "")
    if a.upper() == gene.upper() and b:
        return b
    if b.upper() == gene.upper() and a:
        return a
    return b or a or None


def _clean_gene_set(genes: Iterable[str], limit: int = 200) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in genes:
        gene = str(raw).strip().upper()
        if not gene or gene in seen:
            continue
        seen.add(gene)
        out.append(gene)
        if len(out) >= limit:
            break
    return out


def enrich_gene_set(genes: Iterable[str], limit: int = 20) -> dict:
    """Run functional enrichment for a researcher-provided gene set.

    This is context only. Enrichment never changes Target Priority Scores.
    """
    cleaned = _clean_gene_set(genes)
    if len(cleaned) < 3:
        return {"ok": False, "error": "At least 3 unique genes are required for STRING enrichment."}
    encoded_ids = "%0d".join(urllib.parse.quote(x) for x in cleaned)
    url = f"{BASE}/enrichment?identifiers={encoded_ids}&species={SPECIES}"
    data = http_get_json(url, timeout=30)
    if not isinstance(data, list):
        return {"ok": False, "error": "STRING enrichment data unavailable."}
    preferred = {"Process", "KEGG", "Reactome", "WikiPathways"}
    rows = [r for r in data if isinstance(r, dict)]
    selected = [r for r in rows if str(r.get("category") or "") in preferred] or rows
    results = []
    for row in selected[: max(1, min(int(limit), 50))]:
        results.append({
            "category": row.get("category"),
            "term": row.get("term"),
            "description": row.get("description"),
            "fdr": row.get("fdr"),
            "number_of_genes": row.get("number_of_genes"),
            "genes": row.get("preferredNames") or row.get("inputGenes"),
        })
    return {
        "ok": bool(results),
        "n_input_genes": len(cleaned),
        "results": results,
        "source": "STRING functional enrichment",
        "interpretation": "Gene-set enrichment describes over-represented functional annotations; it is not evidence that every member drives GBM biology.",
    }


def get_network_context(gene: str, limit: int = 12, required_score: int = 700) -> dict:
    gene = gene.strip().upper()
    params = urllib.parse.urlencode({
        "identifiers": gene,
        "species": SPECIES,
        "limit": max(1, min(int(limit), 25)),
        "required_score": max(0, min(int(required_score), 1000)),
    })
    data = http_get_json(f"{BASE}/interaction_partners?{params}", timeout=20)
    if not isinstance(data, list):
        return {"ok": False, "gene": gene, "error": "STRING interaction data unavailable."}

    partners = []
    seen = set()
    for row in data:
        if not isinstance(row, dict):
            continue
        partner = _partner_from_row(row, gene)
        if not partner or partner.upper() in seen or partner.upper() == gene:
            continue
        seen.add(partner.upper())
        partners.append({
            "gene": partner,
            "score": row.get("score"),
            "experimental": row.get("escore"),
            "database": row.get("dscore"),
            "text_mining": row.get("tscore"),
        })

    enrichment = []
    identifiers = [gene] + [p["gene"] for p in partners[:8]]
    if len(identifiers) >= 2:
        enriched = enrich_gene_set(identifiers, limit=12)
        if enriched.get("ok"):
            enrichment = enriched["results"]

    return {
        "ok": True,
        "gene": gene,
        "required_score": required_score,
        "partners": partners,
        "enrichment": enrichment,
        "source_url": f"https://string-db.org/cgi/network?identifier={urllib.parse.quote(gene)}&species={SPECIES}",
        "interpretation": "STRING associations provide functional network context. Network connectivity and enrichment are hypothesis-generation signals and are not used as direct evidence that the gene is a GBM dependency or therapeutic target.",
    }
