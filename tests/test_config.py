"""Tests for loadout.config module."""

from __future__ import annotations

from pathlib import Path

from loadout.config import LoadoutConfig, load_config, save_config


def test_path_properties() -> None:
    """Path properties return the expected locations."""
    cfg = LoadoutConfig()
    home = Path.home()

    assert cfg.dotfiles_dir == home / ".dotfiles"
    assert cfg.dotfiles_private_dir == home / ".dotfiles-private"
    assert cfg.build_dir == home / ".dotfiles" / "build"
    assert cfg.config_path == home / ".dotfiles" / ".loadout.toml"


def test_load_missing_file_returns_defaults(tmp_path: Path, monkeypatch: object) -> None:
    """load_config returns a default config when the TOML file is missing."""
    # Point config_path to a non-existent file by monkeypatching Path.home
    import loadout.config as config_mod

    monkeypatch.setattr(config_mod.Path, "home", staticmethod(lambda: tmp_path))  # type: ignore[arg-type]

    cfg = load_config()

    assert cfg.user == ""
    assert cfg.orgs == []


def test_round_trip_save_load(tmp_path: Path, monkeypatch: object) -> None:
    """Saving and then loading a config preserves all fields."""
    import loadout.config as config_mod

    monkeypatch.setattr(config_mod.Path, "home", staticmethod(lambda: tmp_path))  # type: ignore[arg-type]

    original = LoadoutConfig(user="oakensoul", orgs=["acme", "widgets"])
    save_config(original)

    loaded = load_config()

    assert loaded.user == original.user
    assert loaded.orgs == original.orgs
