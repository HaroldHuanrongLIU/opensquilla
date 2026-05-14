"""Invariants for pyproject.toml after the 0.1.0 release refactor.

The refactor moves real-used channel SDKs into base dependencies, deletes
dead extras (msteams / matrix), and turns the remaining channel extras
into empty backward-compat aliases. These tests assert those invariants
so the configuration cannot silently regress.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


@pytest.fixture(scope="module")
def project_table() -> dict:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return data["project"]


def _dep_names(specs: list[str]) -> set[str]:
    """Extract canonical (lowercased) package names from a list of PEP 508 specs."""

    names: set[str] = set()
    for spec in specs:
        head = spec.strip()
        for sep in ("[", " ", ";", "=", ">", "<", "~", "!"):
            head = head.split(sep, 1)[0]
        if head:
            names.add(head.lower())
    return names


def test_channel_sdks_in_base(project_table: dict) -> None:
    """Channel adapters that ``import`` a vendor SDK must keep that SDK in base."""

    base = _dep_names(project_table["dependencies"])
    required = {
        "lark-oapi",
        "python-telegram-bot",
        "dingtalk-stream",
        "qq-botpy",
        "cryptography",
    }
    missing = required - base
    assert not missing, f"channel SDKs missing from base deps: {sorted(missing)}"


def test_no_dead_extras(project_table: dict) -> None:
    """msteams / matrix extras have no real code consumer and must be removed."""

    extras = project_table.get("optional-dependencies", {})
    assert "msteams" not in extras, "msteams extra is dead — its declared SDK is never imported"
    assert "matrix" not in extras, "matrix extra is dead — code uses httpx, not matrix-nio"


def test_legacy_extras_are_empty(project_table: dict) -> None:
    """Channel extras that used to pull vendor SDKs must now be empty aliases."""

    extras = project_table.get("optional-dependencies", {})
    for name in ("feishu", "telegram", "dingtalk", "wecom", "qq"):
        assert name in extras, f"legacy alias {name} should still exist for compat"
        assert extras[name] == [], (
            f"legacy alias {name} should be an empty list (SDK is now in base)"
        )


def test_no_duplicate_ml_extra(project_table: dict) -> None:
    """``recommended`` and ``model-router`` historically overlapped — only one survives."""

    extras = project_table.get("optional-dependencies", {})
    has_recommended = "recommended" in extras
    has_model_router = "model-router" in extras
    assert has_recommended, "recommended extra must exist (router users opt in here)"
    assert not has_model_router, (
        "model-router extra duplicates recommended — collapse into one"
    )


def test_alpha_classifier_present(project_table: dict) -> None:
    """0.1.0 stays pre-stable — the classifier must reflect that."""

    classifiers = project_table.get("classifiers", [])
    assert "Development Status :: 3 - Alpha" in classifiers, (
        "Alpha classifier signals to PyPI/uv that this is pre-stable"
    )


def test_readme_points_at_user_facing_file(project_table: dict) -> None:
    """``readme`` must be the user-facing README, not the legacy portable view."""

    assert project_table["readme"] == "README.md", (
        "readme should point at the canonical README.md after the 0.1.0 refactor"
    )
