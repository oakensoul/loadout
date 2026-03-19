# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.globals."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from loadout.config import LoadoutConfig
from loadout.globals import (
    _read_package_list,
    ensure_claude_code,
    ensure_nvm_node,
    ensure_pyenv_python,
    install_globals,
    install_npm_globals,
    install_pip_globals,
)

# ---------------------------------------------------------------------------
# ensure_claude_code
# ---------------------------------------------------------------------------


@patch("loadout.globals.run")
@patch("loadout.globals.shutil.which", return_value="/usr/local/bin/claude")
def test_ensure_claude_code_already_installed(mock_which: MagicMock, mock_run: MagicMock) -> None:
    """Should skip install when claude is already on PATH."""
    ensure_claude_code()
    mock_run.assert_not_called()


@patch("loadout.globals.run")
@patch("loadout.globals.shutil.which", return_value=None)
def test_ensure_claude_code_installs(mock_which: MagicMock, mock_run: MagicMock) -> None:
    """Should install when claude is not on PATH."""
    ensure_claude_code()
    mock_run.assert_called_once_with(
        ["npm", "install", "-g", "@anthropic-ai/claude-code"], dry_run=False
    )


@patch("loadout.globals.run")
@patch("loadout.globals.shutil.which", return_value=None)
def test_ensure_claude_code_dry_run(mock_which: MagicMock, mock_run: MagicMock) -> None:
    """Dry-run should pass dry_run=True to runner."""
    ensure_claude_code(dry_run=True)
    mock_run.assert_called_once_with(
        ["npm", "install", "-g", "@anthropic-ai/claude-code"], dry_run=True
    )


# ---------------------------------------------------------------------------
# ensure_nvm_node
# ---------------------------------------------------------------------------


@patch("loadout.globals.run")
@patch("loadout.globals.shutil.which", return_value="/usr/local/bin/node")
def test_ensure_nvm_node_already_installed(
    mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
) -> None:
    """Should skip when NVM dir exists and node is available."""
    nvm_dir = tmp_path / ".nvm"
    nvm_dir.mkdir()
    config = LoadoutConfig(base_dir=tmp_path)
    ensure_nvm_node(config)
    mock_run.assert_not_called()


@patch("loadout.globals.run")
@patch("loadout.globals.shutil.which", return_value=None)
def test_ensure_nvm_node_installs(
    mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
) -> None:
    """Should install NVM and Node when neither exists."""
    config = LoadoutConfig(base_dir=tmp_path)
    ensure_nvm_node(config)
    assert mock_run.call_count == 2


# ---------------------------------------------------------------------------
# ensure_pyenv_python
# ---------------------------------------------------------------------------


@patch("loadout.globals.run")
@patch("loadout.globals.shutil.which", return_value=None)
def test_ensure_pyenv_not_found(mock_which: MagicMock, mock_run: MagicMock) -> None:
    """Should skip gracefully when pyenv is not installed."""
    ensure_pyenv_python()
    mock_run.assert_not_called()


@patch("loadout.globals.run")
@patch("loadout.globals.shutil.which", return_value="/usr/local/bin/pyenv")
def test_ensure_pyenv_python_already_installed(mock_which: MagicMock, mock_run: MagicMock) -> None:
    """Should skip when pyenv already has a python version."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="3.12.0\n", stderr=""
    )
    ensure_pyenv_python()
    # Only one call — to check versions
    mock_run.assert_called_once()


@patch("loadout.globals.run")
@patch("loadout.globals.shutil.which", return_value="/usr/local/bin/pyenv")
def test_ensure_pyenv_python_installs(mock_which: MagicMock, mock_run: MagicMock) -> None:
    """Should install python when pyenv has no versions."""
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    ensure_pyenv_python()
    assert mock_run.call_count == 2


# ---------------------------------------------------------------------------
# install_npm_globals
# ---------------------------------------------------------------------------


@patch("loadout.globals.run")
def test_install_npm_globals_already_installed(mock_run: MagicMock) -> None:
    """Should skip packages that are already globally installed."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="├── typescript@5.0.0\n", stderr=""
    )
    install_npm_globals(["typescript"])
    # Only the check call, no install call
    mock_run.assert_called_once()


@patch("loadout.globals.run")
def test_install_npm_globals_installs_missing(mock_run: MagicMock) -> None:
    """Should install packages that are not globally installed."""
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
    install_npm_globals(["typescript"])
    assert mock_run.call_count == 2
    mock_run.assert_any_call(["npm", "install", "-g", "typescript"], dry_run=False)


# ---------------------------------------------------------------------------
# install_pip_globals
# ---------------------------------------------------------------------------


@patch("loadout.globals.run")
def test_install_pip_globals_already_installed(mock_run: MagicMock) -> None:
    """Should skip packages that are already installed."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="Name: black\n", stderr=""
    )
    install_pip_globals(["black"])
    mock_run.assert_called_once()


@patch("loadout.globals.run")
def test_install_pip_globals_installs_missing(mock_run: MagicMock) -> None:
    """Should install packages that are missing."""
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
    install_pip_globals(["black"])
    assert mock_run.call_count == 2
    mock_run.assert_any_call(["pip", "install", "--user", "black"], dry_run=False)


# ---------------------------------------------------------------------------
# _read_package_list
# ---------------------------------------------------------------------------


def test_read_package_list(tmp_path: Path) -> None:
    """Should read packages, ignoring blanks and comments."""
    pkg_file = tmp_path / "packages.txt"
    pkg_file.write_text("foo\n# comment\n\nbar\n  baz  \n", encoding="utf-8")
    result = _read_package_list(pkg_file)
    assert result == ["foo", "bar", "baz"]


def test_read_package_list_missing(tmp_path: Path) -> None:
    """Should return empty list for missing files."""
    result = _read_package_list(tmp_path / "nope.txt")
    assert result == []


# ---------------------------------------------------------------------------
# install_globals (orchestration)
# ---------------------------------------------------------------------------


@patch("loadout.globals.run")
@patch("loadout.globals.shutil.which", return_value="/usr/bin/thing")
def test_install_globals_reads_org_packages(
    mock_which: MagicMock,
    mock_run: MagicMock,
    tmp_path: Path,
) -> None:
    """Should read npm-globals.txt and pip-globals.txt from org dirs."""
    # Set up pyenv versions check to return something so it skips install
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="3.12.0\n", stderr=""
    )

    # Create NVM dir so ensure_nvm_node skips install
    (tmp_path / ".nvm").mkdir()

    # Create org package list files
    org_dir = tmp_path / ".dotfiles-private" / "dotfiles" / "orgs" / "myorg"
    org_dir.mkdir(parents=True)
    (org_dir / "npm-globals.txt").write_text("eslint\nprettier\n", encoding="utf-8")
    (org_dir / "pip-globals.txt").write_text("black\nruff\n", encoding="utf-8")

    config = LoadoutConfig(user="testuser", orgs=["myorg"], base_dir=tmp_path)
    install_globals(config)

    # Verify npm and pip install calls were made
    call_args_list = [c.args[0] for c in mock_run.call_args_list]
    # Should contain npm list checks for eslint and prettier
    assert ["npm", "list", "-g", "--depth=0", "eslint"] in call_args_list
    assert ["npm", "list", "-g", "--depth=0", "prettier"] in call_args_list
    # Should contain pip show checks for black and ruff
    assert ["pip", "show", "black"] in call_args_list
    assert ["pip", "show", "ruff"] in call_args_list


@patch("loadout.globals.run")
@patch("loadout.globals.shutil.which", return_value="/usr/bin/thing")
def test_install_globals_dry_run(
    mock_which: MagicMock,
    mock_run: MagicMock,
    tmp_path: Path,
) -> None:
    """Dry-run should pass through; read-only checks always execute."""
    (tmp_path / ".nvm").mkdir()
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="3.12.0\n", stderr=""
    )

    config = LoadoutConfig(user="testuser", orgs=[], base_dir=tmp_path)
    install_globals(config, dry_run=True)

    # Read-only queries (pyenv versions, npm list, pip show) should NOT have dry_run
    # Mutating commands (install) should have dry_run=True
    for c in mock_run.call_args_list:
        # Read-only queries (capture=True, check=False) should not have dry_run
        if c.kwargs.get("capture") and c.kwargs.get("check") is False:
            assert c.kwargs.get("dry_run") is not True
        else:
            assert c.kwargs.get("dry_run") is True or "dry_run" not in c.kwargs


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@patch("loadout.globals.run")
@patch("loadout.globals.shutil.which", return_value="/usr/local/bin/claude")
def test_ensure_claude_code_idempotent(mock_which: MagicMock, mock_run: MagicMock) -> None:
    """Calling twice should not install twice."""
    ensure_claude_code()
    ensure_claude_code()
    mock_run.assert_not_called()
