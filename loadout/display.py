"""macOS display profile switching."""

from __future__ import annotations

import platform
import textwrap
from pathlib import Path

from loadout import runner, ui
from loadout.config import LoadoutConfig


def is_macos() -> bool:
    """Check if running on macOS."""
    return platform.system() == "Darwin"


def detect_external_display(*, dry_run: bool = False) -> bool:
    """Detect if an external display is connected.

    Uses system_profiler SPDisplaysDataType on macOS.
    Returns False on non-macOS platforms.
    """
    if not is_macos():
        return False

    result = runner.run(
        ["system_profiler", "SPDisplaysDataType"],
        capture=True,
        dry_run=dry_run,
    )
    # Count "Resolution:" lines — each display has one
    resolution_count = sum(1 for line in result.stdout.splitlines() if "Resolution:" in line)
    return resolution_count > 1


def get_display_scripts(config: LoadoutConfig, mode: str) -> list[Path]:
    """Return the list of macOS defaults scripts to apply for the given mode.

    Args:
        config: Loadout configuration
        mode: "connected" or "solo"

    Returns list of script paths (that exist) from dotfiles_dir/macos/:
    - Always: defaults-base.sh
    - connected: defaults-desktop.sh or defaults-laptop-connected.sh
    - solo: defaults-laptop-solo.sh
    """
    macos_dir = config.dotfiles_dir / "macos"
    scripts: list[Path] = []

    base = macos_dir / "defaults-base.sh"
    if base.exists():
        scripts.append(base)

    if mode == "connected":
        desktop = macos_dir / "defaults-desktop.sh"
        laptop_connected = macos_dir / "defaults-laptop-connected.sh"
        if desktop.exists():
            scripts.append(desktop)
        elif laptop_connected.exists():
            scripts.append(laptop_connected)
    elif mode == "solo":
        solo = macos_dir / "defaults-laptop-solo.sh"
        if solo.exists():
            scripts.append(solo)

    return scripts


def apply_display_profile(
    config: LoadoutConfig,
    mode: str | None = None,
    *,
    dry_run: bool = False,
) -> None:
    """Apply the appropriate display profile.

    If mode is None, auto-detect via system_profiler.
    If mode is "connected" or "solo", use that directly.
    Gracefully no-ops on non-macOS platforms.
    """
    if not is_macos() and mode is None:
        ui.status_line("\u23ed\ufe0f", "Display", "skipped (not macOS)")
        return

    if mode is None:
        has_external = detect_external_display(dry_run=dry_run)
        mode = "connected" if has_external else "solo"

    ui.section_header("Display Profile")
    ui.status_line("\U0001f5a5", "Mode", mode)

    scripts = get_display_scripts(config, mode)

    if not scripts:
        ui.status_line("\u26a0\ufe0f", "Display", "no scripts found")
        return

    for script in scripts:
        ui.status_line("\u25b6\ufe0f", "Running", script.name)
        runner.run(["bash", str(script)], dry_run=dry_run)

    ui.status_line("\u2705", "Display", f"profile '{mode}' applied")


def generate_launch_agent_plist(config: LoadoutConfig) -> str:
    """Generate a launchd plist for automatic display profile switching.

    Returns the plist XML as a string.
    """
    loadout_bin = "loadout"
    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" \
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>com.oakensoul.loadout.display</string>
            <key>ProgramArguments</key>
            <array>
                <string>{loadout_bin}</string>
                <string>display</string>
                <string>connected</string>
            </array>
            <key>WatchPaths</key>
            <array>
                <string>/Library/Preferences/com.apple.windowserver.plist</string>
            </array>
            <key>RunAtLoad</key>
            <true/>
            <key>StandardOutPath</key>
            <string>{config.dotfiles_dir}/logs/display.log</string>
            <key>StandardErrorPath</key>
            <string>{config.dotfiles_dir}/logs/display.err</string>
        </dict>
        </plist>
    """)
