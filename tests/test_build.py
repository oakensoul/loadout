# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.build module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from loadout.build import (
    MergeStrategy,
    _append_zshrc_drop_ins,
    _backup_file,
    _get_merge_strategy,
    _merge_concat,
    _merge_gitconfig,
    _merge_json,
    _merge_yaml,
    build_dotfiles,
)
from loadout.config import LoadoutConfig
from loadout.exceptions import LoadoutBuildError


class TestMergeStrategy:
    """Tests for MergeStrategy enum and _get_merge_strategy."""

    def test_enum_values(self) -> None:
        assert MergeStrategy.CONCAT == "concat"
        assert MergeStrategy.GITCONFIG == "gitconfig"
        assert MergeStrategy.JSON == "json"
        assert MergeStrategy.YAML == "yaml"
        assert MergeStrategy.REPLACE == "replace"

    def test_concat_files(self) -> None:
        assert _get_merge_strategy(".zshrc") is MergeStrategy.CONCAT
        assert _get_merge_strategy(".aliases") is MergeStrategy.CONCAT
        assert _get_merge_strategy(".zprofile") is MergeStrategy.CONCAT
        assert _get_merge_strategy(".zshenv") is MergeStrategy.CONCAT

    def test_gitconfig(self) -> None:
        assert _get_merge_strategy(".gitconfig") is MergeStrategy.GITCONFIG

    def test_json(self) -> None:
        assert _get_merge_strategy("settings.json") is MergeStrategy.JSON
        assert _get_merge_strategy(".prettierrc.json") is MergeStrategy.JSON

    def test_yaml(self) -> None:
        assert _get_merge_strategy("config.yaml") is MergeStrategy.YAML
        assert _get_merge_strategy("config.yml") is MergeStrategy.YAML

    def test_replace(self) -> None:
        assert _get_merge_strategy(".vimrc") is MergeStrategy.REPLACE
        assert _get_merge_strategy(".tmux.conf") is MergeStrategy.REPLACE
        assert _get_merge_strategy("somefile") is MergeStrategy.REPLACE

    def test_str_comparison_works(self) -> None:
        """StrEnum values can be compared with plain strings."""
        assert _get_merge_strategy(".zshrc") == "concat"
        assert _get_merge_strategy(".gitconfig") == "gitconfig"


class TestMergeConcat:
    """Tests for _merge_concat."""

    def test_concat_with_base(self, tmp_path: Path) -> None:
        base = tmp_path / "base" / ".zshrc"
        base.parent.mkdir()
        base.write_text("# base config\nexport FOO=1\n", encoding="utf-8")

        org = tmp_path / "org" / ".zshrc"
        org.parent.mkdir()
        org.write_text("export BAR=2\n", encoding="utf-8")

        dest = tmp_path / "dest" / ".zshrc"
        dest.parent.mkdir()

        _merge_concat(base, org, dest, "test-org")

        content = dest.read_text(encoding="utf-8")
        assert "# base config" in content
        assert "export FOO=1" in content
        assert "# --- overlay: test-org ---" in content
        assert "export BAR=2" in content

    def test_concat_without_base(self, tmp_path: Path) -> None:
        base = tmp_path / "nonexistent" / ".zshrc"

        org = tmp_path / "org" / ".zshrc"
        org.parent.mkdir()
        org.write_text("export BAR=2\n", encoding="utf-8")

        dest = tmp_path / "dest" / ".zshrc"
        dest.parent.mkdir()

        _merge_concat(base, org, dest, "test-org")

        content = dest.read_text(encoding="utf-8")
        assert "export BAR=2" in content


class TestMergeGitconfig:
    """Tests for _merge_gitconfig."""

    def test_gitconfig_with_orgs(self, tmp_path: Path) -> None:
        base = tmp_path / ".gitconfig"
        base.write_text("[user]\n    name = Test\n", encoding="utf-8")

        org1_path = tmp_path / "org1" / ".gitconfig"
        org1_path.parent.mkdir()
        org1_path.write_text("[core]\n    autocrlf = true\n", encoding="utf-8")

        dest = tmp_path / "built" / ".gitconfig"
        dest.parent.mkdir()

        home = tmp_path / "home"
        home.mkdir()

        _merge_gitconfig(base, {"acme": org1_path}, dest, home)

        content = dest.read_text(encoding="utf-8")
        assert "[user]" in content
        assert "[include]" in content
        assert "path = ~/.gitconfig.d/acme" in content

        # Verify the org file was copied.
        assert (home / ".gitconfig.d" / "acme").exists()

    def test_gitconfig_multiple_orgs(self, tmp_path: Path) -> None:
        base = tmp_path / ".gitconfig"
        base.write_text("[user]\n    name = Test\n", encoding="utf-8")

        org_paths: dict[str, Path] = {}
        for org_name in ("alpha", "beta"):
            p = tmp_path / org_name / ".gitconfig"
            p.parent.mkdir()
            p.write_text(f"[{org_name}]\n    key = val\n", encoding="utf-8")
            org_paths[org_name] = p

        dest = tmp_path / "built" / ".gitconfig"
        dest.parent.mkdir()

        home = tmp_path / "home"
        home.mkdir()

        _merge_gitconfig(base, org_paths, dest, home)

        content = dest.read_text(encoding="utf-8")
        assert "path = ~/.gitconfig.d/alpha" in content
        assert "path = ~/.gitconfig.d/beta" in content


class TestMergeJson:
    """Tests for _merge_json."""

    def test_deep_merge(self, tmp_path: Path) -> None:
        base = tmp_path / "base.json"
        base.write_text(json.dumps({"a": 1, "nested": {"x": 10, "y": 20}}), encoding="utf-8")

        org = tmp_path / "org.json"
        org.write_text(json.dumps({"b": 2, "nested": {"y": 99, "z": 30}}), encoding="utf-8")

        dest = tmp_path / "merged.json"

        _merge_json(base, org, dest)

        result = json.loads(dest.read_text(encoding="utf-8"))
        assert result["a"] == 1
        assert result["b"] == 2
        assert result["nested"]["x"] == 10
        assert result["nested"]["y"] == 99  # org wins
        assert result["nested"]["z"] == 30

    def test_no_base(self, tmp_path: Path) -> None:
        base = tmp_path / "nonexistent.json"

        org = tmp_path / "org.json"
        org.write_text(json.dumps({"key": "value"}), encoding="utf-8")

        dest = tmp_path / "merged.json"

        _merge_json(base, org, dest)

        result = json.loads(dest.read_text(encoding="utf-8"))
        assert result == {"key": "value"}

    def test_malformed_json_raises(self, tmp_path: Path) -> None:
        base = tmp_path / "base.json"
        base.write_text(json.dumps({"a": 1}), encoding="utf-8")

        org = tmp_path / "org.json"
        org.write_text("{not valid json!!!", encoding="utf-8")

        dest = tmp_path / "merged.json"

        with pytest.raises(LoadoutBuildError, match=str(org)):
            _merge_json(base, org, dest)


class TestMergeYaml:
    """Tests for _merge_yaml."""

    def test_deep_merge(self, tmp_path: Path) -> None:
        base = tmp_path / "base.yaml"
        base.write_text(yaml.dump({"a": 1, "nested": {"x": 10, "y": 20}}), encoding="utf-8")

        org = tmp_path / "org.yaml"
        org.write_text(yaml.dump({"b": 2, "nested": {"y": 99, "z": 30}}), encoding="utf-8")

        dest = tmp_path / "merged.yaml"

        _merge_yaml(base, org, dest)

        result = yaml.safe_load(dest.read_text(encoding="utf-8"))
        assert result["a"] == 1
        assert result["b"] == 2
        assert result["nested"]["x"] == 10
        assert result["nested"]["y"] == 99
        assert result["nested"]["z"] == 30

    def test_no_base(self, tmp_path: Path) -> None:
        base = tmp_path / "nonexistent.yaml"

        org = tmp_path / "org.yaml"
        org.write_text(yaml.dump({"key": "value"}), encoding="utf-8")

        dest = tmp_path / "merged.yaml"

        _merge_yaml(base, org, dest)

        result = yaml.safe_load(dest.read_text(encoding="utf-8"))
        assert result == {"key": "value"}

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        base = tmp_path / "base.yaml"
        base.write_text(yaml.dump({"a": 1}), encoding="utf-8")

        org = tmp_path / "org.yaml"
        org.write_text(":\n  - :\n    bad:: yaml::: {{{\n", encoding="utf-8")

        dest = tmp_path / "merged.yaml"

        with pytest.raises(LoadoutBuildError, match=str(org)):
            _merge_yaml(base, org, dest)

    def test_yaml_to_none_treated_as_empty(self, tmp_path: Path) -> None:
        base = tmp_path / "base.yaml"
        base.write_text(yaml.dump({"a": 1, "nested": {"x": 10}}), encoding="utf-8")

        org = tmp_path / "org.yaml"
        org.write_text("---\n", encoding="utf-8")

        dest = tmp_path / "merged.yaml"

        _merge_yaml(base, org, dest)

        result = yaml.safe_load(dest.read_text(encoding="utf-8"))
        assert result["a"] == 1
        assert result["nested"]["x"] == 10


def _setup_dotfiles(tmp_path: Path, orgs: list[str]) -> LoadoutConfig:
    """Create a temp directory structure with base and org dotfiles."""
    config = LoadoutConfig(user="testuser", orgs=orgs, base_dir=tmp_path)

    # Create base dotfiles.
    base_dir = config.dotfiles_dir / "dotfiles" / "base"
    base_dir.mkdir(parents=True)

    (base_dir / ".zshrc").write_text("# base zshrc\n", encoding="utf-8")
    (base_dir / ".gitconfig").write_text("[user]\n    name = Base\n", encoding="utf-8")
    (base_dir / "settings.json").write_text(
        json.dumps({"editor": "vim", "theme": "dark"}), encoding="utf-8"
    )
    (base_dir / "config.yaml").write_text(
        yaml.dump({"level": 1, "opts": {"a": True}}), encoding="utf-8"
    )
    (base_dir / ".vimrc").write_text("set number\n", encoding="utf-8")

    # Create org dotfiles.
    for org in orgs:
        org_dir = config.dotfiles_private_dir / "dotfiles" / "orgs" / org
        org_dir.mkdir(parents=True)

        (org_dir / ".zshrc").write_text(f"# {org} zshrc\n", encoding="utf-8")
        (org_dir / ".gitconfig").write_text(f"[core]\n    org = {org}\n", encoding="utf-8")
        (org_dir / "settings.json").write_text(
            json.dumps({"theme": "light", "org": org}), encoding="utf-8"
        )
        (org_dir / "config.yaml").write_text(yaml.dump({"opts": {"b": False}}), encoding="utf-8")
        (org_dir / ".vimrc").write_text(f'" {org} vimrc\n', encoding="utf-8")

    return config


class TestBuildDotfiles:
    """Integration tests for build_dotfiles."""

    def test_full_build(self, tmp_path: Path) -> None:
        config = _setup_dotfiles(tmp_path, ["acme"])

        build_dotfiles(config)

        # Verify files were installed to home directory.
        assert (tmp_path / ".zshrc").exists()
        assert (tmp_path / ".gitconfig").exists()
        assert (tmp_path / "settings.json").exists()
        assert (tmp_path / "config.yaml").exists()
        assert (tmp_path / ".vimrc").exists()

        # Verify concat strategy.
        zshrc = (tmp_path / ".zshrc").read_text(encoding="utf-8")
        assert "# base zshrc" in zshrc
        assert "# acme zshrc" in zshrc
        assert "# --- overlay:" in zshrc

        # Verify gitconfig includes.
        gitconfig = (tmp_path / ".gitconfig").read_text(encoding="utf-8")
        assert "[user]" in gitconfig
        assert "[include]" in gitconfig
        assert "path = ~/.gitconfig.d/acme" in gitconfig

        # Verify JSON deep merge.
        json_data = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
        assert json_data["editor"] == "vim"  # from base
        assert json_data["theme"] == "light"  # org wins
        assert json_data["org"] == "acme"

        # Verify YAML deep merge.
        yaml_data = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        assert yaml_data["level"] == 1  # from base
        assert yaml_data["opts"]["a"] is True  # from base
        assert yaml_data["opts"]["b"] is False  # from org

        # Verify replace strategy.
        vimrc = (tmp_path / ".vimrc").read_text(encoding="utf-8")
        assert "acme vimrc" in vimrc
        assert "set number" not in vimrc

    def test_dry_run_does_not_modify(self, tmp_path: Path) -> None:
        config = _setup_dotfiles(tmp_path, ["acme"])

        build_dotfiles(config, dry_run=True)

        # build_dir should not exist after dry run.
        assert not config.build_dir.exists()
        # No dotfiles installed.
        assert not (tmp_path / ".zshrc").exists()

    def test_build_no_orgs(self, tmp_path: Path) -> None:
        config = _setup_dotfiles(tmp_path, [])

        build_dotfiles(config)

        # Base files should be installed directly.
        assert (tmp_path / ".zshrc").exists()
        zshrc = (tmp_path / ".zshrc").read_text(encoding="utf-8")
        assert "# base zshrc" in zshrc
        assert "# --- overlay:" not in zshrc

    def test_build_multiple_orgs(self, tmp_path: Path) -> None:
        config = _setup_dotfiles(tmp_path, ["alpha", "beta"])

        build_dotfiles(config)

        # Both org includes should appear in gitconfig.
        gitconfig = (tmp_path / ".gitconfig").read_text(encoding="utf-8")
        assert "path = ~/.gitconfig.d/alpha" in gitconfig
        assert "path = ~/.gitconfig.d/beta" in gitconfig

        # Concat should show both orgs.
        zshrc = (tmp_path / ".zshrc").read_text(encoding="utf-8")
        assert "# alpha zshrc" in zshrc
        assert "# beta zshrc" in zshrc

    def test_build_clears_previous(self, tmp_path: Path) -> None:
        config = _setup_dotfiles(tmp_path, ["acme"])

        # Create a stale file in build_dir.
        config.build_dir.mkdir(parents=True)
        stale = config.build_dir / ".stale"
        stale.write_text("old", encoding="utf-8")

        build_dotfiles(config)

        # Stale file should be gone.
        assert not (config.build_dir / ".stale").exists()

    def test_build_creates_backup(self, tmp_path: Path) -> None:
        """Build should back up existing home files before overwriting."""
        config = _setup_dotfiles(tmp_path, ["acme"])

        # Pre-create a file that will be overwritten.
        existing = tmp_path / ".zshrc"
        existing.write_text("original content\n", encoding="utf-8")

        build_dotfiles(config)

        # A backup should exist in the backups directory.
        backup_dir = config.dotfiles_dir / "backups"
        assert backup_dir.exists()
        backups = list(backup_dir.glob(".zshrc.*"))
        assert len(backups) >= 1
        assert backups[0].read_text(encoding="utf-8") == "original content\n"

    def test_build_no_backup_for_new_files(self, tmp_path: Path) -> None:
        """Build should not create backups for files that don't exist yet."""
        config = _setup_dotfiles(tmp_path, ["acme"])

        build_dotfiles(config)

        backup_dir = config.dotfiles_dir / "backups"
        # No backups for brand new installs.
        if backup_dir.exists():
            assert len(list(backup_dir.iterdir())) == 0


class TestBackupFile:
    """Tests for _backup_file helper."""

    def test_backup_existing_file(self, tmp_path: Path) -> None:
        src = tmp_path / "myfile"
        src.write_text("hello", encoding="utf-8")
        backup_dir = tmp_path / "backups"

        _backup_file(src, backup_dir)

        assert backup_dir.exists()
        backups = list(backup_dir.glob("myfile.*"))
        assert len(backups) == 1
        assert backups[0].read_text(encoding="utf-8") == "hello"

    def test_no_backup_for_missing_file(self, tmp_path: Path) -> None:
        src = tmp_path / "nonexistent"
        backup_dir = tmp_path / "backups"

        _backup_file(src, backup_dir)

        assert not backup_dir.exists()


class TestAtomicBuildFailure:
    """Tests for atomic build cleanup on failure."""

    def test_temp_dir_cleaned_on_build_failure(self, tmp_path: Path) -> None:
        """If _build_into raises, temp dir is cleaned and build_dir is untouched."""
        config = _setup_dotfiles(tmp_path, ["acme"])

        # Pre-populate build_dir so we can verify it survives.
        config.build_dir.mkdir(parents=True)
        sentinel = config.build_dir / ".sentinel"
        sentinel.write_text("original", encoding="utf-8")

        with (
            patch("loadout.build._build_into", side_effect=RuntimeError("boom")),
            pytest.raises(RuntimeError, match="boom"),
        ):
            build_dotfiles(config)

        # build_dir should still have the original sentinel.
        assert sentinel.exists()
        assert sentinel.read_text(encoding="utf-8") == "original"

        # No leftover temp dirs.
        temp_dirs = list(config.dotfiles_dir.glob("loadout-build-*"))
        assert temp_dirs == []


class TestAppendZshrcDropIns:
    """Tests for _append_zshrc_drop_ins helper."""

    def test_appends_drop_in_sourcing(self, tmp_path: Path) -> None:
        """Should append .zshrc.d/ and .zshrc.local sourcing to .zshrc."""
        zshrc = tmp_path / ".zshrc"
        zshrc.write_text("# base config\nexport FOO=1\n", encoding="utf-8")

        _append_zshrc_drop_ins(tmp_path)

        content = zshrc.read_text(encoding="utf-8")
        assert "zshrc.d" in content
        assert "zshrc.local" in content
        assert "export FOO=1" in content

    def test_skips_when_already_present(self, tmp_path: Path) -> None:
        """Should not duplicate sourcing if sentinel comment is already present."""
        original = "# base config\n# --- loadout: drop-in sourcing ---\n"
        zshrc = tmp_path / ".zshrc"
        zshrc.write_text(original, encoding="utf-8")

        _append_zshrc_drop_ins(tmp_path)

        content = zshrc.read_text(encoding="utf-8")
        assert content == original

    def test_skips_when_no_zshrc(self, tmp_path: Path) -> None:
        """Should do nothing if .zshrc doesn't exist."""
        _append_zshrc_drop_ins(tmp_path)
        assert not (tmp_path / ".zshrc").exists()


class TestBuildDotfilesDropIns:
    """Integration test: build_dotfiles appends drop-in sourcing."""

    def test_full_build_includes_drop_ins(self, tmp_path: Path) -> None:
        config = _setup_dotfiles(tmp_path, ["acme"])

        build_dotfiles(config)

        zshrc = (tmp_path / ".zshrc").read_text(encoding="utf-8")
        assert "# base zshrc" in zshrc
        assert "# acme zshrc" in zshrc
        assert ".zshrc.d" in zshrc
        assert ".zshrc.local" in zshrc
