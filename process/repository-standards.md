# Repository Baseline Standards

**Version**: 1.0
**Date**: 2026-09-27
**Status**: Active

## Overview

This document is the only place the repository baseline is defined: the files and checks a repository needs besides its code. That covers the license decision, a security policy, a contributing guide, issue and pull request templates, and a leak gate. Other documents tell you when an item matters and link here for what it requires. The baseline applies to public and private repositories alike, and to any language.

Each item has a **trigger**, the condition that makes it apply, and says under that trigger whether it is **required** or **recommended**. The required set is deliberately small. Add the recommended items as the repository grows, in keeping with the rest of these standards.

Governance files that are a choice rather than a baseline are out of scope here: a code of conduct, `CODEOWNERS` (except as a way to require review of the leak gate's files, below), and funding files.

## Triggers

**Reading the Trigger column.** A repository matches every trigger whose condition holds, and each item applies under each trigger that names it. When two cells apply to one item, the stricter one wins: a public repository's `SECURITY.md` is required and points to private vulnerability reporting. Most items depend on who contributes to the repository or who uses its code, not on whether it is public.

| Trigger | Holds when |
|---|---|
| always | The repository exists |
| public | The repository is public, or **may become public**: unless a decision to keep it private is recorded, for example in its README, treat it as one that may. A leak in history cannot be retracted after the fact, so a repository that might be opened later adopts the public items now |
| outside contributions | People outside the owning team open pull requests |
| distributed | Others use the code: a published package, a released binary, code a client runs, or a public repository people may copy |

| Item | always | public | outside contributions | distributed |
|---|---|---|---|---|
| [License decision recorded](#license) | required | | | |
| [`LICENSE` file](#license) | | required | | required |
| [`SECURITY.md`](#security-policy) | recommended (internal channel) | required (private vulnerability reporting) | | required when private (channel published where users see it) |
| [`CONTRIBUTING.md`](#contributing-guide) | recommended | | required | |
| [DCO sign-off](#developer-certificate-of-origin) | | | option | |
| [PR template, issue chooser config](#issue-and-pull-request-templates) | recommended | contact link required with `SECURITY.md` | | |
| [Credential scanning](#rule-categories) | required | | | |
| [Leak gate shape rules](#rule-categories) | required | | | |
| [Leak gate value rules](#rule-categories) | | required | | recommended (shipped code can carry internal names to its users) |

Skeletons of each file are in the [starter kit](../templates/README.md).

## License

**Always:** record the license decision where a reader will look for it: a `LICENSE` file, or a line in the README for a repository that is not licensed to anyone. "Proprietary, all rights reserved" is a decision too; an unrecorded one is a question the next person has to ask.

**Public or distributed:** commit a `LICENSE` file at the repository root. A public repository with no license is not open source. GitHub's documentation states that without a license, "the default copyright laws apply", and no one may reproduce, distribute, or create derivative works from the code ([Licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository), checked 2026-09-27). The same page notes that anyone can still view and fork a public repository. [choosealicense.com](https://choosealicense.com/) compares the common choices.

## Security Policy

`SECURITY.md` tells someone who finds a vulnerability how to report it without publishing it. It states which versions get security fixes and where to send a report. What happens to a report after it arrives is owned by [Security Fixes](./technical-work-workflow.md#security-fixes).

**Public:** required, and it points reporters to GitHub's private vulnerability reporting, not an email address. When the feature is enabled, reporters see a **Report a vulnerability** button on the repository's security advisories page, and the report reaches the maintainers privately. Owners and admins enable it under Settings, Code security ([Configuring private vulnerability reporting for a repository](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository), checked 2026-09-27). Enable it **before** committing a `SECURITY.md` that points at it, or the first reporter finds no button.

**Private:** recommended, pointing to an internal channel. GitHub's private vulnerability reporting is available for public repositories only (checked 2026-09-27, same page), and people who can read a private repository are already inside the team.

**Private and distributed:** required. Users of the code cannot see the repository, so publish the reporting channel where they can: the package page, the product's documentation, or a security page on the product's site.

GitHub reads `SECURITY.md` from the repository root, `docs/` or `.github/`, and falls back to one in the account's `.github` repository ([Creating a default community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file), checked 2026-09-27). Use the root.

## Contributing Guide

`CONTRIBUTING.md` tells a contributor how to get from a clone to a mergeable pull request: how to set up, which checks to run before opening a pull request, and where the commit and pull request conventions are. Link to [Git Branching Strategy](./git-branching-strategy.md) for conventions rather than restating them.

**Outside contributions:** required. It also states the terms contributions are accepted under, usually the project's own license ("inbound equals outbound").

**Always:** recommended. A new teammate needs the same setup steps a stranger does.

### Developer Certificate of Origin

The [Developer Certificate of Origin](https://developercertificate.org/) (DCO) is an option when accepting outside contributions: each commit carries a `Signed-off-by:` line in which its author certifies they have the right to submit it. Adopt it or not deliberately, and say which in `CONTRIBUTING.md`.

- **For:** it records provenance per commit with no contributor license agreement to sign, and a check can enforce it.
- **Against:** every commit needs the line, including fix-ups, which trips up first-time contributors.
- **Squash merges:** a squash merge that concatenates the pull request's commit messages leaves earlier sign-offs in the middle of the message rather than in its trailer block, where a DCO check looks. Decide where the sign-off must land before adopting DCO in a repository that squash-merges.
- **AI-assisted work:** a sign-off is a human's attestation. A `Co-Authored-By:` trailer naming an AI assistant does not replace it, and a commit made by a bot cannot carry one. The person who submits the change signs it off.

## Issue and Pull Request Templates

**Always:** a pull request template is recommended. It prompts for the fields in [PR Description](./git-branching-strategy.md#pr-description), plus any fields the [technical work workflow](./technical-work-workflow.md) asks of that kind of change. GitHub reads it from `.github/pull_request_template.md`, `docs/`, or the root ([Creating a pull request template](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository), checked 2026-09-27). Use `.github/`.

**Always:** an issue template chooser config, `.github/ISSUE_TEMPLATE/config.yml`, is recommended. `blank_issues_enabled` decides whether a blank issue is offered, and `contact_links` sends particular reports elsewhere ([Configuring issue templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository), checked 2026-09-27).

**Public, with a `SECURITY.md`:** the chooser config is required, with a contact link to the private vulnerability report, so a reporter choosing a new issue is sent away from a public one.

Issue templates may apply only labels defined in [Label Strategy](./issue-tracking.md#label-strategy). A template that applies any other label creates it on first use.

## Leak Gate

A leak gate fails a change that would publish something that must not be published. It checks files and commits before they reach the default branch, and it says plainly what it cannot see.

This repository's gate is [gitleaks](https://github.com/gitleaks/gitleaks), a single binary, so any repository can run it whatever its language. This follows [the rule](../docs/solutions/tooling-decisions/adopter-checks-ship-in-the-adopters-ecosystem.md) that a check an adopting project runs must ship in that project's ecosystem or as one static binary.

### Rule Categories

| Category | Scans for | Trigger | Where it runs |
|---|---|---|---|
| Credentials | Tokens, keys and passwords | always | CI and locally |
| Shape rules | Values that are wrong by their form, whatever the value: today, an absolute home-directory path | always | CI and locally |
| Value rules | Specific private values: private repository names, internal hostnames and URLs, account handles | public | Locally only |

These categories come from leaks that happened. This repository once published a private repository's name, a URL into that private repository, and an absolute home-directory path out of a contributor's machine. The first two are value rules and the third is a shape rule.

**Credentials.** A repository whose language standard names a credential scanner follows it: for Python, see [Secret Detection](../code/python-standards.md#secret-detection). Any other repository uses gitleaks' default rules, which the committed configuration below includes. A Python project that keeps detect-secrets still runs gitleaks for the shape and value rules; [Using gitleaks Instead](../code/python-standards.md#using-gitleaks-instead) makes gitleaks its only scanner.

**Shape rules** are committed, because a shape names no value. A committed list of the values themselves would be the leak it guards against.

**Value rules** run only on the machine of someone who holds the private list. CI never runs them: its log is public for a public repository, and the list must never reach it.

### Adopting the Gate

Copy these files from this repository:

- `.gitleaks.toml`: the committed rules. It extends gitleaks' default rules with the home-directory path rule and its allowlist of non-identifying directories such as `runner` and `linuxbrew`.
- `scripts/gitleaks-report.tmpl`: the report template. Findings print as file, line and rule, never the matched text.
- `scripts/leak-gate.sh`: the local wrapper that adds value rules. It needs `sh`, git, gitleaks and standard POSIX utilities, and `iconv` when a value list is declared.
- `.github/workflows/leaks.yml`, with `scripts/test-leak-gate.sh`: the CI job, and the fixtures that prove every rule fires before any scan is trusted.

Install gitleaks at a pinned version with its release checksum verified, as [Using gitleaks Instead](../code/python-standards.md#using-gitleaks-instead) shows, never piped from `curl` into a shell. The CI job pins 8.24.2.

The job scans every commit the change adds, merge commits included (with git's `-m`, since a plain `git log` shows no changes for a merge), and with git's `--text`, so a `.gitattributes` entry cannot hide a text file's changes as binary. A leak added in one commit and removed in the next still fails. It then scans the whole tree, so existing content is checked against a newly added rule. Every gitleaks call runs without `-v` and prints only through the template. With `-v`, gitleaks prints the line around each match, which can hold a second secret, and prints file paths, which can hold a private value; `--redact` masks only the match itself (gitleaks 8.24.2, run 2026-09-27). Every call also passes `--ignore-gitleaks-allow`, so an inline allow comment suppresses nothing. A Python project whose standard permits reviewed allow comments under `tests/` ([Secret Detection](../code/python-standards.md#secret-detection)) drops that flag from `leaks.yml`, sets `LEAKGATE_HONOR_ALLOW=1` for `scripts/leak-gate.sh` so local runs agree with CI, and keeps the `make security` pragma check, which confines the comments to `tests/`. The opt-in applies to the committed rules only; value rules ignore allow comments always. None of the copied files contains the literal marker, so copying them does not trip that pragma check.

A pull request can weaken its own CI run by editing `.gitleaks.toml`, adding an entry to `.gitleaksignore`, marking files with `.gitattributes`, or editing the workflow. Give those four files required review, for example through `CODEOWNERS`.

### Private Values

The value list is a plain text file with one literal value per line. Blank lines and lines starting with `#` are ignored. Keep it outside every repository. The wrapper turns each value into a case-insensitive literal match on file contents, so a value is never read as a regular expression. It also checks what gitleaks does not read: the path of every file the scanned commits or staged changes touch, including binary, empty, renamed and non-ASCII-named files; in `range` and `history`, the author, committer and message of each commit; and the staged contents of any file `.gitattributes` hides from git's diff. Findings name the list line, never the value. It rejects, by line number only, a line it cannot quote safely: one holding `\E` or `'''`, one that is not valid UTF-8, one with a control character, or one shorter than four characters.

Declare the list with a git config key holding its path. Declared once globally, it applies to every clone on the machine, including a fresh one:

```bash
git config --global leakgate.values ~/.config/leakgate/values
```

A repository whose own name or hosts are in the shared list would fail on every mention of itself. Point that clone at a different list, or opt it out:

```bash
git config --local leakgate.values ~/.config/leakgate/values-for-this-repo
git config --local leakgate.values none
```

With no declaration, or an opt-out, the wrapper runs the committed rules only and prints a line saying value rules were skipped. That is what an outside contributor gets, so nobody is blocked by a file they cannot have. With a declaration, a list that is missing, empty, unreadable or inside the repository fails. A value rule cannot be suppressed by `.gitleaksignore`: the wrapper fails if that file names one.

Keep the list out of a dotfiles repository. A config directory tracked in git puts the list one commit away from being published, and the wrapper warns when the list sits in a git work tree that does not ignore it.

### Running It Locally

The wrapper takes one of three modes:

```bash
sh scripts/leak-gate.sh staged                 # what is staged: run it as a pre-commit hook
sh scripts/leak-gate.sh range <base>..<head>   # a commit range: before pushing
sh scripts/leak-gate.sh history                # every ref, and commit and tag messages
```

To run it on every commit, make it the clone's pre-commit hook. `git rev-parse --git-path` finds the hooks directory in a worktree too, where `.git` is a file:

```bash
hook="$(git rev-parse --git-path hooks)/pre-commit"
printf '#!/bin/sh\nexec sh scripts/leak-gate.sh staged\n' > "$hook" && chmod +x "$hook"
```

**Before merging a pull request**, a maintainer who holds the list runs the value rules over its commits. Run from the default branch's own checkout, never from the pull request's: the pull request can edit the wrapper, `.gitleaks.toml` and `.gitleaksignore`, and this machine holds the list.

```bash
git fetch origin pull/<N>/head:refs/leakgate/pr-<N>
sh scripts/leak-gate.sh range origin/main..refs/leakgate/pr-<N>
```

It exits 0 when clean, 1 when it finds a leak, and 2 on a usage, list or gitleaks error.

### What the Gate Cannot See

- **Commits made without the value rules.** Commits from an outside pull request, a web edit, or a CI job that commits never ran value rules. The maintainer's pre-merge run keeps such a value off the default branch. In a public repository the value is already published once the pull request exists, so a hit at that point follows the remediation below.
- **Commit messages, pull request bodies, and branch and tag names.** gitleaks scans file contents. The wrapper adds paths, commit identities and, before a push, commit messages; the going-public sweep below also checks ref names and tag messages. CI checks none of them, and nothing checks pull request bodies.
- **Files on gitleaks' default path allowlist.** Lock files, images and vendored paths are not scanned by the credential or shape rules; `package-lock.json` hid a home path in a test on 2026-09-27. The value rules do scan the text among them, such as lock files, because the generated value configuration does not extend the defaults. `scripts/test-leak-gate.sh` pins both behaviours.
- **Binary file contents.** gitleaks skips a file whose contents are binary, such as an image or a PDF, so no rule reads it. The wrapper still checks its path. A text file that `.gitattributes` marks `-diff` or `binary` is still read: CI and the wrapper pass `--text`, and the wrapper scans such a file's staged contents directly.
- **Git LFS contents.** Only the pointer file is committed or checked out, so no rule reads what LFS stores.
- **Names on gitleaks' default global allowlist.** Extending the default rules also inherits an allowlist of placeholder-looking and path-shaped values, so the home-directory rule misses some user directory names, such as one letter repeated. `scripts/test-leak-gate.sh` pins that case.
- **Anything the rules do not describe.** A new kind of leak passes until a rule for it exists.

### When a Leak Is Found

- **A credential:** rotate it at the provider first, then remove it from the tree. It is compromised from the moment it was pushed. A history rewrite is worth considering only after rotation, and it does not retract what has already been fetched or served.
- **Anything else:** remove it from the tree going forward. A history rewrite changes every commit SHA, invalidates every clone, and does not retract what GitHub already serves from pull request refs, so it rarely pays for a value that grants no access.

### Why the Gate Is Separate from `check_secret_refs.py`

`scripts/check_secret_refs.py` holds the [Secrets](../code/python-standards.md#secrets) rule: every line of a committed `secret-refs.env` is a reference into a secret manager. That check allows only what it recognises in one dotenv file type and reads lines the way python-dotenv does. The leak gate is the opposite shape: it rejects what it recognises, in every file and commit. They share no logic, so they stay two checks.

## Going Public

Making a private repository public publishes its whole history, including the refs GitHub keeps for every pull request, which no history rewrite removes. Before changing the visibility:

1. Fetch every pull request head, so their commits are in the sweep:

   ```bash
   git fetch origin '+refs/pull/*/head:refs/remotes/origin/pull/*'
   ```

2. Run `sh scripts/leak-gate.sh history` with the value list declared. It runs every rule over all refs, merge commits included, and checks file paths, commit authors and committers, branch and tag names, and commit and annotated tag messages for values, printing only the matching commit, tag or object SHAs.
3. Review what the sweep cannot reach: issues, pull request bodies and comments, and Actions logs are published by the same switch.
4. If the sweep finds anything, or that GitHub-side content has not been reviewed, seed a fresh public repository from a clean tree instead of flipping this one.
5. After the flip, enable private vulnerability reporting, then commit the public `SECURITY.md`.

## What a Pass Means

A clean run means no rule that ran matched. It does not mean the repository is safe to publish. A longer value list feels like more safety, and it catches only the values someone thought to write down. Treat the gate as a floor under review, not a replacement for it.
