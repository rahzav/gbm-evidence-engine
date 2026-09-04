"""
connectors/glass.py
====================

GLASS (Glioma Longitudinal AnalySiS Consortium) data lives on Synapse
(project syn17038081) and requires a free Synapse account plus acceptance
of the GLASS data-use policy (see SOURCE_REGISTRY) — it is not a simple
anonymous REST endpoint. This module is the documented integration point
for a real `synapseclient`-based ingestion job; until that is wired up in a
networked deployment, cohort_survival.load_cohort_survival("GLASS_recurrent",
gene) serves the labeled synthetic fallback.

GLASS is the one resource in this whole engine that is essentially unique
to glioma — it is what makes primary-to-recurrent longitudinal evidence
possible at all, which is why it gets a first-class place in the evidence
model even though V1 cannot legally auto-ingest it without a registered
team member completing the DUA first.
"""
from .base import SOURCE_REGISTRY

GLASS_META = SOURCE_REGISTRY["glass"]


def registration_reminder() -> str:
    return (
        f"GLASS data requires a free Synapse account and acceptance of the GLASS consortium's "
        f"data-use policy before download ({GLASS_META.base_url}). {GLASS_META.license_note}"
    )
