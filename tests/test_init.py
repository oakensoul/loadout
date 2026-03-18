"""Tests for loadout.init — full machine bootstrap flow."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from loadout.config import LoadoutConfig
from loadout.init import run_init


def _fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    """Return a successful CompletedProcess for any command."""
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")


# ---------------------------------------------------------------------------
# Full flow
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=True)
@patch("loadout.init.generate_launch_agent_plist", return_value="<plist/>")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
def test_run_init_full_flow(
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_plist: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """All 10 steps should execute in order."""
    # Create dirs and files that would exist after a real clone.
    # Clone itself is skipped (already-exists path), but all subsequent
    # steps that rely on these dirs/files existing will work.
    (tmp_path / ".dotfiles").mkdir()
    (tmp_path / ".dotfiles-private").mkdir()
    (tmp_path / ".dotfiles" / "Brewfile").write_text("# brewfile\n")
    macos_dir = tmp_path / ".dotfiles" / "macos"
    macos_dir.mkdir()
    (macos_dir / "defaults-base.sh").write_text("#!/bin/bash\n")

    # Patch home to tmp_path so file operations are isolated
    with patch.object(LoadoutConfig, "home", new_callable=lambda: property(lambda self: tmp_path)):
        run_init("testuser", ["orgA", "orgB"])

    # 1. Clone repos — dirs exist so clone is skipped (tested separately)

    # 2. SSH keygen
    keygen_calls = [c for c in mock_run.call_args_list if "ssh-keygen" in c.args[0]]
    assert len(keygen_calls) == 1

    # 3. SSH key registration (op read + gh ssh-key add)
    op_calls = [c for c in mock_run.call_args_list if c.args[0][0] == "op"]
    gh_calls = [c for c in mock_run.call_args_list if c.args[0][0] == "gh"]
    assert len(op_calls) >= 1
    assert len(gh_calls) >= 1

    # 4. Switch remotes
    set_url_calls = [c for c in mock_run.call_args_list if "set-url" in c.args[0]]
    assert len(set_url_calls) == 2

    # 5. Build dotfiles
    mock_build.assert_called_once()

    # 6. Brew bundle (brew update + brew bundle)
    brew_calls = [c for c in mock_run.call_args_list if c.args[0][0] == "brew"]
    assert len(brew_calls) >= 1  # At least brew update; Brewfile may not exist

    # 7. Install globals
    mock_globals.assert_called_once()

    # 10. Save config
    mock_save.assert_called_once()
    saved_config = mock_save.call_args.args[0]
    assert saved_config.user == "testuser"
    assert saved_config.orgs == ["orgA", "orgB"]


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
def test_run_init_dry_run(
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """Mutating calls should receive dry_run=True."""
    with patch.object(LoadoutConfig, "home", new_callable=lambda: property(lambda self: tmp_path)):
        run_init("testuser", ["org1"], dry_run=True)

    # All runner.run calls should have dry_run=True
    for c in mock_run.call_args_list:
        # Skip read-only calls (op read with capture=True)
        if c.kwargs.get("capture"):
            continue
        assert c.kwargs.get("dry_run") is True, f"Expected dry_run=True for {c}"

    # build_dotfiles should get dry_run=True
    mock_build.assert_called_once()
    assert mock_build.call_args.kwargs.get("dry_run") is True

    # install_globals should get dry_run=True
    mock_globals.assert_called_once()
    assert mock_globals.call_args.kwargs.get("dry_run") is True


# ---------------------------------------------------------------------------
# Existing dotfiles skip clone
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
def test_run_init_existing_dotfiles_skips_clone(
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """When dotfiles dirs already exist, git clone should not be called."""
    (tmp_path / ".dotfiles").mkdir()
    (tmp_path / ".dotfiles-private").mkdir()

    with patch.object(LoadoutConfig, "home", new_callable=lambda: property(lambda self: tmp_path)):
        run_init("testuser", ["org1"])

    clone_calls = [c for c in mock_run.call_args_list if "clone" in c.args[0]]
    assert len(clone_calls) == 0


# ---------------------------------------------------------------------------
# Existing SSH key skips keygen
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
def test_run_init_existing_ssh_key_skips_keygen(
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """When SSH key already exists, ssh-keygen should not be called."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_ed25519").write_text("fake key", encoding="utf-8")

    with patch.object(LoadoutConfig, "home", new_callable=lambda: property(lambda self: tmp_path)):
        run_init("testuser", ["org1"])

    keygen_calls = [c for c in mock_run.call_args_list if "ssh-keygen" in c.args[0]]
    assert len(keygen_calls) == 0


# ---------------------------------------------------------------------------
# No op CLI skips SSH registration
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.runner.run", side_effect=_fake_run)
def test_run_init_no_op_cli_skips_ssh_registration(
    mock_run: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """When 1Password CLI is not available, SSH key registration should be skipped."""

    def selective_which(name: str) -> str | None:
        if name == "op":
            return None
        return "/usr/bin/thing"

    with (
        patch("loadout.init.shutil.which", side_effect=selective_which),
        patch.object(LoadoutConfig, "home", new_callable=lambda: property(lambda self: tmp_path)),
    ):
        run_init("testuser", ["org1"])

    # No op or gh calls should have been made
    op_calls = [c for c in mock_run.call_args_list if c.args[0][0] == "op"]
    gh_auth_calls = [
        c for c in mock_run.call_args_list if c.args[0][0] == "gh" and "ssh-key" in c.args[0]
    ]
    assert len(op_calls) == 0
    assert len(gh_auth_calls) == 0


# ---------------------------------------------------------------------------
# No brew skips bundle
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.runner.run", side_effect=_fake_run)
def test_run_init_no_brew_skips_bundle(
    mock_run: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """When brew is not available, brew bundle step should be skipped."""

    def selective_which(name: str) -> str | None:
        if name == "brew":
            return None
        return "/usr/bin/thing"

    with (
        patch("loadout.init.shutil.which", side_effect=selective_which),
        patch.object(LoadoutConfig, "home", new_callable=lambda: property(lambda self: tmp_path)),
    ):
        run_init("testuser", ["org1"])

    brew_calls = [c for c in mock_run.call_args_list if c.args[0][0] == "brew"]
    assert len(brew_calls) == 0


# ---------------------------------------------------------------------------
# Save config
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
def test_run_init_saves_config(
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """save_config should be called with correct user and orgs."""
    with patch.object(LoadoutConfig, "home", new_callable=lambda: property(lambda self: tmp_path)):
        run_init("myuser", ["orgX", "orgY"])

    mock_save.assert_called_once()
    saved = mock_save.call_args.args[0]
    assert isinstance(saved, LoadoutConfig)
    assert saved.user == "myuser"
    assert saved.orgs == ["orgX", "orgY"]


# ---------------------------------------------------------------------------
# Non-macOS skips launch agent
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
def test_run_init_non_macos_skips_launch_agent(
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """On non-macOS, the launch agent plist should not be written."""
    with patch.object(LoadoutConfig, "home", new_callable=lambda: property(lambda self: tmp_path)):
        run_init("testuser", ["org1"])

    # No launchctl calls
    launchctl_calls = [c for c in mock_run.call_args_list if "launchctl" in c.args[0]]
    assert len(launchctl_calls) == 0

    # No plist file written
    plist_path = tmp_path / "Library" / "LaunchAgents" / "com.oakensoul.loadout.display.plist"
    assert not plist_path.exists()
