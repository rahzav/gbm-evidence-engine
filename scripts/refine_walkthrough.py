from pathlib import Path

path = Path("streamlit_app_v5.py")
text = path.read_text()

start = text.index("def _move_walkthrough(delta: int):")
end_marker = 'st.caption("Integrated gene-level evidence synthesis for glioblastoma research.")\n'
end = text.index(end_marker, start) + len(end_marker)

replacement = r'''def _move_walkthrough(delta: int):
    current = int(st.session_state.get("walkthrough_step", 0))
    st.session_state["walkthrough_step"] = max(0, min(7, current + delta))


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
            "title": "Target Priority Score and Evidence Coverage",
            "intro": "These two values summarize different parts of the profile and are most informative when read together.",
            "sections": [
                (
                    "Target Priority Score",
                    [
                        "A 0–100 comparative research-priority score calculated from the weighted evidence dimensions that are available for the gene.",
                        "The overall value can be driven by very different evidence patterns. The Priority Score Composition table shows the score, weight, source, and rationale for each contributing dimension.",
                        "The priority classification is a label derived from the overall score; it is not a separate measurement.",
                    ],
                ),
                (
                    "Evidence Coverage",
                    [
                        "The percentage of the weighted scoring model supported by usable data for the current gene.",
                        "Missing sources reduce coverage rather than lowering a biological score. This keeps unavailable evidence separate from negative evidence.",
                        "Two genes with similar Target Priority Scores can therefore have very different evidence depth.",
                    ],
                ),
            ],
        },
        {
            "title": "Evidence Summary and Evidence Consistency",
            "intro": "These outputs compress the profile into cross-source findings while preserving disagreement between evidence types.",
            "sections": [
                (
                    "Evidence Summary",
                    [
                        "Highlights the strongest findings that can be stated directly from the assembled profile.",
                        "A summary item may reflect genomic, functional, spatial, human-validation, tissue-context, literature, or translational evidence depending on what is strongest for the gene.",
                    ],
                ),
                (
                    "Evidence Consistency",
                    [
                        "Flags meaningful agreement, discordance, or missing dimensions across the evidence base.",
                        "Different evidence layers answer different biological questions. For example, frequent genomic alteration and weak CRISPR dependency can coexist without either result being incorrect.",
                        "The consistency output is meant to expose those relationships rather than force every source into a single narrative.",
                    ],
                ),
            ],
        },
        {
            "title": "Genomic Evidence and Disease Association",
            "intro": "This section separates direct tumor alterations from broader target–disease association evidence.",
            "sections": [
                (
                    "TCGA alteration frequencies",
                    [
                        "Mutation Frequency is the fraction of profiled GBM tumors with a detected sequence mutation in the gene.",
                        "Amplification Frequency reflects high-level copy-number gain; Deep Deletion Frequency reflects high-level copy-number loss.",
                        "These values describe how often an alteration occurs. They do not indicate whether the altered gene is required for tumor survival.",
                    ],
                ),
                (
                    "Open Targets Association Score",
                    [
                        "A target–disease evidence score assembled by Open Targets from multiple evidence classes.",
                        "It is broader than TCGA alteration frequency, so the two values are not expected to move together.",
                    ],
                ),
                (
                    "Gene Identity",
                    [
                        "Confirms the canonical symbol, approved name, Ensembl ID, Entrez ID, and alias mapping used for downstream source matching.",
                    ],
                ),
            ],
        },
        {
            "title": "Functional Dependency and Spatial Expression",
            "intro": "These tables address two different questions: whether GBM models depend on the gene and whether expression varies across tumor anatomy.",
            "sections": [
                (
                    "DepMap / Chronos",
                    [
                        "Chronos estimates gene effect from CRISPR loss-of-function screens. More negative values generally indicate stronger dependency.",
                        "The displayed median summarizes the strict GBM model set rather than a single cell line.",
                        "Pan-essential classification indicates that a gene is broadly required across many cancer models, which makes a dependency less GBM-specific.",
                    ],
                ),
                (
                    "Selectivity Difference and p value",
                    [
                        "Selectivity Difference compares the GBM dependency distribution with the broader comparison-model distribution.",
                        "A positive difference supports stronger dependency in the GBM set under this analysis; a negative difference indicates the opposite pattern.",
                        "The one-sided p value quantifies the statistical evidence for that directional comparison.",
                    ],
                ),
                (
                    "Ivy GAP",
                    [
                        "LMD Samples are laser-microdissected tumor regions with region-specific expression measurements.",
                        "Highest-Expression Anatomic Zone identifies the region with the largest median expression for the gene.",
                        "Median Expression Range describes the spread between regional medians, while the Kruskal p value tests whether the regional distributions differ overall.",
                    ],
                ),
            ],
        },
        {
            "title": "Human Validation: CGGA and GLASS",
            "intro": "These datasets add patient-level evidence that is distinct from cell-line dependency and cross-sectional tumor genomics.",
            "sections": [
                (
                    "CGGA survival association",
                    [
                        "Each cohort estimates the association between gene expression and survival within a strict GBM subset.",
                        "HR per 1 SD is the hazard ratio associated with a one-standard-deviation increase in expression. HR > 1 corresponds to higher observed hazard; HR < 1 corresponds to lower observed hazard.",
                        "The pooled HR combines usable cohorts. The pooled p value reflects evidence for the combined association.",
                        "I² describes heterogeneity between cohort estimates: larger values indicate greater between-cohort inconsistency.",
                    ],
                ),
                (
                    "GLASS recurrence analysis",
                    [
                        "Primary/Recurrent Pairs is the number of matched patients contributing paired tumor measurements.",
                        "Median Recurrence Change summarizes the within-patient expression shift from primary tumor to recurrence.",
                        "The paired p value tests whether the observed within-patient changes are systematically different from zero.",
                    ],
                ),
            ],
        },
        {
            "title": "Normal Tissue, Network, and GBM Cellular Context",
            "intro": "These layers explain where the gene sits biologically without adding another score to the Target Priority Score.",
            "sections": [
                (
                    "Human Protein Atlas",
                    [
                        "Tissue Specificity summarizes how restricted expression is across normal human tissues.",
                        "Brain single-nuclei specificity and displayed brain-region expression provide normal-brain context for the target.",
                        "These measurements describe expression context; they are not direct measurements of therapeutic safety.",
                    ],
                ),
                (
                    "STRING network",
                    [
                        "Partners are high-confidence functional or physical associations surrounding the target.",
                        "Network enrichment summarizes biological processes or pathways that are overrepresented among those associated proteins.",
                        "Network membership indicates biological context and does not by itself establish a causal mechanism.",
                    ],
                ),
                (
                    "GBmap reference",
                    [
                        "GBmap is a GBM single-cell and spatial reference used here to provide cellular and tumor-state context.",
                        "The current profile links to the reference collection so the gene can be examined in the underlying atlas context.",
                    ],
                ),
            ],
        },
        {
            "title": "Literature, Target-Directed Candidates, Trials, and BBB Evidence",
            "intro": "These outputs describe how mature the existing research and translational landscape is around the target.",
            "sections": [
                (
                    "Literature",
                    [
                        "GBM Literature Co-Mentions is the number of Europe PMC records matching the gene with GBM-related terms.",
                        "The count reflects literature volume rather than study quality or direction of evidence.",
                        "Publication titles are linked directly to the available DOI, PubMed, PMC, or Europe PMC record.",
                    ],
                ),
                (
                    "Target-Directed Candidates and Clinical Trials",
                    [
                        "Target-Directed Candidates are compounds associated with the target in Open Targets.",
                        "Matching GBM Trials counts ClinicalTrials.gov records that meet the GBM-target matching logic, while Highest Matching GBM Trial Phase summarizes the most advanced matched phase.",
                        "Candidate count and trial phase measure different stages of translational maturity and are displayed separately.",
                    ],
                ),
                (
                    "BBB / B3DB",
                    [
                        "B3DB Matches are target-directed compounds with a corresponding experimental blood–brain barrier record in B3DB.",
                        "BBB+ Records are matches labeled permeable in the source dataset.",
                        "No B3DB match means permeability evidence was not found in that dataset; it is not equivalent to a BBB-negative result.",
                    ],
                ),
            ],
        },
        {
            "title": "Evidence Record, Evidence Gaps, Validation Studies, and Comparison",
            "intro": "These outputs expose the provenance behind the profile and the dimensions that remain unresolved.",
            "sections": [
                (
                    "Evidence Record",
                    [
                        "Stores source-level claims with statistics, sample size where available, source dataset, and evidence confidence.",
                        "Evidence confidence describes the support for an individual claim and is separate from the Target Priority Score.",
                        "Source Status shows which connected evidence sources were available for the current analysis.",
                    ],
                ),
                (
                    "Evidence Gaps and Potential Validation Studies",
                    [
                        "Evidence Gaps identify parts of the profile where evidence is missing, limited, or unresolved.",
                        "Potential Validation Studies translate those specific gaps into concrete experimental or analytical tests that could address the uncertainty.",
                        "They are presented separately from the retrieved evidence so the distinction remains visible in the interface.",
                    ],
                ),
                (
                    "Gene Set Comparison and Export",
                    [
                        "Gene Set Comparison applies the same scoring model to up to six genes and displays the resulting profiles side by side.",
                        "The JSON export preserves the complete profile structure; the Markdown export provides a compact research summary with linked publications.",
                    ],
                ),
            ],
        },
    ]

    step = max(0, min(len(steps) - 1, int(st.session_state.get("walkthrough_step", 0))))
    item = steps[step]

    st.progress((step + 1) / len(steps))
    st.caption(f"{step + 1} of {len(steps)}")
    st.markdown(f"## {item['title']}")
    st.write(item["intro"])

    for heading, points in item["sections"]:
        st.markdown(f"**{heading}**")
        for point in points:
            st.markdown(f"- {point}")

    st.markdown(
        "<div style='text-align:center; letter-spacing:0.32rem; opacity:0.65; margin:0.5rem 0 0.25rem 0;'>"
        + " ".join("●" if i == step else "○" for i in range(len(steps)))
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
        if step < len(steps) - 1:
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


title_col, info_col, spacer_col = st.columns(
    [3.45, 0.28, 8.27],
    gap="small",
    vertical_alignment="center",
)
with title_col:
    st.title("GBM Gene Analysis")
with info_col:
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
path.write_text(text)
