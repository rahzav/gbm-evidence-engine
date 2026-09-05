from pathlib import Path
import re


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Expected {label} not found")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"Expected one {label}, found {count}")
    return updated


# ---------------------------------------------------------------------------
# Glia interface: stronger launcher, cohesive header/logo, force-open hook.
# ---------------------------------------------------------------------------
path = Path("glia_interface.py")
text = path.read_text(encoding="utf-8")

text = regex_once(
    text,
    r'''#glia-header \{.*?\.glia-memory-dot \{ width:6px; height:6px; border-radius:50%; background: var\(--st-primary-color, #ff4b4b\); \}\n''',
    '''#glia-header {
  padding: 14px 14px 11px;
  border-bottom: 1px solid color-mix(in srgb, var(--st-text-color, #111) 10%, transparent);
  background: var(--st-background-color, #fff);
}
.glia-header-row {
  display:grid;
  grid-template-columns:40px minmax(0,1fr) 30px 30px 30px;
  align-items:center;
  column-gap:7px;
}
.glia-mark {
  width:40px; height:40px; border-radius:12px;
  display:flex; align-items:center; justify-content:center;
  border:1px solid color-mix(in srgb, var(--st-primary-color, #ff4b4b) 48%, transparent);
  background:color-mix(in srgb, var(--st-primary-color, #ff4b4b) 9%, var(--st-background-color, #fff));
  color:var(--st-primary-color, #ff4b4b);
}
.glia-mark svg { width:25px; height:25px; display:block; }
.glia-title-wrap {
  min-width:0; display:flex; flex-direction:column; justify-content:center;
  padding-left:2px;
}
.glia-title { font-weight:780; font-size:1.08rem; letter-spacing:-.015em; line-height:1.08; }
.glia-context { font-size:.78rem; opacity:.60; margin-top:3px; line-height:1.15; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.glia-icon-btn {
  border:0; background:transparent; color:inherit; opacity:.62; cursor:pointer;
  width:30px; height:30px; border-radius:8px; font-size:17px;
}
.glia-icon-btn:hover { background: color-mix(in srgb, var(--st-text-color, #111) 7%, transparent); opacity:.9; }
.glia-memory-line { display:flex; align-items:center; gap:7px; margin:8px 0 0 49px; font-size:.73rem; opacity:.66; }
.glia-memory-dot { width:6px; height:6px; border-radius:50%; background: var(--st-primary-color, #ff4b4b); }
''',
    "Glia header CSS block",
)

text = regex_once(
    text,
    r'''#glia-launcher \{.*?#glia-selection-action\.glia-visible \{ display:block; \}\n''',
    '''#glia-launcher {
  position:fixed; z-index:1000001; right:20px; bottom:72px;
  border:0;
  background:var(--st-primary-color, #ff4b4b); color:#fff; border-radius:999px;
  box-shadow:0 10px 28px rgba(0,0,0,.20); padding:10px 16px 10px 11px;
  display:none; align-items:center; gap:8px; font-weight:760; cursor:pointer;
  letter-spacing:-.01em;
}
#glia-launcher:hover { filter:brightness(.96); transform:translateY(-1px); }
#glia-launcher.glia-visible { display:flex; }
.glia-launcher-mark {
  width:27px; height:27px; border-radius:9px; display:flex; align-items:center; justify-content:center;
  background:rgba(255,255,255,.18); color:#fff;
}
.glia-launcher-mark svg { width:18px; height:18px; display:block; }

#glia-selection-action {
  position:fixed; z-index:1000002; display:none;
  border:1px solid #171717;
  background:#171717; color:#fff; border-radius:8px;
  box-shadow:0 6px 20px rgba(0,0,0,.20); padding:7px 10px; font-size:.76rem;
  font-weight:740; cursor:pointer;
}
#glia-selection-action.glia-visible { display:block; }
''',
    "Glia launcher and selection CSS",
)

text = replace_once(
    text,
    '''    lastPayloadRevision: null,\n  };''',
    '''    lastPayloadRevision: null,\n    lastForceOpenNonce: null,\n  };''',
    "Glia runtime state",
)

text = replace_once(
    text,
    '''  runtime.uiLoaded = true;\n\n  if (!data.hydrated && !runtime.hydrationSent) {''',
    '''  runtime.uiLoaded = true;\n\n  const forceOpenNonce = Number(data.force_open_nonce || 0);\n  if (forceOpenNonce && forceOpenNonce !== runtime.lastForceOpenNonce) {\n    runtime.open = true;\n    runtime.lastForceOpenNonce = forceOpenNonce;\n    try { localStorage.setItem(UI_KEY, JSON.stringify({open: true})); } catch (_) {}\n  }\n\n  if (!data.hydrated && !runtime.hydrationSent) {''',
    "Glia force-open hook",
)

text = replace_once(
    text,
    '''  const shell = document.createElement("aside");\n  shell.id = "glia-shell";\n  shell.setAttribute("aria-label", "Glia research copilot");\n  document.body.appendChild(shell);\n\n  const launcher = document.createElement("button");''',
    '''  const shell = document.createElement("aside");\n  shell.id = "glia-shell";\n  shell.setAttribute("aria-label", "Glia research copilot");\n  document.body.appendChild(shell);\n\n  const gliaGlyph = `<svg viewBox="0 0 32 32" aria-hidden="true" focusable="false">\n    <g fill="none" stroke="currentColor" stroke-width="2.15" stroke-linecap="round" stroke-linejoin="round">\n      <path d="M16 10.2 10.4 6.4M16 10.2l5.8-4M16 20.9l-6 4.2M16 20.9l6.3 3.7M11.2 15.5H5.8M20.8 15.5h5.4"/>\n      <circle cx="16" cy="15.5" r="5.4" fill="currentColor" fill-opacity=".16"/>\n      <circle cx="10.1" cy="6.2" r="1.8" fill="currentColor"/>\n      <circle cx="22.1" cy="6" r="1.8" fill="currentColor"/>\n      <circle cx="9.7" cy="25.3" r="1.8" fill="currentColor"/>\n      <circle cx="22.6" cy="24.8" r="1.8" fill="currentColor"/>\n      <circle cx="5.3" cy="15.5" r="1.7" fill="currentColor"/>\n      <circle cx="26.7" cy="15.5" r="1.7" fill="currentColor"/>\n    </g>\n  </svg>`;\n\n  const launcher = document.createElement("button");''',
    "Glia glyph definition",
)

text = replace_once(
    text,
    '''  launcher.innerHTML = '<span class="glia-launcher-mark">G</span><span>Glia</span>';''',
    '''  launcher.innerHTML = `<span class="glia-launcher-mark">${gliaGlyph}</span><span>Ask Glia</span>`;''',
    "Glia launcher markup",
)

text = replace_once(
    text,
    '''          <div class="glia-mark">G</div>''',
    '''          <div class="glia-mark">${gliaGlyph}</div>''',
    "Glia header logo",
)

text = replace_once(
    text,
    '''    st.session_state.setdefault("glia_processing", False)''',
    '''    st.session_state.setdefault("glia_processing", False)\n    st.session_state.setdefault("glia_force_open_nonce", 0)''',
    "Glia force-open session state",
)

text = replace_once(
    text,
    '''            "active_workflow": active_workflow,\n            "context_summary": _context_summary(context),''',
    '''            "active_workflow": active_workflow,\n            "context_summary": _context_summary(context),\n            "force_open_nonce": int(st.session_state.get("glia_force_open_nonce") or 0),''',
    "Glia force-open component data",
)

path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Research agent: keep requests under the free-tier TPM envelope and hide raw
# provider errors.
# ---------------------------------------------------------------------------
path = Path("gbm_evidence_engine/research_agent.py")
text = path.read_text(encoding="utf-8")

text = replace_once(
    text,
    '''MAX_TOOL_ROUNDS = 4\nMAX_EVIDENCE_RECORDS = 12\nMAX_HISTORY_MESSAGES = 6''',
    '''MAX_TOOL_ROUNDS = 3\nMAX_EVIDENCE_RECORDS = 6\nMAX_HISTORY_MESSAGES = 3\nMAX_HISTORY_CHARS = 900\nMAX_MEMORY_CHARS = 1400\nMAX_TOOL_OUTPUT_CHARS = 6500\nMAX_PUBLICATION_ABSTRACT_CHARS = 700\nMAX_OUTPUT_TOKENS = 500''',
    "research-agent context constants",
)

text = replace_once(
    text,
    '''def _safe_text(value: Any, limit: int = 2200) -> str | None:\n    if value is None:\n        return None\n    text = str(value).strip()\n    return text[:limit] if text else None\n\n\ndef _record_payload''',
    '''def _safe_text(value: Any, limit: int = 2200) -> str | None:\n    if value is None:\n        return None\n    text = str(value).strip()\n    return text[:limit] if text else None\n\n\ndef _compact_for_model(value: Any, *, depth: int = 0) -> Any:\n    """Bound nested tool context before it is sent to the language model."""\n    if depth >= 4:\n        return _safe_text(value, 320)\n    if isinstance(value, dict):\n        out: dict[str, Any] = {}\n        for key, item in list(value.items())[:28]:\n            out[str(key)] = _compact_for_model(item, depth=depth + 1)\n        return out\n    if isinstance(value, (list, tuple)):\n        return [_compact_for_model(item, depth=depth + 1) for item in list(value)[:8]]\n    if isinstance(value, str):\n        return value[:900]\n    return value\n\n\ndef _bounded_json(value: Any, limit: int = MAX_TOOL_OUTPUT_CHARS) -> str:\n    compacted = _compact_for_model(value)\n    encoded = json.dumps(compacted, default=str, separators=(",", ":"))\n    if len(encoded) <= limit:\n        return encoded\n    summary = encoded[: max(400, limit - 120)]\n    return json.dumps({"truncated_for_model": True, "summary": summary}, separators=(",", ":"))\n\n\ndef _record_payload''',
    "research-agent compaction helpers",
)

text = regex_once(
    text,
    r'''def _record_payload\(record: Any, registry: dict\[str, AgentReference\]\) -> dict\[str, Any\]:.*?\n\n\ndef _publication_token''',
    '''def _record_payload(record: Any, registry: dict[str, AgentReference]) -> dict[str, Any]:\n    provenance = record.provenance\n    citation = _register_reference(\n        registry,\n        f"EV:{record.id}",\n        record.claim_text,\n        provenance.source_dataset,\n        url=provenance.citation_url,\n        kind="evidence_record",\n    )\n    caveats = record.caveats\n    if isinstance(caveats, (list, tuple)):\n        caveats = [_safe_text(item, 280) for item in caveats[:3]]\n    else:\n        caveats = _safe_text(caveats, 500)\n    return {\n        "citation": citation,\n        "claim": _safe_text(record.claim_text, 700),\n        "tier": record.tier.value,\n        "statistic_name": record.statistic_name,\n        "statistic_value": record.statistic_value,\n        "p_value": record.p_value,\n        "corrected_p_value": record.corrected_p_value,\n        "effect_size": record.effect_size,\n        "confidence_interval": record.confidence_interval,\n        "confidence": record.confidence.value,\n        "source_dataset": provenance.source_dataset,\n        "sample_size": provenance.sample_size,\n        "caveats": caveats,\n    }\n\n\ndef _publication_token''',
    "compact evidence record payload",
)

text = regex_once(
    text,
    r'''def _publication_payload\(paper: dict\[str, Any\], registry: dict\[str, AgentReference\]\) -> dict\[str, Any\]:.*?\n\n\ndef _profile_payload''',
    '''def _publication_payload(paper: dict[str, Any], registry: dict[str, AgentReference]) -> dict[str, Any]:\n    token = _publication_token(paper)\n    citation = _register_reference(\n        registry,\n        token,\n        _safe_text(paper.get("title"), 400) or "Biomedical publication",\n        "Biomedical literature",\n        url=paper.get("url"),\n        kind="publication",\n    )\n    return {\n        "citation": citation,\n        "title": _safe_text(paper.get("title"), 400),\n        "authors": _safe_text(paper.get("authors"), 320),\n        "journal": _safe_text(paper.get("journal"), 180),\n        "year": paper.get("year"),\n        "pmid": paper.get("pmid"),\n        "pmcid": paper.get("pmcid"),\n        "doi": paper.get("doi"),\n        "cited_by": paper.get("cited_by"),\n        "url": paper.get("url"),\n        "abstract": _safe_text(paper.get("abstract"), MAX_PUBLICATION_ABSTRACT_CHARS),\n        "publication_types": (paper.get("publication_types") or [])[:4],\n    }\n\n\ndef _profile_payload''',
    "compact publication payload",
)

text = replace_once(text, 'for paper in (live.get("literature", {}).get("top_papers") or [])[:10]', 'for paper in (live.get("literature", {}).get("top_papers") or [])[:4]', "profile publication cap")
text = replace_once(text, '"key_findings": live.get("key_findings") or [],', '"key_findings": (live.get("key_findings") or [])[:6],', "profile key findings cap")
text = replace_once(text, '"research_opportunities": live.get("research_opportunities") or [],', '"research_opportunities": (live.get("research_opportunities") or [])[:4],', "profile opportunities cap")
text = replace_once(text, '"mechanistic_hypotheses": live.get("mechanistic_hypotheses") or [],', '"mechanistic_hypotheses": (live.get("mechanistic_hypotheses") or [])[:3],', "profile hypotheses cap")
text = replace_once(text, '"evidence_gaps": profile.evidence_gaps,', '"evidence_gaps": list(profile.evidence_gaps)[:6],', "profile gaps cap")
text = replace_once(text, '"next_experiments": profile.next_experiments,', '"next_experiments": list(profile.next_experiments)[:5],', "profile experiments cap")
text = replace_once(text, '"source_status": profile.source_status,', '"source_status": _compact_for_model(profile.source_status),', "profile source status compaction")

text = regex_once(
    text,
    r'''def _pair_payload\(pair: dict\[str, Any\], registry: dict\[str, AgentReference\]\) -> dict\[str, Any\]:.*?\n\n\ndef _signature_payload''',
    '''def _pair_payload(pair: dict[str, Any], registry: dict[str, AgentReference]) -> dict[str, Any]:\n    gene_a = str(pair.get("gene_a") or "A").upper()\n    gene_b = str(pair.get("gene_b") or "B").upper()\n    citation = _register_reference(\n        registry,\n        f"AN:PAIR:{gene_a}-{gene_b}",\n        f"Production target-pair analysis for {gene_a} + {gene_b}",\n        f"GBM Gene Analysis {pair.get('software_version') or SOFTWARE_VERSION}",\n        kind="analysis",\n    )\n    compacted = _compact_for_model(pair)\n    return {"analysis_citation": citation, **(compacted if isinstance(compacted, dict) else {})}\n\n\ndef _signature_payload''',
    "compact pair payload",
)

text = replace_once(text, '(signature.get("top_genes_profiled") or [])[:25]', '(signature.get("top_genes_profiled") or [])[:10]', "signature gene cap")
text = replace_once(text, '"up_pathway_enrichment": signature.get("up_pathway_enrichment"),', '"up_pathway_enrichment": _compact_for_model(signature.get("up_pathway_enrichment")),', "signature up pathways")
text = replace_once(text, '"down_pathway_enrichment": signature.get("down_pathway_enrichment"),', '"down_pathway_enrichment": _compact_for_model(signature.get("down_pathway_enrichment")),', "signature down pathways")
text = replace_once(text, '"l1000_reversal": signature.get("l1000_reversal"),', '"l1000_reversal": _compact_for_model(signature.get("l1000_reversal")),', "signature reversal")
text = replace_once(text, '"interpretation": signature.get("interpretation"),', '"interpretation": _safe_text(signature.get("interpretation"), 900),', "signature interpretation")
text = replace_once(text, '"key_findings": (live.get("key_findings") or [])[:5],', '"key_findings": (live.get("key_findings") or [])[:3],', "comparison findings cap")

text = replace_once(
    text,
    '''        selected["gene"] = _profile_payload(session_context["profile"], registry, include_evidence=True)''',
    '''        selected["gene"] = _profile_payload(\n            session_context["profile"], registry, include_evidence=(scope == "gene")\n        )''',
    "inspect-session gene depth",
)

text = replace_once(text, 'page_size=12,', 'page_size=8,', "agent publication page size")
text = replace_once(text, '(result.get("papers") or [])[:12]', '(result.get("papers") or [])[:6]', "agent publication result cap")
text = replace_once(text, '"content": content[:5000]', '"content": content[:MAX_HISTORY_CHARS]', "history cap")
text = replace_once(text, '"max_output_tokens": 900,', '"max_output_tokens": MAX_OUTPUT_TOKENS,', "agent output cap")
text = replace_once(text, 'json.dumps(memory, default=str, sort_keys=True)[:7000]', 'json.dumps(memory, default=str, sort_keys=True)[:MAX_MEMORY_CHARS]', "memory cap")
text = replace_once(text, '"output": json.dumps(payload, default=str),', '"output": _bounded_json(payload),', "tool output cap")

text = replace_once(
    text,
    '''        if status_code == 429 or "rate limit" in lowered or "too many requests" in lowered:\n            raise ResearchAgentError(\n                "Glia is temporarily at capacity on the shared Groq free tier. Please try again later."\n            ) from exc''',
    '''        if (\n            status_code == 413\n            or "request too large" in lowered\n            or "rate_limit_exceeded" in lowered and "tokens per minute" in lowered\n        ):\n            raise ResearchAgentError(\n                "Glia could not fit this request within the current free-tier context limit. "\n                "Try again; if it repeats, start a new thread or ask a narrower question."\n            ) from exc\n        if status_code == 429 or "rate limit" in lowered or "too many requests" in lowered:\n            raise ResearchAgentError(\n                "Glia is temporarily at capacity on the shared Groq free tier. Please try again later."\n            ) from exc''',
    "friendly 413 handling",
)

path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Single product walkthrough replacing workflow-specific tours.
# ---------------------------------------------------------------------------
Path("ui_walkthroughs.py").write_text(r'''"""Single condensed product walkthrough for GBM Gene Analysis."""
from __future__ import annotations

import streamlit as st


PERSISTED_SUPPRESSION_PARAM = "hide_walkthroughs"
TOUR_ID = "tool"
TOUR_TITLES = [
    "Gene Analysis",
    "Target Pair Analysis",
    "Researcher Data",
    "Gene Set Comparison",
    "Methods & Data Sources",
    "Glia",
]


def _persisted_suppressed() -> bool:
    raw = st.query_params.get(PERSISTED_SUPPRESSION_PARAM, "")
    values = raw if isinstance(raw, list) else [raw]
    return any(TOUR_ID in {part.strip() for part in str(value).split(",")} for value in values)


def _write_suppressed(suppressed: bool) -> None:
    if suppressed:
        st.query_params[PERSISTED_SUPPRESSION_PARAM] = TOUR_ID
    elif PERSISTED_SUPPRESSION_PARAM in st.query_params:
        del st.query_params[PERSISTED_SUPPRESSION_PARAM]


def _sync_suppression() -> None:
    _write_suppressed(bool(st.session_state.get("tool_tour_do_not_show", False)))


def _current_step() -> int:
    return max(0, min(len(TOUR_TITLES) - 1, int(st.session_state.get("tool_tour_step", 0))))


def _move(delta: int) -> None:
    st.session_state["tool_tour_step"] = max(0, min(len(TOUR_TITLES) - 1, _current_step() + delta))


def _note(text: str) -> None:
    st.markdown(
        f"<div style='border:1px solid rgba(128,128,128,.22);border-radius:.7rem;"
        f"padding:.68rem .85rem;margin-top:.45rem;line-height:1.42;'>{text}</div>",
        unsafe_allow_html=True,
    )


def _open_glia_from_tour() -> None:
    st.session_state["glia_force_open_nonce"] = int(st.session_state.get("glia_force_open_nonce", 0)) + 1
    st.session_state["tool_tour_seen"] = True
    st.rerun()


def _nav(step: int) -> None:
    st.markdown(
        "<div style='text-align:center;letter-spacing:.22rem;opacity:.55;margin:.3rem 0 .1rem;'>"
        + " ".join("●" if i == step else "○" for i in range(len(TOUR_TITLES)))
        + "</div>",
        unsafe_allow_html=True,
    )
    st.session_state.setdefault("tool_tour_do_not_show", _persisted_suppressed())
    pref, back, nxt = st.columns([4.6, 1.25, 1.25], vertical_alignment="center")
    with pref:
        st.checkbox(
            "Don't show this tour again",
            key="tool_tour_do_not_show",
            help="You can reopen the tour anytime from Tool tour.",
            on_change=_sync_suppression,
        )
    with back:
        if step > 0:
            st.button("← Previous", key=f"tool_tour_prev_{step}", width="stretch", on_click=_move, args=(-1,))
    with nxt:
        if step < len(TOUR_TITLES) - 1:
            st.button("Next →", key=f"tool_tour_next_{step}", type="primary", width="stretch", on_click=_move, args=(1,))
        elif st.button("Close", key="tool_tour_close", width="stretch"):
            st.rerun()


@st.dialog(
    "GBM Gene Analysis Tour",
    width="large",
    dismissible=True,
    icon=":material/slideshow:",
)
def show_tool_walkthrough() -> None:
    step = _current_step()
    st.caption(f"{step + 1} of {len(TOUR_TITLES)} · Illustrative preview")
    st.markdown(f"## {TOUR_TITLES[step]}")

    if step == 0:
        m1, m2, m3 = st.columns(3)
        m1.metric("Target Priority", "64.2 / 100")
        m2.metric("Evidence Coverage", "82.5%")
        m3.metric("Confidence", "Moderate")
        left, right = st.columns(2)
        with left:
            with st.container(border=True):
                st.markdown("**Key Findings**")
                st.write("Integrated genomic, functional, human, spatial, translational, and cell-state evidence.")
        with right:
            with st.container(border=True):
                st.markdown("**Research Gaps**")
                st.write("Conflicts and missing evidence become explicit validation opportunities.")
        _note("Enter a gene to build a traceable GBM evidence dossier, then inspect the evidence behind the score rather than treating the score as the conclusion.")

    elif step == 1:
        p1, p2, p3 = st.columns(3)
        p1.metric("Pair Rationale", "67.4 / 100")
        p2.metric("Coverage", "88%")
        p3.metric("Confidence", "Moderate")
        st.dataframe(
            [
                {"Component": "Functional support", "Score": 71},
                {"Component": "Spatial complementarity", "Score": 80},
                {"Component": "Translational feasibility", "Score": 60},
            ], width="stretch", hide_index=True, height=143,
        )
        _note("Compare two targets through the same evidence architecture. The result prioritizes a combination experiment; it is not a synergy or efficacy prediction.")

    elif step == 2:
        st.dataframe(
            [
                {"gene": "EGFR", "effect": 2.4, "p value": 0.0001, "fdr": 0.002},
                {"gene": "SOX2", "effect": 1.8, "p value": 0.001, "fdr": 0.01},
                {"gene": "BAX", "effect": -2.0, "p value": 0.0001, "fdr": 0.002},
            ], width="stretch", hide_index=True, height=143,
        )
        r1, r2 = st.columns(2)
        r1.metric("Input Genes", "148")
        r2.metric("Statistically Supported", "37")
        _note("Bring processed gene-level results into the tool to add GBM-specific evidence, pathway, cell-state, and perturbational context around your own analysis.")

    elif step == 3:
        st.dataframe(
            [
                {"Gene": "EGFR", "Priority": 64, "Coverage": "83%", "Confidence": "Moderate"},
                {"Gene": "CDK4", "Priority": 47, "Coverage": "79%", "Confidence": "Moderate"},
                {"Gene": "PTEN", "Priority": 46, "Coverage": "76%", "Confidence": "Moderate"},
            ], width="stretch", hide_index=True, height=143,
        )
        _note("Compare a focused gene set side by side using the same production evidence model. Read priority together with coverage, confidence, biology, and unresolved uncertainty.")

    elif step == 4:
        left, mid, right = st.columns(3)
        with left:
            with st.container(border=True):
                st.markdown("**Scoring**")
                st.caption("Weights, interpretation, caveats")
        with mid:
            with st.container(border=True):
                st.markdown("**Sources**")
                st.caption("Availability and provenance")
        with right:
            with st.container(border=True):
                st.markdown("**Boundaries**")
                st.caption("What each evidence type can and cannot establish")
        _note("Use this tab to audit how the system works, where evidence comes from, and which conclusions the data do not support.")

    else:
        with st.container(border=True):
            st.markdown("**Highlight → Ask Glia**")
            st.caption("Select a finding anywhere in the workspace, attach it to the composer, and ask a follow-up question.")
            st.markdown("> Evidence is strongest in the functional layer, but human validation remains incomplete.")
        _note("Glia follows the active workflow, remembers your research trail across visits in this browser, and can interrogate the evidence without replacing the underlying scientific analysis.")
        if st.button("Ask Glia", key="tool_tour_open_glia", type="primary", width="stretch"):
            _open_glia_from_tour()

    _nav(step)


def _launch_tool_tour(*, manual: bool = False) -> None:
    if not manual and _persisted_suppressed():
        return
    st.session_state["tool_tour_step"] = 0
    show_tool_walkthrough()


def render_tool_tour_launcher() -> None:
    left, right = st.columns([8.6, 1.4], vertical_alignment="center")
    with right:
        if st.button("Tool tour", key="open_tool_tour", type="tertiary", width="stretch"):
            _launch_tool_tour(manual=True)


def render_feature_header(title: str, feature: str, caption: str | None = None) -> None:
    """Render a workflow header without per-tab walkthrough controls."""
    st.markdown(
        f"<div style='font-size:1.5rem;font-weight:650;line-height:1.25;letter-spacing:-.01em;"
        f"margin:0;padding:0;'>{title}</div>",
        unsafe_allow_html=True,
    )
    if caption:
        st.caption(caption)


def maybe_show_initial_tool_walkthrough() -> None:
    if "tool_tour_seen" not in st.session_state:
        st.session_state["tool_tour_seen"] = True
        if not _persisted_suppressed():
            st.session_state["tool_tour_step"] = 0
            show_tool_walkthrough()
''', encoding="utf-8")


# ---------------------------------------------------------------------------
# App UI wiring: one product tour, no per-tab walkthrough triggers.
# ---------------------------------------------------------------------------
path = Path("app_ui.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''from ui_walkthroughs import (\n    maybe_show_active_walkthrough,\n    maybe_show_initial_gene_walkthrough,\n    on_workflow_tab_change,\n    render_feature_header,\n)''',
    '''from ui_walkthroughs import (\n    maybe_show_initial_tool_walkthrough,\n    render_feature_header,\n    render_tool_tour_launcher,\n)''',
    "app walkthrough imports",
)
text = replace_once(
    text,
    '''maybe_show_initial_gene_walkthrough()\n\n\nanalysis_tab, pair_tab, researcher_tab, batch_tab, methods_tab = st.tabs(''',
    '''render_tool_tour_launcher()\nmaybe_show_initial_tool_walkthrough()\n\n\nanalysis_tab, pair_tab, researcher_tab, batch_tab, methods_tab = st.tabs(''',
    "single tour startup",
)
text = replace_once(
    text,
    '''    ],\n    key="research_workflow_tabs",\n    on_change=on_workflow_tab_change,\n)\nmaybe_show_active_walkthrough()\nrender_glia_layer()''',
    '''    ],\n    key="research_workflow_tabs",\n)\nrender_glia_layer()''',
    "remove per-tab walkthrough trigger",
)
path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------
Path("tests/test_glia_interface.py").write_text(r'''from pathlib import Path

from glia_interface import _normalize_memory, _normalize_messages, _quick_actions


def test_memory_is_bounded_and_normalized():
    memory = _normalize_memory(
        {
            "investigated_genes": ["egfr", "pten"],
            "visited_workflows": ["Gene Analysis"],
            "recent_questions": ["q"] * 30,
            "recent_quotes": ["x"] * 20,
            "interaction_count": "4",
        }
    )
    assert memory["investigated_genes"] == ["EGFR", "PTEN"]
    assert memory["interaction_count"] == 4
    assert len(memory["recent_questions"]) <= 12
    assert len(memory["recent_quotes"]) <= 8


def test_messages_keep_only_conversation_fields():
    messages = _normalize_messages(
        [
            {"role": "user", "content": "Why?", "quote": "selected finding", "section": "Key Findings"},
            {
                "role": "assistant",
                "content": "Because.",
                "references": [{"token": "AN:GENE:EGFR"}],
                "grounding_ok": True,
                "unexpected": "drop me",
            },
        ]
    )
    assert messages[0]["quote"] == "selected finding"
    assert messages[0]["section"] == "Key Findings"
    assert "unexpected" not in messages[1]


def test_quick_actions_are_workflow_specific():
    assert "Challenge this target pair" in _quick_actions("Target Pair Analysis")
    assert "Interpret the highest-priority signals" in _quick_actions("Researcher Data")


def test_glia_component_has_integrated_high_contrast_controls_and_force_open():
    source = Path("glia_interface.py").read_text(encoding="utf-8")
    for required in (
        "Ask Glia",
        "gliaGlyph",
        "force_open_nonce",
        "selectionTouchesIgnoredArea",
        "syncWorkspaceLayout",
        "localStorage",
        "glia-panel-open",
        "Research memory",
        "background:#171717; color:#fff",
        "<span>Ask Glia</span>",
    ):
        assert required in source, required


def test_main_header_is_excluded_from_ask_glia_selection():
    source = Path("app_ui.py").read_text(encoding="utf-8")
    assert source.count('data-glia-ignore-selection="true"') >= 2


def test_single_condensed_product_tour_replaces_per_tab_walkthroughs():
    source = Path("ui_walkthroughs.py").read_text(encoding="utf-8")
    assert "def show_tool_walkthrough" in source
    assert "Gene Analysis" in source
    assert "Target Pair Analysis" in source
    assert "Researcher Data" in source
    assert "Gene Set Comparison" in source
    assert "Methods & Data Sources" in source
    assert "glia_force_open_nonce" in source
    assert 'st.button("Ask Glia"' in source
    for obsolete in (
        "def show_gene_walkthrough",
        "def show_pair_walkthrough",
        "def show_researcher_walkthrough",
        "def show_comparison_walkthrough",
        "on_workflow_tab_change",
    ):
        assert obsolete not in source


if __name__ == "__main__":
    test_memory_is_bounded_and_normalized()
    test_messages_keep_only_conversation_fields()
    test_quick_actions_are_workflow_specific()
    test_glia_component_has_integrated_high_contrast_controls_and_force_open()
    test_main_header_is_excluded_from_ask_glia_selection()
    test_single_condensed_product_tour_replaces_per_tab_walkthroughs()
    print("GLIA INTERFACE TESTS OK")
''', encoding="utf-8")

Path("tests/test_research_agent.py").write_text(r'''import json
from types import SimpleNamespace

from gbm_evidence_engine.research_agent import (
    AgentReference,
    ResearchAgentError,
    _bounded_json,
    _signature_payload,
    run_agent_turn,
    validate_quantitative_grounding,
)


class FakeResponses:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            tool_call = SimpleNamespace(
                type="function_call",
                name="build_gene_dossier",
                arguments='{"gene":"EGFR"}',
                call_id="call_1",
            )
            return SimpleNamespace(output=[tool_call], output_text="")
        return SimpleNamespace(
            output=[],
            output_text="EGFR has a Target Priority Score of 64.2 [AN:GENE:EGFR].",
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


class FakeRateLimitError(RuntimeError):
    status_code = 429


class FakeRequestTooLargeError(RuntimeError):
    status_code = 413


class RateLimitedResponses:
    def create(self, **kwargs):
        raise FakeRateLimitError("rate limit exceeded")


class RateLimitedClient:
    def __init__(self):
        self.responses = RateLimitedResponses()


class TooLargeResponses:
    def create(self, **kwargs):
        raise FakeRequestTooLargeError("Request too large on tokens per minute; rate_limit_exceeded")


class TooLargeClient:
    def __init__(self):
        self.responses = TooLargeResponses()


class CaptureResponses:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output=[], output_text="No quantitative claim.")


class CaptureClient:
    def __init__(self):
        self.responses = CaptureResponses()


def fake_dispatch(name, arguments, session_context, registry):
    assert name == "build_gene_dossier"
    assert arguments == {"gene": "EGFR"}
    registry["AN:GENE:EGFR"] = AgentReference(
        token="AN:GENE:EGFR",
        label="Production GBM Gene Analysis dossier for EGFR",
        source="GBM Gene Analysis 7.0.0",
        kind="analysis",
    )
    return {
        "analysis_citation": "[AN:GENE:EGFR]",
        "gene": "EGFR",
        "target_priority_score": 64.2,
    }


def test_agent_runs_bounded_function_call_loop_with_grounded_output():
    result = run_agent_turn(
        "Why is EGFR interesting?",
        client=FakeClient(),
        tool_dispatcher=fake_dispatch,
        model="openai/gpt-oss-120b",
    )
    assert result.grounding_ok
    assert result.unmatched_numbers == []
    assert result.tools_used == ["build_gene_dossier"]
    assert result.references[0]["token"] == "AN:GENE:EGFR"
    assert "64.2" in result.text


def test_quantitative_grounding_rejects_unreturned_statistic():
    ok, unmatched = validate_quantitative_grounding(
        "The score was 88.7%.",
        [{"score": 64.2}],
    )
    assert not ok
    assert "88.7%" in unmatched


def test_researcher_context_excludes_raw_table_fields():
    registry = {}
    signature = {
        "n_input_genes": 8,
        "n_statistically_supported": 6,
        "statistics_provided": True,
        "top_genes_profiled": [{"gene": "EGFR", "discovery_priority": 79}],
        "up_pathway_enrichment": {"ok": True, "results": []},
        "down_pathway_enrichment": {"ok": True, "results": []},
        "l1000_reversal": {"ok": True, "top_drugs": []},
        "interpretation": "Processed result context.",
        "software_version": "7.0.0",
        "raw_table": "must not leave the application",
        "uploaded_rows": [{"patient": "example"}],
    }
    payload = _signature_payload(signature, registry)
    assert "raw_table" not in payload
    assert "uploaded_rows" not in payload
    assert payload["n_input_genes"] == 8
    assert "CTX:RESEARCHER_DATA" in registry


def test_rate_limit_is_presented_as_temporary_shared_capacity():
    try:
        run_agent_turn("Compare EGFR and CDK4.", client=RateLimitedClient(), model="openai/gpt-oss-120b")
    except ResearchAgentError as exc:
        assert "temporarily at capacity" in str(exc)
        assert "Groq free tier" in str(exc)
    else:
        raise AssertionError("Expected ResearchAgentError for a Groq 429 response")


def test_413_request_size_error_is_friendly_and_provider_details_are_hidden():
    try:
        run_agent_turn("Explain the strongest finding.", client=TooLargeClient(), model="openai/gpt-oss-120b")
    except ResearchAgentError as exc:
        message = str(exc)
        assert "free-tier context limit" in message
        assert "org_" not in message
        assert "8953" not in message
    else:
        raise AssertionError("Expected ResearchAgentError for a 413 response")


def test_history_memory_and_output_budget_are_bounded_before_provider_call():
    client = CaptureClient()
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": "x" * 10000}
        for i in range(12)
    ]
    memory = {"recent_questions": ["y" * 5000] * 20, "investigated_genes": ["EGFR"]}
    run_agent_turn(
        "Summarize this workspace.",
        history=history,
        persistent_memory=memory,
        client=client,
        model="openai/gpt-oss-120b",
    )
    kwargs = client.responses.kwargs
    assert kwargs is not None
    assert kwargs["max_output_tokens"] == 500
    serialized = json.dumps(kwargs["input"], default=str)
    assert len(serialized) < 9000


def test_tool_output_serialization_is_hard_bounded():
    payload = {"rows": [{"text": "z" * 5000, "value": i} for i in range(50)]}
    encoded = _bounded_json(payload)
    assert len(encoded) <= 6600
    json.loads(encoded)


if __name__ == "__main__":
    test_agent_runs_bounded_function_call_loop_with_grounded_output()
    test_quantitative_grounding_rejects_unreturned_statistic()
    test_researcher_context_excludes_raw_table_fields()
    test_rate_limit_is_presented_as_temporary_shared_capacity()
    test_413_request_size_error_is_friendly_and_provider_details_are_hidden()
    test_history_memory_and_output_budget_are_bounded_before_provider_call()
    test_tool_output_serialization_is_hard_bounded()
    print("RESEARCH AGENT TESTS OK")
''', encoding="utf-8")


# ---------------------------------------------------------------------------
# CI assertions updated for the single product tour.
# ---------------------------------------------------------------------------
path = Path(".github/workflows/ci.yml")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''          assert 'on_change=on_workflow_tab_change' in ui\n          assert 'PERSISTED_SUPPRESSION_PARAM = "hide_walkthroughs"' in walkthroughs\n          assert 'st.query_params[PERSISTED_SUPPRESSION_PARAM]' in walkthroughs\n          assert 'def show_walkthrough()' not in ui\n          for function_name in (\n              'show_gene_walkthrough',\n              'show_pair_walkthrough',\n              'show_researcher_walkthrough',\n              'show_comparison_walkthrough',\n              'on_workflow_tab_change',\n              'maybe_show_active_walkthrough',\n          ):\n              assert f'def {function_name}' in walkthroughs, function_name''',
    '''          assert 'on_change=on_workflow_tab_change' not in ui\n          assert 'PERSISTED_SUPPRESSION_PARAM = "hide_walkthroughs"' in walkthroughs\n          assert 'st.query_params[PERSISTED_SUPPRESSION_PARAM]' in walkthroughs\n          assert 'def show_tool_walkthrough' in walkthroughs\n          assert 'maybe_show_initial_tool_walkthrough' in ui\n          assert 'render_tool_tour_launcher()' in ui\n          assert 'glia_force_open_nonce' in walkthroughs\n          for obsolete in (\n              'show_gene_walkthrough',\n              'show_pair_walkthrough',\n              'show_researcher_walkthrough',\n              'show_comparison_walkthrough',\n              'on_workflow_tab_change',\n              'maybe_show_active_walkthrough',\n          ):\n              assert f'def {obsolete}' not in walkthroughs, obsolete''',
    "CI walkthrough assertions",
)
text = replace_once(
    text,
    '''          for required in ('Ask Glia', 'localStorage', 'st.components.v2.component', 'glia-panel-open', 'Research memory'):\n              assert required in glia, required''',
    '''          for required in ('Ask Glia', 'gliaGlyph', 'force_open_nonce', 'localStorage', 'st.components.v2.component', 'glia-panel-open', 'Research memory'):\n              assert required in glia, required''',
    "CI Glia assertions",
)
text = replace_once(
    text,
    '''          print('SINGLE PRODUCTION UI + PUBLICATION BROWSER + FEATURE WALKTHROUGHS + INTEGRATED GLIA COPILOT OK')''',
    '''          print('SINGLE PRODUCTION UI + PUBLICATION BROWSER + PRODUCT TOUR + INTEGRATED GLIA COPILOT OK')''',
    "CI success label",
)
text = replace_once(
    text,
    '''          assert bool(at.session_state['gene_walkthrough_seen'])''',
    '''          assert bool(at.session_state['tool_tour_seen'])''',
    "CI Streamlit tour state",
)
path.write_text(text, encoding="utf-8")

print("Glia UX, tour, and context migration applied")
