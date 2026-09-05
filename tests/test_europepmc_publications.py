"""Deterministic tests for Europe PMC publication browsing and citation normalization."""
from unittest.mock import patch

from gbm_evidence_engine.connectors import europepmc


def test_normalize_publication_fills_author_and_journal_fallbacks():
    record = {
        "title": "Conference abstract",
        "pubYear": "2024",
        "pmcid": "PMC123",
        "journalInfo": {"journal": {"title": "Neuro-Oncology"}},
        "authorList": {"author": [{"firstName": "Ada", "lastName": "Lovelace"}]},
        "pubTypeList": {"pubType": ["conference paper"]},
    }
    paper = europepmc.normalize_publication(record)
    assert paper["authors"] == "Ada Lovelace"
    assert paper["journal"] == "Neuro-Oncology"
    assert paper["year"] == "2024"
    assert paper["pmcid"] == "PMC123"
    assert "PMC123" in paper["url"]


def test_search_query_scopes_gene_gbm_context_and_user_terms_to_title_or_abstract():
    query = europepmc.build_publication_query("EGFR", "recurrent", "osimertinib resistance")
    assert 'TITLE:"EGFR"' in query and 'ABSTRACT:"EGFR"' in query
    assert 'TITLE:"glioblastoma"' in query and 'ABSTRACT:"GBM"' in query
    assert 'TITLE:"recurrent"' in query and 'ABSTRACT:"recurrence"' in query
    assert 'TITLE:"osimertinib"' in query and 'ABSTRACT:"osimertinib"' in query
    assert 'TITLE:"resistance"' in query and 'ABSTRACT:"resistance"' in query


def test_search_publications_returns_cursor_and_normalized_records():
    payload = {
        "hitCount": 81,
        "nextCursorMark": "NEXT",
        "resultList": {
            "result": [{
                "title": "Example",
                "authorString": "A Author, B Author",
                "journalTitle": "Cancer Research",
                "pubYear": "2026",
                "pmid": "12345",
            }]
        },
    }
    with patch.object(europepmc, "search", return_value=payload) as mocked:
        result = europepmc.search_publications("EGFR", "MGMT", "therapy", cursor_mark="CURSOR")
    assert result["ok"]
    assert result["hit_count"] == 81
    assert result["next_cursor"] == "NEXT"
    assert result["papers"][0]["authors"] == "A Author, B Author"
    assert "pubmed.ncbi.nlm.nih.gov/12345" in result["papers"][0]["url"]
    assert mocked.call_args.kwargs["cursor_mark"] == "CURSOR"


if __name__ == "__main__":
    test_normalize_publication_fills_author_and_journal_fallbacks()
    test_search_query_scopes_gene_gbm_context_and_user_terms_to_title_or_abstract()
    test_search_publications_returns_cursor_and_normalized_records()
    print("ALL EUROPE PMC PUBLICATION TESTS PASSED")
