---
title: Agent Policy Hook - Plan
type: feat
date: 2026-10-05
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
origin: https://github.com/rmorison/engineering-standards/issues/76
---

# Agent Policy Hook - Plan

## Goal Capsule

- Objective: no agent session merges a pull request, pushes to a default branch, or changes repository settings, rulesets or branch protection. When it tries, the hook refuses with a message saying who does that instead.
- Means: a new user-scope Claude Code `PreToolUse` hook, `scripts/claude_policy_hook.py`, beside the leak hook. One table lists the denied actions (KTD2). One function decides (KTD3), and it is where a future marked role could be granted an action. A missing or unknown marker grants nothing.
- Authority: #76 and its two comments: the lead's input for the plan, and the maintainer's note on a future principal role. The decisions below were signed off on #76. Where this plan and the issue disagree, the sign-off comment wins.
- Execution profile: new `scripts/claude_policy_hook.py` and `scripts/test_claude_policy_hook.py`. The test step of `.github/workflows/leaks.yml` only. A new `## Guarding Repository Authority` section of `process/repository-standards.md` after § Leak Gate, plus one cross-link line in § Guarding Agent Sessions, added after #84 merges. No edits to `scripts/claude_leak_hook.py`, `scripts/test_claude_leak_hook.py`, the rest of § Guarding Agent Sessions, the PR templates, `process/git-branching-strategy.md`, or `pm-trial/`.
- Stop conditions: stop and comment on #76 if a fixture does not fail against the stub it is meant to fail against. Also stop if the import of the leak hook's parser (KTD4) needs a change to `claude_leak_hook.py`, or if Claude Code cannot deny an MCP tool call by exit 2.
- Finishes the work: `ce-work` on branch `76-worker-policy-hook`, one PR that closes #76. buzai-lead runs the adopter test on the open PR. It merges after #84; this branch rebases onto it first. The operator merges.

---

## Decisions (signed off on #76, 2026-10-06)

The operator signed these off on #76 (issuecomment from 2026-10-06T04:06Z), with the buzai lead's adopter input (issuecomment-6009078354) folded into D3. **Operator** here means the human in the loop: the person who signs off, merges in the GitHub web UI and owns repository settings. **Maintainer** keeps its general meaning of repository ownership.

**Assumption: a human is in the loop.** Every merge and settings change is made by the operator, outside any agent session. The hook's whole design rests on this.

### D1. Who the hook applies to: every agent session, with no role marker.

The operator merges in the web UI and owns settings and rulesets. No agent session needs to merge, push to a default branch, or write a setting: not a worker, not a lead, not the operator's own sessions. A user-scope hook that denies those actions in every session has no marker, so a marker can't go missing or be set wrong.

The cost: the operator's own agent sessions can't merge, edit settings or push to a default branch either. The operator does those in the web UI or in a terminal outside Claude Code, which the hook never sees. It has happened once: `agent-transcripts/2026-01-12-python-standards.md` shows a session asked to squash-merge PR #6 with `gh pr merge 6 --squash --delete-branch`. That session would now be refused, with a message saying the operator merges.

This changes #76's premise ("in worker sessions only"). The acceptance criterion "in a maintainer session they are allowed" now means the operator *outside an agent session*. The "missing or misconfigured marker" criterion has nothing to fail, because no marker exists. KTD3 keeps the shape a later grant needs.

The workers-only alternative was rejected. It used an explicit `CLAUDE_AGENT_ROLE` set when a worker is started, a `--whoami` self-check, and a missing marker meaning maintainer authority. A worker started without the marker could still merge until someone read its ping.

### D2. Per-agent GitHub identities: not now. Revisit under #49.

A separate account or GitHub App for workers would enforce this on GitHub's side. A ruleset could deny merges to that identity with no bypass, and the operator could approve worker pull requests, since they would no longer be the author. It is the stronger control, and the one to reach for once the agent-team model in #49 settles which roles exist. It doesn't replace the hook for now:

- **Tokens at rest.** Every machine that runs workers would hold a second credential, and each session would need to pick the right one. That runs against the no-secrets-at-rest standard, and a session that picks up the wrong token gets the operator's authority back without any sign.
- **Accounts.** GitHub allows one free machine account per person. A GitHub App needs installing, key handling and token minting for every session. Either is a project of its own, not a hook.
- **A hook still helps afterwards.** It refuses before the call is made and says why, which a server-side 403 doesn't. It also covers settings that live outside rulesets.

### D3. A push to a default branch: denied, with a per-clone opt-out only a person can set.

#76 names merges and settings writes. A `git push` to `main` is a merge by another route, and the ruleset bypass that lets the operator push lets every session push. The hook denies a push that reaches the remote's default branch by any route (R5). Each route has a fixture seen to fail first.

Some repositories have no pull-request flow: a notebook or personal repository that commits straight to its default branch, such as a private repository on the free plan, which can't have rulesets. For those, a person sets `git config --local agentpolicy.allowDefaultPush true` once per clone, in a terminal outside Claude Code. The hook then allows default-branch pushes from that clone. The hook denies agents writing that key, the same way the leak hook denies a `core.hooksPath` write (R5a). Without this escape, the likely response in such a repository is to uninstall the hook, which removes the merge protection too.

---

## Product Contract

### Summary

Add a hook that Claude Code runs before every Bash command and every MCP tool call. It denies `gh pr merge`, `gh api` writes to merge, ruleset, branch-protection and repository-settings endpoints, `gh` commands that change settings, matching GraphQL mutations, GitHub MCP tools that merge or change settings, and a push to a default branch. Each denial names the action and says who does it instead. Ship it with tests run in CI and an install section that adds it next to the leak hook.

### Problem Frame

Agent sessions build tickets and open pull requests, and the operator merges. Every session posts as the operator's account, so GitHub sees the operator, and a ruleset bypass that covers the operator covers every session. The rule lives only in each hand-over ("the operator merges; you never do"). Under the leak gate's threat model, the case to guard against is a mistake: an agent that "finishes the job" by merging, or loosens a setting to get a check to pass. buzai's next sprint runs about three workers in parallel, so the hand-over alone no longer carries that weight.

### Requirements

**What is denied (one table, KTD2)**

- R1. `gh pr merge`, with any flags, `--auto` and `--admin` included.
- R2. `gh api` calls that write (any method other than GET, or any field or `--input`, as the leak hook decides it) to:
  - `repos/{o}/{r}/pulls/{n}/merge` and `repos/{o}/{r}/merges`;
  - `repos/{o}/{r}` itself (PATCH or DELETE: repository settings, rename, delete), and `repos/{o}/{r}/transfer`;
  - `repos/{o}/{r}/rulesets…` and `orgs/{o}/rulesets…`;
  - `repos/{o}/{r}/branches/{b}/protection…`;
  - `repos/{o}/{r}/git/refs…`: moving a ref through the API can move the default branch;
  - settings subpaths: `collaborators`, `teams`, `hooks`, `keys`, `environments`, `pages`, `topics`, `actions/permissions`, `actions/secrets`, `actions/variables`, `vulnerability-alerts`, `automated-security-fixes`, `private-vulnerability-reporting`.

  The path is matched after an optional leading `/` and any `?query` are dropped, with `{o}`, `{r}`, `{n}` and `{b}` as any one segment, `:owner`/`{owner}` placeholders included.
- R3. `gh api graphql` whose query text, inline or from an `@file`, names the mutation `mergePullRequest`, `enablePullRequestAutoMerge`, `mergeBranch`, `updateRepository`, `updateRefs`, or any `create|update|deleteBranchProtectionRule` or `create|update|deleteRepositoryRuleset`. Names are matched case-insensitively, as words.
- R4. `gh repo edit|delete|rename|archive|unarchive`, `gh repo deploy-key add|delete`, `gh secret set|delete`, `gh variable set|delete`, `gh workflow enable|disable`, and `gh ruleset` with anything other than `list|view|check` (all `gh ruleset` verbs read today; the rule is there for any that write later).
- R5. A push that reaches the remote's default branch (D3), by any of these routes: a refspec naming it (`main`, `refs/heads/main`), a `<src>:<dst>` refspec whose destination is it (`HEAD:main`, `x:refs/heads/main`), either with a leading `+`, `--all`, `--mirror`, and a bare `git push` (or `git push <remote>`) while the current branch is the default or tracks it. The default branch is read locally from `refs/remotes/<remote>/HEAD`, falling back to `main` and `master` when that ref is not set. A push whose target the hook cannot work out (a refspec in a variable) is denied with that reason. Allowed when the clone's local config sets `agentpolicy.allowDefaultPush` to `true`.
- R5a. A `git config` write of `agentpolicy.allowDefaultPush`, and `git -c agentpolicy.allowDefaultPush=…`, are denied in every clone. A read (`--get`, `--list`) is allowed.
- R6. A GitHub MCP tool whose name ends in `merge_pull_request`, `update_repository`, `delete_repository`, or contains `branch_protection` or `ruleset` and isn't a read. Also `push_files`, `create_or_update_file` and `delete_file` on `main`, `master` or no branch. This applies to any `mcp__<server>__` prefix. No GitHub MCP server runs on the agent hosts today, so this is a name rule with fixtures, nothing more.

**What stays allowed**

- R7. Everything else, including everything a worker and a lead do today: `git push` of a non-default branch, with `--force-with-lease` too; `gh pr create|edit|comment|review|ready|close|reopen|checkout|view|diff|checks`; `gh issue` and `gh label` commands; `gh api` reads, and writes to comments, reactions, labels, review threads and issues; `gh ruleset list|view|check`; `gh repo view|clone|set-default`. The hook adds no permission approval of its own: an allowed command still goes through the session's normal permission prompts.

**Decision point and grants**

- R8. Every denial goes through one function, `decide(action, role)`. Today the grant table is empty and `role` is always `None`, so every action in the table is denied. A missing, empty or unknown role grants nothing (KTD3).

**Output and failure**

- R9. Each denial names the action (for example "merging pull request 12" or "a write to repository rulesets") and ends: "Agent sessions don't merge or change repository settings; the operator does that in the GitHub web UI. Say what you need in the issue or PR, and stop." It does not echo a body file's contents.
- R10. A command the hook cannot parse falls back to a text match on the denied forms, as the leak hook falls back for gate escapes. A crash, a missing `python3` or a missing script denies every call, through the `|| exit 2` install form.

**Documentation**

- R11. A new subsection gives what is denied and allowed, the install steps, and the residuals. One line in § Guarding Agent Sessions links to it, added after #84 merges.

### Acceptance Examples

- AE1. **Covers R1, R9.** When the command is `gh pr merge 12 --squash`, then it exits 2 and the message names merging pull request 12 and says the operator merges in the web UI. The same for `cd x && gh -R o/r pr merge 12`, and inside `$(...)` and `sh -c`.
- AE2. **Covers R2, R7.** When the command is `gh api -X PUT repos/o/r/pulls/12/merge`, then it is denied. When it is `gh api repos/o/r/pulls/12/merge` (a GET), then it is allowed. When it is `gh api -X POST repos/o/r/issues/12/comments -f body=hi`, then it is allowed.
- AE3. **Covers R3.** When `gh api graphql -F query=@q.graphql` and `q.graphql` holds `mutation { mergePullRequest(...) }`, then it is denied. When the file holds a query that only reads, then it is allowed.
- AE4. **Covers R5.** In a scratch repo whose `refs/remotes/origin/HEAD` points at `trunk`: `git push origin trunk`, `HEAD:trunk`, `+HEAD:refs/heads/trunk`, `--all`, `--mirror`, and a bare `git push` with `trunk` checked out, or with a branch that tracks `origin/trunk`, are each denied. `git push -u origin 76-x` and `git push origin trunk:76-x` are allowed.
- AE4a. **Covers R5, R5a.** With `git config --local agentpolicy.allowDefaultPush true` set by the test harness, `git push origin trunk` is allowed. `git config agentpolicy.allowDefaultPush true` and `git config --local agentpolicy.allowdefaultpush false` in a hook input are denied; `git config --get agentpolicy.allowDefaultPush` is allowed.
- AE5. **Covers R6.** A hook input with `tool_name` `mcp__github__merge_pull_request` is denied. One with `mcp__github__get_pull_request` is allowed.
- AE6. **Covers R8.** With `CLAUDE_AGENT_ROLE=principal` in the hook's environment, `gh pr merge 12` is still denied, because the grant table is empty. A test pins that a role that is not in the table grants nothing.

### Scope Boundaries

- Outbound text and gate escapes: the leak hook (#74, #84).
- Actions taken outside Claude Code: the web UI, a person's own terminal, and CI. The Claude Action runs without user-scope hooks.
- Other GitHub clients such as `curl`, commands run through `xargs` or `find -exec`, a refspec built at run time by another command, and the `-c`/`GIT_CONFIG_*` routes to a different push target. These are documented residuals, pinned by fixtures as still allowed, as the leak hook does.
- A clone whose project settings set `"disableAllHooks": true`, which also turns off the leak hook. This is documented, not solved.
- Per-agent identities (D2), and building any role or grant (KTD3).

---

## Planning Contract

### Key Technical Decisions

- **KTD1. Its own script and its own settings entry.** `claude_policy_hook.py` sits beside `claude_leak_hook.py` and is installed the same way. It is a second command in the same `PreToolUse` `Bash` matcher entry, plus a second matcher entry, `mcp__.*`, for R6. Claude Code runs every matching hook, and any exit 2 blocks the call, so the two hooks compose without knowing about each other. Keeping them apart lets either change without the other's tests, and keeps ES-hookfix's file untouched this sprint.
- **KTD2. One table of denied actions.** A single module-level `DENIED` list holds each action's name, a matcher, and its message noun. R1–R6 are rows in it. Adding or removing an action is a one-row change, and the doc's list is checked against it by a test that reads both.
- **KTD3. One decision point; a grant can only allow.** `decide(action, role)` returns deny unless `action.name in GRANTS.get(role, ())`. `GRANTS` is `{}`. `role` comes from `os.environ.get("CLAUDE_AGENT_ROLE")` and nowhere else. **How a principal grant would slot in later (not built):** add `"principal": {"merge"}` to `GRANTS`, and have whoever starts a principal session set `CLAUDE_AGENT_ROLE=principal` in that process's environment. Nothing else changes: no new branch, no new parse. A missing marker, an empty one, a typo, or a role not in `GRANTS` falls through to deny, so the only failure a marker can cause is a refusal, which is loud. The rejected workers-only model would have lived at the same point, which is why it stays the single place to change.
- **KTD4. Reuse the leak hook's parser by import, not by copy.** The command parser (`parse`, heredocs, `$(...)`, `sh -c`, wrappers, `cd` tracking) took most of #74's review rounds. A copy would drift. The policy hook does `from claude_leak_hook import parse, gh_outbound, Deny` from its own directory. Installed, both files sit in `~/.claude/hooks/`, and a missing leak hook makes the import fail, which `|| exit 2` turns into deny-all: loud, not silent. The cost is a coupling to the leak hook's internal names. Its own tests in CI catch a rename on the same pull request that makes it. A shared module, `claude_hook_shell.py`, is the clean end state. It needs an edit to the leak hook, so it is a follow-up after #84. The install section says both scripts are required, and that a missing leak hook makes every call deny.
- **KTD5. Deny by exit 2, with no permission decision.** This is the same as the leak hook, and for the same reason. `docs/solutions/best-practices/a-guard-hook-fails-open-unless-every-path-exits-2.md` applies as it stands: every path ends in exit 2 or exit 0, and a test plants a crash and checks for exit 2.
- **KTD6. Read the default branch locally.** R5 runs `git symbolic-ref refs/remotes/<remote>/HEAD` in the command's working directory, with no network call. When that ref isn't set, it falls back to `main` and `master`. This is in the residuals: a repository whose default is `trunk` and whose clone has no `origin/HEAD` is not covered.

### High-Level Technical Design

```
stdin JSON ─┬─ tool_name mcp__* ──► MCP rule (R6) ─────────────┐
            └─ tool_name Bash ─► parse(command, cwd)  (KTD4)   │
                                  for each simple command:     ▼
                                  match DENIED (KTD2) ──► decide(action, role) (KTD3)
                                                               │ deny → stderr, exit 2
                                                               └ allow → exit 0
```

### Assumptions

- The `PreToolUse` hook input for an MCP tool carries `tool_name` as `mcp__<server>__<tool>`, and exit 2 blocks it, as it does for Bash. U1 checks this against the hooks docs before writing R6. If it fails, R6 moves to residuals and the issue gets a comment.
- ES-hookfix (#84) keeps `parse` and `gh_outbound` under those names. If it renames them, this branch rebases and follows.

### Risks

- **A false deny that blocks normal work.** The R2 path rules are the most likely source. Mitigation: R7's allowed list is a fixture table, and buzai-lead's adopter test runs a full worker day against the PR before merge.
- **D1 refuses the operator in their own sessions.** Mitigation: the message says what to do, and the install section says how to pause the hook for a session: remove the entry, or run the command outside Claude Code.

---

## Implementation Units

### U1. The hook script

- `scripts/claude_policy_hook.py`: docstring in the leak hook's form, `DENIED` (KTD2), `GRANTS` and `decide` (KTD3), Bash path via the imported parser (KTD4), MCP path (R6), default-branch lookup (KTD6), fallback text match (R10), the opt-out read and the R5a key guard, and `--whoami`, which prints the role from `CLAUDE_AGENT_ROLE` (or none) and the actions it is granted (none today).

### U2. The test harness

- `scripts/test_claude_policy_hook.py`, in the leak hook test's style, standard library only, scratch `HOME` and scratch repos under a temp dir. No canary values are needed (nothing here reads the value list), but no fixture holds a real value either.
- Each fixture is first run against a stub that allows everything, and seen to fail, before it runs against the real hook. The PR body carries both runs' commands and output.
- Tables: every `DENIED` row, denied in each spelling AE1–AE5 name; every R7 form, allowed; AE6's role cases; residuals pinned as allowed; a planted crash denies; the doc's denied list matches `DENIED`.

### U3. CI wiring

- Add `python3 scripts/test_claude_policy_hook.py` to the test step of `.github/workflows/leaks.yml` and nothing else. Rebase over #84 if it touches the same step.

### U4. Documentation

- `## Guarding Repository Authority` in `process/repository-standards.md`, after § Leak Gate and before § Going Public. It is its own section, not a Leak Gate subsection, because it guards authority, not leaks, and § What the Gate Cannot See must keep following the leak hook. It holds: why the hook exists (one paragraph), denied and allowed lists, D1's outcome in a sentence, the install (copy command, plus the settings JSON showing both hooks in one `Bash` entry and the `mcp__.*` entry), and the residuals.
- After #84 merges, one line at the end of § Guarding Agent Sessions: "To keep agent sessions from merging or changing settings, see [Guarding Repository Authority](#guarding-repository-authority)."

---

## Verification Contract

- `python3 scripts/test_claude_policy_hook.py` passes, and each fixture was seen to fail against the allow-all stub.
- `python3 scripts/test_claude_leak_hook.py` still passes, unchanged.
- `node scripts/check-docs.mjs` passes after `npm ci` in `scripts/`.
- The install copy and settings were run against a scratch `HOME`: `gh pr merge 1` was denied, `gh pr comment 1 --body-file f` was allowed, and the leak hook still denied `git commit -n` alongside it. With the policy script missing, every call was denied.
- CI conclusions are green on the PR head.
- buzai-lead's adopter test result is on the PR.

## Definition of Done

- D1–D3 and KTD4 signed off by the operator on #76 (done).
- U1–U4 merged in one PR that closes #76. The operator merges.
- A follow-up issue filed for the shared parser module (KTD4), and one for scanning GitHub MCP writes if it isn't already tracked.
