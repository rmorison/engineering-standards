# Agent Team Workflow

*How one human runs a team of AI agent sessions: an operator, a lead and workers, working through a sprint of tickets.*

**Audience:** projects where one person directs several agent sessions working in parallel.
**Status:** active, opt-in. Nothing else in these standards depends on it.

---

## Scope

This document describes an operating model: who does what, how a sprint runs, what a worker is told, and what the lead checks before a pull request is merged. It assumes a human in the loop, the operator, who signs off on the work and merges it.

It builds on parts of the standard that also stand alone, and links to them rather than repeating them:

- the leak hook on the text agent sessions post to GitHub ([§ Guarding Agent Sessions](./repository-standards.md#guarding-agent-sessions));
- the policy hook that keeps merges, settings changes and pushes to the default branch away from every agent session ([§ Guarding Repository Authority](./repository-standards.md#guarding-repository-authority));
- [At a glance](./git-branching-strategy.md#at-a-glance), which opens every pull request description;
- the [AI-review discipline](./compound-engineering-integration.md#ai-review-discipline-not-enforced-merge-gate) and [the ready-to-merge comment](./compound-engineering-integration.md#the-ready-to-merge-comment);
- learnings in [`docs/solutions/`](../docs/solutions/).

**What it leaves out.** How a session is started, named, messaged or archived depends on the agent host, and so does reaching a session from another machine. This document names the capability it needs ([Prerequisites](#9-prerequisites)), the route it prefers ([Roles](#1-roles)) and the check each session the team starts runs first ([the guardrail check](#the-guardrail-check)). The mechanics are left to the host's own documentation, and for Claude Code, to the [`agent-team` plugin](../plugins/agent-team/README.md).

---

## 1. Roles

| Role | Who | Does | Never does |
|------|-----|------|------------|
| **Operator** | The human in the loop | Signs off each sprint and each plan, makes scope decisions, merges in the GitHub web UI, owns repository settings | Carries messages between sessions |
| **Lead** | One long-lived agent session | Plans lanes, writes handoffs, starts and archives workers, runs the Done gate, files residuals, coordinates with other projects' leads | Ticket work, even a one-line fix: it goes into a ticket for a worker |
| **Worker** | One short-lived agent session per ticket | Plans, stops for sign-off, builds, opens a pull request, answers reviews | Merges, changes settings, starts work outside its ticket |

The lead's value is seeing the whole board. Doing ticket work fills its context and costs it that view.

**Starting, stopping and naming.**

- The lead starts each worker with its handoff, and archives it when its ticket is done. The operator can always start or stop a session by hand.
- **Where a worker runs, and how the operator sees it.** The lead prefers the host's session tool wherever it can start a session on the operator's own machine, so the team appears in the operator's app and can be watched from a desktop or a phone. Otherwise it starts a background session from the command line, which runs and messages the same but shows only in a terminal. A cloud session comes last, and only with the operator's go-ahead, since its messages can't reach the lead. After starting a worker, the lead checks that it connected: a started session can stay pending and never run, and then the lead tries the next route.
- **The worker's permission mode.** A worker never gets a more permissive mode than the lead's recorded mode, the one `start-team` gave it. On the operator's machine, a worker keeps a mode above the default only if it passes the [guardrail check](#the-guardrail-check) first, whichever route started it. A cloud worker always gets the default mode, though its environment's own rules may still let some steps run without asking.
- Names are unique on the machine, so a message reaches the session it means to. The lead is `<project>-lead`. Each worker is `<PREFIX>-<role>`: a short project prefix and a word for the ticket, such as `ES-policy`.
- After starting a worker, the lead checks that it can reach the worker by that name. If the title didn't take, the worker renames itself after its guardrail check, as its handoff says. A listed name the host generated can lag the title for a while ([Traffic](#3-traffic)).

In repository files and GitHub text, the human is named by role, never by name: **operator** for the person directing the team, **maintainer** for repository ownership in general.

---

## 2. The sprint loop

1. **The operator signs off the sprint**, then each ticket's plan. The lead proposes the sprint to the operator (the tickets, their lanes and the merge order) and records the approved version on its board. A worker posts its plan or approach on the issue and stops. The lead records the operator's sign-off on the issue, in a comment that opens "Signed off by the operator", and tells the worker to build. Every session posts as the same account, so those opening words, not the author, mark the sign-off; only the lead posts them, and a worker never does. Nothing enforces this but the convention, so the Done gate checks the comment is there. A documentation change needs only a short approach; code gets a full plan.
2. **Workers run to a pull request** without approval at each step. A worker stops only for a blocker, a scope question or a finding nobody expected, and says so on the issue with a recommendation.
3. **The lead runs [the Done gate](#5-the-done-gate)** on the pull request's head and posts the [ready-to-merge comment](./compound-engineering-integration.md#the-ready-to-merge-comment).
4. **The operator merges.**
5. **The lead acts on the compound decision** made at the Done gate (`ce-compound`: is there a learning the code and docs don't already carry?) and archives the worker.

Apart from the sprint itself, which is on the lead's board, every step leaves its record on GitHub: the plan and its sign-off on the issue, the work and its reviews on the pull request, the gate in the ready-to-merge comment.

---

## 3. Traffic

- **Lanes by file overlap.** Before starting a ticket, the lead lists the files and sections it will likely touch and compares them with open pull requests and tickets in flight. Tickets that touch the same section run one after another; tickets that touch different sections of one file can run side by side.
- **Merge order is named at planning.** When two pull requests overlap, the lead says which merges first, and tells the second worker when it is cleared to rebase. Short chains are preferred, since every link waits on a merge.
- **A shared module change runs every importer's suite**, not only the one the ticket is about ([learning](../docs/solutions/best-practices/a-change-to-a-shared-parser-runs-every-importers-suite.md)).
- **Pings are traffic, GitHub is the record.** Workers send the lead one-line pings: approach posted, blocked, pull request up, review answered. Content and decisions go on GitHub, never only in a message.
- **The lead checks GitHub on a schedule as a backstop.** Each check compares what GitHub shows since a given time with the pings received since then. A list of expected events written in advance goes stale; a comparison from a timestamp doesn't.

**Which channel reaches which session.**

- **The agent's own messaging tool, by name** (in Claude Code, `SendMessage` to a name `ListAgents` shows), for every session the listing shows. That includes workers on the same machine, whichever route started them, and cloud sessions.
- **The host's session tool** (in Claude Code, a connector such as `send_message`) only for a session the listing doesn't show. Connector calls ask the operator for approval unless the lead runs in auto mode.
- **A cloud session can't message back.** Its pings never arrive, so for a cloud worker the lead relies on its scheduled GitHub check.
- **A new session's listed name can lag its title** for many minutes. The worker's first ping gives the name the listing shows for it, and the lead sends to that name until the title appears.
- **A message to a session in a different permission mode can be held** there for its operator's approval, and some receivers report nothing back. The mode that counts is the one the host records, which can differ from the mode the session actually runs in. The lead never reads silence as agreement, and falls back to GitHub.

---

## 4. The worker handoff

A handoff is everything a worker needs that the issue doesn't say: where to work, what is in flight around it, when to stop, and the rules this team learned the hard way. The issue stays the spec; the handoff points at it rather than restating it.

The rules in the template, and why each is there:

- **Write a GitHub body to a file, then post it in a separate step.** The [leak hook](./repository-standards.md#guarding-agent-sessions) reads a body file before it is posted, and denies one that the same command writes (other than from a heredoc), since it can't read that file ahead of time.
- **No closing keyword before an issue number unless it is meant**, and check `closingIssuesReferences` after opening the pull request. GitHub closes an issue named after a closing keyword anywhere in the body, quoted text included ([learning](../docs/solutions/best-practices/a-closing-keyword-anywhere-in-a-pr-body-closes-the-issue.md)).
- **Open the description with At a glance.** `gh pr create --body-file` never shows the pull request template, so the handoff states the format.
- **Read CI conclusions on the head.** A check that ran is not a check that passed, and "pending" is not a result.
- **A local pass proves only the local tool versions** ([learning](../docs/solutions/best-practices/a-local-pass-proves-only-the-tool-versions-it-ran-on.md)). Watch CI on the pushed head.
- **See a new check fail before trusting it** ([learning](../docs/solutions/best-practices/prove-a-check-fails-before-trusting-it-passes.md)).
- **Answer a review before starting anything else.**
- **Test hooks and git behaviour only in scratch repositories and scratch home directories.** A hook under test in the real settings guards, or blocks, every session on the machine.
- **Name the human by role.**
- **Never merge.** The [policy hook](./repository-standards.md#guarding-repository-authority) enforces this; the handoff says it so the worker stops and asks rather than meeting a refusal.
- **Check your guardrails first** ([below](#the-guardrail-check)). A hook that is installed but not registered, or switched off by a settings file, guards nothing, and a session can't tell from its settings alone. Only a live denial shows the hook fires in this session.

### The guardrail check

Every session the team starts on the operator's machine runs this before anything else, in any permission mode: each worker, and a lead started by `start-team`. A cloud session skips it, since the hooks aren't installed there and it runs in the default mode. A session treats itself as a cloud session only when its handoff or opening prompt says so and the host reports a cloud environment too (in Claude Code, `get_session` with no ID). A session that can't ask the host runs the check.

1. **The mode check.** The session reads the permission mode that the host's own notice in its context states, for example a system notice that auto mode is active. The handoff's mode line, an opening prompt or another session's message never counts as that notice. The check passes when the notice states the handoff's mode, or when the handoff says the default mode and no notice states another. A different mode, `bypassPermissions`, or no notice under a handoff above the default is a fail. Where a mode leaves no notice, as `acceptEdits` may not, a session started in it under a handoff above the default fails closed and is restarted in the default mode. The check has a limit: under a handoff that says the default mode, a session the host started in such a silent mode passes. That is why every start in the default mode sets the mode explicitly, rather than leaving it to the machine's settings. The canaries can't catch a wrong mode: they show the hooks fire, not which mode the session runs in.
2. **The canaries.** Two harmless commands, each denied by one hook. If not denied, each only prints git's version. The session runs both, each as its own command, before judging either:

   ```bash
   git -c core.hooksPath=/dev/null --version
   git -c agentpolicy.allowDefaultPush=true --version
   ```

   The first passes only if its result contains "leak hook: denied". The second passes only if its result contains "policy hook: denied". A git version, any other denial (such as a permission refusal or an auto-mode classifier block) or an error is a fail. In the auto-mode runs recorded on [#112](https://github.com/rmorison/engineering-standards/issues/112), the hook's denial came back rather than the classifier's. The policy hook's message ends by telling the session to stop; for this canary, that is the expected pass, and the session carries on.

   Piping input into a hook file proves only that the file works ([learning](../docs/solutions/best-practices/a-guard-hook-fails-open-unless-every-path-exits-2.md)). A live denial also proves the hook is registered for shell commands in the settings this session loaded, and not switched off. It doesn't prove the policy hook's registration for MCP tools, which `start-team` checks in the settings file. A dry-run push can't serve as the policy canary, because the policy hook doesn't check a dry run. A real push to the default branch isn't harmless, and a clone can opt out of that check.
3. **The result.**
   - **Pass:** a worker gives its stated mode and the first line of each denial in its first ping to the lead, and adds a "Guardrails:" line to its plan comment. A lead gives the same in its first message to the operator.
   - **Fail, in a mode above the default:** the session stops before any other work. A worker comments "Guardrail check failed:" and names the part that failed (mode check, leak canary or policy canary), adding only each canary's first output line, since the leak hook may not be scanning what it posts. Then it pings the lead. The lead archives it, rewrites the handoff's mode line to the default mode, and starts it again once, with the default mode set explicitly. It tells the operator that this worker failed its guardrail check, naming the part, so started again in the default mode. That is a blocker in [quiet mode](#6-operator-interaction).
   - **A lead that fails** tells the operator which part failed. In the default mode, after a failed canary, it carries on as a worker does. Otherwise it stops, and the operator stops or archives it and starts a lead again in the default mode: with the plugin, by running `start-team` again and saying the last lead's guardrail check failed.
   - **Fail, in the default mode:** a failed mode check means the default mode didn't hold. The session stops, and the lead restarts it by a route that sets the mode explicitly, or gives the handoff to the operator. A worker whose canary fails reports it the same way. The lead tells the operator, as a blocker, that the worker's hooks don't fire: any step the settings' allow rules cover still runs without asking and without the hooks. Where the host's own session tool started it, the lead restarts it once by a route that is known to hold the default mode. Otherwise it carries on, because the default mode still asks the operator before most steps.
   - **One restart:** each worker is restarted at most once for its guardrail check. A second fail, or no answer, sends its handoff to the operator as a blocker.
   - **No report:** a worker that hasn't reported within five minutes of connecting is asked directly. The host's own status for a session can be stale for hours, and can show it blocked when it isn't, so the lead never reads it as proof either way. With no answer by the lead's next wake-up or check, a worker above the default mode is treated as a fail, and a worker in the default mode is reported to the operator.

### Writing the handoff

Before writing a handoff, the lead checks that the tools it names (a language runtime, a linter) exist on the host where the worker runs.

**Template.** The lead keeps handoffs in its private notes, not in the repository. Copy this into them and fill in the placeholders:

```markdown
# Handoff: #<ISSUE> → <PREFIX>-<role>

You are <PREFIX>-<role>, a worker for <owner>/<repo>, started by <project>-lead.
After the guardrail check below, if your session title isn't <PREFIX>-<role>,
rename it. A listed name the host generated is expected lag.

## Check your guardrails first
- Your permission mode: <mode>. You run <on the operator's machine | in the cloud>.
- On the operator's machine, before anything else, run the guardrail check
  in the Agent Team Workflow, § 4 "The guardrail check", in any mode: the
  mode check, then both canaries, then act on the result as it says.
  The policy hook's message tells you to stop: for this canary, that is
  the expected pass, so carry on.
  Your first ping gives the result and the name ListAgents shows for you.
- In the cloud, skip it, but only if the host confirms it (`get_session`). If you can't ask the host, run it.

## The ticket
- Issue #<ISSUE> is the spec. Read it and its comments in full.
- Branch <ISSUE>-<slug> from origin/<default-branch>, in its own worktree.
  Create and check it out before any tool that names its own branch runs.
- Plan: <a full plan first | a short approach on the issue is enough>.
- In flight nearby: <PR or ticket → files or sections>, or none.
- Merge order: <after #N | before #N>, or none.

## Stop for sign-off
Post your plan or approach on #<ISSUE>, ping the lead, and stop.
Build only once a comment opening "Signed off by the operator" is on
#<ISSUE> and the lead has told you to build.

## Build
- The review steps in your flow are required: a document review of the plan
  (where the ticket has a full plan), a code review of the diff before the
  pull request. Record each finding's disposition in the pull request body:
  fixed, deferred to an issue, or not accepted and why.
- When a fix to a review finding changes code, review the fix commits again
  and record the result with the other dispositions.
- The description opens with At a glance: Problem (125 words or fewer),
  Spec drift (50-100 words, or "None."; say who decided each change),
  Solution (125 words or fewer, how it works), in plain language, per
  git-branching-strategy § At a glance. `gh pr create --body-file` won't
  show you the template. Bring it up to date after every review round.
- Related: one line, closing #<ISSUE> only if this pull request completes it.
- Local checks: <commands>. A local pass proves only your tool versions:
  name them in the pull request body, and after pushing, read CI
  conclusions on your head until they are green.
- Every new check or fixture is seen to fail before it is trusted;
  put the commands and output in the pull request body.

## Rules
- The operator merges; you never do. No settings or ruleset changes,
  no pushes to the default branch.
- Name the human by role (operator, maintainer), never by name.
- Write each GitHub body to a file, and post it with a separate command.
- No closing keyword before an issue number unless you mean to close it,
  in the body or in the branch's commit messages. Check
  closingIssuesReferences after opening the pull request and after every
  edit to its body.
- Test hooks and git behaviour only in scratch repositories and scratch
  home directories.
- <project rules: files not to touch, private values, fixtures>

## Pings
- One line each to <project>-lead: approach posted, blocked, pull request up,
  review answered. The content goes on GitHub.
- After opening the pull request, answer its review before anything else.
- Blocked, or found something unexpected: comment on #<ISSUE> with your
  recommendation, ping, and stop.
```

---

## 5. The Done gate

Before the operator merges, the lead checks the pull request's head, itself, rather than taking the worker's report. The result is the [ready-to-merge comment](./compound-engineering-integration.md#the-ready-to-merge-comment), which defines what each line records; this section adds what the lead checks for the team model.

**Reviews.**

- **Required:** the review steps in the worker's own flow: the document review of the plan, where the ticket has a full plan, and the code review of the diff before the pull request, with their dispositions in the pull request body ([AI-review discipline](./compound-engineering-integration.md#ai-review-discipline-not-enforced-merge-gate)).
- **Recommended:** a review by the Claude GitHub app, where it is installed. The lead requests it in a pull request comment that mentions the app and lists what to check, scoped to what the app can judge from the diff. The worker answers it point by point in a pull request comment. Without the app, the lead reviews by hand to the same scope.
- **A fix-delta review** whenever a fix to a review finding changes code. Fixes are new code, and a fail-open can hide in one. The worker reviews its fix commits; where the app is installed, the lead's next request is scoped to the delta.

**The private-value scan** is the leak gate run over the pull request's commits, from the default branch's checkout, where the project keeps a [private value list](./repository-standards.md#private-values); [Running It Locally](./repository-standards.md#running-it-locally) gives the command.

**Checklist.** Copy this into the lead's notes for each pull request:

```markdown
Done gate: #<PR>, head <sha>
- [ ] CI: every check's conclusion on <sha> is success (not "pending")
- [ ] Sign-off: the "Signed off by the operator" comment is on the issue
- [ ] Required reviews: plan review (if a full plan) and code review ran; dispositions in the body
- [ ] Recommended review: scoped app review answered, or lead review by hand
- [ ] Fix-delta review: for every fix that changed code, or none needed
- [ ] Acceptance: each criterion checked by the lead on <sha>
- [ ] closingIssuesReferences: exactly the issues meant to close
- [ ] Names: the human named by role only
- [ ] Private-value scan over the pull request's commits: clean, or no list kept
- [ ] At a glance: current on <sha>, within the word limits
- [ ] Residuals: filed as issues, or none
- [ ] Compound decision: done, deferred to when, or not needed
- [ ] Other gates: an adopter's test, every importer's suite, the merge order; or none
- [ ] After the merge: any step someone must take, such as re-installing a hook; or none
All ticked: post the ready-to-merge comment. Any open: say "NOT ready" and name it.
```

A push after the ready-to-merge comment makes it stale: the lead reruns the gate on the new head and posts a fresh comment.

---

## 6. Operator interaction

**Quiet mode is on by default.** The lead messages the operator only for:

- a pull request ready to merge;
- a decision only the operator can make;
- a blocker;
- a leak, meaning a private value posted or committed.

Everything else goes to the lead's board and log, and the operator asks for a digest when they want one ("status?"). The operator turns quiet mode off or on by telling the lead, and the lead records the setting on its board, so a restarted lead keeps it.

- **Batch ready pull requests.** One message lists every pull request ready to merge, in merge order.
- **Present decisions one at a time.** With several open, the lead queues them and brings them one item at a time, each with its recommendation.
- **Say "NOT ready" explicitly** while any gate is open. A summary that sounds finished gets merged.

---

## 7. Lead hygiene

- **Keep a resumable board and log** in a private, untracked location, not in the repository. The board is what is in flight and what is next; the log is one dated line per event, in UTC (`date -u`, not the session's sense of the time). A new lead session resumes from the board.
- **Verify installs on the machine, not on the default branch.** A fix merged to a hook isn't guarding anything until the installed copy is updated.
- **Check that every new worker is reachable by name.**
- **Archive a worker when its ticket is done**, rather than reusing it for the next ticket. A fresh session starts with a clean context and only the handoff.
- **Watch the shared usage window.** Every session draws on the same usage allowance; check it before starting workers.

---

## 8. Adopting and declining

The model is opt-in. The hooks, At a glance and the AI-review discipline stand alone, and the ready-to-merge comment already applies only where someone other than the author merges.

**When it fits:** one human directing agent sessions, with several tickets that can run in parallel.

**When it doesn't:** one session at a time, or a team of human reviewers. The overhead of a lead buys nothing when there is no board to coordinate, and human reviewers bring their own process.

**Quick start.** With Claude Code, install the [`agent-team` plugin](../plugins/agent-team/README.md) and run its `start-team` skill from a session in your project:

```bash
claude plugin marketplace add rmorison/engineering-standards
claude plugin install agent-team@engineering-standards
```

Then, in the session, run `/agent-team:start-team`, or ask for an agent team. It checks the [prerequisites](#9-prerequisites), adds the line in step 2 below if it is missing, and starts `<project>-lead` in the lead role. It starts the lead as a background session, or through the host's session tool, or, where neither works, makes the current session the lead. It then tells you where the lead is and what it does next, as in [Starting a team](#starting-a-team). The lead and worker roles it loads link to this document rather than copying it.

**To adopt by hand,** or without Claude Code:

1. Meet the [prerequisites](#9-prerequisites).
2. Add this line to the project's `CLAUDE.md` or `AGENTS.md`, so every session knows its context. You may pin the link to a commit, as you pin the hooks.

   ```markdown
   This project runs an agent team (see [Agent Team Workflow](https://github.com/rmorison/engineering-standards/blob/main/process/agent-team-workflow.md)): the operator starts one lead session with that document, and the lead starts each worker with a handoff.
   ```

3. Start a lead session and point it at this document, as in [Starting a team](#starting-a-team).
4. Give the lead a private, untracked place for its board, log and handoffs.

**Partial adoption is fine:** the guardrails and At a glance without a lead, or a lead with one worker at a time.

**To decline or stop:** remove the line and archive the lead, and uninstall the plugin if you installed it. Nothing in the repository depends on the model.

### Starting a team

**With the plugin,** `start-team` does the operator's part: it starts the lead with an opening prompt like the one below, filled in, and the lead's role is loaded from the start. It asks once where the lead keeps its board, records how it started the lead, and on a second run reports the running lead instead of starting another. Sessions it starts get the starting session's `auto` or `acceptEdits` permission mode only when both hooks are installed, and never `bypassPermissions`. A worker on the operator's machine then keeps that mode only if it passes [the guardrail check](#the-guardrail-check). A cloud session, or any session when the hooks are missing, runs in the default mode, and the operator answers its prompts.

**By hand,** the operator starts a new session and types something like this opening prompt:

```text
You are <project>-lead, the lead for <project>. This project runs an agent team:
read the adoption line in CLAUDE.md (or AGENTS.md) and the Agent Team Workflow
it links to, and act as the lead it describes. Keep your board, log and handoffs in <private path>.
Check the prerequisites, read the open issues and pull requests, and propose a
first sprint. Stop for my sign-off before starting any worker.
```

**The lead's first moves, in order:**

1. **Set up its board, log and handoffs** in the private, untracked location, as in [Lead hygiene](#7-lead-hygiene), and check that its session is reachable as `<project>-lead`, renaming itself if the name didn't take ([Roles](#1-roles)).
2. **Check each [prerequisite](#9-prerequisites)** and report any that is missing, with § 9's fallback where there is one. If it can't start sessions, the operator starts workers by hand. If sessions can't message each other, it says so and stops: pings depend on messaging. The one exception is a lead the operator chose to start on a host where messages reach sessions but replies can't come back, such as a cloud session started from a local one; there the lead relies on its scheduled GitHub check (§ 3) instead of pings, and says so.
3. **Read the open issues and pull requests** on GitHub.
4. **Propose a first sprint:** the tickets, their lanes by file overlap and the merge order ([Traffic](#3-traffic)), with one worker per ticket. Then it stops for the operator's sign-off.
5. **After sign-off,** it records the approved sprint on its board, writes each ticket's handoff from [the template](#4-the-worker-handoff), checks the usage window, and starts the workers by the route [§ 1](#1-roles) prefers. It checks that each one connected, is reachable by name and reported its [guardrail check](#the-guardrail-check). If it can't start sessions, it gives the handoffs to the operator.

**What the operator does next.** Sign off the sprint, or edit it and sign off the edit. If the lead can't start sessions, start each worker by hand with the handoff the lead wrote. Each worker then posts a plan, and the lead brings it to the operator for sign-off ([the sprint loop](#2-the-sprint-loop)). [Quiet mode](#6-operator-interaction) is on throughout: the lead messages the operator only for a pull request ready to merge, a decision, a blocker or a leak.

---

## 9. Prerequisites

- **Both hooks installed** for the account the sessions run as: [the leak hook](./repository-standards.md#guarding-agent-sessions) and [the policy hook](./repository-standards.md#guarding-repository-authority). Both are Claude Code hooks; on another agent host, an equivalent guard is needed. Installed is not enough for a session above the default mode: [the guardrail check](#the-guardrail-check) shows the hooks fire in that session.
- **A plan review, a code review and a learnings step** in each worker's flow. The [compound-engineering plugin](./compound-engineering-integration.md) provides them (`ce-doc-review`, `ce-code-review`, `ce-compound`); equivalents work too.
- **Sessions that can message each other**, and a lead that can start and archive sessions. Without the second, the operator starts and archives workers by hand and the rest of the model still holds.
- **A way to wake the lead on a schedule**, for the backstop check in [Traffic](#3-traffic). Without it, the operator prompts the lead to check ("status?" does it), and a missed ping waits until then.
- **One posting account.** Every session posts to GitHub as the operator's account, so GitHub can't tell a session from the operator; the policy hook is what keeps merges and settings with the operator.

---

## 10. Future work

Each is a separate ticket, not built here:

- **Done-gate checks as code:** a script that runs the gate's mechanical checks (CI conclusions, closing references, the private-value scan, At a glance word counts) instead of the lead doing them by hand.
- **A budget and health monitor:** watches the shared usage window and each worker's context size, and warns or archives before a worker degrades.

---

## See also

- [`process/compound-engineering-integration.md`](./compound-engineering-integration.md) — AI-review discipline and the ready-to-merge comment
- [`process/repository-standards.md`](./repository-standards.md) — the leak gate and both hooks
- [`process/git-branching-strategy.md`](./git-branching-strategy.md) — the pull request description and At a glance
- [`ai/claude-code/README.md`](../ai/claude-code/README.md) — the six-layer AI architecture
- [`plugins/agent-team/`](../plugins/agent-team/README.md) — the `start-team` skill and the lead and worker roles; [ADR-0002](../docs/engineering/adr/0002-agent-team-roles.md) records where the roles sit in the six layers
