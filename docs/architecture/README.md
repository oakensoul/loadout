# Loadout — Architecture

## What is Loadout?

Loadout is a machine configuration management system — bigger than dotfiles, built around the concept of *operating contexts*. You define orgs (project/company contexts), users (operating scopes that bundle orgs), and the system handles getting a fresh machine from zero to fully configured in one command.

**Loadout is the stage. AIDA is the performance.** Loadout sets up the machine and installs everything — including AIDA and its plugins — so Claude Code sessions are fully context-aware from the first keystroke.

---

## Ecosystem Position

```
Machine layer         →  loadout
  └── installs
Python packages       →  devbox (core logic, CLI)
                          canvas (ephemeral workspaces, org-aware)
  └── exposed via
AIDA plugins          →  aida-loadout-plugin (/loadout check, /loadout update)
                          aida-devbox-plugin  (/devbox create, /devbox list)
                          aida-canvas-plugin  (/canvas new, /canvas list)
  └── running on
Claude Code layer     →  aida-core-plugin
```

---

## Repo Relationship

Loadout is a **tool**, not a config. Config lives separately:

| Repo | Purpose |
|------|---------|
| `oakensoul/loadout` | This repo — Python package, CLI logic |
| `oakensoul/dotfiles` | Public base config — brewfiles, dotfiles, macos scripts |
| `oakensoul/dotfiles-private` | Private org config — personal, splash, mythical overlays |

The package contains the logic. `~/.dotfiles/` + `~/.dotfiles-private/` contain the user's personal config. Same model as `git` + `~/.gitconfig`.

---

## User Model

| User | Type | Access | Purpose |
|------|------|--------|---------|
| `gunnar` | Personal | Physical display | Day-to-day personal |
| `work` | Work | Screen Share (virtual display) | Focused work context |
| `devbox1`, `devbox2` | Dev | SSH only | Disposable, isolated |

Each user declares which orgs they load:

```bash
loadout init --user=gunnar --orgs="personal mythical"
loadout init --user=work   --orgs="splash"
```

---

## CLI Interface

```bash
loadout init --user=<name> --orgs="<org1> <org2>"  # bootstrap a user
loadout update        # pull + build + brew bundle + globals (safe, idempotent)
loadout upgrade       # everything in update + brew upgrade (intentional)
loadout check         # health check — warn only, never mutates
loadout build         # merge base + org dotfile fragments → ~/
loadout globals       # install/update global packages
loadout display connected   # force desktop-style defaults
loadout display solo        # force laptop-solo defaults
```

---

## Core Flows

### `loadout init`

1. Clone `~/.dotfiles` (public base) and `~/.dotfiles-private` (org config)
2. Generate SSH key → register with GitHub via API
3. Switch git remotes from HTTPS to SSH
4. Run `loadout build` to merge dotfiles
5. Run `brew bundle` for base + org Brewfiles
6. Run `loadout globals` for non-Homebrew installs
7. Apply macOS defaults via `macos/` scripts
8. Install launch agent for display detection
9. Write `~/.canvas/config` and `~/.devbox/` registry dirs
10. Bootstrap AIDA plugins for this user

### `loadout update`

```
git pull ~/.dotfiles && git pull ~/.dotfiles-private
loadout build
brew update && brew bundle --all
loadout globals
```

### `loadout upgrade`

Everything in `update` plus `brew upgrade` — run intentionally, can break things.

### `loadout build`

Merges `~/.dotfiles/dotfiles/base/` + `~/.dotfiles-private/dotfiles/orgs/<org>/` fragments:

| File type | Strategy |
|-----------|----------|
| `.zshrc`, `.aliases` | Concatenation — base + org fragment |
| `.gitconfig` | Native `[include]` — git handles merge |
| JSON | Deep merge, org wins on conflict |
| YAML | Deep merge, org wins on conflict |
| Unknown | Org replaces base |

Output staged to `~/.dotfiles/build/`, then copied to `~/`. Idempotent — safe to re-run.

### `loadout globals`

Installs non-Homebrew tools idempotently:

- Claude Code: `curl -fsSL https://claude.ai/install.sh | bash`
- nvm + node LTS
- pyenv + latest stable Python
- npm globals and pip globals per org config

### `loadout check`

Warn-only health check — never mutates anything:

```
🖥  ENVIRONMENT (oakensoul)
✅ Homebrew
✅ git (2.x.x)
✅ nvm + node (lts)
✅ pyenv + python (3.x.x)
✅ 1Password CLI — vault reachable
✅ GitHub SSH (oakensoul)
✅ Claude Code (1.x.x)
⚠️  AWS profile: side-project — credentials expired
❌ Brewfile — 2 packages missing

📦  DEVBOXES
✅ devbox1 (splash-data) — reachable, last seen 2h ago
⚠️  devbox2 (f1-fantasy)  — reachable, last seen 47d ago

🎨  CANVAS
✅ 2026-03-13-okr-planning (splash) — 2d ago
⚠️  2026-02-01-electric-penguin (personal) — 39d ago
```

---

## Dotfile Build System

Stow is replaced by a Python build step. No symlinks — orgs layer cleanly on top of base.

```
~/.dotfiles/dotfiles/base/     +    ~/.dotfiles-private/dotfiles/orgs/splash/
        .zshrc                                   .zshrc
        .gitconfig                               .gitconfig
             │                                       │
             └──────────── loadout build ────────────┘
                                  │
                        ~/.dotfiles/build/     ← staged output
                                  │
                              copy to ~/       ← written to final locations
```

`.gitconfig` uses git's native `[include]` mechanism — no merge logic needed:

```ini
# base .gitconfig (built output)
[include]
    path = ~/.gitconfig.d/splash
```

```ini
# ~/.gitconfig.d/splash
[user]
    email = rjohnson@splashsports.com
    signingkey = ~/.ssh/id_ed25519_splash
```

---

## macOS Settings

Display profile detection via launch agent + `display-watch.sh`:

| Context | Scripts applied |
|---------|----------------|
| Mac Mini | `defaults-base.sh` + `defaults-desktop.sh` |
| MacBook, no display | `defaults-base.sh` + `defaults-laptop-solo.sh` |
| MacBook + display | `defaults-base.sh` + `defaults-laptop-connected.sh` |

Mac Mini power: `pmset -a sleep 0` (never), `pmset -a displaysleep 10`.

Manual override:

```bash
loadout display connected
loadout display solo
```

---

## Git Workflow

Manual updates only — never auto-apply. Background check on every shell login:

```bash
# in ~/.zshrc — non-blocking
(cd ~/.dotfiles && git fetch origin --quiet && \
  BEHIND=$(git rev-list HEAD..origin/main --count) && \
  [ "$BEHIND" -gt 0 ] && \
  echo "⚠️  loadout: $BEHIND update(s) available — run 'loadout update'") &
```

---

## Secrets

All secrets via 1Password CLI — never hardcoded in any file:

```bash
op read "op://Personal/GitHub/token"
op read "op://Work/Snowflake/account"
```

SSH keys served via 1Password SSH agent — no private keys written to disk.

---

## Package Structure

```
loadout/
├── __init__.py
├── cli.py       # Click CLI entry point
├── core.py      # importable by aida-loadout-plugin
├── build.py     # dotfile merge logic
├── globals.py   # non-Homebrew installs
├── display.py   # macOS display profile switching
└── check.py     # health check — warn only
```

---

## Naming Conventions

kebab-case everywhere: `[a-z0-9-]`, no leading/trailing dashes.

| Thing | Convention | Example |
|-------|-----------|---------|
| Org names | kebab-case | `personal`, `splash`, `mythical` |
| User names | lowercase | `gunnar`, `work` |
| AWS profiles | kebab-case | `splash-main`, `personal-main` |

---

## Platform Support

macOS + Linux/*nix. No Windows — intentional. The `macos/` layer is the only macOS-specific piece. A `linux/` sibling can be added surgically later without touching anything above it.
