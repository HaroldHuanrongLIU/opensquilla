from __future__ import annotations

import asyncio

import pytest

from opensquilla.run_contract import (
    ArtifactRequirement,
    BudgetExceeded,
    EnforcementMode,
    RunBudgetState,
    RunContract,
    RunProfile,
    apply_run_contract_overrides,
    constrain_run_contract,
    resolve_run_contract,
    validate_required_artifacts,
)
from opensquilla.tools.types import CallerKind, InteractionMode


def test_resolve_run_contract_keeps_webchat_interactive_not_channel() -> None:
    contract = resolve_run_contract(
        caller_kind=CallerKind.WEB,
        interaction_mode=InteractionMode.INTERACTIVE,
        channel_kind="webchat",
    )

    assert contract.run_profile is RunProfile.INTERACTIVE
    assert contract.enforcement_mode is EnforcementMode.SOFT


def test_resolve_run_contract_maps_external_channel_to_channel_profile() -> None:
    contract = resolve_run_contract(
        caller_kind=CallerKind.CHANNEL,
        interaction_mode=InteractionMode.UNATTENDED,
        channel_kind="feishu",
    )

    assert contract.run_profile is RunProfile.CHANNEL
    assert contract.enforcement_mode is EnforcementMode.HARD
    assert contract.network_fetch_calls == 8


@pytest.mark.asyncio
async def test_run_budget_state_reserves_network_calls_atomically() -> None:
    contract = RunContract(
        run_profile=RunProfile.BENCHMARK,
        enforcement_mode=EnforcementMode.HARD,
        network_fetch_calls=2,
        network_text_chars=1_000,
        network_per_fetch_chars=500,
    )
    state = RunBudgetState()

    async def reserve_one(index: int) -> str:
        try:
            reservation = await state.reserve_tool_call(
                contract,
                "web_fetch",
                {"max_chars": 1_000},
            )
            return f"ok:{index}:{reservation.arguments['max_chars']}"
        except BudgetExceeded:
            return f"blocked:{index}"

    results = await asyncio.gather(*(reserve_one(i) for i in range(5)))

    assert sum(item.startswith("ok:") for item in results) == 2
    assert sum(item.startswith("blocked:") for item in results) == 3


@pytest.mark.asyncio
async def test_run_budget_state_rejects_unenforceable_web_fetch_char_cap() -> None:
    contract = RunContract(
        run_profile=RunProfile.BENCHMARK,
        enforcement_mode=EnforcementMode.HARD,
        network_fetch_calls=1,
        network_text_chars=50,
        network_per_fetch_chars=50,
    )
    state = RunBudgetState()

    with pytest.raises(BudgetExceeded):
        await state.reserve_tool_call(contract, "web_fetch", {"max_chars": 1000})
    assert state.fetch_calls_used == 0
    assert state.network_text_chars_reserved == 0


def test_validate_required_artifacts_counts_unique_sha_matching_extension() -> None:
    requirement = ArtifactRequirement(extensions=(".pptx",), min_count=2)
    artifacts = [
        {"name": "deck.pptx", "sha256": "a" * 64},
        {"name": "deck-copy.pptx", "sha256": "a" * 64},
        {"name": "notes.txt", "sha256": "b" * 64},
        {"name": "second.pptx", "sha256": "c" * 64},
    ]

    result = validate_required_artifacts([requirement], artifacts)

    assert result.ok is True
    assert result.missing == []


def test_apply_run_contract_overrides_preserves_profile_and_sets_budget_values() -> None:
    contract = resolve_run_contract(
        caller_kind=CallerKind.CLI,
        interaction_mode=InteractionMode.UNATTENDED,
        run_profile="benchmark",
        required_artifacts=(ArtifactRequirement(extensions=(".pptx",)),),
    )

    updated = apply_run_contract_overrides(
        contract,
        network_search_calls=1,
        network_fetch_calls=2,
        network_text_chars=3456,
        network_per_fetch_chars=789,
    )

    assert updated.run_profile is RunProfile.BENCHMARK
    assert updated.enforcement_mode is EnforcementMode.HARD
    assert updated.required_artifacts == contract.required_artifacts
    assert updated.max_iterations_cap == 30
    assert updated.network_search_calls == 1
    assert updated.network_fetch_calls == 2
    assert updated.network_text_chars == 3456
    assert updated.network_per_fetch_chars == 789


def test_constrain_run_contract_keeps_server_hard_mode_and_lower_budgets() -> None:
    base = RunContract(
        run_profile=RunProfile.CHANNEL,
        enforcement_mode=EnforcementMode.HARD,
        network_search_calls=3,
        network_fetch_calls=8,
        network_text_chars=64_000,
        network_per_fetch_chars=6_000,
    )
    requested = RunContract(
        run_profile=RunProfile.INTERACTIVE,
        enforcement_mode=EnforcementMode.SOFT,
        network_search_calls=99,
        network_fetch_calls=99,
        network_text_chars=999_000,
        network_per_fetch_chars=99_000,
    )

    constrained = constrain_run_contract(base, requested)

    assert constrained.run_profile is RunProfile.CHANNEL
    assert constrained.enforcement_mode is EnforcementMode.HARD
    assert constrained.network_search_calls == 3
    assert constrained.network_fetch_calls == 8
    assert constrained.network_text_chars == 64_000
    assert constrained.network_per_fetch_chars == 6_000
