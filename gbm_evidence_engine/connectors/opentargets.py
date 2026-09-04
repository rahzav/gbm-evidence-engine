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
  search(queryString: $q, entityNames: ["target"], page: {index: 0, size: 5}) {
    hits { id name entity }
  }
}
"""

TARGET_PROFILE_QUERY = """
query TargetProfile($ensemblId: String!) {
  target(ensemblId: $ensemblId) {
    id approvedSymbol approvedName biotype
    tractability { label modality value }
    knownDrugs(page: {index: 0, size: 50}) {
      count
      rows {
        drug { id name isApproved }
        disease { id name }
        phase status mechanismOfAction
      }
    }
    associatedDiseases(page: {index: 0, size: 200}) {
      count
      rows {
        score
        disease { id name }
        datatypeScores { id score }
      }
    }
  }
}
"""


def resolve_target(gene: str) -> Optional[str]:
    response = _post_graphql(SEARCH_TARGET_QUERY, {"q": gene.upper()}) or {}
    hits = response.get("data", {}).get("search", {}).get("hits", []) or []
    if not hits:
        return None
    # Target search is ranked; exact symbols generally resolve first. The second
    # query verifies the approved symbol before data are used.
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
    drug_block = target.get("knownDrugs") or {}
    drugs = drug_block.get("rows", []) or []
    gbm_drugs = [r for r in drugs if "glioblast" in str((r.get("disease") or {}).get("name", "")).lower()]
    tract = target.get("tractability") or []
    tractable = [t for t in tract if t.get("value") is True or str(t.get("value")).lower() == "true"]
    max_phase = max([int(r.get("phase") or 0) for r in drugs] or [0])
    max_gbm_phase = max([int(r.get("phase") or 0) for r in gbm_drugs] or [0])
    unique_drugs = []
    seen = set()
    for row in sorted(drugs, key=lambda r: int(r.get("phase") or 0), reverse=True):
        drug = row.get("drug") or {}
        name = drug.get("name")
        if name and name not in seen:
            seen.add(name)
            unique_drugs.append({
                "id": drug.get("id"), "name": name, "is_approved": drug.get("isApproved"),
                "phase": row.get("phase"), "status": row.get("status"),
                "mechanism": row.get("mechanismOfAction"),
                "disease": (row.get("disease") or {}).get("name"),
            })
    return {
        "ok": True,
        "gene": gene,
        "ensembl_id": target.get("id"),
        "approved_name": target.get("approvedName"),
        "biotype": target.get("biotype"),
        "gbm_association_score": gbm_assoc.get("score") if gbm_assoc else None,
        "gbm_association": gbm_assoc,
        "known_drug_count": drug_block.get("count", len(drugs)),
        "gbm_drug_rows": len(gbm_drugs),
        "max_phase": max_phase,
        "max_gbm_phase": max_gbm_phase,
        "tractability_positive": len(tractable),
        "tractability_total": len(tract),
        "tractability": tract,
        "drugs": unique_drugs[:25],
    }


def get_known_drugs(ensembl_gene_id: str) -> Optional[dict]:
    # Backward-compatible helper retained for callers in the V1 codebase.
    response = _post_graphql(TARGET_PROFILE_QUERY, {"ensemblId": ensembl_gene_id})
    if not response:
        return None
    target = response.get("data", {}).get("target")
    return {"data": {"target": target}} if target else None
