from pathlib import Path

path = Path('streamlit_app_v5.py')
text = path.read_text()

old_intro = '''st.title("GBM Gene Analysis")
st.caption(
    "Integrated gene-level evidence synthesis for glioblastoma research across genomic, functional, spatial, clinical, longitudinal, and literature datasets."
)
st.write(
    "Enter a gene symbol to generate a GBM-specific research profile. The analysis brings together tumor genomics, functional dependency, spatial expression, independent patient cohorts, clinical trials, literature, normal-tissue context, interaction networks, and available blood-brain barrier data for target-directed compounds."
)
st.caption("Note: Results are intended for research prioritization and hypothesis development, not clinical decision-making.")
'''

new_intro = '''@st.dialog("Using GBM Gene Analysis", width="large", dismissible=True)
def show_walkthrough():
    st.write(
        "GBM Gene Analysis organizes multi-source evidence into a focused workflow for evaluating genes in glioblastoma research."
    )
    st.markdown("**1. Analyze a gene**")
    st.write("Enter a gene symbol and press Enter or select **Analyze** to generate a research profile.")
    st.markdown("**2. Review the evidence summary**")
    st.write("Start with the priority score, evidence coverage, key findings, and evidence consistency.")
    st.markdown("**3. Examine supporting evidence**")
    st.write("Use **Evidence** for molecular and human data and **Translation** for therapeutic and clinical-development context.")
    st.markdown("**4. Plan follow-up work**")
    st.write("Use **Interpretation & Next Steps** to review evidence gaps and proposed validation studies.")
    st.markdown("**5. Verify and export**")
    st.write("Use **Sources & Export** for provenance, source status, and downloadable research profiles.")
    if st.button("Start analyzing", type="primary", use_container_width=True):
        st.rerun()


title_col, info_col, spacer_col = st.columns([5.0, 0.5, 6.5], vertical_alignment="center")
with title_col:
    st.title("GBM Gene Analysis")
with info_col:
    open_walkthrough = st.button(
        ":material/info:",
        help="Open walkthrough",
        key="open_walkthrough",
        type="tertiary",
    )

st.caption("Integrated gene-level evidence synthesis for glioblastoma research.")
st.write(
    "Enter a gene symbol to evaluate its relevance in GBM across complementary biological and translational evidence. Results are organized to support target prioritization, evidence review, and experimental planning."
)
st.caption("Note: Results are intended for research prioritization and hypothesis development, not clinical decision-making.")

if "walkthrough_seen" not in st.session_state:
    st.session_state["walkthrough_seen"] = True
    show_walkthrough()
elif open_walkthrough:
    show_walkthrough()
'''

if old_intro not in text:
    raise SystemExit('Intro block not found')
text = text.replace(old_intro, new_intro)

text = text.replace('st.markdown("### Research Snapshot")', 'st.markdown("### Evidence Summary")')
text = text.replace('st.caption("Tool-synthesized summary of the retrieved evidence.")', 'st.caption("Integrated summary of the strongest findings across available evidence.")')
text = text.replace(
    'st.caption(f"{score.label}. Research prioritization only; not a measure of causality or clinical benefit.")',
    'st.caption(f"{score.label}. Intended for comparative research prioritization.")',
)
text = text.replace(
    '''        st.caption(\n            "This workspace contains tool-generated research interpretation. These are prioritization aids and proposed validation steps, not new experimental observations."\n        )''',
    '''        st.caption(\n            "Integrated interpretation of evidence gaps and proposed validation studies to support experimental planning."\n        )''',
)

# Guard against old phrasing remaining in the visible UI.
for forbidden in [
    'brings together tumor genomics',
    'Research Snapshot',
    'Tool-synthesized',
    'tool-generated research interpretation',
    'Research prioritization only; not a measure of causality or clinical benefit',
]:
    if forbidden in text:
        raise SystemExit(f'Forbidden visible copy remains: {forbidden}')

path.write_text(text)
