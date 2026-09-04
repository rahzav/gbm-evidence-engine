"""
connectors/cbioportal.py
=========================

Live REST client for cBioPortal (https://www.cbioportal.org/api,
Swagger at /api/swagger-ui/index.html). No API key required for the public
instance. Real endpoints used here:

    GET /studies?keyword={term}
    GET /studies/{studyId}/molecular-profiles
    GET /molecular-profiles/{molecularProfileId}/mutations?sampleListId=...
    GET /studies/{studyId}/clinical-data?clinicalDataType=PATIENT

This mirrors what cBioPortal's own new MCP/chat prototype does under the
hood (see docs/ARCHITECTURE.md "Landscape verdict") — the difference is that
here, results get wrapped in a provenance-tracked EvidenceRecord and cross-
validated against independent cohorts, rather than answered as a one-off
chat message.

IMPORTANT: this sandbox has no network egress, so `fetch_*` calls below will
return None here and the caller should fall back to a cached/demo snapshot
(see scripts/run_demo_dossier.py for exactly that fallback pattern). Point
this module at a networked environment and it works unmodified.
"""

from __future__ import annotations
from typing import Optional
from .base import http_get_json, SOURCE_REGISTRY

BASE = SOURCE_REGISTRY["cbioportal"].base_url


def get_portal_info() -> Optional[dict]:
    return http_get_json(f"{BASE}/info")


def find_studies(keyword: str) -> Optional[list[dict]]:
    return http_get_json(f"{BASE}/studies?keyword={keyword}&projection=SUMMARY")


def get_molecular_profiles(study_id: str) -> Optional[list[dict]]:
    return http_get_json(f"{BASE}/studies/{study_id}/molecular-profiles")


def get_mutations_in_gene(molecular_profile_id: str, sample_list_id: str, hugo_gene_symbol: str) -> Optional[list[dict]]:
    url = (f"{BASE}/molecular-profiles/{molecular_profile_id}/mutations"
           f"?sampleListId={sample_list_id}&geneIdType=HUGO_GENE_SYMBOL"
           f"&projection=SUMMARY")
    return http_get_json(url)


def get_clinical_data(study_id: str) -> Optional[list[dict]]:
    return http_get_json(f"{BASE}/studies/{study_id}/clinical-data?clinicalDataType=PATIENT")
