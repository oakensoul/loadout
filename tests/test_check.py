# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for the health check engine."""

from __future__ import annotations

import subprocess
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

from loadout.check import (
    CheckResult,
    CheckStatus,
    check_brewfile_fragments,
    check_claude_code,
    check_claude_config,
    check_git,
    check_github_ssh,
    check_globals_scripts,
    check_homebrew,
    check_macos_scripts,
    check_nvm_node,
    check_onepassword,
    check_pyenv_python,
    render_checks,
    run_checks,
)
from loadout.config import LoadoutConfig


class TestCheckHomebrew:
    """Tests for check_homebrew."""

    def test_brew_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "shutil.which",
            lambda cmd: "/opt/homebrew/bin/brew" if cmd == "brew" else None,
        )
        result = check_homebrew()
        assert result.status == CheckStatus.OK
        assert "brew found" in result.detail

    def test_brew_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        result = check_homebrew()
        assert result.status == CheckStatus.ERROR
        assert "not found" in result.detail


class TestCheckGit:
    """Tests for check_git."""

    def test_git_present_with_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/git" if cmd == "git" else None)
        completed = subprocess.CompletedProcess(
            args=["git", "--version"], returncode=0, stdout="git version 2.44.0", stderr=""
        )
        with patch("loadout.check.subprocess.run", return_value=completed):
            result = check_git()
        assert result.status == CheckStatus.OK
        assert "2.44.0" in result.detail

    def test_git_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        result = check_git()
        assert result.status == CheckStatus.ERROR

    def test_git_version_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/git" if cmd == "git" else None)
        with patch(
            "loadout.check.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            result = check_git()
        assert result.status == CheckStatus.WARN


class TestCheckNvmNode:
    """Tests for check_nvm_node."""

    def test_node_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/usr/local/bin/node" if cmd == "node" else None
        )
        completed = subprocess.CompletedProcess(
            args=["node", "--version"], returncode=0, stdout="v20.11.0", stderr=""
        )
        with patch("loadout.check.subprocess.run", return_value=completed):
            result = check_nvm_node()
        assert result.status == CheckStatus.OK
        assert "v20.11.0" in result.detail

    def test_node_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        result = check_nvm_node()
        assert result.status == CheckStatus.WARN


class TestCheckPyenvPython:
    """Tests for check_pyenv_python."""

    def test_python3_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/usr/bin/python3" if cmd == "python3" else None
        )
        completed = subprocess.CompletedProcess(
            args=["python3", "--version"], returncode=0, stdout="Python 3.12.3", stderr=""
        )
        with patch("loadout.check.subprocess.run", return_value=completed):
            result = check_pyenv_python()
        assert result.status == CheckStatus.OK
        assert "3.12.3" in result.detail

    def test_python3_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        result = check_pyenv_python()
        assert result.status == CheckStatus.WARN


class TestCheckOnePassword:
    """Tests for check_onepassword."""

    def test_op_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "shutil.which",
            lambda cmd: "/usr/local/bin/op" if cmd == "op" else None,
        )
        result = check_onepassword()
        assert result.status == CheckStatus.OK

    def test_op_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        result = check_onepassword()
        assert result.status == CheckStatus.WARN


class TestCheckGithubSsh:
    """Tests for check_github_ssh."""

    def test_ssh_success(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["ssh", "-T", "git@github.com"],
            returncode=1,
            stdout="",
            stderr="Hi oakensoul! You've successfully authenticated.",
        )
        with patch("loadout.check.subprocess.run", return_value=completed):
            result = check_github_ssh()
        assert result.status == CheckStatus.OK
        assert "Hi oakensoul" in result.detail

    def test_ssh_no_greeting(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["ssh", "-T", "git@github.com"],
            returncode=255,
            stdout="",
            stderr="Connection refused",
        )
        with patch("loadout.check.subprocess.run", return_value=completed):
            result = check_github_ssh()
        assert result.status == CheckStatus.WARN

    def test_ssh_timeout(self) -> None:
        with patch(
            "loadout.check.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=10),
        ):
            result = check_github_ssh()
        assert result.status == CheckStatus.WARN
        assert "timed out" in result.detail.lower()

    def test_ssh_not_found(self) -> None:
        with patch("loadout.check.subprocess.run", side_effect=FileNotFoundError):
            result = check_github_ssh()
        assert result.status == CheckStatus.ERROR


class TestCheckClaudeCode:
    """Tests for check_claude_code."""

    def test_claude_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/usr/local/bin/claude" if cmd == "claude" else None
        )
        result = check_claude_code()
        assert result.status == CheckStatus.OK

    def test_claude_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        result = check_claude_code()
        assert result.status == CheckStatus.WARN


class TestCheckBrewfileFragments:
    """Tests for check_brewfile_fragments."""

    def test_check_brewfile_fragments_base_exists(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / ".dotfiles"
        brewfiles = dotfiles / "brewfiles"
        brewfiles.mkdir(parents=True)
        (brewfiles / "Brewfile.base").touch()
        config = LoadoutConfig(base_dir=tmp_path)
        results = check_brewfile_fragments(config)
        assert len(results) == 1
        assert results[0].status == CheckStatus.OK
        assert results[0].label == "Brewfile.base"

    def test_check_brewfile_fragments_base_missing(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / ".dotfiles"
        brewfiles = dotfiles / "brewfiles"
        brewfiles.mkdir(parents=True)
        config = LoadoutConfig(base_dir=tmp_path)
        results = check_brewfile_fragments(config)
        assert len(results) == 1
        assert results[0].status == CheckStatus.ERROR
        assert results[0].label == "Brewfile.base"

    def test_check_brewfile_fragments_org_missing(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / ".dotfiles"
        brewfiles = dotfiles / "brewfiles"
        brewfiles.mkdir(parents=True)
        (brewfiles / "Brewfile.base").touch()
        config = LoadoutConfig(base_dir=tmp_path, orgs=["acme"])
        results = check_brewfile_fragments(config)
        assert len(results) == 2
        assert results[0].status == CheckStatus.OK
        assert results[1].status == CheckStatus.WARN
        assert results[1].label == "Brewfile.acme"

    def test_check_brewfile_fallback(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / ".dotfiles"
        dotfiles.mkdir(parents=True)
        (dotfiles / "Brewfile").touch()
        config = LoadoutConfig(base_dir=tmp_path)
        results = check_brewfile_fragments(config)
        assert len(results) == 1
        assert results[0].status == CheckStatus.OK
        assert results[0].label == "Brewfile"


class TestCheckGlobalsScripts:
    """Tests for check_globals_scripts."""

    def test_check_globals_scripts(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / ".dotfiles"
        globals_dir = dotfiles / "globals"
        globals_dir.mkdir(parents=True)
        (globals_dir / "globals.base.sh").touch()
        config = LoadoutConfig(base_dir=tmp_path, orgs=["acme"])
        results = check_globals_scripts(config)
        assert len(results) == 2
        assert results[0].status == CheckStatus.OK
        assert results[0].label == "globals.base.sh"
        assert results[1].status == CheckStatus.WARN
        assert results[1].label == "globals.acme.sh"

    def test_check_globals_private_base(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / ".dotfiles"
        globals_dir = dotfiles / "globals"
        globals_dir.mkdir(parents=True)
        (globals_dir / "globals.base.sh").touch()

        private_globals = tmp_path / ".dotfiles-private" / "globals" / "base"
        private_globals.mkdir(parents=True)
        (private_globals / "globals.sh").touch()

        config = LoadoutConfig(base_dir=tmp_path, orgs=[])
        results = check_globals_scripts(config)
        assert len(results) == 2
        assert results[0].label == "globals.base.sh"
        assert results[1].label == "globals.sh (private base)"
        assert results[1].status == CheckStatus.OK


class TestCheckMacosScripts:
    """Tests for check_macos_scripts."""

    def test_no_private_scripts(self, tmp_path: Path) -> None:
        """Returns empty list when no private macos scripts exist."""
        config = LoadoutConfig(base_dir=tmp_path)
        results = check_macos_scripts(config)
        assert results == []

    def test_private_base_exists(self, tmp_path: Path) -> None:
        """Detects private base set-defaults.sh when present."""
        private_macos = tmp_path / ".dotfiles-private" / "macos" / "base"
        private_macos.mkdir(parents=True)
        (private_macos / "set-defaults.sh").touch()

        config = LoadoutConfig(base_dir=tmp_path)
        results = check_macos_scripts(config)
        assert len(results) == 1
        assert results[0].status == CheckStatus.OK
        assert results[0].label == "set-defaults.sh (private base)"

    def test_org_script_missing(self, tmp_path: Path) -> None:
        """Reports WARN when an org macos script is missing."""
        config = LoadoutConfig(base_dir=tmp_path, orgs=["acme"])
        results = check_macos_scripts(config)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN
        assert results[0].label == "set-defaults.sh (acme)"

    def test_org_script_exists(self, tmp_path: Path) -> None:
        """Detects per-org set-defaults.sh when present."""
        org_macos = tmp_path / ".dotfiles-private" / "macos" / "orgs" / "acme"
        org_macos.mkdir(parents=True)
        (org_macos / "set-defaults.sh").touch()

        config = LoadoutConfig(base_dir=tmp_path, orgs=["acme"])
        results = check_macos_scripts(config)
        assert len(results) == 1
        assert results[0].status == CheckStatus.OK
        assert results[0].label == "set-defaults.sh (acme)"

    def test_private_base_and_org(self, tmp_path: Path) -> None:
        """Both private base and org scripts are reported."""
        private_macos = tmp_path / ".dotfiles-private" / "macos" / "base"
        private_macos.mkdir(parents=True)
        (private_macos / "set-defaults.sh").touch()

        org_macos = tmp_path / ".dotfiles-private" / "macos" / "orgs" / "acme"
        org_macos.mkdir(parents=True)
        (org_macos / "set-defaults.sh").touch()

        config = LoadoutConfig(base_dir=tmp_path, orgs=["acme"])
        results = check_macos_scripts(config)
        assert len(results) == 2
        assert results[0].label == "set-defaults.sh (private base)"
        assert results[1].label == "set-defaults.sh (acme)"


class TestCheckClaudeConfig:
    """Tests for check_claude_config."""

    def test_check_claude_config_valid(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "mcp.json").write_text('{"mcpServers": {}}', encoding="utf-8")
        config = LoadoutConfig(base_dir=tmp_path)
        result = check_claude_config(config)
        assert result.status == CheckStatus.OK

    def test_check_claude_config_missing(self, tmp_path: Path) -> None:
        config = LoadoutConfig(base_dir=tmp_path)
        result = check_claude_config(config)
        assert result.status == CheckStatus.WARN
        assert "not found" in result.detail

    def test_check_claude_config_malformed(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "mcp.json").write_text("{invalid json", encoding="utf-8")
        config = LoadoutConfig(base_dir=tmp_path)
        result = check_claude_config(config)
        assert result.status == CheckStatus.WARN
        assert "malformed" in result.detail


class TestRunChecks:
    """Tests for run_checks."""

    def test_returns_list_of_check_results(self, tmp_path: Path) -> None:
        config = LoadoutConfig(base_dir=tmp_path)
        with patch("loadout.check.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="version", stderr=""
            )
            results = run_checks(config)
        assert isinstance(results, list)
        # 7 tool checks + brewfile fallback(1) + globals base(1) + macos(0) + claude config(1) = 10
        assert len(results) == 10
        assert all(isinstance(r, CheckResult) for r in results)


class TestRenderChecks:
    """Tests for render_checks."""

    def test_render_output(self) -> None:
        results = [
            CheckResult(status=CheckStatus.OK, label="Git", detail="git version 2.44"),
            CheckResult(status=CheckStatus.WARN, label="Node.js", detail="not found"),
            CheckResult(status=CheckStatus.ERROR, label="Homebrew", detail="brew not found"),
        ]
        buf = StringIO()
        test_console = Console(file=buf, width=120)
        with patch("loadout.ui.console", test_console):
            render_checks(results)
        output = buf.getvalue()
        assert "Git" in output
        assert "Node.js" in output
        assert "Homebrew" in output
