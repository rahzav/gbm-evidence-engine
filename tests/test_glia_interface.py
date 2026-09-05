from pathlib import Path

from glia_interface import _normalize_memory, _normalize_messages, _quick_actions


def test_memory_is_bounded_and_normalized():
    memory = _normalize_memory(
        {
            "investigated_genes": ["egfr", "pten"],
            "visited_workflows": ["Gene Analysis"],
            "recent_questions": ["q"] * 30,
            "recent_quotes": ["x"] * 20,
            "interaction_count": "4",
        }
    )
    assert memory["investigated_genes"] == ["EGFR", "PTEN"]
    assert memory["interaction_count"] == 4
    assert len(memory["recent_questions"]) <= 12
    assert len(memory["recent_quotes"]) <= 8


def test_messages_keep_only_conversation_fields():
    messages = _normalize_messages(
        [
            {"role": "user", "content": "Why?", "quote": "selected finding", "section": "Key Findings"},
            {
                "role": "assistant",
                "content": "Because.",
                "references": [{"token": "AN:GENE:EGFR"}],
                "grounding_ok": True,
                "unexpected": "drop me",
            },
        ]
    )
    assert messages[0]["quote"] == "selected finding"
    assert messages[0]["section"] == "Key Findings"
    assert "unexpected" not in messages[1]


def test_quick_actions_are_workflow_specific():
    assert "Challenge this target pair" in _quick_actions("Target Pair Analysis")
    assert "Interpret the highest-priority signals" in _quick_actions("Researcher Data")


def test_component_contains_required_integrated_interactions():
    source = Path("glia_interface.py").read_text(encoding="utf-8")
    for required in (
        "Ask Glia",
        "mouseup",
        "localStorage",
        "setTriggerValue(\"prompt\"",
        "glia-panel-open",
        "Research memory",
        "selectionTouchesIgnoredArea",
        "syncWorkspaceLayout",
        "Memory on · carries across visits",
        "background:var(--st-text-color, #111); color:var(--st-background-color, #fff)",
    ):
        assert required in source, required


def test_main_header_is_excluded_from_ask_glia_selection():
    source = Path("app_ui.py").read_text(encoding="utf-8")
    assert source.count('data-glia-ignore-selection="true"') >= 2


if __name__ == "__main__":
    test_memory_is_bounded_and_normalized()
    test_messages_keep_only_conversation_fields()
    test_quick_actions_are_workflow_specific()
    test_component_contains_required_integrated_interactions()
    test_main_header_is_excluded_from_ask_glia_selection()
    print("GLIA INTERFACE TESTS OK")
