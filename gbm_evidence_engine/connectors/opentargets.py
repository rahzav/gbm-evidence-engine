"""Open Targets GraphQL connector for target identity, disease evidence and drugs."""
from __future__ import annotations
from typing import Optional
from .base import SOURCE_REGISTRY, http_post_json

ENDPOINT = SOURCE_REGISTRY["open_targets"].base_url


def _post_graphql(query: str, variables: dict) -> Optional[dict]:
    result = http_post_json(ENDPOINT, {"query": query, "variables": variables}, timeout=25)
    if not isinstance(result, dict) or result.get("errors"):
        return None
    return result


SEARCH_TARGET_QUERY = """
query SearchTarget($q: String!) {
  search(queryString: $q, entityNames: ["target"], page: {index: 0, size: 10}) {
    hits {
      id
      entity
      object {
        ... on Target { approvedSymbol }
      }
    }
  }
}
"""

TARGET_PROFILE_QUERY = """
query TargetProfile($ensemblId: String!) {
  target(ensemblId: $ensemblId) {
    id approvedSymbol approvedName biotype
    tractability { label modality value }
    drugAndClinicalCandidates {
      rows { drug { id name } }
    }
    associatedDiseases(page: {index: 0, size: 200}) {
      rows {
        score
        disease { id name }
      }
    }
  }
}
"""


def resolve_target(gene: str) -> Optional[str]:
    gene = gene.upper().strip()
    response = _post_graphql(SEARCH_TARGET_QUERY, {"q": gene}) or {}
    hits = response.get("data", {}).get("search", {}).get("hits", []) or []
    if not hits:
        return None
    for hit in hits:
        symbol = str((hit.get("object") or {}).get("approvedSymbol") or "").upper()
        if symbol == gene:
            return hit.get("id")
    return hits[0].get("id")


def get_target_profile(gene: str) -> dict:
    gene = gene.upper().strip()
    ensembl = resolve_target(gene)
    if not ensembl:
        return {"ok": False, "gene": gene, "error": "Open Targets could not resolve the gene symbol."}
    response = _post_graphql(TARGET_PROFILE_QUERY, {"ensemblId": ensembl}) or {}
    target = response.get("data", {}).get("target")
    if not target:
        return {"ok": False, "gene": gene, "ensembl_id": ensembl,
                "error": "Open Targets target profile unavailable."}
    approved = (target.get("approvedSymbol") or "").upper()
    if approved and approved != gene:
        return {"ok": False, "gene": gene, "ensembl_id": ensembl,
                "error": f"Gene resolved to {approved}; refusing ambiguous mapping."}

    disease_rows = (target.get("associatedDiseases") or {}).get("rows", []) or []
    gbm_rows = [r for r in disease_rows
                if "glioblast" in str((r.get("disease") or {}).get("name", "")).lower()]
    gbm_assoc = max(gbm_rows, key=lambda r: r.get("score") or 0, default=None)

    drugs = (target.get("drugAndClinicalCandidates") or {}).get("rows", []) or []
    tract = target.get("tractability") or []
    tractable = [t for t in tract if t.get("value") is True or str(t.get("value")).lower() == "true"]
    unique_drugs, seen = [], set()
    for row in drugs:
        drug = row.get("drug") or {}
        name = drug.get("name")
        if name and name not in seen:
            seen.add(name)
            unique_drugs.append({"id": drug.get("id"), "name": name})

    return {
        "ok": True,
        "gene": gene,
        "ensembl_id": target.get("id"),
        "approved_name": target.get("approvedName"),
        "biotype": target.get("biotype"),
        "gbm_association_score": gbm_assoc.get("score") if gbm_assoc else None,
        "gbm_association": gbm_assoc,
        "known_drug_count": len(unique_drugs),
        "gbm_drug_rows": None,
        "max_phase": None,
        "max_gbm_phase": None,
        "drug_phase_available": False,
        "tractability_positive": len(tractable),
        "tractability_total": len(tract),
        "tractability": tract,
        "drugs": unique_drugs[:25],
    }


def get_known_drugs(ensembl_gene_id: str) -> Optional[dict]:
    response = _post_graphql(TARGET_PROFILE_QUERY, {"ensemblId": ensembl_gene_id})
    if not response:
        return None
    target = response.get("data", {}).get("target")
    return {"data": {"target": target}} if target else None
