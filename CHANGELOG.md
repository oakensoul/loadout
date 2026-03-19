# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-03-13

### Added

- CLI commands: `init`, `update`, `upgrade`, `check`, `build`, `globals`, `display`.
- Dotfile merge engine with concat, gitconfig, JSON, YAML, and replace strategies.
- Homebrew integration for bundle install and upgrade.
- NVM/Node version management and global npm package installs.
- pyenv/pip version management and global pip package installs.
- macOS display profile switching via `display` command.
- Health check engine for verifying system state.
- 1Password CLI integration for GitHub authentication.
- Atomic build with automatic backup before applying changes.
- Dry-run support across all commands.
- Verbose mode for detailed output.

[Unreleased]: https://github.com/oakensoul/loadout/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/oakensoul/loadout/releases/tag/v0.1.0
