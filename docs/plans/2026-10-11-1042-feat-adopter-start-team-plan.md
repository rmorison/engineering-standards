---
title: start-team Gaps a New Adopter Hits First (#110 items 1, 3, 4, 7) - Plan
type: feat
date: 2026-10-11
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
origin: https://github.com/rmorison/engineering-standards/issues/110
---

# start-team Gaps a New Adopter Hits First (#110 items 1, 3, 4, 7) - Plan

## Goal Capsule

- Objective: a new adopter who runs start-team gets roles that match the workflow they pinned, a plugin update that actually arrives, an honest guardrail result when no private-value list is configured, and no second lead beside one they started by hand.
- Means: derive the role URL from the adoption line's ref and compare the installed plugin with the pin (item 1); a CI check that a plugin change raises `plugin.json`'s version (item 3); a presence-only value-list check in start-team and the guardrail check (item 4); an adoption-line-aware "is a lead running?" step (item 7).
- Authority: #110 and its comments are the spec. D1 to D6 below are **PROPOSED** for the operator's sign-off on #110. Where this plan and a sign-off comment disagree, the sign-off wins.
- Execution profile: `plugins/agent-team/` (start-team `SKILL.md`, `agents/lead.md`, `agents/worker.md`, `README.md`, `plugin.json` 0.10.0 to 0.11.0); `process/agent-team-workflow.md` § 4 "The guardrail check" and § 9 only; `scripts/check-template-kit.mjs` (new check 12) and `.github/workflows/docs.yml`'s `check-template-kit` job. No change to the hooks, `pm-trial/`, or #110's items 2, 5 and 6.
- Stop conditions: stop, comment on #110 and ping the lead if any proof would need the real git config, the real value list, `~/.claude/settings.json` or the installed plugins; if the CI base commit (`HEAD^1`) isn't what U2 expects on a pull request run; or if a proof session can't be cleaned up.
- Finishes the work: `ce-work` on branch `110-adopter-start-team`, one PR saying `Part of #110` with no closing keyword. The operator merges.

---

## Product Contract

### Summary

The operator is about to try the agent team with a new adopter. Four of #110's residuals are the ones that adopter is likeliest to hit: a pinned adoption line still loads roles from `main`; a plugin change that forgets the version bump never reaches installed users; a guardrail check passes while no private values are scanned; and an adopter who ran a lead by hand before installing the plugin gets a second lead.

### Requirements

- R1. (item 1) Every role start that reads a role by URL reads it at the ref the project's workflow URL names, falling back to `main` only when that ref has no role file, and saying so. Where the role comes from the installed plugin instead, start-team tells the operator when the installed version differs from the version at the pin.
- R2. (item 3) A pull request that changes any file under a plugin directory without raising that plugin's `plugin.json` version fails CI. Seen failing first, on this PR's own CI run.
- R3. (item 4) start-team and every guardrail check learn whether a value list is configured from presence alone: the git config key and whether it names an existing file. Nothing reads the list. A session with none says so in its result.
- R4. (item 7) When no lead record exists but the adoption line does, start-team asks the operator whether a lead is already running before it starts one. An adopter's first run, with neither, is not asked.
- R5. `plugin.json` goes to 0.11.0; README and § 9 describe the new behaviour; no host-specific detail lands in the repository.

### Acceptance Examples

- AE1 (R1). A project's adoption line links `.../blob/1fecda5/process/agent-team-workflow.md`. A Route B lead's opening prompt names `.../blob/1fecda5/plugins/agent-team/agents/lead.md`. With a ref older than the plugin (`c1d78fe`, where that file is 404), it names `main`'s URL and start-team says the role is newer than the pin.
- AE2 (R1). The installed plugin is 0.9.0 and the pin's `plugin.json` says 0.10.0. start-team's report says Route A's role comes from 0.9.0, not the pin's 0.10.0, and how to match them.
- AE3 (R2). A commit that edits `plugins/agent-team/README.md` and leaves `plugin.json` at 0.10.0 fails `check-template-kit` in CI with a message naming the plugin and both versions. Raising it to 0.11.0 passes.
- AE4 (R3). With `leakgate.values` unset, a worker's first ping reads "Guardrails: passed … value list: none". start-team lists "no private-value list" among the prerequisites missing, and the lead passes it on.
- AE5 (R4). In a scratch project with the adoption line and no `lead.json`, start-team lists the sessions it found in the project, asks whether a lead is already running, and starts nothing until answered.

### Scope Boundaries

- #110 items 2 (simultaneous runs), 5 (re-run route) and 6 (lead's guardrail window) stay open.
- #127 (the route order) is not in scope.
- start-team's own text comes from the installed plugin and reads § 8/§ 9 at `main`; making start-team itself follow the pin is not attempted (see Risks).
- No change to `claude_leak_hook.py`, its tests, or how the hook reads the list.

---

## Planning Contract

### Decisions (PROPOSED for the operator's sign-off)

**D1. Roles load at the pin's ref (item 1).**
- The role URL is the workflow URL with `process/agent-team-workflow.md` replaced by `plugins/agent-team/agents/<role>.md`, same owner, repository and ref. A workflow URL not of the form `https://github.com/<owner>/<repo>/blob/<ref>/process/agent-team-workflow.md` gets `main`'s URL.
- start-team checks that both role files exist at that ref before using them (`gh api repos/<owner>/<repo>/contents/plugins/agent-team/agents/<role>.md?ref=<ref>`). Only an HTTP 404 counts as absent: then it uses `main`'s URL for that role and tells the operator the role is newer than the pin, so where the two differ the workflow they pinned wins (each role already says so). Any other failure (gh signed out, network, rate limit) keeps the pinned URL, skips the version comparison below, and tells the operator the pin couldn't be checked.
- start-team puts **both** role URLs in the opening prompt: the lead's, and "start each worker with the worker role at <worker role URL>". A lead loaded at an older pin has a `lead.md` that names `main`'s worker URL (as at `1fecda5`), so only the prompt reaches it. lead.md's worker route 1 and route 3 use the prompt's worker URL when it gives one, and otherwise derive it from the workflow URL the same way.
- Route B's two prompts and Route C name the lead role URL **first** and the installed plugin's copy as the fallback. Today the installed copy comes first, but it can lag both `main` and the pin: the operator's machine runs 0.9.0 while `main` is 0.10.0.
- Route A starts with `--agent agent-team:lead`, which always loads the installed plugin, and the lead's CLI workers load `agent-team:worker` the same way. So start-team compares versions: `claude plugin list --json` gives the installed `agent-team` version, and `gh api …/contents/plugins/agent-team/.claude-plugin/plugin.json?ref=<ref>` gives the pin's. A difference is a prerequisite warning, not a stop: the report names both versions and says Route A's roles come from the installed copy, with the pinned workflow winning where they differ. It points to the README's pinning section for matching them; how to move an installed copy *back* to an older pin is checked in the build (Verification Contract) before the warning prescribes any command. An unpinned project (`main`) gets the same comparison, which also catches an installed copy older than `main`.
- What a pinned adopter gets: Routes B and C, and every worker started by a host session tool, read roles at the pin. Route A and CLI workers read the installed plugin's roles, and start-team says when that copy differs from the pin. When the plugin is newer than the pin, its roles may name workflow steps the pinned document lacks; the roles defer to the workflow, so the pinned document wins.

**D2. The version check (item 3): check 12 in `check-template-kit.mjs`.**
- Rule: for each plugin directory under `plugins/`, if `git diff --name-only <base> -- plugins/<name>/` lists any file (working tree against the base, so a local run catches it before a commit), the working tree's `plugin.json` version must be greater than the base's, compared as `MAJOR.MINOR.PATCH` integers. A non-numeric version fails. A plugin with no `plugin.json` at the base (a new plugin) passes.
- The base: `--base <rev>` when given; otherwise `git merge-base HEAD origin/main`. No base that resolves is a failure, not a skip: the script's rule is that a check that ran on nothing reports a failure.
- CI: the `check-template-kit` job's checkout gets `fetch-depth: 2` and the step runs `node scripts/check-template-kit.mjs --base HEAD^1`. On `pull_request`, the checkout is the merge commit, whose first parent is the base branch's tip, so the diff is exactly the PR's change against today's base. On a push to `main` (squash merges), `HEAD^1` is the commit before, so two PRs that each bumped to the same version and both merged fail on `main` afterwards. The job's `paths` already include `plugins/**`.
- A pure function decides each plugin's result from (changed files, base version, head version), with fixture cases run every time, as checks 8's fixtures are; each fixture is seen failing by inverting it once.
- Seen failing first in CI: the PR's first pushed commit carries check 12 and the plugin edits with `plugin.json` still at 0.10.0, so CI's `check-template-kit` fails on it; the next commit raises it to 0.11.0. Both run links go in the PR body.

**D3. The value-list presence check (item 4).**
- Grounded in `read_list()`: `git config --global --get leakgate.values`; unset, empty or `none` means no list (the hook allows outbound commands and notes "value rules skipped"); a value that isn't absolute or `~/`, or names no file, makes the hook deny every outbound command.
- One command, which prints one of three words and never the path or the list. Directional:

  ```sh
  v=$(git config --global --get leakgate.values); rc=$?; if [ $rc -gt 1 ]; then echo "value list: broken"; else case "$v" in ""|none) echo "value list: none";; *) case "$v" in "~/"*) v="$HOME/${v#\~/}";; esac; case "$v" in /*) if test -f "$v" && test -r "$v" && test -s "$v"; then echo "value list: declared"; else echo "value list: broken"; fi;; *) echo "value list: broken";; esac;; esac; fi
  ```

  A git error (status above 1) is "broken", as the hook denies on it. `test -f`, `-r` and `-s` read only the file's type, access and size, which the presence rule allows; an empty or unreadable list is "broken", as the hook denies on those too. A non-empty list whose lines are all comments or bad still shows "declared"; the hook's own denial reports that the first time a session posts.
- **start-team step 4:** a new prerequisite, graded warn if missing like the others. "none": warn that the leak hook still blocks gate escapes but scans no private values, and how to declare a list (link to repository-standards § Guarding Agent Sessions). "broken": warn that every GitHub post from the team will be denied until it is fixed.
- **The guardrail check (§ 4):** after the canaries, the session runs the command and adds its word to the result it reports ("Guardrails: passed …; value list: none"). It never changes the result: not a fail, not a restart.

**D4. "none" is a prerequisite warning, not a guardrail fail.** The canaries prove the hooks are registered and fire; they still block gate escapes, merges, settings writes and default-branch pushes with no list. `none` is a valid declaration (repository-standards allows it for a project with nothing private). Failing it would restart sessions into `default`, which scans no more values than `auto` does. So it lowers no mode: start-team lists it among the missing prerequisites, the lead tells the operator once in its first message, and each session's result line names it so a pass is never read as "values scanned". "broken" is a warning too: the hook already fails closed on it.

**D5. A lead started by hand (item 7).** Step 1 gains reading the adoption line (step 5's search, moved earlier; step 5 then only adds a missing line). Step 2 adds, when there is no lead record:
- **No adoption line:** the first ever run. Carry on as today, with no question.
- **An adoption line:** list what may be a lead: `claude agents --json` entries (running ones only, not `--all`) whose `cwd` is the main checkout or one of its worktrees (`git worktree list`), any name, leaving out this session itself, and any ListAgents name ending in `-lead` or containing the project name. Ask the operator whether a lead is already running, naming those candidates. Yes: tell them how to reach it, and stop. No: carry on.
- Asking once costs an adopter who added the line by hand but never ran a lead one answer, and an adopter on their first run never sees it.

**D6. Recording a lead started by hand (item 7, optional): recommend not building it.** It would have step 2's "yes" branch write `lead.json` with `route: "manual"` and its address before stopping, and step 8 allow `manual`, so the next run wouldn't ask again. #110 asks only for the question, no requirement needs the record, and without it the cost is the same one question on a later run. If the operator wants it, it is those two edits.

### Implementation Units

- U1. **start-team SKILL.md** (D1, D3, D4, D5, D6). Step 1 reads the adoption line and derives the workflow URL and role URLs; step 2 gains the no-record branch; step 4 gains the value-list prerequisite and the plugin-version comparison; step 5 only adds a missing line; step 7's Route B prompts and Route C name the role URL first; step 7 puts the worker role URL in the opening prompt; step 9 reports the version and value-list warnings. Test expectation: the scratch-project proofs in the Verification Contract.
- U2. **check 12** (D2) in `scripts/check-template-kit.mjs`, with its header doc and fixtures, and `.github/workflows/docs.yml`'s job (`fetch-depth: 2`, `--base HEAD^1`). Tests: fixtures for changed+bumped (pass), changed+same (fail), changed+lower (fail), unchanged+same (pass), new plugin (pass), non-numeric version (fail); a missing base fails; live run in a scratch clone with an unbumped edit fails, then passes after the bump.
- U3. **lead.md and worker.md** (D1, D3). lead.md: the worker role URL from the opening prompt, else derived from the workflow URL's ref; first message includes the value-list word and any version warning start-team passed. worker.md: the first ping's guardrail line includes the value-list word.
- U4. **Workflow § 4 and § 9** (D3, D4). § 4 "The guardrail check": the value-list command after the canaries, and that its word is reported, never judged. § 9 "Both hooks installed": a value list declared, or `none` on purpose, with the reason. Nothing else in the workflow changes.
- U5. **README and plugin.json** (R5). README: pinning now covers roles read by URL; the version-bump sentence points to check 12. `plugin.json` 0.11.0 lands in the second commit (D2).

### Risks

- start-team itself runs from the installed plugin and reads § 8/§ 9 at `main` (its line 8). A pinned adopter's start-team steps can be newer than their pin. D1's version warning surfaces it; following the pin in start-team's own text is left for a follow-up if the operator wants it.
- `fetch-depth: 2` and `HEAD^1` rest on `actions/checkout` checking out the PR merge commit. The first CI run proves it; if it doesn't hold, stop (Stop conditions).
- A `workflow_dispatch` run diffs against the previous commit of the dispatched branch, which may be no plugin change. Accepted: the pull request run is the gate.
- D1's comparison treats equal versions as equal roles. Before check 12, a plugin edit could land without a bump; every edit since #108 did bump (checked in git history), so the gap is theoretical.
- `claude plugin list --json`'s shape is observed on 2.1.296 only (`id`, `version`). A missing field becomes "couldn't compare", not a stop.

---

## Verification Contract

- **Item 1:** probe both role URLs at a pinned commit (200), a pre-plugin commit (404 → `main` fallback) and `main`, and with `gh` failing for another reason (an unreachable host via `GH_HOST`, so the pinned URL is kept); run the version comparison on the operator's machine (installed 0.9.0 vs pin); in the item 7 scratch session, the opening prompt start-team writes names the pinned worker URL. In a scratch `CLAUDE_CONFIG_DIR`, try the README's route from an installed copy newer than a pin and word the warning from what it shows. Commands and output in the PR body.
- **Item 3:** fixtures each seen failing once; a scratch clone run that fails on an unbumped plugin edit and passes after the bump; CI red on the first commit, green after the bump.
- **Item 4:** a scratch `HOME` with its own `.gitconfig` in each state (unset, `none`, a path to a canary-only file, an empty file, a path to nothing, a relative path): the command's word matches what `claude_leak_hook.py` does in the same `HOME` on a fixture `gh issue comment` command (note, pass, deny). The naive form (`git config --get`'s exit status) is shown misreading `none` as declared, so the case form is seen to be needed. Never the real config or list.
- **Item 7:** `~/scratch/rcproof` with the adoption line committed and no `lead.json`: a session started there with `--plugin-dir <worktree>/plugins/agent-team` runs start-team and stops at step 2's question; `claude agents --json` shows no lead started. Then with no adoption line: it goes past step 2 without asking (stopped at step 6's board question). Every session started is stopped and archived.
- Local: `check-docs`, `check-template-kit` (check 11 and check 12). After push: CI conclusions green on the head.

## Definition of Done

All of R1 to R5 proven as above; PR body opens with At a glance and holds each proof; CE review steps done; CI green on the head; `closingIssuesReferences` is `[]`.

## Assumptions

- No synchronous operator during planning: the scoping confirmation is replaced by sign-off on #110.
- The new adopter uses Claude Code with the plugin, so the plugin-side fixes reach them once 0.11.0 is installed.
- The adoption line links github.com; a line linking a mirror or a raw URL gets `main`'s role (D1).

## Appendix: plan review (ce-doc-review, round 1, non-interactive)

Reviewers: coherence, feasibility, scope-guardian, adversarial. The cross-model pass was skipped: the handoff doesn't authorize sending the plan to another provider.

- Applied: start-team puts the worker role URL in the opening prompt, since a lead loaded at an older pin names `main`'s (adversarial, coherence). Only an HTTP 404 means "no role at the pin"; other `gh` failures keep the pin and say so (feasibility, adversarial). The value-list command reports a git error, an empty or unreadable file as "broken", as the hook denies all three (adversarial). D5 lists running sessions only, without this one (feasibility). The version warning no longer prescribes an unproven downgrade; the build checks it (adversarial). Residual risk of unbumped pre-check-12 edits recorded (adversarial).
- Left to the operator: D6. Scope-guardian recommends dropping it; coherence showed it needs step 2's "yes" branch too. The plan now recommends not building it and says what it would take.
