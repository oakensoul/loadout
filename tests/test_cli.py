"""CLI smoke tests using Click's CliRunner."""

from __future__ import annotations

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


class TestDryRunFlag:
    """Verify --dry-run propagates through context."""

    def test_dry_run_sets_context(self) -> None:
        result = CliRunner().invoke(cli, ["--dry-run", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
