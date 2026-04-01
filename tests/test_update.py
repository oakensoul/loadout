# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.update."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from loadout.config import LoadoutConfig
from loadout.update import run_update, run_upgrade

# ---------------------------------------------------------------------------
# run_update
# ---------------------------------------------------------------------------


@patch("loadout.update.build_claude_config")
@patch("loadout.update.install_globals")
@patch("loadout.update.build_dotfiles")
@patch("loadout.brew.run")
@patch("loadout.brew.shutil.which", return_value="/opt/homebrew/bin/brew")
@patch("loadout.update.run")
def test_run_update_full_flow(
    mock_update_run: MagicMock,
    mock_brew_which: MagicMock,
    mock_brew_run: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    tmp_path: Path,
) -> None:
    """All steps should execute when dotfiles dirs exist and brew is available."""
    dotfiles = tmp_path / ".dotfiles"
    dotfiles.mkdir()
    private = tmp_path / ".dotfiles-private"
    private.mkdir()
    brewfile = dotfiles / "Brewfile"
    brewfile.write_text("", encoding="utf-8")

    config = LoadoutConfig(base_dir=tmp_path)
    run_update(config)

    # Git pulls
    mock_update_run.assert_any_call(
        ["git", "-C", str(dotfiles), "pull", "--ff-only"], dry_run=False
    )
    mock_update_run.assert_any_call(["git", "-C", str(private), "pull", "--ff-only"], dry_run=False)
    # Build
    mock_build.assert_called_once_with(config, dry_run=False)
    # Brew update + bundle (via brew.py)
    mock_brew_run.assert_any_call(["brew", "update"], dry_run=False, interactive=True)
    mock_brew_run.assert_any_call(
        ["brew", "bundle", f"--file={brewfile}"],
        dry_run=False,
        check=False,
        interactive=True,
    )
    # Globals
    mock_globals.assert_called_once_with(config, dry_run=False)


@patch("loadout.update.build_claude_config")
@patch("loadout.update.install_globals")
@patch("loadout.update.build_dotfiles")
@patch("loadout.brew.run")
@patch("loadout.brew.shutil.which", return_value="/opt/homebrew/bin/brew")
@patch("loadout.update.run")
def test_run_update_dry_run(
    mock_update_run: MagicMock,
    mock_brew_which: MagicMock,
    mock_brew_run: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    tmp_path: Path,
) -> None:
    """Dry-run flag should propagate to all mutating operations."""
    dotfiles = tmp_path / ".dotfiles"
    dotfiles.mkdir()
    private = tmp_path / ".dotfiles-private"
    private.mkdir()
    brewfile = dotfiles / "Brewfile"
    brewfile.write_text("", encoding="utf-8")

    config = LoadoutConfig(base_dir=tmp_path)
    run_update(config, dry_run=True)

    # All runner calls should have dry_run=True
    for c in mock_update_run.call_args_list:
        assert c.kwargs.get("dry_run") is True, f"Expected dry_run=True in {c}"
    for c in mock_brew_run.call_args_list:
        assert c.kwargs.get("dry_run") is True, f"Expected dry_run=True in {c}"

    mock_build.assert_called_once_with(config, dry_run=True)
    mock_globals.assert_called_once_with(config, dry_run=True)


@patch("loadout.update.build_claude_config")
@patch("loadout.update.install_globals")
@patch("loadout.update.build_dotfiles")
@patch("loadout.brew.run")
@patch("loadout.brew.shutil.which", return_value="/opt/homebrew/bin/brew")
@patch("loadout.update.run")
def test_run_update_missing_dotfiles_dir(
    mock_update_run: MagicMock,
    mock_brew_which: MagicMock,
    mock_brew_run: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    tmp_path: Path,
) -> None:
    """Should skip git pull and warn when dotfiles dirs don't exist."""
    config = LoadoutConfig(base_dir=tmp_path)
    run_update(config)

    # No git pull calls should have been made
    git_calls = [c for c in mock_update_run.call_args_list if c.args[0][0] == "git"]
    assert len(git_calls) == 0

    # Build and globals should still be called
    mock_build.assert_called_once()
    mock_globals.assert_called_once()


@patch("loadout.update.build_claude_config")
@patch("loadout.update.install_globals")
@patch("loadout.update.build_dotfiles")
@patch("loadout.brew.run")
@patch("loadout.brew.shutil.which", return_value=None)
@patch("loadout.update.run")
def test_run_update_no_brew(
    mock_update_run: MagicMock,
    mock_brew_which: MagicMock,
    mock_brew_run: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    tmp_path: Path,
) -> None:
    """Should skip all brew steps when brew is not found."""
    dotfiles = tmp_path / ".dotfiles"
    dotfiles.mkdir()
    private = tmp_path / ".dotfiles-private"
    private.mkdir()

    config = LoadoutConfig(base_dir=tmp_path)
    run_update(config)

    # No brew calls
    mock_brew_run.assert_not_called()

    # Other steps should still run
    mock_build.assert_called_once()
    mock_globals.assert_called_once()


@patch("loadout.update.build_claude_config")
@patch("loadout.update.install_globals")
@patch("loadout.update.build_dotfiles")
@patch("loadout.brew.run")
@patch("loadout.brew.shutil.which", return_value="/opt/homebrew/bin/brew")
@patch("loadout.update.run")
def test_run_update_no_brewfile(
    mock_update_run: MagicMock,
    mock_brew_which: MagicMock,
    mock_brew_run: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    tmp_path: Path,
) -> None:
    """Should skip brew bundle when Brewfile is missing."""
    dotfiles = tmp_path / ".dotfiles"
    dotfiles.mkdir()
    # No Brewfile created

    config = LoadoutConfig(base_dir=tmp_path)
    run_update(config)

    # No brew calls (no Brewfile means brew_bundle skips entirely)
    mock_brew_run.assert_not_called()


# ---------------------------------------------------------------------------
# run_upgrade
# ---------------------------------------------------------------------------


@patch("loadout.update.build_claude_config")
@patch("loadout.update.install_globals")
@patch("loadout.update.build_dotfiles")
@patch("loadout.brew.run")
@patch("loadout.brew.shutil.which", return_value="/opt/homebrew/bin/brew")
@patch("loadout.update.shutil.which", return_value="/opt/homebrew/bin/brew")
@patch("loadout.update.run")
def test_run_upgrade_calls_update_then_upgrade(
    mock_update_run: MagicMock,
    mock_update_which: MagicMock,
    mock_brew_which: MagicMock,
    mock_brew_run: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    tmp_path: Path,
) -> None:
    """Upgrade should call update first, then brew upgrade."""
    dotfiles = tmp_path / ".dotfiles"
    dotfiles.mkdir()
    private = tmp_path / ".dotfiles-private"
    private.mkdir()

    config = LoadoutConfig(base_dir=tmp_path)
    run_upgrade(config)

    # build_dotfiles should have been called (from update)
    mock_build.assert_called_once()
    # install_globals should have been called (from update)
    mock_globals.assert_called_once()
    # brew upgrade should be in the runner calls
    mock_update_run.assert_any_call(["brew", "upgrade"], dry_run=False, interactive=True)


@patch("loadout.update.build_claude_config")
@patch("loadout.update.install_globals")
@patch("loadout.update.build_dotfiles")
@patch("loadout.brew.run")
@patch("loadout.brew.shutil.which", return_value=None)
@patch("loadout.update.shutil.which", return_value=None)
@patch("loadout.update.run")
def test_run_upgrade_no_brew(
    mock_update_run: MagicMock,
    mock_update_which: MagicMock,
    mock_brew_which: MagicMock,
    mock_brew_run: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    tmp_path: Path,
) -> None:
    """Should skip brew upgrade when brew is not found."""
    config = LoadoutConfig(base_dir=tmp_path)
    run_upgrade(config)

    # No brew calls at all
    brew_calls = [c for c in mock_update_run.call_args_list if c.args[0][0] == "brew"]
    assert len(brew_calls) == 0
    mock_brew_run.assert_not_called()

    # Update steps should still have run
    mock_build.assert_called_once()
    mock_globals.assert_called_once()
