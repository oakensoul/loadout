"""Shell command runner with dry-run support."""

from __future__ import annotations

import shlex
import subprocess

from loadout.ui import err_console


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
        check: If True, raise CalledProcessError on non-zero exit.
        capture: If True, capture stdout and stderr.
        dry_run: If True, log the command but do not execute it.

    Returns:
        A CompletedProcess instance. In dry-run mode, returns a synthetic
        result with returncode=0 and empty stdout/stderr.
    """
    if dry_run:
        display_cmd = shlex.join(cmd)
        err_console.print(f"[bold yellow][DRY-RUN][/bold yellow] {display_cmd}")
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
    )
