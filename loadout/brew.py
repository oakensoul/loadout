"""Shared Homebrew helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from loadout.runner import run
from loadout.ui import status_line


def brew_bundle(dotfiles_dir: Path, *, dry_run: bool = False) -> None:
    """Run brew update and brew bundle if Homebrew and a Brewfile are available.

    Gracefully skips when brew is not installed or no Brewfile exists.
    """
    if shutil.which("brew") is None:
        status_line("[yellow]![/yellow]", "Homebrew", "not found — skipping")
        return

    brewfile = dotfiles_dir / "Brewfile"
    if not brewfile.exists():
        status_line("[yellow]![/yellow]", "Brewfile", "not found — skipping")
        return

    run(["brew", "update"], dry_run=dry_run)
    run(["brew", "bundle", f"--file={brewfile}"], dry_run=dry_run)
