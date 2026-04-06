# Loadout — Architecture

## What is Loadout?

Loadout is a machine configuration management system — bigger than dotfiles, built around the concept of *operating contexts*. You define orgs (project/company contexts), users (operating scopes that bundle orgs), and the system handles getting a fresh machine from zero to fully configured in one command.

**Loadout is the stage. AIDA is the performance.** Loadout sets up the machine and installs everything — including AIDA and its plugins — so Claude Code sessions are fully context-aware from the first keystroke.

---

## Ecosystem Position

```
Machine layer         →  loadout
  └── installs
Python packages       →  devbox (core logic, CLI)              [planned]
                          canvas (ephemeral workspaces)         [planned]
  └── exposed via
AIDA plugins          →  aida-loadout-plugin                   [planned]
                          aida-devbox-plugin                    [planned]
                          aida-canvas-plugin                    [planned]
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
| `oakensoul/dotfiles-private` | Private org config — personal, work, creative overlays |

The package contains the logic. `~/.dotfiles/` + `~/.dotfiles-private/` contain the user's personal config. Same model as `git` + `~/.gitconfig`.

---

## User Model

| User | Type | Access | Purpose |
|------|------|--------|---------|
| `alice` | Personal | Physical display | Day-to-day personal |
| `work` | Work | Screen Share (virtual display) | Focused work context |
| `devbox1`, `devbox2` | Dev | SSH only | Disposable, isolated |

Each user declares which orgs they load:

```bash
loadout init --user=alice --orgs=personal --orgs=creative
loadout init --user=work  --orgs=work
```

---

## CLI Interface

```bash
loadout init --user=<name> --orgs=<org1> --orgs=<org2>  # bootstrap a user
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
2. Generate SSH key
3. Register SSH key with GitHub via 1Password + gh CLI
4. Switch git remotes from HTTPS to SSH
5. Build dotfiles (merge base + org layers)
6. Run `brew bundle` from `~/.dotfiles/Brewfile`
7. Run `loadout globals` for non-Homebrew installs
8. Apply macOS defaults via `macos/` scripts
9. Install launch agent for display detection
10. Save loadout config (`~/.dotfiles/.loadout.toml`)

### `loadout update`

```
git pull ~/.dotfiles && git pull ~/.dotfiles-private
loadout build
brew update && brew bundle --file=~/.dotfiles/Brewfile
loadout globals
```

### `loadout upgrade`

Everything in `update` plus `brew upgrade` — run intentionally, can break things.

### `loadout build`

Merges three layers of dotfile configuration:

1. **Public base** — `~/.dotfiles/dotfiles/base/` (lowest priority)
2. **Private base** — `~/.dotfiles-private/dotfiles/base/` (middle priority, optional)
3. **Org overlays** — `~/.dotfiles-private/dotfiles/orgs/<org>/` (highest priority)

| File type | Strategy |
|-----------|----------|
| `.zshrc`, `.aliases` | Concatenation — layers appended with separators |
| `.gitconfig` | Native `[include]` — git handles merge |
| JSON | Deep merge, later layers win on conflict |
| YAML | Deep merge, later layers win on conflict |
| Unknown | Later layer replaces earlier |

Output staged to `~/.dotfiles/build/` via an atomic temp-dir-then-swap pattern, then copied to `~/`. Existing files are backed up to `~/.dotfiles/backups/` with UTC timestamps before overwriting. Idempotent — safe to re-run.

### `loadout globals`

Installs non-Homebrew tools idempotently:

- Claude Code: `npm install -g @anthropic-ai/claude-code`
- nvm + node LTS
- pyenv + latest stable Python
- npm globals and pip globals per org config

### `loadout check`

Warn-only health check — never mutates anything. Currently checks:

```
✓  Homebrew       brew found on PATH
✓  Git            git version 2.x.x
!  Node.js        node not found on PATH
✓  Python         Python 3.x.x
✓  1Password CLI  op found on PATH
✓  GitHub SSH     Hi yourname! ...
✓  Claude Code    claude found on PATH
✓  Brewfile       found at ~/.dotfiles/Brewfile
```

Future checks (planned): devbox reachability, canvas staleness, AWS credential expiry, Brewfile diff.

---

## Dotfile Build System

Stow is replaced by a Python build step. No symlinks — layers merge cleanly.

```
~/.dotfiles/dotfiles/base/   +   ~/.dotfiles-private/dotfiles/base/   +   ~/.dotfiles-private/dotfiles/orgs/work/
       .zshrc                            .zshrc                                     .zshrc
       .gitconfig                        .gitconfig                                 .gitconfig
            │                                │                                          │
            └──── public base ───────────────┴──── private base ────────────────────────┘
                                                        │
                                              ~/.dotfiles/build/     ← staged output
                                                        │
                                                    copy to ~/       ← written to final locations
```

The private base layer is optional — when `~/.dotfiles-private/dotfiles/base/` does not exist, the pipeline falls back to the two-layer model (public base + org overlays).

`.gitconfig` uses git's native `[include]` mechanism — no merge logic needed:

```ini
# base .gitconfig (built output)
[include]
    path = ~/.gitconfig.d/private-base
[include]
    path = ~/.gitconfig.d/work
```

```ini
# ~/.gitconfig.d/work
[user]
    email = you@company.com
    signingkey = ~/.ssh/id_ed25519_work
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
├── __init__.py      # package root
├── brew.py          # shared Homebrew helpers
├── build.py         # dotfile merge logic (MergeStrategy enum)
├── check.py         # health check — warn only
├── cli.py           # Click CLI entry point + main()
├── config.py        # LoadoutConfig dataclass + TOML I/O
├── core.py          # stable API facade for aida-loadout-plugin
├── display.py       # macOS display profile switching
├── exceptions.py    # custom exception hierarchy
├── globals.py       # non-Homebrew installs (npm, pip, nvm, pyenv)
├── init.py          # full machine bootstrap flow (10-step)
├── py.typed         # PEP 561 marker
├── runner.py        # shell runner with dry-run support
├── ui.py            # Rich console helpers
└── update.py        # update + upgrade commands
```

---

## Naming Conventions

kebab-case everywhere: `[a-z0-9-]`, no leading/trailing dashes.

| Thing | Convention | Example |
|-------|-----------|---------|
| Org names | kebab-case | `personal`, `work`, `creative` |
| User names | lowercase | `alice`, `work` |
| AWS profiles | kebab-case | `work-main`, `personal-main` |

---

## Platform Support

macOS + Linux/*nix. No Windows — intentional. The `macos/` layer is the only macOS-specific piece. A `linux/` sibling can be added surgically later without touching anything above it.
