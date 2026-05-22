"""Tool result truncation — token-budget-aware, head+tail strategy."""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(0, len(text) // 4)


def truncate_result(
    text: str,
    context_window_tokens: int,
    max_share: float = 0.25,
) -> str:
    """Truncate tool result if it exceeds max_share of context window.

    Strategy: keep head 70% + tail 20% of budget, insert truncation marker.
    Returns original text if within budget.
    """
    budget_tokens = int(context_window_tokens * max_share)
    budget_chars = max(0, budget_tokens * 4)

    if budget_chars <= 0:
        return ""

    if budget_chars >= len(text):
        return text

    keep_chars = max(0, int(budget_chars * 0.90))
    while keep_chars >= 0:
        head_chars = int(keep_chars * 0.70)
        tail_chars = keep_chars - head_chars
        omitted = len(text) - head_chars - tail_chars
        marker = f"\n[...truncated {omitted} chars...]\n"
        if len(marker) > budget_chars:
            break
        tail = text[-tail_chars:] if tail_chars > 0 else ""
        truncated = text[:head_chars] + marker + tail
        if len(truncated) <= budget_chars:
            return truncated
        keep_chars -= 1

    return text[:budget_chars]
