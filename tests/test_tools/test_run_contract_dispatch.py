from __future__ import annotations

import json

import pytest

from opensquilla.engine.types import ToolCall
from opensquilla.run_contract import EnforcementMode, RunBudgetState, RunContract, RunProfile
from opensquilla.tools.dispatch import build_tool_handler
from opensquilla.tools.registry import ToolRegistry
from opensquilla.tools.types import ToolContext, ToolSpec, current_tool_context


@pytest.mark.asyncio
async def test_dispatch_clamps_web_fetch_max_chars_and_records_warning() -> None:
    observed: dict[str, int | None] = {}
    registry = ToolRegistry()

    async def web_fetch(max_chars: int | None = None) -> str:
        observed["max_chars"] = max_chars
        return "x" * int(max_chars or 0)

    registry.register(
        ToolSpec(
            name="web_fetch",
            description="Fetch",
            parameters={"type": "object", "properties": {"max_chars": {"type": "integer"}}},
        ),
        web_fetch,
    )
    ctx = ToolContext(
        run_contract=RunContract(
            run_profile=RunProfile.BENCHMARK,
            enforcement_mode=EnforcementMode.HARD,
            network_fetch_calls=2,
            network_text_chars=10_000,
            network_per_fetch_chars=800,
        ),
        run_budget_state=RunBudgetState(),
    )
    handler = build_tool_handler(registry)
    token = current_tool_context.set(ctx)
    try:
        result = await handler(
            ToolCall(
                tool_use_id="fetch-1",
                tool_name="web_fetch",
                arguments={"max_chars": 1000},
            )
        )
    finally:
        current_tool_context.reset(token)

    assert result.is_error is False
    assert observed["max_chars"] == 800
    assert result.content == "x" * 800
    assert ctx.run_budget_state.warnings
    assert ctx.run_budget_state.fetch_calls_used == 1
    assert ctx.run_budget_state.network_text_chars_used == 800


@pytest.mark.asyncio
async def test_dispatch_blocks_network_budget_excess_as_non_retryable_error() -> None:
    registry = ToolRegistry()

    async def http_request() -> str:
        return "response"

    registry.register(
        ToolSpec(name="http_request", description="HTTP", parameters={}),
        http_request,
    )
    ctx = ToolContext(
        is_owner=True,
        run_contract=RunContract(
            run_profile=RunProfile.BENCHMARK,
            enforcement_mode=EnforcementMode.HARD,
            network_fetch_calls=1,
            network_text_chars=100,
            network_per_fetch_chars=50,
        ),
        run_budget_state=RunBudgetState(),
    )
    handler = build_tool_handler(registry)
    token = current_tool_context.set(ctx)
    try:
        first = await handler(
            ToolCall(tool_use_id="http-1", tool_name="http_request", arguments={})
        )
        second = await handler(
            ToolCall(tool_use_id="http-2", tool_name="http_request", arguments={})
        )
    finally:
        current_tool_context.reset(token)

    assert first.is_error is False
    assert second.is_error is True
    payload = json.loads(second.content)
    assert payload["error_class"] == "BudgetExceeded"
    assert payload["retry_allowed"] is False
    assert ctx.run_budget_state.fetch_calls_used == 1


@pytest.mark.asyncio
async def test_dispatch_blocks_hard_http_request_text_over_budget() -> None:
    registry = ToolRegistry()

    async def http_request() -> str:
        return "x" * 200

    registry.register(
        ToolSpec(name="http_request", description="HTTP", parameters={}),
        http_request,
    )
    ctx = ToolContext(
        is_owner=True,
        run_contract=RunContract(
            run_profile=RunProfile.BENCHMARK,
            enforcement_mode=EnforcementMode.HARD,
            network_fetch_calls=1,
            network_text_chars=100,
            network_per_fetch_chars=100,
        ),
        run_budget_state=RunBudgetState(),
    )
    handler = build_tool_handler(registry)
    token = current_tool_context.set(ctx)
    try:
        result = await handler(
            ToolCall(tool_use_id="http-1", tool_name="http_request", arguments={})
        )
    finally:
        current_tool_context.reset(token)

    assert result.is_error is True
    payload = json.loads(result.content)
    assert payload["error_class"] == "BudgetExceeded"
    assert payload["retry_allowed"] is False
    assert ctx.run_budget_state.network_text_chars_reserved == 0
    assert ctx.run_budget_state.network_text_chars_used == 200


@pytest.mark.asyncio
async def test_dispatch_releases_reserved_text_budget_when_fetch_handler_fails() -> None:
    registry = ToolRegistry()

    async def web_fetch(max_chars: int | None = None) -> str:
        raise RuntimeError("transient fetch failure")

    registry.register(
        ToolSpec(
            name="web_fetch",
            description="Fetch",
            parameters={"type": "object", "properties": {"max_chars": {"type": "integer"}}},
        ),
        web_fetch,
    )
    ctx = ToolContext(
        run_contract=RunContract(
            run_profile=RunProfile.BENCHMARK,
            enforcement_mode=EnforcementMode.HARD,
            network_fetch_calls=2,
            network_text_chars=1000,
            network_per_fetch_chars=500,
        ),
        run_budget_state=RunBudgetState(),
    )
    handler = build_tool_handler(registry)
    token = current_tool_context.set(ctx)
    try:
        result = await handler(
            ToolCall(
                tool_use_id="fetch-1",
                tool_name="web_fetch",
                arguments={"max_chars": 1000},
            )
        )
    finally:
        current_tool_context.reset(token)

    assert result.is_error is True
    assert ctx.run_budget_state.network_text_chars_reserved == 0
    assert ctx.run_budget_state.network_text_chars_used == 0
