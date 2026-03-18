"""CLI smoke tests using Click's CliRunner."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
from click.testing import CliRunner

from loadout.cli import cli


class TestCLIHelp:
    """Verify all commands are wired and produce valid help."""

    def test_main_help(self) -> None:
        result = CliRunner().invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Loadout" in result.output

    def test_init_help(self) -> None:
        result = CliRunner().invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "--user" in result.output
        assert "--orgs" in result.output

    def test_update_help(self) -> None:
        result = CliRunner().invoke(cli, ["update", "--help"])
        assert result.exit_code == 0

    def test_upgrade_help(self) -> None:
        result = CliRunner().invoke(cli, ["upgrade", "--help"])
        assert result.exit_code == 0

    def test_check_help(self) -> None:
        result = CliRunner().invoke(cli, ["check", "--help"])
        assert result.exit_code == 0

    def test_build_help(self) -> None:
        result = CliRunner().invoke(cli, ["build", "--help"])
        assert result.exit_code == 0

    def test_globals_help(self) -> None:
        result = CliRunner().invoke(cli, ["globals", "--help"])
        assert result.exit_code == 0

    def test_display_help(self) -> None:
        result = CliRunner().invoke(cli, ["display", "--help"])
        assert result.exit_code == 0


class TestStubCommands:
    """Verify stub commands print a not-implemented message."""

    def test_init_not_implemented(self) -> None:
        result = CliRunner().invoke(cli, ["init", "--user", "test", "--orgs", "org1"])
        assert "not yet implemented" in result.output.lower()

    def test_update_not_implemented(self) -> None:
        result = CliRunner().invoke(cli, ["update"])
        assert "not yet implemented" in result.output.lower()

    def test_upgrade_not_implemented(self) -> None:
        result = CliRunner().invoke(cli, ["upgrade"])
        assert "not yet implemented" in result.output.lower()


class TestDryRunFlag:
    """Verify --dry-run propagates through context."""

    def test_dry_run_sets_context(self) -> None:
        """--dry-run flag sets ctx.obj['dry_run'] to True."""
        captured: dict[str, bool] = {}

        @cli.command("_test_dry_run")
        @click.pass_context
        def test_cmd(ctx: click.Context) -> None:
            captured["dry_run"] = ctx.obj["dry_run"]

        try:
            result = CliRunner().invoke(cli, ["--dry-run", "_test_dry_run"])
            assert result.exit_code == 0
            assert captured["dry_run"] is True

            result = CliRunner().invoke(cli, ["_test_dry_run"])
            assert result.exit_code == 0
            assert captured["dry_run"] is False
        finally:
            # Clean up the temporary test command
            cli.commands.pop("_test_dry_run", None)  # type: ignore[union-attr]


class TestCLIDelegation:
    """Verify CLI commands delegate to core functions."""

    @patch("loadout.core.check_health")
    def test_check_invokes_core(self, mock_check: MagicMock) -> None:
        result = CliRunner().invoke(cli, ["check"])
        assert result.exit_code == 0
        mock_check.assert_called_once()

    @patch("loadout.core.run_build")
    def test_build_invokes_core(self, mock_build: MagicMock) -> None:
        result = CliRunner().invoke(cli, ["--dry-run", "build"])
        assert result.exit_code == 0
        mock_build.assert_called_once_with(dry_run=True)

    @patch("loadout.core.run_globals")
    def test_globals_invokes_core(self, mock_globals: MagicMock) -> None:
        result = CliRunner().invoke(cli, ["globals"])
        assert result.exit_code == 0
        mock_globals.assert_called_once()

    @patch("loadout.core.run_display")
    def test_display_invokes_core_with_mode(self, mock_display: MagicMock) -> None:
        result = CliRunner().invoke(cli, ["display", "connected"])
        assert result.exit_code == 0
        mock_display.assert_called_once_with(mode="connected", dry_run=False)

    @patch("loadout.core.run_display")
    def test_display_invokes_core_without_mode(self, mock_display: MagicMock) -> None:
        result = CliRunner().invoke(cli, ["display"])
        assert result.exit_code == 0
        mock_display.assert_called_once_with(mode=None, dry_run=False)
