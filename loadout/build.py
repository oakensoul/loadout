# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Dotfile merge engine — build final dotfiles from base + org layers."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import yaml

from loadout.config import LoadoutConfig
from loadout.exceptions import LoadoutBuildError
from loadout.ui import section_header, status_line, verbose_line

# Files that use concatenation merge strategy.
_CONCAT_FILES = frozenset({".zshrc", ".aliases", ".zprofile", ".zshenv"})


class MergeStrategy(StrEnum):
    """Merge strategies for dotfile building."""

    CONCAT = "concat"
    GITCONFIG = "gitconfig"
    JSON = "json"
    YAML = "yaml"
    REPLACE = "replace"


def _get_merge_strategy(filename: str) -> MergeStrategy:
    """Return the merge strategy for a given filename."""
    if filename in _CONCAT_FILES:
        return MergeStrategy.CONCAT
    if filename == ".gitconfig":
        return MergeStrategy.GITCONFIG
    if filename.endswith(".json"):
        return MergeStrategy.JSON
    if filename.endswith((".yaml", ".yml")):
        return MergeStrategy.YAML
    return MergeStrategy.REPLACE


def _merge_concat(base_path: Path, org_path: Path, dest_path: Path) -> None:
    """Merge by concatenating org content after base content with a separator.

    When multiple orgs are configured, concatenation is intentionally cumulative:
    each org's content is appended after the previous result so that all layers
    contribute to the final file.
    """
    base_content = base_path.read_text(encoding="utf-8") if base_path.exists() else ""
    org_content = org_path.read_text(encoding="utf-8")

    separator = f"\n# --- org overlay: {org_path.parent.name} ---\n"
    merged = base_content.rstrip("\n") + separator + org_content
    dest_path.write_text(merged, encoding="utf-8")


def _merge_gitconfig(
    base_path: Path,
    org_paths: dict[str, Path],
    dest_path: Path,
    home_dir: Path,
) -> None:
    """Merge ``.gitconfig`` using git include directives.

    Copies the base ``.gitconfig`` to *dest_path*, then for each org creates
    ``~/.gitconfig.d/<org>`` and appends an ``[include]`` section.
    """
    content = base_path.read_text(encoding="utf-8") if base_path.exists() else ""

    gitconfig_d = home_dir / ".gitconfig.d"
    gitconfig_d.mkdir(parents=True, exist_ok=True)

    for org, org_path in org_paths.items():
        org_dest = gitconfig_d / org
        shutil.copy2(org_path, org_dest)

        include_line = f"\n[include]\n    path = ~/.gitconfig.d/{org}\n"
        content += include_line

    dest_path.write_text(content, encoding="utf-8")


def _deep_merge(base: object, overlay: object) -> object:
    """Recursively merge *overlay* into *base*; overlay values win on conflict."""
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = dict(base)
        for key, value in overlay.items():
            if key in merged:
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    return overlay


def _merge_json(base_path: Path, org_path: Path, dest_path: Path) -> None:
    """Deep-merge two JSON files; org values win on conflict."""
    base_data: object = {}
    if base_path.exists():
        try:
            base_data = json.loads(base_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LoadoutBuildError(f"Malformed JSON in {base_path}: {exc}") from exc

    try:
        org_data: object = json.loads(org_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LoadoutBuildError(f"Malformed JSON in {org_path}: {exc}") from exc
    merged = _deep_merge(base_data, org_data)
    dest_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")


def _merge_yaml(base_path: Path, org_path: Path, dest_path: Path) -> None:
    """Deep-merge two YAML files; org values win on conflict."""
    base_data: object = {}
    if base_path.exists():
        try:
            raw = yaml.safe_load(base_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise LoadoutBuildError(f"Malformed YAML in {base_path}: {exc}") from exc
        if raw is not None:
            base_data = raw

    try:
        raw_org = yaml.safe_load(org_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise LoadoutBuildError(f"Malformed YAML in {org_path}: {exc}") from exc
    org_data: object = raw_org if raw_org is not None else {}
    merged = _deep_merge(base_data, org_data)
    dest_path.write_text(yaml.dump(merged, default_flow_style=False), encoding="utf-8")


def _safe_path(path: Path, allowed_parent: Path) -> Path:
    """Resolve *path* and verify it lives under *allowed_parent*.

    Raises LoadoutBuildError if the resolved path escapes *allowed_parent*
    (e.g. via symlinks or ``..`` components).
    """
    resolved = path.resolve()
    parent_resolved = allowed_parent.resolve()
    if not str(resolved).startswith(str(parent_resolved) + os.sep) and resolved != parent_resolved:
        raise LoadoutBuildError(
            f"Path {path} resolves to {resolved}, which is outside {parent_resolved}"
        )
    return resolved


def _backup_file(dest: Path, backup_dir: Path) -> None:
    """Create a timestamped backup of *dest* in *backup_dir* if it exists."""
    if dest.is_symlink():
        verbose_line(f"skipping backup of symlink {dest.name}")
        return
    if not dest.exists():
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"{dest.name}.{stamp}"
    shutil.copy2(dest, backup_path)
    verbose_line(f"backed up {dest.name} → {backup_path}")


def _build_into(
    build_dir: Path,
    base_dir: Path,
    private_dir: Path,
    home_dir: Path,
    orgs: list[str],
) -> None:
    """Run the merge pipeline into *build_dir* (Steps 1–3).

    Separated from install so we can build into a temp dir for atomicity.
    """
    # Step 1: Clear and recreate build_dir.
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    # Step 2: Copy base files into build_dir (skip symlinks).
    if base_dir.exists():
        for src in sorted(base_dir.iterdir()):
            if src.is_symlink():
                verbose_line(f"skipping symlink in base: {src.name}")
                continue
            if src.is_file():
                shutil.copy2(src, build_dir / src.name)
                status_line(">>", "base", src.name)

    # Step 3: Apply org overlays.
    gitconfig_org_paths: dict[str, Path] = {}

    for org in orgs:
        org_dir = private_dir / org
        if not org_dir.exists():
            continue

        for org_file in sorted(org_dir.iterdir()):
            if org_file.is_symlink():
                verbose_line(f"skipping symlink in org {org}: {org_file.name}")
                continue
            if not org_file.is_file():
                continue

            strategy = _get_merge_strategy(org_file.name)
            dest = build_dir / org_file.name

            if strategy is MergeStrategy.CONCAT:
                accumulated = build_dir / org_file.name
                _merge_concat(accumulated, org_file, dest)
                status_line(">>", f"concat ({org})", org_file.name)

            elif strategy is MergeStrategy.GITCONFIG:
                gitconfig_org_paths[org] = org_file

            elif strategy is MergeStrategy.JSON:
                accumulated = build_dir / org_file.name
                _merge_json(accumulated, org_file, dest)
                status_line(">>", f"json ({org})", org_file.name)

            elif strategy is MergeStrategy.YAML:
                accumulated = build_dir / org_file.name
                _merge_yaml(accumulated, org_file, dest)
                status_line(">>", f"yaml ({org})", org_file.name)

            elif strategy is MergeStrategy.REPLACE:
                shutil.copy2(org_file, dest)
                status_line(">>", f"replace ({org})", org_file.name)

    # Handle gitconfig after collecting all org paths.
    if gitconfig_org_paths:
        base_gitconfig = build_dir / ".gitconfig"
        _merge_gitconfig(
            base_gitconfig if base_gitconfig.exists() else base_dir / ".gitconfig",
            gitconfig_org_paths,
            build_dir / ".gitconfig",
            home_dir,
        )
        status_line(">>", "gitconfig", ".gitconfig")


def build_dotfiles(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Build merged dotfiles from base and org layers.

    Steps:
    1. Build into a temporary directory for atomicity.
    2. Swap the temp dir to the final ``build_dir``.
    3. Backup existing home files, then install from ``build_dir``.
    """
    home_dir = config.home
    build_dir = config.build_dir
    base_dir = config.dotfiles_dir / "dotfiles" / "base"
    private_dir = config.dotfiles_private_dir / "dotfiles" / "orgs"
    backup_dir = config.dotfiles_dir / "backups"

    section_header("build")

    if dry_run:
        status_line(">>", "dry-run", "no files will be modified")
        return

    # Build into a temp directory first for atomic swap.
    tmp_build = Path(tempfile.mkdtemp(prefix="loadout-build-", dir=config.dotfiles_dir))
    try:
        _build_into(tmp_build, base_dir, private_dir, home_dir, config.orgs)

        # Atomic swap: replace build_dir with the temp dir.
        if build_dir.exists():
            shutil.rmtree(build_dir)
        tmp_build.rename(build_dir)
    except BaseException:
        # Clean up temp dir on any failure.
        if tmp_build.exists():
            shutil.rmtree(tmp_build)
        raise

    # Step 4: Backup existing files, then install from build_dir.
    for built_file in sorted(build_dir.iterdir()):
        if built_file.is_file():
            dest = home_dir / built_file.name
            _safe_path(dest, home_dir)
            _backup_file(dest, backup_dir)
            shutil.copy2(built_file, dest)
            status_line(">>", "install", built_file.name)
