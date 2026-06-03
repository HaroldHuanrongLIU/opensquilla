from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from opensquilla.gateway import rpc_skills
from opensquilla.gateway.rpc import RpcContext
from opensquilla.skills.hub.installer import InstallResult
from opensquilla.skills.loader import SkillLoader
from opensquilla.skills.types import SkillLayer, SkillPlatformMeta, SkillRequires, SkillSpec


def test_rpc_skill_install_uses_loader_managed_dir_and_list_sees_skill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        managed_dir = tmp_path / "managed"
        loader = SkillLoader(
            managed_dir=managed_dir,
            snapshot_path=tmp_path / "snapshot.json",
        )
        ctx = RpcContext(conn_id="test", skill_loader=loader)
        captured: dict[str, Path | None] = {}

        class FakeInstaller:
            def __init__(self, managed_dir: Path) -> None:
                self.managed_dir = managed_dir

            async def install(
                self,
                identifier: str,
                source_id: str,
                force: bool = False,
            ) -> InstallResult:
                skill_dir = self.managed_dir / identifier
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(
                    "---\n"
                    f"name: {identifier}\n"
                    "description: Installed from chat\n"
                    "---\n"
                    "Installed body.\n",
                    encoding="utf-8",
                )
                return InstallResult(
                    success=True,
                    name=identifier,
                    message="installed",
                    path=str(skill_dir),
                )

        def fake_builder(*, managed_dir: Path | None = None) -> FakeInstaller:
            assert managed_dir is not None
            captured["managed_dir"] = managed_dir
            return FakeInstaller(managed_dir)

        monkeypatch.setattr(rpc_skills, "build_default_skill_installer", fake_builder)
        assert await rpc_skills._handle_skills_list(None, ctx) == {"skills": []}
        assert loader._cached is not None

        installed = await rpc_skills._handle_skills_install(
            {"identifier": "plotter", "source": "clawhub"},
            ctx,
        )
        listed = await rpc_skills._handle_skills_list(None, ctx)

        assert captured["managed_dir"] == managed_dir
        assert installed["success"] is True
        assert Path(installed["path"]).name == "plotter"
        row = next(skill for skill in listed["skills"] if skill["name"] == "plotter")
        assert row["layer"] == "managed"
        assert row["description"] == "Installed from chat"

    asyncio.run(run())


def test_skill_payload_rolls_up_meta_subskill_requirements() -> None:
    python_skill = SkillSpec(
        name="docx",
        description="Docx export",
        layer=SkillLayer.BUNDLED,
        always=False,
        triggers=[],
        content="",
        metadata=SkillPlatformMeta(requires=SkillRequires(any_bins=["python", "python3"])),
    )
    ffmpeg_skill = SkillSpec(
        name="video-merger",
        description="Video merge",
        layer=SkillLayer.BUNDLED,
        always=False,
        triggers=[],
        content="",
        metadata=SkillPlatformMeta(requires=SkillRequires(bins=["ffmpeg", "ffprobe"])),
    )
    meta_skill = SkillSpec(
        name="meta-demo",
        description="Meta demo",
        layer=SkillLayer.BUNDLED,
        always=False,
        triggers=[],
        content="",
        kind="meta",
        composition_raw={
            "steps": [
                {"id": "export", "kind": "skill_exec", "skill": "docx"},
                {"id": "merge", "kind": "skill_exec", "skill": "video-merger"},
            ]
        },
    )

    ctx = rpc_skills.EligibilityContext.auto()
    ctx.has_bin_cache.update(
        {"python": True, "python3": True, "ffmpeg": False, "ffprobe": False}
    )
    skill_index = {s.name: s for s in (meta_skill, python_skill, ffmpeg_skill)}
    payload = rpc_skills._skill_to_dict(
        meta_skill,
        rpc_skills.diagnose_eligibility(meta_skill, ctx),
        ctx.os_name,
        skill_index=skill_index,
        eligibility_ctx=ctx,
    )

    assert payload["requirements"]["summary"] == "needs_setup"
    assert payload["requirements"]["items"] == [
        {
            "name": "docx",
            "source": "sub_skill",
            "status": "ready",
            "requires_bins": [],
            "requires_any_bins": ["python", "python3"],
            "requires_env": [],
            "missing_bins": [],
            "missing_env": [],
        },
        {
            "name": "video-merger",
            "source": "sub_skill",
            "status": "needs_setup",
            "requires_bins": ["ffmpeg", "ffprobe"],
            "requires_any_bins": [],
            "requires_env": [],
            "missing_bins": ["ffmpeg", "ffprobe"],
            "missing_env": [],
        },
    ]


def test_meta_paper_write_declares_pdf_compile_binaries() -> None:
    bundled = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "opensquilla"
        / "skills"
        / "bundled"
    )
    loader = SkillLoader(bundled_dir=bundled)
    skills = loader.load_all()
    skill_index = {skill.name: skill for skill in skills}
    ctx = rpc_skills.EligibilityContext.auto()
    spec = skill_index["meta-paper-write"]
    payload = rpc_skills._skill_to_dict(
        spec,
        rpc_skills.diagnose_eligibility(spec, ctx),
        ctx.os_name,
        skill_index=skill_index,
        eligibility_ctx=ctx,
    )

    own_requirements = next(
        item for item in payload["requirements"]["items"] if item["source"] == "self"
    )
    assert own_requirements["requires_bins"] == ["xelatex", "bibtex"]
