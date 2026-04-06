# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""macOS defaults management with hardware-appropriate script selection."""

from __future__ import annotations

import subprocess

from loadout import runner, ui
from loadout.config import LoadoutConfig
from loadout.display import detect_external_display


def detect_machine_type() -> str:
    """Detect whether the Mac is a laptop or desktop.

    Runs ``sysctl -n hw.model`` and checks the model identifier.

    Returns:
        ``"laptop"`` for MacBook models, ``"desktop"`` for other Macs,
        or ``"unknown"`` if sysctl fails (e.g. on Linux).
    """
    try:
        result = subprocess.run(  # noqa: S603, S607 — known macOS binary
            ["sysctl", "-n", "hw.model"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
        )
        model = result.stdout.strip()
        if model.startswith("MacBook"):
            return "laptop"
        return "desktop"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _run_private_macos_defaults(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Run private macOS defaults scripts from dotfiles-private.

    Looks for:
    - ``{dotfiles_private_dir}/macos/base/set-defaults.sh`` (private base)
    - ``{dotfiles_private_dir}/macos/orgs/{org}/set-defaults.sh`` for each org

    Missing scripts are silently skipped.
    """
    private_base_script = config.dotfiles_private_dir / "macos" / "base" / "set-defaults.sh"
    if private_base_script.exists():
        ui.status_line("[dim]\u25b6[/dim]", "Running", "private base set-defaults.sh")
        runner.run(
            ["bash", "-euo", "pipefail", str(private_base_script)],
            dry_run=dry_run,
            interactive=True,
        )

    for org in config.orgs:
        org_script = config.dotfiles_private_dir / "macos" / "orgs" / org / "set-defaults.sh"
        if org_script.exists():
            ui.status_line("[dim]\u25b6[/dim]", "Running", f"org {org} set-defaults.sh")
            runner.run(
                ["bash", "-euo", "pipefail", str(org_script)],
                dry_run=dry_run,
                interactive=True,
            )


def apply_macos_defaults(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Apply macOS defaults scripts based on hardware type.

    Always runs ``defaults-base.sh`` if present, then selects the
    appropriate hardware-specific script:

    - **desktop** -> ``defaults-desktop.sh``
    - **laptop** -> ``defaults-laptop-connected.sh`` or
      ``defaults-laptop-solo.sh`` depending on external display
    - **unknown** -> skipped with a warning

    Then runs private macOS defaults from dotfiles-private (base and per-org).

    Missing scripts are skipped gracefully.
    """
    macos_dir = config.dotfiles_dir / "macos"

    ui.section_header("macOS Defaults")

    # Always run base script if it exists
    base_script = macos_dir / "defaults-base.sh"
    if base_script.exists():
        ui.status_line("[dim]\u25b6[/dim]", "Running", "defaults-base.sh")
        runner.run(
            ["bash", "-euo", "pipefail", str(base_script)],
            dry_run=dry_run,
            interactive=True,
        )
    else:
        ui.status_line("[yellow]![/yellow]", "macOS defaults", "defaults-base.sh not found")

    # Detect machine type and run appropriate script
    machine = detect_machine_type()
    ui.status_line("[green]\u2713[/green]", "Machine type", machine)

    if machine == "desktop":
        desktop_script = macos_dir / "defaults-desktop.sh"
        if desktop_script.exists():
            ui.status_line("[dim]\u25b6[/dim]", "Running", "defaults-desktop.sh")
            runner.run(
                ["bash", "-euo", "pipefail", str(desktop_script)],
                dry_run=dry_run,
                interactive=True,
            )
        else:
            ui.status_line(
                "[yellow]![/yellow]", "macOS defaults", "defaults-desktop.sh not found — skipping"
            )
    elif machine == "laptop":
        has_external = detect_external_display()
        script_name = "defaults-laptop-connected.sh" if has_external else "defaults-laptop-solo.sh"
        laptop_script = macos_dir / script_name
        if laptop_script.exists():
            ui.status_line("[dim]\u25b6[/dim]", "Running", script_name)
            runner.run(
                ["bash", "-euo", "pipefail", str(laptop_script)],
                dry_run=dry_run,
                interactive=True,
            )
        else:
            ui.status_line(
                "[yellow]![/yellow]", "macOS defaults", f"{script_name} not found — skipping"
            )
    else:
        ui.status_line(
            "[yellow]![/yellow]",
            "macOS defaults",
            "unknown machine type — skipping hardware-specific defaults",
        )

    # Run private macOS defaults (base and per-org)
    _run_private_macos_defaults(config, dry_run=dry_run)
