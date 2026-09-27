# Security Policy

## Reporting a Vulnerability

**Please do not open a public issue for a security problem.** Report it privately through GitHub's private vulnerability reporting: open the repository's Security tab, go to Advisories, and choose **Report a vulnerability**. The report reaches the maintainer privately, and you will get an acknowledgment within a few days.

This repository is documentation and a starter kit that other projects copy, so a security problem here is usually one that ships to them. In scope, especially:

- A permission rule in the starter kit's `.claude/settings.json` that auto-approves something its documentation says reaches a human
- A hook in the starter kit that can be made to run something it should not
- A check in `scripts/` or `.github/workflows/` that passes a leak it claims to catch, prints a secret or private value into a log, or can be given more privilege than it needs
- A standard whose instructions, followed as written, expose a secret

How a report is handled after it arrives follows [Security Fixes](process/technical-work-workflow.md#security-fixes).

## Supported Versions

The `main` branch. There are no release branches; a fix lands on `main`.
