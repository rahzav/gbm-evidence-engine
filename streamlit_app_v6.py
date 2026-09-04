"""Streamlit interface for GBM Gene Analysis V6."""
from __future__ import annotations

import io
import json

import pandas as pd
import streamlit as st

from gbm_evidence_engine.evidence_model import EvidenceTier
from gbm_evidence_engine.research_intelligence_v6 import (
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
    return rank_gene_list(list(genes), max_workers=2)


@st.cache_data(ttl=3600, max_entries=4, show_spinner=False)
def cached_pair(gene_a: str, gene_b: str):
    return evaluate_gene_pair(gene_a, gene_b)


@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def cached_signature(genes: tuple[str, ...], values: tuple[float, ...]):
    return analyze_researcher_signature(genes, values)


def pct(value):
    return "N/A" if value is None else f"{100 * float(value):.1f}%"


def num(value, digits=2):
    if value is None:
        return "N/A"
    return f"{float(value):.{digits}f}" if isinstance(value, (float, int)) else str(value)


def pval(value):
    if value is None:
        return "N/A"
    return f"{float(value):.2g}"


def section_space(size: float = 1.25):
    st.markdown(f"<div style='height:{size}rem'></div>", unsafe_allow_html=True)


def markdown_brief(profile) -> str:
    score = profile.score
    live = profile.live
    lines = [
        f"# GBM Gene Analysis: {profile.gene}", "",
        f"**Target Priority Score:** {score.overall if score.overall is not None else 'N/A'}/100 ({score.label})",
        f"**Evidence Coverage:** {score.evidence_coverage_pct}%", "",
        "## Key Findings",
    ]
    lines += [f"- {x}" for x in live.get("key_findings", [])]
    lines += ["", "## Research Opportunities"]
    for row in live.get("research_opportunities", []):
        lines.append(f"- **{row['title']}** ({row['priority']}/100): {row['signal']}")
    lines += ["", "## Mechanistic Hypotheses"]
    for row in live.get("mechanistic_hypotheses", []):
        lines.append(f"- {row['hypothesis']} Falsification: {row['falsification_test']}")
    lines += ["", "## Experiment Prioritization"]
    for row in live.get("experiment_portfolio", []):
        lines.append(f"- **{row['experiment']}** ({row['priority']}/100): {row['design']}")
    lines += ["", "## Score Composition"]
    for name, dimension in score.dimensions.items():
        lines.append(f"- **{name}:** {num(dimension.score, 1)}/100. {dimension.rationale}")
    lines += ["", "## Evidence Gaps"] + [f"- {x}" for x in profile.evidence_gaps]
    lines += ["", "## Potential Validation Studies"] + [f"- {x}" for x in profile.next_experiments]
    lines += ["", "## Data Source Status"] + [f"- **{k}:** {v}" for k, v in profile.source_status.items()]
    lines += ["", f"> {score.caveat}"]
    return "\n".join(lines)


def render_discovery(profile):
    opportunities = profile.live.get("research_opportunities", [])
    hypotheses = profile.live.get("mechanistic_hypotheses", [])
    experiments = profile.live.get("experiment_portfolio", [])

    section_space()
    st.markdown("### Research Opportunities")
    st.caption("Cross-source patterns that may define unusually informative follow-up questions. These are research hypotheses, not validated biological conclusions.")
    if opportunities:
        for row in opportunities:
            with st.expander(f"{row['title']} · priority {row['priority']}/100", expanded=row["priority"] >= 70):
                st.write(row["signal"])
                st.markdown(f"**Recommended test:** {row['recommended_test']}")
                st.caption(f"Caution: {row['caution']}")
    else:
        st.info("No high-value cross-source opportunity pattern was detected from the currently available evidence.")

    section_space()
    st.markdown("### Mechanistic Hypotheses")
    st.caption("Falsifiable hypotheses assembled from observed dependency, spatial, longitudinal, and interaction-network structure.")
    if hypotheses:
        for idx, row in enumerate(hypotheses, start=1):
            with st.expander(f"Hypothesis {idx}: {row['hypothesis']}"):
                for observation in row.get("supporting_observations", []):
                    st.markdown(f"- {observation}")
                st.markdown(f"**Falsification test:** {row['falsification_test']}")
                st.caption(row.get("status", "Hypothesis"))
    else:
        st.info("Available sources do not yet support a sufficiently specific mechanistic hypothesis.")

    section_space()
    st.markdown("### Experiment Prioritization")
    st.caption("Ranks experiments by unresolved evidence and cross-source conflict. The priority is an uncertainty-reduction heuristic, not a statistical information-gain calculation.")
    if experiments:
        st.dataframe(experiments, width="stretch", hide_index=True)


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
    gbmap = live.get("gbmap_reference", {})

    section_space(1.0)
    title = profile.gene
    if identity.get("ok") and identity.get("name"):
        title += f" | {identity['name']}"
    st.subheader(title)
    if identity.get("ok") and identity.get("was_normalized"):
        st.caption(f"Submitted symbol {identity.get('query')} was normalized to {identity.get('symbol')}.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Target Priority Score", "N/A" if score.overall is None else f"{score.overall}/100")
    m2.metric("Evidence Coverage", f"{score.evidence_coverage_pct}%")
    m3.metric("Evidence Records", len(profile.dossier.evidence))
    m4.metric("Active GBM Trials", trials.get("active", 0))
    st.caption(f"{score.label}. {score.caveat}")

    section_space()
    findings_col, review_col = st.columns(2)
    with findings_col:
        st.markdown("### Key Findings")
        findings = live.get("key_findings", [])
        if findings:
            for finding in findings:
                st.markdown(f"- {finding}")
        else:
            st.write("No concise findings were generated from the available sources.")
    with review_col:
        st.markdown("### Evidence Consistency")
        st.write(consistency.get("status", "Not assessed"))
        for flag in consistency.get("flags", []):
            st.markdown(f"- {flag}")
        if not consistency.get("flags"):
            st.caption(consistency.get("note", ""))

    render_discovery(profile)

    section_space()
    st.markdown("### Priority Score Composition")
    score_rows = [{
        "Evidence Dimension": name,
        "Score": None if d.score is None else round(d.score, 1),
        "Weight": f"{d.weight:.0%}",
        "Primary Source": d.source,
        "Interpretation": d.rationale,
    } for name, d in score.dimensions.items()]
    st.dataframe(score_rows, width="stretch", hide_index=True)

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
    gaps_col, studies_col = st.columns(2)
    with gaps_col:
        st.markdown("### Evidence Gaps")
        for gap in profile.evidence_gaps:
            st.markdown(f"- {gap}")
    with studies_col:
        st.markdown("### Potential Validation Studies")
        for idea in profile.next_experiments:
            st.markdown(f"- {idea}")

    section_space(1.5)
    detail_tabs = st.tabs([
        "Functional & Spatial",
        "Human Validation",
        "Translation & BBB",
        "Tissue & Network Context",
        "Evidence Record",
        "Literature",
        "Export",
    ])

    with detail_tabs[0]:
        st.markdown("#### DepMap Functional Dependency")
        if dep.get("ok"):
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Strict GBM Models", dep.get("n_gbm"))
            d2.metric("Median GBM Chronos Score", num(dep.get("median_effect_gbm"), 2))
            d3.metric("Selectivity Difference", num(dep.get("median_selectivity_delta"), 2))
            d4.metric("One-Sided p Value", pval(dep.get("p_value")))
            st.caption(
                f"GBM definition: {dep.get('gbm_definition')}. Pan-essential classification: {'Yes' if dep.get('pan_essential') else 'No'}."
            )
            if dep.get("most_dependent_gbm_models"):
                st.dataframe(dep["most_dependent_gbm_models"], width="stretch", hide_index=True)

            nextgen = dep.get("nextgen_model_context") or {}
            if nextgen.get("metadata_available"):
                section_space(0.8)
                st.markdown("##### Next-Generation 3D Model Context")
                n1, n2, n3, n4 = st.columns(4)
                n1.metric("NextGen 3D GBM Models", nextgen.get("n_nextgen_3d_gbm", 0))
                n2.metric("Conventional GBM Models", nextgen.get("n_conventional_gbm", 0))
                n3.metric("Median 3D Chronos", num(nextgen.get("median_nextgen_3d_chronos"), 2))
                n4.metric("Median Conventional Chronos", num(nextgen.get("median_conventional_chronos"), 2))
                st.caption(nextgen.get("interpretation", ""))
        else:
            st.info(dep.get("error", "DepMap evidence is unavailable."))

        section_space(1.0)
        st.markdown("#### Ivy GAP Spatial Expression")
        if ivy.get("ok"):
            i1, i2, i3, i4 = st.columns(4)
            i1.metric("LMD Samples", ivy.get("n_samples"))
            i2.metric("Highest-Expression Anatomic Zone", str(ivy.get("top_zone", "N/A")).replace("_", " ").title())
            i3.metric("Median Expression Range", num(ivy.get("median_range"), 2))
            i4.metric("Kruskal p Value", pval(ivy.get("p_value")))
            zone_rows = [{
                "Anatomic Zone": zone.replace("_", " ").title(),
                "Median log2(FPKM+1)": round(value, 3),
                "n": ivy.get("zone_counts", {}).get(zone),
            } for zone, value in ivy.get("zone_medians", {}).items()]
            st.dataframe(zone_rows, width="stretch", hide_index=True)
        else:
            st.info(ivy.get("error", "Ivy GAP evidence is unavailable."))

    with detail_tabs[1]:
        st.markdown("#### CGGA External Cohort Validation")
        if cgg.get("ok"):
            meta = cgg.get("meta_analysis")
            c1, c2, c3 = st.columns(3)
            c1.metric("Usable Strict-GBM Cohorts", f"{cgg.get('n_usable_cohorts', 0)}/2")
            c2.metric("Pooled HR per 1 SD", num((meta or {}).get("pooled_hr"), 2))
            c3.metric("Pooled p Value", pval((meta or {}).get("pooled_p_value")))
            cohort_rows = [{
                "Cohort": row.get("cohort"), "Usable": row.get("ok"), "n": row.get("n"),
                "Events": row.get("events"), "HR per 1 SD": row.get("hr_per_sd"),
                "p Value": row.get("p_value"), "Status": row.get("error"),
            } for row in cgg.get("cohorts", [])]
            st.dataframe(cohort_rows, width="stretch", hide_index=True)
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
            st.info("GLASS GBM-specific longitudinal analysis requires an authorized Synapse token. This dimension remains unscored until credentials are configured.")
        else:
            st.info(gla.get("error", "GLASS longitudinal evidence is unavailable."))

    with detail_tabs[2]:
        t1, t2, t3 = st.columns(3)
        t1.metric("Target-Directed Candidates", ot.get("known_drug_count", 0) if ot.get("ok") else "N/A")
        t2.metric("Highest Matching GBM Trial Phase", trials.get("max_phase", 0) if trials.get("ok") else "N/A")
        t3.metric("Matching GBM Trials", trials.get("total", 0) if trials.get("ok") else "N/A")
        if ot.get("drugs"):
            st.markdown("#### Target-Directed Candidates")
            st.dataframe(ot["drugs"], width="stretch", hide_index=True)
        if trials.get("studies"):
            section_space(0.8)
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

    with detail_tabs[3]:
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
            h3.metric("Maximum Displayed Normal-Brain Expression", num(hpa.get("normal_brain_max_expression"), 1))
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

        section_space(1.0)
        st.markdown("#### GBmap Single-Cell and Spatial Reference")
        st.write(gbmap.get("scope", "Public GBM single-cell/spatial reference collection."))
        st.caption("The current public deployment does not download the full >1M-cell atlas for each query. Native quantitative GBmap analysis requires a precomputed/queryable atlas service to remain reproducible and resource-safe.")
        if gbmap.get("collection_url"):
            st.link_button("Open GBmap Collection", gbmap["collection_url"])

    with detail_tabs[4]:
        if not profile.dossier.evidence:
            st.info("No evidence records were returned. Review data source status for availability.")
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
                    st.caption(f"Source: {record.provenance.source_dataset} | Confidence: {record.confidence.value} | Access: {record.provenance.access_tier.value}")
                    for caveat in record.caveats:
                        st.caption(f"Caveat: {caveat}")
                    st.divider()

    with detail_tabs[5]:
        l1, l2 = st.columns([1, 2])
        with l1:
            st.metric("GBM Literature Co-Mentions", lit.get("hit_count", 0) if lit.get("ok") else "N/A")
            st.dataframe([{"Disease Context": key.replace("_", " ").title(), "Indexed Publications": value} for key, value in profile.context_map.items()], width="stretch", hide_index=True)
        with l2:
            papers = lit.get("top_papers") or []
            if papers:
                st.markdown("#### Relevant Publications")
                for paper in papers:
                    st.markdown(f"**{paper.get('title') or 'Untitled'}**")
                    metadata = " | ".join(str(x) for x in [paper.get("journal"), paper.get("year"), paper.get("pmid") and f"PMID {paper.get('pmid')}"] if x)
                    if metadata:
                        st.caption(metadata)

    with detail_tabs[6]:
        profile_json = json.dumps(profile.to_dict(), indent=2, default=str)
        st.download_button("Download Full Research Profile (JSON)", profile_json, file_name=f"{profile.gene}_gbm_gene_analysis.json", mime="application/json")
        brief = markdown_brief(profile)
        st.download_button("Download Research Summary (Markdown)", brief, file_name=f"{profile.gene}_gbm_gene_analysis.md", mime="text/markdown")


st.title("GBM Gene Analysis")
st.caption("Integrated gene-level evidence synthesis and research-discovery analysis for glioblastoma.")
st.write(
    "Enter a gene symbol to generate a GBM-specific research profile. The analysis integrates tumor genomics, functional dependency, spatial expression, independent patient cohorts, longitudinal recurrence, clinical translation, literature, normal-tissue context, interaction networks, and available blood-brain barrier evidence. V6 also identifies cross-source research opportunities, builds falsifiable mechanistic hypotheses, prioritizes uncertainty-reducing experiments, evaluates target pairs, and interprets researcher-provided expression signatures."
)
st.caption("Note: Results are intended for research prioritization and hypothesis development, not clinical decision-making.")

analysis_tab, discovery_tab, researcher_tab, batch_tab, methods_tab = st.tabs([
    "Gene Analysis",
    "Discovery Lab",
    "Researcher Data",
    "Gene Set Comparison",
    "Methods & Data Sources",
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
                st.session_state["profile_v6"] = cached_profile(gene)
        except Exception as exc:
            st.error(f"Could not build the profile: {exc}")

    profile = st.session_state.get("profile_v6")
    if profile:
        render_profile(profile)

with discovery_tab:
    st.subheader("Target Pair Analysis")
    st.write("Evaluate whether two genes provide a defensible experimental rationale for complementary targeting. This does not predict pharmacologic synergy.")
    a_col, b_col, run_col = st.columns([2, 2, 1], vertical_alignment="bottom")
    with a_col:
        gene_a = st.text_input("Target A", value="EGFR", key="pair_a").strip()
    with b_col:
        gene_b = st.text_input("Target B", value="CDK4", key="pair_b").strip()
    with run_col:
        pair_run = st.button("Analyze Pair", type="primary", width="stretch")

    if pair_run:
        try:
            with st.spinner(f"Evaluating {gene_a.upper()} + {gene_b.upper()} across functional, network, spatial, recurrence, and translational evidence..."):
                st.session_state["pair_v6"] = cached_pair(gene_a, gene_b)
        except Exception as exc:
            st.error(f"Pair analysis failed: {exc}")

    pair = st.session_state.get("pair_v6")
    if pair:
        section_space()
        p1, p2, p3 = st.columns(3)
        p1.metric("Combination Rationale Score", f"{pair.get('combination_rationale_score', 'N/A')}/100")
        p2.metric("Evidence Coverage", f"{pair.get('evidence_coverage_pct', 'N/A')}%")
        p3.metric("Direct STRING Interaction", "Yes" if pair.get("direct_string_interaction") else "No")
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
            if pair.get("risks"):
                for item in pair["risks"]:
                    st.markdown(f"- {item}")
            else:
                st.write("No major pair-specific risk flag was generated from the available evidence.")
        st.markdown("### Validation Sequence")
        for idx, item in enumerate(pair.get("validation_sequence", []), start=1):
            st.markdown(f"{idx}. {item}")

with researcher_tab:
    st.subheader("Researcher Signature Analysis")
    st.write("Upload or paste a signed gene-level result such as log2 fold-change, model coefficient, CRISPR effect difference, or another signed statistic. The tool cross-references the strongest signals against GBM evidence and searches LINCS/L1000 for perturbations predicted to reverse the uploaded signature.")
    uploaded = st.file_uploader("Upload CSV or TSV", type=["csv", "tsv", "txt"])
    default_text = "EGFR,2.4\nSOX2,1.8\nSTAT3,1.5\nCDK6,1.2\nOLIG2,-1.1\nGFAP,-1.4\nCDKN1A,-1.7\nBAX,-2.0"
    pasted = st.text_area("Or paste gene,value rows", value=default_text, height=180)

    signature_df = None
    try:
        if uploaded is not None:
            raw_bytes = uploaded.getvalue()
            signature_df = pd.read_csv(io.BytesIO(raw_bytes), sep=None, engine="python")
        elif pasted.strip():
            signature_df = pd.read_csv(io.StringIO(pasted), header=None, names=["gene", "value"])
    except Exception as exc:
        st.error(f"Could not parse the signature: {exc}")

    if signature_df is not None and not signature_df.empty:
        columns = list(signature_df.columns)
        c1, c2 = st.columns(2)
        with c1:
            gene_col = st.selectbox("Gene column", columns, index=0)
        with c2:
            value_col = st.selectbox("Signed value column", columns, index=1 if len(columns) > 1 else 0)
        preview = signature_df[[gene_col, value_col]].head(20)
        st.dataframe(preview, width="stretch", hide_index=True)
        if st.button("Analyze Research Signature", type="primary"):
            try:
                gene_values = signature_df[gene_col].astype(str).tolist()
                numeric_values = pd.to_numeric(signature_df[value_col], errors="coerce")
                clean = [(g, float(v)) for g, v in zip(gene_values, numeric_values) if pd.notna(v)]
                with st.spinner("Cross-referencing the signature with GBM evidence and querying perturbational reversal signatures..."):
                    st.session_state["signature_v6"] = cached_signature(
                        tuple(g for g, _ in clean), tuple(v for _, v in clean)
                    )
            except Exception as exc:
                st.error(f"Signature analysis failed: {exc}")

    signature = st.session_state.get("signature_v6")
    if signature:
        section_space()
        st.markdown("### GBM-Prioritized Signals")
        st.dataframe(signature.get("top_genes_profiled", []), width="stretch", hide_index=True)
        st.caption(signature.get("interpretation", ""))

        l1000 = signature.get("l1000_reversal", {})
        section_space()
        st.markdown("### Perturbational Reversal Hypotheses")
        if l1000.get("ok"):
            st.write("Small-molecule signatures ranked for opposing the researcher-provided expression state.")
            st.dataframe(l1000.get("top_drugs", []), width="stretch", hide_index=True)
            if l1000.get("combinations"):
                st.markdown("#### L1000 Combination Hypotheses")
                st.dataframe(l1000["combinations"], width="stretch", hide_index=True)
            st.caption(l1000.get("interpretation", ""))
        else:
            st.info(l1000.get("error", "L1000 reversal analysis is unavailable."))

        st.download_button(
            "Download Signature Analysis (JSON)",
            json.dumps(signature, indent=2, default=str),
            file_name="gbm_researcher_signature_analysis.json",
            mime="application/json",
        )

with batch_tab:
    st.write("Enter a short gene set to compare targets using the same scored evidence and discovery model.")
    raw = st.text_area("Gene symbols", value="EGFR, PTEN, TP53, CDK4", key="batch_genes")
    genes = list(dict.fromkeys(x.strip() for x in raw.replace(",", " ").split() if x.strip()))
    if len(genes) > 6:
        st.warning("Gene set comparison is limited to 6 genes per run to maintain reasonable load on public research sources.")
        genes = genes[:6]
    if st.button("Compare Gene Set", type="primary") and genes:
        try:
            with st.spinner("Building and comparing multi-source profiles..."):
                profiles = cached_batch(tuple(genes))
            rows = []
            for item in profiles:
                item_live = item.live
                item_dep = item_live.get("depmap", {})
                item_cgg = item_live.get("cgga", {})
                item_identity = item_live.get("gene_identity", {})
                top_opp = (item_live.get("research_opportunities") or [{}])[0]
                rows.append({
                    "Gene": item.gene,
                    "Submitted Symbol": item_identity.get("query", item.gene),
                    "Target Priority Score": item.score.overall,
                    "Evidence Coverage (%)": item.score.evidence_coverage_pct,
                    "Priority Classification": item.score.label,
                    "Top Research Opportunity": top_opp.get("title"),
                    "Opportunity Priority": top_opp.get("priority"),
                    "DepMap Selectivity Difference": item_dep.get("median_selectivity_delta"),
                    "Usable CGGA Cohorts": item_cgg.get("n_usable_cohorts", 0),
                    "Active GBM Trials": item_live.get("clinical_trials", {}).get("active", 0),
                })
            st.dataframe(rows, width="stretch", hide_index=True)
        except Exception as exc:
            st.error(f"Gene set comparison failed: {exc}")

with methods_tab:
    st.markdown("### Scored Evidence Model")
    st.write("The Target Priority Score is unchanged from the validated V4/V5 model. It integrates TCGA genomic signal, Open Targets disease relevance and druggability, clinical translation, literature context, DepMap dependency, Ivy GAP spatial expression, CGGA external human validation, and strict GLASS recurrence evidence when authorized. Missing sources reduce evidence coverage rather than becoming negative biological evidence.")

    section_space(0.8)
    st.markdown("### Discovery Layer")
    st.write("V6 does not hide new biology inside the scalar score. It separately detects cross-source mismatches, translational whitespace, niche-specific signals, recurrence gaps, and therapeutic-window questions; converts those patterns into falsifiable hypotheses; and ranks experiments according to unresolved evidence and contradiction burden.")

    section_space(0.8)
    st.markdown("### Target Pair Analysis")
    st.write("The Combination Rationale Score asks whether two targets have enough individual evidence, functional support, network complementarity, spatial complementarity, recurrence relevance, and translational feasibility to justify a combination experiment. It is not a pharmacologic synergy model.")

    section_space(0.8)
    st.markdown("### Researcher Signature + LINCS")
    st.write("Researcher-provided signed gene results can be interpreted directly against GBM target evidence. The same signature is submitted to the public L1000CDS2 API to identify LINCS-derived perturbational signatures predicted to reverse the state and to surface pairwise drug hypotheses. L1000 results are hypothesis-generation evidence and require GBM-specific experimental validation.")

    section_space(0.8)
    st.markdown("### Next-Generation Models")
    st.write("When current DepMap model metadata exposes model format, the functional panel separately reports strict GBM NextGen 3D/organoid/spheroid context. This contextual stratification is not allowed to change the validated dependency score without a sufficiently powered comparison.")

    section_space(0.8)
    st.markdown("### Single-Cell Roadmap")
    st.write("GBmap is publicly available through CELLxGENE and contains a large harmonized IDH-wildtype GBM single-cell/spatial collection. The current public deployment links the atlas but does not download the full atlas during each query. The next infrastructure step is a compact precomputed/queryable GBmap service that can return cell-state and spatial gene statistics reproducibly without destabilizing the public app.")

    section_space(0.8)
    st.markdown("### Interpretation")
    st.write("Every V6 discovery output is explicitly labeled as a research hypothesis or heuristic unless it directly reports a source statistic. Genomic alteration, dependency, spatial heterogeneity, prognosis, recurrence, normal-tissue expression, network connectivity, perturbational reversal, BBB permeability, and clinical maturity answer different biological questions and should not be treated as interchangeable evidence.")
