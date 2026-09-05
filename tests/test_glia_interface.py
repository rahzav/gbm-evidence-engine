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
    assert "What is the strongest reason this pair could fail?" in _quick_actions("Target Pair Analysis")
    assert "Which signal is most worth validating?" in _quick_actions("Researcher Data")


def test_glia_component_has_integrated_high_contrast_controls_and_force_open():
    source = Path("glia_interface.py").read_text(encoding="utf-8")
    for required in (
        "Ask Glia",
        "gliaGlyph",
        "force_open_nonce",
        "selectionTouchesIgnoredArea",
        "syncWorkspaceLayout",
        "localStorage",
        "glia-panel-open",
        "glia-fullscreen",
        "glia-expand",
        "Research memory",
        "<span>Ask Glia</span>",
    ):
        assert required in source, required


def test_main_header_is_excluded_from_ask_glia_selection():
    source = Path("ui_walkthroughs.py").read_text(encoding="utf-8")
    assert 'class="glia-product-bar" data-glia-ignore-selection="true"' in source


def test_single_condensed_product_tour_replaces_per_tab_walkthroughs():
    source = Path("ui_walkthroughs.py").read_text(encoding="utf-8")
    assert "def show_tool_walkthrough" in source
    assert "Gene Analysis" in source
    assert "Target Pair Analysis" in source
    assert "Researcher Data" in source
    assert "Gene Set Comparison" in source
    assert "Methods & Data Sources" in source
    assert "glia_force_open_nonce" in source
    assert '"Open Glia"' in source
    assert 'open_tool_tour_info' in source
    assert 'class="glia-wordmark">Glia' in source
    assert 'Evidence-grounded research intelligence for glioblastoma.' in source
    assert "Don't show this walkthrough again" in source
    for obsolete in (
        "def show_gene_walkthrough",
        "def show_pair_walkthrough",
        "def show_researcher_walkthrough",
        "def show_comparison_walkthrough",
        "on_workflow_tab_change",
    ):
        assert obsolete not in source


if __name__ == "__main__":
    test_memory_is_bounded_and_normalized()
    test_messages_keep_only_conversation_fields()
    test_quick_actions_are_workflow_specific()
    test_glia_component_has_integrated_high_contrast_controls_and_force_open()
    test_main_header_is_excluded_from_ask_glia_selection()
    test_single_condensed_product_tour_replaces_per_tab_walkthroughs()
    print("GLIA INTERFACE TESTS OK")
