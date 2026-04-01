# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Non-Homebrew global package installation."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from loadout.config import LoadoutConfig
from loadout.exceptions import LoadoutConfigError
from loadout.runner import run
from loadout.ui import run_step, section_header, status_line, verbose_line


def ensure_claude_code(*, dry_run: bool = False) -> None:
    """Install Claude Code CLI if not already present."""
    if shutil.which("claude") is not None:
        status_line("[green]✓[/green]", "Claude Code", "already installed")
        return
    run(
        [
            "bash",
            "-c",
            "curl -fsSL https://claude.ai/install.sh | bash",
        ],
        dry_run=dry_run,
    )


def ensure_devbox(*, dry_run: bool = False) -> None:
    """Install devbox CLI if not already present."""
    if shutil.which("devbox") is not None:
        status_line("[green]✓[/green]", "devbox CLI", "already installed")
        return
    # Not on PyPI — try local install, warn if unavailable
    result = run(["pip3", "install", "oakensoul-devbox"], dry_run=dry_run, check=False)
    if not dry_run and result.returncode != 0:
        status_line(
            "[yellow]![/yellow]",
            "devbox CLI",
            "not available via pip — install from source:"
            " pip3 install ~/Developer/oakensoul/devbox",
        )


def ensure_canvas(*, dry_run: bool = False) -> None:
    """Install canvas CLI if not already present."""
    if shutil.which("canvas") is not None:
        status_line("[green]✓[/green]", "canvas CLI", "already installed")
        return
    # Not on PyPI — try local install, warn if unavailable
    result = run(["pip3", "install", "oakensoul-canvas"], dry_run=dry_run, check=False)
    if not dry_run and result.returncode != 0:
        status_line(
            "[yellow]![/yellow]",
            "canvas CLI",
            "not available via pip — install from source:"
            " pip3 install ~/Developer/oakensoul/canvas",
        )


def ensure_nvm_node(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Install NVM and Node LTS if not already present."""
    nvm_dir = config.home / ".nvm"
    nvm_version = config.nvm_version
    if nvm_dir.exists() and shutil.which("node") is not None:
        status_line("[green]✓[/green]", "NVM + Node", "already installed")
        return

    if not nvm_dir.exists():
        if not re.match(r"^\d+\.\d+\.\d+$", nvm_version):
            raise LoadoutConfigError(
                f"Invalid nvm_version {nvm_version!r}: must be in X.Y.Z format"
            )
        run(
            [
                "bash",
                "-c",
                "curl --fail --proto =https -o-"
                f" https://raw.githubusercontent.com/nvm-sh/nvm/v{nvm_version}/install.sh"
                " | bash",
            ],
            dry_run=dry_run,
        )

    if shutil.which("node") is None:
        run(
            [
                "bash",
                "-c",
                'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] '
                '&& . "$NVM_DIR/nvm.sh" && nvm install --lts',
            ],
            dry_run=dry_run,
        )


def ensure_pyenv_python(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Install pyenv and latest stable Python if not already present."""
    if shutil.which("pyenv") is None:
        status_line("[yellow]![/yellow]", "pyenv", "not found — install via Homebrew first")
        return

    result = run(["pyenv", "versions", "--bare"], capture=True, check=False)
    installed = result.stdout.strip()
    if installed:
        status_line("[green]✓[/green]", "pyenv Python", "already installed")
        return

    run(["pyenv", "install", "--skip-existing", config.pyenv_version], dry_run=dry_run)


def install_npm_globals(packages: list[str], *, dry_run: bool = False) -> None:
    """Install global npm packages."""
    for package in packages:
        result = run(
            ["npm", "list", "-g", "--depth=0", package],
            capture=True,
            check=False,
        )
        if result.returncode == 0 and package in result.stdout:
            status_line("[green]✓[/green]", f"npm: {package}", "already installed")
            continue
        run(["npm", "install", "-g", package], dry_run=dry_run, interactive=True)


def install_pip_globals(packages: list[str], *, dry_run: bool = False) -> None:
    """Install global pip packages."""
    for package in packages:
        result = run(
            ["pip", "show", package],
            capture=True,
            check=False,
        )
        if result.returncode == 0:
            status_line("[green]✓[/green]", f"pip: {package}", "already installed")
            continue
        run(["pip", "install", "--user", package], dry_run=dry_run, interactive=True)


def _run_globals_script(script: Path, *, dry_run: bool = False) -> None:
    """Run a globals shell script if it exists."""
    if not script.exists():
        verbose_line(f"Globals script not found: {script}")
        return
    run(["bash", "-euo", "pipefail", str(script)], dry_run=dry_run, interactive=True)


def _install_org_globals_scripts(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Install per-org globals scripts into ~/.zshrc.d/ for shell sourcing."""
    zshrc_d = config.home / ".zshrc.d"
    for org in config.orgs:
        src = config.dotfiles_private_dir / "globals" / "orgs" / f"globals.{org}.sh"
        if not src.exists():
            verbose_line(f"Org globals script not found: {src}")
            continue
        dest = zshrc_d / f"globals.{org}.sh"
        if dry_run:
            verbose_line(f"[DRY-RUN] Would copy {src} -> {dest}")
            continue
        zshrc_d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        status_line("[green]✓[/green]", f"globals.{org}.sh", f"installed to {zshrc_d}")


def _read_package_list(path: Path) -> list[str]:
    """Read a package list file (one package per line), ignoring blanks and comments."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def install_globals(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Install all non-Homebrew global packages."""
    section_header("Non-Homebrew Globals")

    run_step(
        "Ensure NVM + Node",
        lambda: ensure_nvm_node(config, dry_run=dry_run),
        interactive=True,
    )
    run_step(
        "Ensure Claude Code CLI",
        lambda: ensure_claude_code(dry_run=dry_run),
        interactive=True,
    )
    run_step("Ensure devbox CLI", lambda: ensure_devbox(dry_run=dry_run))
    run_step("Ensure canvas CLI", lambda: ensure_canvas(dry_run=dry_run))
    run_step(
        "Ensure pyenv Python",
        lambda: ensure_pyenv_python(config, dry_run=dry_run),
        interactive=True,
    )

    run_step(
        "Run base globals script",
        lambda: _run_globals_script(
            config.dotfiles_dir / "globals" / "globals.base.sh", dry_run=dry_run
        ),
        interactive=True,
    )
    run_step(
        "Run private base globals script",
        lambda: _run_globals_script(
            config.dotfiles_private_dir / "globals" / "base" / "globals.sh",
            dry_run=dry_run,
        ),
        interactive=True,
    )
    run_step(
        "Install org globals scripts",
        lambda: _install_org_globals_scripts(config, dry_run=dry_run),
    )

    # Collect npm and pip packages from private base and org config files
    npm_packages: list[str] = []
    pip_packages: list[str] = []

    private_base_dir = config.dotfiles_private_dir / "dotfiles" / "base"
    npm_packages.extend(_read_package_list(private_base_dir / "npm-globals.txt"))
    pip_packages.extend(_read_package_list(private_base_dir / "pip-globals.txt"))

    for org in config.orgs:
        org_dir = config.dotfiles_private_dir / "dotfiles" / "orgs" / org
        npm_packages.extend(_read_package_list(org_dir / "npm-globals.txt"))
        pip_packages.extend(_read_package_list(org_dir / "pip-globals.txt"))

    npm_packages = list(dict.fromkeys(npm_packages))
    pip_packages = list(dict.fromkeys(pip_packages))

    if npm_packages:
        run_step(
            "Install npm globals",
            lambda: install_npm_globals(npm_packages, dry_run=dry_run),
        )

    if pip_packages:
        run_step(
            "Install pip globals",
            lambda: install_pip_globals(pip_packages, dry_run=dry_run),
        )
