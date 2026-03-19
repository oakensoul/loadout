"""Tests for error handling, verbose mode, and Ctrl+C behavior."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from loadout import ui
from loadout.cli import cli
from loadout.exceptions import (
    LoadoutBuildError,
    LoadoutCommandError,
    LoadoutConfigError,
)

if TYPE_CHECKING:
    from rich.console import Console


# ── Verbose flag ────────────────────────────────────────────────────────────


class TestVerboseFlag:
    """Verify --verbose/-v flag propagation."""

    def test_verbose_flag_accepted(self) -> None:
        result = CliRunner().invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_short_verbose_flag(self) -> None:
        result = CliRunner().invoke(cli, ["-v", "--help"])
        assert result.exit_code == 0

    @patch("loadout.core.check_health")
    def test_verbose_sets_ui_flag(self, mock_check: MagicMock) -> None:
        CliRunner().invoke(cli, ["-v", "check"])
        assert ui.is_verbose() is True

    @patch("loadout.core.check_health")
    def test_no_verbose_clears_flag(self, mock_check: MagicMock) -> None:
        ui.set_verbose(True)
        CliRunner().invoke(cli, ["check"])
        assert ui.is_verbose() is False


# ── verbose_line ────────────────────────────────────────────────────────────


class TestVerboseLine:
    def test_verbose_line_prints_when_enabled(
        self, monkeypatch: pytest.MonkeyPatch, captured_console: tuple[Console, StringIO]
    ) -> None:
        test_console, buf = captured_console
        monkeypatch.setattr(ui, "err_console", test_console)
        monkeypatch.setattr(ui, "_verbose", True)

        ui.verbose_line("debug info here")

        assert "debug info here" in buf.getvalue()

    def test_verbose_line_silent_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch, captured_console: tuple[Console, StringIO]
    ) -> None:
        test_console, buf = captured_console
        monkeypatch.setattr(ui, "err_console", test_console)
        monkeypatch.setattr(ui, "_verbose", False)

        ui.verbose_line("debug info here")

        assert buf.getvalue() == ""


# ── error_panel ─────────────────────────────────────────────────────────────


class TestErrorPanel:
    def test_error_panel_renders(
        self, monkeypatch: pytest.MonkeyPatch, captured_console: tuple[Console, StringIO]
    ) -> None:
        test_console, buf = captured_console
        monkeypatch.setattr(ui, "err_console", test_console)

        ui.error_panel("Test Error", "something went wrong")

        output = buf.getvalue()
        assert "Test Error" in output
        assert "something went wrong" in output


# ── CLI error handling (via CliRunner) ──────────────────────────────────────


class TestCLIErrorHandling:
    """Verify that LoadoutError subclasses produce non-zero exit codes."""

    @patch("loadout.core.run_build")
    def test_build_error_exits_nonzero(self, mock_build: MagicMock) -> None:
        """LoadoutBuildError propagates and Click reports non-zero exit."""
        mock_build.side_effect = LoadoutBuildError("Malformed JSON in /tmp/bad.json")
        result = CliRunner().invoke(cli, ["build"])
        assert result.exit_code != 0

    @patch("loadout.core.run_build")
    def test_command_error_exits_nonzero(self, mock_build: MagicMock) -> None:
        mock_build.side_effect = LoadoutCommandError(
            "Command failed", cmd="brew update", exit_code=1, stderr="E: network"
        )
        result = CliRunner().invoke(cli, ["build"])
        assert result.exit_code != 0

    @patch("loadout.core.check_health")
    def test_config_error_exits_nonzero(self, mock_check: MagicMock) -> None:
        mock_check.side_effect = LoadoutConfigError("Invalid TOML")
        result = CliRunner().invoke(cli, ["check"])
        assert result.exit_code != 0


# ── Config error ────────────────────────────────────────────────────────────


class TestConfigError:
    def test_invalid_toml_raises_config_error(self, tmp_path: Path) -> None:
        from loadout.config import load_config

        config_dir = tmp_path / ".dotfiles"
        config_dir.mkdir(parents=True)
        config_path = config_dir / ".loadout.toml"
        config_path.write_text("this is not valid toml {{{}}}!!!", encoding="utf-8")

        with pytest.raises(LoadoutConfigError, match="Invalid TOML"):
            load_config(base_dir=tmp_path)


# ── Runner verbose output ──────────────────────────────────────────────────


class TestRunnerVerbose:
    @patch("loadout.runner.subprocess.run")
    def test_verbose_logs_command(
        self,
        mock_run: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        captured_console: tuple[Console, StringIO],
    ) -> None:
        import subprocess

        test_console, buf = captured_console
        monkeypatch.setattr(ui, "err_console", test_console)
        # Also patch the runner's reference to err_console
        from loadout import runner

        monkeypatch.setattr(runner, "err_console", test_console)
        monkeypatch.setattr(ui, "_verbose", True)

        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hello"], returncode=0, stdout="", stderr=""
        )

        from loadout.runner import run

        run(["echo", "hello"])

        output = buf.getvalue()
        assert "echo hello" in output
