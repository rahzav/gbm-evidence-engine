#!/usr/bin/env python3
from pathlib import Path

src = Path("streamlit_app_v5.py")
text = src.read_text(encoding="utf-8")


def must_replace(old: str, new: str, count: int = 1):
    global text
    if old not in text:
        raise SystemExit(f"Required integration marker not found: {old[:120]!r}")
    text = text.replace(old, new, count)


# Production identity and imports.
must_replace('"""Streamlit interface for GBM Gene Analysis V5."""', '"""Streamlit interface for GBM Gene Analysis."""')
must_replace(
    'import json\nimport streamlit as st\n\nfrom gbm_evidence_engine.evidence_model import EvidenceTier\nfrom gbm_evidence_engine.research_intelligence_v5 import build_research_profile, rank_gene_list\n',
    'import io\nimport json\n\nimport pandas as pd\nimport streamlit as st\n\nfrom gbm_evidence_engine.evidence_model import EvidenceTier\nfrom gbm_evidence_engine.research_intelligence_v7_prod import (\n    analyze_researcher_signature,\n    build_research_profile,\n    evaluate_gene_pair,\n    rank_gene_list,\n)\n',
)

must_replace(
    '@st.cache_data(ttl=3600, show_spinner=False)\ndef cached_batch(genes: tuple[str, ...]):\n    return rank_gene_list(list(genes), max_workers=2)\n',
    '@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)\ndef cached_batch(genes: tuple[str, ...]):\n    return rank_gene_list(list(genes), max_workers=1)\n\n\n@st.cache_data(ttl=3600, max_entries=4, show_spinner=False)\ndef cached_pair(gene_a: str, gene_b: str):\n    return evaluate_gene_pair(gene_a, gene_b)\n\n\n@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)\ndef cached_signature(\n    genes: tuple[str, ...],\n    values: tuple[float, ...],\n    p_values: tuple[float | None, ...] | None,\n    fdr_values: tuple[float | None, ...] | None,\n):\n    return analyze_researcher_signature(\n        genes, values, p_values=p_values, fdr_values=fdr_values\n    )\n',
)

# Add V7-specific helpers before profile rendering.
marker = '\ndef render_profile(profile):\n'
if marker not in text:
    raise SystemExit("render_profile marker not found")
helpers = r'''

def confidence_text(item: dict) -> str:
    if not item or item.get("score") is None:
        return "Insufficient"
    return f"{str(item.get('level', 'unknown')).title()} · {item.get('score')}/100"


def render_confidence_summary(profile):
    live = profile.live
    overall = live.get("overall_evidence_confidence", {})
    model = live.get("model_relevance", {})
    by_dim = live.get("confidence_by_dimension", {})

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("#### Evidence Confidence")
            st.metric("Overall", confidence_text(overall))
            for reason in (overall.get("reasons") or [])[:2]:
                st.caption(reason)
    with c2:
        with st.container(border=True):
            st.markdown("#### Functional Model Relevance")
            score = model.get("score")
            score_text = "N/A" if score is None else f"{score}/100"
            st.metric("Model Relevance", f"{str(model.get('level', 'unknown')).title()} · {score_text}")
            for reason in (model.get("reasons") or [])[:2]:
                st.caption(reason)

    with st.expander("Confidence by Evidence Dimension", expanded=False):
        rows = []
        for name, dimension in profile.score.dimensions.items():
            conf = by_dim.get(name, {})
            rows.append({
                "Evidence Dimension": name,
                "Evidence Score": None if dimension.score is None else round(dimension.score, 1),
                "Confidence": str(conf.get("level") or "insufficient").title(),
                "Confidence Score": conf.get("score"),
                "Primary Source": dimension.source,
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)


def render_cell_state(cell: dict):
    st.subheader("GBmap Cell-State Context", help=HELP["gbmap"], anchor=False)
    if not cell.get("ok"):
        status = cell.get("status")
        if status == "ambiguous_gene_symbol":
            st.info(cell.get("error", "This symbol maps to multiple GBmap features and is not collapsed."))
        else:
            st.info(cell.get("error", "The compact GBmap reference is unavailable for this gene."))
        if cell.get("source_url"):
            st.link_button("Open GBmap Collection", cell["source_url"])
        return

    top = cell.get("top_malignant_state") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Top Malignant State", top.get("state") or "N/A")
    c2.metric("Patient Prevalence", pct(cell.get("malignant_patient_prevalence")))
    c3.metric("Malignant Expression Breadth", pct(cell.get("malignant_fraction_expressing")))
    c4.metric("Annotated States", cell.get("n_states", "N/A"))
    rows = []
    for row in (cell.get("states") or [])[:25]:
        rows.append({
            "State": row.get("state"),
            "Class": row.get("state_class"),
            "State Patients": row.get("n_state_patients"),
            "Expressing Patients": row.get("n_expressing_patients"),
            "Patient Prevalence": row.get("patient_prevalence"),
            "Cells": row.get("n_cells"),
            "Fraction Expressing": row.get("fraction_expressing"),
            "Mean Expression": row.get("mean_expression"),
            "Across-State Z": row.get("expression_z_across_states"),
        })
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    if cell.get("interpretation"):
        st.caption(cell["interpretation"])


def render_discovery_workspace(profile):
    live = profile.live
    opportunities = live.get("research_opportunities", [])
    hypotheses = live.get("mechanistic_hypotheses", [])
    experiments = live.get("experiment_portfolio", [])

    opportunity_tab, hypothesis_tab, experiment_tab, gap_tab = st.tabs([
        "Research Opportunities",
        "Mechanistic Hypotheses",
        "Experimental Planning",
        "Evidence Gaps",
    ])
    with opportunity_tab:
        if opportunities:
            for row in opportunities:
                with st.expander(f"{row.get('title', 'Research opportunity')} · Priority {row.get('priority', 'N/A')}/100"):
                    st.write(row.get("signal", ""))
                    if row.get("recommended_test"):
                        st.markdown(f"**Proposed test:** {row['recommended_test']}")
                    if row.get("caution"):
                        st.caption(row["caution"])
        else:
            st.info("No high-priority cross-source research opportunity was identified from the available evidence.")

    with hypothesis_tab:
        if hypotheses:
            for index, row in enumerate(hypotheses, start=1):
                with st.expander(f"Hypothesis {index}: {row.get('hypothesis', '')}"):
                    for observation in row.get("supporting_observations", []):
                        st.markdown(f"- {observation}")
                    if row.get("falsification_test"):
                        st.markdown(f"**Falsification test:** {row['falsification_test']}")
        else:
            st.info("The current evidence does not support a sufficiently specific mechanistic hypothesis under the system guardrails.")

    with experiment_tab:
        if experiments:
            st.dataframe(experiments, use_container_width=True, hide_index=True)
        else:
            st.info("No experiment portfolio was generated from the current evidence profile.")
        if profile.next_experiments:
            st.markdown("#### Additional Validation Studies")
            for idea in profile.next_experiments:
                st.markdown(f"- {idea}")

    with gap_tab:
        if profile.evidence_gaps:
            for gap in profile.evidence_gaps:
                st.markdown(f"- {gap}")
        else:
            st.write("No major evidence gaps were identified from the available sources.")
'''
text = text.replace(marker, helpers + marker, 1)

# Keep the polished profile organization, but expose the final confidence/cell-state layers.
must_replace(
    '    gbmap = live.get("gbmap_reference", {})\n',
    '    gbmap = live.get("gbmap_reference", {})\n    cell = live.get("gbmap_cell_state", {})\n    overall_confidence = live.get("overall_evidence_confidence", {})\n',
)
must_replace(
    '    m3.metric("Evidence Records", len(profile.dossier.evidence))\n',
    '    m3.metric("Evidence Confidence", confidence_text(overall_confidence))\n',
)

# Add compact confidence/model context to Overview before score composition.
overview_marker = '        section_space(0.5)\n        with st.expander("Priority Score Composition", expanded=False):\n'
if overview_marker not in text:
    raise SystemExit("Overview marker not found")
text = text.replace(
    overview_marker,
    '        section_space(0.5)\n        render_confidence_summary(profile)\n\n        section_space(0.5)\n        with st.expander("Priority Score Composition", expanded=False):\n',
    1,
)

# Place native GBmap in the biological-context workspace.
must_replace(
    'def render_tissue_and_network(identity, hpa, network, gbmap):\n    st.subheader("Normal Tissue and Brain Context", anchor=False)\n',
    'def render_tissue_and_network(identity, hpa, network, gbmap, cell):\n    render_cell_state(cell)\n    section_space(0.8)\n    st.subheader("Normal Tissue and Brain Context", anchor=False)\n',
)
must_replace(
    '            render_tissue_and_network(identity, hpa, network, gbmap)\n',
    '            render_tissue_and_network(identity, hpa, network, gbmap, cell)\n',
)

# Add model-format context beneath DepMap without changing the underlying calculations.
old_dep = '''        if dep.get("most_dependent_gbm_models"):\n            st.dataframe(dep["most_dependent_gbm_models"], use_container_width=True, hide_index=True)\n'''
new_dep = '''        if dep.get("most_dependent_gbm_models"):\n            st.dataframe(dep["most_dependent_gbm_models"], use_container_width=True, hide_index=True)\n        nextgen = dep.get("nextgen_model_context") or {}\n        if nextgen.get("metadata_available"):\n            with st.expander("Model Format Context", expanded=False):\n                n1, n2, n3, n4 = st.columns(4)\n                n1.metric("NextGen 3D Models", nextgen.get("n_nextgen_3d_gbm", 0))\n                n2.metric("Conventional Models", nextgen.get("n_conventional_gbm", 0))\n                n3.metric("Median 3D Chronos", num(nextgen.get("median_nextgen_3d_chronos"), 2))\n                n4.metric("Median Conventional", num(nextgen.get("median_conventional_chronos"), 2))\n                if nextgen.get("interpretation"):\n                    st.caption(nextgen["interpretation"])\n'''
if old_dep not in text:
    raise SystemExit("DepMap table marker not found")
text = text.replace(old_dep, new_dep, 1)

# Replace the interpretation workspace with the structured V7 discovery workspace.
start = text.index('    with interpretation_tab:\n')
end = text.index('    with sources_tab:\n', start)
replacement = '''    with interpretation_tab:\n        st.caption("Integrated interpretation of cross-source evidence, mechanistic hypotheses, and experimental validation priorities.")\n        render_discovery_workspace(profile)\n\n'''
text = text[:start] + replacement + text[end:]

# Expand Markdown export with final research layers.
must_replace(
    '        f"**Evidence Coverage:** {s.evidence_coverage_pct}%", "",\n',
    '        f"**Evidence Coverage:** {s.evidence_coverage_pct}%",\n        f"**Evidence Confidence:** {confidence_text(live.get(\'overall_evidence_confidence\', {}))}",\n        f"**Functional Model Relevance:** {str((live.get(\'model_relevance\') or {}).get(\'level\', \'unknown\')).title()}", "",\n',
)
insert_after = '    lines += ["", "## Evidence Gaps"] + [f"- {x}" for x in profile.evidence_gaps]\n'
if insert_after not in text:
    raise SystemExit("Markdown evidence-gap marker not found")
text = text.replace(
    insert_after,
    '    lines += ["", "## Research Opportunities"]\n    for row in live.get("research_opportunities", []):\n        lines.append(f"- **{row.get(\'title\', \'Research opportunity\')}** ({row.get(\'priority\', \'N/A\')}/100): {row.get(\'signal\', \'\')}")\n    lines += ["", "## Mechanistic Hypotheses"]\n    for row in live.get("mechanistic_hypotheses", []):\n        lines.append(f"- {row.get(\'hypothesis\', \'\')}")\n    lines += ["", "## Evidence Gaps"] + [f"- {x}" for x in profile.evidence_gaps]\n',
    1,
)

# Replace all top-level workspaces with the final production workflows.
root_start = text.index('analysis_tab, batch_tab, methods_tab = st.tabs([')
new_root = r'''analysis_tab, pair_tab, researcher_tab, batch_tab, methods_tab = st.tabs([
    "Gene Analysis",
    "Target Pair Analysis",
    "Researcher Data",
    "Gene Set Comparison",
    "Methods & Data Sources",
])

with analysis_tab:
    with st.form("gene_analysis_form", clear_on_submit=False):
        input_col, button_col = st.columns([4, 1], vertical_alignment="bottom")
        with input_col:
            gene = st.text_input(
                "Gene symbol",
                value="EGFR",
                placeholder="e.g. EGFR, PTEN, TERT, CDK6",
            ).strip()
        with button_col:
            run = st.form_submit_button(
                "Build dossier",
                type="primary",
                use_container_width=True,
            )

    if run:
        if not gene:
            st.warning("Enter a gene symbol to build a dossier.")
        else:
            try:
                with st.spinner(f"Building the GBM evidence dossier for {gene.upper()}..."):
                    profile = cached_profile(gene)
                st.session_state["profile"] = profile
            except Exception as exc:
                st.error(f"Could not build the dossier: {exc}")

    profile = st.session_state.get("profile")
    if profile:
        render_profile(profile)

with pair_tab:
    st.subheader("Target Pair Analysis", anchor=False)
    st.caption("Cross-target evidence comparison across functional, network, spatial, cell-state, recurrence, translational, and model-relevance layers.")
    with st.form("pair_analysis_form", clear_on_submit=False):
        a_col, b_col, run_col = st.columns([2, 2, 1], vertical_alignment="bottom")
        with a_col:
            gene_a = st.text_input("Target A", value="EGFR", key="pair_a").strip()
        with b_col:
            gene_b = st.text_input("Target B", value="CDK4", key="pair_b").strip()
        with run_col:
            pair_run = st.form_submit_button("Build pair dossier", type="primary", use_container_width=True)
    if pair_run:
        try:
            with st.spinner(f"Building the evidence comparison for {gene_a.upper()} + {gene_b.upper()}..."):
                st.session_state["pair"] = cached_pair(gene_a, gene_b)
        except Exception as exc:
            st.error(f"Pair analysis failed: {exc}")

    pair = st.session_state.get("pair")
    if pair:
        section_space(0.7)
        p1, p2, p3 = st.columns(3)
        p1.metric("Combination Rationale Score", f"{pair.get('combination_rationale_score', 'N/A')}/100")
        p2.metric("Evidence Coverage", f"{pair.get('evidence_coverage_pct', 'N/A')}%")
        p3.metric("Pair Evidence Confidence", confidence_text(pair.get("pair_evidence_confidence", {})))
        component_tab, rationale_tab, model_tab, validation_tab = st.tabs([
            "Rationale Components", "Evidence Interpretation", "Model Relevance", "Validation Sequence"
        ])
        with component_tab:
            st.dataframe([
                {"Component": key.replace("_", " ").title(), "Score": value}
                for key, value in pair.get("components", {}).items()
            ], use_container_width=True, hide_index=True)
        with rationale_tab:
            left, right = st.columns(2)
            with left:
                st.markdown("#### Supporting Rationale")
                for item in pair.get("why_test_it", []):
                    st.markdown(f"- {item}")
            with right:
                st.markdown("#### Limitations")
                for item in pair.get("risks", []):
                    st.markdown(f"- {item}")
                if not pair.get("risks"):
                    st.write("No pair-specific limitation flag was generated from the available evidence.")
        with model_tab:
            rows = [{"Gene": gene_name, **model} for gene_name, model in pair.get("model_relevance", {}).items()]
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)
        with validation_tab:
            for index, item in enumerate(pair.get("validation_sequence", []), start=1):
                st.markdown(f"{index}. {item}")

with researcher_tab:
    st.subheader("Processed Researcher Result Analysis", anchor=False)
    st.caption("Analyze processed gene-level results using signed effect sizes with optional p-values or FDR/q-values. Uploaded tables are read for analysis and are not written to the project repository by the application.")
    uploaded = st.file_uploader("Upload CSV or TSV", type=["csv", "tsv", "txt"], key="research_upload")
    default_text = "gene,effect,p_value,fdr\nEGFR,2.4,0.0001,0.002\nSOX2,1.8,0.001,0.01\nSTAT3,1.5,0.004,0.02\nCDK6,1.2,0.01,0.04\nOLIG2,-1.1,0.02,0.05\nGFAP,-1.4,0.001,0.01\nCDKN1A,-1.7,0.0005,0.005\nBAX,-2.0,0.0001,0.002"
    pasted = st.text_area("Or paste a processed table", value=default_text, height=180)
    signature_df = None
    try:
        if uploaded is not None:
            signature_df = pd.read_csv(io.BytesIO(uploaded.getvalue()), sep=None, engine="python")
        elif pasted.strip():
            signature_df = pd.read_csv(io.StringIO(pasted), sep=None, engine="python")
    except Exception as exc:
        st.error(f"Could not parse the result table: {exc}")

    if signature_df is not None and not signature_df.empty:
        columns = list(signature_df.columns)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            gene_col = st.selectbox("Gene column", columns, index=0)
        with c2:
            value_col = st.selectbox("Signed effect column", columns, index=1 if len(columns) > 1 else 0)
        optional = ["None"] + columns
        with c3:
            p_col = st.selectbox("p-value column", optional, index=(columns.index("p_value") + 1 if "p_value" in columns else 0))
        with c4:
            fdr_col = st.selectbox("FDR/q-value column", optional, index=(columns.index("fdr") + 1 if "fdr" in columns else 0))
        preview_cols = [gene_col, value_col] + ([p_col] if p_col != "None" else []) + ([fdr_col] if fdr_col != "None" else [])
        st.dataframe(signature_df[preview_cols].head(20), use_container_width=True, hide_index=True)
        if st.button("Build result dossier", type="primary"):
            try:
                gene_values = signature_df[gene_col].astype(str).tolist()
                effects = pd.to_numeric(signature_df[value_col], errors="coerce")
                p_series = pd.to_numeric(signature_df[p_col], errors="coerce") if p_col != "None" else None
                fdr_series = pd.to_numeric(signature_df[fdr_col], errors="coerce") if fdr_col != "None" else None
                keep = effects.notna()
                genes_clean = tuple(g for g, ok in zip(gene_values, keep) if ok)
                values_clean = tuple(float(v) for v in effects[keep])
                p_clean = tuple(None if pd.isna(v) else float(v) for v in p_series[keep]) if p_series is not None else None
                fdr_clean = tuple(None if pd.isna(v) else float(v) for v in fdr_series[keep]) if fdr_series is not None else None
                with st.spinner("Building the processed-result dossier..."):
                    st.session_state["signature"] = cached_signature(genes_clean, values_clean, p_clean, fdr_clean)
            except Exception as exc:
                st.error(f"Research-result analysis failed: {exc}")

    signature = st.session_state.get("signature")
    if signature:
        section_space(0.7)
        s1, s2 = st.columns(2)
        s1.metric("Input Genes", signature.get("n_input_genes"))
        s2.metric("Statistically Supported", signature.get("n_statistically_supported") if signature.get("statistics_provided") else "Not supplied")
        signal_tab, pathway_tab, perturbation_tab, export_tab = st.tabs([
            "GBM-Prioritized Signals", "Pathway Enrichment", "Perturbational Reversal", "Export"
        ])
        with signal_tab:
            st.dataframe(signature.get("top_genes_profiled", []), use_container_width=True, hide_index=True)
            if signature.get("interpretation"):
                st.caption(signature["interpretation"])
        with pathway_tab:
            e1, e2 = st.columns(2)
            with e1:
                st.markdown("#### Upregulated Program")
                up = signature.get("up_pathway_enrichment", {})
                if up.get("ok"):
                    st.dataframe(up.get("results", []), use_container_width=True, hide_index=True)
                else:
                    st.info(up.get("error", "No enrichment available."))
            with e2:
                st.markdown("#### Downregulated Program")
                down = signature.get("down_pathway_enrichment", {})
                if down.get("ok"):
                    st.dataframe(down.get("results", []), use_container_width=True, hide_index=True)
                else:
                    st.info(down.get("error", "No enrichment available."))
        with perturbation_tab:
            l1000 = signature.get("l1000_reversal", {})
            if l1000.get("ok"):
                st.dataframe(l1000.get("top_drugs", []), use_container_width=True, hide_index=True)
                if l1000.get("combinations"):
                    st.markdown("#### Combination Hypotheses")
                    st.dataframe(l1000["combinations"], use_container_width=True, hide_index=True)
                if l1000.get("interpretation"):
                    st.caption(l1000["interpretation"])
            else:
                st.info(l1000.get("error", "Perturbational reversal evidence is unavailable."))
        with export_tab:
            st.download_button(
                "Download Result Dossier (JSON)",
                json.dumps(signature, indent=2, default=str),
                file_name="gbm_processed_result_dossier.json",
                mime="application/json",
            )

with batch_tab:
    st.write("Enter a short gene set to compare targets using the same evidence architecture.")
    raw = st.text_area("Gene symbols", value="EGFR, PTEN, TP53, CDK4", key="gene_set")
    genes = list(dict.fromkeys(x.strip() for x in raw.replace(",", " ").split() if x.strip()))
    if len(genes) > 6:
        st.warning("Gene set comparison is limited to 6 genes per run.")
        genes = genes[:6]
    if st.button("Build comparison", type="primary") and genes:
        try:
            with st.spinner("Building and comparing GBM evidence dossiers..."):
                profiles = cached_batch(tuple(genes))
            rows = []
            for item in profiles:
                item_live = item.live
                item_dep = item_live.get("depmap", {})
                item_cgg = item_live.get("cgga", {})
                item_identity = item_live.get("gene_identity", {})
                rows.append({
                    "Gene": item.gene,
                    "Submitted Symbol": item_identity.get("query", item.gene),
                    "Target Priority Score": item.score.overall,
                    "Evidence Coverage (%)": item.score.evidence_coverage_pct,
                    "Evidence Confidence": confidence_text(item_live.get("overall_evidence_confidence", {})),
                    "Model Relevance": str((item_live.get("model_relevance") or {}).get("level", "unknown")).title(),
                    "Priority Classification": item.score.label,
                    "DepMap Selectivity Difference": item_dep.get("median_selectivity_delta"),
                    "Usable CGGA Cohorts": item_cgg.get("n_usable_cohorts", 0),
                    "Active GBM Trials": item_live.get("clinical_trials", {}).get("active", 0),
                    "B3DB Matches": item_live.get("bbb_candidates", {}).get("matched_count", 0),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"Gene set comparison failed: {exc}")

with methods_tab:
    st.markdown("### Research Scope")
    st.write("GBM Gene Analysis integrates molecular evidence for research prioritization, processed-result interpretation, target-pair evaluation, and experimental planning. The system is focused on glioblastoma molecular research rather than clinical treatment selection.")

    section_space(0.7)
    st.markdown("### Scored Evidence Model")
    st.write("The Target Priority Score integrates TCGA genomic signal, Open Targets disease relevance and druggability, clinical translation, literature context, DepMap functional dependency, Ivy GAP spatial expression, CGGA independent human validation, and GLASS longitudinal recurrence when authorized evidence is available. Missing sources reduce Evidence Coverage rather than being treated as negative biological evidence.")

    section_space(0.7)
    st.markdown("### Confidence, Model Relevance, and Cell State")
    st.write("Evidence Confidence is calculated separately from Target Priority. Functional Model Relevance describes the available dependency-model context. GBmap provides patient-aware malignant and microenvironment cell-state expression context from a compact reference derived from the published Core GBmap atlas.")

    section_space(0.7)
    st.markdown("### Processed Researcher Results")
    st.write("Processed gene-level signatures can be analyzed using signed effects with optional p-values or FDR/q-values. The workflow adds GBM evidence prioritization, pathway enrichment, and L1000 perturbational-reversal context without processing raw sequencing files.")

    section_space(0.7)
    st.markdown("### Provenance and Validation")
    st.write("Quantitative evidence retains source, method, retrieval metadata, confidence, and citation information. Deterministic scientific tests, grounding checks, current-behavior benchmarks, and production interaction tests are maintained separately from biological validation.")
'''
text = text[:root_start] + new_root + "\n"

# Final production file names: one public UI entrypoint plus one UI module.
Path("app_ui.py").write_text(text, encoding="utf-8")
src.unlink()
Path("streamlit_app.py").write_text(
    '"""Streamlit entrypoint for GBM Gene Analysis."""\n'
    'from pathlib import Path\n'
    'import runpy\n\n'
    '_PAGE = Path(__file__).with_name("app_ui.py")\n'
    'runpy.run_path(str(_PAGE), run_name="__main__")\n',
    encoding="utf-8",
)
print("Final production UI integration complete")
