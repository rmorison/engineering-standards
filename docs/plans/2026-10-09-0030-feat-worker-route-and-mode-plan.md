---
title: Starting Workers by Where They Land and Whether Their Hooks Fire - Plan
type: feat
date: 2026-10-09
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
origin: https://github.com/rmorison/engineering-standards/issues/112
---

# Starting Workers by Where They Land and Whether Their Hooks Fire - Plan

## Goal Capsule

- Objective: the operator sees every worker in their app, and a worker on their own machine runs without prompts once it has shown its hooks fire. A worker whose hooks don't fire stops before doing anything, and the lead restarts it in `default` and tells the operator.
- Means: a live **guardrail check** (a mode check and two canaries) that each worker on the operator's machine runs first (D1), a permission rule keyed on that check and on where the session landed rather than on the route (D2, D3), a preferred route for workers (D4), and a stated messaging channel per kind of session (D5).
- Authority: #112 is the spec. D1 to D6 are **PROPOSED** for the operator's sign-off on #112. The operator already chose the two canaries and the probe script (issue comment of 2026-10-08, "option 2"). Where this plan and a sign-off comment disagree, the sign-off wins.
- Execution profile: `process/agent-team-workflow.md` (§ 1, § 3, § 4, § 8 "Starting a team", § 9); `plugins/agent-team/` (the start-team skill's step 7, both roles, the plugin README, plugin.json 0.8.0 to 0.9.0). No change to the hooks, `QUICKSTART.md`, the root `README.md`, `templates/` or `pm-trial/`.
- Stop conditions: stop and comment on #112 if the operator's probe run (U6) gives a row other than the expected one; if a bridge worker can't be started at all; if a bridge child started with explicit `default` doesn't show `blocked` on its first write (D3.4's restart then needs the `claude --bg --permission-mode default` route only); or if a proof step needs a settings change.
- Finishes the work: `ce-work` on branch `112-worker-route-mode`, one PR that closes #112. This sprint's merge order is lane C, then lane B, then this PR (lane A). Lanes B and C are the two other open tickets: they edit the leak hook, the leak workflow, `QUICKSTART.md` step 3, `code/python-standards.md` and two sections of `process/repository-standards.md`, none of which this PR touches. This branch is rebased before its final checks. The operator merges.

---

## Product Contract

### Summary

Today a worker the operator can see in the app (started with the host's session tool) gets `default` and waits on every prompt. A worker that runs on its own (`claude --bg`) is hidden from the app. After this change, the lead prefers the host's session tool wherever it reaches the operator's machine. Each worker on the operator's machine checks its guardrails before anything else: two harmless canaries must be denied by the hooks themselves, and the mode its own context states must match its handoff. A worker above `default` keeps its mode only if both checks hold.

### Problem Frame

#112 gives three gaps: visibility (Route A sessions don't show in the app), mode (start-team's rule gives every Route B session `default`, on the assumption that Route B means a cloud session), and messaging (how the lead reaches workers is never stated). Research for this plan found three further facts the docs must reflect:

- The host's record of a session's mode is not the mode the session runs in. A session started on a bridge with no `permission_mode` runs under the machine's `defaultMode` (this worker: context says auto mode is active), but the host records no mode, treats it as `default` when checking a child request, and labels its messages `from-mode="prompting"`. So a lead started from the app can't pass `auto` to `create_session`, however it runs.
- A cloud session in `default` doesn't necessarily wait on anyone: the cloud environment's own allow rules let a Bash write through (`permission_decision: accept, source: config`).
- The policy hook never denies `git push --dry-run`, so the canary the issue suggested can't work.

### Requirements

- R1. The workflow says how the lead starts workers, which route it prefers, and the visibility trade-off, in generic terms (AC 1).
- R2. start-team's permission rule tells a session on the operator's machine from a cloud session, and sets the mode by the live canary check, not by the route (AC 2).
- R3. The worker role and the handoff template run the canary check first, and stop if it fails (AC 3).
- R4. The workflow and the lead role say which channel the lead uses for which session, what to do while a new worker's name lags its title, and how permission modes affect messages (AC 4).
- R5. Proven in a scratch project: a host-tool worker on the same machine passes and runs unattended; a session whose hooks aren't registered fails and stops; a cloud worker gets `default` (AC 5).
- R6. Nothing host-specific in the repository: no environment IDs, machine names or paths (AC 6).

### Acceptance Examples

- A lead on the operator's machine starts `ES-x` with `create_session` in the same machine's environment. `ES-x` appears in the app. Its context states auto mode, matching its handoff, and both canaries give "leak hook: denied" and "policy hook: denied". It pings the lead with the result and carries on without a prompt. The operator hears nothing.
- The same start on a machine whose hooks aren't registered: both canaries print `git version …`. `ES-x` comments "Guardrail check failed: leak canary, policy canary" with the two output lines, pings the lead and stops. The lead archives it, starts it again in `default`, and tells the operator that `ES-x`'s guardrails didn't fire.
- A cloud worker: started with `permission_mode: "default"`. Its messages can't reach the lead, which falls back to its scheduled GitHub check.

### Scope Boundaries

- No change to either hook (out of scope in #112). The canaries use the hooks as they are.
- App visibility for `claude --bg` sessions is a host feature (out of scope in #112).
- #110 (start-team residuals) is next, except its item 3, the version bump, which this PR does.

---

## Planning Contract

### Decisions (PROPOSED for the operator's sign-off)

**D1. The guardrail check.** Every worker on the operator's machine runs it first, whatever its mode. A cloud worker skips it (D2, D3.2). The check has two parts.

*The mode check.* The worker reads the permission mode its own context states (for example a notice that auto mode is active). It passes only when that mode is the handoff's mode, or when the handoff says `default` and the context states no other mode. A stated `bypassPermissions`, a mode other than the handoff's, or no stated mode under a handoff above `default` is a fail. This is what holds the ceiling of D3.1, since hooks fire in every mode and the canaries can't tell one mode from another.

*The canaries.* Run both, each as its own command, before judging either:

| Canary | Hook that denies it | Pass only on | If not denied |
|---|---|---|---|
| `git -c core.hooksPath=/dev/null --version` | leak hook (a `core.hooksPath` override) | "leak hook: denied" | prints git's version |
| `git -c agentpolicy.allowDefaultPush=true --version` | policy hook (setting the push opt-out) | "policy hook: denied" | prints git's version |

- Each is denied by exactly one hook and does nothing else (piped to each installed hook: denied by one, exit 0 from the other; both denied in this worker's own Bash tool).
- A pass needs the hook's own message. A git version, any other denial (an auto-mode classifier block, a permission refusal) or an error is a fail. Claude Code runs `PreToolUse` hooks before the permission decision, so a registered hook always answers first; if the classifier answers, the hook didn't.
- A pass shows the hook script is installed, registered in the settings this session loaded, and not switched off by `disableAllHooks` at any level. Piping JSON into the hook file proves only the file.
- The policy hook's message ends "… and stop." For these two canaries that is the expected pass, and the worker carries on. The worker role says so.

*Reporting.* The result is always reported, pass or fail. A pass goes in the worker's first ping to the lead (its stated mode, and the first line of each denial) and as one "Guardrails:" line in its plan comment, so the record is on GitHub without an extra comment. The operator still hears nothing. On a fail, the leak hook may not be scanning GitHub text, so the worker posts fixed wording: "Guardrail check failed: <mode check | leak canary | policy canary>", plus each canary's first output line and nothing else. The lead treats a worker above `default` that hasn't reported a pass within five minutes of connecting as a fail.
- **Dropped:** `git push --dry-run` to the default branch. The policy hook returns before checking any refspec when it sees `-n` or `--dry-run`, so it is never denied. A real push is denied, but it isn't harmless, and a clone with `agentpolicy.allowDefaultPush` set lets it through. The chosen policy canary is a write of that same opt-out key, which no role is granted and which the clone's own setting doesn't affect. `gh pr merge --help` is denied today too, but a later merge grant to a principal role would let it through, so it isn't used.

**D2. Where a session landed.** A session that can call the host's `get_session` with no ID reads `environment_kind`: `bridge` means the operator's own machine (Remote Control), and `anthropic_cloud` means the cloud. A session started with `claude --bg` is on the machine that started it. The lead reads the same field from `create_session`'s result. Where it landed decides the messaging (D5) and whether the mode can be above `default` (D3). It is not a substitute for the canary check, which alone shows the hooks fire.

**D3. The permission rule** (start-team step 7, the lead role and § 8):

1. **The ceiling:** the mode start-team decides today: `auto` or `acceptEdits` only when the starting session's context states that mode and the hooks passed step 4. Otherwise `default`. Never `bypassPermissions`. A worker never gets more than the lead's recorded mode.
2. **Cloud** (`anthropic_cloud`): always `default`, passed explicitly, as today. The docs add that a cloud environment's own allow rules may still let steps through without the operator: in this probe a Bash write ran under a rule from the environment's config.
3. **The operator's machine,** by either route:
   - `claude --bg`: pass the recorded mode with `--permission-mode`, as today.
   - The host's session tool: pass `default` explicitly when the recorded mode is `default`. When it is `auto` or `acceptEdits`, leave `permission_mode` out. The host refuses `auto` unless its record of the parent's mode is `auto`, and a parent started from the app or by another session is recorded without a mode (observed: "permission_mode 'auto' requires the parent session to be in auto mode (parent is "default")" from this worker, whose context says auto mode is active). Without the field, the session runs under the machine's own `defaultMode`.
4. **The live check decides.** Every worker on the operator's machine runs D1 first.
   - **Above `default`:** if any part fails, the worker stops before any other work, comments and pings the lead. The lead archives it, starts it again with `default`, and tells the operator: a blocker, in quiet mode's words.
   - **In `default`:** the restarted worker, or any worker started in `default`, runs D1 too. A canary fail is reported and the worker carries on, since the operator approves each of its steps. A mode-check fail (its context states a higher mode than `default`) means the explicit `default` didn't hold. The worker stops, and the lead restarts it with `claude --bg --permission-mode default`, or gives the handoff to the operator.
   - **Leaving the mode out** (D3.3) hands the choice to the machine's `defaultMode`. The mode check is what catches a `defaultMode` above the lead's recorded mode, or `bypassPermissions`.

The lead also checks the worker connects. The host shows a started session's `connection_status`. A bridge session can stay `PENDING` and disconnected: one probe here never connected in over 10 minutes. After five minutes the lead archives it and tries Route A, or gives the handoff to the operator.

**D4. The preferred route for workers** (§ 1 and the lead role): where the host's session tool reaches the operator's machine, the lead uses it, so the team shows up in the operator's app. Otherwise it uses `claude --bg`, which runs and messages the same but appears only in a terminal: watch with `claude agents` and `claude attach <id>`. A cloud environment comes last, and only with the operator's go-ahead, as for a cloud lead. The workflow names the trade-off in generic terms: app visibility comes from the host's session tool, not from the CLI.

**D5. Messaging channels** (§ 3 or § 7 and the lead role):

- **`SendMessage` by name** to every session ListAgents lists. That covers workers on the same machine by either route, and cloud sessions, which ListAgents lists with the kind `cloud` (a local-to-cloud message was delivered and acted on).
- **The host's session tool** (`send_message`) only for a session ListAgents doesn't list. Outside auto mode each call prompts the operator (reported by another project's lead; not reproducible from this auto-mode worker).
- **Cloud to local doesn't work.** A cloud session's ListAgents sees nothing, and its SendMessage reports "No agent named … is reachable". A cloud worker's pings never arrive, so the lead relies on its scheduled GitHub check (§ 3).
- **A name that lags its title.** A new session can be listed under a generated name for a while: this worker was titled ES-route at start but listed as `bridge-cse-…` for over ten minutes, and as ES-route within 30. Its ListAgents header names it ("This session is …"). The worker's first ping carries that name, and the lead sends to it until the title shows.
- **Messages and modes.** A session in a different permission mode can hold an incoming message for its operator's approval, and a Remote Control or cloud receiver reports nothing back (SendMessage's own documentation; every message carries its sender's mode as `from-mode`). The mode compared is the host's record, not the effective mode: this worker's messages carry `from-mode="prompting"`, like the lead's. The lead treats silence as unknown, never as agreement, and falls back to GitHub.

**D6. Where the text goes.** The workflow gets the generic rules: § 1 the starting route and its trade-off; § 3 Traffic the channels; § 4 the canary step in the template and its reason; § 8 "Starting a team" the mode sentence; § 9 the prerequisite wording. The roles and start-team carry the host-specific steps (`create_session`, `get_session`, `claude --bg`), as they do now. The canary commands appear once in the workflow (§ 4); the worker role and start-team link to them. A `copy-of` marker is added if check-template-kit's check 11 needs one.

### High-Level Technical Design

```text
lead (recorded mode M)
  |-- same machine reachable by host tool? --> create_session (M=default: "default"; else omit field)
  |-- else claude on PATH?                 --> claude --bg --permission-mode M
  |-- else cloud (operator's go-ahead)     --> create_session permission_mode "default"
  |-- else                                 --> handoff to operator
worker on the operator's machine, first step (any mode):
  mode check: context's stated mode == handoff mode (or default and none stated)?
  run canary 1 and canary 2, then judge: "leak hook: denied"? "policy hook: denied"?
  all yes -> report pass to lead (+ "Guardrails:" line in plan), carry on
  any no, mode above default -> fixed-text comment, ping lead, stop
  canary no, mode default    -> report, carry on (operator approves each step)
lead: failed check or no pass report in 5 min -> archive, restart in default, tell operator
lead: restarted worker's mode check fails -> claude --bg --permission-mode default, or operator
```

### Implementation Units

**U1. Workflow document** — `process/agent-team-workflow.md`.
- § 1 "Starting, stopping and naming": how the lead starts a worker, the preferred route (D4) and the visibility trade-off.
- § 3 Traffic: the channel per session (D5), name lag, and modes on messages.
- § 4: a rule bullet for the guardrail check with its reason, and the template's first section "Check your guardrails" (D1): the mode check, both canaries run before judging, the hook's "stop" being the expected pass, reporting, and fixed-text failure. The lead fills in the mode and where the worker lands. The section is left out only for a cloud worker.
- § 8 "Starting a team": replace "Background sessions get … only when both hooks are installed" with the D3 rule in one or two sentences.
- § 9: "Both hooks installed" adds "and seen to fire by the canary check".
- Test: `node scripts/check-docs.mjs` passes. Every acceptance criterion has a sentence it maps to (table in the PR body).

**U2. start-team** — `plugins/agent-team/skills/start-team/SKILL.md` step 7 and step 9.
- The rule becomes D3. The Route B paragraph keeps `default` for a cloud lead, and for a lead on the operator's machine reached by the host's session tool, applies D3.3 (leave the mode out when it is above `default`). Route A and C are unchanged, apart from the lead's opening prompt asking it to run the canary check first when its mode isn't `default`.
- Test: check-template-kit passes, check 11 included.

**U3. Worker role** — `plugins/agent-team/agents/worker.md`: a first step before reading anything else. Unless the handoff says you are a cloud worker, run § 4's guardrail check, in any mode, and act on the result by D3.4. Your first ping carries the result and the name ListAgents gives you.

**U4. Lead role** — `plugins/agent-team/agents/lead.md` "Starting a worker":
- the route order of D4, and per route the mode by D3;
- check `connection_status` and reachability;
- expect a pass report within five minutes;
- on a failed or missing check, archive the worker, restart it in `default` and tell the operator, with the `claude --bg` fallback of D3.4;
- the channels of D5.

**U5. Plugin README and version** — `plugins/agent-team/README.md` "How the lead is started" and its mode paragraph follow D3. `plugin.json` 0.8.0 to 0.9.0.

**U6. Proof** (after sign-off). Each result goes in the PR body with the Claude Code version.
1. **No hooks registered, or switched off: fails and stops.** The operator runs `probe-112.sh` (below) once from a terminal and posts its output on #112. The script uses scratch config dirs only, never the real `~/.claude`. Expected:

   | case | leak canary | policy canary | marker | meaning |
   |---|---|---|---|---|
   | hooked | hook-denied | hook-denied | yes | passes and carries on, in a clone with the push opt-out set |
   | unregistered | ran | ran | no | fails and stops |
   | disabled (user settings) | ran | ran | no | `disableAllHooks` is caught |
   | project-off (project settings) | ran | ran | no | `disableAllHooks` in project settings is caught |

   `marker` is the scratch file a probe session touches only after both canaries pass: yes means it carried on, no means it stopped. Any other row means a canary or the stop doesn't work. The hooked/unregistered pair is the fail-before-trust evidence for the check. The probe runs in `default` with exact allow rules, so it tests the canaries and the stop, not the mode check. The mode check is tested in step 2.
2. **A host-tool worker on the same machine: passes and runs unattended.**
   - (a) In the bridge environment, start a throwaway worker with `create_session`, no `permission_mode`, and the new worker role's first step as its handoff, giving `auto` as its mode. It must report its stated mode and both hook denials, then finish a scratch-only task without a prompt (`status_bucket` never `blocked`).
   - (b) Start a second one with `permission_mode: "default"` and a handoff saying `default`. Its first scratch write must show `blocked` (explicit `default` holds). If it doesn't, stop by the Goal Capsule.
   - If the classifier blocks this worker from starting either one, the operator starts it from the app with the given handoff, as the sign-off directs for blocked proofs, and the transcript is cited.
3. **A cloud worker gets `default`.** The run of 2026-10-09 already shows `permission_mode: default` and one-way messaging. It is repeated with the final worker role, the session is archived, and the result is recorded.

### Risks

- **The host's mode record may change.** If a later host version records the effective mode, D3.3's "leave the mode out" is no longer needed. The docs state the observed behaviour with the version, so a change is easy to spot.
- **Leaving the mode out hands the decision to the machine's `defaultMode`,** which could be higher than the lead's recorded mode, or `bypassPermissions`. The canaries can't catch that; D1's mode check does, by failing any stated mode other than the handoff's.
- **The mode check reads the session's own context,** the same signal start-team uses today. A mode that leaves no notice in context reads as "none stated", which fails closed above `default`.
- **The classifier blocked several research steps in this worker** (starting a probe with explicit `default` on the bridge, a probe prompt that ran the canaries). Proof steps it blocks go to the operator, never round it.
- **Whether explicit `default` holds on a bridge child isn't verified** (that probe was blocked). U6 step 2(b) tests it, and the Goal Capsule stops on a fail. Until then, D3.4's mode check keeps the restart path safe either way: a restarted worker whose context states a higher mode stops, and the lead uses `claude --bg --permission-mode default`.

---

## Verification Contract

- `node scripts/check-docs.mjs` and `node scripts/check-template-kit.mjs` pass locally (versions named) and in CI on the head.
- `probe-112.sh` output from the operator matches U6's table.
- `closingIssuesReferences` is exactly [112].
- No environment IDs, machine names or absolute paths in any changed file (grep in the PR body).

## Definition of Done

All of #112's acceptance criteria are mapped to text and proof in the PR body, CE reviews ran and their dispositions are recorded, CI conclusions are green on the rebased head, and the lead has been pinged.

---

## Appendix: research runs (2026-10-08 to 2026-10-09 UTC)

Local Claude Code 2.1.295 (CLI). The bridge sessions report `container_cc_version` 2.1.288; the cloud probe 2.1.295.

| Run | Result |
|---|---|
| Canary candidates piped to each installed hook | `git -c core.hooksPath=/dev/null --version`: leak 2, policy 0. `git -c agentpolicy.allowDefaultPush=true --version`: leak 0, policy 2. `gh pr merge --help`: leak 0, policy 2. `git push --dry-run origin HEAD:main`: leak 0, policy 0 |
| Both canaries in this worker's own Bash tool | "leak hook: denied: a core.hooksPath override …"; "policy hook: denied: setting agentpolicy.allowDefaultPush …" |
| `get_session` on this worker and the lead | `environment_kind: bridge`; the lead has `origin: desktop_app`; neither record has a `permission_mode` |
| `create_session` with `auto` from this worker | refused: "permission_mode 'auto' requires the parent session to be in auto mode (parent is "default")" |
| Cloud probe, `create_session` with `default` in the cloud environment | `permission_mode: default`, `environment_kind: anthropic_cloud`, no mode notice in context; its ListAgents is empty; its SendMessage to this worker: "No agent named … is reachable"; `touch` in /tmp ran, accepted by a rule from config. Archived |
| SendMessage from this worker to the cloud probe | delivered and acted on; it arrived as `from-mode="prompting"` |
| Bridge probe, `create_session` with no mode | stayed `PENDING`, disconnected, for over ten minutes |
| Bridge probe with explicit `default` | blocked by the auto-mode classifier before it was sent |
| Probes running the canaries in other sessions, and a session without hooks | blocked by the classifier; moved to the operator's script |
| ListAgents | this worker listed as `bridge-cse-…-03` about ten minutes after start, as ES-route about 30 minutes after; cloud sessions listed with kind `cloud` |

The operator's probe script is `docs/plans/2026-10-09-0030-probe-112.sh` on this branch. It is a proof tool: whether it stays in the PR is a review call; its output goes in the PR body.

## Appendix: plan review (ce-doc-review, round 1)

Reviewers: coherence, feasibility, adversarial, security-lens. The cross-model pass was skipped because no other-family CLI is installed. Every finding was accepted and applied:

| Finding | Reviewers | Disposition |
|---|---|---|
| The canaries show hooks fire, not the mode; leaving the mode out can exceed the ceiling or give `bypassPermissions` | security, adversarial, feasibility | Fixed: D1's mode check; Risks reworded |
| The check was skipped when the handoff said `default`, so a restarted worker could run unguarded | security, adversarial | Fixed: every worker on the operator's machine runs D1; D3.4 covers the `default` case |
| A silent pass looks the same as a skipped check | security | Fixed: the pass is always reported, and the lead treats a missing report as a fail |
| Explicit `default` on a bridge child was unproven, and its proof was missing from U6 | coherence, feasibility, security | Fixed: U6 2(b), plus a stop condition |
| Blocked proofs fell back to the lead, not the operator | feasibility | Fixed: they go to the operator, per the sign-off |
| A probe session might stop after the first canary fails | adversarial | Fixed: run both before judging (D1, probe prompt) |
| The hook's "… and stop" text could stop a passing worker | feasibility | Fixed: D1 says that is the expected pass (probe prompt too) |
| A failure comment posts while the leak hook may be off | security (residual) | Fixed: fixed wording plus each canary's first line |
| Scope wording: "each session" vs non-default; undefined lanes; the `marker` column; root vs plugin README | coherence | Fixed |
| Exact allow rules: a reworded command shows as `other:` | feasibility (residual) | Accepted: the prompt says "exactly as written", and a rerun is the cost |
