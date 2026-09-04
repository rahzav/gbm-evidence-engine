from pathlib import Path

# Patch Europe PMC connector so each paper carries a stable click-through URL.
p = Path('gbm_evidence_engine/connectors/europepmc.py')
t = p.read_text()
if 'def _publication_url' not in t:
    marker = 'def top_papers(gene: str, page_size: int = 8) -> list[dict]:\n'
    helper = '''def _publication_url(row: dict) -> str:\n    doi = str(row.get("doi") or "").strip()\n    if doi:\n        return f"https://doi.org/{doi}"\n    pmcid = str(row.get("pmcid") or "").strip()\n    if pmcid:\n        return f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"\n    pmid = str(row.get("pmid") or "").strip()\n    if pmid:\n        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"\n    title = str(row.get("title") or "").strip()\n    return "https://europepmc.org/search?query=" + urllib.parse.quote(title)\n\n\n'''
    if marker not in t:
        raise SystemExit('Europe PMC top_papers marker not found')
    t = t.replace(marker, helper + marker, 1)
    target = '            "abstract": r.get("abstractText"),\n'
    repl = '            "abstract": r.get("abstractText"),\n            "url": _publication_url(r),\n'
    if target not in t:
        raise SystemExit('Europe PMC paper mapping marker not found')
    t = t.replace(target, repl, 1)
p.write_text(t)

# Patch deployed V5 UI presentation only; scientific data remain unchanged.
p = Path('streamlit_app_v5.py')
t = p.read_text()
old = '''                        if record.statistic_name and record.statistic_value is not None:\n                            stats.append(f"{record.statistic_name}={record.statistic_value:.4g}")\n                        if record.p_value is not None:\n                            stats.append(f"p={record.p_value:.3g}")\n                        if record.provenance.sample_size:\n                            stats.append(f"n={record.provenance.sample_size}")\n                        if stats:\n                            st.caption(" | ".join(stats))\n                        st.caption(\n                            f"Source: {record.provenance.source_dataset} | Confidence: {record.confidence.value} | Access: {record.provenance.access_tier.value}"\n                        )\n                        for caveat in record.caveats:\n                            st.caption(f"Caveat: {caveat}")\n'''
new = '''                        if record.statistic_name and record.statistic_value is not None:\n                            statistic_label = record.statistic_name.replace("_", " ").strip().title()\n                            stats.append(f"{statistic_label}: {record.statistic_value:.4g}")\n                        if record.p_value is not None:\n                            stats.append(f"p = {record.p_value:.3g}")\n                        if record.provenance.sample_size:\n                            stats.append(f"n = {record.provenance.sample_size}")\n                        if stats:\n                            st.caption(" | ".join(stats))\n                        st.caption(\n                            f"Source: {record.provenance.source_dataset} | Confidence: {record.confidence.value.title()}"\n                        )\n'''
if old not in t:
    raise SystemExit('Evidence-record UI block not found')
t = t.replace(old, new, 1)

old = '''                    for paper in papers:\n                        paper_title = paper.get("title") or "Untitled"\n                        metadata = " | ".join(\n                            str(x) for x in [\n                                paper.get("journal"),\n                                paper.get("year"),\n                                paper.get("pmid") and f"PMID {paper.get('pmid')}",\n                            ] if x\n                        )\n                        st.markdown(f"**{paper_title}**")\n                        if metadata:\n                            st.caption(metadata)\n'''
new = '''                    for paper in papers:\n                        paper_title = str(paper.get("title") or "Untitled")\n                        safe_title = paper_title.replace("\\\\", "\\\\\\\\").replace("[", "\\\\[").replace("]", "\\\\]")\n                        if paper.get("url"):\n                            st.markdown(f"**[{safe_title}]({paper['url']})**")\n                        else:\n                            st.markdown(f"**{paper_title}**")\n                        if paper.get("authors"):\n                            st.caption(paper.get("authors"))\n                        metadata = " | ".join(\n                            str(x) for x in [\n                                paper.get("journal"),\n                                paper.get("year"),\n                                paper.get("pmid") and f"PMID {paper.get('pmid')}",\n                                paper.get("doi") and f"DOI {paper.get('doi')}",\n                            ] if x\n                        )\n                        if metadata:\n                            st.caption(metadata)\n'''
if old not in t:
    raise SystemExit('Literature UI block not found')
t = t.replace(old, new, 1)
p.write_text(t)
