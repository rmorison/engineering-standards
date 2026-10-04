---
title: Leak Gate Threat Model, Pre-commit Framework Entry, and Pre-push Check - Plan
type: feat
date: 2026-10-04
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
origin: https://github.com/rmorison/engineering-standards/issues/75
---

# Leak Gate Threat Model, Pre-commit Framework Entry, and Pre-push Check - Plan

## Goal Capsule

- Objective: an adopter that runs its hooks through the pre-commit framework, such as rmorison/buzai, can wire the leak gate into both pre-commit and pre-push by copying a stable file set and install text. Commit messages and `--no-verify` commits are checked before they leave the machine. The standard says plainly whose mistakes the gate guards against.
- Means: the framework entry runs the adopter's pinned gitleaks through `repo: local`, `language: system` (KTD1). A missing gitleaks fails closed with one line that says what to do (KTD3). One `pre-push` mode in `scripts/leak-gate.sh` serves both hook forms (KTD5, KTD6).
- Authority: issue #75, the buzai lead's hand-over (issuecomment-5983618653) and the proposed criterion (issuecomment-5983643905) are the spec. Where this plan and the issue disagree, the issue wins, and the disagreement goes on the issue as a question.
- Execution profile: edits to `process/repository-standards.md` § Leak Gate (except the parts ES-pins owns, listed under Scope Boundaries), `scripts/leak-gate.sh` and `scripts/test-leak-gate.sh`, plus this plan file. Nothing in `code/python-standards.md`, `.github/workflows/leaks.yml`, `scripts/check-docs.mjs`, `docs/solutions/` or `pm-trial/`.
- Stop conditions: stop and comment on #75 if a fixture cannot be made to fail before it is trusted, if gitleaks rejects a multi-argument `--log-opts` revision list (KTD6), or if a real pre-commit run in a scratch repository behaves differently from the pre-commit 4.6.2 source read for this plan.
- Finishes the work: `ce-work` in three PRs, merged in order: `75-leak-gate-threat-model` (U1), `75-pre-commit-framework-entry` (U2, U3), and `75-pre-push-check` (U4 to U6). The first two say "Part of #75", and the last says "Closes #75". Rod merges.

---

## Product Contract

### Summary

Open § Leak Gate with the threat model the issue proposes. Say that `CODEOWNERS` review only works with more than one maintainer identity, and that adopters may add their own shape rules. Give a `repo: local` pre-commit framework entry that runs `sh scripts/leak-gate.sh staged` with the gitleaks the adopter installed from § Adopting the Gate. When that gitleaks is missing, the entry fails closed with a single line pointing at the install. Add a `pre-push` mode to the wrapper that reads git's ref lines on stdin, or pre-commit's environment variables, and scans what the remote does not have, commit messages included. Give one install block for each hook form.

### Problem Frame

Planning the gate's adoption in rmorison/buzai turned up three gaps (#75).

- The section never says whose values the gate protects, or against what. Some of its guidance reads as defence against a hostile contributor, so reviewers size adopters' work against deliberate bypass.
- A repository whose hooks run through the pre-commit framework cannot use the hand-written hook. `pre-commit install` owns the same `.git/hooks/pre-commit` file.
- Nothing wires `range` as a pre-push check. Pre-push is the only local check of commit messages, author identities and `--no-verify` commits. An agent that writes a private value into a commit message is a common case.

The hand-over added a question the issue missed: which gitleaks does the framework entry run? KTD1 settles it. Rod signs off on that answer, because it changes the scope of #71.

### Key Decisions

- **The framework entry runs the adopter's installed gitleaks (option A).** CI, both hand-written hooks, the framework entry, and a maintainer's direct `range` and `history` runs then use one binary, at one version, verified by one SHA-256, on every machine that installs from the pinned block. The full comparison, and what option A costs, is in KTD1. Governs R4, R5.
- **The Python standard's upstream gitleaks hook is replaced by the gate's entry in any project that adopts the gate.** The decision and what it hands ES-pins are in KTD2. Governs R7.
- **The framework's pre-push stage scans only what pre-commit hands it.** pre-commit 4.6.2 passes hooks the first ref of a push that has something to scan, and drops the rest. The standard states this and says which form to use when several refs are pushed at once (KTD7). Governs R12.

### Requirements

**Threat model and scope notes (piece 1)**

- R1. § Leak Gate opens with the issue's threat-model sentence: "The gate protects the holder of a value list from publishing their own private values by mistake, including mistakes their agents make. It is not a control against someone who means to leak or to get around it."
- R2. The `CODEOWNERS` paragraph at the end of § Adopting the Gate says that required review needs more than one maintainer identity. In a one-person repository, the author is the code owner, so the review never happens.
- R3. § Rule Categories says that adopters may add shape rules for their own domain to `.gitleaks.toml`, for example formatted account-number shapes in a project that handles personal financial data.

**Framework entry and missing gitleaks (piece 2)**

- R4. § Running It Locally gives a `repo: local`, `language: system` entry whose `entry` is `sh scripts/leak-gate.sh staged`, together with the one command that installs it.
- R5. In a scratch repository that runs pre-commit, the entry refuses a staged canary. A commit on a branch whose `.pre-commit-config.yaml` predates the entry goes through.
- R6. When gitleaks cannot be run, every mode of `scripts/leak-gate.sh`, and so every hook form, exits 2 with one line. The line says gitleaks was not found, and points to § Adopting the Gate or to setting `GITLEAKS`. A fixture runs with `GITLEAKS` set to a missing path.
- R7. The plan states what happens to the Python standard's `repo: gitleaks/gitleaks` hook in a project that adopts the gate (KTD2). ES-pins makes any edit to `code/python-standards.md`.

**Pre-push check (piece 3)**

- R8. `sh scripts/leak-gate.sh pre-push` scans every commit the push would give the remote, using the same rules as `range`, commit messages, identities and paths included.
- R9. It takes the refs from git's pre-push stdin lines (the hand-written hook passes the remote name and URL as arguments), or from pre-commit's `PRE_COMMIT_*` variables. The range logic lives in one place.
- R10. Fixtures in `scripts/test-leak-gate.sh` cover:
  - an existing branch;
  - a new branch, which scans only the new commits;
  - a force push;
  - a deletion;
  - several refs in one push;
  - a canary in a commit message;
  - the framework's variables, including pre-commit's whole-branch case.

  Each fixture is seen to fail before it is trusted.
- R11. The hand-written pre-push hook installs with one command block, and is guarded for branches that predate the gate the way the pre-commit hook is. The framework config gains a pre-push entry, and one command installs both framework hooks.
- R12. The standard says what the framework's pre-push stage cannot see (KTD7), and § What the Gate Cannot See is updated to match.

**Everywhere**

- R13. Output names list lines only, never values, as now.
- R14. `sh scripts/test-leak-gate.sh` and `node scripts/check-docs.mjs` pass before each PR opens.

### Scope Boundaries

- ES-pins (#70, #71) owns these, so this work does not touch them:
  - the install blocks and the upgrade paragraph in § Adopting the Gate;
  - the install step in `.github/workflows/leaks.yml`;
  - `code/python-standards.md` § Using gitleaks Instead;
  - `scripts/check-docs.mjs`.
- One sentence in § Adopting the Gate goes stale with R6: "Without it on `PATH`, the wrapper reports `gitleaks exited 127` and every commit is refused." It is in the paragraph before the install blocks, not in a block. U3 rewrites that sentence only, and the PR says so to ES-pins (see Risks & Dependencies).
- Out of scope, per #75: GitHub text and hook bypass (#74), the gitleaks version and hash copies (#70, #71), and any change to what the rules match.
- No buzai-specific rules. buzai's financial-data shapes stay in buzai's `.gitleaks.toml`.

### Deferred to Follow-Up Work

- **Pushed ref names and annotated tag messages.** A pre-push hook knows the remote ref names, and an annotated tag's message is not a commit message. Neither is scanned here. `history` already scans both, and § What the Gate Cannot See keeps saying so. buzai asked for stable output over extras, so this is a follow-up issue, not part of this work.
- **A version check in the wrapper.** It would warn when the gitleaks it runs is not the pinned version. That belongs with #70's drift check, so it goes to ES-pins as a suggestion.

---

## Planning Contract

### Key Technical Decisions

- KTD1. **The framework entry is `repo: local`, `language: system`, `entry: sh scripts/leak-gate.sh staged`, and it runs the gitleaks the adopter installed (option A, in).**
  - One binary everywhere. CI's install step, the hand-written hooks, the framework entry, and the maintainer's own `range` and `history` runs all resolve the same `gitleaks`, through `PATH` or `GITLEAKS`. That copy was installed from a tarball checked against the SHA-256 in § Adopting the Gate. #70's drift check covers only the copies of the version and hash written in this repository. Nothing checks the version of a local binary until the deferred version check lands, so a machine with an older or Homebrew gitleaks on `PATH` runs it unnoticed.
  - The install is needed anyway. The pre-merge check (`range origin/main..refs/leakgate/pr-<N>`) and the going-public sweep (`history`) run the wrapper directly, outside pre-commit. So the maintainer who holds the list, the person the gate protects, needs gitleaks installed whatever the framework does. Option B would save that person nothing.
  - **The cost of option A:** every clone that installs the framework hooks needs the pinned gitleaks, not only the list holder. That includes outside contributors, other machines, and agents in fresh containers. Today, a project on the Python standard's upstream hook gets gitleaks with nothing installed by hand. After KTD2's swap, KTD3's fail-closed check refuses those clones' commits until they install it. The offset is the unattended install proposed on #70 for `make dev`, and the sign-off request on #75 states this cost.
  - `language: system` with `entry: sh ...` means pre-commit never fails with its own "executable not found" error. A missing gitleaks reaches the wrapper, which prints KTD3's line.
  - **Option B, out:** a gitleaks that pre-commit builds, either the upstream hook (`repo: https://github.com/gitleaks/gitleaks`, `language: golang`) or a local `language: golang` hook with `additional_dependencies` on the gitleaks module. It would work technically, since pre-commit puts the hook environment's `bin` first on `PATH` (pre-commit 4.6.2, `languages/golang.py`), so the wrapper would find it. It is out because:
    1. It is a second binary, built from source rather than the released tarball. No tarball SHA-256 applies to it, so its integrity rests on Go's module checksum database, a second trust path.
    2. It adds a fourth hand-kept version for #70: the hook `rev` or the dependency version.
    3. It needs a Go toolchain on each machine, or pre-commit downloads one on first run, so the install is hidden rather than gone.
    4. It does not reach the direct runs above.

    Its real advantage is that the hook `rev` pins the version on every machine that runs pre-commit, with no manual install. Option A matches that only once the deferred version check, or the unattended install, exists.
  - **The upstream hook as the scanner, out:** pre-commit would run it alongside, or instead of, the wrapper. Its entry at v8.24.2 is `gitleaks git --pre-commit --redact --staged --verbose`, and the upstream `gitleaks-system` variant uses the same flags. `--verbose` prints the line around each match, which the gate forbids. It honours inline allow comments, and it runs no value rules.
- KTD2. **In a project that adopts the gate, the leak-gate entry replaces the Python standard's `repo: gitleaks/gitleaks` hook.**
  - The entry is a superset. It reads the same committed `.gitleaks.toml`, and adds value rules, path checks, a binary-file pass, and output that never shows a matched line. Running both would run two gitleaks binaries, the upstream one with `--verbose`.
  - One exception: inline allow comments. § Using gitleaks Instead permits reviewed `gitleaks:allow` comments under `tests/`. The upstream hook honours them, but the wrapper ignores them unless `LEAKGATE_HONOR_ALLOW=1` is set. So U3 and U6 give a variant entry, `entry: env LEAKGATE_HONOR_ALLOW=1 sh scripts/leak-gate.sh staged` (and the same for `pre-push`), for a project whose language standard permits those comments. With the variant, the swap is a superset for exactly the projects it applies to.
  - A detect-secrets project keeps its detect-secrets hook and adds the gate's entry beside it, as § Rule Categories already says.
  - For ES-pins, which makes the edit:
    1. § Using gitleaks Instead's "Pre-commit hook" row becomes the gate's local entry.
    2. #71, pinning that hook's `rev` by commit SHA, falls away for projects that adopt the gate.
    3. The Python CI step reads its gitleaks version from that hook's `rev` (`sed -n '/gitleaks\/gitleaks/{n;s/.*rev: v//p;}' .pre-commit-config.yaml`). Without the hook, it needs a version literal, as `leaks.yml` has.
  - Recorded here and on #75. Nothing in `code/python-standards.md` changes in this work.
- KTD3. **A missing gitleaks is detected once, at the top of the wrapper, before any value-list work.**
  - If `GITLEAKS` (default `gitleaks`) does not resolve through `command -v`, the wrapper calls `die`, which exits 2. Its one line says gitleaks was not found, and to install the pinned version from § Adopting the Gate in `process/repository-standards.md` or set `GITLEAKS` to its path.
  - The line does not echo the `GITLEAKS` value. That value is a local path, and a path can hold a home directory.
  - Exit 2 keeps the documented contract: a usage, list or gitleaks error.
  - If ES-pins adds an install script, the line points to it in the PR that adds the script.
  - The existing `gitleaks exited <rc>` stays for every other failure.
- KTD4. **The framework config lists the stage on each hook, with `pass_filenames: false` and `always_run: true`.**
  - `always_run` matters. Without it, pre-commit skips a hook when no changed file matches, and that would skip a commit or push that changes only a message, a deletion, or a file type pre-commit does not classify.
  - The install command is `pre-commit install --hook-type pre-commit --hook-type pre-push`, which is one block. The rule is one form per hook file: for each of pre-commit and pre-push, use the hand-written hook or the framework entry, never both. `pre-commit install` renames an existing hand-written hook to `.legacy` and runs it too, so the gate would run twice. The paired form in KTD7 installs with `pre-commit install --hook-type pre-commit` and leaves the framework's pre-push entry out of the config.
  - The guard the hand-written hook needs is not needed here. The framework reads each branch's own `.pre-commit-config.yaml`, so a branch that predates the entry does not run it.
  - A branch with no config file at all is pre-commit's own `--allow-missing-config` question, not the gate's. The doc says so in a sentence.
- KTD5. **`pre-push` scans the commits reachable from the pushed local SHAs and not from what the remote already has.**
  - For each ref line:
    - a deletion (local SHA all zeros) contributes nothing;
    - otherwise the local SHA is included;
    - a remote SHA that is non-zero and present locally is excluded. This covers an existing branch, and a force push too, since `^<remote sha>` leaves exactly what the remote lacks.
  - After that, the whole set excludes the pushed-to remote's remote-tracking refs (`--remotes=<name>`). This covers a new branch, and a force push whose old remote SHA was never fetched.
  - `--remotes` is added only when the name is a configured remote with no `remote.<name>.pushurl`. A remote with a separate push URL fetches from one repository and pushes to another, so its tracking refs say nothing about the push target, and it is treated like a bare URL.
  - Without the exclusion, the mode scans everything the local SHAs reach, as `history` would. That covers a push to a bare URL, a remote never fetched, an empty new remote, or a pushurl remote, and it **refuses** on any finding already in history, not merely runs slowly. This repository's own history holds two committed-rule findings. The doc says so, with the remedy:
    - `git fetch <remote>` when the remote already has the history;
    - for an empty remote, run `sh scripts/leak-gate.sh history`, review the findings, then push with `--no-verify`.
  - After changing a remote's URL, old tracking refs can hide commits from the check, so the doc also says to run `git fetch --prune <remote>` before pushing.
  - Using the pushed-to remote's refs rather than every remote's is deliberate. A commit on a private remote but not on a public one must still be scanned when it is pushed to the public one.
  - No refs to scan, because everything is a deletion or already on the remote, prints the same "nothing to scan" note that `range` prints, and exits 0.
- KTD6. **The pushed set becomes one revision list fed to the code `range` already runs.** The `range` path takes a single `<base>..<head>` argument today. It is generalised to a list of revision arguments, which feeds:
  - `rev-list --count`, the paths log, the identities log, the message grep, and gitleaks' `--log-opts`, which is already a whitespace-split string;
  - the list holds only SHAs, `^`-prefixed SHAs, `--not` and `--remotes=<configured remote name>`, so word splitting is safe. A remote name is checked against `git remote` output before it is used.

  `range <base>..<head>` behaves exactly as now: the same fixtures pass unchanged. Before relying on this, `ce-work` checks that gitleaks 8.24.2 passes a multi-argument `--log-opts` with `^<sha>` and `--remotes` through to `git log` (stop condition).
- KTD7. **The mode reads pre-commit's variables first, then stdin, and the standard states the framework form's limit.**
  - With `PRE_COMMIT_TO_REF` set, the set is `PRE_COMMIT_TO_REF ^PRE_COMMIT_FROM_REF`, plus KTD5's remote exclusion through `PRE_COMMIT_REMOTE_NAME`.
  - pre-commit sometimes sets no FROM/TO: its whole-branch case, when the push reaches a root commit. Then the set is `PRE_COMMIT_LOCAL_BRANCH` with the remote exclusion.
  - pre-commit's new-branch `FROM_REF` is the first new commit's parent, so on a branch with merges it can over-scan. The remote exclusion trims that.
  - Otherwise, the mode reads stdin lines only when `<remote> <url>` arguments are given, which is the hand-written hook's call.
  - It fails closed (exit 2, with the usage line) in two cases: no arguments and no `PRE_COMMIT_REMOTE_NAME`; or `PRE_COMMIT_REMOTE_NAME` set without `PRE_COMMIT_TO_REF` or `PRE_COMMIT_LOCAL_BRANCH`.
    - pre-commit runs hooks with an empty stdin, so either case would otherwise read no refs and pass having scanned nothing. Examples are `pre-commit run --hook-stage pre-push` by hand, or a pre-commit version that sets different variables.
    - A real framework push always sets `PRE_COMMIT_REMOTE_NAME`.
  - The limit: pre-commit 4.6.2 (`commands/hook_impl.py`, `_pre_push_ns`) returns the first ref line with something to push, and never shows hooks the rest. So `git push --all`, `--tags`, or `--follow-tags` with a new tag reaches the framework entry as one ref.
  - The standard says this beside the framework install, and in § What the Gate Cannot See. It names the hand-written pre-push hook as the form that sees every ref. A clone can pair the framework's pre-commit entry with the hand-written pre-push hook, since they own different hook files. U6 gives that pairing its own install text (KTD4).
  - **Open for Rod and the buzai lead (posted on #75):** keep this documented limit, or have the framework form scan every local branch and tag not on the remote (`--branches --tags --not --remotes=<name>`). That needs no stdin and has no gap, but it also scans unpushed local branches, so a canary on a branch nobody is pushing blocks the push. The plan assumes the documented limit until they answer.
- KTD8. **The hand-written pre-push hook mirrors the pre-commit hook's guard.**
  - The hook runs `exec sh scripts/leak-gate.sh pre-push "$@"`. `exec` keeps git's stdin.
  - It refuses when `HEAD` has the script and the working tree does not, and skips with a message when `HEAD` has no script.
  - It also skips with a message when the working tree's `scripts/leak-gate.sh` has no `pre-push` mode, so a branch cut before piece 3 does not refuse every push with a usage error. The check is a `grep` for the mode name.
  - A skip covers the whole push, every ref included, whatever is pushed. `git push origin main` from an old checkout publishes `main`'s new commits unscanned. U6 adds this to § What the Gate Cannot See.
  - Like the pre-commit hook, it runs the checked-out branch's wrapper, not the pushed branch's. The doc says this in one clause.

### Assumptions

- No synchronous confirmation of scope was taken. The issue and the two lead comments define the scope, and Rod signs off on this plan, the gitleaks answer included, before `ce-work` starts.
- gitleaks stays at 8.24.2. pre-commit behaviour is taken from the 4.6.2 source read for this plan, and checked by a real run in a scratch repository in U3 and U6.
- The pre-commit framework is not installed in CI. `test-leak-gate.sh` keeps needing only git and gitleaks. It drives the framework form by setting the `PRE_COMMIT_*` variables, and the real framework runs are recorded in the PR bodies.
- ES-hooks (#74) adds a subsection after § Running It Locally and merges after piece 3, so piece 3 does not wait for it.

### Risks & Dependencies

- **ES-pins edits the same section.** Pieces 1 and 2 touch § Adopting the Gate: the `CODEOWNERS` paragraph, and the one "exited 127" sentence. ES-pins edits the install blocks and the upgrade paragraph between them. Whichever lands second rebases. Each PR names the lines it touched in § Adopting the Gate.
- **Public proof output.** PR bodies carry command output in a public repository. Every proof runs in a `mktemp -d` scratch repository under the session scratchpad, uses canary values only, and points `GIT_CONFIG_GLOBAL` at a scratch file, so a real `leakgate.values` is never read. Before anything is pasted, every scratch path is replaced with `<scratch>`. That covers the `mktemp -d` result and anything under the session scratchpad, whose prefix encodes the home directory with dashes, a form that neither the home-directory rule nor a search for `/home/` finds. The pasted text is then checked for the scratchpad root and the local username before posting.
- **Hooks in this clone.** Every worktree shares one hooks directory. No proof runs `pre-commit install`, writes `.git/hooks/*`, or sets `core.hooksPath` in this clone, only in scratch repositories.
- **Over-scan on stale tracking refs.** A new-branch push after a long time without fetching can scan commits that are already public, and could refuse on an old, already-published finding. `git fetch` clears it. The doc says so where it describes the new-branch case.
- **buzai's adopter test.** It is a Done condition for pieces 2 and 3. The file set and install text are kept stable once each PR is up. Later changes go to a follow-up unless review requires them.

---

## Implementation Units

### U1. Threat model, maintainer-identity note, and domain shape rules

**Goal:** § Leak Gate states its threat model and the two scope notes. Nothing else changes.

**Requirements:** R1, R2, R3, R14

**Dependencies:** none

**Files:** `process/repository-standards.md`, and this plan file in the same PR.

**Approach:**
- Insert R1's sentence at the top of § Leak Gate, before "A leak gate fails a change...". Keep the existing paragraph after it.
- At the end of the `CODEOWNERS` paragraph in § Adopting the Gate, add R2's sentence. Touch nothing else in § Adopting the Gate.
- Add R3's line to the **Shape rules** paragraph in § Rule Categories.

**Test scenarios:** none. This is documentation only, so `check-docs` is the gate.

**Verification:** `node scripts/check-docs.mjs` and `sh scripts/test-leak-gate.sh` pass. The PR quotes the three changed passages.

### U2. Fail closed with one line when gitleaks is missing

**Goal:** a missing gitleaks produces one actionable line and exit 2 in every mode.

**Requirements:** R6, R13

**Dependencies:** U1 merged (branch rebased).

**Files:** `scripts/leak-gate.sh`, `scripts/test-leak-gate.sh`

**Approach:**
- Add the KTD3 check right after argument parsing and the config and template checks, before the value list is read.
- The `gate` helper pins `GITLEAKS="$GITLEAKS"` on every call. Add a one-call override in the style of `hook_git_dir`, or call the wrapper directly for this fixture.

**Execution note:** write the fixture first, and record it failing against `origin/main`'s wrapper, which prints `gitleaks exited 127`.

**Patterns to follow:** the `gate` helper and its one-call settings in `scripts/test-leak-gate.sh`. `docs/solutions/best-practices/prove-a-check-fails-before-trusting-it-passes.md`.

**Test scenarios:**
- `GITLEAKS` set to a missing path, mode `staged`, with a value list declared: exit 2. The output is exactly one line, contains "gitleaks was not found" and `Adopting the Gate`, and does not contain the missing path or the canary.
- The same with no value list declared: exit 2 and the same line. The check comes before the "value rules skipped" note, or the output says which.
- Mode `range HEAD~1..HEAD`: exit 2 and the same line.

**Verification:** the fixture fails against the unfixed wrapper and passes after. Any check-docs reference to the old message is updated.

### U3. Framework entry for `staged`, and the stale sentence

**Goal:** an adopter that uses the pre-commit framework has a documented, proven entry for the pre-commit stage.

**Requirements:** R4, R5, R7, R13, R14

**Dependencies:** U2 (same PR).

**Files:** `process/repository-standards.md` (§ Running It Locally, and the one sentence in § Adopting the Gate)

**Approach:**
- In § Running It Locally, after the hand-written hook, add a short paragraph and a YAML block for the KTD1/KTD4 entry (`id: leak-gate`, `stages: [pre-commit]`), then the one install command.
- Say why no guard is needed (each branch's own config), and that the rule is one form per hook file (KTD4).
- Give the `LEAKGATE_HONOR_ALLOW=1` variant entry beside the default, for projects that permit reviewed allow comments (KTD2).
- Rewrite the "exited 127" sentence in § Adopting the Gate to describe KTD3's line.
- Say that the Python standard's upstream gitleaks hook is replaced in a project that adopts the gate, pointing to the Python standard rather than editing it. If even that sentence belongs to ES-pins' text, leave it for them and say so on the PR.

**Test scenarios (scratch repository with pre-commit, recorded in the PR body):**
- A config holding the entry, a canary list declared, and a staged canary: the commit is refused. The output names the list line, not the value.
- A clean staged change: the commit goes through.
- A branch whose `.pre-commit-config.yaml` has no leak-gate entry, with the canary staged: the commit goes through. This is the "predates the gate" case.
- `GITLEAKS` set to a missing path: the commit is refused with KTD3's line.

**Verification:** the four runs above, with commands and output. The YAML in the PR is the YAML in the doc, copied from the doc's own text (`docs/solutions/best-practices/prove-a-pasted-command-from-the-docs-own-text.md`).

### U4. `pre-push` mode: one revision list from stdin or pre-commit variables

**Goal:** the wrapper scans exactly what a push would give the remote, in either hook form.

**Requirements:** R8, R9, R13

**Dependencies:** U3 merged (branch rebased).

**Files:** `scripts/leak-gate.sh`

**Approach:**
- Add `pre-push` to the usage line and the header comment. Arguments are optional: `<remote> <url>` from the hand-written hook, none from the framework.
- Build the revision list as KTD5 and KTD7 describe, in one function.
- Generalise the `range` code path to that list (KTD6), so `pre-push` reuses the path, identity, message and gitleaks scans unchanged.
- Run KTD3's gitleaks check in this mode too.
- The comment block names pre-commit's first-ref behaviour, with its version and source file.

**Execution note:** before generalising, confirm with gitleaks 8.24.2 that `--log-opts` passes `^<sha>` and `--remotes=<name>` through to `git log`. If it does not, stop and comment on #75.

**Patterns to follow:** the existing `range` branch of the `case "$mode"` blocks, and the `die` and usage conventions.

**Test scenarios:** in U5.

**Verification:** U5's fixtures, and the existing `range` fixtures passing unchanged.

### U5. Pre-push fixtures

**Goal:** every #75 case is pinned by a fixture that was seen to fail.

**Requirements:** R10, R13, R14

**Dependencies:** U4 (same PR).

**Files:** `scripts/test-leak-gate.sh`

**Approach:**
- Each fixture builds a scratch "origin" as a bare repository under `$WORK`, a clone with a canary list declared, and `git fetch` for the remote-tracking refs.
- It then calls `leak-gate.sh pre-push origin <url>` with hand-built stdin ref lines, or with `PRE_COMMIT_*` set for the framework form.
- One end-to-end fixture installs the hand-written hook in a scratch clone and runs a real `git push` to the bare origin, which proves the stdin plumbing.

**Execution note:** for each fixture, record the mutation that makes it fail. Do not trust a fixture that fails only because the mode does not exist yet.

**Test scenarios (each line: setup → expected; mutation that must make it fail):**
- Existing branch, canary in a file in a new commit → exit 1. Mutation: exclude the local SHA.
- Existing branch, canary only in a commit already on the remote → exit 0. Mutation: drop `^<remote sha>` and `--remotes`.
- New branch (remote SHA all zeros) off a pushed `main`, canary in a new commit → exit 1. Canary only in `main`'s already-pushed history → exit 0. Mutation: drop the `--remotes` exclusion.
- Force push: rewrite a pushed commit, with the canary in the replacement commit → exit 1. Mutation: use `<local>..<remote>`.
- Force push whose old remote SHA is not in the local object store (a fabricated SHA) → no error, and the canary in the new commit → exit 1.
- Deletion only (local SHA all zeros) → exit 0 with the "nothing to scan" note. Mutation: pass the zero SHA through, which exits 2.
- Two refs in one push, canary only on the second → exit 1. Mutation: scan the first line only.
- Canary only in a commit message, with clean files → exit 1, and the report says "a commit message matches private value (list line N)". Mutation: drop the message grep from the shared path.
- Framework form: `PRE_COMMIT_FROM_REF`, `PRE_COMMIT_TO_REF` and `PRE_COMMIT_REMOTE_NAME` set to an existing-branch range with a canary → exit 1. The whole-branch case, with only `PRE_COMMIT_LOCAL_BRANCH` and `PRE_COMMIT_REMOTE_NAME` set → exit 1 on a canary, exit 0 when clean.
- Missing gitleaks in `pre-push` mode → exit 2 with KTD3's line.
- Push to a bare URL (not a configured remote) → scans what the local SHA reaches, with no `--remotes` argument and no error.
- A configured remote with a `pushurl`, whose tracking refs hold a commit carrying the canary → exit 1. Mutation: drop the pushurl check.
- No arguments, no `PRE_COMMIT_*` variables, empty stdin → exit 2 with the usage line. `PRE_COMMIT_REMOTE_NAME` alone → exit 2. Mutation: fall through to stdin, which exits 0.
- Every fixture: the canary never appears in the output (the `gate` helper's existing check).

**Verification:** each mutation's failing run is recorded for the PR body. The whole suite passes.

### U6. Pre-push install text and what the framework form cannot see

**Goal:** each pre-push form installs with one block, and its limits are written down.

**Requirements:** R11, R12, R14

**Dependencies:** U4, U5 (same PR).

**Files:** `process/repository-standards.md` (§ Running It Locally, § What the Gate Cannot See)

**Approach:**
- Replace the `range` line's "before pushing" usage comment with a `pre-push` line.
- Add the hand-written pre-push hook block (KTD8), shaped like the pre-commit block, through `git rev-parse --git-path hooks`.
- Add the `id: leak-gate-pre-push` entry (`stages: [pre-push]`) to the framework YAML from U3. The install command from U3 already installs both hooks.
- Give the paired form's install text: `pre-commit install --hook-type pre-commit`, then the hand-written pre-push block (KTD4, KTD7).
- State the whole-history refusal and its remedies, and the `git fetch --prune` note (KTD5).
- State KTD7's limit beside the framework block, and the stale-tracking-ref note.
- In § What the Gate Cannot See:
  - say that pre-push now checks commit messages, identities and `--no-verify` commits locally;
  - keep ref names and tag messages listed as unchecked before a push;
  - extend the "Commits the hook skipped" bullet: the hand-written pre-push hook skips the whole push when the checked-out branch has no wrapper, or a wrapper without `pre-push`;
  - add the framework form's first-ref limit.

**Test scenarios (scratch repositories, recorded in the PR body):**
- The hand-written hook block, pasted verbatim into a scratch clone: a push with a canary in a commit message is refused, a clean push goes through, a push from a branch with no script skips with the message, and a push from a branch whose wrapper predates `pre-push` skips with its message instead of exiting 2.
- Framework: a scratch repository with the YAML from the doc, installed with the doc's command. A push with a canary in a commit message is refused. A new-branch push scans only the new commits: a canary already on the remote's `main` does not refuse it.
- Framework, two refs pushed at once with the canary only on the second: the push goes through. This records the limit KTD7 states, so the doc's claim is proven, not assumed.

**Verification:** the runs above, the doc text quoted in the PR, and `check-docs` passing.

---

## Verification Contract

Every run goes into its PR body as the command and its output, with canaries only and every scratch path replaced with `<scratch>`, as Risks & Dependencies says.

| Proof | Holds | Unit | PR |
|---|---|---|---|
| The three changed passages quoted, and `check-docs` passing | R1–R3 | U1 | 1 |
| Missing-gitleaks fixture failing on `origin/main`'s wrapper, then passing | R6 | U2 | 2 |
| Scratch pre-commit repository: canary refused, clean commit allowed, pre-entry branch allowed, missing gitleaks refused with one line | R4, R5, R6 | U3 | 2 |
| KTD2 recorded on #75 and in the PR body for ES-pins | R7 | U3 | 2 |
| Each pre-push fixture's mutation failing, then the suite passing | R8–R10 | U4, U5 | 3 |
| Real hand-written-hook push and real framework push in scratch repositories, including the two-ref limit | R11, R12 | U6 | 3 |
| No canary in any output | R13 | all | all |
| `sh scripts/test-leak-gate.sh` and `node scripts/check-docs.mjs` pass | R14 | all | all |

CI (`Leak gate` and `docs`) is green on each PR head. For pieces 2 and 3, the buzai lead's adopter test passes and is posted on the PR.

---

## Definition of Done

- R1–R14 hold, each with a recorded proof from the table above.
- Three PRs, merged in order. The first two say "Part of #75", and the third says "Closes #75".
- buzai's adopter test has passed on pieces 2 and 3.
- No file outside the execution profile changed. Nothing ES-pins owns was edited, apart from the one sentence named under Scope Boundaries.
- No scratch files, hooks, or leftover experiments are in any diff. This clone's hooks directory is unchanged.
- KTD2's answer is on #75 for ES-pins, and the deferred items are filed or noted on #75.
- KTD7's first-ref limit and the alternative are on #75 as a question for Rod and the buzai lead. Their answer is recorded before PR 3 opens, and Rod's sign-off on this plan does not stand in for it.
