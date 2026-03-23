# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Assemble Claude Code configuration from dotfiles repos into ~/.claude/."""

from __future__ import annotations

import json
import shutil

from loadout.config import LoadoutConfig
from loadout.merge import deep_merge
from loadout.ui import status_line, verbose_line


def _build_mcp_json(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Deep-merge mcp-shared.json with per-org MCP configs and write mcp.json."""
    base_path = config.dotfiles_dir / "claude" / "base" / "mcp-shared.json"
    if not base_path.exists():
        verbose_line(f"mcp base not found: {base_path}")
        return

    merged: object = json.loads(base_path.read_text(encoding="utf-8"))

    for org in config.orgs:
        org_mcp = config.dotfiles_private_dir / "claude" / "orgs" / org / f"mcp-{org}.json"
        if org_mcp.exists():
            org_data: object = json.loads(org_mcp.read_text(encoding="utf-8"))
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

    for org in config.orgs:
        org_md = config.dotfiles_private_dir / "claude" / "orgs" / org / "CLAUDE.md"
        if org_md.exists():
            separator = f"\n\n# --- org overlay: {org} ---\n\n"
            content = content.rstrip("\n") + separator + org_md.read_text(encoding="utf-8")
            verbose_line(f"appended CLAUDE.md overlay for org: {org}")

    dest = config.claude_dir / "CLAUDE.md"
    if dry_run:
        status_line("[dim]▶[/dim]", "CLAUDE.md", "would write (dry run)")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    status_line("[green]✓[/green]", "CLAUDE.md", str(dest))


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
            shutil.copy2(sh_file, providers_dest / sh_file.name)
            verbose_line(f"copied provider: {sh_file.name}")

    status_line("[green]✓[/green]", "providers", str(providers_dest))


def build_claude_config(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Assemble full Claude Code configuration from dotfiles repos.

    Creates ``~/.claude/`` (via ``config.claude_dir``) and populates it with:
    - ``mcp.json`` — deep-merged MCP server config
    - ``CLAUDE.md`` — concatenated template + org overlays
    - ``statusline.sh`` — copied from public dotfiles
    - ``providers/`` — auth provider scripts from private dotfiles
    """
    if not dry_run:
        config.claude_dir.mkdir(parents=True, exist_ok=True)

    _build_mcp_json(config, dry_run=dry_run)
    _build_claude_md(config, dry_run=dry_run)
    _copy_statusline(config, dry_run=dry_run)
    _copy_providers(config, dry_run=dry_run)
