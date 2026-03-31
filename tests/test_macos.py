# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.macos — macOS defaults with hardware-appropriate scripts."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from loadout.config import LoadoutConfig
from loadout.macos import apply_macos_defaults, detect_machine_type

# ---------------------------------------------------------------------------
# detect_machine_type
# ---------------------------------------------------------------------------


def test_detect_machine_type_desktop() -> None:
    """A non-MacBook model should be detected as desktop."""
    fake_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="Mac14,13\n", stderr="")
    with patch("loadout.macos.subprocess.run", return_value=fake_result):
        assert detect_machine_type() == "desktop"


def test_detect_machine_type_laptop() -> None:
    """A MacBook model should be detected as laptop."""
    fake_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="MacBookPro18,1\n", stderr=""
    )
    with patch("loadout.macos.subprocess.run", return_value=fake_result):
        assert detect_machine_type() == "laptop"


def test_detect_machine_type_unknown() -> None:
    """When sysctl fails, machine type should be unknown."""
    with patch(
        "loadout.macos.subprocess.run",
        side_effect=FileNotFoundError("sysctl not found"),
    ):
        assert detect_machine_type() == "unknown"


# ---------------------------------------------------------------------------
# apply_macos_defaults
# ---------------------------------------------------------------------------


def _fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    """Return a successful CompletedProcess for any command."""
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")


def _make_macos_dir(tmp_path: Path, scripts: list[str]) -> Path:
    """Create a fake macos directory with the given script files."""
    macos = tmp_path / ".dotfiles" / "macos"
    macos.mkdir(parents=True)
    for name in scripts:
        (macos / name).write_text("#!/bin/bash\necho test\n")
    return macos


def test_apply_defaults_desktop(tmp_path: Path) -> None:
    """Desktop machine should run base + desktop scripts."""
    _make_macos_dir(tmp_path, ["defaults-base.sh", "defaults-desktop.sh"])
    config = LoadoutConfig(base_dir=tmp_path)

    run_calls: list[list[str]] = []

    def capture_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with (
        patch("loadout.macos.runner.run", side_effect=capture_run),
        patch("loadout.macos.detect_machine_type", return_value="desktop"),
    ):
        apply_macos_defaults(config)

    assert len(run_calls) == 2
    assert "defaults-base.sh" in run_calls[0][-1]
    assert "defaults-desktop.sh" in run_calls[1][-1]


def test_apply_defaults_laptop(tmp_path: Path) -> None:
    """Laptop machine should run base + laptop-solo script when no external display."""
    _make_macos_dir(
        tmp_path,
        ["defaults-base.sh", "defaults-laptop-solo.sh", "defaults-laptop-connected.sh"],
    )
    config = LoadoutConfig(base_dir=tmp_path)

    run_calls: list[list[str]] = []

    def capture_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with (
        patch("loadout.macos.runner.run", side_effect=capture_run),
        patch("loadout.macos.detect_machine_type", return_value="laptop"),
        patch("loadout.macos.detect_external_display", return_value=False),
    ):
        apply_macos_defaults(config)

    assert len(run_calls) == 2
    assert "defaults-base.sh" in run_calls[0][-1]
    assert "defaults-laptop-solo.sh" in run_calls[1][-1]


def test_apply_defaults_laptop_connected(tmp_path: Path) -> None:
    """Laptop with external display should run defaults-laptop-connected.sh."""
    _make_macos_dir(
        tmp_path,
        ["defaults-base.sh", "defaults-laptop-connected.sh"],
    )
    config = LoadoutConfig(base_dir=tmp_path)

    run_calls: list[list[str]] = []

    def capture_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with (
        patch("loadout.macos.runner.run", side_effect=capture_run),
        patch("loadout.macos.detect_machine_type", return_value="laptop"),
        patch("loadout.macos.detect_external_display", return_value=True),
    ):
        apply_macos_defaults(config)

    assert len(run_calls) == 2
    assert "defaults-base.sh" in run_calls[0][-1]
    assert "defaults-laptop-connected.sh" in run_calls[1][-1]


def test_apply_defaults_missing_scripts(tmp_path: Path) -> None:
    """Missing scripts should be skipped gracefully without errors."""
    # Create macos dir with NO scripts
    macos = tmp_path / ".dotfiles" / "macos"
    macos.mkdir(parents=True)
    config = LoadoutConfig(base_dir=tmp_path)

    with (
        patch("loadout.macos.runner.run", side_effect=_fake_run) as mock_run,
        patch("loadout.macos.detect_machine_type", return_value="desktop"),
    ):
        apply_macos_defaults(config)

    mock_run.assert_not_called()


def test_apply_defaults_dry_run(tmp_path: Path) -> None:
    """In dry-run mode, runner.run should receive dry_run=True."""
    _make_macos_dir(tmp_path, ["defaults-base.sh", "defaults-desktop.sh"])
    config = LoadoutConfig(base_dir=tmp_path)

    run_kwargs: list[dict[str, object]] = []

    def capture_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_kwargs.append(dict(kwargs))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with (
        patch("loadout.macos.runner.run", side_effect=capture_run),
        patch("loadout.macos.detect_machine_type", return_value="desktop"),
    ):
        apply_macos_defaults(config, dry_run=True)

    assert len(run_kwargs) == 2
    for kw in run_kwargs:
        assert kw.get("dry_run") is True


def test_apply_defaults_unknown_machine(tmp_path: Path) -> None:
    """Unknown machine type should skip hardware-specific scripts with warning."""
    _make_macos_dir(tmp_path, ["defaults-base.sh", "defaults-desktop.sh"])
    config = LoadoutConfig(base_dir=tmp_path)

    run_calls: list[list[str]] = []

    def capture_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with (
        patch("loadout.macos.runner.run", side_effect=capture_run),
        patch("loadout.macos.detect_machine_type", return_value="unknown"),
    ):
        apply_macos_defaults(config)

    # Only base script should run
    assert len(run_calls) == 1
    assert "defaults-base.sh" in run_calls[0][-1]


def test_scripts_invoked_with_euo_pipefail(tmp_path: Path) -> None:
    """All script invocations must use 'bash -euo pipefail'."""
    _make_macos_dir(tmp_path, ["defaults-base.sh", "defaults-desktop.sh"])
    config = LoadoutConfig(base_dir=tmp_path)

    run_calls: list[list[str]] = []

    def capture_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with (
        patch("loadout.macos.runner.run", side_effect=capture_run),
        patch("loadout.macos.detect_machine_type", return_value="desktop"),
    ):
        apply_macos_defaults(config)

    assert len(run_calls) == 2
    for call in run_calls:
        assert call[0] == "bash"
        assert call[1] == "-euo"
        assert call[2] == "pipefail"
