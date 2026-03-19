"""Integration tests using fixture dotfile repos.

These tests exercise the full merge pipeline against real fixture files
in isolated temp directories — no mocks for the build logic itself.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from loadout.build import build_dotfiles
from loadout.cli import cli
from loadout.config import LoadoutConfig, load_config, save_config

FIXTURES = Path(__file__).parent / "fixtures"


def _setup_from_fixtures(tmp_path: Path, orgs: list[str]) -> LoadoutConfig:
    """Copy fixture dotfiles into a temp dir and return a config pointing there."""
    dotfiles_dest = tmp_path / ".dotfiles"
    private_dest = tmp_path / ".dotfiles-private"

    shutil.copytree(FIXTURES / "dotfiles", dotfiles_dest)
    shutil.copytree(FIXTURES / "dotfiles-private", private_dest)

    return LoadoutConfig(user="testuser", orgs=orgs, base_dir=tmp_path)


# ── Build pipeline integration ──────────────────────────────────────────────


class TestBuildIntegration:
    """End-to-end build tests using fixture repos in temp dirs."""

    def test_single_org_concat(self, tmp_path: Path) -> None:
        """Concat strategy merges base + org for .zshrc and .aliases."""
        config = _setup_from_fixtures(tmp_path, ["acme"])
        build_dotfiles(config)

        zshrc = (tmp_path / ".zshrc").read_text(encoding="utf-8")
        assert "export PATH" in zshrc  # from base
        assert "ACME_ENV" in zshrc  # from acme org
        assert "# --- org overlay: acme ---" in zshrc

        aliases = (tmp_path / ".aliases").read_text(encoding="utf-8")
        assert 'alias ll="ls -la"' in aliases  # from base
        assert 'alias deploy="acme-deploy"' in aliases  # from acme

    def test_single_org_gitconfig_includes(self, tmp_path: Path) -> None:
        """Gitconfig strategy creates include directives and .gitconfig.d/."""
        config = _setup_from_fixtures(tmp_path, ["acme"])
        build_dotfiles(config)

        gitconfig = (tmp_path / ".gitconfig").read_text(encoding="utf-8")
        assert "[user]" in gitconfig
        assert "name = Test User" in gitconfig
        assert "[include]" in gitconfig
        assert "path = ~/.gitconfig.d/acme" in gitconfig

        org_file = tmp_path / ".gitconfig.d" / "acme"
        assert org_file.exists()
        assert "dev@acme.com" in org_file.read_text(encoding="utf-8")

    def test_single_org_json_deep_merge(self, tmp_path: Path) -> None:
        """JSON strategy deep-merges, org wins on conflict."""
        config = _setup_from_fixtures(tmp_path, ["acme"])
        build_dotfiles(config)

        data = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
        assert data["editor"] == "vim"  # from base
        assert data["indent"] == 4  # from base
        assert data["theme"] == "light"  # org wins over "dark"
        assert data["org"] == "acme"  # from org
        assert data["acme_specific"] is True  # from org

    def test_single_org_yaml_deep_merge(self, tmp_path: Path) -> None:
        """YAML strategy deep-merges, org wins on conflict."""
        config = _setup_from_fixtures(tmp_path, ["acme"])
        build_dotfiles(config)

        data = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        assert data["level"] == 1  # from base
        assert data["opts"]["color"] is True  # from base
        assert data["opts"]["pager"] == "bat"  # org wins over "less"
        assert data["opts"]["acme_flag"] is True  # from org

    def test_single_org_replace(self, tmp_path: Path) -> None:
        """Replace strategy fully replaces base file with org file."""
        config = _setup_from_fixtures(tmp_path, ["acme"])
        build_dotfiles(config)

        vimrc = (tmp_path / ".vimrc").read_text(encoding="utf-8")
        assert "tabstop=2" in vimrc  # from org
        assert "set number" not in vimrc  # base is gone

    def test_multiple_orgs_cumulative_concat(self, tmp_path: Path) -> None:
        """Multiple orgs concatenate cumulatively on .zshrc."""
        config = _setup_from_fixtures(tmp_path, ["acme", "widgets"])
        build_dotfiles(config)

        zshrc = (tmp_path / ".zshrc").read_text(encoding="utf-8")
        assert "export PATH" in zshrc  # base
        assert "ACME_ENV" in zshrc  # acme
        assert "WIDGETS_API" in zshrc  # widgets
        assert "# --- org overlay: acme ---" in zshrc
        assert "# --- org overlay: widgets ---" in zshrc

    def test_multiple_orgs_gitconfig_includes(self, tmp_path: Path) -> None:
        """Both orgs get include directives in .gitconfig."""
        config = _setup_from_fixtures(tmp_path, ["acme", "widgets"])
        build_dotfiles(config)

        gitconfig = (tmp_path / ".gitconfig").read_text(encoding="utf-8")
        assert "path = ~/.gitconfig.d/acme" in gitconfig
        assert "path = ~/.gitconfig.d/widgets" in gitconfig
        assert (tmp_path / ".gitconfig.d" / "acme").exists()
        assert (tmp_path / ".gitconfig.d" / "widgets").exists()

    def test_multiple_orgs_json_layered_merge(self, tmp_path: Path) -> None:
        """Second org's JSON values override first org's on conflict."""
        config = _setup_from_fixtures(tmp_path, ["acme", "widgets"])
        build_dotfiles(config)

        data = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
        assert data["editor"] == "vim"  # base survives
        assert data["theme"] == "solarized"  # widgets wins over acme's "light"
        assert data["org"] == "widgets"  # widgets wins over acme

    def test_build_creates_build_dir(self, tmp_path: Path) -> None:
        """Build dir is created and contains intermediate files."""
        config = _setup_from_fixtures(tmp_path, ["acme"])
        build_dotfiles(config)

        assert config.build_dir.exists()
        assert (config.build_dir / ".zshrc").exists()

    def test_build_is_idempotent(self, tmp_path: Path) -> None:
        """Running build twice produces the same output."""
        config = _setup_from_fixtures(tmp_path, ["acme"])

        build_dotfiles(config)
        first_zshrc = (tmp_path / ".zshrc").read_text(encoding="utf-8")
        first_json = (tmp_path / "settings.json").read_text(encoding="utf-8")

        build_dotfiles(config)
        second_zshrc = (tmp_path / ".zshrc").read_text(encoding="utf-8")
        second_json = (tmp_path / "settings.json").read_text(encoding="utf-8")

        assert first_zshrc == second_zshrc
        assert first_json == second_json

    def test_no_orgs_base_only(self, tmp_path: Path) -> None:
        """With no orgs, base files are installed unmodified."""
        config = _setup_from_fixtures(tmp_path, [])
        build_dotfiles(config)

        zshrc = (tmp_path / ".zshrc").read_text(encoding="utf-8")
        assert "export PATH" in zshrc
        assert "org overlay" not in zshrc

    def test_nonexistent_org_graceful(self, tmp_path: Path) -> None:
        """A non-existent org in the config is silently skipped."""
        config = _setup_from_fixtures(tmp_path, ["acme", "nonexistent"])
        build_dotfiles(config)

        zshrc = (tmp_path / ".zshrc").read_text(encoding="utf-8")
        assert "ACME_ENV" in zshrc
        assert "nonexistent" not in zshrc


# ── Config round-trip integration ───────────────────────────────────────────


class TestConfigIntegration:
    """Test config save/load with real files."""

    def test_save_load_round_trip(self, tmp_path: Path) -> None:
        config = LoadoutConfig(user="oakensoul", orgs=["acme", "widgets"], base_dir=tmp_path)

        # Must create the directory
        config.config_path.parent.mkdir(parents=True, exist_ok=True)
        save_config(config)

        loaded = load_config(base_dir=tmp_path)
        assert loaded.user == "oakensoul"
        assert loaded.orgs == ["acme", "widgets"]

    def test_config_then_build(self, tmp_path: Path) -> None:
        """Save a config then use it for a build."""
        config = LoadoutConfig(user="testuser", orgs=["acme"], base_dir=tmp_path)

        # Copy fixtures
        shutil.copytree(FIXTURES / "dotfiles", tmp_path / ".dotfiles")
        shutil.copytree(FIXTURES / "dotfiles-private", tmp_path / ".dotfiles-private")

        save_config(config)
        loaded = load_config(base_dir=tmp_path)
        build_dotfiles(loaded)

        assert (tmp_path / ".zshrc").exists()
        assert "ACME_ENV" in (tmp_path / ".zshrc").read_text(encoding="utf-8")


# ── CLI smoke tests ─────────────────────────────────────────────────────────


class TestCLISmokeTests:
    """Verify all CLI help commands produce valid output."""

    _COMMANDS = [
        [],
        ["init"],
        ["update"],
        ["upgrade"],
        ["check"],
        ["build"],
        ["globals"],
        ["display"],
    ]

    @pytest.mark.parametrize("cmd", _COMMANDS, ids=lambda c: " ".join(c) or "root")
    def test_help_output(self, cmd: list[str]) -> None:
        result = CliRunner().invoke(cli, [*cmd, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_verbose_flag_in_help(self) -> None:
        result = CliRunner().invoke(cli, ["--help"])
        assert "--verbose" in result.output
        assert "-v" in result.output

    def test_dry_run_flag_in_help(self) -> None:
        result = CliRunner().invoke(cli, ["--help"])
        assert "--dry-run" in result.output

    def test_unknown_command(self) -> None:
        result = CliRunner().invoke(cli, ["nonexistent"])
        assert result.exit_code != 0

    def test_init_missing_required_args(self) -> None:
        result = CliRunner().invoke(cli, ["init"])
        assert result.exit_code != 0
        assert "Missing" in result.output or "required" in result.output.lower()
