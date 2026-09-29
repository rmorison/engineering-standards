---
title: Narrow the Starter Kit's git grep, fetch and pull Entries - Plan
type: fix
date: 2026-09-27
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
origin: https://github.com/rmorison/engineering-standards/issues/57
---

# Narrow the Starter Kit's git grep, fetch and pull Entries - Plan

## Goal Capsule

- Objective: an adopter who copies the starter kit no longer has arbitrary commands auto-approved through its `git grep`, `git fetch` or `git pull` entries, and a routine session still fetches and pulls without a prompt. The kit's README and the Python standard describe what the git entries still allow, and the kit check holds each of those claims.
- Means: drop `Bash(git grep:*)` (KTD1), replace `Bash(git fetch:*)` and `Bash(git pull:*)` with exact entries (KTD2, KTD3), move the three accepted-risk rows into `ALLOW_NEGATIVE` with flag-placement variants (KTD4), and hold the remaining `git log --output` route as an accepted risk (KTD5).
- Authority: the issue's acceptance criteria govern. Where this plan and the Claude Code permissions page disagree, the page wins, and the README records what was found.
- Execution profile: edits to `templates/.claude/settings.json`, `scripts/check-template-kit.mjs`, `templates/README.md`, and § The Limit in `code/python-standards.md`. Nothing else in `code/python-standards.md`, and no changes to hooks, `process/`, `docs/solutions/`, `.github/`, the leak-gate scripts, or the uv entries.
- Stop conditions: stop and ask if any new negative row passes against the pre-fix kit, because the matcher or the row would be wrong, not the kit. Stop and ask if Node 22 cannot be installed to run the checks, rather than shipping unverified fixtures.
- Finishes the work: `ce-work` on branch `57-starter-kit-git-entries`, shipped as one PR that closes #57. Rod merges.

---

## Product Contract

### Summary

Remove the kit's `git grep` entry, and replace the `git fetch` and `git pull` wildcards with the six exact forms that a routine session and this repository's branching standard use. Hold the closed routes with negative fixtures that cover flag placement, and bring the two documents that describe these entries back in line with what the check holds.

### Problem Frame

`templates/.claude/settings.json` is the kit every adopter copies. Three of its git entries are prefix rules on subcommands that take a command-running flag:

- `git grep -O<cmd>` (and `--open-files-in-pager=<cmd>`) runs `<cmd>`.
- `git fetch --upload-pack=<cmd>` and `git pull --upload-pack=<cmd>` run `<cmd>` through the shell for a local-path remote.

#56 recorded these as accepted risks instead of fixing them. `templates/README.md` says they "cannot be" fixed, and `ALLOW_ACCEPTED_RISK` asserts that the kit still approves each one. That is true only while the entries are wildcards. The README's own argument is that a prefix rule cannot exclude a flag that may appear anywhere after the prefix, which is why an exact entry, or no entry, is the only fix at the allow-list layer. `docs/solutions/best-practices/hold-a-stated-risk-with-a-fixture-that-fails-when-the-risk-is-gone.md` anticipates this change and says the rows then move to `ALLOW_NEGATIVE`.

Flag placement was verified on git 2.34.1 during planning, in scratch repositories with a local-path `origin`. Each of these ran the injected command and exited 0: `git fetch origin --upload-pack=…`, `git fetch --prune --upload-pack=… origin`, `git fetch origin master --upload-pack=…`, `git pull --ff-only --upload-pack=…` and `git pull origin master --upload-pack=…`. The `git grep -n -O…` and trailing `-O` spellings were not re-run: this session's sandbox refuses `git grep -O` even in a scratch repository. The README's existing record (git 2.43.0, `-O'<cmd>' needle`) stands, and the new grep rows are negative fixtures, which stay correct whether or not git accepts a given spelling.

Narrowing these three entries does not close every git route to a command. During review, `git log -1 --format='[remote "origin"]%n…uploadpack = <cmd>…' --output=.git/config` rewrote a scratch repository's config on git 2.34.1, and `git config --get remote.origin.uploadpack` returned the injected command. `Bash(git log:*)` approves that write, and a later approved `git fetch origin` or `git status` (through `core.fsmonitor`) would run what it planted. `git diff` and `git show` accept `--output` too.

### Key Decisions

- **Remove `git grep` from the allow list rather than keep a justified wildcard.** No wildcard spelling excludes `-O`, and an exact entry never matches because the search pattern varies. Repository search stays prompt-free through the built-in Grep tool and shell `grep`. Governs R1, R3.
- **Name `main` in the fetch and pull entries.** It is the default branch in `process/git-branching-strategy.md`, which documents `git fetch origin` and `git pull origin main`. An adopter on another default branch edits two entries and two fixture rows. Governs R2.

### Requirements

**Allow list**

- R1. No kit allow entry matches `git grep -O…`, `git grep --open-files-in-pager=…`, or `--upload-pack` on `git fetch` or `git pull`, in any flag position covered by KTD4 (AC 1).
- R2. These forms still need no prompt: `git fetch`, `git fetch origin`, `git fetch origin main`, `git pull`, `git pull --ff-only` and `git pull origin main` (AC 3).
- R3. No kit allow entry approves any `git grep` form. The README names the prompt-free search tools that replace it, without claiming whether Claude Code itself prompts for `git grep` (AC 3).

**Checks**

- R4. The three git rows leave `ALLOW_ACCEPTED_RISK` and join `ALLOW_NEGATIVE`, with the flag-placement variants in KTD4 beside them (AC 2).
- R5. `ALLOW_POSITIVE` has exactly one row per remaining git entry, under the existing exactly-one-match rule (AC 3).
- R6. Every new or changed fixture row was seen to fail against the entries it guards (KTD6) before it was trusted. The commands and output are in the PR body (AC 5).
- R9. The check asserts that `Bash(git log:*)` still approves a `--output` write to `.git/config`, so the README's statement of that route goes stale loudly if the entry is narrowed.

**Documentation**

- R7. `templates/README.md` says which git forms are approved, which prompt, and why. It names the `git log --output` route rather than implying `make` is the only one left, and no sentence in it claims more than the check holds (AC 4).
- R8. The starter-kit bullet in `code/python-standards.md` § The Limit matches the merged kit and carries the date it was last confirmed with the check (AC 4).

### Scope Boundaries

- `.env` reads through read-only command chains, and `UV_ENV_FILE`, which belong to #58.
- The uv entries, which #56 settled.
- Closing execution driven by git configuration: `remote.<name>.uploadpack`, `core.sshCommand`, `core.fsmonitor` and repository hooks. A rule on command text cannot see configuration, and the kept `git log`, `git diff` and `git show` wildcards can write `.git/config` through `--output` without a prompt (Problem Frame). #57 states that route and holds it with a fixture (R9); it does not narrow those entries.
- Files owned by parallel work: `process/repository-standards.md`, `.github/workflows/leaks.yml`, `scripts/leak-gate.sh`, `scripts/test-leak-gate.sh` and python-standards § Using gitleaks Instead (#62), and `docs/solutions/` (PR #63).
- Historical plans under `docs/plans/`.

#### Deferred to Follow-Up Work

- `docs/solutions/best-practices/hold-a-stated-risk-with-a-fixture-that-fails-when-the-risk-is-gone.md` quotes the three git rows as current `ALLOW_ACCEPTED_RISK` content. After #63 merges, a `ce-compound-refresh` pass should mark that quotation historical. The PR body says so; this PR does not touch `docs/solutions/`.
- `--output` on the `git log`, `git diff` and `git show` entries, and a flag-by-flag audit of the other wildcard git entries (`branch`, `checkout`, `stash` and the rest). Narrowing `log`, `diff` and `show` to exact forms would cost the session its most-used read commands, so it needs its own decision. The PR proposes a follow-up issue, and whether to file it is Rod's call.

### Success Criteria

- On the merged kit, `node scripts/check-template-kit.mjs` passes, and its summary line reports two accepted-risk cases (`make` and `git log --output`).
- With the three old wildcards restored in a scratch edit, the same check fails once for each git negative row and names the wildcard that approved it. It also reports `Bash(git grep:*)` as not covered by `ALLOW_POSITIVE`.

### Sources

- Issue #57 and its readiness comment.
- Claude Code permissions page, retrieved 2026-09-27: <https://code.claude.com/docs/en/permissions>. The permission-system table lists Grep under read-only tools with no approval required. "Read-only commands" lists `grep` in the built-in set and says only "read-only forms of `git`", without naming them.
- `process/git-branching-strategy.md`, Keeping Branches Current (`git fetch origin`) and the release steps (`git pull origin main`).
- `docs/plans/2026-09-25-2130-fix-narrow-uv-allow-entries-plan.md`, the #47 pattern this plan follows.
- `docs/solutions/best-practices/prove-a-check-fails-before-trusting-it-passes.md` and `hold-a-stated-risk-with-a-fixture-that-fails-when-the-risk-is-gone.md`. The second one's Examples section shows `Bash(git grep -n:*)` still approving `git grep -n -O…`.

---

## Planning Contract

### Key Technical Decisions

- KTD1. **`Bash(git grep:*)` is removed and nothing replaces it.** This implements the first Key Decision. The README should not claim that Claude Code's built-in read-only set does or does not cover `git grep`, because the permissions page does not list which git forms it includes.
- KTD2. **The fetch entries are `Bash(git fetch)`, `Bash(git fetch origin)` and `Bash(git fetch origin main)`, none with a wildcard.** Any trailing wildcard admits `--upload-pack` after it; `git fetch origin --upload-pack=…` ran during planning. These prompt by design: another branch, `--prune`, `--all`, `--tags`, and any other remote.
- KTD3. **The pull entries are `Bash(git pull)`, `Bash(git pull --ff-only)` and `Bash(git pull origin main)`, none with a wildcard.** The reason is the same as KTD2. `--rebase`, other branches and other remotes prompt.
- KTD4. **`ALLOW_NEGATIVE` gains twelve git rows.** Three are the moved rows, kept verbatim. The rest cover flag placement: before the positional arguments, after them, after another flag, and with the value as a separate argument.

  | Entry guarded | Rows |
  |---|---|
  | grep | `git grep -O'sh -c id' needle` (moved), `git grep -n -O'sh -c id' needle`, `git grep needle -O'sh -c id'`, `git grep --open-files-in-pager='sh -c id' needle` |
  | fetch | `git fetch --upload-pack='id; git-upload-pack' .` (moved), `git fetch origin --upload-pack='id; git-upload-pack'`, `git fetch origin main --upload-pack='id; git-upload-pack'`, `git fetch --prune --upload-pack='id; git-upload-pack' origin`, `git fetch origin --upload-pack 'id; git-upload-pack'` |
  | pull | `git pull --upload-pack='id; git-upload-pack' .` (moved), `git pull --ff-only --upload-pack='id; git-upload-pack'`, `git pull origin main --upload-pack='id; git-upload-pack'` |

  A comment in the style of the `remote -v` comment says why the rows exist: a prefix rule cannot exclude a flag that appears anywhere after it, so each exact entry is guarded by a row that starts with the entry's own text and adds the flag.
- KTD5. **`ALLOW_ACCEPTED_RISK` loses its three git rows and gains one for `git log --output`: `['Bash(git log:*)', "git log -1 --format=x --output=.git/config"]`.** The header comment's git paragraph is rewritten to say that `--output` writes caller-chosen text to any path, including `.git/config`, which is how an approved `git fetch origin` or `git status` can be made to run a command. This follows `docs/solutions/best-practices/hold-a-stated-risk-with-a-fixture-that-fails-when-the-risk-is-gone.md`: the README will state the risk (R7), so a row holds it (R9).
- KTD6. **The proof is manual, as in #44 and #56.** Scratch edits to `templates/.claude/settings.json` are run with the new check and reverted before commit:
  1. The three old wildcards replace the six new entries. Every new git negative row should fail and name its wildcard.
  2. Each tempting partial narrowing, one at a time, in place of the exact entries it would cover: `Bash(git grep -n:*)`, `Bash(git fetch origin:*)`, `Bash(git pull --ff-only:*)` and `Bash(git pull origin main:*)`. Each should fail on the placement rows that begin with its prefix. This is the evidence that the placement rows guard something the moved rows do not.
  3. Each of the six new entries deleted in turn. Its positive row should report no match. The old kit cannot prove these rows, because its wildcards also match every positive.
  4. The old wildcards added beside the new entries. Each new positive should report two matches.
  5. The three old git rows left in `ALLOW_ACCEPTED_RISK` against the new kit. Each should fail with "no allow entry approves", which shows that the move was forced rather than optional.
  6. `Bash(git log:*)` deleted. The `git log --output` accepted-risk row should fail, alongside the `git log --oneline -5` positive.

  Some runs print more than the rows they target, because `checkKitPermissions` also fails any allow entry that no positive matches exactly once. The U2 test scenarios give the full expected output of each run, and the PR body should match it.

### Assumptions

- The default branch is `main` for this repository and for adopters who follow its branching standard (see Key Decisions).

### Sequencing

U1 and U2 land in one commit, so no commit has fixtures that fail against the settings beside them. U3 depends on both. U4 comes last because it records the date the merged kit was confirmed.

---

## Implementation Units

### U1. Replace the three git entries

**Goal:** the kit's allow list carries the KTD2 and KTD3 entries, and no `git grep` entry.

**Requirements:** R1, R2, R3

**Dependencies:** none

**Files:** `templates/.claude/settings.json`

**Approach:** delete `Bash(git grep:*)` per KTD1. Put the three fetch entries where `Bash(git fetch:*)` was and the three pull entries where `Bash(git pull:*)` was. Leave every other entry as it is.

**Test scenarios:** covered by U2, which is the test for this file.

**Verification:** the U2 check passes against this file.

### U2. Move the rows and hold the new entries

**Goal:** `scripts/check-template-kit.mjs` fails if any of the three routes returns in any covered flag position, or if a new entry is mistyped.

**Requirements:** R3, R4, R5, R6, R9

**Dependencies:** U1

**Files:** `scripts/check-template-kit.mjs`

**Approach:**
1. In `ALLOW_POSITIVE`, remove `git grep -n TODO` and add `git fetch`, `git fetch origin main`, `git pull` and `git pull origin main` beside the existing `git fetch origin` and `git pull --ff-only`, for one row per entry.
2. Add the KTD4 rows and comment to `ALLOW_NEGATIVE`, after the `remote -v` rows.
3. Replace the three git rows in `ALLOW_ACCEPTED_RISK` with the `git log --output` row, and rewrite its comment's git paragraph, per KTD5.

**Execution note:** run KTD6 steps 1 to 6 before trusting any row, and keep each command and its output for the PR body. A row that passes on the pre-fix kit proves nothing.

**Patterns to follow:** the `remote -v` and uv option-placement rows and comments in `ALLOW_NEGATIVE`.

**Test scenarios:**
- Merged kit: the check passes. Each of the six new positive rows matches exactly one entry, all twelve git negative rows match none, and both accepted-risk rows are still approved.
- KTD6 step 1: 13 failures. Twelve are negative failures, each naming `Bash(git grep:*)`, `Bash(git fetch:*)` or `Bash(git pull:*)`, and one reports `Bash(git grep:*)` as not covered by `ALLOW_POSITIVE`.
- KTD6 step 2, `Bash(git grep -n:*)` added: 2 failures. `git grep -n -O'sh -c id' needle` fails, and the entry is reported as not covered.
- KTD6 step 2, `Bash(git fetch origin:*)` in place of `Bash(git fetch origin)` and `Bash(git fetch origin main)`: 3 failures, one for each row that begins `git fetch origin`.
- KTD6 step 2, `Bash(git pull --ff-only:*)` and `Bash(git pull origin main:*)`, each in place of its exact entry: 1 failure each, on the matching pull placement row.
- KTD6 step 3: six runs, each with 1 failure, a no-match report for the deleted entry's positive.
- KTD6 step 4: 27 failures. Six positives report two matches, the twelve git negative rows fail, and nine entries are reported as not covered: the six new ones, because no positive now matches them exactly once, plus the three wildcards.
- KTD6 step 5: 3 failures, each "no allow entry approves".
- KTD6 step 6: 2 failures. The `git log --output` accepted-risk row fails, and so does the `git log --oneline -5` positive.
- The rule-syntax fixtures still pass unchanged.

**Verification:** the check passes on the merged kit, and each failure above was observed and recorded for the PR body.

### U3. Make the kit README match

**Goal:** `templates/README.md` says what the three git entries approve now, and every claim in it is backed by a U2 row or a quoted source.

**Requirements:** R3, R7

**Dependencies:** U1, U2

**Files:** `templates/README.md`

**Approach:**
1. In "Why `allow` names git subcommands rather than `Bash(git:*)`", replace "and through three git entries described below" in the `rm` paragraph with a pointer to the `git log --output` route described below. `make` must not read as the only route left.
2. Remove `grep` from the "Read-only subcommands are listed generously" list.
3. Replace the paragraph that opens "Three git entries run arbitrary commands through a flag" with one that says why these three were narrowed rather than stated. It covers:
   - the flag facts already recorded, and why a prefix rule cannot exclude a later flag, so the fix is an exact entry or none;
   - the six exact entries (KTD2, KTD3) and what prompts;
   - that when a fetch or pull form prompts, the fix is another exact entry such as `Bash(git fetch --prune)`, never a trailing wildcard, because any `Bash(git fetch …:*)` readmits `--upload-pack`;
   - that `git grep` has no entry, and that the Grep tool and shell `grep` search without a prompt, citing the permissions page without claiming how Claude Code treats `git grep` itself;
   - that an adopter on another default branch edits the two `main` entries and their fixture rows;
   - the retained warning that the other entries have not been audited flag by flag, with `git log --output=.git/config` as the known example (Problem Frame, KTD5).
4. In the closing check paragraph under "Why `Bash(make:*)` stays", say that `ALLOW_ACCEPTED_RISK` holds the `make --eval` and `git log --output` forms and that `ALLOW_NEGATIVE` holds the git flag forms.

**Test expectation:** none beyond `check-docs.mjs`, since this unit is prose only.

**Verification:** `node scripts/check-docs.mjs` passes. Each factual sentence added maps to a U2 row, a quoted doc, or a git run recorded in Problem Frame.

### U4. Update the Limit bullet

**Goal:** the starter-kit bullet in § The Limit describes the merged kit.

**Requirements:** R8

**Dependencies:** U1, U2, U3

**Files:** `code/python-standards.md` (§ The Limit only)

**Approach:** in the first bullet, replace "and so do `git grep -O` and `git fetch`/`git pull --upload-pack`" with a sentence saying that no kit allow entry approves those forms any more, but that `git log --output` can still write `.git/config` for a later approved git command to act on. Re-date "last confirmed" to the day the U2 check was run on the final head. Leave the link to the README's uv section as it is.

**Test expectation:** none, since this unit is prose only. The U2 check confirms the claim.

**Verification:** on the final head, the U2 check approves none of the grep, fetch or pull forms the bullet names, and it approves `make --eval` and `git log --output`. `check-docs.mjs` and `check_secret_refs.py --standard` pass.

---

## Verification Contract

| Gate | Command | Proves |
|---|---|---|
| Kit permissions | `node scripts/check-template-kit.mjs` | R1, R2, R3, R4, R5, R9 on the merged kit |
| Fail-first proof | the same command against each KTD6 scratch edit | R6. Commands and output go in the PR body |
| Doc checks | `npm ci --prefix scripts` then `node scripts/check-docs.mjs` | links, anchors and fences in U3 and U4 |
| Secret refs | `python3 scripts/check_secret_refs.py --standard` | U4 did not break the standard's parsed examples |
| CI | the `docs.yml` jobs on the PR head | the same gates on Node 22 |

Node is not installed in this environment. Install Node 22, the version CI pins, before starting U2.

---

## Definition of Done

- All gates above pass locally and in CI on the PR head.
- The PR body says "Closes #57" and records every KTD6 run with its command and output.
- No sentence in `templates/README.md` or § The Limit claims an approval or a prompt that no fixture or quoted source backs.
- The PR body notes the `docs/solutions/` quotation deferred to a refresh after #63, and proposes the `--output` follow-up issue for Rod to decide on.
- No scratch settings edits or abandoned fixture experiments remain in the diff.
