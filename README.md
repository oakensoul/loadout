# Loadout

Machine configuration management CLI. Loadout orchestrates dotfile building,
Homebrew, global package installs, and health checks across multiple user/org
contexts.

## Prerequisites

- **Python 3.11+** — required runtime
- **Git** — for cloning and updating dotfile repos
- **Homebrew** — optional but expected for macOS package management
- **1Password CLI (`op`)** — optional, used for secret-backed SSH key registration
- **GitHub CLI (`gh`)** — optional, used during `init` for SSH key registration

## Install

```bash
# Clone and install in development mode
git clone https://github.com/oakensoul/loadout.git
cd loadout
pip install -e ".[dev]"
```

This installs the `loadout` binary into your PATH.

## Quick Start

```bash
# 1. Bootstrap a new machine for a user + orgs
loadout init --user=oakensoul --orgs=personal --orgs=splash

# 2. Verify everything is set up
loadout check

# 3. Day-to-day: pull latest config and rebuild
loadout update

# 4. Intentional upgrades (includes brew upgrade)
loadout upgrade
```

## Commands

### `loadout init`

Full machine bootstrap — clones dotfile repos, generates SSH keys, registers
with GitHub, builds dotfiles, runs Homebrew bundle, and installs global packages.

```bash
loadout init --user=oakensoul --orgs=personal --orgs=splash
loadout init --user=work --orgs=splash --dry-run
```

### `loadout update`

Pull latest dotfile sources, rebuild merged dotfiles, run `brew bundle`, and
install global packages. Safe and idempotent.

```bash
loadout update
loadout update --dry-run
```

### `loadout upgrade`

Everything in `update` plus `brew upgrade`. Run intentionally — upgrades can
break things.

```bash
loadout upgrade
loadout upgrade --verbose
```

### `loadout check`

Read-only health checks. Never mutates anything.

```bash
loadout check
```

### `loadout build`

Merge base + org dotfile fragments into final dotfiles in `~/`.

```bash
loadout build
loadout build --dry-run
```

### `loadout globals`

Install non-Homebrew global packages: Claude Code, NVM + Node LTS,
pyenv + Python, npm globals, and pip globals from org config.

```bash
loadout globals
loadout globals --dry-run
```

### `loadout display`

Switch macOS display profile. Auto-detects connected displays when no mode
is given.

```bash
loadout display              # auto-detect
loadout display connected    # force desktop/connected mode
loadout display solo         # force laptop-solo mode
```

## Global Flags

| Flag | Description |
|------|-------------|
| `--dry-run` | Show what would be done without executing |
| `-v`, `--verbose` | Increase output detail (show commands, stderr) |
| `--help` | Show help for any command |

## How It Works

### Dotfile Merge Strategies

Loadout merges `~/.dotfiles/dotfiles/base/` (public) with
`~/.dotfiles-private/dotfiles/orgs/<org>/` (private) using per-file strategies:

| File type | Strategy | Behavior |
|-----------|----------|----------|
| `.zshrc`, `.aliases`, `.zprofile`, `.zshenv` | Concatenation | Base + org appended with separator |
| `.gitconfig` | Include | Git native `[include]` directives to `~/.gitconfig.d/<org>` |
| `*.json` | Deep merge | Recursive merge, org wins on conflict |
| `*.yaml`, `*.yml` | Deep merge | Recursive merge, org wins on conflict |
| Everything else | Replace | Org file replaces base entirely |

Output is staged to `~/.dotfiles/build/` then copied to `~/`. Idempotent — safe to re-run.

### Repo Layout

| Repo | Purpose |
|------|---------|
| `oakensoul/loadout` | This repo — Python package, CLI logic |
| `oakensoul/dotfiles` | Public base config — Brewfiles, dotfiles, macOS scripts |
| `oakensoul/dotfiles-private` | Private org config — org-specific overlays |

### Config File

Loadout stores its configuration in `~/.dotfiles/.loadout.toml`:

```toml
user = "oakensoul"
orgs = ["personal", "splash"]
```

This is written by `loadout init` and read by all other commands.

## Troubleshooting

For any issue, try running with `--verbose` first to see the exact commands
being executed and their stderr output.

**`loadout check` shows warnings:**
Warnings are informational — they indicate optional tools that aren't installed.
Errors indicate required tools that are missing.

**`loadout build` fails with "Malformed JSON/YAML":**
Check the file path in the error message. The org overlay file has a syntax error.
Fix the file and re-run `loadout build`.

**`loadout init` fails at SSH key registration:**
This step requires both `op` (1Password CLI) and `gh` (GitHub CLI). If either
is missing, the step is skipped with a warning. You can register your SSH key
manually and continue.

**`loadout update` fails on `git pull`:**
Loadout uses `--ff-only` for safety. If you have local changes in your dotfiles
repos, commit or stash them first.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check loadout/ tests/

# Type check
mypy loadout/
```
