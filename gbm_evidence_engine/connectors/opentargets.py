"""
connectors/opentargets.py
==========================

Live GraphQL client for the Open Targets Platform
(https://api.platform.opentargets.org/api/v4/graphql). Used for the
"existing compounds / known drugs against this target" evidence layer and
as a disease-agnostic sanity check against our GBM-specific statistics
(see docs/ARCHITECTURE.md's adversarial analysis of Open Targets).

GraphQL needs a POST body; `base.http_get_json` is GET-only, so this module
defines its own minimal POST helper. As with the other live connectors,
this sandbox has no egress, so calls degrade to None here.
"""

from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Optional

from .base import SOURCE_REGISTRY

ENDPOINT = SOURCE_REGISTRY["open_targets"].base_url

KNOWN_DRUGS_QUERY = """
query KnownDrugs($ensemblId: String!) {
  target(ensemblId: $ensemblId) {
    approvedSymbol
    knownDrugs {
      rows {
        drug { name }
        mechanismOfAction
        phase
        status
        disease { name }
      }
    }
  }
}
"""


def _post_graphql(query: str, variables: dict) -> Optional[dict]:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def get_known_drugs(ensembl_gene_id: str) -> Optional[dict]:
    return _post_graphql(KNOWN_DRUGS_QUERY, {"ensemblId": ensembl_gene_id})
