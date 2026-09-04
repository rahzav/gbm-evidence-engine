"""
streamlit_app.py
==================

The actual clickable front-end. Everything it calls
(gbm_evidence_engine.orchestrator) is already unit-tested — this file is
just a UI shell around it, kept deliberately thin so bugs have nowhere to
hide but the display logic.

NOT EXECUTED IN THIS SANDBOX: streamlit is not installed here (no network
to pip install it) and this could not be click-tested end-to-end the way
tests/*.py and scripts/run_demo_dossier.py were. Read it before trusting
it, and run it locally once (`streamlit run streamlit_app.py`) before
deploying. It calls only functions that already have passing unit tests,
which keeps the risk surface small, but "the UI renders correctly" itself
is untested.

Run locally:
    pip install streamlit
    streamlit run streamlit_app.py

Deploy for free (recommended path — see chat for the full walkthrough):
    1. Push this repo to a GitHub repo.
    2. https://share.streamlit.io -> "New app" -> pick the repo ->
       main file path: streamlit_app.py -> Deploy.
    3. You get a public URL (e.g. gbm-evidence-engine.streamlit.app) in
       a few minutes, for free, with no server to manage.
"""
import streamlit as st

from gbm_evidence_engine.orchestrator import (
    build_single_gene_dossier, generate_synthesis, validate_numeric_grounding,
)
from gbm_evidence_engine.evidence_model import EvidenceTier
from gbm_evidence_engine.analysis.multiple_testing import benjamini_hochberg

st.set_page_config(page_title="GBM Evidence Engine", layout="wide")

st.title("GBM Evidence Engine")
st.caption(
    "A cross-cohort, cross-modality evidence dossier for glioblastoma research targets. "
    "Built for Rutgers Gray for Glioblastoma (rutgersg4g.org)."
)

with st.expander("⚠️ Read before trusting any number below", expanded=False):
    st.markdown(
        "This deployment's demo genes (EGFR, PTEN, TP53, CDK4) run partly on **synthetic, "
        "calibrated placeholder data** where a live data pull hasn't been wired up yet for "
        "this deployment -- see `data/README.md` and `docs/VALIDATION_REPORT.md` in the repo "
        "for exactly which numbers are real-cited vs. synthetic, and why. Every record below "
        "states its own source and access tier -- check that field, not just the headline claim."
    )

AVAILABLE_GENES = ["EGFR", "PTEN", "TP53", "CDK4"]

tab_single, tab_batch = st.tabs(["Single-gene dossier", "Batch triage"])

with tab_single:
    col1, col2 = st.columns([3, 1])
    with col1:
        gene = st.selectbox(
            "Gene", AVAILABLE_GENES,
            help="This deployment only has demo data loaded for these four genes. "
                 "In a networked deployment with live connectors wired up, any HUGO gene "
                 "symbol would work.",
        )
    with col2:
        run = st.button("Build dossier", type="primary")

    if run:
        with st.spinner(f"Assembling evidence for {gene}..."):
            dossier = build_single_gene_dossier(gene)
            synthesis = generate_synthesis(dossier)
            check = validate_numeric_grounding(synthesis, dossier)
            dossier.ai_synthesis = synthesis
            dossier.ai_synthesis_grounding_ok = check.ok

        c1, c2, c3 = st.columns(3)
        c1.metric("Evidence records", len(dossier.evidence))
        c2.metric("Safeguard warnings", len(dossier.warnings))
        c3.metric("Synthesis grounding check", "PASS" if check.ok else "FAIL")

        if dossier.warnings:
            for w in dossier.warnings:
                st.warning(w)

        st.subheader("AI synthesis")
        if not check.ok:
            st.error(f"Synthesis failed the numeric grounding check (unmatched: "
                     f"{check.unmatched_numbers}) -- showing the structured evidence "
                     f"below instead of trusting this prose.")
        st.text(dossier.ai_synthesis)

        st.subheader("Evidence, by tier")
        for tier in EvidenceTier:
            records = dossier.by_tier(tier)
            if not records:
                continue
            with st.expander(f"{tier.value} ({len(records)})", expanded=(tier == EvidenceTier.STATISTICAL_ASSOCIATION)):
                for r in records:
                    st.markdown(f"**{r.claim_text}**")
                    meta_bits = []
                    if r.statistic_name:
                        meta_bits.append(f"{r.statistic_name}={r.statistic_value}")
                    if r.p_value is not None:
                        meta_bits.append(f"p={r.p_value:.3g}")
                    if r.confidence_interval and r.confidence_interval[0] is not None:
                        meta_bits.append(f"95% CI [{r.confidence_interval[0]:.3g}, {r.confidence_interval[1]:.3g}]")
                    if meta_bits:
                        st.caption(" · ".join(meta_bits))
                    st.caption(
                        f"Source: {r.provenance.source_dataset} ({r.provenance.dataset_version}) "
                        f"· access: {r.provenance.access_tier.value} · confidence: {r.confidence.value}"
                        + (f" · n={r.provenance.sample_size}" if r.provenance.sample_size else "")
                    )
                    if r.provenance.citation:
                        st.caption(f"Citation: {r.provenance.citation}")
                    for cav in r.caveats:
                        st.caption(f"⚠️ {cav}")
                    st.divider()

        st.download_button("Download full dossier (JSON)", dossier.to_json(),
                            file_name=f"{gene}_dossier.json", mime="application/json")

with tab_batch:
    st.write("Triage a gene list the way a researcher would triage their own "
             "differential-expression hit list (see high-value capability test #5 "
             "in the architecture doc).")
    genes = st.multiselect("Genes", AVAILABLE_GENES, default=AVAILABLE_GENES)
    if st.button("Run batch triage"):
        rows = []
        with st.spinner("Running batch..."):
            for g in genes:
                d = build_single_gene_dossier(g)
                meta = next((e for e in d.evidence if e.statistic_name == "pooled_hazard_ratio"), None)
                dep = next((e for e in d.by_tier(EvidenceTier.STATISTICAL_ASSOCIATION)
                            if e.statistic_name == "U_statistic"), None)
                pan_essential = any("pan-essential" in c for e in d.evidence for c in e.caveats)
                rows.append({
                    "gene": g,
                    "pooled_HR": round(meta.statistic_value, 2) if meta else None,
                    "pooled_p": meta.p_value if meta else None,
                    "I2_pct": round(meta.effect_size, 0) if meta else None,
                    "dependency_p": dep.p_value if dep else None,
                    "pan_essential": pan_essential,
                })
        p_vals = [r["pooled_p"] for r in rows if r["pooled_p"] is not None]
        if p_vals:
            corrected = iter(benjamini_hochberg(p_vals))
            for r in rows:
                r["BH_corrected_p"] = next(corrected) if r["pooled_p"] is not None else None
        st.dataframe(rows, use_container_width=True)

st.divider()
st.caption(
    "Every claim above traces to a specific source, method, and confidence tier -- "
    "see docs/ARCHITECTURE.md in the repository for the full evidence model."
)
