from __future__ import annotations

from opensquilla.engine.tool_truncation import truncate_result


def test_truncate_result_respects_final_character_budget_with_marker() -> None:
    text = "0123456789" * 40

    truncated = truncate_result(text, context_window_tokens=80, max_share=0.25)

    assert truncated != text
    assert "[...truncated" in truncated
    assert len(truncated) <= 80


def test_truncate_result_handles_marker_larger_than_tiny_budget() -> None:
    text = "abcdefghijklmnopqrstuvwxyz" * 4

    truncated = truncate_result(text, context_window_tokens=4, max_share=0.25)

    assert truncated != text
    assert len(truncated) <= 4


def test_truncate_result_uses_character_budget_as_hard_ceiling() -> None:
    text = "abcdefg"

    truncated = truncate_result(text, context_window_tokens=4, max_share=0.25)

    assert truncated == "abcd"
