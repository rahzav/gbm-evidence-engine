"""Live Europe PMC literature connector."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import urllib.parse

from .base import SOURCE_REGISTRY, http_get_json

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


def publication_url(record: dict) -> str | None:
    """Return a stable click-through URL for a Europe PMC result.

    Prefer DOI when present, then PubMed/PMC identifiers, then Europe PMC's own
    source/id route. A title-search fallback ensures a displayed publication is
    still navigable even when identifier metadata is incomplete.
    """
    doi = str(record.get("doi") or "").strip()
    if doi:
        return f"https://doi.org/{urllib.parse.quote(doi, safe='/:;()[]') }"
    pmid = str(record.get("pmid") or "").strip()
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{urllib.parse.quote(pmid)}/"
    pmcid = str(record.get("pmcid") or "").strip()
    if pmcid:
        return f"https://pmc.ncbi.nlm.nih.gov/articles/{urllib.parse.quote(pmcid)}/"
    source = str(record.get("source") or "").strip()
    ext_id = str(record.get("id") or record.get("extId") or "").strip()
    if source and ext_id:
        return f"https://europepmc.org/article/{urllib.parse.quote(source)}/{urllib.parse.quote(ext_id)}"
    title = str(record.get("title") or "").strip()
    if title:
        return "https://europepmc.org/search?query=" + urllib.parse.quote(f'TITLE:"{title}"')
    return None


def top_papers(gene: str, page_size: int = 8) -> list[dict]:
    result = search(f'"{gene}" AND (glioblastoma OR GBM)', page_size=page_size, result_type="core") or {}
    rows = result.get("resultList", {}).get("result", [])
    papers = []
    for r in rows:
        paper = {
            "title": r.get("title"),
            "authors": r.get("authorString"),
            "journal": r.get("journalTitle"),
            "year": r.get("pubYear"),
            "pmid": r.get("pmid"),
            "pmcid": r.get("pmcid"),
            "doi": r.get("doi"),
            "source": r.get("source"),
            "id": r.get("id") or r.get("extId"),
            "cited_by": r.get("citedByCount"),
            "abstract": r.get("abstractText"),
        }
        paper["url"] = publication_url(paper)
        papers.append(paper)
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

    # Two workers keeps latency reasonable without adding unnecessary request
    # pressure to the rest of a multi-source profile build.
    with ThreadPoolExecutor(max_workers=2) as ex:
        return dict(ex.map(one, CONTEXT_QUERIES.items()))


def summarize_gene_literature(gene: str) -> dict:
    base = search(f'"{gene}" AND (glioblastoma OR GBM)', page_size=1, result_type="lite")
    return {
        "ok": base is not None,
        "hit_count": base.get("hitCount") if base else None,
        "contexts": context_counts(gene),
        "top_papers": top_papers(gene),
    }
