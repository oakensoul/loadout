# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Scaffold a new dotfiles-private repository via cookiecutter."""

from __future__ import annotations

import shutil
from pathlib import Path

from loadout import runner, ui
from loadout.exceptions import LoadoutError

_DEFAULT_TEMPLATE = "https://github.com/oakensoul/dotfiles-private-cookiecutter"


def _check_cookiecutter() -> None:
    """Verify that cookiecutter is importable, raising a clear error if not."""
    try:
        import cookiecutter  # noqa: F401
    except ImportError:
        raise LoadoutError(
            "cookiecutter is not installed. "
            'Install it with: pip install "oakensoul-loadout[scaffold]"'
        ) from None


def _build_context(
    user: str,
    orgs: list[str],
    git_name: str,
    git_email: str,
) -> dict[str, str]:
    """Build the cookiecutter extra_context dictionary."""
    return {
        "github_username": user,
        "git_name": git_name,
        "git_email": git_email,
        "primary_org": orgs[0] if orgs else "",
        "additional_orgs": ",".join(orgs[1:]) if len(orgs) > 1 else "",
    }


def run_scaffold(
    user: str,
    orgs: list[str],
    git_name: str,
    git_email: str,
    *,
    template: str = _DEFAULT_TEMPLATE,
    create_repo: bool = False,
    dry_run: bool = False,
    home_dir: Path | None = None,
) -> None:
    """Scaffold a new dotfiles-private repository.

    Uses cookiecutter to generate the repo structure from a template, then
    optionally creates a private GitHub repository.

    Args:
        user: GitHub username.
        orgs: List of org names (first is primary).
        git_name: Full name for git config.
        git_email: Email for git config.
        template: Cookiecutter template URL or local path.
        create_repo: If True, create a private GitHub repo via ``gh``.
        dry_run: If True, preview actions without making changes.
        home_dir: Override home directory (for testing).
    """
    home = home_dir if home_dir is not None else Path.home()
    target_dir = home / ".dotfiles-private"

    ui.section_header("Scaffold dotfiles-private")

    # 1. Check cookiecutter is available
    ui.run_step("Check cookiecutter dependency", _check_cookiecutter)

    # 2. Check target directory does not exist
    def _check_target() -> None:
        if target_dir.exists():
            raise LoadoutError(
                f"{target_dir} already exists. "
                "Remove it first or use 'loadout init' to bootstrap an existing repo."
            )
        ui.status_line(
            "[green]\u2713[/green]", str(target_dir), "does not exist — ready to scaffold"
        )

    ui.run_step("Check target directory", _check_target)

    # 3. Build context
    context = _build_context(user, orgs, git_name, git_email)

    # 4. Run cookiecutter
    def _run_cookiecutter() -> None:
        if dry_run:
            ui.status_line(
                "[dim]\u25b6[/dim]",
                "cookiecutter",
                f"would scaffold from {template} (dry run)",
            )
            return

        from cookiecutter.main import cookiecutter as run_cookiecutter

        run_cookiecutter(
            template,
            no_input=True,
            extra_context=context,
            output_dir=str(home),
        )

    ui.run_step("Run cookiecutter template", _run_cookiecutter)

    # 5. Rename output directory to ~/.dotfiles-private
    def _rename_output() -> None:
        # cookiecutter typically outputs to {output_dir}/{project_slug}
        # The template should produce a directory named {github_username}-dotfiles-private
        expected_output = home / f"{user}-dotfiles-private"

        if dry_run:
            ui.status_line(
                "[dim]\u25b6[/dim]",
                "Rename",
                f"would rename {expected_output} -> {target_dir} (dry run)",
            )
            return

        if expected_output.exists():
            expected_output.rename(target_dir)
            ui.status_line(
                "[green]\u2713[/green]",
                "Rename",
                f"{expected_output.name} -> {target_dir.name}",
            )
        elif target_dir.exists():
            # Template may have already output to the target name
            ui.status_line(
                "[green]\u2713[/green]",
                "Rename",
                "target directory already has correct name",
            )
        else:
            # Look for any new directory that might have been created
            raise LoadoutError(
                f"Expected cookiecutter output at {expected_output} but it was not found. "
                "Check that the template produces a directory named "
                f"'{user}-dotfiles-private'."
            )

    ui.run_step("Rename output directory", _rename_output)

    # 6. Create GitHub repo if requested
    if create_repo:

        def _create_repo() -> None:
            if shutil.which("gh") is None:
                ui.status_line(
                    "[yellow]![/yellow]",
                    "GitHub CLI",
                    "not found — skipping repo creation",
                )
                return

            runner.run(
                [
                    "gh",
                    "repo",
                    "create",
                    f"{user}/dotfiles-private",
                    "--private",
                    f"--source={target_dir}",
                    "--push",
                ],
                dry_run=dry_run,
            )

        ui.run_step("Create GitHub repository", _create_repo)

    # 7. Success message
    ui.console.print()
    ui.console.print("[green]Scaffold complete![/green]")
    ui.console.print()
    ui.console.print("Next steps:")
    ui.console.print(f"  1. Review the generated files in {target_dir}")
    ui.console.print("  2. Customize your private dotfiles")
    orgs_flags = " --orgs=".join(orgs)
    ui.console.print(f"  3. Run: loadout init --user={user} --orgs={orgs_flags}")
