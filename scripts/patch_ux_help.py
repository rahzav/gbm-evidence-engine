from pathlib import Path

path = Path("streamlit_app_v5.py")
text = path.read_text()


def replace_once(old: str, new: str):
    global text
    if old not in text:
        raise RuntimeError(f"Missing replacement target: {old[:120]!r}")
    text = text.replace(old, new, 1)


HELP_BLOCK = '''

HELP = {
    "gene_symbol": "Enter an official human gene symbol or a recognized alias, such as EGFR, PTEN, TP53, or CDK4.",
    "analyze": "Runs the full GBM evidence synthesis for the entered gene. Pressing Enter in the gene field does the same thing.",
    "target_priority_score": "A 0–100 research-prioritization heuristic combining supported GBM evidence across multiple sources. It is not a clinical probability or treatment recommendation.",
    "evidence_coverage": "The percentage of the scored evidence model backed by usable data for this gene. Missing sources lower coverage rather than counting as negative evidence.",
    "evidence_records": "The number of individual source-grounded evidence claims stored in this profile.",
    "active_trials": "Matching ClinicalTrials.gov glioblastoma studies currently classified as active.",
    "genomic_evidence": "Genomic evidence asks whether this gene is altered in human glioblastoma tumors and how strongly it is associated with GBM in curated target–disease resources.",
    "tcga_mutation": "The proportion of TCGA glioblastoma samples with a reported coding mutation in this gene.",
    "tcga_amplification": "The proportion of TCGA glioblastoma samples with high-level copy-number amplification of this gene.",
    "tcga_deletion": "The proportion of TCGA glioblastoma samples with a deep copy-number deletion of this gene.",
    "open_targets_score": "Open Targets' aggregated target–disease association score for this gene and glioblastoma. Higher values indicate stronger curated evidence of association, not treatment efficacy.",
    "gene_identity": "Canonical identifiers confirm that aliases and database records refer to the same human gene before evidence is combined.",
    "depmap": "DepMap uses CRISPR loss-of-function screens to test whether cancer models depend on a gene for growth or survival.",
    "strict_gbm_models": "The number of IDH-wildtype GBM models that passed this tool's strict inclusion criteria for the dependency analysis.",
    "chronos": "DepMap Chronos gene-effect score from CRISPR screens. More negative values generally indicate stronger dependency on the gene.",
    "selectivity": "How much stronger the dependency signal is in the selected GBM models relative to the comparison cancer-model set. In this tool, a larger positive difference supports greater GBM selectivity.",
    "one_sided_p": "A p value from a prespecified one-sided test asking whether the GBM dependency signal is stronger in the expected direction.",
    "pan_essential": "A pan-essential gene is required by many cell types. Strong pan-essentiality can make a dependency less specific to GBM.",
    "ivy_gap": "The Ivy Glioblastoma Atlas Project measures gene expression in laser-microdissected anatomic regions of human GBM tumors.",
    "lmd_samples": "Laser-microdissected samples isolated from defined microscopic regions of glioblastoma tissue.",
    "anatomic_zone": "The Ivy GAP tumor region with the highest median expression of the gene among the regions measured.",
    "expression_range": "The difference between the highest and lowest median expression values across the measured Ivy GAP anatomic regions.",
    "kruskal_p": "The p value from a Kruskal–Wallis test asking whether expression differs across the tumor regions. It does not identify which specific regions differ.",
    "cgga": "The Chinese Glioma Genome Atlas provides independent patient cohorts used here to test whether gene expression is associated with survival in strict GBM subsets.",
    "strict_cohorts": "The number of independent CGGA cohorts that met the tool's GBM-specific inclusion and data-quality requirements.",
    "pooled_hr": "Meta-analytic hazard ratio per 1-standard-deviation increase in gene expression. Values above 1 indicate higher observed hazard and values below 1 lower observed hazard; this is association, not causation.",
    "pooled_p": "The p value for the pooled survival association across the usable CGGA cohorts.",
    "glass": "GLASS is the Glioma Longitudinal Analysis Consortium. Paired primary and recurrent tumors are used to examine how expression changes when GBM returns.",
    "pairs": "The number of matched primary-versus-recurrent tumor pairs available for this gene's longitudinal comparison.",
    "recurrence_change": "The median within-patient change in gene expression from the primary tumor to the recurrent tumor.",
    "paired_p": "The p value from the paired statistical comparison of primary and recurrent expression.",
    "normal_tissue": "Normal-tissue context helps determine where the gene is normally expressed outside GBM. It is contextual evidence and is not a direct toxicity prediction.",
    "tissue_specificity": "How restricted the gene's expression is across normal human tissues in the Human Protein Atlas.",
    "brain_single_nuclei": "How specifically the gene is expressed across normal brain cell populations measured by single-nucleus RNA sequencing.",
    "normal_brain_expression": "The highest displayed normal-brain expression value across the Human Protein Atlas brain regions included by the tool.",
    "network": "STRING protein-association networks show experimentally supported or curated functional relationships around the target. They are useful for mechanism generation but do not prove causality.",
    "gbmap": "GBmap is an integrated glioblastoma single-cell and spatial reference atlas used to place a gene in cellular and tumor-state context.",
    "literature_count": "The number of Europe PMC records matching the gene together with glioblastoma/GBM terms. It measures literature volume, not evidence quality by itself.",
    "translation": "Translation summarizes whether target-directed compounds and GBM clinical studies already exist, plus available blood–brain barrier evidence.",
    "target_candidates": "Compounds reported by Open Targets to act on this target. This is target-level drug information and does not mean the compound is effective in GBM.",
    "trial_phase": "The highest clinical-development phase among matching GBM studies found for the target. A higher phase reflects development maturity, not proof of efficacy.",
    "matching_trials": "The number of ClinicalTrials.gov GBM studies matching this target or its associated intervention context.",
    "bbb": "The blood–brain barrier (BBB) limits entry of many compounds into brain tissue, making CNS exposure an important consideration for GBM drug development.",
    "candidates_checked": "The number of target-directed compounds checked against the available experimental BBB database records.",
    "b3db_matches": "The number of checked compounds with matching records in B3DB, a database of experimentally measured blood–brain barrier permeability.",
    "bbb_positive": "The number of matching B3DB records labeled BBB-positive/permeable. A missing record is not evidence that a compound cannot cross the BBB.",
    "evidence_consistency": "A cross-source check for agreement, discordance, and important limitations in the available evidence. Different evidence types answer different biological questions, so disagreement is interpreted cautiously.",
    "score_composition": "Shows which evidence dimensions contribute to the Target Priority Score, their weights, source, and rationale.",
    "evidence_gaps": "Areas where evidence is missing, weak, conflicting, or insufficient to support a confident research conclusion.",
    "validation_studies": "Tool-generated experiments that could reduce uncertainty or test the current hypothesis. These are research suggestions, not observed results.",
    "evidence_record": "The auditable source-grounded claims underlying the profile, grouped by evidence type and accompanied by statistics, source, and confidence.",
}
'''

replace_once(
    'st.set_page_config(page_title="GBM Gene Analysis", page_icon="🧬", layout="wide")\n',
    'st.set_page_config(page_title="GBM Gene Analysis", page_icon="🧬", layout="wide")\n' + HELP_BLOCK,
)

heading_replacements = {
    'st.markdown("#### Genomic Evidence")': 'st.subheader("Genomic Evidence", help=HELP["genomic_evidence"], anchor=False)',
    'st.markdown("#### Gene Identity")': 'st.subheader("Gene Identity", help=HELP["gene_identity"], anchor=False)',
    'st.markdown("#### DepMap Functional Dependency")': 'st.subheader("DepMap Functional Dependency", help=HELP["depmap"], anchor=False)',
    'st.markdown("#### Ivy GAP Spatial Expression")': 'st.subheader("Ivy GAP Spatial Expression", help=HELP["ivy_gap"], anchor=False)',
    'st.markdown("#### CGGA External Cohort Validation")': 'st.subheader("CGGA External Cohort Validation", help=HELP["cgga"], anchor=False)',
    'st.markdown("#### GLASS Longitudinal Validation")': 'st.subheader("GLASS Longitudinal Validation", help=HELP["glass"], anchor=False)',
    'st.markdown("#### Normal Tissue and Brain Context")': 'st.subheader("Normal Tissue and Brain Context", help=HELP["normal_tissue"], anchor=False)',
    'st.markdown("#### Interaction Network and Pathways")': 'st.subheader("Interaction Network and Pathways", help=HELP["network"], anchor=False)',
    'st.markdown("#### GBmap Single-Cell and Spatial Reference")': 'st.subheader("GBmap Single-Cell and Spatial Reference", help=HELP["gbmap"], anchor=False)',
    'st.markdown("#### Blood-Brain Barrier Evidence")': 'st.subheader("Blood-Brain Barrier Evidence", help=HELP["bbb"], anchor=False)',
}
for old, new in heading_replacements.items():
    text = text.replace(old, new)

metric_replacements = {
    'g1.metric("TCGA Mutation Frequency", pct((cbio.get("mutation") or {}).get("frequency")))': 'g1.metric("TCGA Mutation Frequency", pct((cbio.get("mutation") or {}).get("frequency")), help=HELP["tcga_mutation"])',
    'g2.metric("TCGA Amplification Frequency", pct((cbio.get("copy_number") or {}).get("amplification_frequency")))': 'g2.metric("TCGA Amplification Frequency", pct((cbio.get("copy_number") or {}).get("amplification_frequency")), help=HELP["tcga_amplification"])',
    'g3.metric("TCGA Deep Deletion Frequency", pct((cbio.get("copy_number") or {}).get("deep_deletion_frequency")))': 'g3.metric("TCGA Deep Deletion Frequency", pct((cbio.get("copy_number") or {}).get("deep_deletion_frequency")), help=HELP["tcga_deletion"])',
    'g4.metric("Open Targets Association Score", num(ot.get("gbm_association_score"), 3))': 'g4.metric("Open Targets Association Score", num(ot.get("gbm_association_score"), 3), help=HELP["open_targets_score"])',
    'd1.metric("Strict GBM Models", dep.get("n_gbm"))': 'd1.metric("Strict GBM Models", dep.get("n_gbm"), help=HELP["strict_gbm_models"])',
    'd2.metric("Median GBM Chronos Score", num(dep.get("median_effect_gbm"), 2))': 'd2.metric("Median GBM Chronos Score", num(dep.get("median_effect_gbm"), 2), help=HELP["chronos"])',
    'd3.metric("Selectivity Difference", num(dep.get("median_selectivity_delta"), 2))': 'd3.metric("Selectivity Difference", num(dep.get("median_selectivity_delta"), 2), help=HELP["selectivity"])',
    'd4.metric("One-Sided p Value", pval(dep.get("p_value")))': 'd4.metric("One-Sided p Value", pval(dep.get("p_value")), help=HELP["one_sided_p"])',
    'i1.metric("LMD Samples", ivy.get("n_samples"))': 'i1.metric("LMD Samples", ivy.get("n_samples"), help=HELP["lmd_samples"])',
    'i2.metric("Highest-Expression Anatomic Zone", str(ivy.get("top_zone", "N/A")).replace("_", " ").title())': 'i2.metric("Highest-Expression Anatomic Zone", str(ivy.get("top_zone", "N/A")).replace("_", " ").title(), help=HELP["anatomic_zone"])',
    'i3.metric("Median Expression Range", num(ivy.get("median_range"), 2))': 'i3.metric("Median Expression Range", num(ivy.get("median_range"), 2), help=HELP["expression_range"])',
    'i4.metric("Kruskal p Value", pval(ivy.get("p_value")))': 'i4.metric("Kruskal p Value", pval(ivy.get("p_value")), help=HELP["kruskal_p"])',
    'c1.metric("Usable Strict-GBM Cohorts", f"{cgg.get(\'n_usable_cohorts\', 0)}/2")': 'c1.metric("Usable Strict-GBM Cohorts", f"{cgg.get(\'n_usable_cohorts\', 0)}/2", help=HELP["strict_cohorts"])',
    'c2.metric("Pooled HR per 1 SD", num((meta or {}).get("pooled_hr"), 2))': 'c2.metric("Pooled HR per 1 SD", num((meta or {}).get("pooled_hr"), 2), help=HELP["pooled_hr"])',
    'c3.metric("Pooled p Value", pval((meta or {}).get("pooled_p_value")))': 'c3.metric("Pooled p Value", pval((meta or {}).get("pooled_p_value")), help=HELP["pooled_p"])',
    'x1.metric("Primary/Recurrent Pairs", gla.get("n_pairs"))': 'x1.metric("Primary/Recurrent Pairs", gla.get("n_pairs"), help=HELP["pairs"])',
    'x2.metric("Median Recurrence Change", num(gla.get("median_delta"), 3))': 'x2.metric("Median Recurrence Change", num(gla.get("median_delta"), 3), help=HELP["recurrence_change"])',
    'x3.metric("Paired p Value", pval(gla.get("p_value")))': 'x3.metric("Paired p Value", pval(gla.get("p_value")), help=HELP["paired_p"])',
    'h1.metric("Tissue Specificity", hpa.get("tissue_specificity") or "N/A")': 'h1.metric("Tissue Specificity", hpa.get("tissue_specificity") or "N/A", help=HELP["tissue_specificity"])',
    'h2.metric("Brain Single-Nuclei Specificity", hpa.get("single_nuclei_brain_specificity") or "N/A")': 'h2.metric("Brain Single-Nuclei Specificity", hpa.get("single_nuclei_brain_specificity") or "N/A", help=HELP["brain_single_nuclei"])',
    'h3.metric("Maximum Displayed Normal-Brain Expression", num(hpa.get("normal_brain_max_expression"), 1))': 'h3.metric("Maximum Displayed Normal-Brain Expression", num(hpa.get("normal_brain_max_expression"), 1), help=HELP["normal_brain_expression"])',
    'st.metric("GBM Literature Co-Mentions", lit.get("hit_count", 0) if lit.get("ok") else "N/A")': 'st.metric("GBM Literature Co-Mentions", lit.get("hit_count", 0) if lit.get("ok") else "N/A", help=HELP["literature_count"])',
    't1.metric("Target-Directed Candidates", ot.get("known_drug_count", 0) if ot.get("ok") else "N/A")': 't1.metric("Target-Directed Candidates", ot.get("known_drug_count", 0) if ot.get("ok") else "N/A", help=HELP["target_candidates"])',
    't2.metric("Highest Matching GBM Trial Phase", trials.get("max_phase", 0) if trials.get("ok") else "N/A")': 't2.metric("Highest Matching GBM Trial Phase", trials.get("max_phase", 0) if trials.get("ok") else "N/A", help=HELP["trial_phase"])',
    't3.metric("Matching GBM Trials", trials.get("total", 0) if trials.get("ok") else "N/A")': 't3.metric("Matching GBM Trials", trials.get("total", 0) if trials.get("ok") else "N/A", help=HELP["matching_trials"])',
    'b1.metric("Candidates Checked", bbb.get("candidates_checked", 0))': 'b1.metric("Candidates Checked", bbb.get("candidates_checked", 0), help=HELP["candidates_checked"])',
    'b2.metric("B3DB Matches", bbb.get("matched_count", 0))': 'b2.metric("B3DB Matches", bbb.get("matched_count", 0), help=HELP["b3db_matches"])',
    'b3.metric("BBB+ Records", bbb.get("bbb_positive_count", 0))': 'b3.metric("BBB+ Records", bbb.get("bbb_positive_count", 0), help=HELP["bbb_positive"])',
    'm1.metric("Target Priority Score", "N/A" if score.overall is None else f"{score.overall}/100")': 'm1.metric("Target Priority Score", "N/A" if score.overall is None else f"{score.overall}/100", help=HELP["target_priority_score"])',
    'm2.metric("Evidence Coverage", f"{score.evidence_coverage_pct}%")': 'm2.metric("Evidence Coverage", f"{score.evidence_coverage_pct}%", help=HELP["evidence_coverage"])',
    'm3.metric("Evidence Records", len(profile.dossier.evidence))': 'm3.metric("Evidence Records", len(profile.dossier.evidence), help=HELP["evidence_records"])',
    'm4.metric("Active GBM Trials", trials.get("active", 0))': 'm4.metric("Active GBM Trials", trials.get("active", 0), help=HELP["active_trials"])',
}
for old, new in metric_replacements.items():
    if old not in text:
        raise RuntimeError(f"Missing metric replacement target: {old}")
    text = text.replace(old, new)

replace_once(
    '''st.caption(
            f"GBM definition: {dep.get('gbm_definition')}. Pan-essential classification: {'Yes' if dep.get('pan_essential') else 'No'}."
        )''',
    '''st.caption(
            f"GBM definition: {dep.get('gbm_definition')}. Pan-essential classification: {'Yes' if dep.get('pan_essential') else 'No'}.",
            help=HELP["pan_essential"],
        )''',
)

replace_once('st.markdown("### Evidence Consistency")', 'st.subheader("Evidence Consistency", help=HELP["evidence_consistency"], anchor=False)')
replace_once(
    'with st.expander("Priority Score Composition", expanded=False):',
    'with st.expander("Priority Score Composition", expanded=False):\n            st.caption("How the overall research-prioritization score is assembled.", help=HELP["score_composition"])',
)
replace_once('st.markdown("### Evidence Gaps")', 'st.subheader("Evidence Gaps", help=HELP["evidence_gaps"], anchor=False)')
replace_once('st.markdown("### Potential Validation Studies")', 'st.subheader("Potential Validation Studies", help=HELP["validation_studies"], anchor=False)')
replace_once(
    'with record_tab:\n            render_evidence_record(profile)',
    'with record_tab:\n            st.caption("Auditable claims used by the profile.", help=HELP["evidence_record"])\n            render_evidence_record(profile)',
)
replace_once(
    'st.caption("Therapeutic and clinical-development context is separated from the underlying biological evidence.")',
    'st.caption("Therapeutic and clinical-development context is separated from the underlying biological evidence.", help=HELP["translation"])',
)

old_form = '''with analysis_tab:
    input_col, button_col = st.columns([4, 1], vertical_alignment="bottom")
    with input_col:
        gene = st.text_input(
            "Gene symbol",
            value="EGFR",
            placeholder="e.g. EGFR, PTEN, TERT, CDK6",
        ).strip()
    with button_col:
        run = st.button("Build Research Profile", type="primary", use_container_width=True)

    if run:
        try:
            with st.spinner(f"Assembling multi-source GBM evidence for {gene.upper()}..."):
                profile = cached_profile(gene)
            st.session_state["profile_v5"] = profile
        except Exception as exc:
            st.error(f"Could not build the profile: {exc}")
'''
new_form = '''with analysis_tab:
    with st.form("gene_analysis_form", clear_on_submit=False):
        input_col, button_col = st.columns([4, 1], vertical_alignment="bottom")
        with input_col:
            gene = st.text_input(
                "Gene symbol",
                value="EGFR",
                placeholder="e.g. EGFR, PTEN, TERT, CDK6",
                help=HELP["gene_symbol"],
            ).strip()
        with button_col:
            run = st.form_submit_button(
                "Analyze",
                type="primary",
                use_container_width=True,
                help=HELP["analyze"],
            )

    if run:
        if not gene:
            st.warning("Enter a gene symbol to analyze.")
        else:
            try:
                with st.spinner(f"Analyzing multi-source GBM evidence for {gene.upper()}..."):
                    profile = cached_profile(gene)
                st.session_state["profile_v5"] = profile
            except Exception as exc:
                st.error(f"Could not analyze the gene: {exc}")
'''
replace_once(old_form, new_form)

path.write_text(text)
print("patched", text.count('help=HELP['))
