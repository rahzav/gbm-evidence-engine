"""Streamlit interface for GBM Gene Analysis."""
from __future__ import annotations

import io
import json

import pandas as pd
import streamlit as st

from ui_walkthroughs import (
    maybe_show_active_walkthrough,
    maybe_show_initial_gene_walkthrough,
    on_workflow_tab_change,
    render_feature_header,
)
from gbm_evidence_engine.evidence_model import EvidenceTier
from gbm_evidence_engine.connectors import europepmc
from gbm_evidence_engine.research_intelligence_v7_prod import (
    analyze_researcher_signature,
    build_research_profile,
    evaluate_gene_pair,
    rank_gene_list,
)

st.set_page_config(page_title="GBM Gene Analysis", page_icon="🧬", layout="wide")

# Keep Enter-to-submit behavior while removing Streamlit's redundant form hint.
st.markdown(
    """
    <style>
    div[data-testid="stForm"] div[data-testid="InputInstructions"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


HELP = {
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

@st.cache_data(ttl=3600, show_spinner=False)
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
        genes, values, p_values=p_values, fdr_values=fdr_values
    )


@st.cache_data(ttl=1800, max_entries=48, show_spinner=False)
def cached_publication_search(
    gene: str,
    context_key: str | None,
    terms: str,
    cursor_mark: str | None,
):
    return europepmc.search_publications(
        gene,
        context_key=context_key,
        terms=terms,
        page_size=25,
        cursor_mark=cursor_mark,
    )


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


def display_status(value):
    if value is None:
        return "Unavailable"
    raw = str(value).strip().replace("_", " ")
    mapping = {
        "ok": "Available",
        "available": "Available",
        "credentials required": "Unavailable",
        "open live api": "Available",
        "live api": "Available",
        "unavailable": "Unavailable",
    }
    normalized = raw.lower()
    if normalized in mapping:
        return mapping[normalized]
    if "credentials" in normalized or "token" in normalized:
        return "Unavailable"
    if "live api" in normalized or normalized in {"open", "public"}:
        return "Available"
    return raw[:1].upper() + raw[1:]


def markdown_brief(profile) -> str:
    s = profile.score
    live = profile.live
    lines = [
        f"# GBM Gene Analysis: {profile.gene}", "",
        f"**Target Priority Score:** {s.overall if s.overall is not None else 'N/A'}/100 ({s.label})",
        f"**Evidence Coverage:** {s.evidence_coverage_pct}%",
        f"**Evidence Confidence:** {confidence_text(live.get('overall_evidence_confidence', {}))}",
        f"**Functional Model Relevance:** {str((live.get('model_relevance') or {}).get('level', 'unknown')).title()}", "",
        "## Key Findings",
    ]
    lines += [f"- {x}" for x in live.get("key_findings", [])]
    lines += ["", "## Score Composition"]
    for name, dimension in s.dimensions.items():
        lines.append(f"- **{name}:** {num(dimension.score, 1)}/100. {dimension.rationale}")
    consistency = live.get("evidence_consistency", {})
    lines += ["", "## Evidence Consistency", f"- {consistency.get('status', 'N/A')}"]
    lines += [f"- {x}" for x in consistency.get("flags", [])]
    lines += ["", "## Research Opportunities"]
    for row in live.get("research_opportunities", []):
        lines.append(f"- **{row.get('title', 'Research opportunity')}** ({row.get('priority', 'N/A')}/100): {row.get('signal', '')}")
    lines += ["", "## Mechanistic Hypotheses"]
    for row in live.get("mechanistic_hypotheses", []):
        lines.append(f"- {row.get('hypothesis', '')}")
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
    lines += ["", "## Data Source Status"] + [
        f"- **{str(k).replace('_', ' ').title()}:** {display_status(v)}"
        for k, v in profile.source_status.items()
    ]
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
    st.subheader("Genomic Evidence", anchor=False)
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("TCGA Mutation Frequency", pct((cbio.get("mutation") or {}).get("frequency")))
    g2.metric("TCGA Amplification Frequency", pct((cbio.get("copy_number") or {}).get("amplification_frequency")))
    g3.metric("TCGA Deep Deletion Frequency", pct((cbio.get("copy_number") or {}).get("deep_deletion_frequency")))
    g4.metric("Open Targets Association Score", num(ot.get("gbm_association_score"), 3))

    section_space(0.6)
    st.subheader("Gene Identity", anchor=False)
    if identity.get("ok"):
        identity_rows = [{
            "Canonical Symbol": identity.get("symbol"),
            "Approved Name": identity.get("name"),
            "Ensembl": identity.get("ensembl_gene_id"),
            "Entrez": identity.get("entrez_gene_id"),
            "Matched By": identity.get("matched_by"),
        }]
        st.dataframe(identity_rows, width="stretch", hide_index=True)
        if identity.get("aliases"):
            st.caption("Known aliases: " + ", ".join(identity["aliases"][:15]))
    else:
        st.info(identity.get("error", "Canonical gene identity could not be verified."))


def render_functional_and_spatial(dep, ivy):
    st.subheader("DepMap Functional Dependency", help=HELP["depmap"], anchor=False)
    if dep.get("ok"):
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Strict GBM Models", dep.get("n_gbm"))
        d2.metric("Median GBM Chronos Score", num(dep.get("median_effect_gbm"), 2), help=HELP["chronos"])
        d3.metric("Selectivity Difference", num(dep.get("median_selectivity_delta"), 2), help=HELP["selectivity"])
        d4.metric("One-Sided p Value", pval(dep.get("p_value")))
        st.caption(
            f"GBM definition: {dep.get('gbm_definition')}. Pan-essential classification: {'Yes' if dep.get('pan_essential') else 'No'}.",
        )
        if dep.get("most_dependent_gbm_models"):
            st.dataframe(dep["most_dependent_gbm_models"], width="stretch", hide_index=True)
        nextgen = dep.get("nextgen_model_context") or {}
        if nextgen.get("metadata_available"):
            with st.expander("Model Format Context", expanded=False):
                n1, n2, n3, n4 = st.columns(4)
                n1.metric("NextGen 3D Models", nextgen.get("n_nextgen_3d_gbm", 0))
                n2.metric("Conventional Models", nextgen.get("n_conventional_gbm", 0))
                n3.metric("Median 3D Chronos", num(nextgen.get("median_nextgen_3d_chronos"), 2))
                n4.metric("Median Conventional", num(nextgen.get("median_conventional_chronos"), 2))
                if nextgen.get("interpretation"):
                    st.caption(nextgen["interpretation"])
    else:
        st.info(dep.get("error", "DepMap evidence is unavailable."))

    section_space(0.8)
    st.subheader("Ivy GAP Spatial Expression", help=HELP["ivy_gap"], anchor=False)
    if ivy.get("ok"):
        i1, i2, i3, i4 = st.columns(4)
        i1.metric("LMD Samples", ivy.get("n_samples"), help=HELP["lmd_samples"])
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


def render_human_validation(cgg, gla):
    st.subheader("CGGA External Cohort Validation", help=HELP["cgga"], anchor=False)
    if cgg.get("ok"):
        meta = cgg.get("meta_analysis")
        c1, c2, c3 = st.columns(3)
        c1.metric("Usable Strict-GBM Cohorts", f"{cgg.get('n_usable_cohorts', 0)}/2")
        c2.metric("Pooled HR per 1 SD", num((meta or {}).get("pooled_hr"), 2), help=HELP["pooled_hr"])
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
        st.dataframe(cohort_rows, width="stretch", hide_index=True)
        if meta:
            direction = "consistent" if cgg.get("direction_consistent") else "discordant"
            st.caption(
                f"{meta.get('model')} effect meta-analysis | I²={meta.get('i_squared', 0):.1f}% | Direction: {direction}. Prognostic association is not causal evidence."
            )
    else:
        st.info("CGGA validation is unavailable in the strict GBM subset.")

    section_space(0.8)
    st.subheader("GLASS Longitudinal Validation", help=HELP["glass"], anchor=False)
    if gla.get("ok"):
        x1, x2, x3 = st.columns(3)
        x1.metric("Primary/Recurrent Pairs", gla.get("n_pairs"))
        x2.metric("Median Recurrence Change", num(gla.get("median_delta"), 3))
        x3.metric("Paired p Value", pval(gla.get("p_value")))
        st.caption(gla.get("scope", ""))
    elif gla.get("status") == "credentials_required":
        st.info(
            "GLASS longitudinal evidence is unavailable for this analysis. This dimension remains unscored and evidence coverage is reduced."
        )
    else:
        st.info(gla.get("error", "GLASS longitudinal evidence is unavailable."))


def render_tissue_and_network(identity, hpa, network, gbmap, cell):
    render_cell_state(cell)
    section_space(0.8)
    st.subheader("Normal Tissue and Brain Context", anchor=False)
    if hpa.get("ok"):
        h1, h2, h3 = st.columns(3)
        h1.metric("Tissue Specificity", hpa.get("tissue_specificity") or "N/A", help=HELP["tissue_specificity"])
        h2.metric("Brain Single-Nuclei Specificity", hpa.get("single_nuclei_brain_specificity") or "N/A", help=HELP["brain_single_nuclei"])
        h3.metric("Maximum Displayed Normal-Brain Expression", num(hpa.get("normal_brain_max_expression"), 1))
        if hpa.get("brain_region_expression"):
            brain_rows = [
                {"Brain Region": region, "Expression": value}
                for region, value in hpa["brain_region_expression"].items()
            ]
            st.dataframe(brain_rows, width="stretch", hide_index=True)
        st.caption(hpa.get("interpretation", ""))
        if hpa.get("source_url"):
            st.link_button("Open Human Protein Atlas", hpa["source_url"])
    else:
        st.info(hpa.get("error", "Human Protein Atlas context is unavailable."))

    section_space(0.8)
    st.subheader("Interaction Network and Pathways", help=HELP["network"], anchor=False)
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

    section_space(0.8)
    st.subheader("GBmap Single-Cell and Spatial Reference", help=HELP["gbmap"], anchor=False)
    st.write(gbmap.get("scope", "Public GBM single-cell/spatial reference collection."))
    if gbmap.get("collection_url"):
        st.link_button("Open GBmap Collection", gbmap["collection_url"])


def _publication_metadata(paper: dict) -> str:
    parts = []
    if paper.get("journal"):
        parts.append(str(paper["journal"]))
    if paper.get("pmid"):
        parts.append(f"PMID {paper['pmid']}")
    if paper.get("pmcid"):
        parts.append(f"PMCID {paper['pmcid']}")
    if paper.get("doi"):
        parts.append(f"DOI {paper['doi']}")
    if not parts:
        source = str(paper.get("source") or "Europe PMC")
        identifier = paper.get("id")
        parts.append(f"{source} {identifier}".strip())
    return " · ".join(parts)


def _render_publication(paper: dict, index: int) -> None:
    paper_title = str(paper.get("title") or "Untitled publication")
    safe_title = paper_title.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    authors = str(paper.get("authors") or "").strip()
    year = str(paper.get("year") or "").strip()
    metadata = _publication_metadata(paper)

    with st.container(border=True):
        title_col, year_col = st.columns([8.5, 1.2], vertical_alignment="top")
        with title_col:
            if paper.get("url"):
                st.markdown(f"**[{safe_title}]({paper['url']})**")
            else:
                st.markdown(f"**{paper_title}**")
        with year_col:
            if year:
                st.markdown(
                    f"<div style='text-align:right;font-size:.82rem;font-weight:600;opacity:.62;white-space:nowrap;'>{year}</div>",
                    unsafe_allow_html=True,
                )
        st.caption(authors if authors else "Authors not indexed in Europe PMC.")
        st.caption(metadata)


def render_literature(profile, lit):
    gene = profile.gene
    total_records = lit.get("hit_count") if lit.get("ok") else None

    heading_col, source_col = st.columns([5, 2], vertical_alignment="bottom")
    with heading_col:
        st.markdown("### Literature Explorer")
        st.caption(
            "Search the live Europe PMC index for this gene and narrow results by GBM disease context."
        )
    with source_col:
        indexed_text = f"{total_records:,} indexed GBM records" if isinstance(total_records, int) else "Live Europe PMC"
        st.markdown(
            f"<div style='text-align:right;font-size:.88rem;font-weight:600;opacity:.62;padding-bottom:.2rem;'>Europe PMC · {indexed_text}</div>",
            unsafe_allow_html=True,
        )

    context_keys = [key for key in europepmc.CONTEXT_QUERIES if key in profile.context_map]
    label_to_key = {"All GBM literature": None}
    context_options = ["All GBM literature"]
    for key in context_keys:
        label = europepmc.CONTEXT_LABELS.get(key, key.replace("_", " ").title())
        context_options.append(label)
        label_to_key[label] = key

    applied_key = f"literature_applied_terms_{gene}"
    search_input_key = f"literature_search_input_{gene}"
    st.session_state.setdefault(applied_key, "")
    st.session_state.setdefault(search_input_key, st.session_state[applied_key])

    with st.container(border=True):
        st.markdown("#### Find publications")
        st.markdown(
            "<div style='font-size:.86rem;font-weight:600;opacity:.76;margin:.15rem 0 .12rem;'>Disease context</div>",
            unsafe_allow_html=True,
        )
        selected_label = st.pills(
            "Disease context",
            context_options,
            default="All GBM literature",
            selection_mode="single",
            key=f"literature_context_{gene}",
            label_visibility="collapsed",
        ) or "All GBM literature"
        context_key = label_to_key.get(selected_label)

        st.markdown(
            "<div style='font-size:.86rem;font-weight:600;opacity:.76;margin:.7rem 0 .12rem;'>Search publications</div>",
            unsafe_allow_html=True,
        )
        with st.form(f"literature_search_form_{gene}", clear_on_submit=False, border=False):
            search_col, button_col = st.columns([7, 1.25], vertical_alignment="bottom")
            with search_col:
                search_text = st.text_input(
                    "Search publications",
                    key=search_input_key,
                    placeholder="Search title/abstract — e.g. osimertinib, CAR T, resistance",
                    help="Searches within this gene's GBM literature in Europe PMC. Empty the field and search again to reset.",
                    label_visibility="collapsed",
                )
            with button_col:
                search_submitted = st.form_submit_button("Search", type="primary", width="stretch")
        if search_submitted:
            st.session_state[applied_key] = search_text.strip()

    applied_terms = st.session_state.get(applied_key, "")
    signature = (gene, context_key or "", applied_terms)
    sig_key = f"literature_signature_{gene}"
    papers_key = f"literature_papers_{gene}"
    cursor_key = f"literature_cursor_{gene}"
    hits_key = f"literature_hits_{gene}"
    error_key = f"literature_error_{gene}"

    if st.session_state.get(sig_key) != signature:
        result = cached_publication_search(gene, context_key, applied_terms, None)
        st.session_state[sig_key] = signature
        st.session_state[papers_key] = result.get("papers") or []
        st.session_state[cursor_key] = result.get("next_cursor")
        st.session_state[hits_key] = result.get("hit_count")
        st.session_state[error_key] = result.get("error")

    papers = st.session_state.get(papers_key, [])
    hit_count = st.session_state.get(hits_key)
    error = st.session_state.get(error_key)
    if error:
        st.info(error)
        return

    section_space(0.35)
    results_col, count_col = st.columns([5, 2], vertical_alignment="bottom")
    query_description = selected_label
    if applied_terms:
        query_description += f' · "{applied_terms}"'
    with results_col:
        st.markdown("### Relevant Publications")
        st.caption(query_description)
    with count_col:
        if isinstance(hit_count, int):
            count_text = f"{hit_count:,} matches · {len(papers):,} shown"
        else:
            count_text = f"{len(papers):,} shown"
        st.markdown(
            f"<div style='text-align:right;font-size:.86rem;font-weight:600;opacity:.62;padding-bottom:.2rem;'>{count_text}</div>",
            unsafe_allow_html=True,
        )

    if not papers:
        st.info("No matching publications were returned for this filter/search.")
        return

    for index, paper in enumerate(papers, start=1):
        _render_publication(paper, index)

    next_cursor = st.session_state.get(cursor_key)
    if next_cursor and (not isinstance(hit_count, int) or len(papers) < hit_count):
        remaining = None if not isinstance(hit_count, int) else max(0, hit_count - len(papers))
        button_label = "Load 25 more" if remaining is None else f"Load 25 more · {remaining:,} remaining"
        section_space(0.25)
        _, load_col, _ = st.columns([2, 3, 2])
        with load_col:
            if st.button(button_label, key=f"literature_load_more_{gene}", width="stretch"):
                more = cached_publication_search(gene, context_key, applied_terms, next_cursor)
                if more.get("ok"):
                    existing = {
                        str(p.get("doi") or p.get("pmid") or p.get("pmcid") or p.get("id") or p.get("title"))
                        for p in papers
                    }
                    additions = []
                    for paper in more.get("papers") or []:
                        identity = str(paper.get("doi") or paper.get("pmid") or paper.get("pmcid") or paper.get("id") or paper.get("title"))
                        if identity not in existing:
                            additions.append(paper)
                            existing.add(identity)
                    st.session_state[papers_key] = papers + additions
                    st.session_state[cursor_key] = more.get("next_cursor")
                    st.rerun()
                else:
                    st.info(more.get("error", "Europe PMC is temporarily unavailable."))


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
            st.dataframe(ot["drugs"], width="stretch", hide_index=True)
        else:
            st.info("No target-directed candidates were returned from the current Open Targets result.")

    with trial_tab:
        st.markdown("#### Clinical Trial Matches")
        if trials.get("studies"):
            st.dataframe(trials["studies"], width="stretch", hide_index=True)
        else:
            st.info("No matching GBM clinical trial records were returned.")

    with bbb_tab:
        st.subheader("Blood-Brain Barrier Evidence", help=HELP["bbb"], anchor=False)
        if bbb.get("ok"):
            b1, b2, b3 = st.columns(3)
            b1.metric("Candidates Checked", bbb.get("candidates_checked", 0))
            b2.metric("B3DB Matches", bbb.get("matched_count", 0), help=HELP["b3db_matches"])
            b3.metric("BBB+ Records", bbb.get("bbb_positive_count", 0), help=HELP["bbb_positive"])
            if bbb.get("matches"):
                st.dataframe(bbb["matches"], width="stretch", hide_index=True)
            st.caption(bbb.get("interpretation", ""))
        else:
            st.info(bbb.get("error", "B3DB evidence is unavailable."))



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
    c1.metric("Overall Evidence Confidence", confidence_text(overall))
    model_score = model.get("score")
    model_score_text = "N/A" if model_score is None else f"{model_score}/100"
    c2.metric(
        "Functional Model Relevance",
        f"{str(model.get('level', 'unknown')).title()} · {model_score_text}",
    )

    reason_col, model_reason_col = st.columns(2)
    with reason_col:
        for reason in (overall.get("reasons") or [])[:2]:
            st.caption(reason)
    with model_reason_col:
        for reason in (model.get("reasons") or [])[:2]:
            st.caption(reason)

    section_space(0.35)
    st.markdown("#### Confidence by Evidence Dimension")
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
    st.dataframe(rows, width="stretch", hide_index=True)


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
        st.dataframe(rows, width="stretch", hide_index=True)
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
            st.dataframe(experiments, width="stretch", hide_index=True)
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
    cell = live.get("gbmap_cell_state", {})
    overall_confidence = live.get("overall_evidence_confidence", {})

    section_space(0.9)
    title = profile.gene
    if identity.get("ok") and identity.get("name"):
        title += f" | {identity['name']}"
    st.subheader(title)
    if identity.get("ok") and identity.get("was_normalized"):
        st.caption(f"Submitted symbol {identity.get('query')} was normalized to {identity.get('symbol')}.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Target Priority Score", "N/A" if score.overall is None else f"{score.overall}/100", help=HELP["target_priority_score"])
    m2.metric("Evidence Coverage", f"{score.evidence_coverage_pct}%", help=HELP["evidence_coverage"])
    m3.metric("Evidence Confidence", confidence_text(overall_confidence))
    m4.metric("Active GBM Trials", trials.get("active", 0))
    st.caption(f"{score.label}. Intended for comparative research prioritization.")

    section_space(0.4)

    overview_tab, evidence_tab, translation_tab, interpretation_tab, sources_tab = st.tabs([
        "Overview",
        "Evidence",
        "Translation",
        "Interpretation & Next Steps",
        "Sources & Export",
    ])

    with overview_tab:
        st.caption("Integrated summary of the strongest findings, evidence consistency, confidence, and score composition.")
        findings_tab, confidence_tab, composition_tab = st.tabs([
            "Key Findings",
            "Evidence Confidence",
            "Priority Score Composition",
        ])

        with findings_tab:
            st.markdown("#### Key Findings")
            findings = live.get("key_findings", [])
            if findings:
                for finding in findings:
                    st.markdown(f"- {finding}")
            else:
                st.write("No concise findings were generated from the available sources.")

            section_space(0.45)
            st.markdown("#### Evidence Consistency")
            st.write(consistency.get("status", "Not assessed"))
            flags = consistency.get("flags", [])
            if flags:
                for flag in flags:
                    st.markdown(f"- {flag}")
            elif consistency.get("note"):
                st.caption(consistency.get("note", ""))

        with confidence_tab:
            render_confidence_summary(profile)

        with composition_tab:
            st.markdown("#### Priority Score Composition")
            st.caption("Dimension-level scores, model weights, primary sources, and interpretation used in the research-prioritization score.")
            score_rows = [{
                "Evidence Dimension": name,
                "Score": None if d.score is None else round(d.score, 1),
                "Weight": f"{d.weight:.0%}",
                "Primary Source": d.source,
                "Interpretation": d.rationale,
            } for name, d in score.dimensions.items()]
            st.dataframe(score_rows, width="stretch", hide_index=True)

    with evidence_tab:
        st.caption("Source-derived molecular and human evidence.")
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
            render_tissue_and_network(identity, hpa, network, gbmap, cell)
        with literature_tab:
            render_literature(profile, lit)

    with translation_tab:
        st.caption("Therapeutic and clinical-development evidence.")
        render_translation(ot, trials, bbb)

    with interpretation_tab:
        st.caption("Integrated interpretation of cross-source evidence, mechanistic hypotheses, and experimental validation priorities.")
        render_discovery_workspace(profile)

    with sources_tab:
        st.caption("Detailed provenance, source availability, and research-profile exports.")
        record_tab, status_tab, export_tab = st.tabs(["Evidence Record", "Source Status", "Export"])
        with record_tab:
            render_evidence_record(profile)
        with status_tab:
            source_rows = [
                {"Data Source": str(name).replace("_", " ").title(), "Status": display_status(status)}
                for name, status in profile.source_status.items()
            ]
            st.dataframe(source_rows, width="stretch", hide_index=True)
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



st.markdown(
    """
    <div style="margin:0 0 .9rem 0;padding:0;">
      <div style="font-size:2.75rem;font-weight:700;line-height:1.08;letter-spacing:-0.02em;margin:0;padding:0;">GBM Gene Analysis</div>
      <div style="font-size:1.04rem;line-height:1.42;opacity:.68;margin:.38rem 0 0 0;padding:0;">Real-time synthesis of live and curated gene-level evidence for glioblastoma research.</div>
      <div style="font-size:.91rem;line-height:1.42;opacity:.68;margin:.42rem 0 0 0;padding:0;"><b style="opacity:.94;">Research use only:</b> Results are intended for research prioritization and hypothesis development, not clinical decision-making.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

maybe_show_initial_gene_walkthrough()


analysis_tab, pair_tab, researcher_tab, batch_tab, methods_tab = st.tabs(
    [
        "Gene Analysis",
        "Target Pair Analysis",
        "Researcher Data",
        "Gene Set Comparison",
        "Methods & Data Sources",
    ],
    key="research_workflow_tabs",
    on_change=on_workflow_tab_change,
)
maybe_show_active_walkthrough()

with analysis_tab:
    render_feature_header(
        "Gene Analysis", "gene",
        "Build a single-gene dossier across genomic, functional, spatial, human, translational, literature, and cell-state evidence.",
    )
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
                width="stretch",
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
    render_feature_header(
        "Target Pair Analysis", "pair",
        "Cross-target evidence comparison across functional, network, spatial, cell-state, recurrence, translational, and model-relevance layers.",
    )
    with st.form("pair_analysis_form", clear_on_submit=False):
        a_col, b_col, run_col = st.columns([2, 2, 1], vertical_alignment="bottom")
        with a_col:
            gene_a = st.text_input("Target A", value="EGFR", key="pair_a").strip()
        with b_col:
            gene_b = st.text_input("Target B", value="CDK4", key="pair_b").strip()
        with run_col:
            pair_run = st.form_submit_button("Build pair dossier", type="primary", width="stretch")
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
            ], width="stretch", hide_index=True)
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
                st.dataframe(rows, width="stretch", hide_index=True)
        with validation_tab:
            for index, item in enumerate(pair.get("validation_sequence", []), start=1):
                st.markdown(f"{index}. {item}")

with researcher_tab:
    render_feature_header(
        "Researcher Data", "researcher",
        "Analyze processed gene-level signed effects with optional p-values/FDR, then add GBM evidence, pathway, and perturbational context. Uploaded tables are read for analysis and are not written to the project repository.",
    )
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
        st.dataframe(signature_df[preview_cols].head(20), width="stretch", hide_index=True)
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
            st.dataframe(signature.get("top_genes_profiled", []), width="stretch", hide_index=True)
            if signature.get("interpretation"):
                st.caption(signature["interpretation"])
        with pathway_tab:
            e1, e2 = st.columns(2)
            with e1:
                st.markdown("#### Upregulated Program")
                up = signature.get("up_pathway_enrichment", {})
                if up.get("ok"):
                    st.dataframe(up.get("results", []), width="stretch", hide_index=True)
                else:
                    st.info(up.get("error", "No enrichment available."))
            with e2:
                st.markdown("#### Downregulated Program")
                down = signature.get("down_pathway_enrichment", {})
                if down.get("ok"):
                    st.dataframe(down.get("results", []), width="stretch", hide_index=True)
                else:
                    st.info(down.get("error", "No enrichment available."))
        with perturbation_tab:
            l1000 = signature.get("l1000_reversal", {})
            if l1000.get("ok"):
                st.dataframe(l1000.get("top_drugs", []), width="stretch", hide_index=True)
                if l1000.get("combinations"):
                    st.markdown("#### Combination Hypotheses")
                    st.dataframe(l1000["combinations"], width="stretch", hide_index=True)
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
    render_feature_header(
        "Gene Set Comparison", "comparison",
        "Compare a focused gene set side by side using the same production evidence architecture.",
    )
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
            st.dataframe(rows, width="stretch", hide_index=True)
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

