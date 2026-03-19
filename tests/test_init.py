# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
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
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
def test_run_init_full_flow(
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_plist: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """All steps should execute in order."""
    (tmp_path / ".dotfiles").mkdir()
    (tmp_path / ".dotfiles-private").mkdir()
    macos_dir = tmp_path / ".dotfiles" / "macos"
    macos_dir.mkdir()
    (macos_dir / "defaults-base.sh").write_text("#!/bin/bash\n")

    run_init("testuser", ["orgA", "orgB"], base_dir=tmp_path)

    # 2. SSH keygen
    keygen_calls = [c for c in mock_run.call_args_list if "ssh-keygen" in c.args[0]]
    assert len(keygen_calls) == 1

    # 3. SSH key registration (bash pipeline)
    bash_calls = [
        c
        for c in mock_run.call_args_list
        if c.args[0][0] == "bash" and "gh auth login" in str(c.args[0])
    ]
    assert len(bash_calls) == 1

    # 4. Switch remotes — repo names should NOT have leading dot
    set_url_calls = [c for c in mock_run.call_args_list if "set-url" in c.args[0]]
    assert len(set_url_calls) == 2
    for c in set_url_calls:
        url = c.args[0][-1]
        assert "/." not in url, f"URL should not have leading dot: {url}"

    # 5. Build dotfiles
    mock_build.assert_called_once()

    # 6. Brew bundle
    mock_brew.assert_called_once()

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
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
def test_run_init_dry_run(
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """Mutating calls should receive dry_run=True; save_config skipped."""
    run_init("testuser", ["org1"], base_dir=tmp_path, dry_run=True)

    # All runner.run calls should have dry_run=True
    for c in mock_run.call_args_list:
        assert c.kwargs.get("dry_run") is True, f"Expected dry_run=True: {c}"

    # build_dotfiles should get dry_run=True
    mock_build.assert_called_once()
    assert mock_build.call_args.kwargs.get("dry_run") is True

    # install_globals should get dry_run=True
    mock_globals.assert_called_once()
    assert mock_globals.call_args.kwargs.get("dry_run") is True

    # brew_bundle should get dry_run=True
    mock_brew.assert_called_once()
    assert mock_brew.call_args.kwargs.get("dry_run") is True

    # save_config should NOT be called in dry-run
    mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# Existing dotfiles skip clone
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
def test_run_init_existing_dotfiles_skips_clone(
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """When dotfiles dirs already exist, git clone should not be called."""
    (tmp_path / ".dotfiles").mkdir()
    (tmp_path / ".dotfiles-private").mkdir()

    run_init("testuser", ["org1"], base_dir=tmp_path)

    clone_calls = [c for c in mock_run.call_args_list if "clone" in c.args[0]]
    assert len(clone_calls) == 0


# ---------------------------------------------------------------------------
# Existing SSH key skips keygen
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
def test_run_init_existing_ssh_key_skips_keygen(
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
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

    run_init("testuser", ["org1"], base_dir=tmp_path)

    keygen_calls = [c for c in mock_run.call_args_list if "ssh-keygen" in c.args[0]]
    assert len(keygen_calls) == 0


# ---------------------------------------------------------------------------
# No op CLI skips SSH registration
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
def test_run_init_no_op_cli_skips_ssh_registration(
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """When 1Password CLI is not available, SSH registration is skipped."""

    def selective_which(name: str) -> str | None:
        if name == "op":
            return None
        return "/usr/bin/thing"

    with patch("loadout.init.shutil.which", side_effect=selective_which):
        run_init("testuser", ["org1"], base_dir=tmp_path)

    # No bash pipeline (op read | gh auth login) calls
    bash_auth_calls = [
        c
        for c in mock_run.call_args_list
        if c.args[0][0] == "bash" and "gh auth login" in str(c.args[0])
    ]
    assert len(bash_auth_calls) == 0


# ---------------------------------------------------------------------------
# No brew skips bundle
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
def test_run_init_no_brew_skips_bundle(
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """brew_bundle is called regardless; it handles missing brew internally."""

    def selective_which(name: str) -> str | None:
        if name == "brew":
            return None
        return "/usr/bin/thing"

    with patch("loadout.init.shutil.which", side_effect=selective_which):
        run_init("testuser", ["org1"], base_dir=tmp_path)

    # brew_bundle is still called (it decides internally to skip)
    mock_brew.assert_called_once()


# ---------------------------------------------------------------------------
# Save config
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
def test_run_init_saves_config(
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """save_config should be called with correct user and orgs."""
    run_init("myuser", ["orgX", "orgY"], base_dir=tmp_path)

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
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
def test_run_init_non_macos_skips_launch_agent(
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """On non-macOS, the launch agent plist should not be written."""
    run_init("testuser", ["org1"], base_dir=tmp_path)

    launchctl_calls = [c for c in mock_run.call_args_list if "launchctl" in c.args[0]]
    assert len(launchctl_calls) == 0

    plist_path = tmp_path / "Library" / "LaunchAgents" / "com.oakensoul.loadout.display.plist"
    assert not plist_path.exists()
