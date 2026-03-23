# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.config module."""

from __future__ import annotations

from pathlib import Path

from loadout.config import LoadoutConfig, _toml_escape, load_config, save_config


class TestHomeProperty:
    def test_default_returns_path_home(self) -> None:
        """home property returns Path.home() when base_dir is None."""
        cfg = LoadoutConfig()
        assert cfg.home == Path.home()

    def test_custom_base_dir(self, tmp_path: Path) -> None:
        """home property returns base_dir when set."""
        cfg = LoadoutConfig(base_dir=tmp_path)
        assert cfg.home == tmp_path


class TestTomlEscape:
    def test_escapes_newlines_and_tabs(self) -> None:
        """_toml_escape should escape newline and tab characters."""
        assert _toml_escape("a\nb") == "a\\nb"
        assert _toml_escape("a\tb") == "a\\tb"
        assert _toml_escape("a\n\tb") == "a\\n\\tb"

    def test_escapes_quotes_and_backslashes(self) -> None:
        """_toml_escape should escape quotes and backslashes."""
        assert _toml_escape('a"b') == 'a\\"b'
        assert _toml_escape("a\\b") == "a\\\\b"


class TestPathProperties:
    def test_default_paths(self) -> None:
        """Path properties return the expected locations under home."""
        cfg = LoadoutConfig()
        home = Path.home()

        assert cfg.dotfiles_dir == home / ".dotfiles"
        assert cfg.dotfiles_private_dir == home / ".dotfiles-private"
        assert cfg.build_dir == home / ".dotfiles" / "build"
        assert cfg.config_path == home / ".dotfiles" / ".loadout.toml"
        assert cfg.claude_dir == home / ".claude"

    def test_custom_base_dir(self, tmp_path: Path) -> None:
        """Path properties respect a custom base_dir."""
        cfg = LoadoutConfig(base_dir=tmp_path)

        assert cfg.dotfiles_dir == tmp_path / ".dotfiles"
        assert cfg.dotfiles_private_dir == tmp_path / ".dotfiles-private"
        assert cfg.build_dir == tmp_path / ".dotfiles" / "build"
        assert cfg.config_path == tmp_path / ".dotfiles" / ".loadout.toml"
        assert cfg.claude_dir == tmp_path / ".claude"


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

    def test_round_trip_new_fields(self, tmp_path: Path) -> None:
        """New config fields (github_token_op_path, nvm_version) round-trip correctly."""
        cfg = LoadoutConfig(
            user="testuser",
            orgs=["acme"],
            base_dir=tmp_path,
            github_token_op_path="op://Work/GitHub/token",
            nvm_version="0.41.0",
        )
        save_config(cfg)

        loaded = load_config(base_dir=tmp_path)

        assert loaded.github_token_op_path == "op://Work/GitHub/token"
        assert loaded.nvm_version == "0.41.0"

    def test_defaults_for_new_fields(self, tmp_path: Path) -> None:
        """New config fields have sensible defaults when not in the TOML file."""
        cfg = LoadoutConfig(user="testuser", orgs=[], base_dir=tmp_path)
        assert cfg.github_token_op_path == "op://Personal/GitHub Token/credential"
        assert cfg.nvm_version == "0.40.1"
        assert cfg.pyenv_version == "3"

    def test_round_trip_pyenv_version(self, tmp_path: Path) -> None:
        """pyenv_version round-trips through save/load correctly."""
        cfg = LoadoutConfig(
            user="testuser",
            orgs=[],
            base_dir=tmp_path,
            pyenv_version="3.12",
        )
        save_config(cfg)

        loaded = load_config(base_dir=tmp_path)

        assert loaded.pyenv_version == "3.12"
