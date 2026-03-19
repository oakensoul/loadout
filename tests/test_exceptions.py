# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.exceptions."""

from __future__ import annotations

from loadout.exceptions import (
    LoadoutBuildError,
    LoadoutCommandError,
    LoadoutConfigError,
    LoadoutError,
)


class TestExceptionHierarchy:
    """Verify custom exceptions inherit from LoadoutError."""

    def test_config_error_is_loadout_error(self) -> None:
        assert issubclass(LoadoutConfigError, LoadoutError)

    def test_command_error_is_loadout_error(self) -> None:
        assert issubclass(LoadoutCommandError, LoadoutError)

    def test_build_error_is_loadout_error(self) -> None:
        assert issubclass(LoadoutBuildError, LoadoutError)

    def test_loadout_error_is_exception(self) -> None:
        assert issubclass(LoadoutError, Exception)


class TestLoadoutCommandError:
    """Verify LoadoutCommandError stores metadata."""

    def test_stores_cmd_and_exit_code(self) -> None:
        exc = LoadoutCommandError("failed", cmd="brew update", exit_code=1, stderr="error output")
        assert str(exc) == "failed"
        assert exc.cmd == "brew update"
        assert exc.exit_code == 1
        assert exc.stderr == "error output"

    def test_defaults(self) -> None:
        exc = LoadoutCommandError("simple failure")
        assert exc.cmd == ""
        assert exc.exit_code is None
        assert exc.stderr == ""
