"""Feature-specific walkthrough dialogs for the GBM Gene Analysis UI.

Each research workflow owns a short walkthrough so researchers can learn one
feature at a time without scrolling through a monolithic product tour.
"""
from __future__ import annotations

import streamlit as st


def _step_key(feature: str) -> str:
    return f"{feature}_walkthrough_step"


def _current_step(feature: str, count: int) -> int:
    return max(0, min(count - 1, int(st.session_state.get(_step_key(feature), 0))))


def _move(feature: str, delta: int, count: int) -> None:
    key = _step_key(feature)
    st.session_state[key] = max(0, min(count - 1, int(st.session_state.get(key, 0)) + delta))


def _reset(feature: str) -> None:
    st.session_state[_step_key(feature)] = 0


def _note(text: str) -> None:
    st.markdown(
        f"<div style='border:1px solid rgba(128,128,128,.24);border-radius:.7rem;"
        f"padding:.72rem .9rem;margin-top:.45rem;line-height:1.42;'>{text}</div>",
        unsafe_allow_html=True,
    )


def _nav(feature: str, step: int, titles: list[str]) -> None:
    st.markdown(
        "<div style='text-align:center;letter-spacing:.26rem;opacity:.58;margin:.35rem 0 .05rem;'>"
        + " ".join("●" if i == step else "○" for i in range(len(titles)))
        + "</div>",
        unsafe_allow_html=True,
    )
    back_col, _, next_col = st.columns([1.3, 4.4, 1.3], vertical_alignment="center")
    with back_col:
        if step > 0:
            st.button(
                "← Previous",
                key=f"{feature}_walkthrough_prev_{step}",
                width="stretch",
                on_click=_move,
                args=(feature, -1, len(titles)),
            )
    with next_col:
        if step < len(titles) - 1:
            st.button(
                "Next →",
                key=f"{feature}_walkthrough_next_{step}",
                type="primary",
                width="stretch",
                on_click=_move,
                args=(feature, 1, len(titles)),
            )
        elif st.button(
            "Close",
            key=f"{feature}_walkthrough_close",
            type="primary",
            width="stretch",
        ):
            st.rerun()


def _intro(feature: str, titles: list[str]) -> int:
    step = _current_step(feature, len(titles))
    st.caption(f"{step + 1} of {len(titles)}  ·  Illustrative preview")
    st.markdown(f"## {titles[step]}")
    return step


@st.dialog(
    "Gene Analysis Walkthrough",
    width="large",
    dismissible=True,
    icon=":material/slideshow:",
)
def show_gene_walkthrough() -> None:
    feature = "gene"
    titles = [
        "Priority Score & Evidence Coverage",
        "Genomic Evidence",
        "Functional & Spatial Evidence",
        "Human Validation",
        "Biological Context",
        "Literature & Translation",
        "Evidence Record & Research Gaps",
    ]
    step = _intro(feature, titles)

    if step == 0:
        m1, m2, m3 = st.columns(3)
        m1.metric("Target Priority Score", "64.2 / 100")
        m2.metric("Evidence Coverage", "82.5%")
        m3.metric("Evidence Confidence", "Moderate")
        st.dataframe(
            [
                {"Evidence Dimension": "Genomic", "Score": 72, "Weight": "16.9%"},
                {"Evidence Dimension": "Functional Dependency", "Score": 58, "Weight": "15.0%"},
                {"Evidence Dimension": "Human Validation", "Score": 66, "Weight": "7.5%"},
            ],
            width="stretch",
            hide_index=True,
            height=143,
        )
        _note(
            "<b>Priority Score</b> ranks the research target. <b>Evidence Coverage</b> shows how much of the scored model is available. "
            "<b>Evidence Confidence</b> is separate and reflects support/replication. Missing evidence lowers coverage rather than becoming negative biology."
        )
    elif step == 1:
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Mutation Frequency", "8.2%")
        g2.metric("Amplification", "36.1%")
        g3.metric("Deep Deletion", "1.4%")
        g4.metric("Open Targets", "0.82")
        with st.container(border=True):
            st.markdown("**Gene identity** · canonical symbol, aliases, Ensembl and Entrez identifiers")
        _note(
            "TCGA/cBioPortal reports tumor alteration frequencies. Open Targets summarizes broader target–disease evidence. They answer different questions and remain separate in the dossier."
        )
    elif step == 2:
        d1, d2, d3 = st.columns(3)
        d1.metric("Median GBM Chronos", "-0.42")
        d2.metric("Selectivity Difference", "+0.18")
        d3.metric("One-Sided p Value", "0.03")
        st.caption("Pan-essential classification: No · Model relevance: Limited")
        st.dataframe(
            [
                {"Ivy GAP Zone": "Cellular Tumor", "Median Expression": 5.8},
                {"Ivy GAP Zone": "Leading Edge", "Median Expression": 3.1},
                {"Ivy GAP Zone": "Microvascular Proliferation", "Median Expression": 6.4},
            ],
            width="stretch",
            hide_index=True,
            height=143,
        )
        _note(
            "More negative Chronos values indicate stronger CRISPR dependency. Selectivity asks whether GBM models are more dependent than the comparison panel. Ivy GAP adds anatomic tumor context."
        )
    elif step == 3:
        c1, c2, c3 = st.columns(3)
        c1.metric("CGGA Pooled HR", "1.31")
        c2.metric("Pooled p Value", "0.01")
        c3.metric("I²", "22%")
        x1, x2, x3 = st.columns(3)
        x1.metric("GLASS Pairs", "44")
        x2.metric("Recurrence Change", "+0.18")
        x3.metric("Paired p Value", "0.04")
        _note(
            "CGGA tests independent human survival association; GLASS examines matched primary-to-recurrent change. Associations and longitudinal changes are evidence, not causal treatment effects."
        )
    elif step == 4:
        hpa_col, string_col, gbmap_col = st.columns(3)
        with hpa_col:
            with st.container(border=True):
                st.markdown("**Human Protein Atlas**")
                st.caption("Normal-tissue / brain context")
        with string_col:
            with st.container(border=True):
                st.markdown("**STRING**")
                st.caption("Interaction network + pathways")
        with gbmap_col:
            with st.container(border=True):
                st.markdown("**GBmap**")
                st.caption("Patient-aware GBM cell states")
        _note(
            "These layers add biological context without silently changing the Target Priority Score. GBmap expression patterns do not establish dependency, resistance, or drug response."
        )
    elif step == 5:
        left, right = st.columns(2)
        with left:
            st.metric("GBM Literature Records", "1,240")
            st.markdown("**Clickable publication title ↗**")
            st.caption("Europe PMC · PMID / DOI")
        with right:
            t1, t2 = st.columns(2)
            t1.metric("Target Candidates", "82")
            t2.metric("Highest Trial Phase", "2")
            b1, b2 = st.columns(2)
            b1.metric("B3DB Matches", "5")
            b2.metric("BBB+ Records", "3")
        _note(
            "Use the Literature tab's disease-context filters and keyword search to browse matching Europe PMC records beyond the initial results. Publication volume, target-directed candidates, GBM trials and measured BBB records describe different pieces of translational maturity; none alone establishes efficacy."
        )
    else:
        record_col, gap_col = st.columns(2)
        with record_col:
            with st.container(border=True):
                st.markdown("**Evidence record**")
                st.write("Claim · statistic · source · confidence · citation")
        with gap_col:
            with st.container(border=True):
                st.markdown("**Research gap → validation study**")
                st.write("Unresolved evidence is converted into an explicit next-test opportunity.")
        st.caption("Exports preserve the structured dossier and a concise research summary.")
        _note(
            "Use the evidence record to audit where each quantitative claim came from. Research opportunities and proposed experiments remain clearly separated from retrieved evidence."
        )

    _nav(feature, step, titles)


@st.dialog(
    "Target Pair Analysis Walkthrough",
    width="large",
    dismissible=True,
    icon=":material/slideshow:",
)
def show_pair_walkthrough() -> None:
    feature = "pair"
    titles = [
        "What the Pair Score Means",
        "Rationale Components",
        "Cell-State & Model Context",
        "Interpretation & Validation",
    ]
    step = _intro(feature, titles)

    if step == 0:
        p1, p2, p3 = st.columns(3)
        p1.metric("Combination Rationale", "67.4 / 100")
        p2.metric("Evidence Coverage", "88%")
        p3.metric("Pair Confidence", "Moderate")
        _note(
            "The <b>Combination Rationale Score</b> ranks whether a two-target experiment is worth testing from the available evidence. It is not a synergy score, efficacy prediction, or safety estimate."
        )
    elif step == 1:
        st.dataframe(
            [
                {"Component": "Individual target quality", "Score": 63},
                {"Component": "Functional support", "Score": 71},
                {"Component": "Network complementarity", "Score": 78},
                {"Component": "Spatial complementarity", "Score": 80},
                {"Component": "Translational feasibility", "Score": 60},
            ],
            width="stretch",
            hide_index=True,
            height=211,
        )
        _note(
            "The score combines distinct evidence dimensions only when they are available. Missing pair components reduce coverage instead of being imputed as supportive or negative evidence."
        )
    elif step == 2:
        left, right = st.columns(2)
        with left:
            with st.container(border=True):
                st.markdown("**GBmap malignant-state complementarity**")
                st.metric("Complementarity", "62 / 100")
                st.caption("Do the two targets occupy different malignant-state expression patterns?")
        with right:
            with st.container(border=True):
                st.markdown("**Functional model relevance**")
                st.write("Target A: Limited")
                st.write("Target B: Moderate")
        _note(
            "Cell-state complementarity and model relevance qualify the biological context. They do not prove a combination will be synergistic or effective."
        )
    else:
        left, right = st.columns(2)
        with left:
            st.markdown("**Why test it**")
            st.markdown("- Complementary network neighborhoods\n- Distinct tumor-state context\n- Reproducible target evidence")
        with right:
            st.markdown("**Limitations**")
            st.markdown("- Limited physiologic models\n- Therapeutic-window concern\n- Incomplete CNS evidence")
        st.caption("The dossier ends with an ordered validation sequence: single agents → dose matrix → state-matched models → in-vivo CNS evaluation.")
        _note(
            "Treat the output as a rationale for a controlled combination experiment. Direct dose-matrix and state-aware validation are required before making a synergy claim."
        )

    _nav(feature, step, titles)


@st.dialog(
    "Researcher Data Walkthrough",
    width="large",
    dismissible=True,
    icon=":material/slideshow:",
)
def show_researcher_walkthrough() -> None:
    feature = "researcher"
    titles = [
        "Prepare Processed Results",
        "GBM-Prioritized Signals",
        "Pathways & Perturbational Reversal",
        "Interpretation & Export",
    ]
    step = _intro(feature, titles)

    if step == 0:
        st.dataframe(
            [
                {"gene": "EGFR", "effect": 2.4, "p_value": 0.0001, "fdr": 0.002},
                {"gene": "SOX2", "effect": 1.8, "p_value": 0.001, "fdr": 0.01},
                {"gene": "BAX", "effect": -2.0, "p_value": 0.0001, "fdr": 0.002},
            ],
            width="stretch",
            hide_index=True,
            height=143,
        )
        _note(
            "Upload or paste <b>processed gene-level results</b>: gene symbol + signed effect, with optional p-values/FDR. At least 6 unique non-zero genes are required. Do not upload raw sequencing files or identifiable patient data."
        )
    elif step == 1:
        r1, r2 = st.columns(2)
        r1.metric("Input Genes", "148")
        r2.metric("Statistically Supported", "37")
        st.dataframe(
            [
                {"Gene": "EGFR", "Discovery Priority": 79, "Target Priority": 64, "Confidence": 69, "Top State": "AC-like"},
                {"Gene": "STAT3", "Discovery Priority": 72, "Target Priority": 58, "Confidence": 66, "Top State": "MES-like"},
            ],
            width="stretch",
            hide_index=True,
            height=108,
        )
        _note(
            "Discovery Priority combines the uploaded effect/statistical support with existing GBM target evidence and confidence. It prioritizes follow-up inside your processed result; it is not a new differential-expression test."
        )
    elif step == 2:
        left, right = st.columns(2)
        with left:
            with st.container(border=True):
                st.markdown("**STRING pathway enrichment**")
                st.write("Upregulated and downregulated programs are analyzed separately.")
        with right:
            with st.container(border=True):
                st.markdown("**L1000 perturbational reversal**")
                st.write("Compounds predicted to oppose the uploaded molecular state are surfaced as hypotheses.")
        _note(
            "L1000/LINCS evidence comes from historical perturbational cell-line data. Reversal candidates and combinations are experimental hypotheses—not GBM efficacy, BBB, safety, or synergy evidence."
        )
    else:
        with st.container(border=True):
            st.markdown("**Result dossier export (JSON)**")
            st.write("Input summary · prioritized genes · pathway enrichment · perturbational reversal · software version")
        _note(
            "Keep your experiment's original statistical model as the authoritative analysis. This workflow adds GBM-specific evidence context and traceable hypothesis prioritization around those processed results."
        )

    _nav(feature, step, titles)


@st.dialog(
    "Gene Set Comparison Walkthrough",
    width="large",
    dismissible=True,
    icon=":material/slideshow:",
)
def show_comparison_walkthrough() -> None:
    feature = "comparison"
    titles = [
        "Build a Focused Comparison",
        "Compare Evidence Profiles",
        "Choose the Next Target to Investigate",
    ]
    step = _intro(feature, titles)

    if step == 0:
        st.markdown("**Example input:** `EGFR, PTEN, TP53, CDK4`")
        st.caption("The public workflow compares up to 6 genes per run to keep live-source and hosting pressure bounded.")
        _note(
            "Every gene is passed through the same production dossier architecture. This is a side-by-side prioritization workflow, not a separate scoring model."
        )
    elif step == 1:
        st.dataframe(
            [
                {"Gene": "EGFR", "Priority": 64, "Coverage": "83%", "Confidence": "Moderate", "Model Relevance": "Limited"},
                {"Gene": "CDK4", "Priority": 47, "Coverage": "79%", "Confidence": "Moderate", "Model Relevance": "Limited"},
                {"Gene": "PTEN", "Priority": 46, "Coverage": "76%", "Confidence": "Moderate", "Model Relevance": "Limited"},
            ],
            width="stretch",
            hide_index=True,
            height=143,
        )
        _note(
            "Read Priority together with Coverage, Confidence, functional selectivity, human validation, trial context and model relevance. A small score difference alone should not decide the experiment."
        )
    else:
        left, right = st.columns(2)
        with left:
            st.markdown("**Use comparison to ask**")
            st.markdown("- Which target has the strongest supported evidence?\n- Which result is best replicated?\n- Which target has the most informative unresolved gap?")
        with right:
            st.markdown("**Do not use it as**")
            st.markdown("- A clinical ranking\n- A probability of therapeutic success\n- A substitute for mechanistic validation")
        _note(
            "The best next target is often the one where a feasible experiment can reduce the most consequential uncertainty—not simply the gene with the highest scalar score."
        )

    _nav(feature, step, titles)


def _launch(feature: str) -> None:
    _reset(feature)
    if feature == "gene":
        show_gene_walkthrough()
    elif feature == "pair":
        show_pair_walkthrough()
    elif feature == "researcher":
        show_researcher_walkthrough()
    elif feature == "comparison":
        show_comparison_walkthrough()
    else:  # defensive programming for future UI additions
        raise ValueError(f"Unknown walkthrough feature: {feature}")


WORKFLOW_TAB_TO_FEATURE = {
    "Gene Analysis": "gene",
    "Target Pair Analysis": "pair",
    "Researcher Data": "researcher",
    "Gene Set Comparison": "comparison",
}


def on_workflow_tab_change() -> None:
    """Queue the selected workflow's walkthrough whenever its tab is opened."""
    label = st.session_state.get("research_workflow_tabs")
    feature = WORKFLOW_TAB_TO_FEATURE.get(label)
    if feature:
        st.session_state["pending_feature_walkthrough"] = feature


def maybe_show_active_walkthrough() -> None:
    """Show a walkthrough queued by a top-level workflow-tab selection."""
    feature = st.session_state.pop("pending_feature_walkthrough", None)
    if feature:
        _launch(feature)


def render_feature_header(title: str, feature: str, caption: str | None = None) -> None:
    """Render a compact section header with a feature-local walkthrough launcher."""
    with st.container(horizontal=True, vertical_alignment="center", gap="xxsmall"):
        st.markdown(
            f"<div style='font-size:1.5rem;font-weight:650;line-height:1.25;letter-spacing:-.01em;"
            f"margin:0;padding:0;'>{title}</div>",
            unsafe_allow_html=True,
            width="content",
        )
        if st.button(
            ":material/info:",
            help=f"Open {title} walkthrough",
            key=f"open_{feature}_walkthrough",
            type="tertiary",
        ):
            _launch(feature)
    if caption:
        st.caption(caption)


def maybe_show_initial_gene_walkthrough() -> None:
    """Preserve the first-use Gene Analysis tour without forcing other tours."""
    if "gene_walkthrough_seen" not in st.session_state:
        st.session_state["gene_walkthrough_seen"] = True
        _reset("gene")
        show_gene_walkthrough()
