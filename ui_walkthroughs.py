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


def render_tool_tour_launcher() -> None:
    """Compatibility no-op: the unified tour now opens from the Gene Analysis info button."""
    return None


def render_feature_header(title: str, feature: str, caption: str | None = None) -> None:
    """Render a cohesive workflow header with in-layout Glia access and one tour info control."""
    content_col, glia_col = st.columns([8.8, 1.2], vertical_alignment="center")
    with content_col:
        if feature == "gene":
            title_col, info_col, spacer_col = st.columns([1.75, 0.28, 8.0], vertical_alignment="center")
            with title_col:
                st.markdown(
                    f"<div style='font-size:1.5rem;font-weight:650;line-height:1.25;letter-spacing:-.01em;"
                    f"margin:0;padding:0;'>{title}</div>",
                    unsafe_allow_html=True,
                )
            with info_col:
                if st.button(
                    "",
                    icon=":material/info:",
                    key="open_tool_tour_info",
                    help="Open tool walkthrough",
                    type="tertiary",
                ):
                    _launch_tool_tour(manual=True)
        else:
            st.markdown(
                f"<div style='font-size:1.5rem;font-weight:650;line-height:1.25;letter-spacing:-.01em;"
                f"margin:0;padding:0;'>{title}</div>",
                unsafe_allow_html=True,
            )
        if caption:
            st.caption(caption)
    with glia_col:
        if st.button("Ask Glia", key=f"open_glia_{feature}", type="primary", width="stretch"):
            _open_glia()


def maybe_show_initial_tool_walkthrough() -> None:
    if "tool_tour_seen" not in st.session_state:
        st.session_state["tool_tour_seen"] = True
        if not _persisted_suppressed():
            st.session_state["tool_tour_step"] = 0
            show_tool_walkthrough()
