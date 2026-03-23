# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.claude module."""

from __future__ import annotations

import json
from pathlib import Path

from loadout.claude import build_claude_config
from loadout.config import LoadoutConfig


def _make_config(tmp_path: Path, orgs: list[str] | None = None) -> LoadoutConfig:
    """Create a LoadoutConfig rooted at tmp_path."""
    return LoadoutConfig(user="testuser", orgs=orgs or [], base_dir=tmp_path)


def _write(path: Path, content: str) -> None:
    """Write content to a file, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestBuildMcpJson:
    """Tests for MCP JSON merging."""

    def test_build_mcp_json_base_only(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        base = {"mcpServers": {"server-a": {"command": "npx", "args": ["-y", "a"]}}}
        _write(config.dotfiles_dir / "claude" / "base" / "mcp-shared.json", json.dumps(base))

        build_claude_config(config)

        result = json.loads((config.claude_dir / "mcp.json").read_text(encoding="utf-8"))
        assert result == base

    def test_build_mcp_json_with_orgs(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path, orgs=["acme", "globex"])
        base = {
            "mcpServers": {
                "shared": {"command": "npx", "args": ["-y", "shared"]},
                "override-me": {"command": "old", "args": ["old-arg"]},
            }
        }
        _write(config.dotfiles_dir / "claude" / "base" / "mcp-shared.json", json.dumps(base))

        acme_mcp = {
            "mcpServers": {
                "acme-server": {"command": "npx", "args": ["-y", "acme"]},
                "override-me": {"command": "new", "args": ["new-arg"]},
            }
        }
        _write(
            config.dotfiles_private_dir / "claude" / "orgs" / "acme" / "mcp-acme.json",
            json.dumps(acme_mcp),
        )

        globex_mcp = {"mcpServers": {"globex-server": {"command": "npx", "args": ["-y", "globex"]}}}
        _write(
            config.dotfiles_private_dir / "claude" / "orgs" / "globex" / "mcp-globex.json",
            json.dumps(globex_mcp),
        )

        build_claude_config(config)

        result = json.loads((config.claude_dir / "mcp.json").read_text(encoding="utf-8"))
        # shared server preserved
        assert result["mcpServers"]["shared"] == {"command": "npx", "args": ["-y", "shared"]}
        # acme org wins on conflict
        assert result["mcpServers"]["override-me"] == {"command": "new", "args": ["new-arg"]}
        # org-specific servers present
        assert "acme-server" in result["mcpServers"]
        assert "globex-server" in result["mcpServers"]


class TestBuildClaudeMd:
    """Tests for CLAUDE.md concatenation."""

    def test_build_claude_md_template_with_orgs(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path, orgs=["acme", "globex"])
        template = config.dotfiles_dir / "claude" / "CLAUDE.md.template"
        _write(template, "# Base Config\nBase content.")
        _write(
            config.dotfiles_private_dir / "claude" / "orgs" / "acme" / "CLAUDE.md",
            "Acme-specific rules.",
        )
        _write(
            config.dotfiles_private_dir / "claude" / "orgs" / "globex" / "CLAUDE.md",
            "Globex-specific rules.",
        )

        build_claude_config(config)

        content = (config.claude_dir / "CLAUDE.md").read_text(encoding="utf-8")
        assert "# Base Config" in content
        assert "Base content." in content
        assert "# --- org overlay: acme ---" in content
        assert "Acme-specific rules." in content
        assert "# --- org overlay: globex ---" in content
        assert "Globex-specific rules." in content
        # Verify ordering: acme before globex
        assert content.index("acme") < content.index("globex")


class TestCopyStatusline:
    """Tests for statusline.sh copying."""

    def test_copy_statusline(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        _write(config.dotfiles_dir / "claude" / "statusline.sh", "#!/bin/bash\necho status")

        build_claude_config(config)

        dest = config.claude_dir / "statusline.sh"
        assert dest.exists()
        assert "echo status" in dest.read_text(encoding="utf-8")


class TestCopyProviders:
    """Tests for provider script copying."""

    def test_copy_providers(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        providers_dir = config.dotfiles_private_dir / "claude" / "providers"
        _write(providers_dir / "aws.sh", "#!/bin/bash\naws auth")
        _write(providers_dir / "gcp.sh", "#!/bin/bash\ngcp auth")
        # Non-.sh file should be skipped
        _write(providers_dir / "readme.txt", "not a script")

        build_claude_config(config)

        dest = config.claude_dir / "providers"
        assert (dest / "aws.sh").exists()
        assert (dest / "gcp.sh").exists()
        assert not (dest / "readme.txt").exists()


class TestBuildClaudeConfigBehavior:
    """Tests for overall build_claude_config behavior."""

    def test_build_claude_config_dry_run(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path, orgs=["acme"])
        base = {"mcpServers": {"s": {"command": "x"}}}
        _write(config.dotfiles_dir / "claude" / "base" / "mcp-shared.json", json.dumps(base))
        _write(config.dotfiles_dir / "claude" / "CLAUDE.md.template", "# Template")
        _write(config.dotfiles_dir / "claude" / "statusline.sh", "#!/bin/bash")
        _write(
            config.dotfiles_private_dir / "claude" / "providers" / "p.sh",
            "#!/bin/bash",
        )

        build_claude_config(config, dry_run=True)

        # No files should have been written
        assert not (config.claude_dir / "mcp.json").exists()
        assert not (config.claude_dir / "CLAUDE.md").exists()
        assert not (config.claude_dir / "statusline.sh").exists()
        assert not (config.claude_dir / "providers").exists()

    def test_build_claude_config_no_claude_dir(self, tmp_path: Path) -> None:
        """Graceful no-op when source dirs don't exist."""
        config = _make_config(tmp_path)
        # Don't create any source files — should not raise
        build_claude_config(config)
        # claude_dir is created but empty (no source files to process)
        assert config.claude_dir.exists()

    def test_build_claude_config_creates_target_dir(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        _write(config.dotfiles_dir / "claude" / "statusline.sh", "#!/bin/bash\necho hi")

        assert not config.claude_dir.exists()
        build_claude_config(config)
        assert config.claude_dir.exists()
        assert (config.claude_dir / "statusline.sh").exists()
