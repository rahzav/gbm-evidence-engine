"""Apply publication browsing/citation and tab-walkthrough updates."""
from pathlib import Path


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    Path(path).write_text(text, encoding="utf-8")


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"Expected block not found: {label}")
    return text.replace(old, new, 1)


def replace_between(text, start, end, replacement, label):
    i = text.find(start)
    if i < 0:
        raise SystemExit(f"Start marker not found: {label}")
    j = text.find(end, i)
    if j < 0:
        raise SystemExit(f"End marker not found: {label}")
    return text[:i] + replacement + text[j:]


# --- Europe PMC connector -------------------------------------------------
p = "gbm_evidence_engine/connectors/europepmc.py"
text = read(p)
text = replace_once(text, "from typing import Optional\nimport urllib.parse\n", "from typing import Optional\nimport re\nimport urllib.parse\n", "europepmc imports")
text = replace_between(
    text,
    "def search(query: str, page_size: int = 10, result_type: str = \"core\") -> Optional[dict]:\n",
    "\n\ndef co_mention_count",
    '''def search(\n    query: str,\n    page_size: int = 10,\n    result_type: str = "core",\n    cursor_mark: str | None = None,\n) -> Optional[dict]:\n    params = {\n        "query": query,\n        "resultType": result_type,\n        "pageSize": page_size,\n        "format": "json",\n    }\n    if cursor_mark:\n        params["cursorMark"] = cursor_mark\n    return http_get_json(f"{BASE}/search?{urllib.parse.urlencode(params)}")\n''',
    "europepmc search",
)
text = replace_between(
    text,
    "def top_papers(gene: str, page_size: int = 8) -> list[dict]:\n",
    "\n\nCONTEXT_QUERIES =",
    '''def _authors_from_record(record: dict) -> str | None:\n    author_string = str(record.get("authorString") or "").strip()\n    if author_string:\n        return author_string\n    authors = (record.get("authorList") or {}).get("author") or []\n    names = []\n    for author in authors:\n        name = str(author.get("fullName") or "").strip()\n        if not name:\n            first = str(author.get("firstName") or "").strip()\n            last = str(author.get("lastName") or "").strip()\n            name = " ".join(x for x in (first, last) if x)\n        if name:\n            names.append(name)\n    return ", ".join(names) or None\n\n\ndef normalize_publication(record: dict) -> dict:\n    journal_info = record.get("journalInfo") or {}\n    journal = record.get("journalTitle") or (journal_info.get("journal") or {}).get("title")\n    publication_types = (record.get("pubTypeList") or {}).get("pubType") or []\n    if isinstance(publication_types, str):\n        publication_types = [publication_types]\n    paper = {\n        "title": record.get("title"),\n        "authors": _authors_from_record(record),\n        "journal": journal,\n        "year": record.get("pubYear"),\n        "pmid": record.get("pmid"),\n        "pmcid": record.get("pmcid"),\n        "doi": record.get("doi"),\n        "source": record.get("source"),\n        "id": record.get("id") or record.get("extId"),\n        "cited_by": record.get("citedByCount"),\n        "abstract": record.get("abstractText"),\n        "publication_types": publication_types,\n    }\n    paper["url"] = publication_url(paper)\n    return paper\n\n\ndef top_papers(gene: str, page_size: int = 8) -> list[dict]:\n    result = search(f'"{gene}" AND (glioblastoma OR GBM)', page_size=page_size, result_type="core") or {}\n    return [normalize_publication(row) for row in result.get("resultList", {}).get("result", [])]\n''',
    "top_papers normalization",
)
insert_marker = "\n\ndef context_counts(gene: str) -> dict[str, Optional[int]]:\n"
new_search_helpers = '''\n\nCONTEXT_LABELS = {\n    "recurrent": "Recurrent disease",\n    "treatment_resistance": "Treatment resistance",\n    "IDH": "IDH",\n    "MGMT": "MGMT",\n    "single_cell": "Single-cell",\n    "spatial": "Spatial biology",\n    "blood_brain_barrier": "Blood-brain barrier",\n}\n\n\ndef _safe_user_terms(terms: str | None) -> str | None:\n    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9_.+/-]*", str(terms or ""))[:12]\n    if not tokens:\n        return None\n    return " AND ".join(f'"{token}"' for token in tokens)\n\n\ndef build_publication_query(gene: str, context_key: str | None = None, terms: str | None = None) -> str:\n    query = f'"{gene.strip()}" AND (glioblastoma OR GBM)'\n    if context_key:\n        tail = CONTEXT_QUERIES.get(context_key)\n        if tail:\n            query += f" AND {tail}"\n    safe_terms = _safe_user_terms(terms)\n    if safe_terms:\n        query += f" AND ({safe_terms})"\n    return query\n\n\ndef search_publications(\n    gene: str,\n    context_key: str | None = None,\n    terms: str | None = None,\n    *,\n    page_size: int = 25,\n    cursor_mark: str | None = None,\n) -> dict:\n    query = build_publication_query(gene, context_key=context_key, terms=terms)\n    result = search(query, page_size=max(1, min(int(page_size), 100)), result_type="core", cursor_mark=cursor_mark)\n    if result is None:\n        return {\n            "ok": False,\n            "query": query,\n            "hit_count": None,\n            "papers": [],\n            "next_cursor": None,\n            "error": "Europe PMC is temporarily unavailable.",\n        }\n    rows = result.get("resultList", {}).get("result", [])\n    return {\n        "ok": True,\n        "query": query,\n        "hit_count": result.get("hitCount"),\n        "papers": [normalize_publication(row) for row in rows],\n        "next_cursor": result.get("nextCursorMark"),\n    }\n'''
if insert_marker not in text:
    raise SystemExit("context_counts marker missing")
text = text.replace(insert_marker, new_search_helpers + insert_marker, 1)
write(p, text)


# --- Streamlit UI ---------------------------------------------------------
p = "app_ui.py"
text = read(p)
text = replace_once(
    text,
    "from ui_walkthroughs import maybe_show_initial_gene_walkthrough, render_feature_header\nfrom gbm_evidence_engine.evidence_model import EvidenceTier\n",
    "from ui_walkthroughs import (\n    maybe_show_active_walkthrough,\n    maybe_show_initial_gene_walkthrough,\n    on_workflow_tab_change,\n    render_feature_header,\n)\nfrom gbm_evidence_engine.evidence_model import EvidenceTier\nfrom gbm_evidence_engine.connectors import europepmc\n",
    "app imports",
)
cache_marker = "\n\ndef pct(value):\n"
cache_block = '''\n\n@st.cache_data(ttl=1800, max_entries=48, show_spinner=False)\ndef cached_publication_search(\n    gene: str,\n    context_key: str | None,\n    terms: str,\n    cursor_mark: str | None,\n):\n    return europepmc.search_publications(\n        gene,\n        context_key=context_key,\n        terms=terms,\n        page_size=25,\n        cursor_mark=cursor_mark,\n    )\n'''
if cache_marker not in text:
    raise SystemExit("cache marker missing")
text = text.replace(cache_marker, cache_block + cache_marker, 1)

new_render_literature = '''def _publication_metadata(paper: dict) -> str:\n    parts = []\n    if paper.get("journal"):\n        parts.append(str(paper["journal"]))\n    if paper.get("year"):\n        parts.append(str(paper["year"]))\n    if paper.get("pmid"):\n        parts.append(f"PMID {paper['pmid']}")\n    if paper.get("pmcid"):\n        parts.append(f"PMCID {paper['pmcid']}")\n    if paper.get("doi"):\n        parts.append(f"DOI {paper['doi']}")\n    if not parts:\n        source = str(paper.get("source") or "Europe PMC")\n        identifier = paper.get("id")\n        parts.append(f"{source} {identifier}".strip())\n    return " | ".join(parts)\n\n\ndef _render_publication(paper: dict) -> None:\n    paper_title = str(paper.get("title") or "Untitled publication")\n    safe_title = paper_title.replace("\\\\", "\\\\\\\\").replace("[", "\\\\[").replace("]", "\\\\]")\n    if paper.get("url"):\n        st.markdown(f"**[{safe_title}]({paper['url']})**")\n    else:\n        st.markdown(f"**{paper_title}**")\n    authors = str(paper.get("authors") or "").strip()\n    st.caption(authors if authors else "Authors not indexed in Europe PMC.")\n    st.caption(_publication_metadata(paper))\n\n\ndef render_literature(profile, lit):\n    gene = profile.gene\n    st.metric(\n        "GBM Literature Co-Mentions",\n        lit.get("hit_count", 0) if lit.get("ok") else "N/A",\n        help=HELP["literature_count"],\n    )\n    st.caption(\n        "Browse the live Europe PMC literature index for this gene. Disease-context filters and keyword search query the underlying database rather than only the initially ranked papers."\n    )\n\n    context_keys = [key for key in europepmc.CONTEXT_QUERIES if key in profile.context_map]\n    label_to_key = {"All GBM literature": None}\n    context_options = ["All GBM literature"]\n    for key in context_keys:\n        count = profile.context_map.get(key)\n        label = europepmc.CONTEXT_LABELS.get(key, key.replace("_", " ").title())\n        display = f"{label} ({count:,})" if isinstance(count, int) else label\n        context_options.append(display)\n        label_to_key[display] = key\n\n    selected_label = st.pills(\n        "Disease context",\n        context_options,\n        default="All GBM literature",\n        selection_mode="single",\n        key=f"literature_context_{gene}",\n    ) or "All GBM literature"\n    context_key = label_to_key.get(selected_label)\n\n    applied_key = f"literature_applied_terms_{gene}"\n    with st.form(f"literature_search_form_{gene}", clear_on_submit=False):\n        search_text = st.text_input(\n            "Search publications",\n            value=st.session_state.get(applied_key, ""),\n            placeholder="e.g. osimertinib, CAR T, resistance, extracellular vesicles",\n            help="Searches within this gene's GBM literature in Europe PMC.",\n        )\n        search_col, clear_col = st.columns([1, 1])\n        with search_col:\n            search_submitted = st.form_submit_button("Search", type="primary", width="stretch")\n        with clear_col:\n            clear_submitted = st.form_submit_button("Clear search", width="stretch")\n    if search_submitted:\n        st.session_state[applied_key] = search_text.strip()\n    elif clear_submitted:\n        st.session_state[applied_key] = ""\n    applied_terms = st.session_state.get(applied_key, "")\n\n    signature = (gene, context_key or "", applied_terms)\n    sig_key = f"literature_signature_{gene}"\n    papers_key = f"literature_papers_{gene}"\n    cursor_key = f"literature_cursor_{gene}"\n    hits_key = f"literature_hits_{gene}"\n    error_key = f"literature_error_{gene}"\n\n    if st.session_state.get(sig_key) != signature:\n        result = cached_publication_search(gene, context_key, applied_terms, None)\n        st.session_state[sig_key] = signature\n        st.session_state[papers_key] = result.get("papers") or []\n        st.session_state[cursor_key] = result.get("next_cursor")\n        st.session_state[hits_key] = result.get("hit_count")\n        st.session_state[error_key] = result.get("error")\n\n    papers = st.session_state.get(papers_key, [])\n    hit_count = st.session_state.get(hits_key)\n    error = st.session_state.get(error_key)\n    if error:\n        st.info(error)\n        return\n\n    query_description = selected_label\n    if applied_terms:\n        query_description += f' · keywords: "{applied_terms}"'\n    if isinstance(hit_count, int):\n        st.markdown(f"#### Relevant Publications · {hit_count:,} matches")\n    else:\n        st.markdown("#### Relevant Publications")\n    st.caption(query_description)\n\n    if not papers:\n        st.info("No matching publications were returned for this filter/search.")\n        return\n\n    for index, paper in enumerate(papers):\n        _render_publication(paper)\n        if index < len(papers) - 1:\n            st.divider()\n\n    next_cursor = st.session_state.get(cursor_key)\n    if next_cursor and (not isinstance(hit_count, int) or len(papers) < hit_count):\n        remaining = None if not isinstance(hit_count, int) else max(0, hit_count - len(papers))\n        button_label = "Load 25 more publications" if remaining is None else f"Load 25 more · {remaining:,} remaining"\n        if st.button(button_label, key=f"literature_load_more_{gene}", width="stretch"):\n            more = cached_publication_search(gene, context_key, applied_terms, next_cursor)\n            if more.get("ok"):\n                existing = {\n                    str(p.get("doi") or p.get("pmid") or p.get("pmcid") or p.get("id") or p.get("title"))\n                    for p in papers\n                }\n                additions = []\n                for paper in more.get("papers") or []:\n                    identity = str(paper.get("doi") or paper.get("pmid") or paper.get("pmcid") or paper.get("id") or paper.get("title"))\n                    if identity not in existing:\n                        additions.append(paper)\n                        existing.add(identity)\n                st.session_state[papers_key] = papers + additions\n                st.session_state[cursor_key] = more.get("next_cursor")\n                st.rerun()\n            else:\n                st.info(more.get("error", "Europe PMC is temporarily unavailable."))\n'''
text = replace_between(text, "def render_literature(profile, lit):\n", "\n\ndef render_translation", new_render_literature + "\n\n", "render_literature")
old_tabs = '''analysis_tab, pair_tab, researcher_tab, batch_tab, methods_tab = st.tabs([\n    "Gene Analysis",\n    "Target Pair Analysis",\n    "Researcher Data",\n    "Gene Set Comparison",\n    "Methods & Data Sources",\n])\n'''
new_tabs = '''analysis_tab, pair_tab, researcher_tab, batch_tab, methods_tab = st.tabs(\n    [\n        "Gene Analysis",\n        "Target Pair Analysis",\n        "Researcher Data",\n        "Gene Set Comparison",\n        "Methods & Data Sources",\n    ],\n    key="research_workflow_tabs",\n    on_change=on_workflow_tab_change,\n)\nmaybe_show_active_walkthrough()\n'''
text = replace_once(text, old_tabs, new_tabs, "outer tabs")
write(p, text)


# --- Walkthrough auto-launch on tab selection ----------------------------
p = "ui_walkthroughs.py"
text = read(p)
marker = "\ndef render_feature_header(title: str, feature: str, caption: str | None = None) -> None:\n"
helpers = '''\nWORKFLOW_TAB_TO_FEATURE = {\n    "Gene Analysis": "gene",\n    "Target Pair Analysis": "pair",\n    "Researcher Data": "researcher",\n    "Gene Set Comparison": "comparison",\n}\n\n\ndef on_workflow_tab_change() -> None:\n    """Queue the selected workflow's walkthrough whenever its tab is opened."""\n    label = st.session_state.get("research_workflow_tabs")\n    feature = WORKFLOW_TAB_TO_FEATURE.get(label)\n    if feature:\n        st.session_state["pending_feature_walkthrough"] = feature\n\n\ndef maybe_show_active_walkthrough() -> None:\n    """Show a walkthrough queued by a top-level workflow-tab selection."""\n    feature = st.session_state.pop("pending_feature_walkthrough", None)\n    if feature:\n        _launch(feature)\n\n'''
if marker not in text:
    raise SystemExit("walkthrough header marker missing")
text = text.replace(marker, helpers + marker, 1)
text = replace_once(
    text,
    "Publication volume, target-directed candidates, GBM trials and measured BBB records describe different pieces of translational maturity. None alone establishes efficacy.",
    "Use the Literature tab's disease-context filters and keyword search to browse matching Europe PMC records beyond the initial results. Publication volume, target-directed candidates, GBM trials and measured BBB records describe different pieces of translational maturity; none alone establishes efficacy.",
    "literature walkthrough note",
)
write(p, text)


# --- Deterministic tests --------------------------------------------------
test = '''"""Deterministic tests for Europe PMC publication browsing and citation normalization."""\nfrom unittest.mock import patch\n\nfrom gbm_evidence_engine.connectors import europepmc\n\n\ndef test_normalize_publication_fills_author_and_journal_fallbacks():\n    record = {\n        "title": "Conference abstract",\n        "pubYear": "2024",\n        "pmcid": "PMC123",\n        "journalInfo": {"journal": {"title": "Neuro-Oncology"}},\n        "authorList": {"author": [{"firstName": "Ada", "lastName": "Lovelace"}]},\n        "pubTypeList": {"pubType": ["conference paper"]},\n    }\n    paper = europepmc.normalize_publication(record)\n    assert paper["authors"] == "Ada Lovelace"\n    assert paper["journal"] == "Neuro-Oncology"\n    assert paper["year"] == "2024"\n    assert paper["pmcid"] == "PMC123"\n    assert "PMC123" in paper["url"]\n\n\ndef test_search_query_scopes_gene_gbm_context_and_user_terms():\n    query = europepmc.build_publication_query("EGFR", "recurrent", "osimertinib resistance")\n    assert '"EGFR"' in query\n    assert "glioblastoma OR GBM" in query\n    assert "recurrent OR recurrence" in query\n    assert '"osimertinib" AND "resistance"' in query\n\n\ndef test_search_publications_returns_cursor_and_normalized_records():\n    payload = {\n        "hitCount": 81,\n        "nextCursorMark": "NEXT",\n        "resultList": {\n            "result": [{\n                "title": "Example",\n                "authorString": "A Author, B Author",\n                "journalTitle": "Cancer Research",\n                "pubYear": "2026",\n                "pmid": "12345",\n            }]\n        },\n    }\n    with patch.object(europepmc, "search", return_value=payload) as mocked:\n        result = europepmc.search_publications("EGFR", "MGMT", "therapy", cursor_mark="CURSOR")\n    assert result["ok"]\n    assert result["hit_count"] == 81\n    assert result["next_cursor"] == "NEXT"\n    assert result["papers"][0]["authors"] == "A Author, B Author"\n    assert "pubmed.ncbi.nlm.nih.gov/12345" in result["papers"][0]["url"]\n    assert mocked.call_args.kwargs["cursor_mark"] == "CURSOR"\n\n\nif __name__ == "__main__":\n    test_normalize_publication_fills_author_and_journal_fallbacks()\n    test_search_query_scopes_gene_gbm_context_and_user_terms()\n    test_search_publications_returns_cursor_and_normalized_records()\n    print("ALL EUROPE PMC PUBLICATION TESTS PASSED")\n'''
write("tests/test_europepmc_publications.py", test)


# --- CI -------------------------------------------------------------------
p = ".github/workflows/ci.yml"
text = read(p)
text = replace_once(
    text,
    "          PYTHONPATH=. python tests/test_research_intelligence_v7.py\n",
    "          PYTHONPATH=. python tests/test_research_intelligence_v7.py\n          PYTHONPATH=. python tests/test_europepmc_publications.py\n",
    "publication test in CI",
)
text = replace_once(
    text,
    "          assert 'Real-time synthesis of live and curated gene-level evidence' in ui\n",
    "          assert 'Real-time synthesis of live and curated gene-level evidence' in ui\n          assert 'Search publications' in ui\n          assert 'Load 25 more' in ui\n          assert 'on_change=on_workflow_tab_change' in ui\n",
    "CI UI assertions",
)
write(p, text)

print("PUBLICATION_BROWSER_PATCH_APPLIED")
