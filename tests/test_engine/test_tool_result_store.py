from __future__ import annotations

import json
from pathlib import Path

import pytest

from opensquilla.engine.tool_result_store import ToolResultStore, ToolResultStoreBudgetError


def test_tool_result_store_preserves_metadata_for_repeated_content(tmp_path: Path) -> None:
    store = ToolResultStore(tmp_path)

    first = store.write(
        "same output",
        tool_use_id="tool-1",
        tool_name="fetch",
        session_id="session-1",
        session_key="agent:main:webchat:session-1",
        agent_id="main",
    )
    second = store.write(
        "same output",
        tool_use_id="tool-2",
        tool_name="execute_code",
        session_id="session-1",
        session_key="agent:main:webchat:session-1",
        agent_id="main",
    )

    assert first.handle != second.handle
    assert store.read(first.handle, session_id="session-1").tool_use_id == "tool-1"
    assert store.read(first.handle, session_id="session-1").tool_name == "fetch"
    assert store.read(second.handle, session_id="session-1").tool_use_id == "tool-2"
    assert store.read(second.handle, session_id="session-1").tool_name == "execute_code"


def test_tool_result_store_enforces_session_scoped_reads(tmp_path: Path) -> None:
    store = ToolResultStore(tmp_path)
    record = store.write(
        "private output",
        tool_use_id="tool-1",
        tool_name="fetch",
        session_id="session-1",
        session_key="agent:main:webchat:session-1",
        agent_id="main",
    )

    with pytest.raises(FileNotFoundError):
        store.read(record.handle, session_id="session-2")


def test_tool_result_store_rejects_single_result_over_budget(tmp_path: Path) -> None:
    store = ToolResultStore(tmp_path)

    with pytest.raises(ToolResultStoreBudgetError):
        store.write(
            "abcdef",
            tool_use_id="tool-1",
            tool_name="fetch",
            session_id="session-1",
            session_key="agent:main:webchat:session-1",
            agent_id="main",
            max_bytes=5,
        )

    assert not list(tmp_path.rglob("content.txt"))


def test_tool_result_store_prunes_oldest_records_for_disk_budget(tmp_path: Path) -> None:
    store = ToolResultStore(tmp_path)
    first = store.write(
        "a" * 40,
        tool_use_id="tool-1",
        tool_name="fetch",
        session_id="session-1",
        session_key="agent:main:webchat:session-1",
        agent_id="main",
        disk_budget_bytes=120,
    )
    second = store.write(
        "b" * 40,
        tool_use_id="tool-2",
        tool_name="fetch",
        session_id="session-1",
        session_key="agent:main:webchat:session-1",
        agent_id="main",
        disk_budget_bytes=120,
    )

    third = store.write(
        "c" * 40,
        tool_use_id="tool-3",
        tool_name="fetch",
        session_id="session-1",
        session_key="agent:main:webchat:session-1",
        agent_id="main",
        disk_budget_bytes=90,
    )

    with pytest.raises(FileNotFoundError):
        store.read(first.handle, session_id="session-1")
    assert store.read(second.handle, session_id="session-1").content == "b" * 40
    assert store.read(third.handle, session_id="session-1").content == "c" * 40


def test_tool_result_store_removes_expired_records_before_write(tmp_path: Path) -> None:
    store = ToolResultStore(tmp_path)
    expired = store.write(
        "old output",
        tool_use_id="tool-1",
        tool_name="fetch",
        session_id="session-1",
        session_key="agent:main:webchat:session-1",
        agent_id="main",
    )
    meta_path = next(
        path
        for path in tmp_path.rglob("meta.json")
        if json.loads(path.read_text(encoding="utf-8"))["handle"] == expired.handle
    )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["created_at"] = "2000-01-01T00:00:00Z"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    store.write(
        "new output",
        tool_use_id="tool-2",
        tool_name="fetch",
        session_id="session-1",
        session_key="agent:main:webchat:session-1",
        agent_id="main",
        retention_seconds=1,
    )

    with pytest.raises(FileNotFoundError):
        store.read(expired.handle, session_id="session-1")


def test_tool_result_store_rejects_tampered_material(tmp_path: Path) -> None:
    store = ToolResultStore(tmp_path)
    record = store.write(
        "trusted output",
        tool_use_id="tool-1",
        tool_name="fetch",
        session_id="session-1",
        session_key="agent:main:webchat:session-1",
        agent_id="main",
    )
    next(tmp_path.rglob("content.txt")).write_text("tampered", encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        store.read(record.handle, session_id="session-1")
