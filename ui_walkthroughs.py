"""Unified product walkthrough and shell for Glia."""
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

PRODUCT_SHELL_CSS = """
<style>
/* Glia workspace system: a dense, research-first shell around the validated engine. */
:root {
  --glia-canvas:#0a0e13;
  --glia-surface:#10161e;
  --glia-surface-raised:#141b24;
  --glia-line:rgba(148,163,184,.16);
  --glia-line-strong:rgba(148,163,184,.26);
  --glia-text:#eef2f7;
  --glia-muted:#919baa;
  --glia-faint:#677180;
  --glia-accent:#e66c65;
  --glia-accent-hover:#f07870;
  --glia-radius:8px;
}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background:var(--glia-canvas) !important;
}
[data-testid="stAppViewBlockContainer"] {
  max-width:1520px !important;
  padding:1.45rem 2.15rem 5rem !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { right: 1rem !important; }
.glia-product-bar { min-height:2.35rem; display:flex; align-items:center; }
.st-key-glia_header_identity [data-testid="stHorizontalBlock"] {
  gap:.18rem !important;
  align-items:center !important;
  flex-wrap:nowrap !important;
}
.st-key-glia_header_identity [data-testid="stMarkdownContainer"] { width:auto !important; }
.st-key-glia_header_identity [data-testid="stElementContainer"] { flex:0 0 auto !important; width:auto !important; }
.glia-identity { display:flex; align-items:center; gap:.62rem; }
.glia-identity-mark {
  width:1.95rem; height:1.95rem; flex:0 0 auto; color:var(--glia-accent);
  display:flex; align-items:center; justify-content:center;
}
.glia-identity-mark svg { width:100%; height:100%; display:block; }
.glia-wordmark {
  font-size:1.45rem; font-weight:780; letter-spacing:.09em; line-height:1;
  color:var(--glia-text);
}
.glia-product-copy {
  padding:.42rem 0 1.05rem; border-bottom:1px solid var(--glia-line);
}
.glia-product-subtitle {
  color:#b7c0cc; font-size:.9rem; line-height:1.45;
}
.glia-research-note {
  margin-top:.16rem; color:var(--glia-faint); font-size:.72rem; line-height:1.45;
}
.glia-engine-status {
  display:flex; justify-content:flex-end; align-items:center; gap:.46rem;
  min-height:2.25rem; color:var(--glia-muted); font-size:.7rem;
  letter-spacing:.055em; text-transform:uppercase; white-space:nowrap;
}
.glia-engine-status::before {
  content:""; width:6px; height:6px; border-radius:50%; background:#68a986;
}
.st-key-open_glia_header button {
  min-height:2.25rem !important; border-radius:6px !important; padding:0 .85rem !important;
  font-weight:690 !important; box-shadow:none !important;
}
.st-key-open_tool_tour_info { width:2rem !important; flex:0 0 2rem !important; margin-left:.05rem !important; }
.st-key-open_tool_tour_info button {
  min-height:1.9rem !important; width:1.9rem !important; border-radius:6px !important;
  padding:0 !important; border:0 !important; background:transparent !important;
  color:var(--glia-muted) !important;
}
.st-key-open_tool_tour_info button:hover { color:var(--glia-text) !important; background:rgba(148,163,184,.08) !important; }
/* Root workflow rail */
.st-key-research_workflow_tabs > [data-testid="stTabs"] > [data-baseweb="tab-list"],
.st-key-research_workflow_tabs [data-testid="stTabs"]:first-child > [data-baseweb="tab-list"] {
  gap:.24rem !important; border-bottom:1px solid var(--glia-line) !important;
  margin:0 0 1.35rem !important; padding:.55rem 0 0 !important;
}
.st-key-research_workflow_tabs > [data-testid="stTabs"] > [data-baseweb="tab-list"] button,
.st-key-research_workflow_tabs [data-testid="stTabs"]:first-child > [data-baseweb="tab-list"] button {
  min-height:2.65rem !important; padding:0 .9rem !important; border-radius:6px 6px 0 0 !important;
  font-size:.82rem !important; color:var(--glia-muted) !important; white-space:nowrap !important;
}
.st-key-research_workflow_tabs > [data-testid="stTabs"] > [data-baseweb="tab-list"] button[aria-selected="true"],
.st-key-research_workflow_tabs [data-testid="stTabs"]:first-child > [data-baseweb="tab-list"] button[aria-selected="true"] {
  color:var(--glia-text) !important; font-weight:700 !important; background:rgba(148,163,184,.07) !important;
}
/* Evidence navigation stays subordinate to the workflow rail. */
[data-testid="stTabPanel"] [data-testid="stTabs"] > [data-baseweb="tab-list"] {
  gap:1.15rem !important; border-bottom:1px solid var(--glia-line) !important;
  margin:.2rem 0 1rem !important;
}
[data-testid="stTabPanel"] [data-testid="stTabs"] > [data-baseweb="tab-list"] button {
  min-height:2.45rem !important; padding:0 !important; font-size:.77rem !important;
  color:var(--glia-muted) !important;
}
[data-testid="stTabPanel"] [data-testid="stTabs"] > [data-baseweb="tab-list"] button[aria-selected="true"] {
  color:var(--glia-text) !important; font-weight:660 !important;
}
[data-testid="stForm"] {
  border:1px solid var(--glia-line-strong) !important; border-radius:var(--glia-radius) !important;
  background:var(--glia-surface) !important; padding:1rem 1.05rem .95rem !important;
}
[data-baseweb="input"] > div, [data-baseweb="textarea"] > div,
[data-baseweb="select"] > div, [data-testid="stFileUploaderDropzone"] {
  background:var(--glia-surface-raised) !important; border-color:var(--glia-line-strong) !important;
  border-radius:6px !important; box-shadow:none !important;
}
[data-testid="stForm"] [data-testid="stTextInput"] input { min-height:2.8rem; }
[data-testid="stMetric"] {
  border-top:1px solid var(--glia-line-strong); padding:.85rem .2rem .45rem !important;
}
[data-testid="stMetricLabel"] { color:var(--glia-muted) !important; font-size:.74rem !important; }
[data-testid="stMetricValue"] { color:var(--glia-text) !important; font-size:1.55rem !important; letter-spacing:-.025em; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border:1px solid var(--glia-line) !important; border-radius:var(--glia-radius) !important; overflow:hidden; }
[data-testid="stExpander"] { border-color:var(--glia-line) !important; border-radius:var(--glia-radius) !important; background:var(--glia-surface) !important; }
[data-testid="stAlert"] { border-radius:var(--glia-radius) !important; }
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button { border-radius:6px !important; box-shadow:none !important; }
.glia-workflow-heading { margin:.05rem 0 1.1rem; padding-bottom:.1rem; }
.glia-workflow-title {
  font-size:1.48rem; font-weight:730; letter-spacing:-.028em; line-height:1.18; color:var(--glia-text);
}
.glia-workflow-caption {
  margin-top:.34rem; max-width:58rem; color:var(--glia-muted); font-size:.82rem; line-height:1.5;
}
.glia-section-label {
  display:flex; align-items:center; gap:.65rem; margin:.2rem 0 .6rem;
  color:var(--glia-faint); font-size:.66rem; font-weight:750; letter-spacing:.095em;
  line-height:1; text-transform:uppercase;
}
.glia-section-label::after { content:""; height:1px; flex:1; background:var(--glia-line); }
h2, h3, h4 { letter-spacing:-.018em !important; }
h3 { font-size:1.12rem !important; margin-top:1rem !important; }
h4 { font-size:.92rem !important; color:#d8dee7 !important; }
p, li { line-height:1.55; }
hr { border-color:var(--glia-line) !important; }
button:focus-visible, input:focus-visible, textarea:focus-visible { outline:2px solid var(--glia-accent) !important; outline-offset:2px !important; }
@media (prefers-color-scheme: light) {
  :root { --glia-canvas:#f4f6f8; --glia-surface:#ffffff; --glia-surface-raised:#f7f8fa; --glia-line:rgba(30,41,59,.13); --glia-line-strong:rgba(30,41,59,.22); --glia-text:#18212d; --glia-muted:#5f6b79; --glia-faint:#778392; }
}
@media (prefers-reduced-motion: reduce) {
  .st-key-open_glia_header button { transition:none !important; }
}
@media (max-width: 900px) {
  [data-testid="stAppViewBlockContainer"] { padding:1rem 1rem 4rem !important; }
  .glia-engine-status { display:none; }
  .glia-product-subtitle { font-size:.84rem; }
  .st-key-research_workflow_tabs [data-baseweb="tab-list"] { overflow-x:auto !important; }
  .st-key-research_workflow_tabs [data-baseweb="tab-list"] button { padding:0 .7rem !important; }
}
</style>
"""


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


def _open_glia() -> None:
    st.session_state["glia_force_open_nonce"] = int(st.session_state.get("glia_force_open_nonce", 0)) + 1


def _open_glia_from_tour() -> None:
    _open_glia()
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
            "Don't show this walkthrough again",
            key="tool_tour_do_not_show",
            help="This walkthrough remains available at any time through the information button.",
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
    "Glia Walkthrough",
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


def render_product_header() -> None:
    """Render Glia's primary identity and single persistent copilot entry point."""
    st.markdown(PRODUCT_SHELL_CSS, unsafe_allow_html=True)
    identity_col, status_col, glia_col = st.columns([7.8, 1.35, 1.35], vertical_alignment="center")
    with identity_col:
        with st.container(
            horizontal=True,
            vertical_alignment="center",
            gap="small",
            key="glia_header_identity",
        ):
            st.markdown(
                """
                <div class="glia-product-bar" data-glia-ignore-selection="true">
                  <div class="glia-identity">
                    <div class="glia-identity-mark" aria-hidden="true">
                      <svg viewBox="0 0 32 32" focusable="false">
                        <g fill="none" stroke="currentColor" stroke-width="2.15" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M16 10.2 10.4 6.4M16 10.2l5.8-4M16 20.9l-6 4.2M16 20.9l6.3 3.7M11.2 15.5H5.8M20.8 15.5h5.4"/>
                          <circle cx="16" cy="15.5" r="5.4" fill="currentColor" fill-opacity=".14"/>
                          <circle cx="10.1" cy="6.2" r="1.8" fill="currentColor"/><circle cx="22.1" cy="6" r="1.8" fill="currentColor"/>
                          <circle cx="9.7" cy="25.3" r="1.8" fill="currentColor"/><circle cx="22.6" cy="24.8" r="1.8" fill="currentColor"/>
                          <circle cx="5.3" cy="15.5" r="1.7" fill="currentColor"/><circle cx="26.7" cy="15.5" r="1.7" fill="currentColor"/>
                        </g>
                      </svg>
                    </div>
                    <div class="glia-wordmark">GLIA</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
                width="content",
            )
            if st.button(
                "",
                icon=":material/info:",
                key="open_tool_tour_info",
                help="Open Glia walkthrough",
                type="tertiary",
            ):
                _launch_tool_tour(manual=True)
    with status_col:
        st.markdown('<div class="glia-engine-status">V7 engine active</div>', unsafe_allow_html=True)
    with glia_col:
        if st.button(
            "Open Glia",
            icon=":material/forum:",
            key="open_glia_header",
            type="primary",
            width="stretch",
            help="Open the context-aware research interface",
        ):
            _open_glia()
    st.markdown(
        """
        <div class="glia-product-copy" data-glia-ignore-selection="true">
          <div class="glia-product-subtitle">Real-time integrated gene-level evidence synthesis for glioblastoma research.</div>
          <div class="glia-research-note"><strong>Research use only:</strong> Results support research prioritization and hypothesis development, not clinical decision-making.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tool_tour_launcher() -> None:
    """Compatibility no-op retained for release-contract checks."""
    return None


def render_feature_header(title: str, feature: str, caption: str | None = None) -> None:
    """Render a focused workflow header without competing global controls."""
    st.markdown(
        f"<div class='glia-workflow-heading'><div class='glia-workflow-title'>{title}</div>"
        + (f"<div class='glia-workflow-caption'>{caption}</div>" if caption else "")
        + "</div>", unsafe_allow_html=True,
    )


def render_section_label(label: str) -> None:
    """Separate analysis controls from generated research output."""
    st.markdown(f"<div class='glia-section-label'>{label}</div>", unsafe_allow_html=True)


def maybe_show_initial_tool_walkthrough() -> None:
    if "tool_tour_seen" not in st.session_state:
        st.session_state["tool_tour_seen"] = True
        if not _persisted_suppressed():
            st.session_state["tool_tour_step"] = 0
            show_tool_walkthrough()
