"""ClinicalTrials.gov API v2 connector for GBM target/drug landscape."""
from __future__ import annotations
from typing import Optional, Iterable
import urllib.parse
from .base import http_get_json, SOURCE_REGISTRY

BASE = SOURCE_REGISTRY["clinicaltrials"].base_url
ACTIVE_STATUSES = {
    "RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"
}


def search_trials(condition: str = "glioblastoma", intervention: Optional[str] = None,
                  term: Optional[str] = None, page_size: int = 20) -> Optional[dict]:
    params = {"query.cond": condition, "pageSize": str(page_size), "format": "json"}
    if intervention:
        params["query.intr"] = intervention
    if term:
        params["query.term"] = term
    return http_get_json(f"{BASE}/studies?{urllib.parse.urlencode(params)}")


def _flatten_study(study: dict, matched_term: str) -> dict:
    ps = study.get("protocolSection", {})
    ident = ps.get("identificationModule", {})
    status = ps.get("statusModule", {})
    design = ps.get("designModule", {})
    interventions = ps.get("armsInterventionsModule", {}).get("interventions", []) or []
    return {
        "nct_id": ident.get("nctId"),
        "title": ident.get("briefTitle"),
        "overall_status": status.get("overallStatus"),
        "phases": design.get("phases") or [],
        "interventions": [i.get("name") for i in interventions if i.get("name")],
        "matched_term": matched_term,
    }


def search_target_landscape(gene: str, drug_names: Iterable[str] = (), page_size: int = 50) -> dict:
    terms = [gene] + [d for d in drug_names if d][:4]
    merged: dict[str, dict] = {}
    source_ok = False
    for term in terms:
        result = search_trials(condition="glioblastoma", term=term, page_size=page_size)
        if result is None:
            continue
        source_ok = True
        for study in result.get("studies", []):
            row = _flatten_study(study, term)
            key = row.get("nct_id") or f"{term}:{len(merged)}"
            if key not in merged:
                merged[key] = row
            elif term not in str(merged[key].get("matched_term")):
                merged[key]["matched_term"] = f"{merged[key]['matched_term']}, {term}"
    studies = list(merged.values())
    active = [s for s in studies if s.get("overall_status") in ACTIVE_STATUSES]
    phase_numbers = []
    for s in studies:
        for phase in s.get("phases", []):
            digits = ''.join(ch for ch in str(phase) if ch.isdigit())
            if digits:
                phase_numbers.append(int(digits[0]))
    return {
        "ok": source_ok,
        "total": len(studies),
        "active": len(active),
        "max_phase": max(phase_numbers) if phase_numbers else 0,
        "studies": studies[:30],
    }
