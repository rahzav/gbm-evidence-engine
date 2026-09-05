from pathlib import Path
import re

path = Path("streamlit_app_v5.py")
text = path.read_text()

help_block = '''HELP = {
    "target_priority_score": "A 0–100 research-prioritization score integrating supported GBM evidence across multiple sources. It is not a measure of clinical benefit or causality.",
    "evidence_coverage": "The percentage of the scored evidence model supported by usable data for this gene. Missing sources reduce coverage rather than counting as negative evidence.",
    "depmap": "DepMap uses CRISPR loss-of-function screens to estimate whether cancer models depend on a gene for growth or survival.",
    "chronos": "DepMap Chronos gene-effect score from CRISPR screens. More negative values generally indicate stronger dependency on the gene.",
    "selectivity": "The difference in dependency between the selected GBM models and the comparison cancer-model set. A larger positive value supports greater GBM selectivity in this analysis.",
    "pan_essential": "A pan-essential gene is required by many cell types, which can make a dependency less specific to GBM.",
    "ivy_gap": "The Ivy Glioblastoma Atlas Project measures gene expression in laser-microdissected anatomic regions of human GBM tumors.",
    "lmd_samples": "Laser-microdissected samples isolated from defined microscopic regions of glioblastoma tissue.",
    "cgga": "The Chinese Glioma Genome Atlas provides independent patient cohorts used here to test gene-expression associations with survival in strict GBM subsets.",
    "pooled_hr": "Meta-analytic hazard ratio per 1-standard-deviation increase in gene expression. Values above 1 indicate higher observed hazard and values below 1 lower observed hazard; this is association, not causation.",
    "glass": "GLASS is the Glioma Longitudinal Analysis Consortium. Paired primary and recurrent tumors are used to examine expression changes at recurrence.",
    "tissue_specificity": "How restricted the gene's expression is across normal human tissues in the Human Protein Atlas.",
    "brain_single_nuclei": "How specifically the gene is expressed across normal brain cell populations measured by single-nucleus RNA sequencing.",
    "network": "STRING protein-association networks show experimentally supported or curated functional relationships around the target. They support mechanism generation but do not establish causality.",
    "gbmap": "GBmap is an integrated glioblastoma single-cell and spatial reference atlas used to place a gene in cellular and tumor-state context.",
    "literature_count": "The number of Europe PMC records matching the gene together with glioblastoma/GBM terms. It reflects literature volume, not evidence quality by itself.",
    "bbb": "The blood–brain barrier (BBB) limits entry of many compounds into brain tissue and is a key consideration for GBM drug development.",
    "b3db_matches": "The number of checked compounds with matching records in B3DB, a database of experimentally measured blood–brain barrier permeability.",
    "bbb_positive": "The number of matching B3DB records labeled BBB-positive/permeable. A missing record is not evidence that a compound cannot cross the BBB.",
}
'''
text, n = re.subn(r'HELP = \{.*?\}\n+(?=@st\.cache_data)', help_block + '\n', text, count=1, flags=re.S)
if n != 1:
    raise SystemExit("Could not replace HELP dictionary")

text = re.sub(r',\s*help=HELP\["[^"]+"\]', '', text)
text = re.sub(r'\n\s*help=HELP\["[^"]+"\],', '', text)

section_help = {
    'st.subheader("DepMap Functional Dependency", anchor=False)': 'st.subheader("DepMap Functional Dependency", help=HELP["depmap"], anchor=False)',
    'st.subheader("Ivy GAP Spatial Expression", anchor=False)': 'st.subheader("Ivy GAP Spatial Expression", help=HELP["ivy_gap"], anchor=False)',
    'st.subheader("CGGA External Cohort Validation", anchor=False)': 'st.subheader("CGGA External Cohort Validation", help=HELP["cgga"], anchor=False)',
    'st.subheader("GLASS Longitudinal Validation", anchor=False)': 'st.subheader("GLASS Longitudinal Validation", help=HELP["glass"], anchor=False)',
    'st.subheader("Interaction Network and Pathways", anchor=False)': 'st.subheader("Interaction Network and Pathways", help=HELP["network"], anchor=False)',
    'st.subheader("GBmap Single-Cell and Spatial Reference", anchor=False)': 'st.subheader("GBmap Single-Cell and Spatial Reference", help=HELP["gbmap"], anchor=False)',
    'st.subheader("Blood-Brain Barrier Evidence", anchor=False)': 'st.subheader("Blood-Brain Barrier Evidence", help=HELP["bbb"], anchor=False)',
}
for old, new in section_help.items():
    if old in text:
        text = text.replace(old, new)

metric_help = {
    'm1.metric("Target Priority Score", "N/A" if score.overall is None else f"{score.overall}/100")': 'm1.metric("Target Priority Score", "N/A" if score.overall is None else f"{score.overall}/100", help=HELP["target_priority_score"])',
    'm2.metric("Evidence Coverage", f"{score.evidence_coverage_pct}%")': 'm2.metric("Evidence Coverage", f"{score.evidence_coverage_pct}%", help=HELP["evidence_coverage"])',
    'd2.metric("Median GBM Chronos Score", num(dep.get("median_effect_gbm"), 2))': 'd2.metric("Median GBM Chronos Score", num(dep.get("median_effect_gbm"), 2), help=HELP["chronos"])',
    'd3.metric("Selectivity Difference", num(dep.get("median_selectivity_delta"), 2))': 'd3.metric("Selectivity Difference", num(dep.get("median_selectivity_delta"), 2), help=HELP["selectivity"])',
    'i1.metric("LMD Samples", ivy.get("n_samples"))': 'i1.metric("LMD Samples", ivy.get("n_samples"), help=HELP["lmd_samples"])',
    'c2.metric("Pooled HR per 1 SD", num((meta or {}).get("pooled_hr"), 2))': 'c2.metric("Pooled HR per 1 SD", num((meta or {}).get("pooled_hr"), 2), help=HELP["pooled_hr"])',
    'h1.metric("Tissue Specificity", hpa.get("tissue_specificity") or "N/A")': 'h1.metric("Tissue Specificity", hpa.get("tissue_specificity") or "N/A", help=HELP["tissue_specificity"])',
    'h2.metric("Brain Single-Nuclei Specificity", hpa.get("single_nuclei_brain_specificity") or "N/A")': 'h2.metric("Brain Single-Nuclei Specificity", hpa.get("single_nuclei_brain_specificity") or "N/A", help=HELP["brain_single_nuclei"])',
    'st.metric("GBM Literature Co-Mentions", lit.get("hit_count", 0) if lit.get("ok") else "N/A")': 'st.metric("GBM Literature Co-Mentions", lit.get("hit_count", 0) if lit.get("ok") else "N/A", help=HELP["literature_count"])',
    'b2.metric("B3DB Matches", bbb.get("matched_count", 0))': 'b2.metric("B3DB Matches", bbb.get("matched_count", 0), help=HELP["b3db_matches"])',
    'b3.metric("BBB+ Records", bbb.get("bbb_positive_count", 0))': 'b3.metric("BBB+ Records", bbb.get("bbb_positive_count", 0), help=HELP["bbb_positive"])',
}
for old, new in metric_help.items():
    if old not in text:
        raise SystemExit(f"Missing metric target: {old}")
    text = text.replace(old, new)

old_pan = '''        st.caption(
            f"GBM definition: {dep.get('gbm_definition')}. Pan-essential classification: {'Yes' if dep.get('pan_essential') else 'No'}."
        )'''
new_pan = '''        st.caption(
            f"GBM definition: {dep.get('gbm_definition')}. Pan-essential classification: {'Yes' if dep.get('pan_essential') else 'No'}.",
            help=HELP["pan_essential"],
        )'''
if old_pan in text:
    text = text.replace(old_pan, new_pan)

nav = '''    section_space(0.4)
    st.caption(
        "Start with Overview. Use Evidence for source-derived biology, Translation for therapeutic context, "
        "Interpretation & Next Steps for tool-generated synthesis, and Sources & Export for the full evidence record."
    )

'''
text = text.replace(nav, '    section_space(0.4)\n\n')
text = text.replace(
    'st.caption("Source-derived molecular and human evidence. Tool-generated recommendations are kept out of this workspace.")',
    'st.caption("Source-derived molecular and human evidence.")',
)
text = text.replace(
    'st.caption(f"{score.label}. {score.caveat}")',
    'st.caption(f"{score.label}. Research prioritization only; not a measure of causality or clinical benefit.")',
)

text = re.sub(r'\n\s*help=HELP\["gene_symbol"\],', '', text)
text = re.sub(r'\n\s*help=HELP\["analyze"\],', '', text)
text = text.replace('st.subheader("Evidence Consistency", help=HELP["evidence_consistency"], anchor=False)', 'st.subheader("Evidence Consistency", anchor=False)')
text = text.replace('st.subheader("Evidence Gaps", help=HELP["evidence_gaps"], anchor=False)', 'st.subheader("Evidence Gaps", anchor=False)')
text = text.replace('st.subheader("Potential Validation Studies", help=HELP["validation_studies"], anchor=False)', 'st.subheader("Potential Validation Studies", anchor=False)')
text = re.sub(r'\n\s*st\.caption\("How the overall research-prioritization score is assembled\."[^\n]*\)', '', text)
text = re.sub(r'\n\s*st\.caption\("Auditable claims used by the profile\."[^\n]*\)', '', text)

text = text.replace(
    '"The Target Priority Score retains the validated V4 evidence model: TCGA genomic signal, Open Targets disease relevance and druggability, clinical translation, literature context, DepMap functional dependency, Ivy GAP spatial expression, CGGA external human validation, and clinically verified GLASS longitudinal recurrence when available. Missing sources reduce evidence coverage rather than becoming negative biological evidence."',
    '"The Target Priority Score integrates TCGA genomic signal, Open Targets disease relevance and druggability, clinical translation, literature context, DepMap functional dependency, Ivy GAP spatial expression, CGGA external human validation, and GLASS longitudinal recurrence when available. Missing sources reduce evidence coverage rather than being treated as negative evidence."',
)
text = text.replace(
    '"V5 adds canonical gene identity from MyGene.info, normal-tissue and brain context from the Human Protein Atlas, high-confidence interaction and pathway context from STRING, and experimental blood-brain barrier records from B3DB. These layers are displayed separately and do not change the Target Priority Score because their interpretation depends on experimental modality and research question."',
    '"Canonical gene identity is resolved with MyGene.info, normal-tissue and brain context is provided by the Human Protein Atlas, interaction and pathway context comes from STRING, and experimental blood-brain barrier records come from B3DB. These contextual layers are displayed separately from the Target Priority Score."',
)
text = text.replace(
    '"The analysis links directly to the public GBmap IDH-wildtype glioblastoma single-cell and spatial reference collection. Quantitative GBmap expression is not incorporated into the priority score unless it can be analyzed reproducibly at gene level without requiring the application to download the full atlas during each query."',
    '"GBmap provides a public IDH-wildtype glioblastoma single-cell and spatial reference for cellular and tumor-state context. GBmap reference information is presented separately from the Target Priority Score."',
)

if 'def display_status(value):' not in text:
    marker = 'def section_space(size: float = 1.0):\n    st.markdown(f"<div style=\'height:{size}rem\'></div>", unsafe_allow_html=True)\n\n\n'
    replacement = marker + '''def display_status(value):
    if value is None:
        return "Unavailable"
    raw = str(value).strip().replace("_", " ")
    mapping = {
        "ok": "Available",
        "available": "Available",
        "credentials required": "Credentials required",
        "unavailable": "Unavailable",
    }
    return mapping.get(raw.lower(), raw[:1].upper() + raw[1:])


'''
    if marker not in text:
        raise SystemExit("Could not insert status formatter")
    text = text.replace(marker, replacement, 1)

text = text.replace(
    '{"Data Source": str(name).replace("_", " ").title(), "Status": status}',
    '{"Data Source": str(name).replace("_", " ").title(), "Status": display_status(status)}',
)

required_absent = [
    'Start with Overview.',
    'Tool-generated recommendations are kept out of this workspace.',
    'retains the validated V4 evidence model',
    'V5 adds canonical gene identity',
    'requiring the application to download the full atlas',
    'help=HELP["gene_symbol"]',
    'help=HELP["analyze"]',
    'help=HELP["tcga_mutation"]',
    'help=HELP["tcga_amplification"]',
    'help=HELP["tcga_deletion"]',
    'help=HELP["open_targets_score"]',
    'help=HELP["gene_identity"]',
]
for item in required_absent:
    if item in text:
        raise SystemExit(f"Cleanup incomplete: {item}")

path.write_text(text)
print("professional UX cleanup applied")
