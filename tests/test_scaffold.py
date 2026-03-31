# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.scaffold — dotfiles-private repo scaffolding."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from loadout.exceptions import LoadoutError
from loadout.scaffold import _build_context, run_scaffold


def _fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    """Return a successful CompletedProcess for any command."""
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")


# ---------------------------------------------------------------------------
# Successful scaffold
# ---------------------------------------------------------------------------


@patch("loadout.scaffold.shutil.which", return_value="/usr/bin/gh")
@patch("loadout.scaffold.runner.run", side_effect=_fake_run)
def test_scaffold_creates_directory(
    mock_run: MagicMock,
    mock_which: MagicMock,
    tmp_path: Path,
) -> None:
    """Scaffold should call cookiecutter and rename the output directory."""
    expected_output = tmp_path / "testuser-dotfiles-private"

    def fake_cookiecutter(
        template: str,
        no_input: bool = False,
        extra_context: dict[str, str] | None = None,
        output_dir: str = ".",
    ) -> str:
        expected_output.mkdir()
        (expected_output / "README.md").write_text("# test", encoding="utf-8")
        return str(expected_output)

    with patch("loadout.scaffold.run_cookiecutter", side_effect=fake_cookiecutter):
        run_scaffold(
            "testuser",
            ["orgA", "orgB"],
            "Test User",
            "test@example.com",
            template="/fake/template",
            home_dir=tmp_path,
        )

    target = tmp_path / ".dotfiles-private"
    assert target.exists()
    assert (target / "README.md").exists()


# ---------------------------------------------------------------------------
# Abort when target exists
# ---------------------------------------------------------------------------


def test_scaffold_aborts_when_target_exists(tmp_path: Path) -> None:
    """Scaffold should raise LoadoutError if ~/.dotfiles-private exists."""
    (tmp_path / ".dotfiles-private").mkdir()

    with pytest.raises(LoadoutError, match="already exists"):
        run_scaffold(
            "testuser",
            ["org1"],
            "Test User",
            "test@example.com",
            home_dir=tmp_path,
        )


# ---------------------------------------------------------------------------
# Create repo calls gh CLI
# ---------------------------------------------------------------------------


@patch("loadout.scaffold.shutil.which", return_value="/usr/bin/gh")
@patch("loadout.scaffold.runner.run", side_effect=_fake_run)
def test_scaffold_create_repo_calls_gh(
    mock_run: MagicMock,
    mock_which: MagicMock,
    tmp_path: Path,
) -> None:
    """With --create-repo, scaffold should call gh repo create."""
    expected_output = tmp_path / "testuser-dotfiles-private"

    def fake_cookiecutter(
        template: str,
        no_input: bool = False,
        extra_context: dict[str, str] | None = None,
        output_dir: str = ".",
    ) -> str:
        expected_output.mkdir()
        return str(expected_output)

    with patch("loadout.scaffold.run_cookiecutter", side_effect=fake_cookiecutter):
        run_scaffold(
            "testuser",
            ["org1"],
            "Test User",
            "test@example.com",
            template="/fake/template",
            create_repo=True,
            home_dir=tmp_path,
        )

    gh_calls = [c for c in mock_run.call_args_list if "gh" in c.args[0]]
    assert len(gh_calls) == 1
    assert "repo" in gh_calls[0].args[0]
    assert "create" in gh_calls[0].args[0]
    assert "--private" in gh_calls[0].args[0]


# ---------------------------------------------------------------------------
# Dry run does not write files
# ---------------------------------------------------------------------------


def test_scaffold_dry_run_no_files(tmp_path: Path) -> None:
    """Dry run should not create any files."""
    run_scaffold(
        "testuser",
        ["org1"],
        "Test User",
        "test@example.com",
        template="/fake/template",
        dry_run=True,
        home_dir=tmp_path,
    )

    target = tmp_path / ".dotfiles-private"
    assert not target.exists()


# ---------------------------------------------------------------------------
# Multiple orgs are properly handled
# ---------------------------------------------------------------------------


def test_scaffold_multiple_orgs_context() -> None:
    """Multiple orgs should be split into primary + additional."""
    context = _build_context("testuser", ["primary", "second", "third"], "Test", "t@example.com")

    assert context["primary_org"] == "primary"
    assert context["additional_orgs"] == "second,third"
    assert context["github_username"] == "testuser"
    assert context["git_name"] == "Test"
    assert context["git_email"] == "t@example.com"


def test_scaffold_single_org_context() -> None:
    """Single org should have empty additional_orgs."""
    context = _build_context("testuser", ["only"], "Test", "t@example.com")

    assert context["primary_org"] == "only"
    assert context["additional_orgs"] == ""


def test_scaffold_empty_orgs_context() -> None:
    """Empty orgs list should have empty primary and additional."""
    context = _build_context("testuser", [], "Test", "t@example.com")

    assert context["primary_org"] == ""
    assert context["additional_orgs"] == ""


# ---------------------------------------------------------------------------
# Dry run with create-repo does not call gh
# ---------------------------------------------------------------------------


@patch("loadout.scaffold.runner.run", side_effect=_fake_run)
def test_scaffold_dry_run_with_create_repo(
    mock_run: MagicMock,
    tmp_path: Path,
) -> None:
    """Dry run with --create-repo should pass dry_run=True to runner."""
    run_scaffold(
        "testuser",
        ["org1"],
        "Test User",
        "test@example.com",
        template="/fake/template",
        create_repo=True,
        dry_run=True,
        home_dir=tmp_path,
    )

    # runner.run should be called with dry_run=True
    for c in mock_run.call_args_list:
        assert c.kwargs.get("dry_run") is True
