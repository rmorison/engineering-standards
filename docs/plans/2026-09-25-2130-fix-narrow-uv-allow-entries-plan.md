---
title: Narrow the Starter Kit's uv Allow Entries - Plan
type: fix
date: 2026-09-25
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
origin: https://github.com/rmorison/engineering-standards/issues/47
---

# Narrow the Starter Kit's uv Allow Entries - Plan

## Goal Capsule

- Objective: an adopter who copies the starter kit no longer has arbitrary commands auto-approved by putting `uv run` in front of them, and every claim the kit and the Python standard make about what its allow list approves is true and held by CI.
- Means: replace `Bash(uv:*)` with named uv entries (KTD1, KTD2), keep `Bash(make:*)` and hold its risk as a checked fact (KTD4), and move the claims into fixtures in `scripts/check-template-kit.mjs` (KTD3, KTD5).
- Authority: the R-IDs govern the kit's behavior. Where this plan and the Claude Code permissions page disagree, the page wins and the R records what was found.
- Execution profile: edits to `templates/.claude/settings.json`, `scripts/check-template-kit.mjs`, `templates/README.md` and `code/python-standards.md`. No changes to hooks, `process/`, `ai/`, or historical plans.
- Stop conditions: stop and ask if a pre-fix run of the check with the new fixtures does not fail on the new negative rows, other than the `uvx` row KTD6 proves separately (the matcher would then be wrong, not the kit). Stop and ask if Node 22 cannot be installed to run the checks, rather than shipping unverified fixtures.
- Finishes the work: `ce-work` or a human on branch `47-narrow-uv-allow-entries`, shipped as one PR closing #47.

---

## Product Contract

### Summary

Replace the kit's `Bash(uv:*)` with entries for the uv commands a routine session needs, so `uv run cat .env`, `uv run env`, `uv run op read …`, `uv run bash -c …` and `uv run rm -rf …` reach a human prompt. Keep `Bash(make:*)` and say plainly, with a fixture behind it, that it approves any target. Correct the two documents whose statements the change makes false or stale.

### Problem Frame

`templates/.claude/settings.json` is the kit every adopter is told to copy. Its `Bash(uv:*)` entry is a prefix rule, and `uv run` is a general command launcher, so any command becomes pre-approved by prefixing it. Claude Code does not strip `uv run` before matching: its fixed wrapper list is `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `command`, `builtin`, `noglob` and bare `xargs`, and the permissions page's Wrappers section names development-environment runners such as `npx` and `devbox run` as not stripped, adding that a rule like `Bash(devbox run *)` "matches whatever comes after `run`" (retrieved 2026-09-25). The page does not name uv; uv is in the same class.

This is the shape #44 fixed for `Bash(git remote -v:*)`, and it falsifies a sentence #44 left standing. `templates/README.md` says "`rm` appears in no `allow` entry, so a variant the deny rule misses still reaches a human prompt". `uv run rm -rf build` starts with `uv`, so the `Bash(rm -rf:*)` deny never sees it and the allow list approves it.

Removing `Bash(uv:*)` alone does not make that sentence true. `Bash(make:*)` approves `make --eval='x: ; @cat .env' x`, which GNU Make 4.3 runs (verified during research, exit 0). Any command reaches the shell through `make` as well.

The secrets rule shipped in #46 (`code/python-standards.md`, Configuration Management → Secrets → The Limit) records the uv hole as a dated fact. The #30 plan deferred it with the note that the claim "should then be held by `check-template-kit.mjs` rather than asserted" (`docs/plans/2026-09-24-0028-feat-no-secrets-at-rest-plan.md`, Deferred to Follow-Up Work).

### Key Decisions

- Named `uv run` entries for the kit's own tools rather than only package-management entries. Livable: the Python standard's CI and Makefile type `uv run pytest|ruff|mypy`. (session-settled: user-approved — chosen over relying on the bare `pytest`/`ruff`/`mypy` entries alone: agents following the standard type the `uv run` form.) Governs R1, R2.
- Keep `Bash(make:*)` and state its risk, backed by a fixture. Make targets are per-project, so a kit cannot name them. (session-settled: user-approved — chosen over dropping or narrowing `make` in this change: a narrowed list would name targets the adopter does not have.) Governs R6, R7.

### Requirements

**Allow list**

- R1. No entry in the kit's `permissions.allow` matches `uv run` followed by an arbitrary command, including `cat .env`, `env`, `op read op://dev/a/b`, `bash -c "cat .env"`, `rm -rf build`, and the option-placement variants in KTD3.
- R2. A routine Python session's uv commands still need no prompt: `uv sync`, `uv lock`, and `uv run` of `pytest`, `ruff` and `mypy` with any arguments.
- R3. Commands that change the dependency set or launch something other than the three named tools prompt by design, and the README says which ones (KTD2).

**Checks**

- R4. `scripts/check-template-kit.mjs` holds R1 with `ALLOW_NEGATIVE` rows and holds R2 with one `ALLOW_POSITIVE` row per new entry, under the existing exactly-one-match rule.
- R5. Every new or changed fixture row was seen to fail against the pre-fix kit (for a positive row, against the kit with its entry removed; for the `uvx` row, against the scratch widening in KTD6) before it was trusted, and the output is recorded in the PR body.
- R6. The check asserts that `Bash(make:*)` approves an arbitrary-target form, so the README's statement of that risk goes stale loudly if `make` is ever narrowed.

**Documentation**

- R7. `templates/README.md` states what the allow list does and does not route to a human, including the `make` route, and no sentence in it claims more than the check holds.
- R8. `code/python-standards.md`'s Limit bullet about the kit matches the merged kit and is re-verified with the matcher on the merge date.

### Scope Boundaries

- Hooks and sandboxing as the real boundary. The README already names them; this change does not add a command-checking hook.
- The `git grep -O` exception, already stated in the README.
- Historical documents under `archive/` and `docs/plans/`, including the #30 plan's deferred note. They record what was true when written.

#### Deferred to Follow-Up Work

- Compound commands built from built-in read-only commands. Claude Code splits `uv run pytest && cat .env` and checks each part, but `cat` is on its built-in read-only list, so the second part runs without a prompt unless a deny or ask rule covers `.env`. That is independent of `uv` and needs its own issue.
- `UV_ENV_FILE` exported in a developer's shell makes every approved `uv run pytest` load that file with nothing in the command text to show it. Setting `UV_NO_ENV_FILE=1` in the kit is untested; it belongs with the secrets standard, as a follow-up issue.

### Success Criteria

- Against the merged kit, `node scripts/check-template-kit.mjs` passes and its summary line reports the new negative and accepted-risk counts.
- With `Bash(uv:*)` restored in a scratch copy, the same check fails and names each uv negative row except `uvx cowsay`, which that rule never matched.

### Sources

- Claude Code permissions page, Wrappers and compound-command sections, retrieved 2026-09-25: <https://code.claude.com/docs/en/permissions>.
- uv docs on `--env-file` / `UV_ENV_FILE` and on build backends running arbitrary Python code, retrieved 2026-09-25: <https://docs.astral.sh/uv/>.
- #44's fix and plan: `docs/plans/2026-09-21-2044-fix-template-hooks-and-deny-rules-plan.md` (KD3 makes `templates/README.md` the one owner of the permission statement).
- `docs/solutions/best-practices/prove-a-check-fails-before-trusting-it-passes.md`, `a-corrected-claim-is-not-a-verified-claim.md`, `a-check-must-read-a-file-the-way-its-consumer-does.md`.

---

## Planning Contract

### Key Technical Decisions

- KTD1. **The uv entries are `Bash(uv sync)`, `Bash(uv sync --all-extras)`, `Bash(uv lock)`, `Bash(uv lock --upgrade)`, `Bash(uv run pytest:*)`, `Bash(uv run ruff:*)` and `Bash(uv run mypy:*)`.** They cover every uv command the Python standard's Makefile and CI type for testing, linting and type checking, plus the four sync and lock forms the standard documents. The sync and lock entries are exact because a wildcard there would approve uv's index, `--find-links`, `--script`, `--project` and `--directory` options, which install or build packages from a source nobody chose, the thing R3 routes to a human. The three `uv run` entries keep a wildcard, which departs from the docs' exact-rule example: test and lint invocations vary by path and flag, and an exact rule would be widened back within a week. A flag placed before the tool name (`uv run --with x pytest`) is not matched and prompts. (session-settled: user-approved — chosen over package-management-only entries: see Key Decisions.)
- KTD2. **`uv add` and `uv remove` are not pre-approved.** The issue suggested `uv add`; research argues against it. Both change `pyproject.toml` and the lockfile, and `uv add` installs any package by name, whose build backend "may run arbitrary Python code" per the uv docs. Adding a dependency is a decision for a human. Also left to prompt: `uvx`, `uv tool run`, `uv pip`, `uv run python`, and the `uv run` forms of `detect-secrets`, `pip-audit`, `pre-commit` and `mkdocs`. The first three are reached through `make` targets under `Bash(make:*)`.
- KTD3. **Negative rows cover option placement, not just the five commands in the issue.** A negative sweep only excludes the spellings someone wrote down (the `remote -v` comment in the check). Add `uv run -- cat .env`, `uv run --with requests env`, `uv run python -c "print(1)"`, `uv run --env-file .env pytest`, `uv run --env-file .env -- python -m app` (the secrets standard's runner form), `uv sync --default-index https://example.invalid/simple`, `uv sync --script tool.py`, `uv lock --project /tmp/p`, `uvx cowsay`, `uv tool run ruff`, `uv pip install requests`, `uv add requests` and `uv remove requests`.
- KTD4. **A new `ALLOW_ACCEPTED_RISK` list holds entries known to approve a dangerous form, as `[entry, command]` pairs that must match.** Its first row is `Bash(make:*)` with `make --eval='x: ; @cat .env' x`. It is not in `ALLOW_NEGATIVE` because the kit keeps the entry on purpose. Its count joins the summary line.
- KTD5. **`templates/README.md` owns the statement; `code/python-standards.md` keeps one re-verified sentence and links to it.** This follows #44 KD3. The standard's reader needs the fact where the secrets rule is stated, so the sentence stays, dated, with a link for the reasoning.
- KTD6. **Proof is manual, as in #44.** There is no mutation mode in the check and adding one is out of scope. Restore `Bash(uv:*)` in a scratch copy and run the check to see each uv negative fail. `uvx cowsay` is the exception: `Bash(uv:*)` expands to `uv *` and never matched it, so prove that row by adding `Bash(uvx:*)` to a scratch copy instead. Delete each new uv entry in turn to see its positive fail. Delete `Bash(make:*)` to see the accepted-risk row fail. Paste the output into the PR body.

### Sequencing

U1 then U2 in one commit, so no commit has fixtures that fail against the settings beside them. U3 depends on both. U4 last, since it records the date the merged kit was verified.

---

## Implementation Units

### U1. Narrow the uv entries in the kit

**Goal:** the kit's allow list carries the KTD1 entries in place of `Bash(uv:*)`.

**Requirements:** R1, R2, R3

**Dependencies:** none

**Files:** `templates/.claude/settings.json`

**Approach:** replace the one entry with the seven from KTD1 in the same position. `Bash(make:*)` stays. `Bash(pytest:*)`, `Bash(ruff:*)` and `Bash(mypy:*)` stay; they are anchored at the start of the command and never match a `uv run` form, so no positive row matches two entries (verified during research by replicating the matcher over the old and new lists).

**Test scenarios:** covered by U2, which is the test for this file.

**Verification:** the check in U2 passes against this file.

### U2. Hold the claims with fixtures

**Goal:** `scripts/check-template-kit.mjs` fails if any uv hole returns, if a new entry is mistyped, or if `make` is narrowed without the README changing.

**Requirements:** R4, R5, R6

**Dependencies:** U1

**Files:** `scripts/check-template-kit.mjs`

**Approach:**
1. In `ALLOW_POSITIVE`, replace `uv sync` with one row per KTD1 entry: `uv sync`, `uv sync --all-extras`, `uv lock`, `uv lock --upgrade`, `uv run pytest -q`, `uv run ruff check .`, `uv run mypy src`.
2. Add the issue's five commands and the KTD3 rows to `ALLOW_NEGATIVE`, with a comment in the style of the existing `remote -v` comment that says why `uv run` is a launcher and why option-placement rows exist.
3. Add `ALLOW_ACCEPTED_RISK` per KTD4, checked in `checkKitPermissions` beside `DENY_POSITIVE`. A row fails when its entry is missing from the allow list or does not match its command. The comment states why the entry stays.
4. Add the new count to the summary line.

**Execution note:** follow KTD6 before trusting any row. A row that passes on the pre-fix kit proves nothing.

**Patterns to follow:** the `remote -v` rows and comment in `ALLOW_NEGATIVE`; the `DENY_POSITIVE` loop's failure-message style.

**Test scenarios:**
- Merged kit: the check passes. Each new positive row matches exactly one entry, and every negative row matches none.
- `Bash(uv:*)` restored beside the new entries: every uv negative row except `uvx cowsay` fails and names `Bash(uv:*)`. Each new positive row reports two matches.
- `Bash(uvx:*)` added to a scratch copy: the `uvx cowsay` row fails and names it.
- `Bash(uv:*)` restored in place of the new entries: every uv negative row except `uvx cowsay` fails, and the new positive rows pass by matching `Bash(uv:*)`. This is why positives are proven by deletion, not by the old kit.
- Each new uv entry deleted in turn: its positive row reports no match.
- `Bash(make:*)` deleted: the accepted-risk row fails, naming the missing entry.
- `Bash(uv run pytest:*)` mistyped as `Bash(uv run pytest*)`: `uv run pytest -q` still matches, so no row catches it. Confirm the matcher reads it that way and record it as a known limit of the positive rows, not a new fixture.
- Rule-syntax fixtures still pass unchanged.

**Verification:** the check passes on the merged kit, and each failure above was observed and recorded for the PR body.

### U3. Make the kit README true again

**Goal:** `templates/README.md` says what the allow list routes to a human and what it does not, without claiming more than U2 holds.

**Requirements:** R3, R7

**Dependencies:** U1, U2

**Files:** `templates/README.md`

**Approach:**
1. Rewrite the `rm` sentence in "Why `allow` names git subcommands rather than `Bash(git:*)`": no allow entry starts with `rm` and no uv entry launches arbitrary commands, but `Bash(make:*)` runs any target, including one defined on the command line, so a deny rule on `rm` is decorative against `make`.
2. Add a subsection on why `allow` names uv commands rather than `Bash(uv:*)`. Quote the Wrappers sentence (retrieved 2026-09-25) and say uv is in that class without claiming the page names it. State why the sync and lock entries are exact and the `uv run` entries keep a wildcard (KTD1), what prompts by design (KTD2), and that `uv sync`, `uv lock` and `uv run pytest` still execute project code (build backends, `conftest.py`). A named entry controls which program starts, not what that program does.
3. Add a short `make` paragraph: why it stays (the `make` Key Decision) and that `ALLOW_ACCEPTED_RISK` holds the fact.
4. Update the closing "holds the list to both directions" paragraph to name the uv negative rows and the accepted-risk row.

**Test expectation:** none beyond `check-docs.mjs` — prose only. Every claim in it is backed by a U2 row or a quoted source.

**Verification:** `node scripts/check-docs.mjs` passes. Each factual sentence added maps to a U2 fixture, a quoted doc, or the Make run recorded in Problem Frame.

### U4. Update the secrets standard's Limit bullet

**Goal:** the Limit section describes the merged kit.

**Requirements:** R8

**Dependencies:** U1, U2, U3

**Files:** `code/python-standards.md`

**Approach:** rewrite the first bullet under Configuration Management → Secrets → The Limit. It now says the kit's uv entries are named, so `uv run op read`, `uv run env` and `uv run cat` prompt, held by `ALLOW_NEGATIVE`, and that `Bash(make:*)` still approves any target, held by `ALLOW_ACCEPTED_RISK`. Link to the templates README section per KTD5 and re-date it to the merge-day run. The bullet about Makefile targets invoking the manager stays as is; it is now the operative rule rather than a companion to a wider hole.

**Test expectation:** none — prose. Verified by running the matcher.

**Verification:** on the merge date, the matcher run in U2 approves none of the three uv forms the bullet names and approves the `make --eval` form. `check-docs.mjs` passes, including the new link's anchor.

---

## Verification Contract

| Gate | Command | Proves |
|---|---|---|
| Kit permissions | `node scripts/check-template-kit.mjs` | R1, R2, R4, R6 on the merged kit |
| Fail-first proof | same command against the scratch variants in U2 | R5; output pasted in the PR body |
| Doc checks | `npm ci --prefix scripts && node scripts/check-docs.mjs` | links, anchors and fences in U3 and U4 |
| Secret refs | `node scripts/check-secret-refs.mjs --standard` | U4 did not break the standard's parsed examples |

All three scripts need Node 22, the version CI uses in `.github/workflows/docs.yml`. Node is not installed in the planning environment; install it before U2.

---

## Definition of Done

- The four gates above pass locally and in CI on the PR head.
- The PR body records each U2 fail-first run with its output.
- No sentence in `templates/README.md` or the Limit section claims an approval or a prompt that no fixture or quoted source backs.
- Follow-up issues are filed for the two deferred items.
- No scratch settings copies or abandoned fixture experiments remain in the diff.
