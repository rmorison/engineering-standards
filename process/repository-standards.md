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
| public | The repository is public, or **may become public**: unless a decision to keep it private is recorded, for example in its README, treat it as one that may. A leak in history cannot be retracted after the fact, so a repository that might be opened later adopts the public items that guard against leaks now: the license decision and value rules. Items that depend on a GitHub feature of public repositories, private vulnerability reporting and the chooser link to it, follow actual visibility and switch on in [Going Public](#going-public) |
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

**Private:** recommended, pointing to an internal channel, including for a private repository that may become public. GitHub's private vulnerability reporting is available for public repositories only (checked 2026-09-27, same page), and people who can read a private repository are already inside the team.

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

**Public, with a `SECURITY.md`:** the chooser config is required, with a contact link to the private vulnerability report, so a reporter choosing a new issue is sent away from a public one. As with `SECURITY.md`, this follows actual visibility: a private repository that may become public adds the link when it goes public.

Issue templates may apply only labels defined in [Label Strategy](./issue-tracking.md#label-strategy). A template that applies any other label creates it on first use.

## Leak Gate

The gate protects the holder of a value list from publishing their private values by mistake, whether the mistake is theirs, their agents', or a contributor's. It is not a control against someone who means to leak or to get around it.

A leak gate fails a change that would publish something that must not be published. It checks files and commits before they reach the default branch, and it says plainly what it cannot see.

This repository's gate is [gitleaks](https://github.com/gitleaks/gitleaks), a single binary, so any repository can run it whatever its language. This follows [the rule](../docs/solutions/tooling-decisions/adopter-checks-ship-in-the-adopters-ecosystem.md) that a check an adopting project runs must ship in that project's ecosystem or as one static binary.

### Rule Categories

| Category | Scans for | Trigger | Where it runs |
|---|---|---|---|
| Credentials | Tokens, keys and passwords | always | CI and locally |
| Shape rules | Values that are wrong by their form, whatever the value: today, an absolute home-directory path | always | CI and locally |
| Value rules | Specific private values: private repository names, internal hostnames and URLs, account handles | public (required), distributed (recommended) | Locally only |

These categories come from leaks that happened. This repository once published a private repository's name, a URL into that private repository, and an absolute home-directory path out of a contributor's machine. The first two are value rules and the third is a shape rule.

**Credentials.** A repository whose language standard names a credential scanner follows it: for Python, see [Secret Detection](../code/python-standards.md#secret-detection). Any other repository uses gitleaks' default rules, which the committed configuration below includes. A Python project that keeps detect-secrets still runs gitleaks for the shape and value rules; [Using gitleaks Instead](../code/python-standards.md#using-gitleaks-instead) makes gitleaks its only scanner.

**Shape rules** are committed, because a shape names no value. A committed list of the values themselves would be the leak it guards against. An adopter may add shape rules for its own domain to `.gitleaks.toml`. A project that handles personal financial data, for example, adds formatted account-number shapes. Such a rule, and any allowlist entry it needs, still names no value: not a real institution's number, the fixed prefix of the project's own accounts, or a real test account.

**Value rules** run only on the machine of someone who holds the private list. CI never runs them: its log is public for a public repository, and the list must never reach it.

### Adopting the Gate

Copy these files from this repository:

- `.gitleaks.toml`: the committed rules. It extends gitleaks' default rules with the home-directory path rule and its allowlist of non-identifying directories such as `runner` and `linuxbrew`.
- `scripts/gitleaks-report.tmpl`: the report template. Findings print as file, line and rule, never the matched text.
- `scripts/leak-gate.sh`: the local wrapper that adds value rules. It needs `sh`, git, gitleaks and standard POSIX utilities, and `iconv` when a value list is declared.
- `scripts/install-gitleaks.sh`: installs the pinned gitleaks. It is the only file that holds the gitleaks version and tarball hashes.
- `.github/workflows/leaks.yml`, with `scripts/test-leak-gate.sh` and `scripts/test-install-gitleaks.sh`: the CI job, and the fixtures that prove every rule fires and the install fails closed before any scan is trusted.

Install gitleaks in CI and on every developer machine that runs the hook. Without it on `PATH`, or `GITLEAKS` naming it, the wrapper refuses every commit with one line saying that gitleaks was not found and to run `sh scripts/install-gitleaks.sh`. `scripts/install-gitleaks.sh` installs it. CI's Install gitleaks step in `leaks.yml` runs it, as does the step in [Using gitleaks Instead](../code/python-standards.md#using-gitleaks-instead).

On a developer machine, or from a `make dev` target, run it from the repository root. It installs into `~/.local/bin`, or into the directory given as its argument:

```bash
sh scripts/install-gitleaks.sh
```

It picks the Linux or macOS tarball for x86_64 or arm64 from `uname` and checks it against the pinned SHA-256. On a mismatch, a failed download or any other platform it exits non-zero and installs nothing. It never pipes `curl` into a shell, downloads into a temporary directory rather than the working tree, and never prompts, so `make dev` and CI can run it unattended. It prints the installed path. When the `gitleaks` on `PATH` is a different one, it says so: add the directory to `PATH`, or set `GITLEAKS` to the printed path. A `~/.local/bin` the script creates reaches `PATH` only in a new login shell, and only where the shell profile adds it, as Debian's and Ubuntu's default profile does. macOS does not add it, so add it in the shell profile.

The pin block at the top of the script, `GITLEAKS_VERSION=` followed by one `SHA256_<os>_<arch>=` line per tarball, is a stable format, and so is the output of `sh scripts/install-gitleaks.sh --pins`. An upgrade changes the values, never the names or the form, so an adopting project can copy the script whole each time.

The script was run on x86_64 Linux on 2026-10-04 and installed gitleaks 8.24.2. `scripts/test-install-gitleaks.sh` proves, without the network, that it refuses a tampered tarball whether it checks with `sha256sum` or with `shasum -a 256` as on macOS, a failed download, a machine with neither tool, an unknown platform, a missing `HOME`, and a directory where the binary goes. It also proves that each platform requests its own tarball and checks it against its own hash, that a matching tarball installs only `gitleaks` and replaces one already there, and that an interrupted install leaves nothing behind; CI runs it. The script was not run on arm64 Linux or on macOS. Those three hashes were computed from the downloaded tarballs and match the release's checksums file.

To upgrade, change the version and every hash in the script's pin block together. Take each new hash from the downloaded tarball and compare it with the release's `gitleaks_<V>_checksums.txt` before writing it in. That file comes from the same release, so the release is trusted once, at the upgrade, and the pinned hash catches any later replacement of the tarball. Then install the new version and run `sh scripts/test-leak-gate.sh` to prove the rules still fire on it. Nothing else in this repository holds the version or a hash. `node scripts/check-docs.mjs` fails if a hash, a versioned tarball name, a gitleaks release download, a `go install` of gitleaks at a version, or a `rev` on a gitleaks pre-commit hook appears anywhere else. An adopting project re-copies `scripts/install-gitleaks.sh` from this repository, and `scripts/test-install-gitleaks.sh` when it has changed too, then runs the install again. That copy is the only one it keeps.

The job scans every commit the change adds, merge commits included (with git's `-m`, since a plain `git log` shows no changes for a merge), and with git's `--text`, so a `.gitattributes` entry cannot hide a text file's changes as binary. A leak added in one commit and removed in the next still fails. It then scans the whole tree, so existing content is checked against a newly added rule. Every gitleaks call runs without `-v` and prints only through the template. With `-v`, gitleaks prints the line around each match, which can hold a second secret, and prints file paths, which can hold a private value; `--redact` masks only the match itself (gitleaks 8.24.2, run 2026-09-27). Every call also passes `--ignore-gitleaks-allow`, so an inline allow comment suppresses nothing. A Python project whose standard permits reviewed allow comments under `tests/` ([Secret Detection](../code/python-standards.md#secret-detection)) drops that flag from `leaks.yml`, sets `LEAKGATE_HONOR_ALLOW=1` for `scripts/leak-gate.sh` so local runs agree with CI, and keeps the `make security` pragma check, which confines the comments to `tests/`. The opt-in applies to the committed rules only; value rules ignore allow comments always. None of the copied files contains the literal marker, so copying them does not trip that pragma check.

A pull request can weaken its own CI run by editing `.gitleaks.toml`, adding an entry to `.gitleaksignore`, marking files with `.gitattributes`, editing `scripts/install-gitleaks.sh`, which chooses the gitleaks binary the job runs, or editing the workflow. An agent that turns a red check green this way does it by mistake as easily as on purpose. Give those five files required review, for example through `CODEOWNERS`. That review needs more than one maintainer identity. A pull request's author cannot approve it, so in a one-person repository the required review never happens: the change either merges unreviewed through an admin's bypass, which branch protection allows by default, or stays blocked.

### Private Values

The value list is a plain text file with one literal value per line. Blank lines and lines starting with `#` are ignored. Keep it outside every repository. The wrapper turns each value into a case-insensitive literal match on file contents, so a value is never read as a regular expression. It also checks what gitleaks does not read: the path of every file the scanned commits or staged changes touch, including binary, empty, renamed and non-ASCII-named files; in `range` and `history`, the author, committer and message of each commit; and the staged contents of any file git's staged diff shows as binary, whether because of `.gitattributes` or its content. Findings name the list line, never the value. It rejects, by line number only, a line it cannot quote safely: one holding `\E` or `'''`, one that is not valid UTF-8, one with a control character, one shorter than four characters, or one that starts or ends with a non-ASCII space, which usually comes from pasting and would never match. Prefer values of six characters or more: `range` and `history` scan binary content, where a short value can match by chance.

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

Keep the list out of a dotfiles repository. A config directory tracked in git puts the list one commit away from being published, and the wrapper warns when the list sits in a git work tree that does not ignore it. It cannot see a bare dotfiles repository used through `git --git-dir=~/.dotfiles --work-tree=~`, since nothing in the list's directory leads git to that repository.

### Running It Locally

The wrapper takes one of four modes:

```bash
sh scripts/leak-gate.sh staged                 # what is staged: run it as a pre-commit hook
sh scripts/leak-gate.sh pre-push               # what a push would send: run it as a pre-push hook
sh scripts/leak-gate.sh range <base>..<head>   # a commit range: a pull request's commits before merging
sh scripts/leak-gate.sh history                # every ref, and commit and tag messages
```

To run it on every commit, make it the clone's pre-commit hook. The main checkout and every worktree of a clone share one hooks directory, so the hook also runs on branches that predate the gate. Where the commit's parent has no `scripts/leak-gate.sh`, the hook skips the check with a message instead of refusing the commit. Where the parent has the script but the working tree does not, because the commit deletes or renames it or a sparse checkout leaves `scripts/` out, the hook refuses the commit; removing the gate on purpose takes `git commit --no-verify`. `git rev-parse --git-path` finds the hooks directory in a worktree too, where `.git` is a file:

```bash
hook="$(git rev-parse --git-path hooks)/pre-commit"
cat > "$hook" <<'EOF'
#!/bin/sh
[ -f scripts/leak-gate.sh ] && exec sh scripts/leak-gate.sh staged
if git cat-file -e HEAD:scripts/leak-gate.sh 2>/dev/null; then
  echo "leak-gate: HEAD has scripts/leak-gate.sh but the working tree does not; commit refused" >&2
  exit 1
fi
echo "leak-gate: this branch has no scripts/leak-gate.sh; check skipped" >&2
EOF
chmod +x "$hook"
```

The hook runs whichever `scripts/leak-gate.sh` the checked-out branch holds, on the machine that holds the list. On a branch you did not write, such as a contributor's pull request checked out to push a fixup, that is code you have not reviewed running where the list is. Commit with `--no-verify` and run the pre-merge check below from the default branch's checkout instead.

**Before merging a pull request**, a maintainer who holds the list runs the value rules over its commits. Run from the default branch's own checkout, never from the pull request's: the pull request can edit the wrapper, `.gitleaks.toml` and `.gitleaksignore`, and this machine holds the list. A mistaken edit there would make the check pass on the pull request's own terms, and running the default branch's copy costs nothing, so the rule holds whatever the author intended.

```bash
git fetch origin pull/<N>/head:refs/leakgate/pr-<N>
sh scripts/leak-gate.sh range origin/main..refs/leakgate/pr-<N>
```

It exits 0 when clean, 1 when it finds a leak, and 2 on a usage, list or gitleaks error.

**With the pre-commit framework.** A repository whose hooks run through the [pre-commit](https://pre-commit.com) framework uses an entry in its `.pre-commit-config.yaml` instead of the hand-written hook, because `pre-commit install` owns the same `.git/hooks/pre-commit` file. Use one form per hook. `pre-commit install` renames a hand-written hook to `pre-commit.legacy` and still runs it, so the gate would run twice; `pre-commit install -f` replaces it instead. The entry runs the same wrapper with the gitleaks installed in [Adopting the Gate](#adopting-the-gate), so CI, the hooks and a maintainer's own runs share one pinned binary. The framework reads each branch's own `.pre-commit-config.yaml`, so a branch that predates the entry does not run it and needs no guard. A branch with no `.pre-commit-config.yaml` at all is the framework's own matter (`pre-commit install --allow-missing-config`).

```yaml
repos:
  - repo: local
    hooks:
      - id: leak-gate
        name: leak gate
        entry: sh scripts/leak-gate.sh staged
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-commit]
      - id: leak-gate-pre-push
        name: leak gate (pre-push)
        entry: sh scripts/leak-gate.sh pre-push
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
```

```bash
pre-commit install --hook-type pre-commit --hook-type pre-push
```

`pass_filenames: false` is there because the wrapper reads git's index itself. `always_run: true` is there because, without it, the framework skips a hook when no changed file matches, and that would skip a commit that only deletes files. The `stages` name needs pre-commit 3.2 or later. A project that sets `LEAKGATE_HONOR_ALLOW=1` (see [Adopting the Gate](#adopting-the-gate)) uses `entry: env LEAKGATE_HONOR_ALLOW=1 sh scripts/leak-gate.sh staged`, and the same prefix for `pre-push`. The framework shows a passing hook's output only with `--verbose`, so confirm once that the value rules run, with `pre-commit run leak-gate --verbose`: the line saying value rules were skipped must not appear on a machine that holds the list. The entry checks commits only. `pre-commit run --all-files` runs it against an empty index, so it reports no leaks having scanned nothing. CI's coverage comes from `leaks.yml`.

**Before pushing**, the `pre-push` mode scans every commit the push would give the remote: commit messages, author and committer identities and paths with the value rules, and file contents with every rule. It is the only local check of a commit message, and of a commit made with `--no-verify`. For each ref it scans the pushed commits, less the remote's old commit for that ref, less the commits on the remote's tracking refs. So an existing branch scans what is new, a new branch scans the commits that remote had on no branch when it was last fetched, a force push scans what the remote lacks, and a deletion scans nothing.

The tracking refs are trusted only for a configured remote that pushes where it fetches from, whose name has no `/`, and whose name no other remote's name extends with a `/`. A push to a URL, to a remote with a separate `pushurl`, to a remote named like `origin/private`, or to `origin` beside such a remote has no exclusion, so it scans everything the pushed commits reach, as `history` would. A remote with several `url` values pushes to each but fetches from the first, and the check trusts its tracking refs for all of them; give such a remote one URL, or push to each by URL. The check also assumes `refs/remotes/<name>/` holds only that remote's refs, which a custom `fetch` refspec on another remote, or refs left behind by deleting a remote's config section by hand, would break. The same happens with a remote never fetched, or an empty new remote. Such a push refuses on any finding already in the history, not just on new ones. When the remote already has that history, `git fetch <remote>` first clears it. For an empty remote, run `sh scripts/leak-gate.sh history`, review what it finds, and push with `--no-verify`. Tracking refs that are out of date work the same way. After a remote's URL changes, or after a history rewrite removes a commit from the remote, run `git fetch --prune <remote>` before pushing, or old tracking refs can hide commits from the check.

With the pre-commit framework, the `leak-gate-pre-push` entry above does this. The framework passes its hooks only one ref of a push (pre-commit 4.6.2): the first that is not a deletion and not a ref whose old commit is not here and that adds nothing new, even when that ref sends nothing, as a force push that rewinds a branch does. So `git push --all`, `git push --tags`, or `git push --follow-tags` with a new tag gets only one ref scanned. Push one ref at a time, or use the hand-written pre-push hook, which sees every ref. For a new branch the framework works out the commits already pushed from git's own `--remotes=<name>` match, even when the remote has a `pushurl` or a name that reaches another remote's refs, so in this form such a push is scanned only from those commits on. Run by hand as `pre-commit run --hook-stage pre-push`, the entry refuses, because the framework then passes it no refs.

To run it as a hand-written hook, install it the same way as the pre-commit hook. It skips with a message where the checked-out branch has no `scripts/leak-gate.sh`, or one too old to have the `pre-push` mode. It refuses where `HEAD` has the script but the working tree does not. Like the pre-commit hook, it runs the checked-out branch's wrapper whatever is being pushed, so a skip covers the whole push.

```bash
hook="$(git rev-parse --git-path hooks)/pre-push"
cat > "$hook" <<'EOF'
#!/bin/sh
if [ -f scripts/leak-gate.sh ]; then
  grep -q 'pre-push)' scripts/leak-gate.sh && exec sh scripts/leak-gate.sh pre-push "$@"
  echo "leak-gate: this branch's scripts/leak-gate.sh has no pre-push mode; push not checked" >&2
  exit 0
fi
if git cat-file -e HEAD:scripts/leak-gate.sh 2>/dev/null; then
  echo "leak-gate: HEAD has scripts/leak-gate.sh but the working tree does not; push refused" >&2
  exit 1
fi
echo "leak-gate: this branch has no scripts/leak-gate.sh; push not checked" >&2
EOF
chmod +x "$hook"
```

To pair the framework's pre-commit entry with the hand-written pre-push hook, leave `leak-gate-pre-push` out of `.pre-commit-config.yaml` and install the framework for pre-commit only, then install the block above:

```bash
pre-commit install --hook-type pre-commit
```

### Guarding Agent Sessions

The gate checks what goes into git. Agent sessions also post text to GitHub directly: pull request titles and bodies, issue bodies, comments and review text. `scripts/claude_leak_hook.py` is a Claude Code `PreToolUse` hook that runs before every Bash command a session runs and applies the value list to that text. Like the rest of the gate, it guards against mistakes, an agent's included. It does not stop a session that sets out to get around it.

It denies two kinds of command, with a message saying why and what to do instead:

- **Outbound text holding a listed value.** This covers `gh pr|issue create|edit|comment`, `gh pr|issue close|reopen --comment`, `gh pr review`, `gh release create|edit`, and `gh api` calls that write: any method other than GET, or any field or `--input`. The hook matches the command's text, heredocs and comments included, and the contents of every file passed as the body (`--body-file`, `-F`, `--notes-file`, `gh api -F key=@file`, `--input`). Words that only name a file or a directory are not matched, because `gh` sends a file's contents, never its path: those file operands, redirect targets, and `cd`, `pushd` and `popd` operands. Every other word is, including a path after `git -C`, `env -C` or `mkdir -p`, a release asset path (`gh` sends the file's name), and a path in a script nested more than three levels deep. Name such a path relative to the session's directory, or use it in a separate step. Matching is literal and case-insensitive, and the message names the list line, never the value. To resolve a relative body file, the hook follows `cd`, `pushd` and `popd` in the command, including a `cd` to a glob that matches exactly one directory, and the denial says when it could not follow one. A body file that does not exist yet, or that the same command writes, is denied unless the command writes it only from a heredoc, whose text the hook reads from the command. `sed -i`, `gsed -i` and `perl -i`, in all their spellings, count as writing every file they name. So is a body file that is not a regular file, such as a FIFO or a device, and one over 10 MiB. Write the file in one step and post it in the next. Commands after shell keywords such as `then` and `do`, inside `$(...)` or backticks, and inside `sh -c` or `eval` are checked like any other.
- **Switching the git-side gate off.** This covers `--no-verify` on any git command, `git commit -n`, `git -c core.hooksPath=…`, a `git config` write of `core.hooksPath`, and `SKIP=` on git or pre-commit, which is how the pre-commit framework skips a hook.

It reads the global list only, `git config --global leakgate.values`. The text goes to GitHub, not into the clone, and `gh -R` can target any repository, so a clone's `--local` setting, `none` included, does not apply. With no global list declared, or `none`, it allows outbound commands and says value rules were skipped. With a declared list that is missing, unreadable or empty, or that holds a line the wrapper would reject, it denies outbound commands until the list is fixed. It reads the list exactly as the wrapper does, and `scripts/test_claude_leak_hook.py` runs both over the same lists.

Post GitHub text with `--body-file`, from a file written in an earlier step, rather than inline. The hook then sees the whole text in one place, and so does a reviewer.

The uses of `--no-verify` in [Running It Locally](#running-it-locally), such as committing on a branch you did not write, removing the gate on purpose, or pushing to an empty remote, are for a person outside an agent session. Inside one, the hook denies them.

**Installing.** Claude Code's user settings belong to one OS account, so each account that runs agent sessions installs the hook and declares its own value list. The hook needs `python3` 3.10 or later, and git. Copy the script out of the default branch's checkout of this repository, never a pull request's, so that checking out another branch cannot change what guards the machine:

```bash
mkdir -p ~/.claude/hooks && install -m 755 scripts/claude_leak_hook.py ~/.claude/hooks/claude_leak_hook.py
```

Then add this entry to `~/.claude/settings.json`, merged with any `hooks` already there:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/.claude/hooks/claude_leak_hook.py\" || exit 2"
          }
        ]
      }
    ]
  }
}
```

Claude Code blocks a call only when a hook exits 2, so `|| exit 2` makes a broken install deny every Bash command rather than allow them. If that happens, fix `python3` or the copied script, or remove the entry. Copy the script again whenever it changes on the default branch.

The copy command and the settings command were run on 2026-10-04 under bash 5.1 on Linux with Python 3.10, against a scratch home directory. The installed hook denied a listed value and `git commit -n` and allowed clean text. With `python3` missing, the script missing, a planted import failure or a planted syntax error, it denied every command. They were not run under zsh or on macOS.

**What it does not see:**

- GitHub MCP write tools. They are not scanned yet.
- Text produced when the command runs, as in `--body "$(cat f)"`, `--body "$X"`, `--body-file <(cat f)`, or a pipe into `--body-file -`, including a path the shell expands, such as `$(pwd)` or `$PWD`, and text encoded so it no longer matches literally, such as `\u` escapes in a JSON `--input` file.
- A body file the hook resolves differently from the shell: a relative path after a change of directory it cannot follow, such as a `cd` to a variable or inside a subshell, a `cd` before a `$(...)` that names a relative file, which the hook resolves from the directory the command started in, or a `$VAR` path the command itself reassigns. It usually resolves to no file and is denied.
- A body file given in a cluster of short flags, such as `gh pr create -dF body.md`. The hook does not read it, so its contents are not scanned.
- A body file another program rewrites in the same command, such as `awk -i inplace`, `ruby -i`, `yq -i`, `ed`, `ex`, `sort -o`, `sponge`, `prettier --write`, `dd of=`, `truncate`, `patch`, `rsync`, `git checkout` or `git restore`, `curl -o`, `wget -O`, or a script. The hook reads the file as it is before the command runs.
- The contents of release assets.
- Commands run through `xargs` or `find -exec`, other GitHub clients such as `curl`, and `gh` subcommands outside the list above, such as `gh gist create`, `gh repo edit --description` and `gh pr merge --body`.
- Forms that take intent: abbreviated long options such as `--no-veri`, combined short flags such as `-nm`, config set through `GIT_CONFIG_COUNT` and `GIT_CONFIG_KEY_<n>` variables, editing or deleting the hook file or its settings entry, and wrapping a command in `eval`, a nested shell such as `bash -lc`, or a wrapper such as `sudo` or `nice`, or spelling an override as `-ccore.hooksPath` or a separate `--config-env`. The hook catches some of the wrapped and respelled forms, but nothing tests that it does. `scripts/test_claude_leak_hook.py` pins the first three, and the `$(...)`, pipe, `awk -i inplace`, `sort -o`, `gh pr merge`, `gh gist create` and `curl` forms above, as still allowed, so a change that starts denying one fails until this list is updated.
- A clone whose `.claude/settings.json` or `.claude/settings.local.json` sets `"disableAllHooks": true`. Claude Code reads that setting after [settings precedence](https://code.claude.com/docs/en/hooks) applies, and project settings override user settings, so the hook does not run in that clone. Only hooks in managed settings ignore it.
- A session on a machine or account without the hook, and text a person posts through the web UI.

### What the Gate Cannot See

- **Commits made without the value rules.** Commits from an outside pull request, a web edit, or a CI job that commits never ran value rules. The maintainer's pre-merge run keeps such a value off the default branch. In a public repository the value is already published once the pull request exists, so a hit at that point follows the remediation below.
- **Commits the hook skipped.** The pre-commit hook skips on a branch whose parent commit has no `scripts/leak-gate.sh`, and `--no-verify` skips it anywhere outside an agent session that has [the agent-session hook](#guarding-agent-sessions). The hand-written pre-push hook skips the whole push, every ref included, when the checked-out branch has no wrapper or one without the `pre-push` mode; the pre-push check otherwise covers commits made with `--no-verify`. CI's commit scan still reports credential and shape findings in such a commit, but only after the push, when a public repository has already published it, and CI never runs value rules. For a pull request, the maintainer's pre-merge run covers value rules; a direct push has no second check.
- **Commit messages, pull request bodies, and branch and tag names.** gitleaks scans file contents. The wrapper adds paths, commit identities and, before a push, commit messages. Only the going-public sweep below checks ref names and annotated tag messages; a pushed tag is scanned only for the commits it adds, so a tag on a commit the remote already has has nothing to scan. CI checks none of them. Only [the agent-session hook](#guarding-agent-sessions) checks pull request bodies, and only for the `gh` commands it covers, on a machine where it is installed.
- **Later refs of a push, in the pre-commit framework's form.** The framework passes its pre-push hooks only one ref of a push. The hand-written pre-push hook sees every ref.
- **Files on gitleaks' default path allowlist.** Lock files, images and vendored paths are not scanned by the credential or shape rules; `package-lock.json` hid a home path in a test on 2026-09-27. The value rules do scan the text among them, such as lock files, because the generated value configuration does not extend the defaults. `scripts/test-leak-gate.sh` pins both behaviours.
- **Binary file contents, in part.** CI's commit scan and the wrapper's `range` and `history` pass `--text`, so every rule reads each changed file whatever git or `.gitattributes` calls it. CI's tree scan and the wrapper's committed rules in `staged` mode skip content that really is binary, such as an image or a PDF. In `staged` mode the value rules still match its bytes, and the wrapper always checks paths.
- **Allowlists on staged files git shows as binary.** The wrapper scans those from a temporary copy, so a path allowlist or `.gitleaksignore` fingerprint for them does not apply. A false positive there is cleared by fixing the file or its attributes, not by allowlisting.
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
