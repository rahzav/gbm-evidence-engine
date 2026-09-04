"""Streamlit interface for GBM Gene Analysis V5."""
from __future__ import annotations

import json
import streamlit as st

from gbm_evidence_engine.evidence_model import EvidenceTier
from gbm_evidence_engine.research_intelligence_v5 import build_research_profile, rank_gene_list

st.set_page_config(page_title="GBM Gene Analysis", page_icon="🧬", layout="wide")


@st.cache_data(ttl=3600, show_spinner=False)
def cached_profile(gene: str):
    return build_research_profile(gene)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_batch(genes: tuple[str, ...]):
    return rank_gene_list(list(genes), max_workers=2)


def pct(value):
    return "N/A" if value is None else f"{100 * value:.1f}%"


def num(value, digits=2):
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def pval(value):
    if value is None:
        return "N/A"
    return f"{value:.2g}"


def section_space(size: float = 1.0):
    st.markdown(f"<div style='height:{size}rem'></div>", unsafe_allow_html=True)


def markdown_brief(profile) -> str:
    s = profile.score
    live = profile.live
    lines = [
        f"# GBM Gene Analysis: {profile.gene}", "",
        f"**Target Priority Score:** {s.overall if s.overall is not None else 'N/A'}/100 ({s.label})",
        f"**Evidence Coverage:** {s.evidence_coverage_pct}%", "",
        "## Key Findings",
    ]
    lines += [f"- {x}" for x in live.get("key_findings", [])]
    lines += ["", "## Score Composition"]
    for name, dimension in s.dimensions.items():
        lines.append(f"- **{name}:** {num(dimension.score, 1)}/100. {dimension.rationale}")
    consistency = live.get("evidence_consistency", {})
    lines += ["", "## Evidence Consistency", f"- {consistency.get('status', 'N/A')}"]
    lines += [f"- {x}" for x in consistency.get("flags", [])]
    lines += ["", "## Evidence Gaps"] + [f"- {x}" for x in profile.evidence_gaps]
    lines += ["", "## Potential Validation Studies"] + [f"- {x}" for x in profile.next_experiments]
    papers = live.get("literature", {}).get("top_papers") or []
    if papers:
        lines += ["", "## Relevant Publications"]
        for paper in papers:
            title = paper.get("title") or "Untitled"
            url = paper.get("url")
            identifier = paper.get("doi") or (f"PMID {paper.get('pmid')}" if paper.get("pmid") else "")
            if url:
                lines.append(f"- [{title}]({url})" + (f" — {identifier}" if identifier else ""))
            else:
                lines.append(f"- {title}")
    lines += ["", "## Data Source Status"] + [f"- **{k}:** {v}" for k, v in profile.source_status.items()]
    lines += ["", f"> {s.caveat}"]
    return "\n".join(lines)


def render_evidence_record(profile):
    if not profile.dossier.evidence:
        st.info("No evidence records were returned. Review data source status for availability.")
        return
    for tier in EvidenceTier:
        records = profile.dossier.by_tier(tier)
        if not records:
            continue
        with st.expander(
            f"{tier.value.replace('_', ' ').title()} ({len(records)})",
            expanded=False,
        ):
            for record in records:
                st.markdown(f"**{record.claim_text}**")
                stats = []
                if record.statistic_name and record.statistic_value is not None:
                    statistic_label = record.statistic_name.replace("_", " ").strip().title()
                    stats.append(f"{statistic_label}: {record.statistic_value:.4g}")
                if record.p_value is not None:
                    stats.append(f"p = {record.p_value:.3g}")
                if record.provenance.sample_size:
                    stats.append(f"n = {record.provenance.sample_size}")
                if stats:
                    st.caption(" | ".join(stats))
                st.caption(
                    f"Source: {record.provenance.source_dataset} | Confidence: {record.confidence.value.title()}"
                )
                st.divider()


def render_genomics_and_identity(identity, cbio, ot):
    st.markdown("#### Genomic Evidence")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("TCGA Mutation Frequency", pct((cbio.get("mutation") or {}).get("frequency")))
    g2.metric("TCGA Amplification Frequency", pct((cbio.get("copy_number") or {}).get("amplification_frequency")))
    g3.metric("TCGA Deep Deletion Frequency", pct((cbio.get("copy_number") or {}).get("deep_deletion_frequency")))
    g4.metric("Open Targets Association Score", num(ot.get("gbm_association_score"), 3))

    section_space(0.6)
    st.markdown("#### Gene Identity")
    if identity.get("ok"):
        identity_rows = [{
            "Canonical Symbol": identity.get("symbol"),
            "Approved Name": identity.get("name"),
            "Ensembl": identity.get("ensembl_gene_id"),
            "Entrez": identity.get("entrez_gene_id"),
            "Matched By": identity.get("matched_by"),
        }]
        st.dataframe(identity_rows, use_container_width=True, hide_index=True)
        if identity.get("aliases"):
            st.caption("Known aliases: " + ", ".join(identity["aliases"][:15]))
    else:
        st.info(identity.get("error", "Canonical gene identity could not be verified."))


def render_functional_and_spatial(dep, ivy):
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
            st.dataframe(dep["most_dependent_gbm_models"], use_container_width=True, hide_index=True)
    else:
        st.info(dep.get("error", "DepMap evidence is unavailable."))

    section_space(0.8)
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
        st.dataframe(zone_rows, use_container_width=True, hide_index=True)
    else:
        st.info(ivy.get("error", "Ivy GAP evidence is unavailable."))


def render_human_validation(cgg, gla):
    st.markdown("#### CGGA External Cohort Validation")
    if cgg.get("ok"):
        meta = cgg.get("meta_analysis")
        c1, c2, c3 = st.columns(3)
        c1.metric("Usable Strict-GBM Cohorts", f"{cgg.get('n_usable_cohorts', 0)}/2")
        c2.metric("Pooled HR per 1 SD", num((meta or {}).get("pooled_hr"), 2))
        c3.metric("Pooled p Value", pval((meta or {}).get("pooled_p_value")))
        cohort_rows = [{
            "Cohort": row.get("cohort"),
            "Usable": row.get("ok"),
            "n": row.get("n"),
            "Events": row.get("events"),
            "HR per 1 SD": row.get("hr_per_sd"),
            "p Value": row.get("p_value"),
            "Status": row.get("error"),
        } for row in cgg.get("cohorts", [])]
        st.dataframe(cohort_rows, use_container_width=True, hide_index=True)
        if meta:
            direction = "consistent" if cgg.get("direction_consistent") else "discordant"
            st.caption(
                f"{meta.get('model')} effect meta-analysis | I²={meta.get('i_squared', 0):.1f}% | Direction: {direction}. Prognostic association is not causal evidence."
            )
    else:
        st.info("CGGA validation is unavailable in the strict GBM subset.")

    section_space(0.8)
    st.markdown("#### GLASS Longitudinal Validation")
    if gla.get("ok"):
        x1, x2, x3 = st.columns(3)
        x1.metric("Primary/Recurrent Pairs", gla.get("n_pairs"))
        x2.metric("Median Recurrence Change", num(gla.get("median_delta"), 3))
        x3.metric("Paired p Value", pval(gla.get("p_value")))
        st.caption(gla.get("scope", ""))
    elif gla.get("status") == "credentials_required":
        st.info(
            "GLASS GBM-specific longitudinal analysis requires an authorized Synapse token. Until credentials are configured, this dimension remains unscored and evidence coverage is reduced."
        )
    else:
        st.info(gla.get("error", "GLASS longitudinal evidence is unavailable."))


def render_tissue_and_network(identity, hpa, network, gbmap):
    st.markdown("#### Normal Tissue and Brain Context")
    if hpa.get("ok"):
        h1, h2, h3 = st.columns(3)
        h1.metric("Tissue Specificity", hpa.get("tissue_specificity") or "N/A")
        h2.metric("Brain Single-Nuclei Specificity", hpa.get("single_nuclei_brain_specificity") or "N/A")
        h3.metric("Maximum Displayed Normal-Brain Expression", num(hpa.get("normal_brain_max_expression"), 1))
        if hpa.get("brain_region_expression"):
            brain_rows = [
                {"Brain Region": region, "Expression": value}
                for region, value in hpa["brain_region_expression"].items()
            ]
            st.dataframe(brain_rows, use_container_width=True, hide_index=True)
        st.caption(hpa.get("interpretation", ""))
        if hpa.get("source_url"):
            st.link_button("Open Human Protein Atlas", hpa["source_url"])
    else:
        st.info(hpa.get("error", "Human Protein Atlas context is unavailable."))

    section_space(0.8)
    st.markdown("#### Interaction Network and Pathways")
    if network.get("ok"):
        if network.get("partners"):
            st.dataframe(network["partners"], use_container_width=True, hide_index=True)
        if network.get("enrichment"):
            st.markdown("##### Network Enrichment")
            st.dataframe(network["enrichment"], use_container_width=True, hide_index=True)
        st.caption(network.get("interpretation", ""))
        if network.get("source_url"):
            st.link_button("Open STRING Network", network["source_url"])
    else:
        st.info(network.get("error", "STRING network context is unavailable."))

    section_space(0.8)
    st.markdown("#### GBmap Single-Cell and Spatial Reference")
    st.write(gbmap.get("scope", "Public GBM single-cell/spatial reference collection."))
    if gbmap.get("collection_url"):
        st.link_button("Open GBmap Collection", gbmap["collection_url"])


def render_literature(profile, lit):
    l1, l2 = st.columns([1, 2])
    with l1:
        st.metric("GBM Literature Co-Mentions", lit.get("hit_count", 0) if lit.get("ok") else "N/A")
        context_rows = [
            {"Disease Context": key.replace("_", " ").title(), "Indexed Publications": value}
            for key, value in profile.context_map.items()
        ]
        st.dataframe(context_rows, use_container_width=True, hide_index=True)
    with l2:
        papers = lit.get("top_papers") or []
        if papers:
            st.markdown("#### Relevant Publications")
            for paper in papers:
                paper_title = str(paper.get("title") or "Untitled")
                safe_title = paper_title.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
                if paper.get("url"):
                    st.markdown(f"**[{safe_title}]({paper['url']})**")
                else:
                    st.markdown(f"**{paper_title}**")
                if paper.get("authors"):
                    st.caption(paper.get("authors"))
                metadata = " | ".join(
                    str(x) for x in [
                        paper.get("journal"),
                        paper.get("year"),
                        paper.get("pmid") and f"PMID {paper.get('pmid')}",
                        paper.get("doi") and f"DOI {paper.get('doi')}",
                    ] if x
                )
                if metadata:
                    st.caption(metadata)


def render_translation(ot, trials, bbb):
    t1, t2, t3 = st.columns(3)
    t1.metric("Target-Directed Candidates", ot.get("known_drug_count", 0) if ot.get("ok") else "N/A")
    t2.metric("Highest Matching GBM Trial Phase", trials.get("max_phase", 0) if trials.get("ok") else "N/A")
    t3.metric("Matching GBM Trials", trials.get("total", 0) if trials.get("ok") else "N/A")

    section_space(0.5)
    candidate_tab, trial_tab, bbb_tab = st.tabs(["Candidates", "Clinical Trials", "BBB Evidence"])
    with candidate_tab:
        st.markdown("#### Target-Directed Candidates")
        if ot.get("drugs"):
            st.dataframe(ot["drugs"], use_container_width=True, hide_index=True)
        else:
            st.info("No target-directed candidates were returned from the current Open Targets result.")

    with trial_tab:
        st.markdown("#### Clinical Trial Matches")
        if trials.get("studies"):
            st.dataframe(trials["studies"], use_container_width=True, hide_index=True)
        else:
            st.info("No matching GBM clinical trial records were returned.")

    with bbb_tab:
        st.markdown("#### Blood-Brain Barrier Evidence")
        if bbb.get("ok"):
            b1, b2, b3 = st.columns(3)
            b1.metric("Candidates Checked", bbb.get("candidates_checked", 0))
            b2.metric("B3DB Matches", bbb.get("matched_count", 0))
            b3.metric("BBB+ Records", bbb.get("bbb_positive_count", 0))
            if bbb.get("matches"):
                st.dataframe(bbb["matches"], use_container_width=True, hide_index=True)
            st.caption(bbb.get("interpretation", ""))
        else:
            st.info(bbb.get("error", "B3DB evidence is unavailable."))


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
    m3.metric("Evidence Records", len(profile.dossier.evidence))
    m4.metric("Active GBM Trials", trials.get("active", 0))
    st.caption(f"{score.label}. {score.caveat}")

    section_space(0.4)
    st.caption(
        "Start with Overview. Use Evidence for source-derived biology, Translation for therapeutic context, "
        "Interpretation & Next Steps for tool-generated synthesis, and Sources & Export for the full evidence record."
    )

    overview_tab, evidence_tab, translation_tab, interpretation_tab, sources_tab = st.tabs([
        "Overview",
        "Evidence",
        "Translation",
        "Interpretation & Next Steps",
        "Sources & Export",
    ])

    with overview_tab:
        summary_col, consistency_col = st.columns(2)
        with summary_col:
            with st.container(border=True):
                st.markdown("### Research Snapshot")
                st.caption("Tool-synthesized summary of the retrieved evidence.")
                findings = live.get("key_findings", [])
                if findings:
                    for finding in findings:
                        st.markdown(f"- {finding}")
                else:
                    st.write("No concise findings were generated from the available sources.")
        with consistency_col:
            with st.container(border=True):
                st.markdown("### Evidence Consistency")
                st.write(consistency.get("status", "Not assessed"))
                for flag in consistency.get("flags", []):
                    st.markdown(f"- {flag}")
                if not consistency.get("flags"):
                    st.caption(consistency.get("note", ""))

        section_space(0.5)
        with st.expander("Priority Score Composition", expanded=False):
            score_rows = [{
                "Evidence Dimension": name,
                "Score": None if d.score is None else round(d.score, 1),
                "Weight": f"{d.weight:.0%}",
                "Primary Source": d.source,
                "Interpretation": d.rationale,
            } for name, d in score.dimensions.items()]
            st.dataframe(score_rows, use_container_width=True, hide_index=True)

    with evidence_tab:
        st.caption("Source-derived molecular and human evidence. Tool-generated recommendations are kept out of this workspace.")
        genomics_tab, functional_tab, human_tab, tissue_tab, literature_tab = st.tabs([
            "Genomics & Identity",
            "Functional & Spatial",
            "Human Validation",
            "Tissue & Network",
            "Literature",
        ])
        with genomics_tab:
            render_genomics_and_identity(identity, cbio, ot)
        with functional_tab:
            render_functional_and_spatial(dep, ivy)
        with human_tab:
            render_human_validation(cgg, gla)
        with tissue_tab:
            render_tissue_and_network(identity, hpa, network, gbmap)
        with literature_tab:
            render_literature(profile, lit)

    with translation_tab:
        st.caption("Therapeutic and clinical-development context is separated from the underlying biological evidence.")
        render_translation(ot, trials, bbb)

    with interpretation_tab:
        st.caption(
            "This workspace contains tool-generated research interpretation. These are prioritization aids and proposed validation steps, not new experimental observations."
        )
        gaps_col, studies_col = st.columns(2)
        with gaps_col:
            with st.container(border=True):
                st.markdown("### Evidence Gaps")
                if profile.evidence_gaps:
                    for gap in profile.evidence_gaps:
                        st.markdown(f"- {gap}")
                else:
                    st.write("No major evidence gaps were identified from the available sources.")
        with studies_col:
            with st.container(border=True):
                st.markdown("### Potential Validation Studies")
                if profile.next_experiments:
                    for idea in profile.next_experiments:
                        st.markdown(f"- {idea}")
                else:
                    st.write("No additional validation studies were generated.")

    with sources_tab:
        st.caption("Detailed provenance, raw evidence records, source availability, and exports live here so they do not interrupt the main research workflow.")
        record_tab, status_tab, export_tab = st.tabs(["Evidence Record", "Source Status", "Export"])
        with record_tab:
            render_evidence_record(profile)
        with status_tab:
            source_rows = [
                {"Data Source": str(name).replace("_", " ").title(), "Status": status}
                for name, status in profile.source_status.items()
            ]
            st.dataframe(source_rows, use_container_width=True, hide_index=True)
        with export_tab:
            profile_json = json.dumps(profile.to_dict(), indent=2, default=str)
            st.download_button(
                "Download Full Research Profile (JSON)",
                profile_json,
                file_name=f"{profile.gene}_gbm_gene_analysis.json",
                mime="application/json",
            )
            brief = markdown_brief(profile)
            st.download_button(
                "Download Research Summary (Markdown)",
                brief,
                file_name=f"{profile.gene}_gbm_gene_analysis.md",
                mime="text/markdown",
            )


st.title("GBM Gene Analysis")
st.caption(
    "Integrated gene-level evidence synthesis for glioblastoma research across genomic, functional, spatial, clinical, longitudinal, and literature datasets."
)
st.write(
    "Enter a gene symbol to generate a GBM-specific research profile. The analysis brings together tumor genomics, functional dependency, spatial expression, independent patient cohorts, clinical trials, literature, normal-tissue context, interaction networks, and available blood-brain barrier data for target-directed compounds."
)
st.caption("Note: Results are intended for research prioritization and hypothesis development, not clinical decision-making.")

analysis_tab, batch_tab, methods_tab = st.tabs([
    "Gene Analysis",
    "Gene Set Comparison",
    "Methods & Data Sources",
])

with analysis_tab:
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

    profile = st.session_state.get("profile_v5")
    if profile:
        render_profile(profile)

with batch_tab:
    st.write("Enter a short gene set to compare targets using the same scored evidence model and canonical gene-resolution workflow.")
    raw = st.text_area("Gene symbols", value="EGFR, PTEN, TP53, CDK4")
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
                rows.append({
                    "Gene": item.gene,
                    "Submitted Symbol": item_identity.get("query", item.gene),
                    "Target Priority Score": item.score.overall,
                    "Evidence Coverage (%)": item.score.evidence_coverage_pct,
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
    st.markdown("### Scored Evidence Model")
    st.write(
        "The Target Priority Score retains the validated V4 evidence model: TCGA genomic signal, Open Targets disease relevance and druggability, clinical translation, literature context, DepMap functional dependency, Ivy GAP spatial expression, CGGA external human validation, and clinically verified GLASS longitudinal recurrence when available. Missing sources reduce evidence coverage rather than becoming negative biological evidence."
    )

    section_space(0.8)
    st.markdown("### Contextual Research Layers")
    st.write(
        "V5 adds canonical gene identity from MyGene.info, normal-tissue and brain context from the Human Protein Atlas, high-confidence interaction and pathway context from STRING, and experimental blood-brain barrier records from B3DB. These layers are displayed separately and do not change the Target Priority Score because their interpretation depends on experimental modality and research question."
    )

    section_space(0.8)
    st.markdown("### Single-Cell Reference")
    st.write(
        "The analysis links directly to the public GBmap IDH-wildtype glioblastoma single-cell and spatial reference collection. Quantitative GBmap expression is not incorporated into the priority score unless it can be analyzed reproducibly at gene level without requiring the application to download the full atlas during each query."
    )

    section_space(0.8)
    st.markdown("### Interpretation")
    st.write(
        "The score is a research-prioritization heuristic. Genomic alteration, dependency, spatial heterogeneity, prognosis, recurrence, normal-tissue expression, network connectivity, druggability, BBB permeability, and clinical maturity answer different biological questions. Researchers should use the source-specific evidence and caveats rather than the scalar score alone when selecting experiments or targets."
    )
