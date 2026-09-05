"""Apply the feature-walkthrough/header-spacing integration to app_ui.py."""
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "app_ui.py"
text = PATH.read_text(encoding="utf-8")

import_anchor = "import pandas as pd\nimport streamlit as st\n\nfrom gbm_evidence_engine.evidence_model import EvidenceTier\n"
import_replacement = (
    "import pandas as pd\nimport streamlit as st\n\n"
    "from ui_walkthroughs import maybe_show_initial_gene_walkthrough, render_feature_header\n"
    "from gbm_evidence_engine.evidence_model import EvidenceTier\n"
)
if import_anchor not in text:
    raise SystemExit("Could not find app_ui import anchor.")
text = text.replace(import_anchor, import_replacement, 1)

start_marker = "\ndef _close_walkthrough():\n"
end_marker = "\n\nanalysis_tab, pair_tab, researcher_tab, batch_tab, methods_tab = st.tabs([\n"
start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate legacy walkthrough/header block.")

header = '''
st.markdown(
    """
    <div style="margin:0 0 .9rem 0;padding:0;">
      <div style="font-size:2.75rem;font-weight:700;line-height:1.08;letter-spacing:-0.02em;margin:0;padding:0;">GBM Gene Analysis</div>
      <div style="font-size:1.04rem;line-height:1.42;opacity:.68;margin:.38rem 0 0 0;padding:0;">Real-time synthesis of live and curated gene-level evidence for glioblastoma research.</div>
      <div style="font-size:.91rem;line-height:1.42;opacity:.68;margin:.42rem 0 0 0;padding:0;"><b style="opacity:.94;">Research use only:</b> Results are intended for research prioritization and hypothesis development, not clinical decision-making.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

maybe_show_initial_gene_walkthrough()
'''
text = text[:start] + "\n" + header + text[end:]

replacements = {
    "with analysis_tab:\n    with st.form(\"gene_analysis_form\", clear_on_submit=False):\n": (
        "with analysis_tab:\n"
        "    render_feature_header(\n"
        "        \"Gene Analysis\", \"gene\",\n"
        "        \"Build a single-gene dossier across genomic, functional, spatial, human, translational, literature, and cell-state evidence.\",\n"
        "    )\n"
        "    with st.form(\"gene_analysis_form\", clear_on_submit=False):\n"
    ),
    "with pair_tab:\n    st.subheader(\"Target Pair Analysis\", anchor=False)\n    st.caption(\"Cross-target evidence comparison across functional, network, spatial, cell-state, recurrence, translational, and model-relevance layers.\")\n": (
        "with pair_tab:\n"
        "    render_feature_header(\n"
        "        \"Target Pair Analysis\", \"pair\",\n"
        "        \"Cross-target evidence comparison across functional, network, spatial, cell-state, recurrence, translational, and model-relevance layers.\",\n"
        "    )\n"
    ),
    "with researcher_tab:\n    st.subheader(\"Processed Researcher Result Analysis\", anchor=False)\n    st.caption(\"Analyze processed gene-level results using signed effect sizes with optional p-values or FDR/q-values. Uploaded tables are read for analysis and are not written to the project repository by the application.\")\n": (
        "with researcher_tab:\n"
        "    render_feature_header(\n"
        "        \"Researcher Data\", \"researcher\",\n"
        "        \"Analyze processed gene-level signed effects with optional p-values/FDR, then add GBM evidence, pathway, and perturbational context. Uploaded tables are read for analysis and are not written to the project repository.\",\n"
        "    )\n"
    ),
    "with batch_tab:\n    st.write(\"Enter a short gene set to compare targets using the same evidence architecture.\")\n": (
        "with batch_tab:\n"
        "    render_feature_header(\n"
        "        \"Gene Set Comparison\", \"comparison\",\n"
        "        \"Compare a focused gene set side by side using the same production evidence architecture.\",\n"
        "    )\n"
    ),
}

for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"Could not locate expected UI block: {old}")
    text = text.replace(old, new, 1)

for forbidden in ["def show_walkthrough():", 'key="open_walkthrough"', 'st.session_state["walkthrough_open"]']:
    if forbidden in text:
        raise SystemExit(f"Legacy walkthrough marker still present: {forbidden}")

for marker in [
    "Real-time synthesis of live and curated gene-level evidence",
    '"Gene Analysis", "gene"',
    '"Target Pair Analysis", "pair"',
    '"Researcher Data", "researcher"',
    '"Gene Set Comparison", "comparison"',
]:
    if marker not in text:
        raise SystemExit(f"Required marker missing: {marker}")

PATH.write_text(text, encoding="utf-8")
print("Applied feature-specific walkthrough and compact header patch.")
