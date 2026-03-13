# Loadout

Machine configuration management CLI. Loadout orchestrates dotfile building,
Homebrew, global package installs, and health checks across multiple user/org
contexts.

## Install

```bash
pip install -e .
```

This installs the `loadout` binary into your PATH.

## Usage

```bash
# Initialize for a user and orgs
loadout init --user=oakensoul --orgs=my-org,other-org

# Pull latest dotfile sources and rebuild
loadout update

# Run Homebrew upgrade + update global packages
loadout upgrade

# Health checks (read-only, never mutates)
loadout check

# Merge base + org fragments into final dotfiles
loadout build

# Install non-Homebrew globals (Claude Code, npm, pip)
loadout globals

# Switch macOS display profile
loadout display connected
loadout display solo
```
