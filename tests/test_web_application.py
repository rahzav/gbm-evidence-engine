"""Contracts for the standalone Glia web application."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import app
from gbm_evidence_engine import research_agent


def test_web_application_and_assets_are_served():
    client = TestClient(app)
    page = client.get("/")
    styles = client.get("/assets/styles.css")
    script = client.get("/assets/app.js")

    assert page.status_code == 200
    assert "GLIA" in page.text
    assert "Open Glia" in page.text
    assert styles.status_code == 200
    assert script.status_code == 200
    assert "highlight" not in page.text.lower() or "Ask Glia" in script.text


def test_serialized_profile_is_available_to_glia_without_rebuilding():
    registry = {}
    profile = {
        "gene": "EGFR",
        "software_version": "7.0.0",
        "score": {
            "overall": 64.2,
            "label": "Moderate research priority",
            "evidence_coverage_pct": 82.5,
            "caveat": "Research use only",
        },
        "live": {
            "key_findings": ["Functional evidence is strongest."],
            "overall_evidence_confidence": {"level": "moderate"},
            "literature": {"top_papers": []},
        },
        "dossier": {"evidence": []},
        "evidence_gaps": ["Human validation is incomplete."],
        "next_experiments": ["Validate in a patient-derived model."],
        "source_status": {"DepMap": "available"},
    }

    payload = research_agent._profile_payload(profile, registry)

    assert payload["gene"] == "EGFR"
    assert payload["target_priority_score"] == 64.2
    assert payload["key_findings"] == ["Functional evidence is strongest."]
    assert payload["analysis_citation"] == "[AN:GENE:EGFR]"
