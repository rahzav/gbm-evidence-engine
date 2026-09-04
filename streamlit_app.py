"""Standalone Streamlit UI for the GBM Research Evidence Engine."""
from __future__ import annotations

import json
import streamlit as st

from gbm_evidence_engine.research_intelligence_v4 import build_research_profile, rank_gene_list
from gbm_evidence_engine.evidence_model import EvidenceTier

st.set_page_config(page_title="GBM Research Evidence Engine", page_icon="🧬", layout="wide")


@st.cache_data(ttl=3600, show_spinner=False)
def cached_profile(gene: str):
    return build_research_profile(gene)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_batch(genes: tuple[str, ...]):
    return rank_gene_list(list(genes), max_workers=2)


def pct(x):
    return "N/A" if x is None else f"{100*x:.1f}%"


def num(x, digits=2):
    if x is None:
        return "N/A"
    return f"{x:.{digits}f}" if isinstance(x, float) else str(x)


def pval(x):
    if x is None:
        return "N/A"
    return f"{x:.2g}"


def section_space(size: float = 1.35):
    st.markdown(
        f"<div style='height: {size}rem;'></div>",
        unsafe_allow_html=True,
    )


def markdown_brief(profile) -> str:
    s = profile.score
    lines = [
        f"# GBM Research Evidence Engine: {profile.gene}", "",
        f"**Target Priority Score:** {s.overall if s.overall is not None else 'N/A'}/100 ({s.label})",
        f"**Evidence Coverage:** {s.evidence_coverage_pct}%", "", "## Score Composition",
    ]
    for name, d in s.dimensions.items():
        lines.append(f"- **{name}:** {num(d.score, 1)}/100. {d.rationale}")
    lines += ["", "## Evidence Gaps"] + [f"- {x}" for x in profile.evidence_gaps]
    lines += ["", "## Potential Validation Studies"] + [f"- {x}" for x in profile.next_experiments]
    lines += ["", "## Data Source Status"] + [f"- **{k}:** {v}" for k, v in profile.source_status.items()]
    lines += ["", f"> {s.caveat}"]
    return "\n".join(lines)


st.title("GBM Research Evidence Engine")
st.caption(
    "Integrated evidence synthesis and target prioritization for glioblastoma research across genomic, functional, spatial, clinical, longitudinal, and literature data."
)
st.write(
    "Enter a gene symbol to generate a GBM-specific research profile. The tool integrates evidence from TCGA/cBioPortal, Open Targets, ClinicalTrials.gov, Europe PMC, DepMap, Ivy GAP, CGGA, and authorized GLASS data where available."
)
st.caption(
    "Note: Results are intended for research prioritization and hypothesis development, not clinical decision-making."
)

single_tab, batch_tab, methods_tab = st.tabs([
    "Target Analysis",
    "Multi-Gene Prioritization",
    "Methodology & Data Sources",
])

with single_tab:
    c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
    with c1:
        gene = st.text_input(
            "Gene symbol",
            value="EGFR",
            placeholder="e.g. EGFR, PTEN, TERT, CDK6",
        ).strip().upper()
    with c2:
        run = st.button("Build Research Profile", type="primary", use_container_width=True)

    if run:
        try:
            with st.spinner(f"Assembling multi-source GBM evidence for {gene}..."):
                profile = cached_profile(gene)
            st.session_state["profile"] = profile
        except Exception as exc:
            st.error(f"Could not build the profile: {exc}")

    profile = st.session_state.get("profile")
    if profile:
        score = profile.score
        st.subheader(profile.gene)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Target Priority Score", "N/A" if score.overall is None else f"{score.overall}/100")
        m2.metric("Evidence Coverage", f"{score.evidence_coverage_pct}%")
        m3.metric("Evidence Records", len(profile.dossier.evidence))
        m4.metric("Active GBM Trials", profile.live["clinical_trials"].get("active", 0))
        st.caption(f"{score.label}. {score.caveat}")

        section_space()
        st.markdown("### Priority Score Composition")
        rows = [{
            "Evidence Dimension": name,
            "Score": None if d.score is None else round(d.score, 1),
            "Weight": f"{d.weight:.0%}",
            "Primary Source": d.source,
            "Interpretation": d.rationale,
        } for name, d in score.dimensions.items()]
        st.dataframe(rows, use_container_width=True, hide_index=True)

        cbio = profile.live["cbioportal"]
        ot = profile.live["open_targets"]
        trials = profile.live["clinical_trials"]
        lit = profile.live["literature"]
        dep = profile.live.get("depmap", {})
        ivy = profile.live.get("ivy_gap", {})
        cgg = profile.live.get("cgga", {})
        gla = profile.live.get("glass", {})

        section_space()
        st.markdown("### Genomic Evidence")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("TCGA Mutation Frequency", pct((cbio.get("mutation") or {}).get("frequency")))
        g2.metric("TCGA Amplification Frequency", pct((cbio.get("copy_number") or {}).get("amplification_frequency")))
        g3.metric("TCGA Deep Deletion Frequency", pct((cbio.get("copy_number") or {}).get("deep_deletion_frequency")))
        g4.metric("Open Targets Association Score", num(ot.get("gbm_association_score"), 3))

        section_space()
        left, right = st.columns(2)
        with left:
            st.markdown("### Evidence Gaps")
            for gap in profile.evidence_gaps:
                st.markdown(f"- {gap}")
        with right:
            st.markdown("### Potential Validation Studies")
            for idea in profile.next_experiments:
                st.markdown(f"- {idea}")

        section_space(1.6)
        detail_tabs = st.tabs([
            "Evidence Record",
            "Functional & Spatial Evidence",
            "Translational Landscape",
            "Clinical Cohort Validation",
            "Literature & Disease Context",
            "Report Export",
        ])

        with detail_tabs[0]:
            if not profile.dossier.evidence:
                st.info("No evidence records were returned. Review data source status for availability.")
            for tier in EvidenceTier:
                records = profile.dossier.by_tier(tier)
                if not records:
                    continue
                with st.expander(
                    f"{tier.value.replace('_', ' ').title()} ({len(records)})",
                    expanded=tier in (EvidenceTier.OBSERVED_DATA, EvidenceTier.STATISTICAL_ASSOCIATION),
                ):
                    for r in records:
                        st.markdown(f"**{r.claim_text}**")
                        bits = []
                        if r.statistic_name and r.statistic_value is not None:
                            bits.append(f"{r.statistic_name}={r.statistic_value:.4g}")
                        if r.p_value is not None:
                            bits.append(f"p={r.p_value:.3g}")
                        if r.provenance.sample_size:
                            bits.append(f"n={r.provenance.sample_size}")
                        if bits:
                            st.caption(" · ".join(bits))
                        st.caption(
                            f"Source: {r.provenance.source_dataset} · Confidence: {r.confidence.value} · Access: {r.provenance.access_tier.value}"
                        )
                        for caveat in r.caveats:
                            st.caption(f"Caveat: {caveat}")
                        st.divider()

        with detail_tabs[1]:
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
                st.dataframe(zone_rows, use_container_width=True, hide_index=True)
            else:
                st.info(ivy.get("error", "Ivy GAP evidence is unavailable."))

        with detail_tabs[2]:
            d1, d2, d3 = st.columns(3)
            d1.metric("Target-Directed Candidates", ot.get("known_drug_count", 0) if ot.get("ok") else "N/A")
            d2.metric("Highest Matching GBM Trial Phase", trials.get("max_phase", 0) if trials.get("ok") else "N/A")
            d3.metric("Matching GBM Trials", trials.get("total", 0) if trials.get("ok") else "N/A")
            if ot.get("drugs"):
                st.markdown("#### Targeted Therapeutic Candidates")
                st.dataframe(ot["drugs"], use_container_width=True, hide_index=True)
            if trials.get("studies"):
                st.markdown("#### Clinical Trial Matches")
                st.dataframe(trials["studies"], use_container_width=True, hide_index=True)

        with detail_tabs[3]:
            st.markdown("#### CGGA External Cohort Validation")
            if cgg.get("ok"):
                meta = cgg.get("meta_analysis")
                c1, c2, c3 = st.columns(3)
                c1.metric("Usable Strict-GBM Cohorts", f"{cgg.get('n_usable_cohorts', 0)}/2")
                c2.metric("Pooled HR per 1 SD", num((meta or {}).get("pooled_hr"), 2))
                c3.metric("Pooled p Value", pval((meta or {}).get("pooled_p_value")))
                cohort_rows = []
                for row in cgg.get("cohorts", []):
                    cohort_rows.append({
                        "Cohort": row.get("cohort"),
                        "Usable": row.get("ok"),
                        "n": row.get("n"),
                        "Events": row.get("events"),
                        "HR per 1 SD": row.get("hr_per_sd"),
                        "p Value": row.get("p_value"),
                        "Status": row.get("error"),
                    })
                st.dataframe(cohort_rows, use_container_width=True, hide_index=True)
                if meta:
                    direction = "consistent" if cgg.get("direction_consistent") else "discordant"
                    st.caption(
                        f"{meta.get('model')} effect meta-analysis · I²={meta.get('i_squared', 0):.1f}% · Direction: {direction}. Prognostic association is not causal evidence."
                    )
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
                st.info(
                    "GLASS GBM-specific longitudinal analysis is implemented but requires an authorized Synapse token. Configure SYNAPSE_AUTH_TOKEN in deployment secrets after accepting the applicable GLASS/Synapse access conditions. Until credentials are available, this dimension is excluded from the priority score and lowers evidence coverage."
                )
            else:
                st.info(gla.get("error", "GLASS longitudinal evidence is unavailable."))

        with detail_tabs[4]:
            l1, l2 = st.columns([1, 2])
            with l1:
                st.metric("GBM Literature Co-Mentions", lit.get("hit_count", 0) if lit.get("ok") else "N/A")
                context_rows = [
                    {"Disease Context": k.replace("_", " ").title(), "Indexed Publications": v}
                    for k, v in profile.context_map.items()
                ]
                st.dataframe(context_rows, use_container_width=True, hide_index=True)
            with l2:
                papers = lit.get("top_papers") or []
                if papers:
                    st.markdown("#### Relevant Publications")
                    for paper in papers:
                        title = paper.get("title") or "Untitled"
                        meta = " · ".join(
                            str(x)
                            for x in [
                                paper.get("journal"),
                                paper.get("year"),
                                paper.get("pmid") and f"PMID {paper.get('pmid')}",
                            ]
                            if x
                        )
                        st.markdown(f"**{title}**")
                        if meta:
                            st.caption(meta)

        with detail_tabs[5]:
            profile_json = json.dumps(profile.to_dict(), indent=2, default=str)
            st.download_button(
                "Download Full Research Profile (JSON)",
                profile_json,
                file_name=f"{profile.gene}_gbm_research_profile.json",
                mime="application/json",
            )
            brief = markdown_brief(profile)
            st.download_button(
                "Download Research Summary (Markdown)",
                brief,
                file_name=f"{profile.gene}_gbm_research_summary.md",
                mime="text/markdown",
            )

with batch_tab:
    st.write("Enter a concise gene set to compare targets using the same multi-source evidence model.")
    raw = st.text_area(
        "Gene symbols (comma, space, or new line separated)",
        value="EGFR, PTEN, TP53, CDK4",
    )
    genes = list(dict.fromkeys(x.strip().upper() for x in raw.replace(",", " ").split() if x.strip()))
    if len(genes) > 6:
        st.warning("Multi-gene analysis is limited to 6 genes per run to maintain reasonable public-source load.")
        genes = genes[:6]
    if st.button("Prioritize Gene Set", type="primary") and genes:
        try:
            with st.spinner("Building and comparing multi-source profiles..."):
                profiles = cached_batch(tuple(genes))
            table = []
            for p in profiles:
                dep = p.live.get("depmap", {})
                cgg = p.live.get("cgga", {})
                table.append({
                    "Gene": p.gene,
                    "Target Priority Score": p.score.overall,
                    "Evidence Coverage (%)": p.score.evidence_coverage_pct,
                    "Priority Classification": p.score.label,
                    "DepMap Selectivity Difference": dep.get("median_selectivity_delta"),
                    "Usable CGGA Cohorts": cgg.get("n_usable_cohorts", 0),
                    "Active GBM Trials": p.live["clinical_trials"].get("active", 0),
                })
            st.dataframe(table, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"Multi-gene prioritization failed: {exc}")

with methods_tab:
    st.markdown("### Evidence Model")
    st.write(
        "The tool evaluates nine independently visible evidence dimensions: TCGA genomic signal, Open Targets disease association, druggability, clinical translation, literature and disease-context depth, strict-GBM DepMap functional dependency, Ivy GAP spatial expression, independent CGGA human-cohort validation, and GLASS longitudinal recurrence when clinically verified data are available. Missing sources reduce evidence coverage and are not interpreted as negative biological evidence."
    )

    st.markdown("### GLASS Data Access")
    st.write(
        "GLASS longitudinal RNA-seq is accessed through Synapse and requires an authorized personal access token. When available, the tool restricts longitudinal scoring to clinically verified IDH-wildtype glioblastoma primary/recurrent pairs. If credentials or sufficient verified pairs are unavailable, the GLASS dimension remains unscored and evidence coverage is reduced."
    )

    st.markdown("### Interpretation Framework")
    st.write(
        "The Target Priority Score summarizes the density, consistency, and translational relevance of available evidence. Genomic alteration, functional dependency, spatial heterogeneity, survival association, druggability, clinical maturity, and longitudinal recurrence address distinct biological questions and are not treated as interchangeable forms of proof. The underlying evidence record and source-specific caveats should remain the basis for experimental decisions."
    )
