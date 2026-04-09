# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.runner."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from loadout.exceptions import LoadoutCommandError
from loadout.runner import brew_prefix_is_owned, run


class TestRunNormal:
    """Test normal (non-dry-run) execution."""

    @patch("loadout.runner.os.path.isfile", return_value=False)
    @patch("loadout.runner.subprocess.run")
    def test_run_calls_subprocess(self, mock_run: MagicMock, _mock_exists: MagicMock) -> None:
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
            env=None,
        )
        assert result.returncode == 0

    @patch("loadout.runner.os.path.isfile", return_value=False)
    @patch("loadout.runner.subprocess.run")
    def test_run_capture_mode(self, mock_run: MagicMock, _mock_exists: MagicMock) -> None:
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
            env=None,
        )
        assert result.stdout == "hello\n"

    @patch("loadout.runner.os.path.isfile", return_value=False)
    @patch("loadout.runner.subprocess.run")
    def test_run_check_raises_on_failure(
        self, mock_run: MagicMock, _mock_exists: MagicMock
    ) -> None:
        """check=True wraps CalledProcessError as LoadoutCommandError."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["false"], stderr="some error"
        )

        with pytest.raises(LoadoutCommandError, match="Command failed with exit code 1"):
            run(["false"], check=True)

    @patch("loadout.runner.os.path.isfile", return_value=False)
    @patch("loadout.runner.subprocess.run")
    def test_run_check_failure_captures_details(
        self, mock_run: MagicMock, _mock_exists: MagicMock
    ) -> None:
        """LoadoutCommandError preserves exit code and stderr."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=42, cmd=["bad"], stderr="oops"
        )

        with pytest.raises(LoadoutCommandError) as exc_info:
            run(["bad", "arg"], check=True)

        assert exc_info.value.exit_code == 42
        assert exc_info.value.stderr == "oops"
        assert exc_info.value.cmd == "bad arg"

    @patch("loadout.runner.os.path.isfile", return_value=False)
    @patch("loadout.runner.subprocess.run")
    def test_run_file_not_found(self, mock_run: MagicMock, _mock_exists: MagicMock) -> None:
        """FileNotFoundError is wrapped as LoadoutCommandError."""
        mock_run.side_effect = FileNotFoundError("No such file or directory")

        with pytest.raises(LoadoutCommandError, match="Command not found: nosuchcmd"):
            run(["nosuchcmd", "--help"])

    @patch("loadout.runner.os.path.isfile", return_value=False)
    @patch("loadout.runner.subprocess.run")
    def test_run_always_captures_stderr(self, mock_run: MagicMock, _mock_exists: MagicMock) -> None:
        """stderr=PIPE is passed even when capture=False (non-interactive)."""
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
            env=None,
        )


class TestRunInteractive:
    """Test interactive mode — subprocess inherits the terminal."""

    @patch("loadout.runner.os.path.isfile", return_value=False)
    @patch("loadout.runner.subprocess.run")
    def test_interactive_inherits_terminal(
        self, mock_run: MagicMock, _mock_exists: MagicMock
    ) -> None:
        """interactive=True does not pipe stdout or stderr."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["brew", "bundle"], returncode=0, stdout=None, stderr=None
        )

        run(["brew", "bundle"], interactive=True)

        mock_run.assert_called_once_with(
            ["brew", "bundle"],
            check=True,
            text=True,
            env=None,
        )

    @patch("loadout.runner.os.path.isfile", return_value=False)
    @patch("loadout.runner.subprocess.run")
    def test_interactive_check_false(self, mock_run: MagicMock, _mock_exists: MagicMock) -> None:
        """interactive=True respects check=False."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["sudo", "cmd"], returncode=1, stdout=None, stderr=None
        )

        result = run(["sudo", "cmd"], interactive=True, check=False)

        assert result.returncode == 1


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


def _apple_silicon_brew_exists(path: str) -> bool:
    """Simulate Apple Silicon Homebrew install for os.path.isfile mocking."""
    return path == "/opt/homebrew/bin/brew"


def _intel_brew_exists(path: str) -> bool:
    """Simulate Intel Homebrew install for os.path.isfile mocking."""
    return path == "/usr/local/bin/brew"


def _home_brew_exists(path: str) -> bool:
    """Simulate devbox ~/.homebrew install (no system brew)."""
    home_brew = str(Path.home() / ".homebrew" / "bin" / "brew")
    return path == home_brew


def _custom_and_system_brew_exists(path: str) -> bool:
    """Simulate both a custom HOMEBREW_PREFIX and system brew installed."""
    return path in ("/Users/dx-test/.homebrew/bin/brew", "/opt/homebrew/bin/brew")


class TestRunBrewPath:
    """Test Homebrew PATH injection for subprocesses."""

    def setup_method(self) -> None:
        """Clear the brew detection cache before each test."""
        from loadout.runner import detect_brew_bin

        detect_brew_bin.cache_clear()

    @patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}, clear=False)
    @patch(
        "loadout.runner.os.path.isfile",
        side_effect=_apple_silicon_brew_exists,
    )
    @patch("loadout.runner.subprocess.run")
    def test_brew_on_path_apple_silicon(self, mock_run: MagicMock, _mock_exists: MagicMock) -> None:
        """env is passed to subprocess.run with Homebrew bin prepended (Apple Silicon)."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["brew", "list"], returncode=0, stdout="", stderr=""
        )

        run(["brew", "list"])

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"] is not None
        path_entries = call_kwargs["env"]["PATH"].split(os.pathsep)
        assert path_entries[0] == "/opt/homebrew/bin"

    @patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}, clear=False)
    @patch(
        "loadout.runner.os.path.isfile",
        side_effect=_apple_silicon_brew_exists,
    )
    @patch("loadout.runner.subprocess.run")
    def test_existing_path_entries_preserved(
        self, mock_run: MagicMock, _mock_exists: MagicMock
    ) -> None:
        """Existing PATH entries are preserved when Homebrew bin is prepended."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hi"], returncode=0, stdout="", stderr=""
        )

        run(["echo", "hi"])

        call_kwargs = mock_run.call_args[1]
        env_path = call_kwargs["env"]["PATH"]
        assert "/usr/bin" in env_path
        assert "/bin" in env_path

    @patch.dict(os.environ, {"PATH": "/opt/homebrew/bin:/usr/bin"}, clear=False)
    @patch(
        "loadout.runner.os.path.isfile",
        side_effect=_apple_silicon_brew_exists,
    )
    @patch("loadout.runner.subprocess.run")
    def test_no_duplicate_when_already_on_path(
        self, mock_run: MagicMock, _mock_exists: MagicMock
    ) -> None:
        """No modification when Homebrew bin is already on PATH."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hi"], returncode=0, stdout="", stderr=""
        )

        run(["echo", "hi"])

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"] is None

    @patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}, clear=False)
    @patch(
        "loadout.runner.os.path.isfile",
        side_effect=_intel_brew_exists,
    )
    @patch("loadout.runner.subprocess.run")
    def test_brew_on_path_intel(self, mock_run: MagicMock, _mock_exists: MagicMock) -> None:
        """env is passed to subprocess.run with Homebrew bin prepended (Intel)."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["brew", "list"], returncode=0, stdout="", stderr=""
        )

        run(["brew", "list"])

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"] is not None
        path_entries = call_kwargs["env"]["PATH"].split(os.pathsep)
        assert path_entries[0] == "/usr/local/bin"

    @patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}, clear=False)
    @patch(
        "loadout.runner.os.path.isfile",
        side_effect=_home_brew_exists,
    )
    @patch("loadout.runner.subprocess.run")
    def test_brew_on_path_home_homebrew(self, mock_run: MagicMock, _mock_exists: MagicMock) -> None:
        """env is passed to subprocess.run with ~/.homebrew/bin prepended (devbox)."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["brew", "list"], returncode=0, stdout="", stderr=""
        )

        run(["brew", "list"])

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"] is not None
        path_entries = call_kwargs["env"]["PATH"].split(os.pathsep)
        expected = str(Path.home() / ".homebrew" / "bin")
        assert path_entries[0] == expected

    @patch("loadout.runner.os.path.isfile", return_value=False)
    @patch("loadout.runner.subprocess.run")
    def test_no_modification_when_brew_not_installed(
        self, mock_run: MagicMock, _mock_exists: MagicMock
    ) -> None:
        """No PATH modification when Homebrew is not installed."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hi"], returncode=0, stdout="", stderr=""
        )

        run(["echo", "hi"])

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"] is None

    @patch.dict(
        os.environ,
        {"PATH": "/usr/bin:/bin", "HOMEBREW_PREFIX": "/Users/dx-test/.homebrew"},
        clear=False,
    )
    @patch(
        "loadout.runner.os.path.isfile",
        side_effect=_custom_and_system_brew_exists,
    )
    @patch("loadout.runner.subprocess.run")
    def test_homebrew_prefix_takes_precedence(
        self, mock_run: MagicMock, _mock_exists: MagicMock
    ) -> None:
        """HOMEBREW_PREFIX env var overrides system brew detection."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["brew", "update"], returncode=0, stdout="", stderr=""
        )

        run(["brew", "update"])

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"] is not None
        path_entries = call_kwargs["env"]["PATH"].split(os.pathsep)
        assert path_entries[0] == "/Users/dx-test/.homebrew/bin"

    @patch.dict(
        os.environ,
        {"PATH": "/usr/bin:/bin", "HOMEBREW_PREFIX": "/nonexistent/.homebrew"},
        clear=False,
    )
    @patch(
        "loadout.runner.os.path.isfile",
        side_effect=_apple_silicon_brew_exists,
    )
    @patch("loadout.runner.subprocess.run")
    def test_homebrew_prefix_falls_back_when_brew_missing(
        self, mock_run: MagicMock, _mock_exists: MagicMock
    ) -> None:
        """Falls back to system brew if HOMEBREW_PREFIX brew doesn't exist."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["brew", "list"], returncode=0, stdout="", stderr=""
        )

        run(["brew", "list"])

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["env"] is not None
        path_entries = call_kwargs["env"]["PATH"].split(os.pathsep)
        assert path_entries[0] == "/opt/homebrew/bin"


class TestBrewPrefixIsOwned:
    """Test brew_prefix_is_owned ownership check."""

    def setup_method(self) -> None:
        """Clear the brew detection cache before each test."""
        from loadout.runner import detect_brew_bin

        detect_brew_bin.cache_clear()

    @patch("loadout.runner.os.path.isfile", return_value=False)
    def test_returns_true_when_no_brew(self, _mock_exists: MagicMock) -> None:
        """No brew detected — returns True so callers handle it separately."""
        assert brew_prefix_is_owned() is True

    @patch("loadout.runner.os.getuid", return_value=501)
    @patch("loadout.runner.os.stat")
    @patch(
        "loadout.runner.os.path.isfile",
        side_effect=_apple_silicon_brew_exists,
    )
    def test_returns_true_when_owned(
        self, _mock_exists: MagicMock, mock_stat: MagicMock, _mock_uid: MagicMock
    ) -> None:
        """Returns True when prefix is owned by current user."""
        mock_stat.return_value = MagicMock(st_uid=501)
        assert brew_prefix_is_owned() is True

    @patch("loadout.runner.os.getuid", return_value=501)
    @patch("loadout.runner.os.stat")
    @patch(
        "loadout.runner.os.path.isfile",
        side_effect=_apple_silicon_brew_exists,
    )
    def test_returns_false_when_not_owned(
        self, _mock_exists: MagicMock, mock_stat: MagicMock, _mock_uid: MagicMock
    ) -> None:
        """Returns False when prefix is owned by a different user."""
        mock_stat.return_value = MagicMock(st_uid=602)
        assert brew_prefix_is_owned() is False

    @patch("loadout.runner.os.getuid", return_value=501)
    @patch("loadout.runner.os.stat", side_effect=OSError("Permission denied"))
    @patch(
        "loadout.runner.os.path.isfile",
        side_effect=_apple_silicon_brew_exists,
    )
    def test_returns_false_on_stat_error(
        self, _mock_exists: MagicMock, _mock_stat: MagicMock, _mock_uid: MagicMock
    ) -> None:
        """Returns False when os.stat raises OSError."""
        assert brew_prefix_is_owned() is False
