"""Live Europe PMC literature connector."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import re
import urllib.parse

from .base import SOURCE_REGISTRY, http_get_json

BASE = SOURCE_REGISTRY["europepmc"].base_url


def search(
    query: str,
    page_size: int = 10,
    result_type: str = "core",
    cursor_mark: str | None = None,
) -> Optional[dict]:
    params = {
        "query": query,
        "resultType": result_type,
        "pageSize": page_size,
        "format": "json",
    }
    if cursor_mark:
        params["cursorMark"] = cursor_mark
    return http_get_json(f"{BASE}/search?{urllib.parse.urlencode(params)}")


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


def _authors_from_record(record: dict) -> str | None:
    author_string = str(record.get("authorString") or "").strip()
    if author_string:
        return author_string
    authors = (record.get("authorList") or {}).get("author") or []
    names = []
    for author in authors:
        name = str(author.get("fullName") or "").strip()
        if not name:
            first = str(author.get("firstName") or "").strip()
            last = str(author.get("lastName") or "").strip()
            name = " ".join(x for x in (first, last) if x)
        if name:
            names.append(name)
    return ", ".join(names) or None


def normalize_publication(record: dict) -> dict:
    journal_info = record.get("journalInfo") or {}
    journal = record.get("journalTitle") or (journal_info.get("journal") or {}).get("title")
    publication_types = (record.get("pubTypeList") or {}).get("pubType") or []
    if isinstance(publication_types, str):
        publication_types = [publication_types]
    paper = {
        "title": record.get("title"),
        "authors": _authors_from_record(record),
        "journal": journal,
        "year": record.get("pubYear"),
        "pmid": record.get("pmid"),
        "pmcid": record.get("pmcid"),
        "doi": record.get("doi"),
        "source": record.get("source"),
        "id": record.get("id") or record.get("extId"),
        "cited_by": record.get("citedByCount"),
        "abstract": record.get("abstractText"),
        "publication_types": publication_types,
    }
    paper["url"] = publication_url(paper)
    return paper


def top_papers(gene: str, page_size: int = 8) -> list[dict]:
    # Preserve the established scoring/profile query. The interactive browser
    # below uses a stricter title/abstract relevance query without changing the
    # frozen V7 literature score.
    result = search(f'"{gene}" AND (glioblastoma OR GBM)', page_size=page_size, result_type="core") or {}
    return [normalize_publication(row) for row in result.get("resultList", {}).get("result", [])]


CONTEXT_QUERIES = {
    "recurrent": '(recurrent OR recurrence)',
    "treatment_resistance": '(resistance OR resistant OR refractory)',
    "IDH": 'IDH',
    "MGMT": 'MGMT',
    "single_cell": '("single-cell" OR "single cell" OR scRNA)',
    "spatial": '(spatial OR "Ivy GAP" OR "anatomic niche")',
    "blood_brain_barrier": '("blood-brain barrier" OR BBB)',
}


CONTEXT_LABELS = {
    "recurrent": "Recurrent disease",
    "treatment_resistance": "Treatment resistance",
    "IDH": "IDH",
    "MGMT": "MGMT",
    "single_cell": "Single-cell",
    "spatial": "Spatial biology",
    "blood_brain_barrier": "Blood-brain barrier",
}


BROWSER_CONTEXT_TERMS = {
    "recurrent": ["recurrent", "recurrence"],
    "treatment_resistance": ["resistance", "resistant", "refractory"],
    "IDH": ["IDH"],
    "MGMT": ["MGMT"],
    "single_cell": ["single-cell", "single cell", "scRNA"],
    "spatial": ["spatial", "Ivy GAP", "anatomic niche"],
    "blood_brain_barrier": ["blood-brain barrier", "BBB"],
}


def _fielded_term(term: str) -> str:
    escaped = str(term).replace('"', "").strip()
    return f'(TITLE:"{escaped}" OR ABSTRACT:"{escaped}")'


def _safe_user_tokens(terms: str | None) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9_.+/-]*", str(terms or ""))[:12]


def build_publication_query(gene: str, context_key: str | None = None, terms: str | None = None) -> str:
    """Build the interactive-browser query without changing score semantics.

    Browser results are constrained to title/abstract matches so a keyword that
    merely appears elsewhere in a long PMC full-text issue does not make an
    unrelated conference abstract look relevant.
    """
    gene_term = _fielded_term(gene.strip())
    disease_term = "(" + " OR ".join([
        'TITLE:"glioblastoma"',
        'ABSTRACT:"glioblastoma"',
        'TITLE:"GBM"',
        'ABSTRACT:"GBM"',
    ]) + ")"
    query = f"{gene_term} AND {disease_term}"

    context_terms = BROWSER_CONTEXT_TERMS.get(context_key or "", [])
    if context_terms:
        query += " AND (" + " OR ".join(_fielded_term(term) for term in context_terms) + ")"

    user_tokens = _safe_user_tokens(terms)
    if user_tokens:
        query += " AND " + " AND ".join(_fielded_term(token) for token in user_tokens)
    return query


def search_publications(
    gene: str,
    context_key: str | None = None,
    terms: str | None = None,
    *,
    page_size: int = 25,
    cursor_mark: str | None = None,
) -> dict:
    query = build_publication_query(gene, context_key=context_key, terms=terms)
    result = search(query, page_size=max(1, min(int(page_size), 100)), result_type="core", cursor_mark=cursor_mark)
    if result is None:
        return {
            "ok": False,
            "query": query,
            "hit_count": None,
            "papers": [],
            "next_cursor": None,
            "error": "Europe PMC is temporarily unavailable.",
        }
    rows = result.get("resultList", {}).get("result", [])
    return {
        "ok": True,
        "query": query,
        "hit_count": result.get("hitCount"),
        "papers": [normalize_publication(row) for row in rows],
        "next_cursor": result.get("nextCursorMark"),
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
