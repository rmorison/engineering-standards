---
title: A local pass proves only the tool versions it ran on
date: 2026-10-05
category: best-practices
module: leak-gate
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - "A shell script or test suite passes locally and also runs in CI or on an adopter's machine"
  - "A fixture sets up state with porcelain commands whose rules can change between versions, such as git remote add"
  - "A script resolves an executable with command -v and then runs it"
  - "A script parses the output of a utility whose GNU and BSD forms differ, such as wc, sed or date"
  - "Reporting a pushed head as verified"
resolution_type: workflow_improvement
related_components:
  - development_workflow
tags: [ci, verification, portability, git, dash, posix-shell, fixtures, tool-versions]
---

# A local pass proves only the tool versions it ran on

## Context

Issue #75 added two things to the leak gate, both proved by `scripts/test-leak-gate.sh`:
- [PR #79](https://github.com/rmorison/engineering-standards/pull/79): one-line refusal when gitleaks is missing;
- [PR #83](https://github.com/rmorison/engineering-standards/pull/83): a `pre-push` mode.

The work was done on a machine with git 2.34.1, dash as `sh`, and GNU coreutils. The suite ran under both `sh` and `bash` before each push. Three assumptions held only for the tool version or implementation under test. One failed in CI, one failed under the other shell on the same machine, and one is predicted on macOS. None was a mistake in what the code meant to do.

1. **A newer git refused a fixture's setup.** A fixture added a remote named `origin/private` beside `origin`, to prove the wrapper does not trust tracking refs that another remote's name can reach.
   - **Local:** git 2.34.1 accepted `git remote add origin/private …`, and the suite passed 119 of 119 under dash and bash on the PR's head.
   - **CI:** `ubuntu-latest` runs git 2.55.0, which refused it:

     ```text
     fatal: remote name 'origin/private' is a subset of existing remote 'origin'
     ##[error]Process completed with exit code 128.
     ```

     That is Actions run 37247455265 on PR #83. The suite runs under `set -e`, so the failed setup command ended it, and no fixture after it ran.
   - **The delay:** the head had been reported as verified from the local run, and nobody looked at CI on it. The red check sat for about 21 hours, until the lead found it before the merge.
2. **dash's `command -v` accepts any existing path.** PR #79 checked for gitleaks with `command -v "$GITLEAKS"`. For a name containing `/`:
   - bash checks that the file is executable;
   - dash, which is `sh` on Debian, Ubuntu and GitHub's Ubuntu runners, only checks that the path exists.

   So under dash, a `GITLEAKS` naming a directory, or a file without the execute bit, passed the check. The wrapper then ran it and printed the path and `gitleaks exited 126`, which breaks both the one-line promise and the no-path promise. The scoped Claude review on PR #79 found this by reading dash's source. Two new fixtures then failed under `sh` before the fix, and after it the check gave the one-line refusal under both shells (the reply on PR #79).
3. **BSD `wc` pads its count.** The missing-gitleaks fixtures counted output lines with `wc -l` and matched `"$rc:$lines:$out"` against `"2:1:"*`. BSD `wc`, as on macOS, prints `       1`, so the pattern would never match there. The same review flagged it. It was not run on macOS, because no macOS host was available.

## Guidance

**A pass is a statement about the tools it ran on. Name them, run on each one the script's users have, and read CI on the exact head before calling it verified.**

1. **Record the versions with the proof.** "119 passed" means little without the git, the `sh` and the OS it ran on. PR #83's body now names git 2.34.1 locally and git 2.55.0 in CI, with the run ID. When the standard states a tool's behaviour, it names the version too. For example, § Running It Locally in `process/repository-standards.md` gives the framework's one-ref pre-push limit "(pre-commit 4.6.2)".
2. **CI on the pushed head is part of the verification.** After a push, wait for the checks on that head before reporting it verified, for example with `gh pr checks <n> --watch`. A `pull_request` run tests the head merged into its base, so a stacked pull request's CI also changes when its base moves. A local run and a CI run are two environments, and only the one that was read counts. The fix for the first case was reported only after its CI run, Actions run 37379161341, showed git 2.55.0 and "119 passed, 0 failed".
3. **Run each shell the script claims to support.** A `#!/bin/sh` script runs under dash on Debian, Ubuntu and their CI runners, and may run under bash elsewhere. Running the suite under both `sh` and `bash` costs one more command. It is how the dash fix was confirmed, and how a bash-only fix would show itself.
4. **"Found" is not "runnable".** `command -v` answers whether a name resolves. Check that what it returns is a regular executable file before relying on it. The leak gate now does this (`scripts/leak-gate.sh:103-104`):

   ```sh
   gitleaks_path=$(command -v "$GITLEAKS" 2>/dev/null) &&
     [ -f "$gitleaks_path" ] && [ -x "$gitleaks_path" ] ||
   ```

5. **In fixtures, set up state with primitives that carry less version-specific policy.** `git remote add` enforces naming rules, and they changed somewhere between 2.34 and 2.55. `git config` and `git update-ref` write the state the code under test reads without those rules, though `update-ref` still checks ref-name format. So the fixture now writes the remote into the config and sets its tracking ref directly (`nested_remote` and the `update-ref` call in `scripts/test-leak-gate.sh`), and it passes on both versions.

   The product code keeps its guard, because a config written by an older git is still valid on a newer one. The wrapper reads remote names from the config as well as from `git remote` (`scripts/leak-gate.sh:172-173`), so it sees such a name whatever the running git lists.
6. **Normalise output you parse.** Strip padding and whitespace from a utility's output before comparing it: `wc -l | tr -d ' '` (`scripts/test-leak-gate.sh:638`).

## Why This Matters

The leak gate's suite exists so that a green CI run means every rule and every fixture fired. A suite that dies at a setup step on one git proves nothing on that git, and its failure says nothing about the gate itself. Had PR #83 merged on the local report, every later pull request's leaks job would have failed on `main`'s own fixtures.

The gate is also copied verbatim by adopting projects (rmorison/buzai copies the file set), so it runs on whatever git, `sh` and OS they have. A pass on one stack says nothing about theirs. Naming the stack a proof ran on is what lets a reader see what is still unproved.

The siblings each cover a different part of this:
- [prove-a-check-fails-before-trusting-it-passes](./prove-a-check-fails-before-trusting-it-passes.md) is about a check that passes because it cannot fail. Its habit 3, make a pin real, is the closest relative: the version under test must be the version that matters.
- [prove-a-pasted-command-from-the-docs-own-text](./prove-a-pasted-command-from-the-docs-own-text.md) is the closest. Its habit 5, "Say which shells and platforms the run covered, and mark the rest not run", is the rule behind guidance 1 and 3 here. That doc applies it to commands a reader pastes. This doc extends it to scripts, their fixtures and CI, and to tool versions as well as shells.
- [a-check-must-read-a-file-the-way-its-consumer-does](./a-check-must-read-a-file-the-way-its-consumer-does.md) says to pin the consumer version that fixtures were checked against. This doc applies the same idea to the tools a script runs.

## When to Apply

- Any shell script or fixture suite that runs both locally and in CI, or on adopters' machines
- Fixtures that build git state with porcelain (`remote add`, `branch`, `worktree add`, `tag`) rather than plumbing or config
- Code that resolves an executable with `command -v`, `which` or `type`, then runs it
- Code that parses `wc`, `ls`, `date`, `stat`, `sed -i`, `grep -P` or other utilities whose GNU and BSD forms differ
- Reporting a pushed head as verified, in a PR body, an issue comment or a message

## Examples

### Fixture setup a newer git refuses

Before, which failed on git 2.55.0:

```sh
git -C "$R" remote add origin/private "$WORK/p-nested-private.git"
git -C "$R" push -q origin/private secret
git -C "$R" fetch -q origin/private
```

After, which works on git 2.34.1 and 2.55.0:

```sh
nested_remote() {   # nested_remote <repo> <name> <url>
  git -C "$1" config "remote.$2.url" "$3"
  git -C "$1" config "remote.$2.fetch" "+refs/heads/*:refs/remotes/$2/*"
}
nested_remote "$R" origin/private "$WORK/p-nested-private.git"
git -C "$R" update-ref refs/remotes/origin/private/secret HEAD
```

With the wrapper's nested-remote check removed, the reworked fixture still fails with `exit 0, expected 1`, so it still holds the check.

### Found but not runnable

Against PR #79's first check, `command -v "$GITLEAKS"` alone, the two new fixtures failed under `sh` (dash):

```text
FAIL: wrapper, missing gitleaks, staged, a file without the execute bit: the output names the path or the value
FAIL: wrapper, missing gitleaks, staged, a directory: the output names the path or the value
Leak gate fixtures: 92 passed, 2 failed.
```

The review predicted from dash's source that the wrapper then prints the path and `gitleaks exited 126`. With the `-f` and `-x` test added, the reply on PR #79 records every unusable `GITLEAKS` value giving the one-line refusal under both shells, and every working one still scanning:

```text
           GITLEAKS                   dash          bash
gitleaks (bare name, on PATH)    exit 0, scans  exit 0, scans
<scratch>/gl-noexec              exit 2, 1 line exit 2, 1 line
<scratch> (a directory)          exit 2, 1 line exit 2, 1 line
<scratch>/missing                exit 2, 1 line exit 2, 1 line
```

### A count with padding

```sh
lines=$(printf '%s\n' "$out" | wc -l)               # GNU: 1   BSD: "       1"
lines=$(printf '%s\n' "$out" | wc -l | tr -d ' ')   # 1 on both
```

## Related

- [PR #79](https://github.com/rmorison/engineering-standards/pull/79) and [PR #83](https://github.com/rmorison/engineering-standards/pull/83): the review threads and run IDs for each case above
- [prove-a-check-fails-before-trusting-it-passes](./prove-a-check-fails-before-trusting-it-passes.md), [prove-a-pasted-command-from-the-docs-own-text](./prove-a-pasted-command-from-the-docs-own-text.md), [a-check-must-read-a-file-the-way-its-consumer-does](./a-check-must-read-a-file-the-way-its-consumer-does.md): the siblings compared under Why This Matters
