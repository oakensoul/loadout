# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for the core API facade."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from loadout import core


class TestCheckHealth:
    """Tests for check_health delegation."""

    @patch("loadout.check.render_checks")
    @patch("loadout.check.run_checks")
    @patch("loadout.config.load_config")
    def test_check_health_delegates(
        self,
        mock_load_config: MagicMock,
        mock_run_checks: MagicMock,
        mock_render_checks: MagicMock,
    ) -> None:
        sentinel_config = object()
        sentinel_results = [object()]
        mock_load_config.return_value = sentinel_config
        mock_run_checks.return_value = sentinel_results

        core.check_health()

        mock_load_config.assert_called_once()
        mock_run_checks.assert_called_once_with(sentinel_config)
        mock_render_checks.assert_called_once_with(sentinel_results)


class TestRunBuild:
    """Tests for run_build delegation."""

    @patch("loadout.build.build_dotfiles")
    @patch("loadout.config.load_config")
    def test_run_build_delegates(
        self,
        mock_load_config: MagicMock,
        mock_build_dotfiles: MagicMock,
    ) -> None:
        sentinel_config = object()
        mock_load_config.return_value = sentinel_config

        core.run_build(dry_run=True)

        mock_load_config.assert_called_once()
        mock_build_dotfiles.assert_called_once_with(sentinel_config, dry_run=True)


class TestRunGlobals:
    """Tests for run_globals delegation."""

    @patch("loadout.globals.install_globals")
    @patch("loadout.config.load_config")
    def test_run_globals_delegates(
        self,
        mock_load_config: MagicMock,
        mock_install_globals: MagicMock,
    ) -> None:
        sentinel_config = object()
        mock_load_config.return_value = sentinel_config

        core.run_globals()

        mock_load_config.assert_called_once()
        mock_install_globals.assert_called_once_with(sentinel_config, dry_run=False)


class TestRunDisplay:
    """Tests for run_display delegation."""

    @patch("loadout.display.apply_display_profile")
    @patch("loadout.config.load_config")
    def test_run_display_delegates(
        self,
        mock_load_config: MagicMock,
        mock_apply_display: MagicMock,
    ) -> None:
        sentinel_config = object()
        mock_load_config.return_value = sentinel_config

        core.run_display(mode="solo", dry_run=True)

        mock_load_config.assert_called_once()
        mock_apply_display.assert_called_once_with(sentinel_config, mode="solo", dry_run=True)


class TestRunClaudeConfig:
    """Tests for run_claude_config delegation."""

    @patch("loadout.claude.build_claude_config")
    @patch("loadout.config.load_config")
    def test_run_claude_config_delegates(
        self,
        mock_load_config: MagicMock,
        mock_build_claude: MagicMock,
    ) -> None:
        sentinel_config = object()
        mock_load_config.return_value = sentinel_config

        core.run_claude_config(dry_run=True)

        mock_load_config.assert_called_once()
        mock_build_claude.assert_called_once_with(sentinel_config, dry_run=True)


class TestRunInit:
    """Tests for run_init delegation."""

    @patch("loadout.init.run_init")
    def test_run_init_delegates(self, mock_init: MagicMock) -> None:
        core.run_init("testuser", ["org1"], dry_run=True)
        mock_init.assert_called_once_with("testuser", ["org1"], dry_run=True, headless=False)

    @patch("loadout.init.run_init")
    def test_run_init_headless_delegates(self, mock_init: MagicMock) -> None:
        core.run_init("testuser", ["org1"], dry_run=False, headless=True)
        mock_init.assert_called_once_with("testuser", ["org1"], dry_run=False, headless=True)


class TestRunUpdate:
    """Tests for run_update delegation."""

    @patch("loadout.update.run_update")
    @patch("loadout.config.load_config")
    def test_run_update_delegates(
        self,
        mock_load_config: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        sentinel_config = object()
        mock_load_config.return_value = sentinel_config

        core.run_update(dry_run=True)

        mock_load_config.assert_called_once()
        mock_update.assert_called_once_with(sentinel_config, dry_run=True)


class TestRunUpgrade:
    """Tests for run_upgrade delegation."""

    @patch("loadout.update.run_upgrade")
    @patch("loadout.config.load_config")
    def test_run_upgrade_delegates(
        self,
        mock_load_config: MagicMock,
        mock_upgrade: MagicMock,
    ) -> None:
        sentinel_config = object()
        mock_load_config.return_value = sentinel_config

        core.run_upgrade(dry_run=True)

        mock_load_config.assert_called_once()
        mock_upgrade.assert_called_once_with(sentinel_config, dry_run=True)
