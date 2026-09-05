import json
from types import SimpleNamespace

from gbm_evidence_engine.research_agent import (
    AgentReference,
    ResearchAgentError,
    _bounded_json,
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


class FakeRateLimitError(RuntimeError):
    status_code = 429


class FakeRequestTooLargeError(RuntimeError):
    status_code = 413


class RateLimitedResponses:
    def create(self, **kwargs):
        raise FakeRateLimitError("rate limit exceeded")


class RateLimitedClient:
    def __init__(self):
        self.responses = RateLimitedResponses()


class TooLargeResponses:
    def create(self, **kwargs):
        raise FakeRequestTooLargeError("Request too large on tokens per minute; rate_limit_exceeded")


class TooLargeClient:
    def __init__(self):
        self.responses = TooLargeResponses()


class CaptureResponses:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output=[], output_text="No quantitative claim.")


class CaptureClient:
    def __init__(self):
        self.responses = CaptureResponses()


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
        model="openai/gpt-oss-120b",
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


def test_rate_limit_is_presented_as_temporary_shared_capacity():
    try:
        run_agent_turn("Compare EGFR and CDK4.", client=RateLimitedClient(), model="openai/gpt-oss-120b")
    except ResearchAgentError as exc:
        assert "temporarily at capacity" in str(exc)
        assert "Groq free tier" in str(exc)
    else:
        raise AssertionError("Expected ResearchAgentError for a Groq 429 response")


def test_413_request_size_error_is_friendly_and_provider_details_are_hidden():
    try:
        run_agent_turn("Explain the strongest finding.", client=TooLargeClient(), model="openai/gpt-oss-120b")
    except ResearchAgentError as exc:
        message = str(exc)
        assert "free-tier context limit" in message
        assert "org_" not in message
        assert "8953" not in message
    else:
        raise AssertionError("Expected ResearchAgentError for a 413 response")


def test_history_memory_and_output_budget_are_bounded_before_provider_call():
    client = CaptureClient()
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": "x" * 10000}
        for i in range(12)
    ]
    memory = {"recent_questions": ["y" * 5000] * 20, "investigated_genes": ["EGFR"]}
    run_agent_turn(
        "Summarize this workspace.",
        history=history,
        persistent_memory=memory,
        client=client,
        model="openai/gpt-oss-120b",
    )
    kwargs = client.responses.kwargs
    assert kwargs is not None
    assert kwargs["max_output_tokens"] == 320
    serialized = json.dumps(kwargs["input"], default=str)
    assert len(serialized) < 9000


def test_tool_output_serialization_is_hard_bounded():
    payload = {"rows": [{"text": "z" * 5000, "value": i} for i in range(50)]}
    encoded = _bounded_json(payload)
    assert len(encoded) <= 6600
    json.loads(encoded)


if __name__ == "__main__":
    test_agent_runs_bounded_function_call_loop_with_grounded_output()
    test_quantitative_grounding_rejects_unreturned_statistic()
    test_researcher_context_excludes_raw_table_fields()
    test_rate_limit_is_presented_as_temporary_shared_capacity()
    test_413_request_size_error_is_friendly_and_provider_details_are_hidden()
    test_history_memory_and_output_budget_are_bounded_before_provider_call()
    test_tool_output_serialization_is_hard_bounded()
    print("RESEARCH AGENT TESTS OK")
