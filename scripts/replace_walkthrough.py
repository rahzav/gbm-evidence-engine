from pathlib import Path

path = Path("streamlit_app_v5.py")
text = path.read_text()

start = text.index('@st.dialog("Using GBM Gene Analysis"')
end_marker = 'st.caption("Integrated gene-level evidence synthesis for glioblastoma research.")\n'
end = text.index(end_marker, start) + len(end_marker)

replacement = r'''def _close_walkthrough():
    st.session_state["walkthrough_open"] = False


def _open_walkthrough():
    st.session_state["walkthrough_step"] = 0
    st.session_state["walkthrough_open"] = True


def _move_walkthrough(delta: int):
    current = int(st.session_state.get("walkthrough_step", 0))
    st.session_state["walkthrough_step"] = max(0, min(9, current + delta))


@st.dialog(
    "GBM Gene Analysis Walkthrough",
    width="large",
    dismissible=True,
    icon=":material/explore:",
    on_dismiss=_close_walkthrough,
)
def show_walkthrough():
    steps = [
        {
            "title": "Start with the research question",
            "purpose": "Use Gene Analysis when you want to evaluate one target in depth. Enter an approved gene symbol and press Enter or select Analyze to build the profile.",
            "read": [
                "Begin with the Overview rather than reading every table from top to bottom.",
                "Treat the profile as a structured evidence review: first establish priority, then inspect the evidence dimensions that matter for your question.",
                "Use Gene Set Comparison when your decision is comparative rather than target-specific.",
            ],
            "use": "A typical workflow is Overview → relevant Evidence tabs → Translation → Interpretation & Next Steps → Sources & Export.",
        },
        {
            "title": "Overview: decide what deserves attention",
            "purpose": "The Overview is the fastest way to understand whether a gene warrants deeper investigation and where the strongest or weakest support lies.",
            "read": [
                "Target Priority Score summarizes the supported GBM evidence dimensions into a comparative research-priority score.",
                "Evidence Coverage shows how much of the weighted model has usable data. A high score with low coverage should be reviewed more cautiously than the same score with broad coverage.",
                "Evidence Summary highlights the strongest cross-source findings. Evidence Consistency flags agreement, discordance, or important missing dimensions.",
                "Open Priority Score Composition only when you need to see which evidence dimensions are driving the overall score.",
            ],
            "use": "Use this page to decide which evidence tabs require close inspection instead of reading every result equally.",
        },
        {
            "title": "Genomics & Identity: establish disease relevance",
            "purpose": "This section confirms the target identity and shows how strongly the gene is implicated by GBM genomic data.",
            "read": [
                "TCGA mutation, amplification, and deep-deletion frequencies show how often the gene is genomically altered in GBM.",
                "The Open Targets association score summarizes broader target–disease evidence and helps place the genomic signal in disease context.",
                "Gene Identity verifies the canonical symbol and identifiers so downstream evidence is mapped to the intended gene.",
            ],
            "use": "Use this section to answer whether the target is recurrently altered or otherwise associated with GBM before asking whether it is functionally important.",
        },
        {
            "title": "Functional & Spatial: test biological dependence and location",
            "purpose": "This section asks whether GBM models depend on the gene and whether its expression varies across anatomic tumor regions.",
            "read": [
                "In DepMap, more negative Chronos scores generally indicate stronger loss-of-function dependency.",
                "Selectivity Difference compares the GBM models with the broader cancer-model set and helps distinguish GBM-selective dependency from broadly essential biology.",
                "Ivy GAP shows expression across laser-microdissected GBM regions. Compare the highest-expression zone, the expression range, and the statistical evidence for regional differences.",
            ],
            "use": "Use these results together to distinguish a genomically interesting target from one supported by functional vulnerability or spatially restricted biology.",
        },
        {
            "title": "Human Validation: look for patient-level support",
            "purpose": "Human Validation tests whether the target's signal is reproduced in independent GBM patient cohorts and across disease progression.",
            "read": [
                "CGGA reports survival association across strict GBM cohorts. Hazard ratios above 1 indicate higher observed hazard with higher expression; values below 1 indicate lower observed hazard.",
                "Pooled estimates and consistency across cohorts matter more than any single cohort result.",
                "GLASS compares paired primary and recurrent tumors to show whether expression changes systematically at recurrence.",
            ],
            "use": "Use this section when deciding whether a cell-line or genomic signal is also visible in human disease and whether recurrence changes the target's relevance.",
        },
        {
            "title": "Tissue, Network & GBmap: place the target in biological context",
            "purpose": "These layers help determine where the target is normally expressed, what biological programs surround it, and how it may relate to GBM cellular states.",
            "read": [
                "Human Protein Atlas context shows normal-tissue and normal-brain expression, which is useful when considering biological selectivity and experimental interpretation.",
                "STRING identifies high-confidence functional partners and enriched processes around the target. Use these relationships to understand pathway context and candidate mechanisms.",
                "GBmap provides an external single-cell and spatial reference for examining the target across GBM cellular and tumor-state contexts.",
            ],
            "use": "Use this section to move from a gene-level signal toward a mechanistic model and to identify biological contexts that may explain heterogeneous responses.",
        },
        {
            "title": "Literature: move from evidence to rapid literature review",
            "purpose": "The Literature view helps you determine how extensively the target has already been studied in GBM and quickly inspect the most relevant publications.",
            "read": [
                "GBM Literature Co-Mentions reflects publication volume for the gene in GBM-related literature.",
                "Disease-context counts show where the literature is concentrated across related glioma contexts.",
                "Publication titles are clickable. Open the papers that align with the biological signal you are investigating rather than treating publication count as evidence strength by itself.",
            ],
            "use": "Use this section for literature triage: verify established findings, identify prior mechanisms, and determine whether the profile is surfacing a mature or comparatively underexplored direction.",
        },
        {
            "title": "Translation: assess tractability and clinical maturity",
            "purpose": "Translation connects the biological target to available compounds, GBM clinical trials, and blood–brain barrier evidence.",
            "read": [
                "Target-Directed Candidates shows whether compounds have been linked to the target through Open Targets.",
                "Clinical Trials shows whether those target-related strategies have reached GBM studies and the highest matching development phase.",
                "BBB Evidence checks available experimental permeability records for target-directed compounds, an important practical consideration for brain-tumor drug development.",
            ],
            "use": "Use this section to determine whether a biologically compelling target is already tractable, clinically mature, or limited by translational constraints.",
        },
        {
            "title": "Interpretation & Next Steps: convert evidence into a research plan",
            "purpose": "This section synthesizes unresolved evidence and proposes validation directions that can help prioritize follow-up work.",
            "read": [
                "Evidence Gaps identifies the dimensions where support is missing, weak, or incomplete.",
                "Potential Validation Studies translates those gaps into concrete experimental directions that could reduce uncertainty.",
                "Prioritize studies that address the most consequential uncertainty in the profile rather than automatically pursuing every suggested experiment.",
            ],
            "use": "Use this section after reviewing the supporting evidence to decide what experiment or dataset would most improve confidence in the target.",
        },
        {
            "title": "Verify, compare, and export",
            "purpose": "The final step is to verify provenance, compare targets when needed, and carry the analysis into the rest of your research workflow.",
            "read": [
                "Evidence Record provides source-level claims, statistics, sample sizes, and confidence for auditability.",
                "Source Status shows which evidence sources were available for the current analysis.",
                "Export provides the complete JSON research profile and a concise Markdown summary for downstream review or documentation.",
                "Gene Set Comparison ranks up to six targets under the same evidence model. Methods & Data Sources explains how the score and contextual layers are constructed.",
            ],
            "use": "Use these tools for reproducibility, lab-meeting preparation, target shortlisting, and documenting why one research direction was prioritized over another.",
        },
    ]

    step = max(0, min(len(steps) - 1, int(st.session_state.get("walkthrough_step", 0))))
    item = steps[step]

    st.progress((step + 1) / len(steps))
    st.caption(f"Step {step + 1} of {len(steps)}")
    st.markdown(f"## {item['title']}")
    st.write(item["purpose"])

    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True):
            st.markdown("**How to read this section**")
            for point in item["read"]:
                st.markdown(f"- {point}")
    with right:
        with st.container(border=True):
            st.markdown("**How to use it**")
            st.write(item["use"])

    st.markdown(
        "<div style='text-align:center; letter-spacing:0.32rem; opacity:0.65; margin:0.4rem 0 0.2rem 0;'>"
        + " ".join("●" if i == step else "○" for i in range(len(steps)))
        + "</div>",
        unsafe_allow_html=True,
    )

    back_col, middle_col, next_col = st.columns([1.2, 4.6, 1.2], vertical_alignment="center")
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
        if step < len(steps) - 1:
            st.button(
                "Next →",
                key=f"walkthrough_next_{step}",
                type="primary",
                use_container_width=True,
                on_click=_move_walkthrough,
                args=(1,),
            )
        elif st.button("Start analyzing", type="primary", use_container_width=True):
            _close_walkthrough()
            st.rerun()


with st.container(horizontal=True, vertical_alignment="center", gap="xxsmall"):
    st.title("GBM Gene Analysis")
    st.button(
        ":material/info:",
        help="Open walkthrough",
        key="open_walkthrough",
        type="tertiary",
        on_click=_open_walkthrough,
    )

st.caption("Integrated gene-level evidence synthesis for glioblastoma research.")
'''

text = text[:start] + replacement + text[end:]

# Replace the previous first-use/open logic with persistent modal state.
old_logic = '''if "walkthrough_seen" not in st.session_state:\n    st.session_state["walkthrough_seen"] = True\n    show_walkthrough()\nelif open_walkthrough:\n    show_walkthrough()\n'''
new_logic = '''if "walkthrough_seen" not in st.session_state:\n    st.session_state["walkthrough_seen"] = True\n    st.session_state["walkthrough_step"] = 0\n    st.session_state["walkthrough_open"] = True\n\nif st.session_state.get("walkthrough_open", False):\n    show_walkthrough()\n'''
if old_logic not in text:
    raise SystemExit("Previous walkthrough-open logic not found")
text = text.replace(old_logic, new_logic, 1)

path.write_text(text)
