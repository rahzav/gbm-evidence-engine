"""Live cBioPortal helpers for GBM target profiling.

The public cBioPortal API is used for gene identity plus TCGA-GBM mutation,
copy-number and expression summaries. Calls are deliberately small and
source-specific so a temporary failure never invalidates the rest of a
research profile.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Optional
import urllib.parse
import statistics

from .base import http_get_json, SOURCE_REGISTRY

BASE = SOURCE_REGISTRY["cbioportal"].base_url
DEFAULT_GBM_STUDY = "gbm_tcga_pan_can_atlas_2018"


def get_portal_info() -> Optional[dict]:
    return http_get_json(f"{BASE}/info")


def get_gene(gene: str) -> Optional[dict]:
    return http_get_json(f"{BASE}/genes/{urllib.parse.quote(gene.upper())}")


def find_studies(keyword: str) -> Optional[list[dict]]:
    q = urllib.parse.quote(keyword)
    return http_get_json(f"{BASE}/studies?keyword={q}&projection=SUMMARY")


def get_molecular_profiles(study_id: str) -> Optional[list[dict]]:
    return http_get_json(f"{BASE}/studies/{study_id}/molecular-profiles")


def get_sample_lists(study_id: str) -> Optional[list[dict]]:
    return http_get_json(f"{BASE}/studies/{study_id}/sample-lists")


def get_sample_list(sample_list_id: str) -> Optional[dict]:
    return http_get_json(f"{BASE}/sample-lists/{sample_list_id}")


def _params(**kwargs) -> str:
    return urllib.parse.urlencode({k: v for k, v in kwargs.items() if v is not None})


def get_mutations_in_gene(molecular_profile_id: str, sample_list_id: str,
                          entrez_gene_id: int) -> Optional[list[dict]]:
    qs = _params(sampleListId=sample_list_id, entrezGeneId=entrez_gene_id,
                 projection="SUMMARY")
    return http_get_json(f"{BASE}/molecular-profiles/{molecular_profile_id}/mutations?{qs}")


def get_copy_number_in_gene(molecular_profile_id: str, sample_list_id: str,
                            entrez_gene_id: int) -> Optional[list[dict]]:
    qs = _params(sampleListId=sample_list_id, entrezGeneId=entrez_gene_id,
                 discreteCopyNumberEventType="ALL", projection="SUMMARY")
    return http_get_json(
        f"{BASE}/molecular-profiles/{molecular_profile_id}/discrete-copy-number?{qs}"
    )


def get_expression_in_gene(molecular_profile_id: str, sample_list_id: str,
                           entrez_gene_id: int) -> Optional[list[dict]]:
    qs = _params(sampleListId=sample_list_id, entrezGeneId=entrez_gene_id,
                 projection="SUMMARY")
    return http_get_json(
        f"{BASE}/molecular-profiles/{molecular_profile_id}/molecular-data?{qs}"
    )


def _pick_profile(profiles: list[dict], kind: str) -> Optional[dict]:
    if kind == "mutation":
        candidates = [p for p in profiles if "MUTATION" in str(p.get("molecularAlterationType", ""))]
    elif kind == "cna":
        candidates = [p for p in profiles if "COPY_NUMBER" in str(p.get("molecularAlterationType", ""))
                      and str(p.get("datatype", "")).upper() == "DISCRETE"]
    elif kind == "expression":
        candidates = [p for p in profiles if "MRNA_EXPRESSION" in str(p.get("molecularAlterationType", ""))]
        z = [p for p in candidates if "ZSCORE" in str(p.get("datatype", "")).upper()
             or "ZSCORE" in str(p.get("molecularProfileId", "")).upper()]
        if z:
            candidates = z
    else:
        return None
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (
        not bool(p.get("showProfileInAnalysisTab", False)),
        "RNA" not in str(p.get("molecularProfileId", "")).upper(),
    ))[0]


def _record_value(row: dict) -> Optional[float]:
    for key in ("value", "alteration"):
        value = row.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return None


def _mutation_label(row: dict) -> str | None:
    for key in ("proteinChange", "proteinChangeShort", "aminoAcidChange"):
        value = row.get(key)
        if value and str(value).strip() not in {"", "NA", "N/A"}:
            return str(value).strip()
    return None


def _summarize_mutation_variants(rows: list[dict], denominator: int | None, limit: int = 10) -> dict:
    """Summarize recurrent protein changes and mutation classes by unique sample.

    cBioPortal can return more than one mutation row per sample. Counts here are
    unique-sample counts so recurrent calls are not inflated by duplicate rows.
    """
    variant_samples: dict[str, set[str]] = defaultdict(set)
    variant_records: Counter[str] = Counter()
    type_samples: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        sample = str(row.get("sampleId") or "").strip()
        label = _mutation_label(row)
        if label:
            variant_records[label] += 1
            if sample:
                variant_samples[label].add(sample)
        mutation_type = str(row.get("mutationType") or row.get("variantType") or "").strip()
        if mutation_type and sample:
            type_samples[mutation_type].add(sample)

    top_variants = []
    for label, samples in sorted(
        variant_samples.items(),
        key=lambda item: (-len(item[1]), -variant_records[item[0]], item[0]),
    )[:limit]:
        n = len(samples)
        top_variants.append({
            "protein_change": label,
            "sample_count": n,
            "frequency_in_profiled_cohort": (n / denominator if denominator else None),
            "mutation_records": int(variant_records[label]),
        })

    mutation_types = [
        {
            "mutation_type": mutation_type,
            "sample_count": len(samples),
            "frequency_in_profiled_cohort": (len(samples) / denominator if denominator else None),
        }
        for mutation_type, samples in sorted(type_samples.items(), key=lambda item: (-len(item[1]), item[0]))
    ]
    return {"top_variants": top_variants, "mutation_types": mutation_types}


def summarize_gbm_gene(gene: str, study_id: str = DEFAULT_GBM_STUDY) -> dict:
    """Return a compact, live TCGA-GBM genomic profile for ``gene``.

    Missing sub-layers are represented as ``None`` instead of raising. This is
    important because public portal studies differ in which molecular profiles
    they expose.
    """
    gene = gene.strip().upper()
    info = get_gene(gene)
    if not info:
        return {"ok": False, "gene": gene, "study_id": study_id,
                "error": "Gene could not be resolved in cBioPortal."}
    entrez = info.get("entrezGeneId")
    profiles = get_molecular_profiles(study_id) or []
    lists = get_sample_lists(study_id) or []
    all_list = next((x for x in lists if x.get("sampleListId") == f"{study_id}_all"), None)
    if not all_list and lists:
        all_list = next((x for x in lists if str(x.get("category", "")).lower() == "all_cases_in_study"), lists[0])
    sample_list_id = (all_list or {}).get("sampleListId", f"{study_id}_all")
    sample_ids = (all_list or {}).get("sampleIds") or []
    if not sample_ids:
        fetched = get_sample_list(sample_list_id) or {}
        sample_ids = fetched.get("sampleIds") or []
    denominator = len(sample_ids) or None

    mutation_profile = _pick_profile(profiles, "mutation")
    cna_profile = _pick_profile(profiles, "cna")
    expr_profile = _pick_profile(profiles, "expression")

    mutations = (get_mutations_in_gene(mutation_profile["molecularProfileId"], sample_list_id, int(entrez))
                 if mutation_profile and entrez is not None else None)
    cna = (get_copy_number_in_gene(cna_profile["molecularProfileId"], sample_list_id, int(entrez))
           if cna_profile and entrez is not None else None)
    expression = (get_expression_in_gene(expr_profile["molecularProfileId"], sample_list_id, int(entrez))
                  if expr_profile and entrez is not None else None)

    mutation_samples = {r.get("sampleId") for r in (mutations or []) if r.get("sampleId")}
    mutation_detail = _summarize_mutation_variants(mutations or [], denominator)
    cna_values = [_record_value(r) for r in (cna or [])]
    cna_values = [v for v in cna_values if v is not None]
    expr_values = [_record_value(r) for r in (expression or [])]
    expr_values = [v for v in expr_values if v is not None]

    cna_n = len(cna_values) or denominator
    expr_n = len(expr_values)
    amp_count = sum(v >= 2 for v in cna_values)
    homdel_count = sum(v <= -2 for v in cna_values)
    high_expr_count = sum(v >= 2 for v in expr_values)
    low_expr_count = sum(v <= -2 for v in expr_values)

    return {
        "ok": True,
        "gene": gene,
        "gene_name": info.get("hugoGeneSymbol", gene),
        "entrez_gene_id": entrez,
        "cytoband": info.get("cytoband"),
        "study_id": study_id,
        "sample_list_id": sample_list_id,
        "n_samples": denominator,
        "mutation": {
            "profile_id": (mutation_profile or {}).get("molecularProfileId"),
            "mutated_samples": len(mutation_samples),
            "frequency": (len(mutation_samples) / denominator if denominator else None),
            "records": len(mutations or []),
            "top_variants": mutation_detail["top_variants"],
            "mutation_types": mutation_detail["mutation_types"],
        } if mutations is not None else None,
        "copy_number": {
            "profile_id": (cna_profile or {}).get("molecularProfileId"),
            "n": cna_n,
            "amplified": amp_count,
            "amplification_frequency": (amp_count / cna_n if cna_n else None),
            "deep_deleted": homdel_count,
            "deep_deletion_frequency": (homdel_count / cna_n if cna_n else None),
        } if cna is not None else None,
        "expression": {
            "profile_id": (expr_profile or {}).get("molecularProfileId"),
            "n": expr_n,
            "median": (statistics.median(expr_values) if expr_values else None),
            "high_zscore_frequency": (high_expr_count / expr_n if expr_n else None),
            "low_zscore_frequency": (low_expr_count / expr_n if expr_n else None),
        } if expression is not None else None,
    }
