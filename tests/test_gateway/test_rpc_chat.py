from __future__ import annotations

from typing import Any

import pytest

from opensquilla.gateway.auth import Principal
from opensquilla.gateway.config import GatewayConfig
from opensquilla.gateway.rpc import RpcContext
from opensquilla.gateway.rpc_chat import _handle_chat_send


class _FakeChatSessionManager:
    async def get_or_create(self, **kwargs: Any) -> None:
        return None

    async def get_transcript(self, session_key: str) -> list:
        return []


@pytest.mark.asyncio
async def test_chat_send_forwards_run_contract_to_sessions_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_sessions_send(params: dict[str, Any], ctx: RpcContext) -> dict[str, Any]:
        captured.update(params)
        return {"status": "accepted", "key": params["key"]}

    monkeypatch.setattr(
        "opensquilla.gateway.rpc_sessions._handle_sessions_send",
        fake_sessions_send,
    )
    ctx = RpcContext(
        conn_id="test-conn",
        principal=Principal(
            role="operator",
            scopes=frozenset(["operator.admin"]),
            is_owner=True,
            authenticated=True,
        ),
        config=GatewayConfig(),
    )
    ctx.session_manager = _FakeChatSessionManager()

    result = await _handle_chat_send(
        {
            "message": "make a deck",
            "runContract": {
                "runProfile": "benchmark",
                "requiredArtifacts": [".pptx"],
            },
        },
        ctx,
    )

    assert result["status"] == "accepted"
    assert captured["runContract"] == {
        "runProfile": "benchmark",
        "requiredArtifacts": [".pptx"],
    }
    assert captured["_source"]["channel_kind"] == "webchat"
