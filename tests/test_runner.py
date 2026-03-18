"""Tests for loadout.runner."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

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
            capture_output=False,
            text=True,
        )
        assert result.returncode == 0

    @patch("loadout.runner.subprocess.run")
    def test_run_capture_mode(self, mock_run: MagicMock) -> None:
        """capture=True passes capture_output=True to subprocess.run."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hello"], returncode=0, stdout="hello\n", stderr=""
        )

        result = run(["echo", "hello"], capture=True)

        mock_run.assert_called_once_with(
            ["echo", "hello"],
            check=True,
            capture_output=True,
            text=True,
        )
        assert result.stdout == "hello\n"

    @patch("loadout.runner.subprocess.run")
    def test_run_check_raises_on_failure(self, mock_run: MagicMock) -> None:
        """check=True causes CalledProcessError to propagate."""
        mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=["false"])

        with pytest.raises(subprocess.CalledProcessError):
            run(["false"], check=True)


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
