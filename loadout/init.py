# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Full machine bootstrap flow."""

from __future__ import annotations

import shlex
import shutil
import socket
from pathlib import Path

from loadout import runner, ui
from loadout.brew import brew_bundle
from loadout.build import build_dotfiles
from loadout.claude import build_claude_config
from loadout.config import LoadoutConfig, save_config
from loadout.display import generate_launch_agent_plist, is_macos
from loadout.globals import install_globals
from loadout.macos import apply_macos_defaults


def _clone_repo(
    url: str,
    dest: Path,
    *,
    dry_run: bool = False,
) -> None:
    """Clone a git repo if the destination does not already exist."""
    if dest.exists():
        ui.status_line("[green]\u2713[/green]", str(dest.name), "already exists — skipping clone")
        return
    runner.run(["git", "clone", url, str(dest)], dry_run=dry_run)


def _generate_ssh_key(
    user: str,
    ssh_key_path: Path,
    *,
    dry_run: bool = False,
) -> None:
    """Generate an ed25519 SSH key if one does not already exist."""
    if ssh_key_path.exists():
        ui.status_line("[green]\u2713[/green]", "SSH key", "already exists — skipping keygen")
        return
    ssh_key_path.parent.mkdir(parents=True, exist_ok=True)
    runner.run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-C",
            f"{user}@loadout",
            "-f",
            str(ssh_key_path),
            "-N",
            "",
        ],
        dry_run=dry_run,
    )


def _register_ssh_key_with_github(
    ssh_pub_path: Path,
    *,
    github_token_op_path: str,
    dry_run: bool = False,
) -> None:
    """Register the SSH public key with GitHub via 1Password + gh CLI."""
    if shutil.which("op") is None:
        ui.status_line(
            "[yellow]![/yellow]", "1Password CLI", "not found — skipping SSH key registration"
        )
        return
    if shutil.which("gh") is None:
        ui.status_line(
            "[yellow]![/yellow]", "GitHub CLI", "not found — skipping SSH key registration"
        )
        return

    # Authenticate gh with a token from 1Password via shell pipeline
    safe_path = shlex.quote(github_token_op_path)
    runner.run(
        [
            "bash",
            "-euo",
            "pipefail",
            "-c",
            f"op read {safe_path} | gh auth login --with-token",
        ],
        dry_run=dry_run,
    )

    hostname = socket.gethostname()
    runner.run(
        [
            "gh",
            "ssh-key",
            "add",
            str(ssh_pub_path),
            "--title",
            f"loadout-{hostname}",
        ],
        dry_run=dry_run,
    )


def _switch_remotes_to_ssh(
    user: str,
    repos: list[Path],
    *,
    dry_run: bool = False,
) -> None:
    """Switch git remotes from HTTPS to SSH for the given repos."""
    for repo in repos:
        if not repo.exists():
            continue
        # Strip leading dot: ~/.dotfiles -> "dotfiles" on GitHub
        repo_name = repo.name.lstrip(".")
        runner.run(
            [
                "git",
                "-C",
                str(repo),
                "remote",
                "set-url",
                "origin",
                f"git@github.com:{user}/{repo_name}.git",
            ],
            dry_run=dry_run,
        )


def _setup_launch_agent(
    config: LoadoutConfig,
    *,
    dry_run: bool = False,
) -> None:
    """Write and load the display launch agent plist. Only on macOS."""
    if not is_macos():
        ui.status_line("[dim]\u23ed[/dim]", "Launch agent", "skipped (not macOS)")
        return

    plist_content = generate_launch_agent_plist(config)
    plist_path = config.home / "Library" / "LaunchAgents" / "com.oakensoul.loadout.display.plist"

    if not dry_run:
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_text(plist_content, encoding="utf-8")

    runner.run(["launchctl", "load", str(plist_path)], dry_run=dry_run)


def run_init(
    user: str,
    orgs: list[str],
    *,
    base_dir: Path | None = None,
    dry_run: bool = False,
) -> None:
    """Execute the full machine bootstrap flow.

    This is the 11-step init sequence that sets up a new machine from scratch.
    Steps are fail-fast: if any step raises, subsequent steps are skipped.
    Platform-conditional steps (macOS defaults, launch agent) are no-ops on
    non-macOS platforms.
    """
    config = LoadoutConfig(user=user, orgs=list(orgs), base_dir=base_dir)
    dotfiles_dir = config.dotfiles_dir
    dotfiles_private_dir = config.dotfiles_private_dir
    ssh_key_path = config.home / ".ssh" / "id_ed25519"

    ui.section_header("Machine Bootstrap")

    # 1. Clone dotfiles repos
    def _clone_repos() -> None:
        _clone_repo(
            f"https://github.com/{user}/dotfiles.git",
            dotfiles_dir,
            dry_run=dry_run,
        )
        _clone_repo(
            f"https://github.com/{user}/dotfiles-private.git",
            dotfiles_private_dir,
            dry_run=dry_run,
        )

    ui.run_step("Clone dotfiles repos", _clone_repos)

    # 2. Generate SSH key
    ui.run_step(
        "Generate SSH key",
        lambda: _generate_ssh_key(user, ssh_key_path, dry_run=dry_run),
    )

    # 3. Register SSH key with GitHub
    ui.run_step(
        "Register SSH key with GitHub",
        lambda: _register_ssh_key_with_github(
            ssh_key_path.with_suffix(".pub"),
            github_token_op_path=config.github_token_op_path,
            dry_run=dry_run,
        ),
    )

    # 4. Switch remotes to SSH
    ui.run_step(
        "Switch remotes to SSH",
        lambda: _switch_remotes_to_ssh(
            user,
            [dotfiles_dir, dotfiles_private_dir],
            dry_run=dry_run,
        ),
    )

    # 5. Build dotfiles
    ui.run_step(
        "Build dotfiles",
        lambda: build_dotfiles(config, dry_run=dry_run),
    )

    # 6. Brew bundle
    ui.run_step(
        "Brew bundle",
        lambda: brew_bundle(config, dry_run=dry_run),
    )

    # 7. Install globals
    ui.run_step(
        "Install globals",
        lambda: install_globals(config, dry_run=dry_run),
    )

    # 8. Build Claude config
    ui.run_step(
        "Build Claude config",
        lambda: build_claude_config(config, dry_run=dry_run),
    )

    # 9. Apply macOS defaults
    ui.run_step(
        "Apply macOS defaults",
        lambda: apply_macos_defaults(config, dry_run=dry_run),
    )

    # 10. Set up display launch agent
    ui.run_step(
        "Set up display launch agent",
        lambda: _setup_launch_agent(config, dry_run=dry_run),
    )

    # 11. Save config
    if not dry_run:
        ui.run_step(
            "Save config",
            lambda: save_config(config),
        )
    else:
        ui.status_line("[dim]▶[/dim]", "Save config", "skipped (dry run)")
