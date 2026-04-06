# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Assemble Claude Code configuration from dotfiles repos into ~/.claude/."""

from __future__ import annotations

import json
import shutil

from loadout.config import LoadoutConfig
from loadout.exceptions import LoadoutBuildError
from loadout.merge import deep_merge
from loadout.ui import status_line, verbose_line


def _build_mcp_json(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Deep-merge mcp-shared.json with per-org MCP configs and write mcp.json."""
    base_path = config.dotfiles_dir / "claude" / "base" / "mcp-shared.json"
    if not base_path.exists():
        verbose_line(f"mcp base not found: {base_path}")
        return

    try:
        merged: object = json.loads(base_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LoadoutBuildError(f"Malformed JSON in {base_path}: {exc}") from exc

    private_base_mcp = config.dotfiles_private_dir / "claude" / "base" / "mcp-private.json"
    if private_base_mcp.exists():
        try:
            pb_data: object = json.loads(private_base_mcp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LoadoutBuildError(f"Malformed JSON in {private_base_mcp}: {exc}") from exc
        merged = deep_merge(merged, pb_data)
        verbose_line("merged MCP config for private base")

    for org in config.orgs:
        org_mcp = config.dotfiles_private_dir / "claude" / "orgs" / org / f"mcp-{org}.json"
        if org_mcp.exists():
            try:
                org_data: object = json.loads(org_mcp.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise LoadoutBuildError(f"Malformed JSON in {org_mcp}: {exc}") from exc
            merged = deep_merge(merged, org_data)
            verbose_line(f"merged MCP config for org: {org}")

    dest = config.claude_dir / "mcp.json"
    if dry_run:
        status_line("[dim]▶[/dim]", "mcp.json", "would write (dry run)")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    status_line("[green]✓[/green]", "mcp.json", str(dest))


def _build_claude_md(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Concatenate CLAUDE.md.template with per-org CLAUDE.md overlays."""
    template_path = config.dotfiles_dir / "claude" / "CLAUDE.md.template"
    if not template_path.exists():
        verbose_line(f"CLAUDE.md template not found: {template_path}")
        return

    content = template_path.read_text(encoding="utf-8")

    private_base_md = config.dotfiles_private_dir / "claude" / "base" / "CLAUDE.md"
    if private_base_md.exists():
        separator = "\n\n# --- overlay: private-base ---\n\n"
        content = content.rstrip("\n") + separator + private_base_md.read_text(encoding="utf-8")
        verbose_line("appended CLAUDE.md overlay for private base")

    for org in config.orgs:
        org_md = config.dotfiles_private_dir / "claude" / "orgs" / org / "CLAUDE.md"
        if org_md.exists():
            separator = f"\n\n# --- overlay: {org} ---\n\n"
            content = content.rstrip("\n") + separator + org_md.read_text(encoding="utf-8")
            verbose_line(f"appended CLAUDE.md overlay for org: {org}")

    dest = config.claude_dir / "CLAUDE.md"
    if dry_run:
        status_line("[dim]▶[/dim]", "CLAUDE.md", "would write (dry run)")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    status_line("[green]✓[/green]", "CLAUDE.md", str(dest))


def _build_settings_json(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Deep-merge settings.json from public base, private base, and per-org layers."""
    merged: dict[str, object] = {}

    public_base = config.dotfiles_dir / "claude" / "base" / "settings.json"
    if public_base.exists():
        try:
            merged = json.loads(public_base.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LoadoutBuildError(f"Malformed JSON in {public_base}: {exc}") from exc
        verbose_line("loaded settings.json from public base")

    private_base = config.dotfiles_private_dir / "claude" / "base" / "settings.json"
    if private_base.exists():
        try:
            pb_data: object = json.loads(private_base.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LoadoutBuildError(f"Malformed JSON in {private_base}: {exc}") from exc
        merged = deep_merge(merged, pb_data)
        verbose_line("merged settings.json from private base")

    for org in config.orgs:
        org_settings = (
            config.dotfiles_private_dir / "claude" / "orgs" / org / f"settings-{org}.json"
        )
        if org_settings.exists():
            try:
                org_data: object = json.loads(org_settings.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise LoadoutBuildError(f"Malformed JSON in {org_settings}: {exc}") from exc
            merged = deep_merge(merged, org_data)
            verbose_line(f"merged settings.json for org: {org}")

    if not merged:
        verbose_line("no settings.json sources found")
        return

    dest = config.claude_dir / "settings.json"
    if dry_run:
        status_line("[dim]▶[/dim]", "settings.json", "would write (dry run)")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    status_line("[green]✓[/green]", "settings.json", str(dest))


def _copy_statusline(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Copy statusline.sh into the Claude config directory."""
    src = config.dotfiles_dir / "claude" / "statusline.sh"
    if not src.exists():
        verbose_line(f"statusline.sh not found: {src}")
        return

    dest = config.claude_dir / "statusline.sh"
    if dry_run:
        status_line("[dim]▶[/dim]", "statusline.sh", "would copy (dry run)")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    status_line("[green]✓[/green]", "statusline.sh", str(dest))


def _copy_providers(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Copy provider auth scripts into the Claude providers directory."""
    providers_src = config.dotfiles_private_dir / "claude" / "providers"
    if not providers_src.exists():
        verbose_line(f"providers dir not found: {providers_src}")
        return

    providers_dest = config.claude_dir / "providers"
    if dry_run:
        status_line("[dim]▶[/dim]", "providers", "would copy (dry run)")
        return

    providers_dest.mkdir(parents=True, exist_ok=True)
    for sh_file in sorted(providers_src.iterdir()):
        if sh_file.is_file() and sh_file.suffix == ".sh":
            dest_file = providers_dest / sh_file.name
            shutil.copy2(sh_file, dest_file)
            dest_file.chmod(dest_file.stat().st_mode | 0o755)
            verbose_line(f"copied provider: {sh_file.name}")

    status_line("[green]✓[/green]", "providers", str(providers_dest))


def build_claude_config(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Assemble full Claude Code configuration from dotfiles repos.

    Creates ``~/.claude/`` (via ``config.claude_dir``) and populates it with:
    - ``mcp.json`` — deep-merged MCP server config
    - ``settings.json`` — deep-merged settings from base + org layers
    - ``CLAUDE.md`` — concatenated template + org overlays
    - ``statusline.sh`` — copied from public dotfiles
    - ``providers/`` — auth provider scripts from private dotfiles
    """
    if not dry_run:
        config.claude_dir.mkdir(parents=True, exist_ok=True)

    _build_mcp_json(config, dry_run=dry_run)
    _build_settings_json(config, dry_run=dry_run)
    _build_claude_md(config, dry_run=dry_run)
    _copy_statusline(config, dry_run=dry_run)
    _copy_providers(config, dry_run=dry_run)
