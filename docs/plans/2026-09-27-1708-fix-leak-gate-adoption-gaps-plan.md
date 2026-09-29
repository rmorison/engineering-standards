---
title: Close the Leak Gate's Adoption Gaps - Plan
type: fix
date: 2026-09-27
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
origin: https://github.com/rmorison/engineering-standards/issues/62
---

# Close the Leak Gate's Adoption Gaps - Plan

## Goal Capsule

- Objective: a developer who follows `process/repository-standards.md` literally ends up with a working leak gate. Their commits on old branches and worktrees still go through, gitleaks is on their `PATH`, the dotfiles warning fires only when it is true, and every gitleaks binary the standards fetch is checked against a hash that a replaced release asset cannot match.
- Means: a guarded pre-commit hook (KTD1), a pinned SHA-256 literal instead of the release checksum file (KTD3, KTD4), git's local environment cleared around the list-directory probes (KTD2), and the bot's item-5 fixture if it proves it can fail (KTD6).
- Authority: issue #62 and its two comments (items 4 and 5) are the spec. Where this plan and the issue disagree, the issue wins and the disagreement goes on the issue as a question.
- Execution profile: edits to `scripts/leak-gate.sh`, `scripts/test-leak-gate.sh`, `.github/workflows/leaks.yml`, `process/repository-standards.md`, and `code/python-standards.md` § Using gitleaks Instead only, plus this plan file. No edits to `templates/.claude/settings.json`, `scripts/check-template-kit.mjs`, `templates/README.md`, `code/python-standards.md` § The Limit, `docs/solutions/`, or `pm-trial/`.
- Stop conditions: stop and ask on the issue if the item-4 fixture does not fail against the unfixed wrapper, or if the pinned-SHA step does not fail on a tampered tarball. Stop and ask if neither the bot's fixture nor a replacement can be made to fail without `-a` and the fallback in KTD6 would drop coverage that someone relies on.
- Finishes the work: `ce-work` on branch `62-leak-gate-adoption-gaps`, shipped as one PR that closes #62. Rod merges.

---

## Product Contract

### Summary

Replace the one-line hook in the standard with the guarded hook that is already in use on the maintainer's machine. Add a developer-machine gitleaks install next to it. Pin the linux_x64 tarball's SHA-256 as a literal in `leaks.yml`, in the Python standard's CI step, and in the local install, and stop fetching the release checksum file. Clear git's repository environment around the wrapper's dotfiles probe so it answers for the list's directory. Make the Latin-1 fixture able to fail, or drop it and reword the comment.

### Problem Frame

#61 shipped the leak gate. Installing it on a real machine found five gaps, and each one either blocks an adopter or quietly weakens the gate.

- The documented hook runs `sh scripts/leak-gate.sh` unconditionally. Every worktree of a clone shares the hooks directory, so on a branch older than the gate the script is missing, `sh` exits 127, and the commit is refused. The usual reaction is to delete the hook, which turns the gate off.
- The standard never tells a developer to install gitleaks locally. Its only install instructions are a CI step that installs into `$RUNNER_TEMP`, so every hook run fails with `gitleaks exited 127`.
- Both CI installs verify the tarball against `gitleaks_<V>_checksums.txt` from the same release. A replaced asset would ship with a checksum file that matches it.
- Git exports `GIT_DIR` to hooks. With it set, `git -C <list dir> rev-parse --is-inside-work-tree` answers for the repository being committed to, so the dotfiles warning fires on every hook run. A warning that always fires gets ignored.
- The Latin-1 fixture passes with and without `-a`, so it pins nothing, and the comment it backs states a behaviour nobody reproduced.

### Key Decisions

- **Drop the release checksum file once the SHA-256 is pinned.** A tarball that matches the pinned literal also matches an honest checksum file. A tarball that does not match fails on the literal before the file matters. The file's one use is at upgrade time, when a maintainer compares the new literal against it. Governs R6, R7, R8.
- **macOS is given but marked as not run.** No macOS host is available. The darwin tarball hashes are checked on Linux against the release checksum file, so the literals are right. The install on macOS itself (`shasum -a 256 -c`, `~/.local/bin` on `PATH`) is marked as not run. Governs R5.
- **Item 5 takes the bot's approach only if it is proven.** The bot's commit `186f0af` is cherry-picked only after the suite is shown to fail with `-a` removed from `sha_matches`. Governs R11.

### Requirements

**Pre-commit hook (item 1)**

- R1. In a scratch repository, the hook in the standard exits 0 and prints a message naming the skipped check when it runs in a worktree whose branch has no `scripts/leak-gate.sh`.
- R2. The same hook refuses a commit whose staged content holds a private value, on a branch that has the script.
- R3. The standard says why the guard exists: the main checkout and every worktree share one hooks directory.

**Developer-machine install (item 2)**

- R4. § Adopting the Gate gives a Linux install that ends with gitleaks on `PATH` (for example `~/.local/bin`). It is pinned to the SHA-256 literal, is never piped from `curl` into a shell, and leaves no download in the repository's working tree.
- R5. The standard gives the macOS variant (darwin tarball, `shasum -a 256 -c`) with its own pinned literal, and says the install was not run on macOS.

**Pinned tarball hash (item 3)**

- R6. The Install gitleaks step in `.github/workflows/leaks.yml` fails on a tarball whose SHA-256 differs from a literal pinned beside `GITLEAKS_VERSION`.
- R7. The CI step in `code/python-standards.md` § Using gitleaks Instead fails the same way.
- R8. Both places, and the standard's local install, say that an upgrade changes the version and the SHA-256 literal together.

**Dotfiles warning under a hook (item 4)**

- R9. With `GIT_DIR` set to the scanned repository and a declared list that sits in no repository, the wrapper prints no dotfiles warning.
- R10. With `GIT_DIR` set the same way, a list inside an unrelated repository that does not ignore it still produces the warning. The same list stops producing it once that repository ignores it.

**Latin-1 fixture (item 5)**

- R11. The Latin-1 fixture in `scripts/test-leak-gate.sh` fails when `-a` is removed from `sha_matches` on the CI platform (ubuntu, GNU grep). If no fixture can be made to fail there, the fixture is removed and the `sha_matches` comment presents `-a` as a precaution.

**Suite**

- R12. `sh scripts/test-leak-gate.sh` and `node scripts/check-docs.mjs` pass, locally and in CI on the PR head.

### Scope Boundaries

- Only the linux_x64 tarball is pinned in CI. The local install adds darwin literals (R5). Other platforms are not covered.
- No change to the wrapper's modes, rules, or value-list parsing beyond the dotfiles probe.
- The hook stays a plain `.git/hooks` script. Moving it to pre-commit, lefthook or `core.hooksPath` is out of scope.

### Deferred to Follow-Up Work

- `docs/solutions/tooling-decisions/adopter-checks-ship-in-the-adopters-ecosystem.md` says gitleaks is fetched "with the release checksum verified" and cites `code/python-standards.md:825-834`. Once this PR merges, that wording and the line range are both stale. `docs/solutions/` is out of bounds while PR #63 is open, so the PR body flags it for a later `ce-compound-refresh`.

---

## Planning Contract

### Key Technical Decisions

- KTD1. **The hook is the guarded form from the issue, written with a quoted heredoc.** The script's presence is tested relative to the hook's working directory, the worktree root, and a missing script exits 0 with a stderr message. A heredoc replaces the `printf` one-liner because the hook is now three lines, and a quoted heredoc leaves `$`, `\` and `!` unexpanded.
- KTD2. **The two list-directory probes run in a subshell that unsets every variable in `git rev-parse --local-env-vars`.** That is git's own list of repository-local variables, and it is what git's shell scripts clear before touching a second repository. The issue's hand-written list (`GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`) misses `GIT_OBJECT_DIRECTORY` and `GIT_PREFIX`, which a hook or a wrapping tool can also set. Only the two probes change. The rest of the wrapper still has to answer for the repository being committed to.
- KTD3. **The pinned hash sits beside the version it belongs to.** In `leaks.yml` it becomes a `GITLEAKS_SHA256` env entry next to `GITLEAKS_VERSION`, under the existing "upgrade both together" comment. In the Python step, which reads its version from `.pre-commit-config.yaml`, the literal goes in the step. A `make update-hooks` that moves the `rev` without the literal then fails CI instead of installing an unchecked binary. The table row that says `make update-hooks` "moves both" is corrected to say the literal is updated by hand.
- KTD4. **Verification pipes `"<sha>  <file>"` into `sha256sum -c -`, and nothing follows the check.** GitHub's default `run:` shell is `bash -e` without `pipefail`, so only the last command in a pipeline decides the step's exit. `sha256sum` has to be that last command, and no `!` negation may appear (bash `-e` ignores a `!` pipeline; see the #60 learning). Dropping the second `curl` also removes a failure mode that is not about integrity.
- KTD5. **The local install downloads into a `mktemp -d` directory, creates `~/.local/bin` if it is missing, chains every step with `&&`, and ends by checking that `gitleaks` resolves on `PATH`.**
  - The issue's command downloads into the current directory, which is usually the repository, and `install` fails when the target directory does not exist.
  - A developer pastes the command into an interactive shell, which has no `-e`. So KTD4's reliance on the runner's `bash -e` does not carry over. As in the issue's command, a failed hash check has to stop `tar` and `install` through `&&`.
  - A newly created `~/.local/bin` is not on `PATH` until the next login shell on Debian and Ubuntu, and never on macOS by default. The final `command -v gitleaks` check prints what to add to `PATH` (or says to set `GITLEAKS`) instead of leaving the next commit to fail with `gitleaks exited 127`.
  - The version and the hashes stay literals at the top of the command, so an upgrade edits one place.
- KTD6. **Item 5: cherry-pick `186f0af` only on proof, and tighten two points.** The bot's diagnosis agrees with what was reproduced during planning. GNU grep 3.7 under `C.UTF-8` prints `binary file matches` and no line for `Jos\351 <dev@example.org>`, while under `C` it prints the line. `git commit` rewriting Latin-1 as UTF-8 explains why the old fixture never failed. Once the proof passes, two refinements follow:
  1. The `LC_ALL` restore unsets the variable when it was unset before. As written, it leaves an exported empty `LC_ALL`.
  2. Before the gate call, the fixture checks that plain `grep` really drops the line under the forced locale. Where it does not (no `C.UTF-8`, or BSD grep), the fixture prints a note that it was not exercised rather than passing silently.

  If the suite still passes with `-a` removed, fall back to the issue's second option: remove the fixture and reword the comment as a precaution.

### Assumptions

- No one was available to confirm scope synchronously. The issue and its comments define it, and Rod signs off on this plan before `ce-work` starts.
- gitleaks stays at 8.24.2. The SHA-256 literals are computed from the downloaded tarballs, and each is checked against the release checksum file at the time it is pinned.
- #57 merges first. Its files do not overlap with this plan, so rebasing onto it should be conflict-free.

### Risks & Dependencies

- **Public proof output.** The PR body carries command output, and the repository is public. Every proof runs in a `mktemp -d` scratch directory, uses invented values only, and sets `GIT_CONFIG_GLOBAL` to a scratch file so the maintainer's real `leakgate.values` is never read. Home-directory paths are replaced with a placeholder before anything is pasted.
- **The shell's `grep` in an agent session may be a wrapper.** In this environment it is ugrep, which does not drop the line. Proofs call the scripts through `sh`, where the function is not defined, or call `/usr/bin/grep` explicitly.
- **Trust at upgrade time.** A pinned literal is only as good as the release it was taken from. The upgrade note says to take the new hash from the downloaded tarball and compare it with the release checksum file. That is trust on first use, and the note says so.

---

## Implementation Units

### U1. Clear git's environment around the dotfiles probe

**Goal:** the dotfiles warning answers for the list's directory, including when the wrapper runs as a hook.

**Requirements:** R9, R10, R12

**Dependencies:** none

**Files:** `scripts/leak-gate.sh`, `scripts/test-leak-gate.sh`

**Approach:**
- Wrap the `rev-parse --is-inside-work-tree` and `check-ignore` probes in one subshell that unsets the variables KTD2 names, then runs both.
- Add a comment saying why: hooks export `GIT_DIR`, and with it set, `git -C` answers for the committed repository.
- The `gate` helper can only assert that text is present. Add an optional way to assert that text is absent, and use it for the warning.

**Execution note:** write the fixtures first and watch the no-warning case fail against the unfixed wrapper before touching `leak-gate.sh`.

**Patterns to follow:** the `gate` helper and `wrepo`/`declare_list` in `scripts/test-leak-gate.sh`. Handle `GIT_DIR` differently from the `LEAKGATE_HONOR_ALLOW` save-and-restore:
- Build every fixture repository first, including the separate repository and its `.gitignore`. While `GIT_DIR` is exported, `git init`, `add` and `commit` would act on its repository, which is the item-4 bug itself.
- Set `GIT_DIR` only on the `gate` call itself, or export it just before the call and `unset` it just after.
- Never restore it by assignment. An exported empty `GIT_DIR` makes every later git call fail.

**Test scenarios:**
- `GIT_DIR` exported as the fixture repository's `.git`, list under `$LISTS` (in no repository): exit 0, output lacks `inside a git work tree`.
- `GIT_DIR` exported the same way, list inside a separate fixture repository with no ignore rule: output has the warning.
- The same separate repository with a `.gitignore` entry for the list: output lacks the warning.
- No `GIT_DIR` set, list in the unignored separate repository: output has the warning (behaviour unchanged).

**Verification:** the no-warning fixture fails against `origin/main`'s `leak-gate.sh` and passes after the change. A real `git commit` through the hook in a scratch repository, with a list outside every repository, prints no warning.

### U2. Make the Latin-1 fixture able to fail

**Goal:** the `-a` in `sha_matches` is held by a fixture that fails without it, or the claim is reworded and the fixture removed.

**Requirements:** R11, R12

**Dependencies:** none

**Files:** `scripts/test-leak-gate.sh`, `scripts/leak-gate.sh`

**Approach:**
1. Cherry-pick `186f0af` onto the branch, without committing, and run the suite with `-a` removed from `sha_matches`.
2. If the Latin-1 fixture fails with `exit 0, expected 1`, keep it, restore `-a`, and apply the two refinements in KTD6.
3. If it passes, drop the cherry-pick, remove the fixture, and reword the comment (KTD6 fallback).

**Patterns to follow:** `docs/solutions/best-practices/prove-a-check-fails-before-trusting-it-passes.md`.

**Test scenarios:**
- On ubuntu with GNU grep: the suite passes with `-a` in place.
- With `-a` removed: the Latin-1 fixture reports `exit 0, expected 1`.
- On a machine where grep keeps the line without `-a`: the fixture prints its not-exercised note, and the suite does not fail because of it.
- `LC_ALL` unset before the fixture is still unset after it.

**Verification:** the failing run with `-a` removed is recorded, with its output, for the PR body. The final commit credits the bot's commit as its source.

### U3. Pin the tarball hash in `leaks.yml`

**Goal:** CI refuses a gitleaks tarball that does not match a pinned literal.

**Requirements:** R6, R8

**Dependencies:** none

**Files:** `.github/workflows/leaks.yml`

**Approach:**
- Add `GITLEAKS_SHA256` beside `GITLEAKS_VERSION` and extend the "upgrade both together" comment to cover it and the release checksum cross-check.
- Replace the checksum-file line with the KTD4 check, and update the step's comment.

**Test scenarios:**
- The step's `run:` text, extracted from the workflow and run under `bash -e` with a real download: exit 0, and a working `gitleaks version`.
- The same text with a `curl` shim on `PATH` that serves a tarball with one byte changed: non-zero exit, `FAILED` from `sha256sum`, and no `gitleaks` binary extracted.

**Verification:** both runs recorded. CI on the PR head is green.

### U4. Pin the tarball hash in the Python standard's CI step

**Goal:** the Python standard's gitleaks step matches U3, and its prose says how an upgrade works now.

**Requirements:** R7, R8

**Dependencies:** U3, so the literal and idiom match

**Files:** `code/python-standards.md` (§ Using gitleaks Instead only)

**Approach:**
- Add the SHA literal to the CI step and use the KTD4 check.
- Correct the Install table row and the "CI scan" row wording ("checksum-verified" becomes pinned SHA-256) per KTD3.
- Replace the dated verification sentence about the tampered tarball with this run's date and result.

**Test scenarios:**
- In a scratch directory with a `.pre-commit-config.yaml` pinning `rev: v8.24.2`, run the step's text under `bash -e` with `RUNNER_TEMP` and `GITHUB_WORKSPACE` set: it installs, and `gitleaks dir .` runs.
- The same with the tampered-tarball shim: non-zero exit before `tar`.
- The same with `rev` bumped and the literal left alone: non-zero exit (the fail-closed upgrade case KTD3 claims).

**Verification:** all three runs recorded. `node scripts/check-docs.mjs` passes.

### U5. Guarded hook and local install in the repository standard

**Goal:** the standard gives an adopter a hook that never blocks unrelated work and a gitleaks install that makes the hook runnable.

**Requirements:** R1, R2, R3, R4, R5, R8

**Dependencies:** U3 (the literal)

**Files:** `process/repository-standards.md` (§ Adopting the Gate, § Running It Locally)

**Approach:**
- § Running It Locally: replace the `printf` hook with the KTD1 heredoc and add one sentence on why the guard exists (R3).
- § Adopting the Gate: replace "with its release checksum verified, as Using gitleaks Instead shows" with the local install (KTD5), then the macOS variant marked not run, then the upgrade note (R8). Keep the pointer to the CI step for CI.
- Leave the dotfiles paragraph in § Private Values as it is. U1 makes it true under a hook.

**Test scenarios:**
- Scratch repository, gate committed on `main`, branch `old` cut before the gate, hook installed exactly as the standard shows. In a worktree on `old`, a commit succeeds and stderr shows the skipped-check message. Covers R1.
- The same repository on `main`: staging a file with an invented private value, the commit is refused, and the output names only the file and the list line. Covers R2.
- The same repository on `main`, clean change: the commit succeeds.
- The Linux install, run verbatim through `sh` without `-e`, with `HOME` pointed at a scratch directory that has no `.local/bin`:
  - it prints the `PATH` message;
  - with `PATH` then extended as the standard says, `gitleaks version` resolved through `PATH` prints 8.24.2;
  - a real commit through the hook runs gitleaks;
  - the working directory is left without a tarball.
- The Linux install with a tampered tarball, again through `sh` without `-e`: it stops at the hash check, and `$HOME/.local/bin/gitleaks` does not exist afterwards.

**Verification:** all runs recorded. `node scripts/check-docs.mjs` passes, including anchors into § Using gitleaks Instead.

---

## Verification Contract

Every run below goes into the PR body as the command and its output, with home-directory paths replaced.

| Proof | Holds | Unit |
|---|---|---|
| Scratch repository plus a worktree on a pre-gate branch: the commit passes with the skip message, and a staged leak on the gate branch is refused | R1, R2 | U5 |
| Linux local install, verbatim through `sh` without `-e`, into a scratch `HOME`: `PATH` message, lookup through `PATH`, then a tampered tarball that installs nothing | R4 | U5 |
| The changed text, quoted in the PR body: the guard's worktree rationale, the macOS variant marked not run, and the upgrade note in `leaks.yml`, the Python step and the local install | R3, R5, R8 | U3, U4, U5 |
| `leaks.yml` Install step text, real download and then a tampered tarball | R6 | U3 |
| Python CI step text: real download, tampered tarball, and `rev` bumped without the literal | R7 | U4 |
| `GIT_DIR`-set wrapper run with an out-of-repo list: no warning. Unignored list in another repository: warning. A real hook commit | R9, R10 | U1 |
| Test suite with `-a` removed from `sha_matches`: the Latin-1 fixture fails | R11 | U2 |
| `sh scripts/test-leak-gate.sh` and `node scripts/check-docs.mjs` pass | R12 | all |

CI (`Leak gate` and `docs` workflows) is green on the PR head.

---

## Definition of Done

- R1 through R12 hold, each with a recorded proof from the table above.
- The PR says "Closes #62", carries the proof, and flags the deferred `docs/solutions/` drift.
- No file outside the execution profile changed, `pm-trial/` included.
- No scratch files, tarballs, or leftover experiments in the diff.
- The branch is rebased on `origin/main` after #57 merges, and CI is green on the rebased head.
