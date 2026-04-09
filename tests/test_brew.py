# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.brew module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from loadout.brew import _assemble_brewfile, brew_bundle
from loadout.config import LoadoutConfig


def _make_config(tmp_path: Path, orgs: list[str] | None = None) -> LoadoutConfig:
    """Create a LoadoutConfig rooted in *tmp_path*."""
    return LoadoutConfig(user="testuser", orgs=orgs or [], base_dir=tmp_path)


class TestAssembleBrewfile:
    """Tests for _assemble_brewfile fragment discovery."""

    def test_assemble_brewfile_base_only(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        base = config.dotfiles_dir / "brewfiles" / "Brewfile.base"
        base.parent.mkdir(parents=True)
        base.write_text("brew 'git'\n", encoding="utf-8")

        result = _assemble_brewfile(config)

        assert result == [base]

    def test_assemble_brewfile_with_orgs(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path, orgs=["acme", "initech"])

        base = config.dotfiles_dir / "brewfiles" / "Brewfile.base"
        base.parent.mkdir(parents=True)
        base.write_text("brew 'git'\n", encoding="utf-8")

        for org in ("acme", "initech"):
            org_file = config.dotfiles_private_dir / "brewfiles" / "orgs" / f"Brewfile.{org}"
            org_file.parent.mkdir(parents=True, exist_ok=True)
            org_file.write_text(f"brew '{org}-tool'\n", encoding="utf-8")

        result = _assemble_brewfile(config)

        assert len(result) == 3
        assert result[0] == base
        assert result[1].name == "Brewfile.acme"
        assert result[2].name == "Brewfile.initech"

    def test_assemble_brewfile_with_private_base(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)

        base = config.dotfiles_dir / "brewfiles" / "Brewfile.base"
        base.parent.mkdir(parents=True)
        base.write_text("brew 'git'\n", encoding="utf-8")

        private_base = config.dotfiles_private_dir / "brewfiles" / "base" / "Brewfile"
        private_base.parent.mkdir(parents=True)
        private_base.write_text("brew 'private-tool'\n", encoding="utf-8")

        result = _assemble_brewfile(config)

        assert len(result) == 2
        assert result[0] == base
        assert result[1] == private_base

    def test_assemble_brewfile_missing_org(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path, orgs=["acme", "ghost"])

        base = config.dotfiles_dir / "brewfiles" / "Brewfile.base"
        base.parent.mkdir(parents=True)
        base.write_text("brew 'git'\n", encoding="utf-8")

        acme = config.dotfiles_private_dir / "brewfiles" / "orgs" / "Brewfile.acme"
        acme.parent.mkdir(parents=True, exist_ok=True)
        acme.write_text("brew 'acme-tool'\n", encoding="utf-8")

        result = _assemble_brewfile(config)

        assert len(result) == 2
        assert result[0] == base
        assert result[1].name == "Brewfile.acme"


class TestBrewBundle:
    """Tests for brew_bundle orchestration."""

    @patch("loadout.brew.run")
    @patch("loadout.brew.shutil.which", return_value="/opt/homebrew/bin/brew")
    def test_brew_bundle_assembles_and_runs(
        self,
        _mock_which: object,
        mock_run: object,
        tmp_path: Path,
    ) -> None:
        config = _make_config(tmp_path, orgs=["acme"])

        base = config.dotfiles_dir / "brewfiles" / "Brewfile.base"
        base.parent.mkdir(parents=True)
        base.write_text("brew 'git'\n", encoding="utf-8")

        acme = config.dotfiles_private_dir / "brewfiles" / "orgs" / "Brewfile.acme"
        acme.parent.mkdir(parents=True, exist_ok=True)
        acme.write_text("brew 'acme-tool'\n", encoding="utf-8")

        brew_bundle(config, dry_run=False)

        calls = mock_run.call_args_list  # type: ignore[union-attr]
        assert len(calls) == 2

        # First call: brew update
        assert calls[0][0][0] == ["brew", "update"]

        # Second call: brew bundle --file=<tmp>
        bundle_cmd = calls[1][0][0]
        assert bundle_cmd[0:2] == ["brew", "bundle"]
        assert bundle_cmd[2].startswith("--file=")

        # Temp file should be cleaned up
        tmp_file = Path(bundle_cmd[2].split("=", 1)[1])
        assert not tmp_file.exists()

    @patch("loadout.brew.run")
    @patch("loadout.brew.shutil.which", return_value="/opt/homebrew/bin/brew")
    def test_brew_bundle_fallback_single_brewfile(
        self,
        _mock_which: object,
        mock_run: object,
        tmp_path: Path,
    ) -> None:
        config = _make_config(tmp_path)

        # No fragments, but old-style Brewfile exists
        brewfile = config.dotfiles_dir / "Brewfile"
        brewfile.parent.mkdir(parents=True)
        brewfile.write_text("brew 'git'\n", encoding="utf-8")

        brew_bundle(config, dry_run=False)

        calls = mock_run.call_args_list  # type: ignore[union-attr]
        assert len(calls) == 2
        assert calls[0][0][0] == ["brew", "update"]

        bundle_cmd = calls[1][0][0]
        assert f"--file={brewfile}" in bundle_cmd

    @patch("loadout.brew.run")
    @patch("loadout.brew.shutil.which", return_value="/opt/homebrew/bin/brew")
    def test_brew_bundle_no_brewfile(
        self,
        _mock_which: object,
        mock_run: object,
        tmp_path: Path,
    ) -> None:
        config = _make_config(tmp_path)
        # Ensure dotfiles_dir exists but has no Brewfile or fragments
        config.dotfiles_dir.mkdir(parents=True)

        brew_bundle(config, dry_run=False)

        # No brew commands should have been run
        mock_run.assert_not_called()  # type: ignore[union-attr]

    @patch("loadout.brew.run")
    @patch("loadout.brew.shutil.which", return_value=None)
    def test_brew_bundle_no_homebrew(
        self,
        _mock_which: object,
        mock_run: object,
        tmp_path: Path,
    ) -> None:
        config = _make_config(tmp_path)

        brew_bundle(config, dry_run=False)

        mock_run.assert_not_called()  # type: ignore[union-attr]

    @patch("loadout.brew.run")
    @patch("loadout.brew.brew_prefix_is_owned", return_value=False)
    @patch("loadout.brew.detect_brew_bin", return_value="/opt/homebrew/bin")
    @patch("loadout.brew.shutil.which", return_value="/opt/homebrew/bin/brew")
    def test_brew_bundle_skips_unowned_prefix(
        self,
        _mock_which: object,
        _mock_detect: object,
        _mock_owned: object,
        mock_run: object,
        tmp_path: Path,
    ) -> None:
        config = _make_config(tmp_path)

        base = config.dotfiles_dir / "brewfiles" / "Brewfile.base"
        base.parent.mkdir(parents=True)
        base.write_text("brew 'git'\n", encoding="utf-8")

        brew_bundle(config, dry_run=False)

        mock_run.assert_not_called()  # type: ignore[union-attr]
