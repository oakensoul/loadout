"""Health check engine for loadout."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum

from loadout import ui
from loadout.config import LoadoutConfig


class CheckStatus(Enum):
    """Status of a health check."""

    OK = "ok"
    WARN = "warn"
    ERROR = "error"


@dataclass
class CheckResult:
    """Result of a single health check."""

    status: CheckStatus
    label: str
    detail: str


def check_homebrew() -> CheckResult:
    """Verify that Homebrew (brew) is on PATH."""
    if shutil.which("brew"):
        return CheckResult(status=CheckStatus.OK, label="Homebrew", detail="brew found on PATH")
    return CheckResult(status=CheckStatus.ERROR, label="Homebrew", detail="brew not found on PATH")


def check_git() -> CheckResult:
    """Verify that git is on PATH and report its version."""
    if not shutil.which("git"):
        return CheckResult(status=CheckStatus.ERROR, label="Git", detail="git not found on PATH")
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True, check=True)
        version = result.stdout.strip()
        return CheckResult(status=CheckStatus.OK, label="Git", detail=version)
    except subprocess.CalledProcessError:
        return CheckResult(
            status=CheckStatus.WARN, label="Git", detail="git found but version check failed"
        )


def check_nvm_node() -> CheckResult:
    """Check if node is available and report its version."""
    if not shutil.which("node"):
        return CheckResult(
            status=CheckStatus.WARN, label="Node.js", detail="node not found on PATH"
        )
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True)
        version = result.stdout.strip()
        return CheckResult(status=CheckStatus.OK, label="Node.js", detail=version)
    except subprocess.CalledProcessError:
        return CheckResult(
            status=CheckStatus.WARN, label="Node.js", detail="node found but version check failed"
        )


def check_pyenv_python() -> CheckResult:
    """Check if python3 is available and report its version."""
    if not shutil.which("python3"):
        return CheckResult(
            status=CheckStatus.WARN, label="Python", detail="python3 not found on PATH"
        )
    try:
        result = subprocess.run(
            ["python3", "--version"], capture_output=True, text=True, check=True
        )
        version = result.stdout.strip()
        return CheckResult(status=CheckStatus.OK, label="Python", detail=version)
    except subprocess.CalledProcessError:
        return CheckResult(
            status=CheckStatus.WARN,
            label="Python",
            detail="python3 found but version check failed",
        )


def check_onepassword() -> CheckResult:
    """Check if the 1Password CLI (op) is on PATH."""
    if shutil.which("op"):
        return CheckResult(status=CheckStatus.OK, label="1Password CLI", detail="op found on PATH")
    return CheckResult(
        status=CheckStatus.WARN, label="1Password CLI", detail="op not found on PATH"
    )


def check_github_ssh() -> CheckResult:
    """Check GitHub SSH authentication.

    A successful auth returns exit code 1 with 'Hi <username>' in stderr.
    """
    try:
        result = subprocess.run(
            ["ssh", "-T", "git@github.com"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode == 1 and "Hi " in result.stderr:
            detail = result.stderr.strip()
            return CheckResult(status=CheckStatus.OK, label="GitHub SSH", detail=detail)
        return CheckResult(
            status=CheckStatus.WARN,
            label="GitHub SSH",
            detail="SSH connection did not return expected greeting",
        )
    except subprocess.TimeoutExpired:
        return CheckResult(status=CheckStatus.WARN, label="GitHub SSH", detail="SSH timed out")
    except FileNotFoundError:
        return CheckResult(
            status=CheckStatus.ERROR, label="GitHub SSH", detail="ssh not found on PATH"
        )


def check_claude_code() -> CheckResult:
    """Check if the Claude Code CLI (claude) is on PATH."""
    if shutil.which("claude"):
        return CheckResult(
            status=CheckStatus.OK, label="Claude Code", detail="claude found on PATH"
        )
    return CheckResult(
        status=CheckStatus.WARN, label="Claude Code", detail="claude not found on PATH"
    )


def check_brewfile(config: LoadoutConfig) -> CheckResult:
    """Check if a Brewfile exists in the dotfiles directory."""
    brewfile = config.dotfiles_dir / "Brewfile"
    if brewfile.exists():
        return CheckResult(status=CheckStatus.OK, label="Brewfile", detail=f"found at {brewfile}")
    return CheckResult(status=CheckStatus.WARN, label="Brewfile", detail=f"not found at {brewfile}")


def run_checks(config: LoadoutConfig) -> list[CheckResult]:
    """Run all health checks and return results."""
    return [
        check_homebrew(),
        check_git(),
        check_nvm_node(),
        check_pyenv_python(),
        check_onepassword(),
        check_github_ssh(),
        check_claude_code(),
        check_brewfile(config),
    ]


_STATUS_ICONS: dict[CheckStatus, str] = {
    CheckStatus.OK: "[green]✓[/green]",
    CheckStatus.WARN: "[yellow]![/yellow]",
    CheckStatus.ERROR: "[red]✗[/red]",
}


def render_checks(results: list[CheckResult]) -> None:
    """Render check results using ui helpers."""
    for result in results:
        icon = _STATUS_ICONS[result.status]
        ui.status_line(icon, result.label, result.detail)
