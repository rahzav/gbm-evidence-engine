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
.st-key-glia_command_center {
  border: 1px solid color-mix(in srgb, var(--st-primary-color, #ff4b4b) 24%, rgba(128,128,128,.22)) !important;
  border-radius: 1rem !important;
  background:
    radial-gradient(circle at 50% -35%, color-mix(in srgb, var(--st-primary-color, #ff4b4b) 16%, transparent), transparent 58%),
    color-mix(in srgb, var(--st-text-color, #111) 2.2%, transparent) !important;
  box-shadow: 0 12px 34px rgba(0,0,0,.055);
  padding: .35rem .65rem .55rem .65rem !important;
}
.st-key-glia_launch_center button {
  min-height: 3.15rem !important;
  border-radius: .78rem !important;
  font-weight: 760 !important;
  letter-spacing: -.01em !important;
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--st-primary-color, #ff4b4b) 58%, transparent),
    0 0 20px color-mix(in srgb, var(--st-primary-color, #ff4b4b) 34%, transparent),
    0 7px 20px rgba(0,0,0,.12) !important;
  animation: gliaHeroGlow 2.8s ease-in-out infinite;
}
.st-key-glia_launch_center button:hover {
  transform: translateY(-1px);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--st-primary-color, #ff4b4b) 75%, transparent),
    0 0 30px color-mix(in srgb, var(--st-primary-color, #ff4b4b) 48%, transparent),
    0 9px 24px rgba(0,0,0,.15) !important;
}
.st-key-open_tool_tour_info button {
  min-height: 2.25rem !important;
  width: 2.25rem !important;
  border-radius: 999px !important;
  padding: 0 !important;
}
@keyframes gliaHeroGlow {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.055); }
}
@media (prefers-reduced-motion: reduce) {
  .st-key-glia_launch_center button { animation: none !important; transition: none !important; }
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
    """Render the product identity and keep the walkthrough control beside the product title."""
    st.markdown(PRODUCT_SHELL_CSS, unsafe_allow_html=True)
    title_col, info_col, spacer_col = st.columns([3.0, 0.28, 6.72], vertical_alignment="center")
    with title_col:
        st.markdown(
            "<div data-glia-ignore-selection='true' style='font-size:clamp(2.15rem,3vw,2.75rem);font-weight:720;"
            "line-height:1.06;letter-spacing:-.025em;margin:0;padding:0;white-space:nowrap;'>GBM Gene Analysis</div>",
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
    st.markdown(
        """
        <div data-glia-ignore-selection="true" style="font-size:1.03rem;line-height:1.42;opacity:.68;margin:.38rem 0 0 0;">Real-time integrated gene-level evidence synthesis for glioblastoma research.</div>
        <div style="font-size:.89rem;line-height:1.38;opacity:.66;margin:.22rem 0 .95rem 0;"><b style="opacity:.95;">Research use only:</b> Results support research prioritization and hypothesis development, not clinical decision-making.</div>
        """,
        unsafe_allow_html=True,
    )


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
    """Render Glia as the flagship research-interrogation layer above the workflows."""
    with st.container(border=True, key="glia_command_center"):
        st.markdown(
            "<div style='text-align:center;font-size:.7rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase;"
            "opacity:.56;margin-top:.1rem;'>Glia · Evidence-Grounded Research Copilot</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='text-align:center;font-size:clamp(1.45rem,2vw,1.9rem);font-weight:710;letter-spacing:-.022em;"
            "line-height:1.16;margin:.32rem auto 0;max-width:48rem;'>Interrogate the evidence. Challenge the conclusion. Decide what to test next.</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='text-align:center;font-size:.91rem;line-height:1.48;opacity:.67;margin:.4rem auto .8rem;max-width:52rem;'>"
            "Glia works across the current workspace to identify the decisive signal, expose contradictions, retrieve relevant GBM literature, compare targets, and turn uncertainty into a discriminating experiment.</div>",
            unsafe_allow_html=True,
        )
        capability_cols = st.columns(3)
        capabilities = (
            ("Interrogate", "Ask what actually changes the research decision."),
            ("Challenge", "Find the strongest reason a target or interpretation could fail."),
            ("Design", "Convert unresolved evidence into the highest-information next test."),
        )
        for col, (label, copy) in zip(capability_cols, capabilities):
            with col:
                st.markdown(
                    f"<div style='text-align:center;border:1px solid rgba(128,128,128,.18);border-radius:.72rem;padding:.58rem .7rem;min-height:4.2rem;'>"
                    f"<div style='font-size:.82rem;font-weight:720;'>{label}</div>"
                    f"<div style='font-size:.76rem;line-height:1.35;opacity:.6;margin-top:.14rem;'>{copy}</div></div>",
                    unsafe_allow_html=True,
                )
        left, center, right = st.columns([3.1, 1.8, 3.1], vertical_alignment="center")
        with center:
            if st.button(
                "Ask Glia",
                icon=":material/auto_awesome:",
                key="glia_launch_center",
                type="primary",
                width="stretch",
                help="Open the Glia research copilot",
            ):
                _open_glia()
        st.markdown(
            f"<div style='text-align:center;font-size:.74rem;line-height:1.35;opacity:.5;margin:.12rem 0 .05rem 0;'>{_current_glia_context()}</div>",
            unsafe_allow_html=True,
        )


def render_tool_tour_launcher() -> None:
    """Compatibility no-op retained for release-contract checks."""
    return None


def render_feature_header(title: str, feature: str, caption: str | None = None) -> None:
    """Render a focused workflow header without competing global controls."""
    st.markdown(
        f"<div style='font-size:1.48rem;font-weight:680;line-height:1.2;letter-spacing:-.016em;margin:.15rem 0 0 0;'>{title}</div>",
        unsafe_allow_html=True,
    )
    if caption:
        st.markdown(
            f"<div style='font-size:.88rem;line-height:1.42;opacity:.62;margin:.22rem 0 .72rem 0;'>{caption}</div>",
            unsafe_allow_html=True,
        )


def maybe_show_initial_tool_walkthrough() -> None:
    if "tool_tour_seen" not in st.session_state:
        st.session_state["tool_tour_seen"] = True
        if not _persisted_suppressed():
            st.session_state["tool_tour_step"] = 0
            show_tool_walkthrough()
