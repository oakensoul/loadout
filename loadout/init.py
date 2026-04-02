# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Full machine bootstrap flow."""

from __future__ import annotations

import json
import os
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
from loadout.secrets import get_provider, load_ssh_key_config
from loadout.ssh import install_ssh_config


def _ensure_xcode_cli_tools(*, dry_run: bool = False) -> None:
    """Ensure Xcode Command Line Tools are installed (macOS only).

    On a fresh Mac, git and other developer tools require the CLI tools.
    Checks via ``xcode-select -p``; if missing, triggers the install and
    waits for completion.
    """
    if not is_macos():
        ui.status_line("[dim]\u23ed[/dim]", "Xcode CLI Tools", "skipped (not macOS)")
        return

    result = runner.run(["xcode-select", "-p"], capture=True, check=False)
    if result.returncode == 0:
        ui.status_line("[green]\u2713[/green]", "Xcode CLI Tools", "already installed")
        return

    if dry_run:
        ui.status_line("[dim]\u25b6[/dim]", "Xcode CLI Tools", "would install (dry run)")
        return

    # xcode-select --install opens a GUI dialog; the touch-file trick
    # allows a headless install via softwareupdate instead.
    runner.run(
        [
            "bash",
            "-euo",
            "pipefail",
            "-c",
            "touch /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress && "
            'PROD=$(softwareupdate -l 2>&1 | grep -B 1 "Command Line Tools" '
            '| grep -o "Command Line Tools.*" | head -1) && '
            'softwareupdate -i "$PROD" --verbose && '
            "rm -f /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress",
        ],
    )


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


def _pub_key_path(private_key_path: Path) -> Path:
    """Derive the public key path from a private key path.

    Handles both extensionless filenames (``id_acme`` → ``id_acme.pub``)
    and filenames with an extension (``id_acme.pem`` → ``id_acme.pem.pub``).
    """
    return Path(str(private_key_path) + ".pub")


def _collect_existing_pub_keys(config: LoadoutConfig) -> list[Path]:
    """Return public key paths that already exist on disk.

    Used in headless mode where key provisioning is skipped but downstream
    steps (SSH config generation, remote switching) still benefit from
    knowing which keys are available.
    """
    _, key_configs = load_ssh_key_config(config.dotfiles_private_dir)
    ssh_dir = config.home / ".ssh"
    pub_keys: list[Path] = []

    if not key_configs:
        pub = ssh_dir / "id_ed25519.pub"
        if pub.exists():
            pub_keys.append(pub)
        return pub_keys

    for key_config in key_configs:
        key_path = ssh_dir / key_config.filename
        pub_path = _pub_key_path(key_path)
        if pub_path.exists():
            pub_keys.append(pub_path)

    return pub_keys


def _provision_ssh_keys(
    config: LoadoutConfig,
    *,
    dry_run: bool = False,
) -> list[Path]:
    """Provision SSH keys from secrets provider or generate new ones.

    When ``dotfiles-private/ssh/keys.toml`` exists, pulls private keys from
    the configured provider, derives public keys, and adds them to the macOS
    keychain.  Falls back to generating a single ed25519 key when no config
    is present.

    Returns a list of public key paths that were provisioned.
    """
    provider_type, key_configs = load_ssh_key_config(config.dotfiles_private_dir)

    if not key_configs:
        # No provider config — fall back to generating a single key
        ssh_key_path = config.home / ".ssh" / "id_ed25519"
        _generate_ssh_key(config.user, ssh_key_path, dry_run=dry_run)
        pub_path = _pub_key_path(ssh_key_path)
        return [pub_path] if pub_path.exists() or dry_run else []

    provider = get_provider(provider_type)
    ssh_dir = config.home / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    pub_keys: list[Path] = []

    for key_config in key_configs:
        key_path = ssh_dir / key_config.filename
        pub_path = _pub_key_path(key_path)

        if key_path.exists():
            ui.status_line(
                "[green]\u2713[/green]", key_config.filename, "already exists \u2014 skipping"
            )
            if pub_path.exists():
                pub_keys.append(pub_path)
            continue

        if dry_run:
            ui.status_line(
                "[dim]\u25b6[/dim]",
                key_config.filename,
                f"would provision from {provider_type} (dry run)",
            )
            pub_keys.append(pub_path)
            continue

        # Pull private key from provider
        ui.status_line(
            "[blue]\u2193[/blue]", key_config.filename, f"pulling from {provider_type}..."
        )
        private_key = provider.read(key_config.secret_path)

        # Write private key with secure permissions (no race condition)
        fd = os.open(str(key_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, private_key.encode())
        finally:
            os.close(fd)

        # Derive public key from private key
        result = runner.run(["ssh-keygen", "-y", "-f", str(key_path)], capture=True)
        pub_path.write_text(result.stdout.strip() + "\n", encoding="utf-8")

        # Add to macOS keychain
        if is_macos():
            runner.run(["ssh-add", "--apple-use-keychain", str(key_path)], check=False)

        ui.status_line(
            "[green]\u2713[/green]", key_config.filename, "provisioned and added to keychain"
        )
        pub_keys.append(pub_path)

    return pub_keys


def _ensure_gh_authenticated(*, dry_run: bool = False) -> bool:
    """Ensure the GitHub CLI is authenticated, prompting if needed.

    Returns True if gh is authenticated, False if it cannot be.
    """
    if shutil.which("gh") is None:
        ui.status_line(
            "[yellow]![/yellow]", "GitHub CLI", "not found — skipping SSH key registration"
        )
        return False

    # Check if already authenticated
    result = runner.run(["gh", "auth", "status"], capture=True, check=False)
    if result.returncode == 0:
        ui.status_line("[green]\u2713[/green]", "GitHub CLI", "already authenticated")
        return True

    if dry_run:
        ui.status_line(
            "[dim]\u25b6[/dim]", "GitHub CLI", "would authenticate via browser (dry run)"
        )
        return True

    # Authenticate via browser OAuth with SSH protocol
    ui.status_line("[blue]\u2193[/blue]", "GitHub CLI", "opening browser for authentication...")
    result = runner.run(
        ["gh", "auth", "login", "--web", "-p", "ssh"],
        check=False,
        interactive=True,
    )
    return result.returncode == 0


def _register_ssh_key_with_github(
    ssh_pub_path: Path,
    *,
    dry_run: bool = False,
) -> None:
    """Register the SSH public key with GitHub via gh CLI."""
    hostname = socket.gethostname()
    # Extract org from key filename for a descriptive title
    key_name = ssh_pub_path.stem  # e.g. "id_ed25519_oakensoul"
    runner.run(
        [
            "gh",
            "ssh-key",
            "add",
            str(ssh_pub_path),
            "--title",
            f"loadout-{hostname}-{key_name}",
        ],
        dry_run=dry_run,
        check=False,  # key may already be registered
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


def _bootstrap_canvas_config(
    config: LoadoutConfig,
    *,
    dry_run: bool = False,
) -> None:
    """Create ~/.canvas/config.json with default org if it doesn't exist."""
    if shutil.which("canvas") is None:
        ui.status_line("[dim]⏭[/dim]", "Canvas config", "skipped (canvas not installed)")
        return

    if not config.orgs:
        ui.status_line("[dim]⏭[/dim]", "Canvas config", "skipped (no orgs configured)")
        return

    canvas_dir = config.home / ".canvas"
    config_path = canvas_dir / "config.json"

    if config_path.exists():
        ui.status_line("[green]✓[/green]", "Canvas config", "already exists")
        return

    if dry_run:
        ui.status_line("[dim]▶[/dim]", "Canvas config", "would create (dry run)")
        return

    canvas_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps({"org": config.orgs[0]}, indent=2) + "\n",
        encoding="utf-8",
    )
    ui.status_line("[green]✓[/green]", "Canvas config", f"created with org={config.orgs[0]}")


def _skip_step(name: str) -> None:
    """Log that a step was skipped due to headless mode."""
    ui.status_line("[dim]\u23ed[/dim]", name, "skipped (headless)")


def run_init(
    user: str,
    orgs: list[str],
    *,
    base_dir: Path | None = None,
    dry_run: bool = False,
    headless: bool = False,
) -> None:
    """Execute the full machine bootstrap flow.

    This is the 12-step init sequence that sets up a new machine from scratch.
    Steps are fail-fast: if any step raises, subsequent steps are skipped.
    Platform-conditional steps (macOS defaults, launch agent) are no-ops on
    non-macOS platforms.

    When *headless* is True, steps requiring interactive input (browser auth,
    1Password biometric, Homebrew, macOS defaults) are skipped.  This is
    intended for non-interactive environments such as devbox SSH accounts
    where keys are pre-copied and packages are managed externally.
    """
    config = LoadoutConfig(user=user, orgs=list(orgs), base_dir=base_dir)
    dotfiles_dir = config.dotfiles_dir
    dotfiles_private_dir = config.dotfiles_private_dir

    ui.section_header("Machine Bootstrap")
    if headless:
        ui.status_line("[blue]i[/blue]", "mode", "headless — interactive steps will be skipped")

    # 1. Ensure Xcode CLI Tools (macOS — needed for git, brew, etc.)
    if headless:
        _skip_step("Ensure Xcode CLI Tools")
    else:
        ui.run_step(
            "Ensure Xcode CLI Tools",
            lambda: _ensure_xcode_cli_tools(dry_run=dry_run),
            interactive=True,
        )

    # 2. Clone dotfiles repos
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

    # 3. Provision SSH keys (from secrets provider or generate)
    if headless:
        _skip_step("Provision SSH keys")
        # Collect any existing public keys so downstream steps can use them.
        # Must run after clone (step 2) since it reads keys.toml from dotfiles-private.
        pub_keys = _collect_existing_pub_keys(config)
    else:
        pub_keys = ui.run_step(
            "Provision SSH keys",
            lambda: _provision_ssh_keys(config, dry_run=dry_run),
            interactive=True,
        )

    # 3b. Generate SSH config from keys.toml
    _, key_configs = load_ssh_key_config(dotfiles_private_dir)
    ui.run_step(
        "Generate SSH config",
        lambda: install_ssh_config(key_configs, config.home, dry_run=dry_run),
    )

    # 4. Register SSH keys with GitHub
    if headless:
        _skip_step("Register SSH keys with GitHub")
    else:

        def _register_all_ssh_keys() -> None:
            if not _ensure_gh_authenticated(dry_run=dry_run):
                return
            for pub_key in pub_keys:
                _register_ssh_key_with_github(pub_key, dry_run=dry_run)

        ui.run_step("Register SSH keys with GitHub", _register_all_ssh_keys, interactive=True)

    # 5. Switch remotes to SSH
    ui.run_step(
        "Switch remotes to SSH",
        lambda: _switch_remotes_to_ssh(
            user,
            [dotfiles_dir, dotfiles_private_dir],
            dry_run=dry_run,
        ),
    )

    # 6. Build dotfiles
    ui.run_step(
        "Build dotfiles",
        lambda: build_dotfiles(config, dry_run=dry_run),
    )

    # 7. Brew bundle
    if headless:
        _skip_step("Brew bundle")
    else:
        ui.run_step(
            "Brew bundle",
            lambda: brew_bundle(config, dry_run=dry_run),
            interactive=True,
        )

    # 8. Install globals
    if headless:
        _skip_step("Install globals")
    else:
        ui.run_step(
            "Install globals",
            lambda: install_globals(config, dry_run=dry_run),
            interactive=True,
        )

    # 9. Build Claude config
    ui.run_step(
        "Build Claude config",
        lambda: build_claude_config(config, dry_run=dry_run),
    )

    # 10. Bootstrap canvas config
    ui.run_step(
        "Bootstrap canvas config",
        lambda: _bootstrap_canvas_config(config, dry_run=dry_run),
    )

    # 11. Apply macOS defaults
    if headless:
        _skip_step("Apply macOS defaults")
    else:
        ui.run_step(
            "Apply macOS defaults",
            lambda: apply_macos_defaults(config, dry_run=dry_run),
            interactive=True,
        )

    # 12. Set up display launch agent
    ui.run_step(
        "Set up display launch agent",
        lambda: _setup_launch_agent(config, dry_run=dry_run),
    )

    # 13. Save config
    if not dry_run:
        ui.run_step(
            "Save config",
            lambda: save_config(config),
        )
    else:
        ui.status_line("[dim]▶[/dim]", "Save config", "skipped (dry run)")
