# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Shell command runner with dry-run support."""

from __future__ import annotations

import os
import shlex
import subprocess

from loadout.exceptions import LoadoutCommandError
from loadout.ui import err_console, verbose_line


def run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = False,
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a shell command, optionally in dry-run mode.

    Args:
        cmd: Command to execute as a list of arguments.
        check: If True, raise LoadoutCommandError on non-zero exit.
        capture: If True, capture stdout and stderr.
        dry_run: If True, log the command but do not execute it.

    Returns:
        A CompletedProcess instance. In dry-run mode, returns a synthetic
        result with returncode=0 and empty stdout/stderr.

    Raises:
        LoadoutCommandError: When the command exits non-zero (and check=True)
            or the command binary is not found.
    """
    display_cmd = shlex.join(cmd)

    if dry_run:
        err_console.print(f"[bold yellow][DRY-RUN][/bold yellow] {display_cmd}")
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    verbose_line(f"$ {display_cmd}")

    # Ensure Homebrew's bin directory is on PATH so that brew-installed
    # tools are discoverable by subprocesses (e.g. on macOS).
    env: dict[str, str] | None = None
    if os.path.isfile("/opt/homebrew/bin/brew"):
        brew_bin = "/opt/homebrew/bin"
    elif os.path.isfile("/usr/local/bin/brew"):
        brew_bin = "/usr/local/bin"
    else:
        brew_bin = None

    if brew_bin is not None:
        current_path = os.environ.get("PATH", "")
        if brew_bin not in current_path.split(os.pathsep):
            env = {**os.environ, "PATH": brew_bin + os.pathsep + current_path}

    try:
        result = subprocess.run(  # noqa: S603 — cmd is list-form, no shell=True
            cmd,
            check=check,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
    except FileNotFoundError as exc:
        raise LoadoutCommandError(
            f"Command not found: {cmd[0]}",
            cmd=display_cmd,
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise LoadoutCommandError(
            f"Command failed with exit code {exc.returncode}: {display_cmd}",
            cmd=display_cmd,
            exit_code=exc.returncode,
            stderr=exc.stderr or "",
        ) from exc

    if result.stderr:
        verbose_line(result.stderr.rstrip())

    return result
