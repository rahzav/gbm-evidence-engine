"""Live Europe PMC literature connector."""
from __future__ import annotations
from typing import Optional
from .base import http_get_json, SOURCE_REGISTRY
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

BASE = SOURCE_REGISTRY["europepmc"].base_url


def search(query: str, page_size: int = 10, result_type: str = "core") -> Optional[dict]:
    params = urllib.parse.urlencode({
        "query": query,
        "resultType": result_type,
        "pageSize": page_size,
        "format": "json",
    })
    return http_get_json(f"{BASE}/search?{params}")


def co_mention_count(gene: str, context: str = "glioblastoma") -> Optional[int]:
    result = search(f'"{gene}" AND "{context}"', page_size=1, result_type="lite")
    return result.get("hitCount") if result else None


def _publication_url(row: dict) -> str:
    doi = str(row.get("doi") or "").strip()
    if doi:
        return f"https://doi.org/{doi}"
    pmcid = str(row.get("pmcid") or "").strip()
    if pmcid:
        return f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
    pmid = str(row.get("pmid") or "").strip()
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    title = str(row.get("title") or "").strip()
    return "https://europepmc.org/search?query=" + urllib.parse.quote(title)


def top_papers(gene: str, page_size: int = 8) -> list[dict]:
    result = search(f'"{gene}" AND (glioblastoma OR GBM)', page_size=page_size, result_type="core") or {}
    rows = result.get("resultList", {}).get("result", [])
    papers = []
    for r in rows:
        papers.append({
            "title": r.get("title"),
            "authors": r.get("authorString"),
            "journal": r.get("journalTitle"),
            "year": r.get("pubYear"),
            "pmid": r.get("pmid"),
            "pmcid": r.get("pmcid"),
            "doi": r.get("doi"),
            "cited_by": r.get("citedByCount"),
            "abstract": r.get("abstractText"),
            "url": _publication_url(r),
        })
    return papers


CONTEXT_QUERIES = {
    "recurrent": '(recurrent OR recurrence)',
    "treatment_resistance": '(resistance OR resistant OR refractory)',
    "IDH": 'IDH',
    "MGMT": 'MGMT',
    "single_cell": '("single-cell" OR "single cell" OR scRNA)',
    "spatial": '(spatial OR "Ivy GAP" OR "anatomic niche")',
    "blood_brain_barrier": '("blood-brain barrier" OR BBB)',
}


def context_counts(gene: str) -> dict[str, Optional[int]]:
    def one(item):
        label, tail = item
        data = search(f'"{gene}" AND (glioblastoma OR GBM) AND {tail}', page_size=1, result_type="lite")
        return label, (data.get("hitCount") if data else None)
    with ThreadPoolExecutor(max_workers=4) as ex:
        return dict(ex.map(one, CONTEXT_QUERIES.items()))


def summarize_gene_literature(gene: str) -> dict:
    base = search(f'"{gene}" AND (glioblastoma OR GBM)', page_size=1, result_type="lite")
    return {
        "ok": base is not None,
        "hit_count": base.get("hitCount") if base else None,
        "contexts": context_counts(gene),
        "top_papers": top_papers(gene),
    }
