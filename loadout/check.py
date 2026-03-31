# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Health check engine for loadout."""

from __future__ import annotations

import json
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


def check_brewfile_fragments(config: LoadoutConfig) -> list[CheckResult]:
    """Check Brewfile fragments in the dotfiles directory structure."""
    results: list[CheckResult] = []
    base = config.dotfiles_dir / "brewfiles" / "Brewfile.base"
    has_new_structure = base.parent.exists()

    if has_new_structure:
        if base.exists():
            results.append(
                CheckResult(status=CheckStatus.OK, label="Brewfile.base", detail=f"found at {base}")
            )
        else:
            results.append(
                CheckResult(
                    status=CheckStatus.ERROR,
                    label="Brewfile.base",
                    detail=f"not found at {base}",
                )
            )

        private_base = config.dotfiles_private_dir / "brewfiles" / "base" / "Brewfile"
        if private_base.exists():
            results.append(
                CheckResult(
                    status=CheckStatus.OK,
                    label="Brewfile (private base)",
                    detail=f"found at {private_base}",
                )
            )

        for org in config.orgs:
            org_brewfile = config.dotfiles_private_dir / "brewfiles" / "orgs" / f"Brewfile.{org}"
            if org_brewfile.exists():
                results.append(
                    CheckResult(
                        status=CheckStatus.OK,
                        label=f"Brewfile.{org}",
                        detail=f"found at {org_brewfile}",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        status=CheckStatus.WARN,
                        label=f"Brewfile.{org}",
                        detail=f"not found at {org_brewfile}",
                    )
                )
    else:
        # Fall back to old-style single Brewfile
        brewfile = config.dotfiles_dir / "Brewfile"
        if brewfile.exists():
            results.append(
                CheckResult(status=CheckStatus.OK, label="Brewfile", detail=f"found at {brewfile}")
            )
        else:
            results.append(
                CheckResult(
                    status=CheckStatus.WARN,
                    label="Brewfile",
                    detail=f"not found at {brewfile}",
                )
            )

    return results


def check_globals_scripts(config: LoadoutConfig) -> list[CheckResult]:
    """Check globals shell scripts in the dotfiles directory structure."""
    results: list[CheckResult] = []
    base_script = config.dotfiles_dir / "globals" / "globals.base.sh"
    if base_script.exists():
        results.append(
            CheckResult(
                status=CheckStatus.OK,
                label="globals.base.sh",
                detail=f"found at {base_script}",
            )
        )
    else:
        results.append(
            CheckResult(
                status=CheckStatus.WARN,
                label="globals.base.sh",
                detail=f"not found at {base_script}",
            )
        )

    private_base_script = config.dotfiles_private_dir / "globals" / "base" / "globals.sh"
    if private_base_script.exists():
        results.append(
            CheckResult(
                status=CheckStatus.OK,
                label="globals.sh (private base)",
                detail=f"found at {private_base_script}",
            )
        )

    for org in config.orgs:
        org_script = config.dotfiles_private_dir / "globals" / "orgs" / f"globals.{org}.sh"
        if org_script.exists():
            results.append(
                CheckResult(
                    status=CheckStatus.OK,
                    label=f"globals.{org}.sh",
                    detail=f"found at {org_script}",
                )
            )
        else:
            results.append(
                CheckResult(
                    status=CheckStatus.WARN,
                    label=f"globals.{org}.sh",
                    detail=f"not found at {org_script}",
                )
            )

    return results


def check_claude_config(config: LoadoutConfig) -> CheckResult:
    """Check if Claude MCP config exists and is valid JSON."""
    mcp_json = config.claude_dir / "mcp.json"
    if not mcp_json.exists():
        return CheckResult(
            status=CheckStatus.WARN, label="Claude mcp.json", detail=f"not found at {mcp_json}"
        )
    try:
        json.loads(mcp_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return CheckResult(
            status=CheckStatus.WARN,
            label="Claude mcp.json",
            detail=f"malformed JSON at {mcp_json}",
        )
    return CheckResult(
        status=CheckStatus.OK, label="Claude mcp.json", detail=f"valid at {mcp_json}"
    )


def run_checks(config: LoadoutConfig) -> list[CheckResult]:
    """Run all health checks and return results."""
    results = [
        check_homebrew(),
        check_git(),
        check_nvm_node(),
        check_pyenv_python(),
        check_onepassword(),
        check_github_ssh(),
        check_claude_code(),
    ]
    results.extend(check_brewfile_fragments(config))
    results.extend(check_globals_scripts(config))
    results.append(check_claude_config(config))
    return results


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
