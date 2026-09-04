"""
connectors/cgga.py
===================

CGGA (Chinese Glioma Genome Atlas) requires free registration at
http://www.cgga.org.cn before any download (see SOURCE_REGISTRY). This
module is the documented integration point: once a team member completes
that registration and the raw expression/clinical files are placed under
data/_cache/cgga/, a real ingestion function belongs here (parse ->
harmonize to the same column contract as connectors/cohort_survival.py ->
cache). Until then, cohort_survival.load_cohort_survival("CGGA", gene)
serves the labeled synthetic fallback so the rest of the pipeline can be
built and tested against the correct *shape* of CGGA data now.
"""
from .base import SOURCE_REGISTRY

CGGA_META = SOURCE_REGISTRY["cgga"]


def registration_reminder() -> str:
    return (
        f"CGGA data requires free registration at {CGGA_META.base_url} and agreement to "
        f"their data-use terms before download. {CGGA_META.license_note}"
    )
