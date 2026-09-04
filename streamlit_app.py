"""Standalone Streamlit UI for the live-first GBM Evidence Engine."""
from __future__ import annotations

import json
import streamlit as st

from gbm_evidence_engine.research_intelligence import build_research_profile, rank_gene_list
from gbm_evidence_engine.evidence_model import EvidenceTier

st.set_page_config(page_title="GBM Evidence Engine", page_icon="🧬", layout="wide")


@st.cache_data(ttl=3600, show_spinner=False)
def cached_profile(gene: str):
    return build_research_profile(gene)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_batch(genes: tuple[str, ...]):
    return rank_gene_list(list(genes), max_workers=3)


def pct(x):
    return "—" if x is None else f"{100*x:.1f}%"


def num(x, digits=2):
    if x is None:
        return "—"
    return f"{x:.{digits}f}" if isinstance(x, float) else str(x)


def markdown_brief(profile) -> str:
    s = profile.score
    lines = [
        f"# GBM Evidence Engine — {profile.gene}",
        "",
        f"**Priority signal:** {s.overall if s.overall is not None else 'N/A'}/100 — {s.label}",
        f"**Evidence coverage:** {s.evidence_coverage_pct}%",
        "",
        "## Score dimensions",
    ]
    for name, d in s.dimensions.items():
        lines.append(f"- **{name}:** {num(d.score, 1)}/100 — {d.rationale}")
    lines += ["", "## Evidence gaps"] + [f"- {x}" for x in profile.evidence_gaps]
    lines += ["", "## Suggested next experiments"] + [f"- {x}" for x in profile.next_experiments]
    lines += ["", "## Source status"] + [f"- **{k}:** {v}" for k, v in profile.source_status.items()]
    lines += ["", f"> {s.caveat}"]
    return "\n".join(lines)


st.title("GBM Evidence Engine")
st.caption("Live-first target intelligence for glioblastoma research — evidence assembly, prioritisation, gaps, and next experiments.")

with st.expander("What this tool does", expanded=False):
    st.write(
        "Enter a gene to assemble GBM-specific genomic evidence, target-disease evidence, drugs, trials, "
        "and literature context from public research sources. The tool then produces a transparent research-" 
        "priority signal and identifies what evidence is still missing. The score is for research triage, not clinical use."
    )

single_tab, batch_tab, methods_tab = st.tabs(["Target profile", "Batch prioritisation", "Methods & source coverage"])

with single_tab:
    c1, c2 = st.columns([4, 1])
    with c1:
        gene = st.text_input("Gene symbol", value="EGFR", placeholder="e.g. EGFR, PTEN, TERT, CDK6").strip().upper()
    with c2:
        st.write("")
        run = st.button("Build live profile", type="primary", use_container_width=True)

    if run:
        try:
            with st.spinner(f"Querying live GBM evidence for {gene}..."):
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
        m3.metric("Live evidence records", len(profile.dossier.evidence))
        m4.metric("Active matching GBM trials", profile.live["clinical_trials"].get("active", 0))
        st.caption(f"{score.label}. {score.caveat}")

        st.markdown("### Why the score looks this way")
        rows = []
        for name, d in score.dimensions.items():
            rows.append({
                "Dimension": name,
                "Score": None if d.score is None else round(d.score, 1),
                "Weight": f"{d.weight:.0%}",
                "Source": d.source,
                "Rationale": d.rationale,
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        cbio = profile.live["cbioportal"]
        ot = profile.live["open_targets"]
        trials = profile.live["clinical_trials"]
        lit = profile.live["literature"]

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

        detail_tabs = st.tabs(["Evidence ledger", "Drugs & trials", "Literature & GBM context", "Export"])
        with detail_tabs[0]:
            if not profile.dossier.evidence:
                st.info("No live evidence records were returned. Check source status below.")
            for tier in EvidenceTier:
                records = profile.dossier.by_tier(tier)
                if not records:
                    continue
                with st.expander(f"{tier.value.replace('_', ' ').title()} ({len(records)})",
                                 expanded=tier in (EvidenceTier.OBSERVED_DATA, EvidenceTier.COMPUTATIONAL_PREDICTION)):
                    for r in records:
                        st.markdown(f"**{r.claim_text}**")
                        bits = []
                        if r.statistic_name and r.statistic_value is not None:
                            bits.append(f"{r.statistic_name}={r.statistic_value:.4g}")
                        if r.provenance.sample_size:
                            bits.append(f"n={r.provenance.sample_size}")
                        if bits:
                            st.caption(" · ".join(bits))
                        st.caption(f"Source: {r.provenance.source_dataset} · confidence: {r.confidence.value} · access: {r.provenance.access_tier.value}")
                        for caveat in r.caveats:
                            st.caption(f"Caveat: {caveat}")
                        st.divider()

        with detail_tabs[1]:
            d1, d2, d3 = st.columns(3)
            d1.metric("Known target-directed drugs/candidates", ot.get("known_drug_count", 0) if ot.get("ok") else "—")
            d2.metric("Highest target drug phase", ot.get("max_phase", 0) if ot.get("ok") else "—")
            d3.metric("Matching GBM trials", trials.get("total", 0) if trials.get("ok") else "—")
            drug_rows = ot.get("drugs") or []
            if drug_rows:
                st.markdown("#### Target-directed drug landscape")
                st.dataframe(drug_rows, use_container_width=True, hide_index=True)
            if trials.get("studies"):
                st.markdown("#### ClinicalTrials.gov matches")
                st.dataframe(trials["studies"], use_container_width=True, hide_index=True)

        with detail_tabs[2]:
            l1, l2 = st.columns([1, 2])
            with l1:
                st.metric("GBM literature co-mentions", lit.get("hit_count", 0) if lit.get("ok") else "—")
                context_rows = [{"Context": k.replace("_", " ").title(), "Indexed papers": v}
                                for k, v in profile.context_map.items()]
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

        with detail_tabs[3]:
            profile_json = json.dumps(profile.to_dict(), indent=2, default=str)
            st.download_button("Download full research profile (JSON)", profile_json,
                               file_name=f"{profile.gene}_gbm_research_profile.json", mime="application/json")
            brief = markdown_brief(profile)
            st.download_button("Download decision brief (Markdown)", brief,
                               file_name=f"{profile.gene}_gbm_decision_brief.md", mime="text/markdown")

with batch_tab:
    st.write("Paste a short gene list to rank targets using the same live, transparent scoring system.")
    raw = st.text_area("Genes (comma, space, or new line separated)", value="EGFR, PTEN, TP53, CDK4")
    genes = [x.strip().upper() for x in raw.replace(",", " ").split() if x.strip()]
    genes = list(dict.fromkeys(genes))
    if len(genes) > 8:
        st.warning("Batch mode is limited to 8 genes per run to keep public API use reasonable.")
        genes = genes[:8]
    if st.button("Rank gene list", type="primary") and genes:
        try:
            with st.spinner("Building and comparing live profiles..."):
                profiles = cached_batch(tuple(genes))
            table = []
            for p in profiles:
                table.append({
                    "Gene": p.gene,
                    "Priority signal": p.score.overall,
                    "Coverage %": p.score.evidence_coverage_pct,
                    "Label": p.score.label,
                    "Active GBM trials": p.live["clinical_trials"].get("active", 0),
                    "GBM literature": p.live["literature"].get("hit_count"),
                })
            st.dataframe(table, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"Batch ranking failed: {exc}")

with methods_tab:
    st.markdown("### Live sources")
    st.write(
        "The production-facing profile queries cBioPortal/TCGA-GBM, Open Targets, ClinicalTrials.gov, and Europe PMC. "
        "Each layer can fail independently; source status is shown rather than silently substituting a value."
    )
    st.markdown("### What is intentionally not scored yet")
    st.write(
        "Real DepMap dependency data, Ivy GAP spatial expression, CGGA validation, and GLASS longitudinal recurrence data "
        "require bulk ingestion or registration/data-use steps. The older synthetic demonstration files remain useful for "
        "testing statistical code, but they never increase the live target-priority score."
    )
    st.markdown("### Interpretation")
    st.write(
        "A high score means the target has a dense, translationally mature evidence footprint worth deeper review. It does not "
        "mean the gene is causal, safe to target, or likely to improve patient outcomes. Researchers should use the evidence "
        "ledger and gaps—not the score alone—to decide what to test next."
    )
