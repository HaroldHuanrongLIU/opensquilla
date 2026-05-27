"""DAO tests for clarify state on MetaRunWriter (PR2)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from yoyo import get_backend, read_migrations

from opensquilla.persistence.meta_run_writer import (
    AwaitingPeek,
    MetaRunWriter,
)


@pytest.fixture
def writer(tmp_path: Path) -> MetaRunWriter:
    db = tmp_path / "test.sqlite"
    backend = get_backend(f"sqlite:///{db}")
    backend.apply_migrations(read_migrations("migrations"))
    conn = sqlite3.connect(db, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return MetaRunWriter(conn)


def _seed_awaiting(writer: MetaRunWriter, *, run_id: str, session_key: str,
                   step_id: str = "collect", since: float = 1700000000.0) -> None:
    schema_json = json.dumps({"mode": "form", "fields": []})
    with writer._lock:
        writer._conn.execute(
            "INSERT INTO meta_skill_runs "
            "(run_id, meta_skill_name, meta_skill_digest, plan_snapshot_json, "
            " triggered_by, session_key, status, started_at_ms, inputs_json, "
            " awaiting_step_id, awaiting_schema_json, awaiting_since, "
            " awaiting_filled_json, step_outputs_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, "tskill", "d", "{}", "soft_meta_invoke", session_key,
             "awaiting_user", 0, "{}", step_id, schema_json, since,
             "{}", "{}"),
        )
        writer._conn.commit()


def test_peek_awaiting_returns_none_for_unknown_session(writer):
    assert writer.peek_awaiting(session_id="nope") is None


def test_peek_awaiting_returns_record_for_matching_session(writer):
    _seed_awaiting(writer, run_id="r1", session_key="S1")
    peek = writer.peek_awaiting(session_id="S1")
    assert peek is not None
    assert isinstance(peek, AwaitingPeek)
    assert peek.run_id == "r1"
    assert peek.step_id == "collect"
    assert peek.awaiting_session_id == "S1"


def test_peek_awaiting_ignores_non_awaiting_status(writer):
    with writer._lock:
        writer._conn.execute(
            "INSERT INTO meta_skill_runs "
            "(run_id, meta_skill_name, meta_skill_digest, plan_snapshot_json, "
            " triggered_by, session_key, status, started_at_ms, inputs_json) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            ("r2", "tskill", "d", "{}", "soft_meta_invoke", "S2",
             "ok", 0, "{}"),
        )
        writer._conn.commit()
    assert writer.peek_awaiting(session_id="S2") is None
