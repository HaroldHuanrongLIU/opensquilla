"""Runtime-aware turn contracts for budgets and required artifacts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class RunProfile(StrEnum):
    INTERACTIVE = "interactive"
    AUTOMATION = "automation"
    BENCHMARK = "benchmark"
    CHANNEL = "channel"


class EnforcementMode(StrEnum):
    SOFT = "soft"
    HARD = "hard"


NETWORK_SEARCH_TOOLS: frozenset[str] = frozenset({"web_search"})
NETWORK_FETCH_TOOLS: frozenset[str] = frozenset({"web_fetch", "http_request"})
WEB_FETCH_MIN_MAX_CHARS = 100


@dataclass(frozen=True)
class ArtifactRequirement:
    extensions: tuple[str, ...]
    min_count: int = 1

    def __post_init__(self) -> None:
        normalized = tuple(_normalize_extension(ext) for ext in self.extensions if ext)
        object.__setattr__(self, "extensions", normalized)
        object.__setattr__(self, "min_count", max(1, int(self.min_count)))


@dataclass(frozen=True)
class RunContract:
    run_profile: RunProfile = RunProfile.INTERACTIVE
    enforcement_mode: EnforcementMode = EnforcementMode.SOFT
    network_search_calls: int | None = 8
    network_fetch_calls: int | None = 20
    network_text_chars: int | None = 300_000
    network_per_fetch_chars: int | None = 20_000
    required_artifacts: tuple[ArtifactRequirement, ...] = ()
    max_iterations_cap: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_profile": self.run_profile.value,
            "enforcement_mode": self.enforcement_mode.value,
            "network_search_calls": self.network_search_calls,
            "network_fetch_calls": self.network_fetch_calls,
            "network_text_chars": self.network_text_chars,
            "network_per_fetch_chars": self.network_per_fetch_chars,
            "required_artifacts": [
                {"extensions": list(req.extensions), "min_count": req.min_count}
                for req in self.required_artifacts
            ],
            "max_iterations_cap": self.max_iterations_cap,
        }


@dataclass(frozen=True)
class BudgetWarning:
    code: str
    tool: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "tool": self.tool,
            "message": self.message,
            "metadata": dict(self.metadata),
        }


class BudgetExceededError(Exception):
    """Raised when a hard run contract budget rejects a tool call."""

    user_message = "The run contract budget for this turn is exhausted."

    def __init__(self, tool_name: str, message: str) -> None:
        super().__init__(message)
        self.tool_name = tool_name
        self.user_message = message


BudgetExceeded = BudgetExceededError

_BUDGET_STATE_REGISTRY: dict[str, RunBudgetState] = {}


@dataclass(frozen=True)
class ToolBudgetReservation:
    tool_name: str
    arguments: dict[str, Any]
    fetch_text_reserved: int = 0
    counted_as_fetch: bool = False


@dataclass
class RunBudgetState:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    search_calls_used: int = 0
    fetch_calls_used: int = 0
    network_text_chars_used: int = 0
    network_text_chars_reserved: int = 0
    warnings: list[BudgetWarning] = field(default_factory=list)

    async def reserve_tool_call(
        self,
        contract: RunContract,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolBudgetReservation:
        args = dict(arguments)
        if tool_name not in NETWORK_SEARCH_TOOLS and tool_name not in NETWORK_FETCH_TOOLS:
            return ToolBudgetReservation(tool_name=tool_name, arguments=args)

        async with self.lock:
            if tool_name in NETWORK_SEARCH_TOOLS:
                self._reserve_call(
                    contract,
                    tool_name,
                    used=self.search_calls_used,
                    limit=contract.network_search_calls,
                    counter_name="search_calls_used",
                )
                return ToolBudgetReservation(tool_name=tool_name, arguments=args)

            self._check_call_budget(
                contract,
                tool_name,
                used=self.fetch_calls_used,
                limit=contract.network_fetch_calls,
            )
            reserved = self._apply_fetch_char_cap(contract, tool_name, args)
            self.fetch_calls_used += 1
            return ToolBudgetReservation(
                tool_name=tool_name,
                arguments=args,
                fetch_text_reserved=reserved,
                counted_as_fetch=True,
            )

    async def commit_tool_result(
        self,
        contract: RunContract,
        reservation: ToolBudgetReservation,
        content: str,
    ) -> None:
        if not reservation.counted_as_fetch:
            return
        async with self.lock:
            if reservation.fetch_text_reserved:
                self.network_text_chars_reserved = max(
                    0,
                    self.network_text_chars_reserved - reservation.fetch_text_reserved,
                )
            text_chars = len(content)
            self.network_text_chars_used += text_chars
            limit = contract.network_text_chars
            if limit is not None and self.network_text_chars_used > limit:
                message = (
                    "Network text returned by this turn exceeded the run contract "
                    f"budget ({self.network_text_chars_used}>{limit})."
                )
                if contract.enforcement_mode is EnforcementMode.HARD:
                    raise BudgetExceeded(reservation.tool_name, message)
                self._warn(
                    "network_text_budget_exceeded",
                    reservation.tool_name,
                    message,
                    {"used": self.network_text_chars_used, "limit": limit},
                )

    async def abort_tool_result(self, reservation: ToolBudgetReservation) -> None:
        if not reservation.counted_as_fetch or not reservation.fetch_text_reserved:
            return
        async with self.lock:
            self.network_text_chars_reserved = max(
                0,
                self.network_text_chars_reserved - reservation.fetch_text_reserved,
            )

    def _reserve_call(
        self,
        contract: RunContract,
        tool_name: str,
        *,
        used: int,
        limit: int | None,
        counter_name: str,
    ) -> None:
        self._check_call_budget(contract, tool_name, used=used, limit=limit)
        setattr(self, counter_name, used + 1)

    def _check_call_budget(
        self,
        contract: RunContract,
        tool_name: str,
        *,
        used: int,
        limit: int | None,
    ) -> None:
        if limit is not None and used >= limit:
            message = f"Tool '{tool_name}' exceeded the run contract call budget ({limit})."
            if contract.enforcement_mode is EnforcementMode.HARD:
                raise BudgetExceeded(tool_name, message)
            self._warn(
                "network_call_budget_exceeded",
                tool_name,
                message,
                {"used": used, "limit": limit},
            )

    def _apply_fetch_char_cap(
        self,
        contract: RunContract,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> int:
        per_call = contract.network_per_fetch_chars
        total = contract.network_text_chars
        cap = per_call
        if total is not None:
            remaining = total - self.network_text_chars_used - self.network_text_chars_reserved
            if remaining <= 0:
                message = (
                    f"Tool '{tool_name}' exceeded the run contract network text budget "
                    f"({total})."
                )
                if contract.enforcement_mode is EnforcementMode.HARD:
                    raise BudgetExceeded(tool_name, message)
                self._warn(
                    "network_text_budget_exceeded",
                    tool_name,
                    message,
                    {"used": self.network_text_chars_used, "limit": total},
                )
                remaining = 0
            cap = remaining if cap is None else min(cap, remaining)
        if cap is None:
            return 0
        cap = max(0, int(cap))
        if tool_name == "web_fetch":
            if cap < WEB_FETCH_MIN_MAX_CHARS:
                message = (
                    "web_fetch cannot enforce a run contract character cap below "
                    f"{WEB_FETCH_MIN_MAX_CHARS}."
                )
                if contract.enforcement_mode is EnforcementMode.HARD:
                    raise BudgetExceeded(tool_name, message)
                self._warn(
                    "network_max_chars_cap_unenforceable",
                    tool_name,
                    message,
                    {"requested_cap": cap, "minimum": WEB_FETCH_MIN_MAX_CHARS},
                )
                cap = WEB_FETCH_MIN_MAX_CHARS
            requested = arguments.get("max_chars")
            try:
                requested_int = int(requested) if requested is not None else None
            except (TypeError, ValueError):
                requested_int = None
            if requested_int is None or requested_int > cap:
                arguments["max_chars"] = cap
                self._warn(
                    "network_max_chars_clamped",
                    tool_name,
                    f"web_fetch max_chars was clamped to {cap} by the run contract.",
                    {"requested": requested_int, "clamped_to": cap},
                )
        self.network_text_chars_reserved += cap
        return cap

    def _warn(
        self,
        code: str,
        tool_name: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.warnings.append(
            BudgetWarning(
                code=code,
                tool=tool_name,
                message=message,
                metadata=metadata or {},
            )
        )

    def usage_dict(self) -> dict[str, Any]:
        return {
            "search_calls_used": self.search_calls_used,
            "fetch_calls_used": self.fetch_calls_used,
            "network_text_chars_used": self.network_text_chars_used,
            "warnings": [warning.as_dict() for warning in self.warnings],
        }


def register_budget_state(state: RunBudgetState) -> str:
    key = uuid4().hex
    _BUDGET_STATE_REGISTRY[key] = state
    return key


def get_registered_budget_state(key: object) -> RunBudgetState | None:
    if not isinstance(key, str) or not key:
        return None
    return _BUDGET_STATE_REGISTRY.get(key)


@dataclass(frozen=True)
class ArtifactValidationResult:
    ok: bool
    missing: list[dict[str, Any]]


def resolve_run_contract(
    *,
    caller_kind: Any,
    interaction_mode: Any,
    channel_kind: str | None = None,
    run_profile: str | RunProfile | None = None,
    required_artifacts: tuple[ArtifactRequirement, ...] | None = None,
) -> RunContract:
    profile = _coerce_profile(run_profile) if run_profile is not None else None
    if profile is None:
        profile = _default_profile(
            caller_kind=caller_kind,
            interaction_mode=interaction_mode,
            channel_kind=channel_kind,
        )
    contract = _profile_contract(profile)
    if required_artifacts:
        contract = RunContract(
            **{
                **contract.__dict__,
                "required_artifacts": tuple(required_artifacts),
            }
        )
    return contract


def run_contract_from_dict(payload: dict[str, Any]) -> RunContract:
    requirements = tuple(
        ArtifactRequirement(
            extensions=tuple(item.get("extensions") or ()),
            min_count=int(item.get("min_count") or item.get("minCount") or 1),
        )
        for item in payload.get("required_artifacts", [])
        if isinstance(item, dict)
    )
    return RunContract(
        run_profile=_coerce_profile(payload.get("run_profile") or RunProfile.INTERACTIVE),
        enforcement_mode=EnforcementMode(str(payload.get("enforcement_mode") or "soft")),
        network_search_calls=_optional_non_negative_int(payload.get("network_search_calls")),
        network_fetch_calls=_optional_non_negative_int(payload.get("network_fetch_calls")),
        network_text_chars=_optional_non_negative_int(payload.get("network_text_chars")),
        network_per_fetch_chars=_optional_non_negative_int(
            payload.get("network_per_fetch_chars")
        ),
        required_artifacts=requirements,
        max_iterations_cap=_optional_non_negative_int(payload.get("max_iterations_cap")),
    )


def apply_run_contract_overrides(
    contract: RunContract,
    *,
    network_search_calls: int | None = None,
    network_fetch_calls: int | None = None,
    network_text_chars: int | None = None,
    network_per_fetch_chars: int | None = None,
) -> RunContract:
    return RunContract(
        run_profile=contract.run_profile,
        enforcement_mode=contract.enforcement_mode,
        network_search_calls=(
            contract.network_search_calls
            if network_search_calls is None
            else _non_negative_int("network_search_calls", network_search_calls)
        ),
        network_fetch_calls=(
            contract.network_fetch_calls
            if network_fetch_calls is None
            else _non_negative_int("network_fetch_calls", network_fetch_calls)
        ),
        network_text_chars=(
            contract.network_text_chars
            if network_text_chars is None
            else _non_negative_int("network_text_chars", network_text_chars)
        ),
        network_per_fetch_chars=(
            contract.network_per_fetch_chars
            if network_per_fetch_chars is None
            else _non_negative_int("network_per_fetch_chars", network_per_fetch_chars)
        ),
        required_artifacts=contract.required_artifacts,
        max_iterations_cap=contract.max_iterations_cap,
    )


def constrain_run_contract(base: RunContract, requested: RunContract) -> RunContract:
    hard_requested = requested.enforcement_mode is EnforcementMode.HARD
    return RunContract(
        run_profile=requested.run_profile if hard_requested else base.run_profile,
        enforcement_mode=(
            EnforcementMode.HARD
            if base.enforcement_mode is EnforcementMode.HARD
            or requested.enforcement_mode is EnforcementMode.HARD
            else EnforcementMode.SOFT
        ),
        network_search_calls=_min_budget(base.network_search_calls, requested.network_search_calls),
        network_fetch_calls=_min_budget(base.network_fetch_calls, requested.network_fetch_calls),
        network_text_chars=_min_budget(base.network_text_chars, requested.network_text_chars),
        network_per_fetch_chars=_min_budget(
            base.network_per_fetch_chars,
            requested.network_per_fetch_chars,
        ),
        required_artifacts=base.required_artifacts + requested.required_artifacts,
        max_iterations_cap=_min_budget(base.max_iterations_cap, requested.max_iterations_cap),
    )


def validate_required_artifacts(
    requirements: list[ArtifactRequirement] | tuple[ArtifactRequirement, ...],
    artifacts: list[dict[str, Any]],
) -> ArtifactValidationResult:
    missing: list[dict[str, Any]] = []
    for requirement in requirements:
        unique: set[str] = set()
        for artifact in artifacts:
            name = str(artifact.get("name") or "")
            if not any(name.lower().endswith(ext) for ext in requirement.extensions):
                continue
            digest = str(artifact.get("sha256") or artifact.get("id") or name)
            unique.add(digest)
        if len(unique) < requirement.min_count:
            missing.append(
                {
                    "extensions": list(requirement.extensions),
                    "min_count": requirement.min_count,
                    "found": len(unique),
                }
            )
    return ArtifactValidationResult(ok=not missing, missing=missing)


def artifact_missing_message(missing: list[dict[str, Any]]) -> str:
    parts = []
    for item in missing:
        extensions = ", ".join(item.get("extensions") or [])
        parts.append(
            f"{extensions or 'artifact'}: required {item.get('min_count')}, "
            f"found {item.get('found')}"
        )
    return "Required artifact was not published: " + "; ".join(parts)


def _default_profile(
    *,
    caller_kind: Any,
    interaction_mode: Any,
    channel_kind: str | None,
) -> RunProfile:
    caller = _enum_label(caller_kind)
    interaction = _enum_label(interaction_mode)
    if caller == "channel" and _is_external_channel(channel_kind):
        return RunProfile.CHANNEL
    if caller in {"cron", "subagent"}:
        return RunProfile.AUTOMATION
    if interaction == "unattended":
        return RunProfile.AUTOMATION
    return RunProfile.INTERACTIVE


def _is_external_channel(channel_kind: str | None) -> bool:
    normalized = (channel_kind or "").strip().lower()
    return bool(normalized) and normalized not in {"web", "webchat", "cli", "subagent"}


def _profile_contract(profile: RunProfile) -> RunContract:
    match profile:
        case RunProfile.INTERACTIVE:
            return RunContract(
                run_profile=profile,
                enforcement_mode=EnforcementMode.SOFT,
                network_search_calls=8,
                network_fetch_calls=20,
                network_text_chars=300_000,
                network_per_fetch_chars=20_000,
            )
        case RunProfile.AUTOMATION:
            return RunContract(
                run_profile=profile,
                enforcement_mode=EnforcementMode.HARD,
                network_search_calls=4,
                network_fetch_calls=12,
                network_text_chars=120_000,
                network_per_fetch_chars=8_000,
            )
        case RunProfile.BENCHMARK:
            return RunContract(
                run_profile=profile,
                enforcement_mode=EnforcementMode.HARD,
                network_search_calls=3,
                network_fetch_calls=10,
                network_text_chars=80_000,
                network_per_fetch_chars=6_000,
                max_iterations_cap=30,
            )
        case RunProfile.CHANNEL:
            return RunContract(
                run_profile=profile,
                enforcement_mode=EnforcementMode.HARD,
                network_search_calls=3,
                network_fetch_calls=8,
                network_text_chars=64_000,
                network_per_fetch_chars=6_000,
            )


def _coerce_profile(value: str | RunProfile) -> RunProfile:
    if isinstance(value, RunProfile):
        return value
    return RunProfile(str(value).strip().lower())


def _normalize_extension(value: str) -> str:
    stripped = value.strip().lower()
    return stripped if stripped.startswith(".") else f".{stripped}"


def _enum_label(value: Any) -> str:
    return str(getattr(value, "value", value) or "").strip().lower()


def _non_negative_int(field_name: str, value: int) -> int:
    normalized = int(value)
    if normalized < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return normalized


def _optional_non_negative_int(value: Any) -> int | None:
    if value is None:
        return None
    return _non_negative_int("run_contract value", int(value))


def _min_budget(base: int | None, requested: int | None) -> int | None:
    if base is None:
        return requested
    if requested is None:
        return base
    return min(base, requested)
