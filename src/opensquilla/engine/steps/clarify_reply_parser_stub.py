"""STUB: deterministic parser for clarify reply text.

PR4 of docs/superpowers/specs/2026-05-26-meta-skill-user-input-design.md
replaces this stub with the real implementation in
``opensquilla.skills.meta.clarify_text``. Until then, this stub returns
an error for every input — enough to exercise the meta_resolution
branches that handle "errors" (re-prompt, 3-strike cap) but not the
"success" path. Resume is tested via the programmatic
``MetaOrchestrator.resume`` call in tests/test_skills/test_meta_resume.py.
"""

from __future__ import annotations

from typing import Any


def parse_clarify_reply(
    message: str,
    schema: Any,
    *,
    surface: str,
) -> tuple[dict[str, Any], list[str]]:
    """Always returns ({}, ["parser not yet wired (PR4)"]).

    PR3 ships this stub so the meta_resolution awaiting branch can be
    wired and tested end-to-end without depending on the (yet-to-be-
    implemented) deterministic reply parser. PR4 will replace this
    module's implementation with the real `clarify_text` parser.
    """
    return {}, ["parser not yet wired (PR4 will replace this stub)"]
