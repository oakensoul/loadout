# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.runner."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from loadout.exceptions import LoadoutCommandError
from loadout.runner import run


class TestRunNormal:
    """Test normal (non-dry-run) execution."""

    @patch("loadout.runner.subprocess.run")
    def test_run_calls_subprocess(self, mock_run: MagicMock) -> None:
        """run() delegates to subprocess.run with correct arguments."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hello"], returncode=0, stdout="", stderr=""
        )

        result = run(["echo", "hello"])

        mock_run.assert_called_once_with(
            ["echo", "hello"],
            check=True,
            stdout=None,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert result.returncode == 0

    @patch("loadout.runner.subprocess.run")
    def test_run_capture_mode(self, mock_run: MagicMock) -> None:
        """capture=True passes stdout=PIPE, stderr=PIPE."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hello"], returncode=0, stdout="hello\n", stderr=""
        )

        result = run(["echo", "hello"], capture=True)

        mock_run.assert_called_once_with(
            ["echo", "hello"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert result.stdout == "hello\n"

    @patch("loadout.runner.subprocess.run")
    def test_run_check_raises_on_failure(self, mock_run: MagicMock) -> None:
        """check=True wraps CalledProcessError as LoadoutCommandError."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["false"], stderr="some error"
        )

        with pytest.raises(LoadoutCommandError, match="Command failed with exit code 1"):
            run(["false"], check=True)

    @patch("loadout.runner.subprocess.run")
    def test_run_check_failure_captures_details(self, mock_run: MagicMock) -> None:
        """LoadoutCommandError preserves exit code and stderr."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=42, cmd=["bad"], stderr="oops"
        )

        with pytest.raises(LoadoutCommandError) as exc_info:
            run(["bad", "arg"], check=True)

        assert exc_info.value.exit_code == 42
        assert exc_info.value.stderr == "oops"
        assert exc_info.value.cmd == "bad arg"

    @patch("loadout.runner.subprocess.run")
    def test_run_file_not_found(self, mock_run: MagicMock) -> None:
        """FileNotFoundError is wrapped as LoadoutCommandError."""
        mock_run.side_effect = FileNotFoundError("No such file or directory")

        with pytest.raises(LoadoutCommandError, match="Command not found: nosuchcmd"):
            run(["nosuchcmd", "--help"])

    @patch("loadout.runner.subprocess.run")
    def test_run_always_captures_stderr(self, mock_run: MagicMock) -> None:
        """stderr=PIPE is passed even when capture=False."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hi"],
            returncode=0,
            stdout=None,
            stderr="",
        )

        run(["echo", "hi"], capture=False)

        mock_run.assert_called_once_with(
            ["echo", "hi"],
            check=True,
            stdout=None,
            stderr=subprocess.PIPE,
            text=True,
        )


class TestRunDryRun:
    """Test dry-run mode."""

    @patch("loadout.runner.subprocess.run")
    def test_dry_run_does_not_call_subprocess(self, mock_run: MagicMock) -> None:
        """dry_run=True must not invoke subprocess.run."""
        result = run(["rm", "-rf", "/"], dry_run=True)

        mock_run.assert_not_called()
        assert result.returncode == 0
        assert result.stdout == ""
        assert result.stderr == ""

    def test_dry_run_returns_completed_process(self) -> None:
        """dry_run=True returns a CompletedProcess with zero exit."""
        result = run(["echo", "test"], dry_run=True)

        assert isinstance(result, subprocess.CompletedProcess)
        assert result.returncode == 0
        assert result.stdout == ""
        assert result.stderr == ""
