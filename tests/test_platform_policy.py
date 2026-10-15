from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_documented_desktop_matrix_matches_ci_targets() -> None:
    workflow = (ROOT / ".github" / "workflows" / "desktop.yml").read_text(encoding="utf-8")
    policy = (ROOT / "docs" / "platform-support-and-signing.md").read_text(encoding="utf-8")
    assert "target: x86_64-pc-windows-msvc" in workflow
    assert "target: x86_64-unknown-linux-gnu" in workflow
    assert "target: aarch64-apple-darwin" in workflow
    assert "x86_64-apple-darwin" not in workflow
    assert "Intel macOS (x86_64) is not supported" in policy
    assert "unsigned" in policy
    assert "not signed or notarized" in policy


def test_windows_workflow_covers_install_upgrade_and_uninstall() -> None:
    workflow = (ROOT / ".github" / "workflows" / "desktop.yml").read_text(encoding="utf-8")
    assert "Install and launch Windows installer in a clean directory" in workflow
    assert "Upgrade the installed Windows app" in workflow
    assert "Uninstall the Windows app" in workflow
