from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_install_scripts_force_refresh_local_uv_tool_package() -> None:
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert "'--force', '--reinstall-package', 'opensquilla'" in ps1
    assert "--force --reinstall-package opensquilla" in sh


def test_source_install_scripts_do_not_run_onboarding() -> None:
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "install.sh").read_text(encoding="utf-8")

    for script in (ps1, sh):
        assert "onboard --if-needed" not in script
        assert "opensquilla onboard" not in script


def test_windows_installer_stops_when_native_install_command_fails() -> None:
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert 'if ($LASTEXITCODE -ne 0) {' in ps1
    assert "install.ps1: install command failed with exit code $LASTEXITCODE." in ps1
    assert (
        "Close any running OpenSquilla gateway or shell using the existing "
        "tool environment, then retry."
        in ps1
    )
    assert "exit $LASTEXITCODE" in ps1


def test_install_script_banners_are_ascii_for_windows_terminals() -> None:
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "install.sh").read_text(encoding="utf-8")

    for script in (ps1, sh):
        assert "OpenSquilla installed via" in script
        assert "->" in script
        assert "----" in script
        assert "→" not in script
        assert "─" not in script
        assert "⚠" not in script


def test_install_scripts_support_optional_extras() -> None:
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "install.sh").read_text(encoding="utf-8")

    assert "OPENSQUILLA_INSTALL_EXTRAS" in ps1
    assert "[string[]]$Extras" in ps1
    assert "'feishu'" in ps1
    assert "OPENSQUILLA_INSTALL_EXTRAS" in sh
    assert "--extras" in sh
    assert "feishu telegram dingtalk wecom qq matrix matrix-e2e document-extras" in sh
    assert " msteams " not in sh


def test_windows_installer_bootstraps_vc_redist_for_router_runtime() -> None:
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "Install-WindowsVCRedistIfNeeded" in ps1
    assert "OPENSQUILLA_SKIP_VC_REDIST" in ps1
    assert "Microsoft.VCRedist.2015+.x64" in ps1
    assert "https://aka.ms/vs/17/release/vc_redist.x64.exe" in ps1
    assert "safe router fallback" in ps1
    assert "If automatic installation fails, install it manually" in ps1
    assert "After installing, reopen PowerShell and restart OpenSquilla" in ps1
