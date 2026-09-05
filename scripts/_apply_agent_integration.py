from pathlib import Path
import re

app_path = Path('app_ui.py')
app = app_path.read_text(encoding='utf-8')
app = app.replace('import io\nimport json\n', 'import io\nimport json\nimport os\n', 1)
anchor = 'from gbm_evidence_engine.evidence_model import EvidenceTier\n'
insert = '''from gbm_evidence_engine.research_agent import (
    ResearchAgentError,
    configured_model,
    run_agent_turn,
)
'''
if insert not in app:
    app = app.replace(anchor, anchor + insert, 1)

helper_anchor = '''\n\n\nst.markdown(
    """
    <div style="margin:0 0 .9rem 0;padding:0;">
'''
helper_code = '''


def _agent_secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    value = value or os.getenv(name)
    return str(value).strip() if value else None


def _render_agent_references(references):
    if not references:
        return
    with st.expander(f"Evidence references ({len(references)})", expanded=False):
        for ref in references:
            token = ref.get("token", "source")
            label = ref.get("label", "Evidence source")
            source = ref.get("source", "")
            url = ref.get("url")
            if url:
                st.markdown(f"- `{token}` [{label}]({url}) — {source}")
            else:
                st.markdown(f"- `{token}` {label} — {source}")


def _render_agent_message(message):
    st.markdown(message.get("content", ""))
    if message.get("grounding_ok") is False:
        st.warning("Some quantitative phrasing could not be automatically traced to retrieved evidence. Verify the cited records before using it.")
    _render_agent_references(message.get("references") or [])


def render_research_assistant():
    st.markdown("### Research Assistant")
    st.caption("Evidence-grounded GBM research copilot that can interrogate dossiers, compare targets, inspect current analyses, and retrieve live Europe PMC publications.")

    context = {
        "profile": st.session_state.get("profile"),
        "pair": st.session_state.get("pair"),
        "signature": st.session_state.get("signature"),
        "comparison_profiles": st.session_state.get("comparison_profiles"),
    }
    context_labels = []
    if context["profile"] is not None:
        context_labels.append(f"Gene: {context['profile'].gene}")
    if context["pair"] is not None:
        context_labels.append(f"Pair: {context['pair'].get('gene_a')} + {context['pair'].get('gene_b')}")
    if context["signature"] is not None:
        context_labels.append("Researcher Data result")
    if context["comparison_profiles"]:
        context_labels.append("Gene Set Comparison")
    if context_labels:
        st.caption("Current context available · " + " · ".join(context_labels))

    st.caption("Messages and only the derived analysis context the assistant explicitly retrieves are sent to OpenAI. Raw Researcher Data tables are not passed to the assistant.")

    api_key = _agent_secret("OPENAI_API_KEY")
    model = _agent_secret("OPENAI_MODEL") or configured_model()
    if not api_key:
        st.info("Research Assistant is not configured on this deployment yet.")
        return

    messages = st.session_state.setdefault("research_agent_messages", [])
    if messages:
        clear_col, _ = st.columns([1, 5])
        with clear_col:
            if st.button("Clear conversation", key="clear_research_agent", type="tertiary"):
                st.session_state["research_agent_messages"] = []
                st.rerun()

    for message in messages:
        with st.chat_message(message.get("role", "assistant")):
            if message.get("role") == "assistant":
                _render_agent_message(message)
            else:
                st.markdown(message.get("content", ""))

    prompt = st.chat_input(
        "Ask about a target, the evidence, conflicting results, current researcher data, literature, or the next experiment...",
        key="research_agent_input",
    )
    if not prompt:
        return

    prior_history = [
        {"role": item.get("role"), "content": item.get("content", "")}
        for item in messages[-8:]
    ]
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Interrogating the GBM evidence..."):
                result = run_agent_turn(
                    prompt,
                    history=prior_history,
                    session_context=context,
                    api_key=api_key,
                    model=model,
                )
            assistant_message = {
                "role": "assistant",
                "content": result.text,
                "references": result.references,
                "tools_used": result.tools_used,
                "grounding_ok": result.grounding_ok,
            }
            messages.append(assistant_message)
            _render_agent_message(assistant_message)
        except ResearchAgentError as exc:
            error_text = str(exc)
            st.error(error_text)
            messages.append({"role": "assistant", "content": error_text, "references": [], "grounding_ok": True})
'''
if 'def render_research_assistant():' not in app:
    if helper_anchor not in app:
        raise SystemExit('main header anchor not found')
    app = app.replace(helper_anchor, helper_code + helper_anchor, 1)

old_tabs = '''analysis_tab, pair_tab, researcher_tab, batch_tab, methods_tab = st.tabs(
    [
        "Gene Analysis",
        "Target Pair Analysis",
        "Researcher Data",
        "Gene Set Comparison",
        "Methods & Data Sources",
    ],
'''
new_tabs = '''analysis_tab, pair_tab, researcher_tab, batch_tab, assistant_tab, methods_tab = st.tabs(
    [
        "Gene Analysis",
        "Target Pair Analysis",
        "Researcher Data",
        "Gene Set Comparison",
        "Research Assistant",
        "Methods & Data Sources",
    ],
'''
if old_tabs not in app:
    raise SystemExit('top-level tabs block not found')
app = app.replace(old_tabs, new_tabs, 1)

batch_pattern = re.compile(r'with batch_tab:\n.*?\nwith methods_tab:\n', re.S)
batch_replacement = '''with batch_tab:
    render_feature_header(
        "Gene Set Comparison", "comparison",
        "Compare a focused gene set side by side using the same production evidence architecture.",
    )
    raw = st.text_area("Gene symbols", value="EGFR, PTEN, TP53, CDK4", key="gene_set")
    genes = list(dict.fromkeys(x.strip() for x in raw.replace(",", " ").split() if x.strip()))
    if len(genes) > 6:
        st.warning("Gene set comparison is limited to 6 genes per run.")
        genes = genes[:6]
    if st.button("Build comparison", type="primary") and genes:
        try:
            with st.spinner("Building and comparing GBM evidence dossiers..."):
                st.session_state["comparison_profiles"] = cached_batch(tuple(genes))
        except Exception as exc:
            st.error(f"Gene set comparison failed: {exc}")

    profiles = st.session_state.get("comparison_profiles")
    if profiles:
        rows = []
        for item in profiles:
            item_live = item.live
            item_dep = item_live.get("depmap", {})
            item_cgg = item_live.get("cgga", {})
            item_identity = item_live.get("gene_identity", {})
            rows.append({
                "Gene": item.gene,
                "Submitted Symbol": item_identity.get("query", item.gene),
                "Target Priority Score": item.score.overall,
                "Evidence Coverage (%)": item.score.evidence_coverage_pct,
                "Evidence Confidence": confidence_text(item_live.get("overall_evidence_confidence", {})),
                "Model Relevance": str((item_live.get("model_relevance") or {}).get("level", "unknown")).title(),
                "Priority Classification": item.score.label,
                "DepMap Selectivity Difference": item_dep.get("median_selectivity_delta"),
                "Usable CGGA Cohorts": item_cgg.get("n_usable_cohorts", 0),
                "Active GBM Trials": item_live.get("clinical_trials", {}).get("active", 0),
                "B3DB Matches": item_live.get("bbb_candidates", {}).get("matched_count", 0),
            })
        display_dataframe(rows, width="stretch", hide_index=True)

with assistant_tab:
    render_research_assistant()

with methods_tab:
'''
app, count = batch_pattern.subn(batch_replacement, app, count=1)
if count != 1:
    raise SystemExit(f'batch block replacement count={count}')
app = app.replace(
    'GBM Gene Analysis integrates molecular evidence for research prioritization, processed-result interpretation, target-pair evaluation, and experimental planning.',
    'GBM Gene Analysis integrates molecular evidence for research prioritization, processed-result interpretation, target-pair evaluation, conversational evidence interrogation, and experimental planning.',
    1,
)
app_path.write_text(app, encoding='utf-8')

readme_path = Path('README.md')
readme = readme_path.read_text(encoding='utf-8')
gene_set_anchor = '''### Gene Set Comparison

Compares a bounded set of genes through the same production profile architecture while keeping public-source and deployment resource pressure controlled.
'''
assistant_readme = '''
### Research Assistant

Provides an evidence-grounded conversational layer over the production workflows. The assistant can build gene dossiers, run target-pair and gene-set analyses, inspect analysis already present in the current session, and retrieve live Europe PMC publications. Important factual claims are tied to evidence, publication, analysis, or session-context references, and quantitative output is checked against values returned by the underlying tools. The assistant does not redefine production scores or convert hypotheses into evidence.

The assistant uses the OpenAI Responses API with function calling. Configure `OPENAI_API_KEY`; `OPENAI_MODEL` is optional and defaults to `gpt-5.4`.
'''
if '### Research Assistant' not in readme:
    if gene_set_anchor not in readme:
        raise SystemExit('README gene set anchor not found')
    readme = readme.replace(gene_set_anchor, gene_set_anchor + assistant_readme, 1)
readme_path.write_text(readme, encoding='utf-8')

handling_path = Path('docs/RESEARCHER_DATA_HANDLING.md')
handling = handling_path.read_text(encoding='utf-8')
hosting_anchor = '## Hosting and retention boundary\n'
assistant_handling = '''## Research Assistant boundary

The Research Assistant does not receive the raw uploaded or pasted researcher table. If a researcher asks the assistant to inspect the current Researcher Data analysis, the application sends only the derived result-dossier context needed for that question, such as prioritized genes, pathway results, perturbational-reversal results, and summary counts. The message and retrieved derived context are processed through the configured OpenAI API deployment and are therefore subject to that deployment's applicable data controls and retention settings. Do not use the assistant with PHI, identifiable patient information, controlled raw genomic data, credentials, or restricted material that is not approved for that environment.

'''
if '## Research Assistant boundary' not in handling:
    if hosting_anchor not in handling:
        raise SystemExit('researcher data handling anchor not found')
    handling = handling.replace(hosting_anchor, assistant_handling + hosting_anchor, 1)
handling_path.write_text(handling, encoding='utf-8')

ci_path = Path('.github/workflows/ci.yml')
ci = ci_path.read_text(encoding='utf-8')
ci = ci.replace(
    'gbm_evidence_engine/research_discovery.py \\\n            gbm_evidence_engine/research_intelligence_v7.py',
    'gbm_evidence_engine/research_discovery.py \\\n            gbm_evidence_engine/research_agent.py \\\n            gbm_evidence_engine/research_intelligence_v7.py',
    1,
)
ci = ci.replace(
    'PYTHONPATH=. python tests/test_europepmc_publications.py',
    'PYTHONPATH=. python tests/test_europepmc_publications.py\n          PYTHONPATH=. python tests/test_research_agent.py',
    1,
)
ci = ci.replace(
    "('Build dossier', 'Gene Analysis', 'Target Pair Analysis', 'Researcher Data', 'Gene Set Comparison')",
    "('Build dossier', 'Gene Analysis', 'Target Pair Analysis', 'Researcher Data', 'Gene Set Comparison', 'Research Assistant')",
)
ci_path.write_text(ci, encoding='utf-8')
