"""Shared source metadata, cache paths, and resilient JSON HTTP helpers."""
from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from gbm_evidence_engine.evidence_model import AccessTier

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
USER_AGENT = "GBM-Gene-Analysis/6.0 (+https://github.com/rahzav/gbm-evidence-engine)"


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
        version_note="Live public-study query; retain study/profile identifiers and retrieval time.",
        license_note="Public study data are openly accessible through cBioPortal; source-study terms still apply.",
    ),
    "open_targets": SourceMeta(
        name="Open Targets Platform",
        access_tier=AccessTier.OPEN_LIVE_API,
        base_url="https://api.platform.opentargets.org/api/v4/graphql",
        version_note="Live Open Targets Platform GraphQL query.",
        license_note="Open platform data; cite Open Targets and underlying evidence sources.",
    ),
    "europepmc": SourceMeta(
        name="Europe PMC",
        access_tier=AccessTier.OPEN_LIVE_API,
        base_url="https://www.ebi.ac.uk/europepmc/webservices/rest",
        version_note="Live literature index, continuously updated.",
        license_note="Open API; individual article reuse rights vary by publication.",
    ),
    "clinicaltrials": SourceMeta(
        name="ClinicalTrials.gov",
        access_tier=AccessTier.OPEN_LIVE_API,
        base_url="https://clinicaltrials.gov/api/v2",
        version_note="Live ClinicalTrials.gov API v2 registry query.",
        license_note="US government public registry data.",
    ),
    "ivygap": SourceMeta(
        name="Ivy Glioblastoma Atlas Project",
        access_tier=AccessTier.OPEN_BULK_DOWNLOAD,
        base_url="https://glioblastoma.alleninstitute.org",
        version_note="Official normalized RNA-seq snapshot: 270 laser-microdissection samples across seven GBM anatomic structures.",
        license_note="Allen Institute research resource; cache source files locally and cite the Ivy GAP resource rather than re-hosting raw matrices.",
    ),
    "depmap": SourceMeta(
        name="DepMap public Breadbox / Chronos",
        access_tier=AccessTier.OPEN_LIVE_API,
        base_url="https://depmap.org/portal/breadbox",
        version_note="Live Breadbox access to the current public Chronos_Combined matrix and model metadata; dependency values may change across DepMap releases.",
        license_note="Public research access is available; DepMap's current data-use terms apply and commercial use may require separate licensing.",
    ),
    "cgga": SourceMeta(
        name="Chinese Glioma Genome Atlas",
        access_tier=AccessTier.OPEN_BULK_DOWNLOAD,
        base_url="https://www.cgga.org.cn/download.jsp",
        version_note="Public mRNAseq_693 and mRNAseq_325 RSEM-gene/clinical snapshots dated 2020-05-06, as currently exposed by the CGGA download site.",
        license_note="Use for research with CGGA citation; cache locally and do not re-host raw matrices.",
    ),
    "glass": SourceMeta(
        name="GLASS Consortium (Glioma Longitudinal AnalySiS)",
        access_tier=AccessTier.REGISTRATION_GATED,
        base_url="https://www.synapse.org (project syn17038081)",
        version_note="Current gene TPM matrix entity syn57367276; download requires an authenticated Synapse account with applicable access conditions accepted.",
        license_note="Controlled research-use data; never expose credentials or re-host controlled raw matrices.",
    ),
    "b3db": SourceMeta(
        name="B3DB blood-brain barrier permeability database",
        access_tier=AccessTier.OPEN_BULK_DOWNLOAD,
        base_url="https://github.com/theochem/B3DB",
        version_note="Static curated BBB permeability compilation.",
        license_note="Open research resource; citation requested.",
    ),
}


_TRANSIENT_HTTP_ERRORS = (
    urllib.error.URLError,
    TimeoutError,
    ValueError,
    json.JSONDecodeError,
    http.client.IncompleteRead,
    ConnectionResetError,
    BrokenPipeError,
)


def _read_json(req: urllib.request.Request, timeout: int, retries: int):
    """Read JSON with bounded retries for transient/truncated upstream responses."""
    for attempt in range(max(1, retries)):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Client errors are normally deterministic; retry only transient
            # gateway/rate-limit/server responses.
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                return None
            if attempt >= retries - 1:
                return None
        except _TRANSIENT_HTTP_ERRORS:
            if attempt >= retries - 1:
                return None
        time.sleep(0.6 * (attempt + 1))
    return None


def http_get_json(url: str, timeout: int = 20, retries: int = 3) -> Optional[dict]:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    result = _read_json(req, timeout=timeout, retries=retries)
    return result if isinstance(result, dict) else result


def http_post_json(url: str, payload: dict | list, timeout: int = 20, retries: int = 3) -> Optional[dict | list]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    result = _read_json(req, timeout=timeout, retries=retries)
    return result if isinstance(result, (dict, list)) else None
