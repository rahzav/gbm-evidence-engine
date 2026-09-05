"""V5 researcher-facing augmentation for GBM Gene Analysis.

V5 preserves the validated V4 priority score and adds non-scoring context that
researchers routinely need to verify manually: canonical gene identity, normal
human tissue/brain expression, high-confidence interaction networks, candidate
BBB permeability, concise evidence-consistency flags, and direct atlas links.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from gbm_evidence_engine.research_intelligence import ResearchProfile
from gbm_evidence_engine.research_intelligence_v4 import build_research_profile as build_v4_profile
from gbm_evidence_engine.connectors import mygene, hpa, stringdb, b3db_live

GBMAP_COLLECTION = "https://cellxgene.cziscience.com/collections/999f2a15-3d7e-440b-96ae-2c806799c08c"


def _consistency_review(profile: ResearchProfile) -> dict:
    flags: list[str] = []
    cgg = profile.live.get("cgga", {})
    dep = profile.live.get("depmap", {})
    gla = profile.live.get("glass", {})

    if cgg.get("n_usable_cohorts", 0) >= 2 and cgg.get("direction_consistent") is False:
        flags.append("CGGA survival associations are directionally discordant across the two independent cohorts.")
    if dep.get("ok") and dep.get("pan_essential"):
        flags.append("DepMap identifies the gene as pan-essential, limiting interpretation of GBM dependency as a selective therapeutic vulnerability.")
    if gla.get("ok") and gla.get("gbm_specific") and gla.get("n_pairs", 0) < 10:
        flags.append("GLASS longitudinal evidence is based on a small number of clinically verified GBM pairs and should be interpreted as preliminary.")

    available = [(name, d.score) for name, d in profile.score.dimensions.items() if d.score is not None]
    strongest = max(available, key=lambda x: x[1]) if available else None
    weakest = min(available, key=lambda x: x[1]) if available else None
    missing = [name for name, d in profile.score.dimensions.items() if d.score is None]

    return {
        "status": "Review recommended" if flags else "No major within-source conflicts detected",
        "flags": flags,
        "strongest_dimension": {"name": strongest[0], "score": round(float(strongest[1]), 1)} if strongest else None,
        "lowest_available_dimension": {"name": weakest[0], "score": round(float(weakest[1]), 1)} if weakest else None,
        "missing_dimensions": missing,
        "note": "This review flags internal evidence limitations and source-level discordance. It does not treat biologically distinct evidence types as if they measured the same phenomenon.",
    }


def _key_findings(profile: ResearchProfile, hpa_context: dict, network: dict, bbb: dict, identity: dict) -> list[str]:
    findings: list[str] = []
    if identity.get("ok") and identity.get("was_normalized"):
        findings.append(f"Input normalized to the approved human gene symbol {identity['symbol']} from alias {identity['query']}.")

    score = profile.score
    if score.overall is not None:
        findings.append(f"Target Priority Score: {score.overall}/100 with {score.evidence_coverage_pct}% scored-evidence coverage.")

    dep = profile.live.get("depmap", {})
    if dep.get("ok"):
        if dep.get("pan_essential"):
            findings.append("DepMap indicates broad pan-essential dependency rather than a clearly GBM-selective dependency pattern.")
        elif dep.get("median_selectivity_delta") is not None:
            findings.append(f"DepMap GBM selectivity difference: {float(dep['median_selectivity_delta']):.2f} Chronos units.")

    cgg = profile.live.get("cgga", {})
    meta = cgg.get("meta_analysis") if cgg.get("ok") else None
    if meta:
        findings.append(f"CGGA pooled survival association: HR {float(meta['pooled_hr']):.2f} per 1-SD expression, p={float(meta['pooled_p_value']):.2g}.")

    if hpa_context.get("ok") and hpa_context.get("normal_brain_max_expression") is not None:
        findings.append(f"Human Protein Atlas normal-brain expression reaches {float(hpa_context['normal_brain_max_expression']):.1f} nTPM/NX in the sampled brain regions shown.")

    if network.get("ok") and network.get("partners"):
        top = ", ".join(p["gene"] for p in network["partners"][:5])
        findings.append(f"High-confidence STRING network neighbors include {top}.")

    if bbb.get("ok") and bbb.get("matched_count", 0):
        findings.append(f"B3DB contains experimental BBB records for {bbb['matched_count']} target-directed candidate compound(s).")
    return findings[:8]


def build_research_profile(gene: str) -> ResearchProfile:
    raw = gene.strip()
    if not raw:
        raise ValueError("Enter a gene symbol.")

    identity = mygene.resolve_gene(raw)
    identity_status = str(identity.get("status") or "").lower()
    if not identity.get("ok") and identity_status in {"not_found", "ambiguous"}:
        detail = identity.get("error") or "No unambiguous human gene match was found."
        raise ValueError(f"Invalid or ambiguous human gene symbol '{raw}': {detail}")

    # A resolver outage is different from a definitively invalid symbol. In that
    # case downstream sources may still resolve the submitted symbol, so preserve
    # the existing partial-evidence behavior rather than blocking the dossier.
    canonical = identity.get("symbol") if identity.get("ok") else raw.upper()
    profile = build_v4_profile(canonical)

    with ThreadPoolExecutor(max_workers=2) as ex:
        hpa_future = ex.submit(hpa.get_gene_context, canonical)
        string_future = ex.submit(stringdb.get_network_context, canonical)
        hpa_context = hpa_future.result()
        network = string_future.result()

    drugs = [d.get("name") for d in (profile.live.get("open_targets", {}).get("drugs") or []) if d.get("name")]
    bbb = b3db_live.lookup_candidates(drugs)
    consistency = _consistency_review(profile)

    profile.live["gene_identity"] = identity
    profile.live["normal_tissue_context"] = hpa_context
    profile.live["interaction_network"] = network
    profile.live["bbb_candidates"] = bbb
    profile.live["evidence_consistency"] = consistency
    profile.live["gbmap_reference"] = {
        "ok": True,
        "name": "GBmap IDH-wildtype glioblastoma single-cell and spatial reference",
        "collection_url": GBMAP_COLLECTION,
        "scope": "Public GBM single-cell/spatial reference collection. Included as a direct research resource; it is not currently used to alter the priority score.",
    }
    profile.live["key_findings"] = _key_findings(profile, hpa_context, network, bbb, identity)

    profile.source_status["Gene identity"] = (
        f"canonical {identity.get('symbol')} via MyGene.info" if identity.get("ok") else "MyGene.info unavailable; downstream sources used the submitted symbol"
    )
    profile.source_status["Human Protein Atlas"] = "normal tissue and brain context available" if hpa_context.get("ok") else "unavailable"
    profile.source_status["STRING"] = f"{len(network.get('partners') or [])} high-confidence partners" if network.get("ok") else "unavailable"
    profile.source_status["B3DB"] = f"{bbb.get('matched_count', 0)} candidate BBB matches" if bbb.get("ok") else "unavailable"
    profile.source_status["GBmap"] = "public single-cell/spatial reference linked"
    return profile


def rank_gene_list(genes: list[str], max_workers: int = 2) -> list[ResearchProfile]:
    cleaned = list(dict.fromkeys(g.strip() for g in genes if g.strip()))
    if not cleaned:
        return []
    workers = max(1, min(int(max_workers), 2))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        profiles = list(ex.map(build_research_profile, cleaned))
    return sorted(profiles, key=lambda p: (p.score.overall is not None, p.score.overall or -1), reverse=True)
