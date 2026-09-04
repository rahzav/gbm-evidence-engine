"""Streamlit interface for the frozen-scope GBM Gene Analysis V7."""
from __future__ import annotations

import io
import json

import pandas as pd
import streamlit as st

from gbm_evidence_engine.evidence_model import EvidenceTier
from gbm_evidence_engine.research_intelligence_v7 import (
    analyze_researcher_signature,
    build_research_profile,
    evaluate_gene_pair,
    rank_gene_list,
)

st.set_page_config(page_title="GBM Gene Analysis", page_icon="🧬", layout="wide")


@st.cache_data(ttl=3600, max_entries=8, show_spinner=False)
def cached_profile(gene: str):
    return build_research_profile(gene)


@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def cached_batch(genes: tuple[str, ...]):
    return rank_gene_list(list(genes), max_workers=1)


@st.cache_data(ttl=3600, max_entries=4, show_spinner=False)
def cached_pair(gene_a: str, gene_b: str):
    return evaluate_gene_pair(gene_a, gene_b)


@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def cached_signature(
    genes: tuple[str, ...],
    values: tuple[float, ...],
    p_values: tuple[float | None, ...] | None,
    fdr_values: tuple[float | None, ...] | None,
):
    return analyze_researcher_signature(
        genes,
        values,
        p_values=p_values,
        fdr_values=fdr_values,
    )


def pct(value):
    return "N/A" if value is None else f"{100 * float(value):.1f}%"


def num(value, digits=2):
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def pval(value):
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.2g}"
    except (TypeError, ValueError):
        return str(value)


def section_space(size: float = 1.2):
    st.markdown(f"<div style='height:{size}rem'></div>", unsafe_allow_html=True)


def confidence_text(item: dict) -> str:
    if not item or item.get("score") is None:
        return "Insufficient"
    return f"{str(item.get('level', 'unknown')).title()} · {item.get('score')}/100"


def markdown_brief(profile) -> str:
    score = profile.score
    live = profile.live
    overall_conf = live.get("overall_evidence_confidence", {})
    model = live.get("model_relevance", {})
    cell = live.get("gbmap_cell_state", {})
    lines = [
        f"# GBM Gene Analysis: {profile.gene}", "",
        f"**Target Priority Score:** {score.overall if score.overall is not None else 'N/A'}/100 ({score.label})",
        f"**Evidence Coverage:** {score.evidence_coverage_pct}%",
        f"**Evidence Confidence:** {confidence_text(overall_conf)}",
        f"**Functional Model Relevance:** {model.get('level', 'unknown')}", "",
        "## Key Findings",
    ]
    lines += [f"- {x}" for x in live.get("key_findings", [])]
    if cell.get("ok"):
        top = cell.get("top_malignant_state") or {}
        lines += ["", "## GBmap Cell-State Context"]
        lines.append(f"- Top malignant state: {top.get('state', 'N/A')}")
        lines.append(f"- Malignant-state patient prevalence: {pct(cell.get('malignant_patient_prevalence'))}")
        lines.append(f"- Malignant-cell expression breadth: {pct(cell.get('malignant_fraction_expressing'))}")
    lines += ["", "## Research Opportunities"]
    for row in live.get("research_opportunities", []):
        lines.append(f"- **{row['title']}** ({row['priority']}/100): {row['signal']}")
    lines += ["", "## Mechanistic Hypotheses"]
    for row in live.get("mechanistic_hypotheses", []):
        lines.append(f"- {row['hypothesis']} Falsification: {row['falsification_test']}")
    lines += ["", "## Experiment Prioritization"]
    for row in live.get("experiment_portfolio", []):
        lines.append(f"- **{row['experiment']}** ({row['priority']}/100): {row['design']}")
    lines += ["", "## Evidence Gaps"] + [f"- {x}" for x in profile.evidence_gaps]
    papers = live.get("literature", {}).get("top_papers") or []
    if papers:
        lines += ["", "## Relevant Publications"]
        for paper in papers:
            title = paper.get("title") or "Untitled"
            url = paper.get("url")
            identifier = paper.get("doi") or (f"PMID {paper.get('pmid')}" if paper.get("pmid") else "")
            lines.append((f"- [{title}]({url})" if url else f"- {title}") + (f" — {identifier}" if identifier else ""))
    lines += ["", f"**Generated:** {profile.dossier.generated_at}"]
    lines += ["", "## Data Source Status"] + [f"- **{k}:** {v}" for k, v in profile.source_status.items()]
    lines += ["", f"> {score.caveat}"]
    return "\n".join(lines)


def render_confidence(profile):
    live = profile.live
    overall = live.get("overall_evidence_confidence", {})
    model = live.get("model_relevance", {})
    by_dim = live.get("confidence_by_dimension", {})

    section_space()
    st.markdown("### Confidence & Model Relevance")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Overall Evidence Confidence", confidence_text(overall))
        for reason in overall.get("reasons", []):
            st.caption(reason)
    with c2:
        model_score = "N/A" if model.get("score") is None else f"{model.get('score')}/100"
        st.metric("Functional Model Relevance", f"{str(model.get('level', 'unknown')).title()} · {model_score}")
        for reason in model.get("reasons", []):
            st.caption(reason)
        if model.get("limitation"):
            st.caption(model["limitation"])

    rows = []
    for name, dimension in profile.score.dimensions.items():
        conf = by_dim.get(name, {})
        rows.append({
            "Evidence Dimension": name,
            "Evidence Score": None if dimension.score is None else round(dimension.score, 1),
            "Confidence": conf.get("level"),
            "Confidence Score": conf.get("score"),
            "Primary Source": dimension.source,
            "What Would Increase Confidence": "; ".join(conf.get("what_would_change_it", [])),
        })
    st.dataframe(rows, width="stretch", hide_index=True)
    st.caption("Confidence describes how strongly the available evidence supports the displayed conclusion. It is not the probability that a target will become a successful therapy.")


def render_discovery(profile):
    live = profile.live
    opportunities = live.get("research_opportunities", [])
    hypotheses = live.get("mechanistic_hypotheses", [])
    experiments = live.get("experiment_portfolio", [])

    section_space()
    st.markdown("### Research Opportunities")
    st.caption("Cross-source patterns that may define unusually informative follow-up questions. These remain hypotheses until experimentally tested.")
    if opportunities:
        for row in opportunities:
            with st.expander(f"{row['title']} · priority {row['priority']}/100", expanded=row.get("priority", 0) >= 70):
                st.write(row["signal"])
                st.markdown(f"**Recommended test:** {row['recommended_test']}")
                st.caption(f"Caution: {row['caution']}")
    else:
        st.info("No high-value cross-source opportunity pattern was detected from the currently available evidence.")

    section_space()
    st.markdown("### Mechanistic Hypotheses")
    st.caption("Only hypotheses whose required evidence premise passes the production guardrails are displayed.")
    if hypotheses:
        for idx, row in enumerate(hypotheses, start=1):
            with st.expander(f"Hypothesis {idx}: {row['hypothesis']}"):
                for observation in row.get("supporting_observations", []):
                    st.markdown(f"- {observation}")
                st.markdown(f"**Falsification test:** {row['falsification_test']}")
                st.caption(row.get("status", "Hypothesis"))
    else:
        st.info("Available evidence does not support a sufficiently specific guarded mechanistic hypothesis.")

    section_space()
    st.markdown("### Experiment Prioritization")
    st.caption("Ranks experiments by unresolved evidence and cross-source conflict. It is an uncertainty-reduction heuristic, not a statistical information-gain estimate.")
    if experiments:
        st.dataframe(experiments, width="stretch", hide_index=True)


def render_cell_state(cell: dict):
    st.markdown("#### Native GBmap Cell-State Context")
    if not cell.get("ok"):
        st.info(cell.get("error", "The compact GBmap reference is unavailable on this deployment."))
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
    for row in cell.get("states", [])[:25]:
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
        st.dataframe(rows, width="stretch", hide_index=True)
    st.caption(cell.get("interpretation", ""))


def render_profile(profile):
    live = profile.live
    score = profile.score
    identity = live.get("gene_identity", {})
    consistency = live.get("evidence_consistency", {})
    cbio = live.get("cbioportal", {})
    ot = live.get("open_targets", {})
    trials = live.get("clinical_trials", {})
    lit = live.get("literature", {})
    dep = live.get("depmap", {})
    ivy = live.get("ivy_gap", {})
    cgg = live.get("cgga", {})
    gla = live.get("glass", {})
    hpa = live.get("normal_tissue_context", {})
    network = live.get("interaction_network", {})
    bbb = live.get("bbb_candidates", {})
    cell = live.get("gbmap_cell_state", {})

    section_space(0.9)
    title = profile.gene
    if identity.get("ok") and identity.get("name"):
        title += f" | {identity['name']}"
    st.subheader(title)
    if identity.get("ok") and identity.get("was_normalized"):
        st.caption(f"Submitted symbol {identity.get('query')} was normalized to {identity.get('symbol')}.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Target Priority Score", "N/A" if score.overall is None else f"{score.overall}/100")
    m2.metric("Evidence Coverage", f"{score.evidence_coverage_pct}%")
    m3.metric("Evidence Confidence", confidence_text(live.get("overall_evidence_confidence", {})))
    m4.metric("Active GBM Trials", trials.get("active", 0))
    st.caption(f"{score.label}. {score.caveat}")

    section_space()
    left, right = st.columns(2)
    with left:
        st.markdown("### Key Findings")
        for finding in live.get("key_findings", []):
            st.markdown(f"- {finding}")
        if not live.get("key_findings"):
            st.write("No concise findings were generated from the available sources.")
    with right:
        st.markdown("### Evidence Consistency")
        st.write(consistency.get("status", "Not assessed"))
        for flag in consistency.get("flags", []):
            st.markdown(f"- {flag}")
        if not consistency.get("flags"):
            st.caption(consistency.get("note", ""))

    render_confidence(profile)
    render_discovery(profile)

    section_space()
    st.markdown("### Genomic Evidence")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("TCGA Mutation Frequency", pct((cbio.get("mutation") or {}).get("frequency")))
    g2.metric("TCGA Amplification Frequency", pct((cbio.get("copy_number") or {}).get("amplification_frequency")))
    g3.metric("TCGA Deep Deletion Frequency", pct((cbio.get("copy_number") or {}).get("deep_deletion_frequency")))
    g4.metric("Open Targets Association Score", num(ot.get("gbm_association_score"), 3))
    variants = (cbio.get("mutation") or {}).get("top_variants") or []
    if variants:
        st.markdown("#### Recurrent Protein Changes")
        st.dataframe(variants, width="stretch", hide_index=True)

    section_space()
    gap_col, study_col = st.columns(2)
    with gap_col:
        st.markdown("### Evidence Gaps")
        for gap in profile.evidence_gaps:
            st.markdown(f"- {gap}")
    with study_col:
        st.markdown("### Potential Validation Studies")
        for idea in profile.next_experiments:
            st.markdown(f"- {idea}")

    section_space(1.4)
    tabs = st.tabs([
        "Cell State, Functional & Spatial",
        "Human & Recurrence",
        "Translation & BBB",
        "Tissue & Network Context",
        "Evidence Record",
        "Literature",
        "Export",
    ])

    with tabs[0]:
        render_cell_state(cell)
        section_space(1.0)
        st.markdown("#### DepMap Functional Dependency")
        if dep.get("ok"):
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Strict GBM Models", dep.get("n_gbm"))
            d2.metric("Median GBM Chronos", num(dep.get("median_effect_gbm"), 2))
            d3.metric("Selectivity Difference", num(dep.get("median_selectivity_delta"), 2))
            d4.metric("One-Sided p Value", pval(dep.get("p_value")))
            st.caption(f"GBM definition: {dep.get('gbm_definition')}. Pan-essential: {'Yes' if dep.get('pan_essential') else 'No'}.")
            if dep.get("most_dependent_gbm_models"):
                st.dataframe(dep["most_dependent_gbm_models"], width="stretch", hide_index=True)
            nextgen = dep.get("nextgen_model_context") or {}
            if nextgen.get("metadata_available"):
                st.markdown("##### Model Format Context")
                n1, n2, n3, n4 = st.columns(4)
                n1.metric("NextGen 3D Models", nextgen.get("n_nextgen_3d_gbm", 0))
                n2.metric("Conventional Models", nextgen.get("n_conventional_gbm", 0))
                n3.metric("Median 3D Chronos", num(nextgen.get("median_nextgen_3d_chronos"), 2))
                n4.metric("Median Conventional", num(nextgen.get("median_conventional_chronos"), 2))
                st.caption(nextgen.get("interpretation", ""))
        else:
            st.info(dep.get("error", "DepMap evidence is unavailable."))

        section_space(1.0)
        st.markdown("#### Ivy GAP Anatomic Expression")
        if ivy.get("ok"):
            i1, i2, i3, i4 = st.columns(4)
            i1.metric("LMD Samples", ivy.get("n_samples"))
            i2.metric("Highest-Expression Zone", str(ivy.get("top_zone", "N/A")).replace("_", " ").title())
            i3.metric("Median Expression Range", num(ivy.get("median_range"), 2))
            i4.metric("Kruskal p Value", pval(ivy.get("p_value")))
            rows = [{
                "Anatomic Zone": z.replace("_", " ").title(),
                "Median log2(FPKM+1)": round(v, 3),
                "n": ivy.get("zone_counts", {}).get(z),
            } for z, v in ivy.get("zone_medians", {}).items()]
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            st.info(ivy.get("error", "Ivy GAP evidence is unavailable."))

    with tabs[1]:
        st.markdown("#### CGGA External Cohort Validation")
        if cgg.get("ok"):
            meta = cgg.get("meta_analysis") or {}
            c1, c2, c3 = st.columns(3)
            c1.metric("Usable Strict-GBM Cohorts", f"{cgg.get('n_usable_cohorts', 0)}/2")
            c2.metric("Pooled HR per 1 SD", num(meta.get("pooled_hr"), 2))
            c3.metric("Pooled p Value", pval(meta.get("pooled_p_value")))
            rows = [{
                "Cohort": row.get("cohort"), "Usable": row.get("ok"), "n": row.get("n"),
                "Events": row.get("events"), "HR per 1 SD": row.get("hr_per_sd"),
                "p Value": row.get("p_value"), "Status": row.get("error"),
            } for row in cgg.get("cohorts", [])]
            st.dataframe(rows, width="stretch", hide_index=True)
            if meta:
                direction = "consistent" if cgg.get("direction_consistent") else "discordant"
                st.caption(f"{meta.get('model')} effect meta-analysis | I²={meta.get('i_squared', 0):.1f}% | Direction: {direction}. Prognostic association is not causal evidence.")
        else:
            st.info("CGGA validation is unavailable in the strict GBM subset.")
        section_space(1.0)
        st.markdown("#### GLASS Longitudinal Validation")
        if gla.get("ok"):
            x1, x2, x3 = st.columns(3)
            x1.metric("Primary/Recurrent Pairs", gla.get("n_pairs"))
            x2.metric("Median Recurrence Change", num(gla.get("median_delta"), 3))
            x3.metric("Paired p Value", pval(gla.get("p_value")))
            st.caption(gla.get("scope", ""))
        elif gla.get("status") == "credentials_required":
            st.info("GLASS analysis requires an authorized Synapse token. This dimension remains unscored until access is configured.")
        else:
            st.info(gla.get("error", "GLASS longitudinal evidence is unavailable."))

    with tabs[2]:
        t1, t2, t3 = st.columns(3)
        t1.metric("Target-Directed Candidates", ot.get("known_drug_count", 0) if ot.get("ok") else "N/A")
        t2.metric("Highest Matching GBM Trial Phase", trials.get("max_phase", 0) if trials.get("ok") else "N/A")
        t3.metric("Matching GBM Trials", trials.get("total", 0) if trials.get("ok") else "N/A")
        if ot.get("drugs"):
            st.markdown("#### Target-Directed Candidates")
            st.dataframe(ot["drugs"], width="stretch", hide_index=True)
        if trials.get("studies"):
            st.markdown("#### Clinical Trial Matches")
            st.dataframe(trials["studies"], width="stretch", hide_index=True)
        section_space(1.0)
        st.markdown("#### Blood-Brain Barrier Evidence")
        if bbb.get("ok"):
            b1, b2, b3 = st.columns(3)
            b1.metric("Candidates Checked", bbb.get("candidates_checked", 0))
            b2.metric("B3DB Matches", bbb.get("matched_count", 0))
            b3.metric("BBB+ Records", bbb.get("bbb_positive_count", 0))
            if bbb.get("matches"):
                st.dataframe(bbb["matches"], width="stretch", hide_index=True)
            st.caption(bbb.get("interpretation", ""))
        else:
            st.info(bbb.get("error", "B3DB evidence is unavailable."))

    with tabs[3]:
        st.markdown("#### Gene Identity")
        if identity.get("ok"):
            st.dataframe([{
                "Canonical Symbol": identity.get("symbol"), "Approved Name": identity.get("name"),
                "Ensembl": identity.get("ensembl_gene_id"), "Entrez": identity.get("entrez_gene_id"),
                "Matched By": identity.get("matched_by"),
            }], width="stretch", hide_index=True)
            if identity.get("aliases"):
                st.caption("Known aliases: " + ", ".join(identity["aliases"][:15]))
        section_space(1.0)
        st.markdown("#### Normal Tissue and Brain Context")
        if hpa.get("ok"):
            h1, h2, h3 = st.columns(3)
            h1.metric("Tissue Specificity", hpa.get("tissue_specificity") or "N/A")
            h2.metric("Brain Single-Nuclei Specificity", hpa.get("single_nuclei_brain_specificity") or "N/A")
            h3.metric("Maximum Normal-Brain Expression", num(hpa.get("normal_brain_max_expression"), 1))
            if hpa.get("brain_region_expression"):
                st.dataframe([{"Brain Region": k, "Expression": v} for k, v in hpa["brain_region_expression"].items()], width="stretch", hide_index=True)
            st.caption(hpa.get("interpretation", ""))
            if hpa.get("source_url"):
                st.link_button("Open Human Protein Atlas", hpa["source_url"])
        else:
            st.info(hpa.get("error", "Human Protein Atlas context is unavailable."))
        section_space(1.0)
        st.markdown("#### Interaction Network and Pathways")
        if network.get("ok"):
            if network.get("partners"):
                st.dataframe(network["partners"], width="stretch", hide_index=True)
            if network.get("enrichment"):
                st.markdown("##### Network Enrichment")
                st.dataframe(network["enrichment"], width="stretch", hide_index=True)
            st.caption(network.get("interpretation", ""))
            if network.get("source_url"):
                st.link_button("Open STRING Network", network["source_url"])
        else:
            st.info(network.get("error", "STRING network context is unavailable."))

    with tabs[4]:
        if not profile.dossier.evidence:
            st.info("No evidence records were returned. Review source status for availability.")
        for tier in EvidenceTier:
            records = profile.dossier.by_tier(tier)
            if not records:
                continue
            with st.expander(f"{tier.value.replace('_', ' ').title()} ({len(records)})", expanded=tier in (EvidenceTier.OBSERVED_DATA, EvidenceTier.STATISTICAL_ASSOCIATION)):
                for record in records:
                    st.markdown(f"**{record.claim_text}**")
                    stats = []
                    if record.statistic_name and record.statistic_value is not None:
                        stats.append(f"{record.statistic_name}={record.statistic_value:.4g}")
                    if record.p_value is not None:
                        stats.append(f"p={record.p_value:.3g}")
                    if record.provenance.sample_size:
                        stats.append(f"n={record.provenance.sample_size}")
                    if stats:
                        st.caption(" | ".join(stats))
                    provenance = record.provenance
                    retrieved = str(provenance.retrieved_at or "")[:10] or "N/A"
                    version = provenance.dataset_version or "live/current"
                    st.caption(f"Source: {provenance.source_dataset} | Version: {version} | Confidence: {record.confidence.value} | Access: {provenance.access_tier.value} | Retrieved: {retrieved}")
                    if provenance.method:
                        st.caption(f"Method: {provenance.method}")
                    if provenance.citation_url:
                        st.markdown(f"[Open source / citation]({provenance.citation_url})")
                    for caveat in record.caveats:
                        st.caption(f"Caveat: {caveat}")
                    st.divider()

    with tabs[5]:
        l1, l2 = st.columns([1, 2])
        with l1:
            st.metric("GBM Literature Co-Mentions", lit.get("hit_count", 0) if lit.get("ok") else "N/A")
            st.dataframe([{"Disease Context": k.replace("_", " ").title(), "Indexed Publications": v} for k, v in profile.context_map.items()], width="stretch", hide_index=True)
        with l2:
            papers = lit.get("top_papers") or []
            if papers:
                st.markdown("#### Relevant Publications")
                for paper in papers:
                    title = str(paper.get("title") or "Untitled")
                    safe_title = title.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
                    if paper.get("url"):
                        st.markdown(f"**[{safe_title}]({paper['url']})**")
                    else:
                        st.markdown(f"**{title}**")
                    if paper.get("authors"):
                        st.caption(paper.get("authors"))
                    metadata = " | ".join(str(x) for x in [paper.get("journal"), paper.get("year"), paper.get("pmid") and f"PMID {paper.get('pmid')}", paper.get("doi") and f"DOI {paper.get('doi')}"] if x)
                    if metadata:
                        st.caption(metadata)

    with tabs[6]:
        st.download_button(
            "Download Full Research Profile (JSON)",
            json.dumps(profile.to_dict(), indent=2, default=str),
            file_name=f"{profile.gene}_gbm_gene_analysis.json",
            mime="application/json",
        )
        st.download_button(
            "Download Research Summary (Markdown)",
            markdown_brief(profile),
            file_name=f"{profile.gene}_gbm_gene_analysis.md",
            mime="text/markdown",
        )


st.title("GBM Gene Analysis")
st.caption("GBM-specific molecular evidence synthesis, research-opportunity discovery, and experiment prioritization.")
st.write(
    "Enter a gene, compare a target pair, or provide processed gene-level experimental results. The tool integrates GBM genomics, functional dependency, cell-state and spatial context, independent human cohorts, recurrence, clinical translation, literature, normal-brain context, interaction networks, and BBB evidence, then separates observed evidence from confidence, hypotheses, and recommended validation experiments."
)
st.caption("Note: This is a molecular research decision-support tool. It is not intended for clinical decision-making or patient treatment selection.")

analysis_tab, discovery_tab, researcher_tab, batch_tab, methods_tab = st.tabs([
    "Gene Analysis",
    "Target Pair Analysis",
    "Researcher Data",
    "Gene Set Comparison",
    "Methods & Scope",
])

with analysis_tab:
    input_col, button_col = st.columns([4, 1], vertical_alignment="bottom")
    with input_col:
        gene = st.text_input("Gene symbol", value="EGFR", placeholder="e.g. EGFR, PTEN, TERT, CDK6").strip()
    with button_col:
        run = st.button("Build Research Profile", type="primary", width="stretch")
    if run:
        try:
            with st.spinner(f"Assembling and cross-examining GBM evidence for {gene.upper()}..."):
                st.session_state["profile_v7"] = cached_profile(gene)
        except Exception as exc:
            st.error(f"Could not build the profile: {exc}")
    profile = st.session_state.get("profile_v7")
    if profile:
        render_profile(profile)

with discovery_tab:
    st.subheader("State-Aware Target Pair Analysis")
    st.write("Evaluate whether two genes justify a complementary-target experiment across functional evidence, networks, GBM cell states, spatial context, recurrence, CNS feasibility, and model relevance. This does not predict pharmacologic synergy.")
    a_col, b_col, run_col = st.columns([2, 2, 1], vertical_alignment="bottom")
    with a_col:
        gene_a = st.text_input("Target A", value="EGFR", key="pair_a_v7").strip()
    with b_col:
        gene_b = st.text_input("Target B", value="CDK4", key="pair_b_v7").strip()
    with run_col:
        pair_run = st.button("Analyze Pair", type="primary", width="stretch")
    if pair_run:
        try:
            with st.spinner(f"Evaluating {gene_a.upper()} + {gene_b.upper()} across complementary GBM evidence..."):
                st.session_state["pair_v7"] = cached_pair(gene_a, gene_b)
        except Exception as exc:
            st.error(f"Pair analysis failed: {exc}")
    pair = st.session_state.get("pair_v7")
    if pair:
        section_space()
        p1, p2, p3 = st.columns(3)
        p1.metric("Combination Rationale Score", f"{pair.get('combination_rationale_score', 'N/A')}/100")
        p2.metric("Evidence Coverage", f"{pair.get('evidence_coverage_pct', 'N/A')}%")
        p3.metric("Pair Evidence Confidence", confidence_text(pair.get("pair_evidence_confidence", {})))
        st.caption(pair.get("caveat", ""))
        st.markdown("### Rationale Components")
        st.dataframe([{"Component": k.replace("_", " ").title(), "Score": v} for k, v in pair.get("components", {}).items()], width="stretch", hide_index=True)
        left, right = st.columns(2)
        with left:
            st.markdown("### Why Test It")
            for item in pair.get("why_test_it", []):
                st.markdown(f"- {item}")
        with right:
            st.markdown("### Risks / Failure Modes")
            for item in pair.get("risks", []):
                st.markdown(f"- {item}")
            if not pair.get("risks"):
                st.write("No major pair-specific risk flag was generated from the available evidence.")
        st.markdown("### Model Relevance")
        model_rows = [{"Gene": gene_name, **model} for gene_name, model in pair.get("model_relevance", {}).items()]
        if model_rows:
            st.dataframe(model_rows, width="stretch", hide_index=True)
        st.markdown("### Validation Sequence")
        for idx, item in enumerate(pair.get("validation_sequence", []), start=1):
            st.markdown(f"{idx}. {item}")

with researcher_tab:
    st.subheader("Processed Researcher Result Analysis")
    st.write("Upload a processed gene-level result such as differential expression, a model coefficient, or a signed CRISPR statistic. Effect size is required; p-value and FDR are optional but used when supplied. Raw FASTQ/count-matrix processing is intentionally outside this tool's scope.")
    uploaded = st.file_uploader("Upload CSV or TSV", type=["csv", "tsv", "txt"])
    default_text = "gene,effect,p_value,fdr\nEGFR,2.4,0.0001,0.002\nSOX2,1.8,0.001,0.01\nSTAT3,1.5,0.004,0.02\nCDK6,1.2,0.01,0.04\nOLIG2,-1.1,0.02,0.05\nGFAP,-1.4,0.001,0.01\nCDKN1A,-1.7,0.0005,0.005\nBAX,-2.0,0.0001,0.002"
    pasted = st.text_area("Or paste a processed table", value=default_text, height=200)
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
            p_col = st.selectbox("p-value column (optional)", optional, index=(columns.index("p_value") + 1 if "p_value" in columns else 0))
        with c4:
            fdr_col = st.selectbox("FDR/q-value column (optional)", optional, index=(columns.index("fdr") + 1 if "fdr" in columns else 0))
        preview_cols = [gene_col, value_col] + ([p_col] if p_col != "None" else []) + ([fdr_col] if fdr_col != "None" else [])
        st.dataframe(signature_df[preview_cols].head(20), width="stretch", hide_index=True)
        if st.button("Analyze Research Result", type="primary"):
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
                with st.spinner("Interpreting the processed result against GBM evidence, pathways, cell-state context and perturbational signatures..."):
                    st.session_state["signature_v7"] = cached_signature(genes_clean, values_clean, p_clean, fdr_clean)
            except Exception as exc:
                st.error(f"Research-result analysis failed: {exc}")

    signature = st.session_state.get("signature_v7")
    if signature:
        section_space()
        s1, s2 = st.columns(2)
        s1.metric("Input Genes", signature.get("n_input_genes"))
        s2.metric("Statistically Supported", signature.get("n_statistically_supported") if signature.get("statistics_provided") else "Not supplied")
        st.markdown("### GBM-Prioritized Signals")
        st.dataframe(signature.get("top_genes_profiled", []), width="stretch", hide_index=True)
        st.caption(signature.get("interpretation", ""))
        e1, e2 = st.columns(2)
        with e1:
            st.markdown("### Upregulated Program Enrichment")
            up = signature.get("up_pathway_enrichment", {})
            if up.get("ok"):
                st.dataframe(up.get("results", []), width="stretch", hide_index=True)
            else:
                st.info(up.get("error", "No enrichment available."))
        with e2:
            st.markdown("### Downregulated Program Enrichment")
            down = signature.get("down_pathway_enrichment", {})
            if down.get("ok"):
                st.dataframe(down.get("results", []), width="stretch", hide_index=True)
            else:
                st.info(down.get("error", "No enrichment available."))
        section_space()
        st.markdown("### Perturbational Reversal Hypotheses")
        l1000 = signature.get("l1000_reversal", {})
        if l1000.get("ok"):
            st.dataframe(l1000.get("top_drugs", []), width="stretch", hide_index=True)
            if l1000.get("combinations"):
                st.markdown("#### L1000 Combination Hypotheses")
                st.dataframe(l1000["combinations"], width="stretch", hide_index=True)
            st.caption(l1000.get("interpretation", ""))
        else:
            st.info(l1000.get("error", "L1000 reversal analysis is unavailable."))
        st.download_button("Download Result Analysis (JSON)", json.dumps(signature, indent=2, default=str), file_name="gbm_researcher_result_analysis.json", mime="application/json")

with batch_tab:
    st.write("Enter a short gene set to compare targets using the same scored evidence, confidence and final-scope context model.")
    raw = st.text_area("Gene symbols", value="EGFR, PTEN, TP53, CDK4", key="batch_genes_v7")
    genes = list(dict.fromkeys(x.strip() for x in raw.replace(",", " ").split() if x.strip()))
    if len(genes) > 6:
        st.warning("Gene set comparison is limited to 6 genes per run to maintain reasonable load on public sources.")
        genes = genes[:6]
    if st.button("Compare Gene Set", type="primary") and genes:
        try:
            with st.spinner("Building and comparing multi-source profiles..."):
                profiles = cached_batch(tuple(genes))
            rows = []
            for item in profiles:
                item_live = item.live
                top_opp = (item_live.get("research_opportunities") or [{}])[0]
                top_state = ((item_live.get("gbmap_cell_state") or {}).get("top_malignant_state") or {}).get("state")
                rows.append({
                    "Gene": item.gene,
                    "Target Priority Score": item.score.overall,
                    "Evidence Coverage (%)": item.score.evidence_coverage_pct,
                    "Evidence Confidence": (item_live.get("overall_evidence_confidence") or {}).get("score"),
                    "Model Relevance": (item_live.get("model_relevance") or {}).get("level"),
                    "Top Malignant State": top_state,
                    "Top Research Opportunity": top_opp.get("title"),
                    "Opportunity Priority": top_opp.get("priority"),
                    "DepMap Selectivity Difference": item_live.get("depmap", {}).get("median_selectivity_delta"),
                    "Usable CGGA Cohorts": item_live.get("cgga", {}).get("n_usable_cohorts", 0),
                    "Active GBM Trials": item_live.get("clinical_trials", {}).get("active", 0),
                })
            st.dataframe(rows, width="stretch", hide_index=True)
        except Exception as exc:
            st.error(f"Gene set comparison failed: {exc}")

with methods_tab:
    st.markdown("### Frozen Product Scope")
    st.write("GBM Gene Analysis is deliberately limited to GBM molecular research decision support: gene or processed researcher result → evidence → biological context → contradictions → testable hypothesis → highest-value experiment. New modalities are not added unless they materially improve this workflow.")
    section_space(0.7)
    st.markdown("### Scored Evidence Model")
    st.write("The validated Target Priority Score remains separate from V7 context layers. It integrates TCGA/cBioPortal, Open Targets, ClinicalTrials.gov, Europe PMC, DepMap, Ivy GAP, CGGA and strict GLASS recurrence evidence when authorized. Missing sources reduce coverage rather than becoming negative biology.")
    section_space(0.7)
    st.markdown("### Native GBmap Cell-State Intelligence")
    st.write("Production queries use a compact, precomputed reference derived from the published GBmap CELLxGENE atlas. The full Core GBmap H5AD is never downloaded per user query; production uses a compact patient-aware reference built offline from the published Core atlas. Cell-state expression and patient prevalence are contextual evidence and do not change the Target Priority Score.")
    section_space(0.7)
    st.markdown("### Confidence & Model Relevance")
    st.write("Confidence is distinct from signal strength. It reflects sample size, replication, statistical support, cross-source consistency and evidence availability. Model relevance separately flags whether functional results come mainly from conventional models or include next-generation 3D contexts.")
    section_space(0.7)
    st.markdown("### Researcher Results")
    st.write("The upload workflow accepts processed gene-level results only. Optional p-values/FDR influence follow-up prioritization, while pathway enrichment and L1000 reversal remain hypothesis-generation layers. The tool does not re-run or replace the experiment's original statistical model.")
    section_space(0.7)
    st.markdown("### Target Pairs")
    st.write("Pair analysis asks whether two targets justify a combination experiment based on individual evidence, functional support, network and malignant-state complementarity, spatial/recurrence context, CNS feasibility and model limitations. It never labels a pair synergistic without direct synergy data.")
    section_space(0.7)
    st.markdown("### Benchmarking")
    st.write("Current-data regression tests are separated from true retrospective validation. A historical discovery is only counted as retrospective evidence when the benchmark uses frozen or date-bounded evidence that predates the discovery. Prospective hypotheses can be registered and evaluated later without rewriting the benchmark.")
