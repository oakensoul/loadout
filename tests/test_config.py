"""Tests for loadout.config module."""

from __future__ import annotations

from pathlib import Path

from loadout.config import LoadoutConfig, load_config, save_config


class TestPathProperties:
    def test_default_paths(self) -> None:
        """Path properties return the expected locations under home."""
        cfg = LoadoutConfig()
        home = Path.home()

        assert cfg.dotfiles_dir == home / ".dotfiles"
        assert cfg.dotfiles_private_dir == home / ".dotfiles-private"
        assert cfg.build_dir == home / ".dotfiles" / "build"
        assert cfg.config_path == home / ".dotfiles" / ".loadout.toml"

    def test_custom_base_dir(self, tmp_path: Path) -> None:
        """Path properties respect a custom base_dir."""
        cfg = LoadoutConfig(base_dir=tmp_path)

        assert cfg.dotfiles_dir == tmp_path / ".dotfiles"
        assert cfg.dotfiles_private_dir == tmp_path / ".dotfiles-private"
        assert cfg.build_dir == tmp_path / ".dotfiles" / "build"
        assert cfg.config_path == tmp_path / ".dotfiles" / ".loadout.toml"


class TestLoadConfig:
    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        """load_config returns a default config when the TOML file is missing."""
        cfg = load_config(base_dir=tmp_path)

        assert cfg.user == ""
        assert cfg.orgs == []

    def test_round_trip_save_load(self, tmp_path: Path) -> None:
        """Saving and then loading a config preserves all fields."""
        original = LoadoutConfig(user="oakensoul", orgs=["acme", "widgets"], base_dir=tmp_path)
        save_config(original)

        loaded = load_config(base_dir=tmp_path)

        assert loaded.user == original.user
        assert loaded.orgs == original.orgs


class TestSaveConfig:
    def test_escapes_special_characters(self, tmp_path: Path) -> None:
        """Values with quotes and backslashes are properly escaped."""
        cfg = LoadoutConfig(
            user='has"quote',
            orgs=["back\\slash", 'more"quotes'],
            base_dir=tmp_path,
        )
        save_config(cfg)

        loaded = load_config(base_dir=tmp_path)

        assert loaded.user == 'has"quote'
        assert loaded.orgs == ["back\\slash", 'more"quotes']
