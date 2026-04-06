# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.display module."""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import pytest

from loadout import ui
from loadout.config import LoadoutConfig
from loadout.display import (
    apply_display_profile,
    detect_external_display,
    generate_launch_agent_plist,
    get_display_scripts,
    is_macos,
)

# ---------------------------------------------------------------------------
# is_macos
# ---------------------------------------------------------------------------


def test_is_macos_on_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    assert is_macos() is True


def test_is_macos_on_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Linux")
    assert is_macos() is False


# ---------------------------------------------------------------------------
# detect_external_display
# ---------------------------------------------------------------------------

SINGLE_DISPLAY_OUTPUT = """\
Graphics/Displays:

    Apple M1 Pro:

      Chipset Model: Apple M1 Pro
      Type: GPU
      Bus: Built-In
      Total Number of Cores: 16
      Displays:
        Built-in Liquid Retina XDR Display:
          Display Type: Built-In Retina LCD
          Resolution: 3456 x 2234 Retina
"""

MULTI_DISPLAY_OUTPUT = """\
Graphics/Displays:

    Apple M1 Pro:

      Chipset Model: Apple M1 Pro
      Displays:
        Built-in Liquid Retina XDR Display:
          Display Type: Built-In Retina LCD
          Resolution: 3456 x 2234 Retina
        LG HDR 4K:
          Resolution: 3840 x 2160 (2160p/4K UHD)
"""


def test_detect_external_display_single(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("loadout.display.is_macos", lambda: True)
    fake_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=SINGLE_DISPLAY_OUTPUT, stderr=""
    )
    with patch("loadout.display.runner.run", return_value=fake_result):
        assert detect_external_display() is False


def test_detect_external_display_multiple(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("loadout.display.is_macos", lambda: True)
    fake_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=MULTI_DISPLAY_OUTPUT, stderr=""
    )
    with patch("loadout.display.runner.run", return_value=fake_result):
        assert detect_external_display() is True


def test_detect_external_display_not_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("loadout.display.is_macos", lambda: False)
    assert detect_external_display() is False


# ---------------------------------------------------------------------------
# get_display_scripts
# ---------------------------------------------------------------------------


@pytest.fixture()
def macos_dir(tmp_path: Path) -> Path:
    """Create a fake dotfiles macos directory with scripts."""
    macos = tmp_path / ".dotfiles" / "macos"
    macos.mkdir(parents=True)
    (macos / "defaults-base.sh").write_text("#!/bin/bash\n")
    (macos / "defaults-desktop.sh").write_text("#!/bin/bash\n")
    (macos / "defaults-laptop-solo.sh").write_text("#!/bin/bash\n")
    return macos


def test_get_display_scripts_connected(macos_dir: Path, tmp_path: Path) -> None:
    config = LoadoutConfig(base_dir=tmp_path)
    scripts = get_display_scripts(config, "connected")
    names = [s.name for s in scripts]
    assert "defaults-base.sh" in names
    assert "defaults-desktop.sh" in names
    assert len(scripts) == 2


def test_get_display_scripts_connected_laptop_fallback(tmp_path: Path) -> None:
    macos = tmp_path / ".dotfiles" / "macos"
    macos.mkdir(parents=True)
    (macos / "defaults-base.sh").write_text("#!/bin/bash\n")
    (macos / "defaults-laptop-connected.sh").write_text("#!/bin/bash\n")

    config = LoadoutConfig(base_dir=tmp_path)
    scripts = get_display_scripts(config, "connected")
    names = [s.name for s in scripts]
    assert "defaults-base.sh" in names
    assert "defaults-laptop-connected.sh" in names
    assert len(scripts) == 2


def test_get_display_scripts_solo(macos_dir: Path, tmp_path: Path) -> None:
    config = LoadoutConfig(base_dir=tmp_path)
    scripts = get_display_scripts(config, "solo")
    names = [s.name for s in scripts]
    assert "defaults-base.sh" in names
    assert "defaults-laptop-solo.sh" in names
    assert len(scripts) == 2


def test_get_display_scripts_empty_dir(tmp_path: Path) -> None:
    macos = tmp_path / ".dotfiles" / "macos"
    macos.mkdir(parents=True)
    config = LoadoutConfig(base_dir=tmp_path)
    scripts = get_display_scripts(config, "connected")
    assert scripts == []


# ---------------------------------------------------------------------------
# apply_display_profile
# ---------------------------------------------------------------------------


def test_apply_display_profile_runs_scripts(
    macos_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = LoadoutConfig(base_dir=tmp_path)
    run_calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("loadout.display.runner.run", side_effect=fake_run):
        apply_display_profile(config, mode="connected", dry_run=False)

    # Should have run base + desktop
    assert len(run_calls) == 2
    assert "defaults-base.sh" in run_calls[0][-1]
    assert "defaults-desktop.sh" in run_calls[1][-1]


def test_apply_display_profile_solo(
    macos_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = LoadoutConfig(base_dir=tmp_path)
    run_calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("loadout.display.runner.run", side_effect=fake_run):
        apply_display_profile(config, mode="solo", dry_run=False)

    assert len(run_calls) == 2
    assert "defaults-base.sh" in run_calls[0][-1]
    assert "defaults-laptop-solo.sh" in run_calls[1][-1]


def test_apply_display_profile_noop_non_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("loadout.display.is_macos", lambda: False)
    config = LoadoutConfig()
    # mode=None triggers the non-macOS skip path
    with patch("loadout.display.runner.run") as mock_run:
        apply_display_profile(config, mode=None, dry_run=False)
    mock_run.assert_not_called()


def test_apply_display_profile_explicit_mode_non_macos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When mode is explicitly set, it should still run even on non-macOS."""
    monkeypatch.setattr("loadout.display.is_macos", lambda: False)
    macos = tmp_path / ".dotfiles" / "macos"
    macos.mkdir(parents=True)
    (macos / "defaults-base.sh").write_text("#!/bin/bash\n")
    (macos / "defaults-laptop-solo.sh").write_text("#!/bin/bash\n")
    config = LoadoutConfig(base_dir=tmp_path)

    run_calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("loadout.display.runner.run", side_effect=fake_run):
        apply_display_profile(config, mode="solo", dry_run=False)

    assert len(run_calls) == 2


def test_apply_display_profile_non_macos_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit mode on non-macOS emits a platform warning."""
    monkeypatch.setattr("loadout.display.is_macos", lambda: False)
    macos = tmp_path / ".dotfiles" / "macos"
    macos.mkdir(parents=True)
    (macos / "defaults-base.sh").write_text("#!/bin/bash\n")
    (macos / "defaults-laptop-solo.sh").write_text("#!/bin/bash\n")
    config = LoadoutConfig(base_dir=tmp_path)

    status_calls: list[tuple[str, ...]] = []
    original_status_line = ui.status_line

    def capture_status(*args: str) -> None:
        status_calls.append(args)
        original_status_line(*args)

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with (
        patch("loadout.display.runner.run", side_effect=fake_run),
        patch("loadout.display.ui.status_line", side_effect=capture_status),
    ):
        apply_display_profile(config, mode="solo", dry_run=False)

    warnings = [c for c in status_calls if len(c) >= 3 and "macOS scripts may not work" in c[2]]
    assert len(warnings) == 1


# ---------------------------------------------------------------------------
# generate_launch_agent_plist
# ---------------------------------------------------------------------------


def test_apply_display_profile_auto_detect(
    macos_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When mode is None on macOS with external display, should resolve to 'connected'."""
    monkeypatch.setattr("loadout.display.is_macos", lambda: True)
    monkeypatch.setattr("loadout.display.detect_external_display", lambda: True)
    config = LoadoutConfig(base_dir=tmp_path)

    run_calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("loadout.display.runner.run", side_effect=fake_run):
        apply_display_profile(config, mode=None, dry_run=False)

    # Should have resolved to "connected" mode and run base + desktop scripts.
    assert len(run_calls) == 2
    assert "defaults-base.sh" in run_calls[0][-1]
    assert "defaults-desktop.sh" in run_calls[1][-1]


def test_apply_display_profile_dry_run(
    macos_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When dry_run is True, runner.run should be called with dry_run=True."""
    config = LoadoutConfig(base_dir=tmp_path)

    run_kwargs: list[dict[str, object]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_kwargs.append(dict(kwargs))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("loadout.display.runner.run", side_effect=fake_run):
        apply_display_profile(config, mode="connected", dry_run=True)

    assert len(run_kwargs) == 2
    for kw in run_kwargs:
        assert kw.get("dry_run") is True


def test_generate_launch_agent_plist_valid_xml(tmp_path: Path) -> None:
    config = LoadoutConfig(base_dir=tmp_path)
    plist = generate_launch_agent_plist(config)

    # Should be parseable XML
    root = ET.fromstring(plist)
    assert root.tag == "plist"


def test_generate_launch_agent_plist_contains_expected_paths(tmp_path: Path) -> None:
    config = LoadoutConfig(base_dir=tmp_path)
    with patch("loadout.display.shutil.which", return_value="/usr/local/bin/loadout"):
        plist = generate_launch_agent_plist(config)

    assert "com.oakensoul.loadout.display" in plist
    assert "/usr/local/bin/loadout" in plist
    assert "display" in plist
    assert str(config.dotfiles_dir / "logs" / "display.log") in plist
    assert str(config.dotfiles_dir / "logs" / "display.err") in plist


def test_generate_launch_agent_plist_falls_back_to_bare_name(tmp_path: Path) -> None:
    """When shutil.which cannot find loadout, fall back to bare 'loadout'."""
    config = LoadoutConfig(base_dir=tmp_path)
    with patch("loadout.display.shutil.which", return_value=None):
        plist = generate_launch_agent_plist(config)

    assert "<string>loadout</string>" in plist


def test_generate_plist_no_mode_argument(tmp_path: Path) -> None:
    """ProgramArguments should contain the resolved loadout path and 'display', not a mode."""
    config = LoadoutConfig(base_dir=tmp_path)
    with patch("loadout.display.shutil.which", return_value="/usr/local/bin/loadout"):
        plist = generate_launch_agent_plist(config)

    root = ET.fromstring(plist)
    # Find ProgramArguments array.
    dict_elem = root.find("dict")
    assert dict_elem is not None
    keys = list(dict_elem.iter("key"))
    program_args_key = None
    for key in keys:
        if key.text == "ProgramArguments":
            program_args_key = key
            break
    assert program_args_key is not None

    # The array element follows the key.
    children = list(dict_elem)
    key_idx = children.index(program_args_key)
    array_elem = children[key_idx + 1]
    assert array_elem.tag == "array"

    strings = [s.text for s in array_elem.findall("string")]
    assert strings == ["/usr/local/bin/loadout", "display"]
    assert "connected" not in strings
    assert "solo" not in strings
