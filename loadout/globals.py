"""Non-Homebrew global package installation."""

from __future__ import annotations

import shutil
from pathlib import Path

from loadout.config import LoadoutConfig
from loadout.runner import run
from loadout.ui import run_step, section_header, status_line

_NVM_VERSION = "0.40.1"


def ensure_claude_code(*, dry_run: bool = False) -> None:
    """Install Claude Code CLI if not already present."""
    if shutil.which("claude") is not None:
        status_line("[green]✓[/green]", "Claude Code", "already installed")
        return
    run(["npm", "install", "-g", "@anthropic-ai/claude-code"], dry_run=dry_run)


def ensure_nvm_node(*, dry_run: bool = False) -> None:
    """Install NVM and Node LTS if not already present."""
    nvm_dir = Path.home() / ".nvm"
    if nvm_dir.exists() and shutil.which("node") is not None:
        status_line("[green]✓[/green]", "NVM + Node", "already installed")
        return

    if not nvm_dir.exists():
        run(
            [
                "bash",
                "-c",
                "curl --fail -o-"
                f" https://raw.githubusercontent.com/nvm-sh/nvm/v{_NVM_VERSION}/install.sh"
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


def ensure_pyenv_python(*, dry_run: bool = False) -> None:
    """Install pyenv and latest stable Python if not already present."""
    if shutil.which("pyenv") is None:
        status_line("[yellow]![/yellow]", "pyenv", "not found — install via Homebrew first")
        return

    result = run(["pyenv", "versions", "--bare"], capture=True, check=False)
    installed = result.stdout.strip()
    if installed:
        status_line("[green]✓[/green]", "pyenv Python", "already installed")
        return

    run(["pyenv", "install", "--skip-existing", "3"], dry_run=dry_run)


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
        run(["npm", "install", "-g", package], dry_run=dry_run)


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
        run(["pip", "install", package], dry_run=dry_run)


def _read_package_list(path: Path) -> list[str]:
    """Read a package list file (one package per line), ignoring blanks and comments."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def install_globals(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Install all non-Homebrew global packages."""
    section_header("Non-Homebrew Globals")

    run_step("Ensure NVM + Node", lambda: ensure_nvm_node(dry_run=dry_run))
    run_step("Ensure Claude Code CLI", lambda: ensure_claude_code(dry_run=dry_run))
    run_step("Ensure pyenv Python", lambda: ensure_pyenv_python(dry_run=dry_run))

    # Collect npm and pip packages from org config files
    npm_packages: list[str] = []
    pip_packages: list[str] = []

    for org in config.orgs:
        org_dir = config.dotfiles_private_dir / "dotfiles" / "orgs" / org
        npm_packages.extend(_read_package_list(org_dir / "npm-globals.txt"))
        pip_packages.extend(_read_package_list(org_dir / "pip-globals.txt"))

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
