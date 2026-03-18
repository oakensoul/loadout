"""Dotfile merge engine — build final dotfiles from base + org layers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from loadout.config import LoadoutConfig
from loadout.ui import section_header, status_line

# Files that use concatenation merge strategy.
_CONCAT_FILES = frozenset({".zshrc", ".aliases", ".zprofile", ".zshenv"})


def _get_merge_strategy(filename: str) -> str:
    """Return the merge strategy name for a given filename.

    Returns one of: ``"concat"``, ``"gitconfig"``, ``"json"``, ``"yaml"``, or ``"replace"``.
    """
    if filename in _CONCAT_FILES:
        return "concat"
    if filename == ".gitconfig":
        return "gitconfig"
    if filename.endswith(".json"):
        return "json"
    if filename.endswith((".yaml", ".yml")):
        return "yaml"
    return "replace"


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
            raise RuntimeError(f"Malformed JSON in {base_path}: {exc}") from exc

    try:
        org_data: object = json.loads(org_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Malformed JSON in {org_path}: {exc}") from exc
    merged = _deep_merge(base_data, org_data)
    dest_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")


def _merge_yaml(base_path: Path, org_path: Path, dest_path: Path) -> None:
    """Deep-merge two YAML files; org values win on conflict."""
    base_data: object = {}
    if base_path.exists():
        try:
            raw = yaml.safe_load(base_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise RuntimeError(f"Malformed YAML in {base_path}: {exc}") from exc
        if raw is not None:
            base_data = raw

    try:
        raw_org = yaml.safe_load(org_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Malformed YAML in {org_path}: {exc}") from exc
    org_data: object = raw_org if raw_org is not None else {}
    merged = _deep_merge(base_data, org_data)
    dest_path.write_text(yaml.dump(merged, default_flow_style=False), encoding="utf-8")


def build_dotfiles(config: LoadoutConfig, *, dry_run: bool = False) -> None:
    """Build merged dotfiles from base and org layers.

    Steps:
    1. Clear and recreate ``build_dir``.
    2. Copy all base files into ``build_dir``.
    3. For each org, apply the appropriate merge strategy per file.
    4. Copy built files from ``build_dir`` to the home directory.
    """
    home_dir = config.base_dir if config.base_dir is not None else Path.home()
    build_dir = config.build_dir
    base_dir = config.dotfiles_dir / "dotfiles" / "base"
    private_dir = config.dotfiles_private_dir / "dotfiles" / "orgs"

    section_header("build")

    if dry_run:
        status_line(">>", "dry-run", "no files will be modified")
        return

    # Step 1: Clear and recreate build_dir.
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    # Step 2: Copy base files into build_dir.
    if base_dir.exists():
        for src in sorted(base_dir.iterdir()):
            if src.is_file():
                shutil.copy2(src, build_dir / src.name)
                status_line(">>", "base", src.name)

    # Step 3: Apply org overlays.
    # Collect gitconfig paths across all orgs for the gitconfig strategy.
    gitconfig_org_paths: dict[str, Path] = {}

    for org in config.orgs:
        org_dir = private_dir / org
        if not org_dir.exists():
            continue

        for org_file in sorted(org_dir.iterdir()):
            if not org_file.is_file():
                continue

            strategy = _get_merge_strategy(org_file.name)
            dest = build_dir / org_file.name

            if strategy == "concat":
                base_file = build_dir / org_file.name
                _merge_concat(base_file, org_file, dest)
                status_line(">>", f"concat ({org})", org_file.name)

            elif strategy == "gitconfig":
                gitconfig_org_paths[org] = org_file

            elif strategy == "json":
                base_file = build_dir / org_file.name
                _merge_json(base_file, org_file, dest)
                status_line(">>", f"json ({org})", org_file.name)

            elif strategy == "yaml":
                base_file = build_dir / org_file.name
                _merge_yaml(base_file, org_file, dest)
                status_line(">>", f"yaml ({org})", org_file.name)

            else:
                # replace strategy
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

    # Step 4: Copy built files to home directory.
    for built_file in sorted(build_dir.iterdir()):
        if built_file.is_file():
            dest = home_dir / built_file.name
            shutil.copy2(built_file, dest)
            status_line(">>", "install", built_file.name)
