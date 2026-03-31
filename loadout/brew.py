# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Shared Homebrew helpers."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from loadout.config import LoadoutConfig
from loadout.runner import run
from loadout.ui import status_line, verbose_line


def _assemble_brewfile(config: LoadoutConfig) -> list[Path]:
    """Discover Brewfile fragments to concatenate.

    Looks for:
    - ``{dotfiles_dir}/brewfiles/Brewfile.base`` (always included if present)
    - ``{dotfiles_private_dir}/brewfiles/Brewfile.private`` (private base, if present)
    - ``{dotfiles_private_dir}/brewfiles/orgs/Brewfile.{org}`` for each org

    Missing files are silently skipped.

    Returns:
        Ordered list of existing fragment paths.
    """
    fragments: list[Path] = []

    base = config.dotfiles_dir / "brewfiles" / "Brewfile.base"
    if base.exists():
        fragments.append(base)

    private_base = config.dotfiles_private_dir / "brewfiles" / "Brewfile.private"
    if private_base.exists():
        fragments.append(private_base)

    for org in config.orgs:
        org_file = config.dotfiles_private_dir / "brewfiles" / "orgs" / f"Brewfile.{org}"
        if org_file.exists():
            fragments.append(org_file)
        else:
            verbose_line(f"Brewfile fragment not found, skipping: {org_file}")

    return fragments


def brew_bundle(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Run brew update and brew bundle if Homebrew and a Brewfile are available.

    Assembles Brewfile fragments from the dotfiles and dotfiles-private repos
    into a temporary file, then runs ``brew bundle --file=<temp> --no-lock``.
    Falls back to a single ``Brewfile`` in the dotfiles root if no fragments
    are found.  Gracefully skips when brew is not installed or no Brewfile
    exists.
    """
    if shutil.which("brew") is None:
        status_line("[yellow]![/yellow]", "Homebrew", "not found — skipping")
        return

    fragments = _assemble_brewfile(config)

    if fragments:
        for frag in fragments:
            verbose_line(f"Brewfile fragment: {frag}")

        tmp_path: Path | None = None
        try:
            # Write concatenated Brewfile to a temp file
            fd, tmp_str = tempfile.mkstemp(prefix="loadout-brewfile-", suffix=".rb")
            tmp_path = Path(tmp_str)
            with open(fd, "w", encoding="utf-8") as fh:
                for frag in fragments:
                    fh.write(f"# --- {frag.name} ---\n")
                    fh.write(frag.read_text(encoding="utf-8"))
                    fh.write("\n")

            run(["brew", "update"], dry_run=dry_run)
            run(
                ["brew", "bundle", f"--file={tmp_path}", "--no-lock"],
                dry_run=dry_run,
            )
        finally:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink()
        return

    # Fallback: old-style single Brewfile
    brewfile = config.dotfiles_dir / "Brewfile"
    if brewfile.exists():
        verbose_line(f"Using legacy Brewfile: {brewfile}")
        run(["brew", "update"], dry_run=dry_run)
        run(["brew", "bundle", f"--file={brewfile}", "--no-lock"], dry_run=dry_run)
        return

    status_line("[yellow]![/yellow]", "Brewfile", "not found — skipping")
