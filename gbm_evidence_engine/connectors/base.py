"""
connectors/base.py
===================

Shared plumbing for every data connector, plus SOURCE_REGISTRY: an explicit,
human-auditable record of how each upstream resource is actually reached.

This registry exists because Phase 4 of the product brief demands the system
be honest about provenance, and Phase 4's "Privacy/legal" section demands we
"audit licenses and API restrictions before implementation." A generic
tool-calling agent (see docs/ARCHITECTURE.md's discussion of ToolUniverse/
TxAgent) treats every API the same way — call it, get JSON back. GBM research
data doesn't work like that: cBioPortal/Open Targets/Europe PMC/
ClinicalTrials.gov are genuinely live, no-registration REST/GraphQL APIs;
Ivy GAP and DepMap's public release are open but distributed as versioned
bulk downloads, not low-latency per-gene endpoints; CGGA and GLASS require a
free registration / data-use agreement before any ingestion. Collapsing that
distinction is how a tool ends up over-promising "live" data or, worse,
silently re-hosting data it wasn't licensed to redistribute.
"""

from __future__ import annotations

import time
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from gbm_evidence_engine.evidence_model import AccessTier

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SourceMeta:
    name: str
    access_tier: AccessTier
    base_url: str
    version_note: str
    license_note: str


SOURCE_REGISTRY: dict[str, SourceMeta] = {
    "cbioportal": SourceMeta(
        name="cBioPortal (TCGA-GBM and other public studies)",
        access_tier=AccessTier.OPEN_LIVE_API,
        base_url="https://www.cbioportal.org/api",
        version_note="Live query against whatever study snapshot cBioPortal currently serves; "
                      "record the portalVersion (GET /api/info) alongside every result.",
        license_note="Public studies are CC0/open for research use; no API key needed.",
    ),
    "open_targets": SourceMeta(
        name="Open Targets Platform",
        access_tier=AccessTier.OPEN_LIVE_API,
        base_url="https://api.platform.opentargets.org/api/v4/graphql",
        version_note="Bi-monthly Open Targets data releases; record the release tag returned by the API.",
        license_note="Apache 2.0 code, open data, free for academic and commercial use with citation.",
    ),
    "europepmc": SourceMeta(
        name="Europe PMC",
        access_tier=AccessTier.OPEN_LIVE_API,
        base_url="https://www.ebi.ac.uk/europepmc/webservices/rest",
        version_note="Live full-text/abstract search, continuously updated.",
        license_note="Open API, no registration required.",
    ),
    "clinicaltrials": SourceMeta(
        name="ClinicalTrials.gov",
        access_tier=AccessTier.OPEN_LIVE_API,
        base_url="https://clinicaltrials.gov/api/v2",
        version_note="Live registry query.",
        license_note="US government public data.",
    ),
    "ivygap": SourceMeta(
        name="Ivy Glioblastoma Atlas Project",
        access_tier=AccessTier.OPEN_BULK_DOWNLOAD,
        base_url="http://glioblastoma.alleninstitute.org / http://www.ivygap.org",
        version_note="~270 laser-microdissection RNA-seq samples from 41 patients across 7 anatomic "
                      "zones; ingest as a versioned snapshot, not a per-query live call.",
        license_note="Free Allen Institute resource; no registration for bulk download.",
    ),
    "depmap": SourceMeta(
        name="DepMap (CRISPR gene-effect scores, public release)",
        access_tier=AccessTier.OPEN_BULK_DOWNLOAD,
        base_url="https://depmap.org/portal/download/",
        version_note="Quarterly public releases (e.g. 24Q4); pin the exact release string in every "
                      "EvidenceRecord — dependency scores shift slightly between releases.",
        license_note="CC0 / open for research use, no registration required for the public release.",
    ),
    "cgga": SourceMeta(
        name="Chinese Glioma Genome Atlas",
        access_tier=AccessTier.REGISTRATION_GATED,
        base_url="http://www.cgga.org.cn",
        version_note="Free registration required before download; re-verify the data-use terms "
                      "before serving anything beyond derived summary statistics.",
        license_note="Free for academic research after registration; do not re-host raw matrices.",
    ),
    "glass": SourceMeta(
        name="GLASS Consortium (Glioma Longitudinal AnalySiS)",
        access_tier=AccessTier.REGISTRATION_GATED,
        base_url="https://www.synapse.org (project syn17038081)",
        version_note="Free Synapse account + acceptance of the GLASS data-use policy required.",
        license_note="Open research-use data once registered; do not re-host raw matrices.",
    ),
    "b3db": SourceMeta(
        name="B3DB blood-brain barrier permeability database",
        access_tier=AccessTier.OPEN_BULK_DOWNLOAD,
        base_url="https://github.com/theochem/B3DB",
        version_note="Static curated compilation (~7,800 compounds, ~1,058 with numeric logBB).",
        license_note="Open, citation requested.",
    ),
}


def http_get_json(url: str, timeout: int = 20) -> Optional[dict]:
    """Best-effort GET+JSON. Returns None (never raises) if the network call
    fails — this sandbox has no egress, so this always returns None here, but
    the function is what a deployed instance with network access would use."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None
