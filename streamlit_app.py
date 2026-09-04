"""Standalone Streamlit UI for the research-grade GBM Evidence Engine."""
from __future__ import annotations

import json
import streamlit as st

from gbm_evidence_engine.research_intelligence_v4 import build_research_profile, rank_gene_list
from gbm_evidence_engine.evidence_model import EvidenceTier

st.set_page_config(page_title="GBM Evidence Engine", page_icon="🧬", layout="wide")


@st.cache_data(ttl=3600, show_spinner=False)
def cached_profile(gene: str):
    return build_research_profile(gene)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_batch(genes: tuple[str, ...]):
    return rank_gene_list(list(genes), max_workers=2)


def pct(x):
    return "—" if x is None else f"{100*x:.1f}%"


def num(x, digits=2):
    if x is None:
        return "—"
    return f"{x:.{digits}f}" if isinstance(x, float) else str(x)


def pval(x):
    if x is None:
        return "—"
    return f"{x:.2g}"


def markdown_brief(profile) -> str:
    s = profile.score
    lines = [
        f"# GBM Evidence Engine — {profile.gene}", "",
        f"**Priority signal:** {s.overall if s.overall is not None else 'N/A'}/100 — {s.label}",
        f"**Evidence coverage:** {s.evidence_coverage_pct}%", "", "## Score dimensions",
    ]
    for name, d in s.dimensions.items():
        lines.append(f"- **{name}:** {num(d.score, 1)}/100 — {d.rationale}")
    lines += ["", "## Evidence gaps"] + [f"- {x}" for x in profile.evidence_gaps]
    lines += ["", "## Suggested next experiments"] + [f"- {x}" for x in profile.next_experiments]
    lines += ["", "## Source status"] + [f"- **{k}:** {v}" for k, v in profile.source_status.items()]
    lines += ["", f"> {s.caveat}"]
    return "\n".join(lines)


st.title("GBM Evidence Engine")
st.caption("Research-grade target intelligence for glioblastoma — genomics, dependency, spatial biology, external cohorts, trials, literature, and evidence gaps.")

with st.expander("What this tool does", expanded=False):
    st.write(
        "Enter a gene to assemble GBM-specific evidence from public research sources. V3 adds strict IDH-wildtype GBM "
        "DepMap dependency testing, Ivy GAP anatomic RNA-seq, and two independent CGGA survival cohorts to the live "
        "genomic/drug/trial/literature core. GLASS longitudinal ingestion is enabled only for authorized Synapse access. "
        "The score is for research triage, not clinical use."
    )

single_tab, batch_tab, methods_tab = st.tabs(["Target profile", "Batch prioritisation", "Methods & source coverage"])

with single_tab:
    c1, c2 = st.columns([4, 1])
    with c1:
        gene = st.text_input("Gene symbol", value="EGFR", placeholder="e.g. EGFR, PTEN, TERT, CDK6").strip().upper()
    with c2:
        st.write("")
        run = st.button("Build research profile", type="primary", use_container_width=True)

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
        m1.metric("Priority signal", "—" if score.overall is None else f"{score.overall}/100")
        m2.metric("Evidence coverage", f"{score.evidence_coverage_pct}%")
        m3.metric("Evidence records", len(profile.dossier.evidence))
        m4.metric("Active matching GBM trials", profile.live["clinical_trials"].get("active", 0))
        st.caption(f"{score.label}. {score.caveat}")

        st.markdown("### Why the score looks this way")
        rows = [{
            "Dimension": name,
            "Score": None if d.score is None else round(d.score, 1),
            "Weight": f"{d.weight:.0%}",
            "Source": d.source,
            "Rationale": d.rationale,
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

        st.markdown("### GBM genomic signal")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("TCGA mutation", pct((cbio.get("mutation") or {}).get("frequency")))
        g2.metric("TCGA amplification", pct((cbio.get("copy_number") or {}).get("amplification_frequency")))
        g3.metric("TCGA deep deletion", pct((cbio.get("copy_number") or {}).get("deep_deletion_frequency")))
        g4.metric("Open Targets GBM score", num(ot.get("gbm_association_score"), 3))

        left, right = st.columns(2)
        with left:
            st.markdown("### Evidence gaps")
            for gap in profile.evidence_gaps:
                st.markdown(f"- {gap}")
        with right:
            st.markdown("### Suggested next experiments")
            for idea in profile.next_experiments:
                st.markdown(f"- {idea}")

        detail_tabs = st.tabs([
            "Evidence ledger", "Functional & spatial", "Drugs & trials",
            "Human cohorts", "Literature & GBM context", "Export"
        ])

        with detail_tabs[0]:
            if not profile.dossier.evidence:
                st.info("No evidence records were returned. Check source status below.")
            for tier in EvidenceTier:
                records = profile.dossier.by_tier(tier)
                if not records:
                    continue
                with st.expander(f"{tier.value.replace('_', ' ').title()} ({len(records)})",
                                 expanded=tier in (EvidenceTier.OBSERVED_DATA, EvidenceTier.STATISTICAL_ASSOCIATION)):
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
                        st.caption(f"Source: {r.provenance.source_dataset} · confidence: {r.confidence.value} · access: {r.provenance.access_tier.value}")
                        for caveat in r.caveats:
                            st.caption(f"Caveat: {caveat}")
                        st.divider()

        with detail_tabs[1]:
            st.markdown("#### DepMap functional dependency")
            if dep.get("ok"):
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("Strict GBM models", dep.get("n_gbm"))
                d2.metric("GBM median Chronos", num(dep.get("median_effect_gbm"), 2))
                d3.metric("Selectivity Δ", num(dep.get("median_selectivity_delta"), 2))
                d4.metric("One-sided p", pval(dep.get("p_value")))
                st.caption(f"GBM definition: {dep.get('gbm_definition')}. Pan-essential: {'yes' if dep.get('pan_essential') else 'no'}.")
                if dep.get("most_dependent_gbm_models"):
                    st.dataframe(dep["most_dependent_gbm_models"], use_container_width=True, hide_index=True)
            else:
                st.info(dep.get("error", "DepMap layer unavailable."))

            st.markdown("#### Ivy GAP spatial expression")
            if ivy.get("ok"):
                i1, i2, i3, i4 = st.columns(4)
                i1.metric("LMD samples", ivy.get("n_samples"))
                i2.metric("Top anatomic zone", str(ivy.get("top_zone", "—")).replace("_", " ").title())
                i3.metric("Median range", num(ivy.get("median_range"), 2))
                i4.metric("Kruskal p", pval(ivy.get("p_value")))
                zone_rows = [{
                    "Zone": zone.replace("_", " ").title(),
                    "Median log2(FPKM+1)": round(value, 3),
                    "n": ivy.get("zone_counts", {}).get(zone),
                } for zone, value in ivy.get("zone_medians", {}).items()]
                st.dataframe(zone_rows, use_container_width=True, hide_index=True)
            else:
                st.info(ivy.get("error", "Ivy GAP layer unavailable."))

        with detail_tabs[2]:
            d1, d2, d3 = st.columns(3)
            d1.metric("Target-directed candidates", ot.get("known_drug_count", 0) if ot.get("ok") else "—")
            d2.metric("Highest matching GBM trial phase", trials.get("max_phase", 0) if trials.get("ok") else "—")
            d3.metric("Matching GBM trials", trials.get("total", 0) if trials.get("ok") else "—")
            if ot.get("drugs"):
                st.markdown("#### Target-directed candidate landscape")
                st.dataframe(ot["drugs"], use_container_width=True, hide_index=True)
            if trials.get("studies"):
                st.markdown("#### ClinicalTrials.gov matches")
                st.dataframe(trials["studies"], use_container_width=True, hide_index=True)

        with detail_tabs[3]:
            st.markdown("#### CGGA independent GBM validation")
            if cgg.get("ok"):
                meta = cgg.get("meta_analysis")
                c1, c2, c3 = st.columns(3)
                c1.metric("Usable strict-GBM cohorts", f"{cgg.get('n_usable_cohorts', 0)}/2")
                c2.metric("Pooled HR / 1 SD", num((meta or {}).get("pooled_hr"), 2))
                c3.metric("Pooled p", pval((meta or {}).get("pooled_p_value")))
                cohort_rows = []
                for row in cgg.get("cohorts", []):
                    cohort_rows.append({
                        "Cohort": row.get("cohort"), "Usable": row.get("ok"), "n": row.get("n"),
                        "Events": row.get("events"), "HR / 1 SD": row.get("hr_per_sd"),
                        "p": row.get("p_value"), "Error": row.get("error"),
                    })
                st.dataframe(cohort_rows, use_container_width=True, hide_index=True)
                if meta:
                    st.caption(f"{meta.get('model')} effect meta-analysis · I²={meta.get('i_squared', 0):.1f}% · direction {'consistent' if cgg.get('direction_consistent') else 'discordant'}. Prognostic association is not causal evidence.")
            else:
                st.info("CGGA validation unavailable in the strict GBM subset.")

            st.markdown("#### GLASS longitudinal context")
            if gla.get("ok"):
                x1, x2, x3 = st.columns(3)
                x1.metric("Primary/recurrent pairs", gla.get("n_pairs"))
                x2.metric("Median recurrence Δ", num(gla.get("median_delta"), 3))
                x3.metric("Paired p", pval(gla.get("p_value")))
                st.caption(gla.get("scope", ""))
            elif gla.get("status") == "credentials_required":
                st.info("GLASS is wired but controlled. Configure an authorized SYNAPSE_AUTH_TOKEN in the deployment secrets after accepting the GLASS/Synapse access conditions. It is excluded from the priority score until GBM-specific subtype filtering is available.")
            else:
                st.info(gla.get("error", "GLASS layer unavailable."))

        with detail_tabs[4]:
            l1, l2 = st.columns([1, 2])
            with l1:
                st.metric("GBM literature co-mentions", lit.get("hit_count", 0) if lit.get("ok") else "—")
                context_rows = [{"Context": k.replace("_", " ").title(), "Indexed papers": v} for k, v in profile.context_map.items()]
                st.dataframe(context_rows, use_container_width=True, hide_index=True)
            with l2:
                papers = lit.get("top_papers") or []
                if papers:
                    st.markdown("#### Top matching papers")
                    for paper in papers:
                        title = paper.get("title") or "Untitled"
                        meta = " · ".join(str(x) for x in [paper.get("journal"), paper.get("year"), paper.get("pmid") and f"PMID {paper.get('pmid')}"] if x)
                        st.markdown(f"**{title}**")
                        if meta:
                            st.caption(meta)

        with detail_tabs[5]:
            profile_json = json.dumps(profile.to_dict(), indent=2, default=str)
            st.download_button("Download full research profile (JSON)", profile_json,
                               file_name=f"{profile.gene}_gbm_research_profile.json", mime="application/json")
            brief = markdown_brief(profile)
            st.download_button("Download decision brief (Markdown)", brief,
                               file_name=f"{profile.gene}_gbm_decision_brief.md", mime="text/markdown")

with batch_tab:
    st.write("Paste a short gene list to rank targets using the same multi-source scoring system.")
    raw = st.text_area("Genes (comma, space, or new line separated)", value="EGFR, PTEN, TP53, CDK4")
    genes = list(dict.fromkeys(x.strip().upper() for x in raw.replace(",", " ").split() if x.strip()))
    if len(genes) > 6:
        st.warning("Research-grade batch mode is limited to 6 genes per run to keep public-source load reasonable.")
        genes = genes[:6]
    if st.button("Rank gene list", type="primary") and genes:
        try:
            with st.spinner("Building and comparing multi-source profiles..."):
                profiles = cached_batch(tuple(genes))
            table = []
            for p in profiles:
                dep = p.live.get("depmap", {})
                cgg = p.live.get("cgga", {})
                table.append({
                    "Gene": p.gene, "Priority signal": p.score.overall,
                    "Coverage %": p.score.evidence_coverage_pct, "Label": p.score.label,
                    "DepMap selectivity Δ": dep.get("median_selectivity_delta"),
                    "CGGA cohorts": cgg.get("n_usable_cohorts", 0),
                    "Active GBM trials": p.live["clinical_trials"].get("active", 0),
                })
            st.dataframe(table, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"Batch ranking failed: {exc}")

with methods_tab:
    st.markdown("### Scored evidence layers")
    st.write(
        "V3 scores eight independently visible dimensions: TCGA genomic signal, Open Targets disease relevance, druggability, "
        "clinical translation, literature/context depth, strict-GBM DepMap functional dependency, Ivy GAP spatial context, "
        "and independent CGGA human-cohort validation. Missing sources lower evidence coverage; they are never converted into negative biology."
    )
    st.markdown("### GLASS controlled access")
    st.write(
        "The current GLASS TPM matrix is integrated through Synapse entity syn57367276. Synapse requires an authorized personal "
        "access token for download. The engine reports that state explicitly and does not use synthetic recurrence data. Even when "
        "authorized, the current matrix-wide paired result is shown as diffuse-glioma longitudinal context and excluded from the GBM score "
        "until controlled clinical metadata can enforce a GBM-specific subtype filter."
    )
    st.markdown("### Interpretation")
    st.write(
        "A high score means a target has a comparatively dense and selective research evidence footprint. DepMap dependency, spatial "
        "heterogeneity, prognostic survival association, druggability and clinical maturity answer different questions and are not treated "
        "as interchangeable proof. The evidence ledger and source-specific caveats should drive experimental decisions—not the scalar score alone."
    )
