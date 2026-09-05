"""Single condensed product walkthrough for GBM Gene Analysis."""
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
/* Product shell: compact, research-first, and intentionally quieter than the data. */
[data-testid="stAppViewBlockContainer"] {
  max-width: 1480px !important;
  padding-top: 2.25rem !important;
  padding-bottom: 4rem !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { right: 1rem !important; }
.gbm-product-bar {
  display:flex; align-items:center; gap:.85rem; min-height:3.25rem;
  padding-bottom:1.15rem; border-bottom:1px solid rgba(148,163,184,.16);
}
.gbm-product-mark {
  width:2.35rem; height:2.35rem; flex:0 0 auto; display:grid; place-items:center;
  border-radius:.58rem; background:#e4554f; color:#fff; font-weight:800;
  font-size:.9rem; letter-spacing:-.04em;
}
.gbm-product-copy { min-width:0; }
.gbm-product-title {
  font-size:1.2rem; font-weight:720; letter-spacing:-.02em; line-height:1.15;
}
.gbm-product-subtitle {
  margin-top:.16rem; color:rgba(226,232,240,.58); font-size:.82rem; line-height:1.3;
}
.gbm-research-pill {
  margin-left:auto; white-space:nowrap; border:1px solid rgba(148,163,184,.2);
  border-radius:999px; padding:.34rem .65rem; color:rgba(226,232,240,.62);
  font-size:.7rem; font-weight:650; letter-spacing:.025em;
}
.st-key-open_tool_tour_info { width:2.2rem; flex:0 0 auto; }
.st-key-open_tool_tour_info button {
  min-height:2.1rem !important; width:2.1rem !important; border-radius:.5rem !important;
  padding:0 !important; border:1px solid rgba(148,163,184,.16) !important;
}
.st-key-glia_command_center {
  border:1px solid rgba(148,163,184,.16) !important;
  border-radius:.8rem !important;
  background:rgba(20,25,34,.72) !important;
  box-shadow:none !important;
  padding:.25rem .45rem !important;
  margin:.95rem 0 1.15rem !important;
}
.st-key-glia_launch_center button {
  min-height:2.45rem !important; border-radius:.55rem !important;
  font-weight:680 !important; letter-spacing:-.01em !important; box-shadow:none !important;
}
.st-key-glia_launch_center button:hover {
  transform:none; box-shadow:none !important;
}
/* Make the workflow selector read as product navigation, not another content block. */
[data-testid="stTabs"] > [data-baseweb="tab-list"] {
  gap:1.65rem !important; border-bottom:1px solid rgba(148,163,184,.16) !important;
  margin-bottom:1.45rem !important;
}
[data-testid="stTabs"] > [data-baseweb="tab-list"] button {
  min-height:2.8rem !important; padding:0 !important; font-size:.86rem !important;
  color:rgba(226,232,240,.62) !important;
}
[data-testid="stTabs"] > [data-baseweb="tab-list"] button[aria-selected="true"] {
  color:#f8fafc !important; font-weight:680 !important;
}
[data-testid="stForm"] {
  border:1px solid rgba(148,163,184,.2) !important; border-radius:.75rem !important;
  background:rgba(20,25,34,.52) !important; padding:1rem 1.05rem .9rem !important;
}
[data-testid="stForm"] [data-testid="stTextInput"] input {
  min-height:3rem; border-radius:.55rem;
}
.gbm-workflow-heading { margin:.05rem 0 1rem; }
.gbm-workflow-kicker {
  color:#e76b64; font-size:.68rem; font-weight:760; letter-spacing:.12em;
  text-transform:uppercase; margin-bottom:.35rem;
}
.gbm-workflow-title {
  font-size:1.6rem; font-weight:720; letter-spacing:-.025em; line-height:1.15;
}
.gbm-workflow-caption {
  margin-top:.35rem; max-width:53rem; color:rgba(226,232,240,.6);
  font-size:.88rem; line-height:1.5;
}
@media (prefers-reduced-motion: reduce) {
  .st-key-glia_launch_center button { transition:none !important; }
}
@media (max-width: 760px) {
  [data-testid="stAppViewBlockContainer"] { padding-top:1.25rem !important; }
  .gbm-product-subtitle { display:none; }
  .gbm-research-pill { display:none; }
  [data-testid="stTabs"] > [data-baseweb="tab-list"] { gap:1.1rem !important; overflow-x:auto; }
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


def render_product_header() -> None:
    """Render a compact product bar with the walkthrough control in context."""
    st.markdown(PRODUCT_SHELL_CSS, unsafe_allow_html=True)
    title_col, info_col = st.columns([9.7, 0.3], vertical_alignment="center")
    with title_col:
        st.markdown(
            """
            <div class="gbm-product-bar" data-glia-ignore-selection="true">
              <div class="gbm-product-mark">GBM</div>
              <div class="gbm-product-copy">
                <div class="gbm-product-title">GBM Evidence Engine</div>
                <div class="gbm-product-subtitle">Integrated evidence workspace for glioblastoma research</div>
              </div>
              <div class="gbm-research-pill">Research use only</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with info_col:
        if st.button(
            "",
            icon=":material/info:",
            key="open_tool_tour_info",
            help="Open product walkthrough",
            type="tertiary",
        ):
            _launch_tool_tour(manual=True)


def _current_glia_context() -> str:
    active = str(st.session_state.get("research_workflow_tabs") or "Gene Analysis")
    if active == "Gene Analysis":
        profile = st.session_state.get("profile")
        gene = getattr(profile, "gene", None) if profile is not None else None
        return f"Current context: {gene} gene dossier" if gene else "No dossier loaded yet — start with a gene or ask Glia to investigate one."
    if active == "Target Pair Analysis":
        pair = st.session_state.get("pair") or {}
        if isinstance(pair, dict) and pair:
            return f"Current context: {pair.get('gene_a', '')} + {pair.get('gene_b', '')} target pair"
        return "No target pair loaded yet — Glia can help frame which combination is worth testing."
    if active == "Researcher Data":
        return "Current context: processed researcher results" if st.session_state.get("signature") else "No researcher result loaded yet — Glia can help interpret one after analysis."
    if active == "Gene Set Comparison":
        profiles = st.session_state.get("comparison_profiles") or []
        return f"Current context: {len(profiles)}-gene comparison" if profiles else "No gene set comparison loaded yet — Glia can help prioritize a focused set."
    return "Current context: methods, evidence sources, and interpretation boundaries."


def render_glia_command_center() -> None:
    """Render Glia as a compact secondary action within the workspace."""
    with st.container(border=True, key="glia_command_center"):
        copy_col, action_col = st.columns([7.8, 2.2], vertical_alignment="center")
        with copy_col:
            st.markdown(
                f"<div style='padding:.35rem .45rem;'>"
                f"<div style='font-size:.86rem;font-weight:700;letter-spacing:-.01em;'>Glia research copilot</div>"
                f"<div style='font-size:.76rem;line-height:1.4;opacity:.56;margin-top:.12rem;'>{_current_glia_context()}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with action_col:
            if st.button(
                "Ask Glia",
                icon=":material/chat_bubble_outline:",
                key="glia_launch_center",
                type="primary",
                width="stretch",
                help="Interrogate the current evidence with Glia",
            ):
                _open_glia()


def render_tool_tour_launcher() -> None:
    """Compatibility no-op retained for release-contract checks."""
    return None


def render_feature_header(title: str, feature: str, caption: str | None = None) -> None:
    """Render a focused workflow header without competing global controls."""
    st.markdown(
        f"<div class='gbm-workflow-heading'><div class='gbm-workflow-kicker'>Workspace</div>"
        f"<div class='gbm-workflow-title'>{title}</div>"
        + (f"<div class='gbm-workflow-caption'>{caption}</div>" if caption else "")
        + "</div>", unsafe_allow_html=True,
    )


def maybe_show_initial_tool_walkthrough() -> None:
    if "tool_tour_seen" not in st.session_state:
        st.session_state["tool_tour_seen"] = True
        if not _persisted_suppressed():
            st.session_state["tool_tour_step"] = 0
            show_tool_walkthrough()
