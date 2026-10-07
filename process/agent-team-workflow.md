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

**What it leaves out.** How a session is started, named, messaged or archived depends on the agent host, and so does reaching a session from another machine. This document names the capability it needs ([Prerequisites](#9-prerequisites)) and leaves the mechanics to the host's own documentation.

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
- Names are unique on the machine, so a message reaches the session it means to. The lead is `<project>-lead`. Each worker is `<PREFIX>-<role>`: a short project prefix and a word for the ticket, such as `ES-policy`.
- After starting a worker, the lead checks that it can reach the worker by that name. If the name didn't take, the worker renames itself, which is the first line of its handoff.

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

Before writing a handoff, the lead checks that the tools it names (a language runtime, a linter) exist on the host where the worker runs.

**Template.** The lead keeps handoffs in its private notes, not in the repository. Copy this into them and fill in the placeholders:

```markdown
# Handoff: #<ISSUE> → <PREFIX>-<role>

You are <PREFIX>-<role>, a worker for <owner>/<repo>, started by <project>-lead.
If your session name isn't <PREFIX>-<role>, rename it first.

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

**With the plugin,** `start-team` does the operator's part: it starts the lead with an opening prompt like the one below, filled in, and the lead's role is loaded from the start. It asks once where the lead keeps its board, records how it started the lead, and on a second run reports the running lead instead of starting another. Background sessions get the starting session's `auto` or `acceptEdits` permission mode only when both hooks are installed, and never `bypassPermissions`. Otherwise they start in the default mode, and the operator answers their prompts after `claude attach <id>`.

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
2. **Check each [prerequisite](#9-prerequisites)** and report any that is missing, with § 9's fallback where there is one. If it can't start sessions, the operator starts workers by hand. If sessions can't message each other, it says so and stops: pings depend on messaging.
3. **Read the open issues and pull requests** on GitHub.
4. **Propose a first sprint:** the tickets, their lanes by file overlap and the merge order ([Traffic](#3-traffic)), with one worker per ticket. Then it stops for the operator's sign-off.
5. **After sign-off,** it records the approved sprint on its board, writes each ticket's handoff from [the template](#4-the-worker-handoff), checks the usage window, and starts the workers, checking each is reachable by name. If it can't start sessions, it gives the handoffs to the operator.

**What the operator does next.** Sign off the sprint, or edit it and sign off the edit. If the lead can't start sessions, start each worker by hand with the handoff the lead wrote. Each worker then posts a plan, and the lead brings it to the operator for sign-off ([the sprint loop](#2-the-sprint-loop)). [Quiet mode](#6-operator-interaction) is on throughout: the lead messages the operator only for a pull request ready to merge, a decision, a blocker or a leak.

---

## 9. Prerequisites

- **Both hooks installed** for the account the sessions run as: [the leak hook](./repository-standards.md#guarding-agent-sessions) and [the policy hook](./repository-standards.md#guarding-repository-authority). Both are Claude Code hooks; on another agent host, an equivalent guard is needed.
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
