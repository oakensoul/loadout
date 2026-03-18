"""Update and upgrade commands."""

from __future__ import annotations

import shutil

from loadout.build import build_dotfiles
from loadout.config import LoadoutConfig
from loadout.globals import install_globals
from loadout.runner import run
from loadout.ui import run_step, section_header, status_line


def run_update(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Pull latest dotfile sources, rebuild configuration, and install globals.

    Steps:
    1. Pull dotfiles repo (fast-forward only).
    2. Pull dotfiles-private repo (fast-forward only).
    3. Rebuild merged dotfiles.
    4. Run ``brew update`` and ``brew bundle``.
    5. Install non-Homebrew globals.
    """
    section_header("Update")

    # Pull dotfiles
    dotfiles_dir = config.dotfiles_dir
    if dotfiles_dir.exists():
        run_step(
            "Pull dotfiles",
            lambda: run(
                ["git", "-C", str(dotfiles_dir), "pull", "--ff-only"],
                dry_run=dry_run,
            ),
        )
    else:
        status_line("[yellow]![/yellow]", "dotfiles", f"{dotfiles_dir} not found — skipping")

    # Pull dotfiles-private
    private_dir = config.dotfiles_private_dir
    if private_dir.exists():
        run_step(
            "Pull dotfiles-private",
            lambda: run(
                ["git", "-C", str(private_dir), "pull", "--ff-only"],
                dry_run=dry_run,
            ),
        )
    else:
        status_line(
            "[yellow]![/yellow]",
            "dotfiles-private",
            f"{private_dir} not found — skipping",
        )

    # Build dotfiles
    run_step("Build dotfiles", lambda: build_dotfiles(config, dry_run=dry_run))

    # Brew update + bundle
    if shutil.which("brew") is not None:
        run_step(
            "Brew update",
            lambda: run(["brew", "update"], dry_run=dry_run),
        )
        brewfile = dotfiles_dir / "Brewfile"
        if brewfile.exists():
            run_step(
                "Brew bundle",
                lambda: run(
                    ["brew", "bundle", f"--file={brewfile}"],
                    dry_run=dry_run,
                ),
            )
        else:
            status_line("[yellow]![/yellow]", "Brewfile", "not found — skipping bundle")
    else:
        status_line("[yellow]![/yellow]", "brew", "not found — skipping Homebrew steps")

    # Install globals
    run_step("Install globals", lambda: install_globals(config, dry_run=dry_run))


def run_upgrade(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Run a full update then upgrade Homebrew packages.

    Calls :func:`run_update` first, then runs ``brew upgrade``.
    """
    run_update(config, dry_run=dry_run)

    section_header("Upgrade")

    if shutil.which("brew") is not None:
        run_step(
            "Brew upgrade",
            lambda: run(["brew", "upgrade"], dry_run=dry_run),
        )
    else:
        status_line("[yellow]![/yellow]", "brew", "not found — skipping brew upgrade")
