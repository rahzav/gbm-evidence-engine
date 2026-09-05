from types import SimpleNamespace

from gbm_evidence_engine.research_agent import (
    AgentReference,
    _signature_payload,
    run_agent_turn,
    validate_quantitative_grounding,
)


class FakeResponses:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            tool_call = SimpleNamespace(
                type="function_call",
                name="build_gene_dossier",
                arguments='{"gene":"EGFR"}',
                call_id="call_1",
            )
            return SimpleNamespace(output=[tool_call], output_text="")
        return SimpleNamespace(
            output=[],
            output_text="EGFR has a Target Priority Score of 64.2 [AN:GENE:EGFR].",
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def fake_dispatch(name, arguments, session_context, registry):
    assert name == "build_gene_dossier"
    assert arguments == {"gene": "EGFR"}
    registry["AN:GENE:EGFR"] = AgentReference(
        token="AN:GENE:EGFR",
        label="Production GBM Gene Analysis dossier for EGFR",
        source="GBM Gene Analysis 7.0.0",
        kind="analysis",
    )
    return {
        "analysis_citation": "[AN:GENE:EGFR]",
        "gene": "EGFR",
        "target_priority_score": 64.2,
    }


def test_agent_runs_bounded_function_call_loop_with_grounded_output():
    result = run_agent_turn(
        "Why is EGFR interesting?",
        client=FakeClient(),
        tool_dispatcher=fake_dispatch,
        model="gpt-5.4",
    )
    assert result.grounding_ok
    assert result.unmatched_numbers == []
    assert result.tools_used == ["build_gene_dossier"]
    assert result.references[0]["token"] == "AN:GENE:EGFR"
    assert "64.2" in result.text


def test_quantitative_grounding_rejects_unreturned_statistic():
    ok, unmatched = validate_quantitative_grounding(
        "The score was 88.7%.",
        [{"score": 64.2}],
    )
    assert not ok
    assert "88.7%" in unmatched


def test_researcher_context_excludes_raw_table_fields():
    registry = {}
    signature = {
        "n_input_genes": 8,
        "n_statistically_supported": 6,
        "statistics_provided": True,
        "top_genes_profiled": [{"gene": "EGFR", "discovery_priority": 79}],
        "up_pathway_enrichment": {"ok": True, "results": []},
        "down_pathway_enrichment": {"ok": True, "results": []},
        "l1000_reversal": {"ok": True, "top_drugs": []},
        "interpretation": "Processed result context.",
        "software_version": "7.0.0",
        "raw_table": "must not leave the application",
        "uploaded_rows": [{"patient": "example"}],
    }
    payload = _signature_payload(signature, registry)
    assert "raw_table" not in payload
    assert "uploaded_rows" not in payload
    assert payload["n_input_genes"] == 8
    assert "CTX:RESEARCHER_DATA" in registry
