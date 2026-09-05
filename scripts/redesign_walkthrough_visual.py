from pathlib import Path

path = Path("streamlit_app_v5.py")
text = path.read_text()

start = text.index("def _move_walkthrough(delta: int):")
end = text.index('with st.container(horizontal=True, vertical_alignment="center", gap="xxsmall"):', start)

replacement = r'''def _move_walkthrough(delta: int):
    current = int(st.session_state.get("walkthrough_step", 0))
    st.session_state["walkthrough_step"] = max(0, min(6, current + delta))


def _walkthrough_note(text: str):
    st.markdown(
        f"<div style='border:1px solid rgba(128,128,128,.24);border-radius:.7rem;padding:.8rem 1rem;margin-top:.55rem;line-height:1.45;'>{text}</div>",
        unsafe_allow_html=True,
    )


@st.dialog(
    "GBM Gene Analysis Walkthrough",
    width="large",
    dismissible=True,
    icon=":material/slideshow:",
    on_dismiss=_close_walkthrough,
)
def show_walkthrough():
    step = max(0, min(6, int(st.session_state.get("walkthrough_step", 0))))
    titles = [
        "Priority Score & Evidence Coverage",
        "Genomic Evidence",
        "Functional & Spatial Evidence",
        "Human Validation",
        "Biological Context",
        "Literature & Translation",
        "Evidence Record & Research Gaps",
    ]

    st.caption(f"{step + 1} of {len(titles)}  ·  Illustrative preview")
    st.markdown(f"## {titles[step]}")

    if step == 0:
        m1, m2 = st.columns(2)
        m1.metric("Target Priority Score", "64.2 / 100")
        m2.metric("Evidence Coverage", "82.5%")
        st.dataframe(
            [
                {"Evidence Dimension": "Genomic", "Score": 72, "Weight": "16.9%"},
                {"Evidence Dimension": "Functional Dependency", "Score": 58, "Weight": "15.0%"},
                {"Evidence Dimension": "Human Validation", "Score": 66, "Weight": "7.5%"},
                {"Evidence Dimension": "Recurrence", "Score": 41, "Weight": "6.0%"},
            ],
            use_container_width=True,
            hide_index=True,
            height=176,
        )
        _walkthrough_note(
            "<b>Priority Score</b> is the weighted research-priority result. "
            "<b>Evidence Coverage</b> is the share of the weighted model supported by usable data. "
            "Missing data lowers coverage rather than acting as negative evidence."
        )

    elif step == 1:
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Mutation Frequency", "8.2%")
        g2.metric("Amplification Frequency", "36.1%")
        g3.metric("Deep Deletion Frequency", "1.4%")
        g4.metric("Open Targets Score", "0.82")
        with st.container(border=True):
            st.markdown("**Gene Identity**")
            st.dataframe(
                [{"Canonical Symbol": "GENE", "Ensembl": "ENSG…", "Entrez": "####", "Matched By": "symbol"}],
                use_container_width=True,
                hide_index=True,
            )
        _walkthrough_note(
            "TCGA frequencies describe how often specific alterations occur in GBM tumors. "
            "The Open Targets score summarizes broader target–disease evidence, so it is not an alteration frequency."
        )

    elif step == 2:
        d1, d2, d3 = st.columns(3)
        d1.metric("Median GBM Chronos", "-0.42")
        d2.metric("Selectivity Difference", "+0.18")
        d3.metric("One-Sided p Value", "0.03")
        st.caption("Pan-essential classification: No")
        st.markdown("**Ivy GAP spatial expression**")
        st.dataframe(
            [
                {"Anatomic Zone": "Cellular Tumor", "Median Expression": 5.8, "n": 38},
                {"Anatomic Zone": "Leading Edge", "Median Expression": 3.1, "n": 31},
                {"Anatomic Zone": "Microvascular Proliferation", "Median Expression": 6.4, "n": 27},
            ],
            use_container_width=True,
            hide_index=True,
            height=143,
        )
        _walkthrough_note(
            "More negative <b>Chronos</b> values indicate stronger CRISPR dependency. "
            "A positive <b>Selectivity Difference</b> means the GBM model set is more dependent than the comparison set. "
            "Ivy GAP shows whether expression differs across anatomic tumor regions."
        )

    elif step == 3:
        c1, c2, c3 = st.columns(3)
        c1.metric("Pooled HR per 1 SD", "1.31")
        c2.metric("Pooled p Value", "0.01")
        c3.metric("I²", "22%")
        st.dataframe(
            [
                {"CGGA Cohort": "Cohort A", "n": 188, "HR per 1 SD": 1.27, "p Value": 0.04},
                {"CGGA Cohort": "Cohort B", "n": 224, "HR per 1 SD": 1.35, "p Value": 0.02},
            ],
            use_container_width=True,
            hide_index=True,
            height=108,
        )
        x1, x2, x3 = st.columns(3)
        x1.metric("Primary/Recurrent Pairs", "44")
        x2.metric("Median Recurrence Change", "+0.18")
        x3.metric("Paired p Value", "0.04")
        _walkthrough_note(
            "In CGGA, <b>HR &gt; 1</b> corresponds to higher observed hazard as expression increases and <b>HR &lt; 1</b> to lower observed hazard. "
            "<b>I²</b> measures between-cohort disagreement. GLASS recurrence change is calculated within matched primary/recurrent tumors."
        )

    elif step == 4:
        hpa_col, string_col, gbmap_col = st.columns(3)
        with hpa_col:
            with st.container(border=True):
                st.markdown("**Human Protein Atlas**")
                st.metric("Tissue Specificity", "Low")
                st.caption("Normal brain expression context")
        with string_col:
            with st.container(border=True):
                st.markdown("**STRING**")
                st.write("ERBB2  ·  GRB2  ·  PIK3CA")
                st.caption("Network partners + pathway enrichment")
        with gbmap_col:
            with st.container(border=True):
                st.markdown("**GBmap**")
                st.write("Single-cell + spatial reference")
                st.caption("GBM cellular and tumor-state context")
        _walkthrough_note(
            "These layers provide biological context rather than another priority score: normal-tissue expression, interaction-network relationships, and GBM single-cell/spatial reference context."
        )

    elif step == 5:
        left, right = st.columns([1.05, 1.2])
        with left:
            st.metric("GBM Literature Co-Mentions", "1,240")
            with st.container(border=True):
                st.markdown("**Clickable publication title ↗**")
                st.caption("Journal · 2025 · PMID · DOI")
        with right:
            t1, t2 = st.columns(2)
            t1.metric("Target-Directed Candidates", "82")
            t2.metric("Highest GBM Trial Phase", "2")
            b1, b2 = st.columns(2)
            b1.metric("B3DB Matches", "5")
            b2.metric("BBB+ Records", "3")
        _walkthrough_note(
            "Literature co-mentions measure publication volume. Candidate count, clinical-trial phase, and BBB records describe different parts of translational maturity and are displayed separately."
        )

    else:
        with st.container(border=True):
            st.markdown("**Example evidence record**")
            st.write("Higher expression is associated with survival in an independent GBM cohort.")
            st.caption("Pooled HR: 1.31  ·  p = 0.01  ·  n = 412")
            st.caption("Source: CGGA  ·  Confidence: High")
        gap_col, validation_col = st.columns(2)
        with gap_col:
            with st.container(border=True):
                st.markdown("**Evidence Gap**")
                st.write("Longitudinal recurrence evidence unavailable")
        with validation_col:
            with st.container(border=True):
                st.markdown("**Potential Validation Study**")
                st.write("Paired primary/recurrent expression analysis")
        st.caption("Exports preserve the complete evidence record in JSON and a concise Markdown summary.")
        _walkthrough_note(
            "<b>Evidence Confidence</b> belongs to an individual claim and is separate from the Target Priority Score. "
            "Evidence gaps and proposed validation studies remain visually separated from retrieved evidence."
        )

    st.markdown(
        "<div style='text-align:center;letter-spacing:.28rem;opacity:.6;margin:.45rem 0 .1rem;'>"
        + " ".join("●" if i == step else "○" for i in range(len(titles)))
        + "</div>",
        unsafe_allow_html=True,
    )

    back_col, middle_col, next_col = st.columns([1.25, 4.5, 1.25], vertical_alignment="center")
    with back_col:
        if step > 0:
            st.button(
                "← Previous",
                key=f"walkthrough_prev_{step}",
                use_container_width=True,
                on_click=_move_walkthrough,
                args=(-1,),
            )
    with next_col:
        if step < len(titles) - 1:
            st.button(
                "Next →",
                key=f"walkthrough_next_{step}",
                type="primary",
                use_container_width=True,
                on_click=_move_walkthrough,
                args=(1,),
            )
        elif st.button("Close", type="primary", use_container_width=True):
            _close_walkthrough()
            st.rerun()


'''

text = text[:start] + replacement + text[end:]
path.write_text(text)
