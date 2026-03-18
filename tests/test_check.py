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
    check_brewfile,
    check_claude_code,
    check_git,
    check_github_ssh,
    check_homebrew,
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


class TestCheckBrewfile:
    """Tests for check_brewfile."""

    def test_brewfile_exists(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / ".dotfiles"
        dotfiles.mkdir()
        (dotfiles / "Brewfile").touch()
        config = LoadoutConfig(base_dir=tmp_path)
        result = check_brewfile(config)
        assert result.status == CheckStatus.OK

    def test_brewfile_missing(self, tmp_path: Path) -> None:
        config = LoadoutConfig(base_dir=tmp_path)
        result = check_brewfile(config)
        assert result.status == CheckStatus.WARN


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
        assert len(results) == 8
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
