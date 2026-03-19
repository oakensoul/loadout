# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: (Beta) |

## Reporting a Vulnerability

**Please do not open public issues for security vulnerabilities.**

### Preferred: GitHub Security Advisories

Report vulnerabilities through
[GitHub Security Advisories](https://github.com/oakensoul/loadout/security/advisories/new).
This allows us to discuss and fix the issue privately before public disclosure.

### Alternative: Email

If you are unable to use Security Advisories, send an email to
**github@oakensoul.com** with the subject line
`[SECURITY] loadout — <brief description>`.

### What to Include

- A description of the vulnerability and its potential impact.
- Steps to reproduce or a proof-of-concept.
- The version(s) of loadout affected.
- Any suggested fix, if you have one.

### Response Timeline

- **Acknowledgement** — within **72 hours** of your report.
- **Initial assessment** — within 7 days.
- **Fix or mitigation** — as soon as reasonably possible; we will coordinate
  disclosure timing with you.

## Scope

This policy covers:

- The **loadout CLI** application itself.
- **Direct dependencies** shipped with the loadout package.

This policy does **not** cover:

- Downstream dotfile or configuration content managed by loadout.
- Third-party plugins or extensions not maintained in this repository.
