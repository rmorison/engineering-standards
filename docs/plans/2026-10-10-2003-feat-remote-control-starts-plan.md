---
title: Command-Line Starts That Appear in the Operator's App - Plan
type: feat
date: 2026-10-10
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
origin: https://github.com/rmorison/engineering-standards/issues/123
---

# Command-Line Starts That Appear in the Operator's App - Plan

## Goal Capsule

- Objective: every session the team starts from the command line, the lead by start-team's Route A and each worker the lead starts by its route 2, appears in the operator's app, titled by its team name, with its exact permission mode and no manual step.
- Means: add `--remote-control <name>` beside the existing `-n <name>` in each command-line start (D1, D2). Say what happens when Remote Control can't connect, from observed runs (D3). Update the text that says a command-line session shows only in a terminal (D4).
- Authority: #123, including its comment that widens it to every command-line worker start, is the spec. D1 to D5 are **PROPOSED** for the operator's sign-off on #123. Where this plan and a sign-off comment disagree, the sign-off wins.
- Execution profile: `plugins/agent-team/` (start-team's step 7 and step 9, `agents/lead.md`, the README, and `plugin.json` from 0.9.0 to 0.10.0); `process/agent-team-workflow.md` § 1. `agents/worker.md` only if a proof shows the worker needs a step. No change to the hooks, `QUICKSTART.md`, `templates/`, `pm-trial/`, or the two files under `docs/solutions/best-practices/` that lane B (#122) edits. #110's items stay out.
- Stop conditions: stop, comment on #123 and ping the lead if auto mode's classifier blocks any proof step; if a session started with `--remote-control` doesn't appear in the app; if the scratch project's sessions don't group without a GitHub remote; if the lead started with `--remote-control` has the host session tools (U4 step 2), since its worker route then changes and D5 needs the operator; or if any proof would need a change to the operator's settings or installed plugins.
- Finishes the work: `ce-work` on branch `123-remote-control-starts`, one PR that closes #123. The operator merges.

---

## Product Contract

### Summary

Today a session started with `claude --bg` runs and messages like any other but isn't connected to Remote Control, so it doesn't appear in the desktop or mobile app. The operator saw this on start-team's first real run in another project: the lead was missing, and later four sprint workers were missing too, because a lead started by Route A has no host session tool and so starts every worker from the command line. The lead proved on #123 that `--remote-control <name>` fixes it with no loss: the session appears in the project's group, titled from `-n`, with its mode honoured.

### Requirements

- R1. start-team's Route A starts the lead with `--remote-control <project>-lead`. In a scratch project, a lead started by start-team with `--agent agent-team:lead` and `--permission-mode auto` appears in the app's project group titled `<project>-lead` with no manual step, runs in auto, and passes its guardrail check (AC 1).
- R2. Every command-line worker start in `lead.md`, its route 2 and the restarts that use it, passes `-n <name> --remote-control <name>`. Proven with a worker that a Route A lead starts from the command line (AC 2 and the widening comment).
- R3. What happens when Remote Control can't connect is observed and written down: whether the session still starts, what it, `claude agents` and ListAgents show, and what start-team tells the operator (AC 3).
- R4. § 1, the plugin README and start-team's step 9 describe the new behaviour; `plugin.json` goes to 0.10.0 (AC 4).
- R5. Nothing host-specific in the repository: no session links, IDs or paths (AC 5).

### Acceptance Examples

- The operator runs start-team in a project whose folder is trusted. start-team's Route A starts `<project>-lead` with `--remote-control`. Within a minute it appears in the app under the project's group, titled `<project>-lead`. Its first message gives a passing guardrail check in auto mode.
- After the operator signs off a sprint, that lead starts `<PREFIX>-<role>` with `claude --bg … -n <PREFIX>-<role> --remote-control <PREFIX>-<role> …`. The worker appears in the app beside the lead.
- On a machine where Remote Control isn't available, the lead still starts (or doesn't; see D3, which the proof decides). start-team tells the operator that the lead may not appear in the app, and how to reach it from a terminal with `claude attach <id>`.

### Scope Boundaries

- The route order stays as it is. D5 asks the operator whether to change it, and if they want that, it becomes a follow-up ticket.
- No change to how a session is named, or to how the lead checks a worker connected, beyond the text that says a command-line session shows only in a terminal.
- #110 (start-team residuals) is not pulled in.

---

## Planning Contract

### Decisions (PROPOSED for the operator's sign-off)

**D1. The commands.** Each command-line start passes the name twice, `-n` first, then `--remote-control` with the same name, then the mode, with the prompt last:

```bash
# start-team, Route A (from the main checkout)
claude --bg --agent agent-team:lead -n <project>-lead --remote-control <project>-lead --permission-mode <mode> "$(cat "<board path>/opening-prompt.md")"

# lead.md, route 2, and every restart by it (from the main checkout)
claude --bg --agent agent-team:worker -n <PREFIX>-<role> --remote-control <PREFIX>-<role> --permission-mode <recorded mode> "$(cat "<handoff file>")"
```

- `-n` sets the title. `--remote-control <name>` alone left the title from the prompt (#123, probe `rc-probe-b`).
- `--remote-control` takes an optional value (`claude --help` on 2.1.296: `--remote-control [name]`). With no value, the next word is read as its name, so the text says the name is always given. The order above also never leaves `--remote-control` directly before the prompt.
- `--permission-mode` stays explicit, `default` included, as #112 settled.
- The restart in `lead.md` ("by route 2 with `--permission-mode default`") refers to route 2's command, so it picks up the flag with no second copy of the command.
- start-team's Route C prints the Route A command for the operator to run later, so it gets the flag too.
- The handoff template in § 4 gives no start command, and § 8 refers to § 1's routes, so neither changes. Verified by a search of the repository for `claude --bg`: the only start commands are in start-team's step 7 and `lead.md`'s route 2. The README's Route A line gives the command too, and is updated.

**D2. The title and the Remote Control name are the same name.** The app shows the `-n` title. The listed name in ListAgents can lag, as § 3 already says. Using one name for both leaves nothing new to explain.

**D3. When Remote Control can't connect.** The docs say an interactive session started with `--remote-control` keeps running, shows the failure in its status and adds the reason to the conversation (code.claude.com, Remote Control: "Authentication", "Troubleshooting"). They don't say what a background session does. The proof (U4) observes three cases and the text is written from what it shows:

| Case | How the proof makes it | Recorded |
|---|---|---|
| Turned off by settings | `--settings '{"disableRemoteControl": true}'` on the start command, for that one session | exit code and output of `claude --bg`; `claude agents --json`; the ListAgents row; `claude logs <id>`; whether the app shows it |
| Remote Control unavailable for the account or environment | `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` passed by `--settings '{"env": {…}}'` on the start command, since a background session doesn't inherit the caller's environment (U4, the plugin under test). The docs name it as making Remote Control unavailable | the same, plus `printenv` from the session; the case counts only if the variable shows there |

Signed out, and a sign-in that isn't eligible (API-key auth, or an organization that turns Remote Control off), aren't simulated: the operator's sign-in isn't touched, and a scratch HOME would refuse first for want of folder trust. No network isn't simulated either: the operator's other sessions share the machine. The docs say an interactive session keeps working and reconnects when the network returns; the text quotes that and says it isn't proven here.

What start-team tells the operator follows from the result:

- If the session still starts, start-team says the lead is up but may not appear in the app, and that `claude attach <id>`, then `/remote-control` in the lead's session, connects it. That is the manual step #123 began with, now the fallback only.
- If `claude --bg` refuses with `--remote-control` where it would start without, Route A's "Any failure means Route A didn't work" would send start-team to Route B. The plan then needs a decision: retry once without `--remote-control`, or go on to Route B. I'd recommend the retry, since a lead in a terminal beats a cloud lead, and would put it to the operator on #123 before building.

start-team can't see whether Remote Control connected unless the proof finds a field that shows it (`claude agents --json` today gives `id`, `cwd`, `kind`, `startedAt`, `sessionId`, `name`, `state`). If none, step 9 asks the operator to look for `<project>-lead` in the app, and gives the fallback above.

**D4. Where the text goes.**

- § 1, "Where a worker runs": a command-line session started with Remote Control appears in the app too. Where Remote Control isn't available, it shows only in a terminal (`claude agents`, `claude attach <id>`).
- start-team step 7: the Route A command (D1), and the D3 outcome. Step 7's sentence "The operator reaches a CLI lead with `claude attach <id>`" is kept as the terminal route. Step 9: the lead appears in the app as `<project>-lead`; if it doesn't, the fallback.
- `lead.md` route 2: the command (D1); "The worker shows only in a terminal" becomes "The worker appears in the operator's app, and in a terminal with `claude agents` and `claude attach <id>`".
- README "How the lead is started" and "How the lead starts workers": the same, and a "Proved on 2.1.296" line naming #123.
- `plugin.json`: 0.9.0 to 0.10.0, as the README requires for any change under `plugins/agent-team/`.

**D5. A question for the operator: the route order.** start-team puts the command line first for the lead, because it sets the mode exactly. `lead.md` puts the host session tool first for workers, because until now that was the only route that reached the app (§ 1). With this change the command line reaches the app too, and also sets the mode exactly, which the host tool can't do above `default`. The reason for the workers' order goes away. Changing it is a behaviour change beyond #123, so I'd file it as a follow-up for the lead to schedule, unless the operator wants it in this PR. One case can't wait: if a lead started with `--remote-control` turns out to have the host session tools (U4 step 2), `lead.md` sends it to route 1 for every worker, and route 2, the one this PR changes, would then run only as a fallback. The question then goes to the operator before building, with the lead's own unprompted route choice as evidence.

### Implementation Units

**U1. The commands** (`plugins/agent-team/skills/start-team/SKILL.md` step 7 Route A and Route C; `plugins/agent-team/agents/lead.md` route 2; the Route A command in `plugins/agent-team/README.md`). D1. Check: a search for `claude --bg` in `plugins/` and `process/` finds no start command without `--remote-control`.

**U2. The behaviour text** (`process/agent-team-workflow.md` § 1; start-team step 7 and step 9; `lead.md` route 2; the plugin README's prose). D3, D4. Written after U4 so it states what was observed.

**U3. Version** (`plugins/agent-team/.claude-plugin/plugin.json` 0.10.0).

**U4. Proofs** (no repository file; results in the PR body). Run after sign-off, on the branch with U1 committed, and before U2 is written, in this order:

1. **Setup.** The scratch project (below) and the branch's plugin (below). Record `claude plugin list` for `agent-team` before. Then one throwaway probe, `claude --bg … "Reply with the output of printenv CLAUDE_CODE_PLUGIN_DIRS, then stop."` in the scratch project, shows whether the plugin reaches a background session.
2. **Lead by start-team (R1).** A starter session in the scratch project, started with the branch's plugin and `--permission-mode auto`, runs `/agent-team:start-team` with the default board path. Its Route A starts `rcproof-lead` (the scratch project's name plus `-lead`). Record: the command start-team ran, `claude agents --json`, the ListAgents row, the lead's first message (mode and guardrail result), and whether the lead has the host session tools (`create_session`, `get_session`), since that decides which worker route it takes. If it has them, ask it which route it would take for a worker, without naming one, then stop, comment on #123 and ping the lead (D5). The operator confirms in one line, through the lead, that `rcproof-lead` is in the app under the project's group.
3. **Worker from the command line (R2).** The operator tells `rcproof-lead` directly, in the app: "Signed off by the operator for a proof of #123 only: start one worker named rcproof-w by your command-line route (route 2) in the `default` mode, with a handoff that says: run the guardrail check, ping the lead, then stop." Record the command the lead ran, and the operator confirms `rcproof-w` is in the app.
4. **Remote Control unavailable (R3).** The D3 table, each with `--permission-mode default` and the prompt "Reply with exactly: ok. Then stop."
5. **Clean-up.** Both restart paths (start-team's failed lead, `lead.md`'s worker) stop a session with `claude stop <id>` alone and start a new one under the same name. So for one session, run `claude stop <id>` first and record whether its app entry is archived before `claude rm`; if it isn't, U2 adds `claude rm <id>` to both restart paths, so the app never shows two entries with one name. Then `claude stop <id>` and `claude rm <id>` for every session started, and `archive_session` for any left in the app. Record `claude plugin list` for `agent-team` after, unchanged.

**The scratch project.** A new folder outside every repository, `~/scratch/rcproof`, with `git init` and one empty commit, and no remote. A background session refuses an untrusted folder, so the operator runs `claude` in it once and accepts the trust prompt (one step, asked through the lead). If the app doesn't group sessions from a folder with no remote, I stop and ask for a scratch GitHub repository rather than use a real one.

**The plugin under test.** A background session doesn't inherit the environment of the command that starts it: on this machine `claude --bg` hands the start to a long-running daemon, and a running lead's environment lacks variables its caller had (feasibility review). Flags do reach it. So:

- **The starter session** gets the branch's plugin with `--plugin-dir <worktree>/plugins/agent-team`. The docs say a plugin loaded this way replaces a same-named installed marketplace plugin for that session only, and changes no settings or install records ("Plugin loading reference", Name conflicts).
- **The lead and its worker** are started by commands this PR defines, so they can't carry an extra flag without changing what's under test. They get the plugin from the scratch project's own `.claude/settings.local.json`: first an `env` block setting `CLAUDE_CODE_PLUGIN_DIRS`, if the setup probe shows that reaches a background session; otherwise `"agent-team@engineering-standards": false` under `enabledPlugins` there, with the branch's plugin linked into the scratch project's `.claude/skills/`, so the project loads the branch copy as a skills-directory plugin. Both live inside the scratch folder only.
- **Checks that it took:** the probe's `printenv`, or `/plugin` in the lead's session showing the branch copy; and the lead's worker start in step 3 carries `--remote-control`, which only the branch's `lead.md` gives.
- Nothing touches `~/.claude/settings.json` or the installed plugins. If neither way loads the branch copy, I stop and ask.

### Risks

- **Flags move between CLI versions.** `--bg` and `--remote-control` on a background session are recent. The README names the version proved (2.1.296).
- **A refusal in D3 changes Route A's failure rule.** Handled as a stop for the operator's decision, not built ahead.
- **The auto-mode classifier.** It already blocked one research step here (below). If it blocks a proof step, I stop and ping, as on #112.
- **App grouping without a remote** is unproven; the stop condition covers it.
- **The likeliest real failure isn't simulated.** An adopter whose sign-in isn't eligible for Remote Control (API-key auth, an organization that turns it off) may see a different message from the two D3 cases. start-team's text says what the operator does whatever the message: look for the lead in the app, and attach if it isn't there.

## Verification Contract

- `node scripts/check-docs.mjs` and `node scripts/check-template-kit.mjs` (check 11 included) pass locally, with versions named, and CI conclusions are green on the head.
- U4's records in the PR body, each AC mapped to its record.
- `closingIssuesReferences` is exactly [123].
- No session links, IDs or absolute paths in any changed file (a grep in the PR body).

## Definition of Done

Every acceptance criterion of #123 and its widening comment is mapped to text and to a proof record in the PR body. Every session the proofs started is stopped and removed, and the PR says so. The CE reviews ran and their dispositions are recorded. CI is green on the head, and the lead has been pinged.

## Assumptions

- The handoff and #123 set the scope, so the planning skill's chat confirmation was skipped; the operator's sign-off on #123 takes its place.
- The proof lead is named after the scratch folder, so `rcproof-lead`, which doesn't collide with any session on the machine.

---

## Sign-off (2026-10-11)

Signed off by the operator on #123 with six changes, which the build follows where they differ from the decisions above: `--name` in place of `-n`; the combination of `--bg` and `--remote-control` is described as observed, not documented; start-team's step 9 lists the documented reasons Remote Control is unavailable; a refusal that names Remote Control is retried once without the flag, approved in advance; D5 is a follow-up; and `remoteControlAtStartup` is an optional mention only. For the plugin under test, the operator chose a test-only `--plugin-dir` in a scratch copy of the plugin, after the setup probe showed neither way in the plan loads it. The proof records are in the pull request.

## Appendix: research (2026-10-10 UTC, Claude Code 2.1.296)

| Step | Result |
|---|---|
| `claude --help` | `--remote-control [name]` (optional value); `-n, --name`; `--plugin-dir` (session only). `claude logs <id>` exists for a background session. |
| `claude agents --json --all` | Fields per session: `id`, `cwd`, `kind`, `startedAt`, `sessionId`, `name`, `state`. No Remote Control field seen on stopped sessions. |
| Repository search for `claude --bg` | Start commands only in start-team step 7 and `lead.md` route 2; the README gives the Route A command in prose. None in the workflow. |
| Remote Control docs | An interactive `--remote-control` session starts even without an eligible sign-in and shows a failure notice; `disableRemoteControl` turns it off; `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` makes it unavailable; on a network outage an interactive session keeps working and reconnects. Nothing on background sessions. |
| Feasibility review | `claude --bg` hands the start to a long-running `claude daemon run`; a running lead's environment is the daemon's, not its caller's, while its flags (`--agent`, `-n`, `--permission-mode`) reach it. |
| Plugin loading docs | `--plugin-dir`, `--plugin-url` and `CLAUDE_CODE_PLUGIN_DIRS` load a plugin for the session only and replace a same-named installed marketplace plugin. |
| Reading the CLI binary for Remote Control setting names | Denied by the auto-mode classifier ("Auto-Mode Bypass"). Not retried; the docs above were used instead. |

## Appendix: plan review (ce-doc-review, round 1)

Reviewers: coherence, feasibility, scope-guardian, adversarial. The cross-model pass was skipped because no peer CLI is installed.

| Finding | Reviewer | Disposition |
|---|---|---|
| A lead started with `--remote-control` may have the host session tools, so it would take route 1 and never run route 2 (P1) | adversarial; feasibility (residual) | Applied: a stop condition, a branch in U4 step 2, and D5 brought forward for that case |
| A background session doesn't inherit its caller's environment, so `CLAUDE_CODE_PLUGIN_DIRS` and D3 case 2 wouldn't take (P1) | feasibility | Applied: `--plugin-dir` for the starter; scratch-project settings for the lead and worker; a setup probe; D3 case 2 by `--settings` with a `printenv` check |
| A restart that runs `claude stop` alone may leave a second app entry with the same name (P2) | adversarial | Applied: U4 step 5 records it, and U2 adds `claude rm` if needed |
| U1's check would hit the README's Route A command (P2) | coherence | Applied: the README command is in U1 |
| The acceptance example said "won't appear", D3 says "may not" (P2) | coherence | Applied |
| U4 doesn't say U1 comes first (P2) | coherence | Applied |
| U2 named a `lead.md` section that doesn't change (P3) | coherence | Applied: removed |
| The worker proof didn't name the `default` mode AC 2 asks for (P3) | coherence | Applied |
| The signed-out scratch HOME case adds nothing (FYI) | scope-guardian | Applied: dropped, and listed with the cases not simulated |
| The likeliest real failure (an ineligible sign-in) isn't simulated (residual) | adversarial | Added to Risks |
