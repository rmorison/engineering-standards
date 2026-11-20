---
title: A Coordinator Role Above the Leads, and Agent Merges on the Operator's Approval (#135 part 1, #113 follow-up) - Plan
type: feat
date: 2026-11-20
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
origin: https://github.com/rmorison/engineering-standards/issues/135
---

# A Coordinator Role Above the Leads, and Agent Merges on the Operator's Approval - Plan

**Status: DRAFT; open questions resolved by the operator on #141.** Started by the coordinator described here, at the operator's request. Every decision below is
**PROPOSED** and waits for the operator's sign-off on #135.

## Goal Capsule

- Objective: an operator running several projects can add one optional session above the project leads, and can
  move any project from "the operator merges" to "an agent merges once the operator has approved on GitHub". The
  two changes land together because they share one point: the operator's attention, spent once per pull
  request, on an approval GitHub records in the operator's own name.
- Means: a coordinator role in the workflow, the agent-team plugin and a new ADR (#135 part 1); a "Merge
  authority" section with two tracks, built on the #113 spike results; one row in the policy hook's grants
  table; a token helper contract and a setup runbook; a pilot on one project before the standard says "ready".
- Authority: #135 part 1 and #113 (the issue, the CTO-review comment of 2026-11-08, the two-track proposal of
  2026-11-08 and the spike results of 2026-11-10) are the spec. #135 part 2 (a review class for data-model
  changes) is out of scope and moves to its own issue. Where this plan and a sign-off comment disagree, the
  sign-off wins.
- Execution profile: `process/agent-team-workflow.md` (§ 1, § 6, § 9, § 10, new § 11 and § 12),
  `process/repository-standards.md` § Guarding Repository Authority, `scripts/claude_policy_hook.py` and its
  tests, `plugins/agent-team/` (new `agents/coordinator.md`, `README.md`, `plugin.json` 0.12.0 to 0.13.0), new
  `docs/engineering/adr/0003-coordinator-and-merge-authority.md`, new `docs/runbooks/agent-merge-setup.md`,
  `.github/workflows/claude.yml`'s trigger. No change to the leak hook.
- Stop conditions: stop and comment on #135 if a unit needs the operator's real token, a real App private key,
  a change to a live repository's rules, or any host-specific detail in the repository; or if the pilot (U7)
  shows a branch rule letting a merge through without the operator's approval on the head.
- Finishes the work: one PR per unit group (U1 to U3 docs and role; U4 hook; U5 and U6 runbook and action),
  each `Part of #135` or `Part of #113`. The pilot report closes #113. The operator merges every PR in this
  plan: Track 2 does not apply to its own rollout.

---

## Product Contract

### Summary

The workflow stops at one project: operator, lead, workers. Running several projects at once has shown two
needs.

**A role above the leads.** Work crosses projects: one project's change needs another's contract, standards have
to be carried between repositories, and the operator's attention is the shared constraint. A long-lived session
above the leads has done this work for two weeks. It:
- works ideas before a repository exists;
- sets up and retires projects;
- relays decisions between the operator and the leads;
- curates the standards;
- pre-reviews sensitive changes;
- watches shared infrastructure, such as expiring tokens and stopped sessions.

It keeps a decision record and does no ticket work. #135 asks for this to be written down as an optional role.

**Merges that cost the operator one tap.** Every pull request today waits on the operator to merge in the web
UI, and the "ready" news reaches them only by a lead's message: GitHub doesn't notify an account of its own
comments. Relayed decisions have a second cost. A lead won't act on an operator decision passed through another
session. That is right, but it sends the operator back to each lead to say the same words again. The #113 spike
showed a GitHub App as the author, with the operator's approval required by a ruleset, merging only after that
approval. A pure rebase after approval kept the approval, and any content change dismissed it.

They dovetail: with an App as the author, the operator's approval on GitHub is the sign-off, in the operator's
own name, and needs no relaying. The coordinator's job shifts from carrying messages to making sure each
approval request reaches the operator with the gate done and the order right.

### Requirements

- R1. The workflow describes an **optional coordinator role**:
  - what it does and never does;
  - how it relates to each project's lead;
  - its record;
  - its guardrails.

  A project with no coordinator reads exactly as today.
- R2. The coordinator never does ticket work in a project repository. It reaches another project only through
  issues, pull requests and messages to that project's lead. It never starts, stops or restarts its own session.
  It may start and restart a project lead's session where the host allows.
- R3. The coordinator keeps a **decision record**:
  - one canonical document per domain;
  - a "Last updated" date;
  - a dated log of changes that came from outside.

  Where the record and any other note disagree, the record wins. The standard names the shape, not a file layout.
- R4. A **Merge authority** section offers two tracks per project. The operator picks a project's track.
  - **Track 1, the default:** the operator merges.
  - **Track 2:** an agent identity authors, the operator approves on GitHub, and the project's lead merges after
    the approval.
- R5. Under Track 2, GitHub refuses a merge without the operator's approval on the current head. A ruleset
  enforces it, not only a hook or an instruction. A rebase with no content change may keep the approval; any
  content change needs a fresh one.
- R6. The policy hook's grants table gains one row: the `lead` role may merge a pull request, with no
  administrator bypass, only in a session that declares Track 2. Every other action stays denied to every role,
  and the coordinator and workers are granted nothing.
- R7. No session can read the App's private key. Sessions get short-lived installation tokens from a helper,
  scoped to one repository and to the permissions their role needs. The standard defines the helper's contract,
  not its host setup.
- R8. A worker started by a lead gets the worker role, whatever the lead holds. GitHub's branch rules, not token
  scoping, are what stop a worker's merge: the required code-owner approval and approval of the most recent push.
- R9. A Track 2 project's operator gets the ready-to-merge news from GitHub: a review request from the App,
  which reaches their review queue and phone. The lead's ready message to the operator becomes optional.
- R10. Nothing host-specific or secret lands in the repository: no tokens, key paths, account names or recovery
  details.

### Acceptance Examples

- AE1 (R1, R2). Two projects with leads and a coordinator. Project A needs a field from project B's read
  contract. The coordinator files the issue on B, tells B's lead, and records the dependency. It writes no code
  in B, and A's lead gets the order: B's PR first.
- AE2 (R5). On a Track 2 project, the lead runs `gh pr merge 12` before the operator approves. GitHub refuses.
  After approval, the lead rebases onto a new `main` with no conflict, CI passes, and the merge succeeds without
  a second approval. A worker then pushes one more commit, the approval is dismissed, and the merge is refused
  again.
- AE3 (R6). In a `lead` session declaring Track 2, the hook allows `gh pr merge 12 --squash` and denies
  `gh pr merge 12 --admin`. In a `coordinator` or `worker` session, or a `lead` session with no track declared,
  it denies both with today's message.
- AE4 (R7, R8). A lead's token reaches its own repository and nowhere else. A worker pushes a commit after the
  operator's approval; the approval is dismissed and GitHub refuses any merge until the operator approves again,
  even if the hook were missing.
- AE5 (R9). The App requests the operator's review on PR 12. The operator's phone shows it. The operator approves,
  and the lead merges and reports in its log, with no message sent to the operator.

---

## Decisions (all PROPOSED)

- **D1. The role is called "coordinator" in the standard.** A local name such as "CTO" stays local. Like lead and
  worker, it is an orchestration pattern over the six layers, not a layer (ADR-0002's reasoning holds); ADR-0003
  records it. One coordinator per operator, across all of their projects.
- **D2. The project lead merges, not the coordinator and not a separate integration agent.** The lead already
  runs the Done gate and knows the merge order inside its project. The coordinator sets the order across
  projects (AE1) and checks the Done gate on sensitive pull requests before the review request goes out. A
  dedicated integration agent stays future work: the spike showed rebases keep the approval, so leads can merge
  in order without one.
- **D3. One private GitHub App for all agents. Branch rules are the control; the hook is the second line.** This
  is the #113 review's recommendation. The standard doesn't try to scope a worker's token so it can't merge
  (push and merge share Contents: write): the ruleset's required code-owner approval and approval of the most
  recent push are what branch protection is there for (operator, on #141). A second App for leads stays optional
  hardening for sensitive projects.
- **D4. The operator is the only code owner of a Track 2 repository.** The ruleset requires one code-owner
  approval, dismisses stale approvals and requires approval of the most recent reviewable push, as the spike
  set it up.
- **D5. Tokens come from a helper the agent account can call but whose key it can't read.** The helper mints a
  one-hour installation token for the repository and role asked for, and refuses any other request. The contract
  is in the standard; the reference setup (a separate system user, or the operator's own account, holding the
  key) is in the runbook as an example, not a requirement. Sessions refresh a token by calling the helper
  again; a stale token fails closed. A full credential broker, where sessions never hold a token, stays out of
  scope as in #113.
- **D6. Track 1 stays the default.** Track 2 needs enforced branch rules, which on a private repository means a
  paid plan, and it needs the helper. An adopter who declines it changes nothing.
- **D7. The coordinator's decision record follows the buzai hub convention**: one canonical document per domain,
  "Last updated" at the top, a dated ingest log at the bottom, and the hub wins on conflict. The standard links it
  as prior art and asks only for the properties in R3.
- **D8. The Claude action's trigger accepts the App as an author** on Track 2 repositories, so the recommended app
  review still runs on agent-authored pull requests. It is limited to that App's bot login, never to bots in
  general.

## Resolved Questions (operator, on #141)

1. **A rebase that resolves a conflict.** GitHub's branch rules decide. With approval of the most recent
   reviewable push required, the lead doesn't second-guess the rule: if GitHub keeps the approval, the lead may
   merge; if it dismisses it, the lead asks again. The pilot records which it was.
2. **Workflow changes.** The standard recommends giving the App no Workflows permission, as best security
   practice, so a pull request that changes a workflow goes back to the operator. The operator sets the App's
   permissions and may choose otherwise.
3. **A worker's token and merging.** Not scoped in the token; branch rules carry it (D3).
4. **Keeping `gh` on a fresh token (the coordinator's call).** A `gh` wrapper, first on the session's `PATH`,
   asks the helper for a token on every call and runs the real `gh` with it in `GH_TOKEN`. Git goes through the
   same wrapper by `gh`'s credential helper. The helper may cache a token until a few minutes before it expires;
   no session stores one. If the helper is down or refuses, the wrapper exits non-zero without running `gh`, so
   a session fails closed and never falls back to another credential. A timed refresh was the other option. It
   needs a timer in every session and leaves a window where a stale or wrong token sits in the environment.

---

## Implementation Units

- **U1. Coordinator role in the workflow.** § 1 gains an optional fourth row and a short "Coordinating several
  projects" subsection: duties, never-does, relation to leads (it messages leads; it doesn't direct workers), the
  decision record (R3, D7), and guardrails (R2). § 6 gains the coordinator's place in operator traffic: one digest
  across projects instead of one stream per lead. § 7 notes that the coordinator watches the shared usage window
  and token expiry across projects.
- **U2. Role file and ADR.** `plugins/agent-team/agents/coordinator.md`, linking the workflow rather than
  restating it; the plugin README; `plugin.json` 0.13.0. ADR-0003 records D1 and D2.
- **U3. Merge authority, two tracks.** New § 11 in the workflow: the two tracks, the Track 2 sequence (Done gate,
  ready comment, App requests the operator's review, operator approves the head, lead confirms the approval is on
  the current head, lead merges, lead logs), the rebase rule, and what goes back to the operator (workflow
  changes, under the recommended App permissions). § 9's "One posting account" becomes "A posting identity", with
  each track's prerequisite. § 6's "pull request ready to merge" message becomes optional under Track 2 (R9).
- **U4. The policy hook grant.** One row in the grants table: `lead` may run `gh pr merge` without `--admin`,
  `--auto` stays allowed, only when the session's environment declares Track 2. Fixtures for AE3, each seen to fail
  first. The coordinator role exists in the table with no grants, so `--whoami` names it. § Guarding Repository
  Authority describes the row and how a session declares its track.
- **U5. Token helper contract and setup runbook.** `docs/runbooks/agent-merge-setup.md`: creating the App and its
  permissions (Contents, Pull requests, Checks read, Metadata; no Workflows, no Administration), the ruleset
  recipe from the spike, the CODEOWNERS line, the helper contract (inputs, scope rules, refusal cases, one-hour
  lifetime), the `gh` wrapper (resolved question 4) with its fail-closed test, and an example setup with the key out of the agent account's reach. Placeholders only.
- **U6. The Claude action trigger.** `.github/workflows/claude.yml` accepts the configured App's bot login as an
  author on a Track 2 repository (D8), with the owner-only rule unchanged for everyone else. The starter kit's copy
  follows.
- **U7. Pilot.** The operator picks one low-risk project and moves it to Track 2 by the runbook. One unit of real
  work goes through it, including one conflict-resolving rebase after approval. What GitHub did is posted on
  #113, which then closes. The workflow's Track 2 text says "piloted" until this report exists.

Order: U1 to U3 together (docs only), then U4, then U5 and U6, then U7. U4 can be reviewed while the docs are in
review; it grants nothing until a session declares Track 2.

## Review

- U1 to U3, U5 and U6 are docs and configuration: a plan review, then a read of the diff with CI.
- U4 is a change to a guard: a full blind review on its first complete head, with fixtures that show each denial
  firing before the grant row exists.
- U7 needs a human: the operator sets the ruleset and installs the App. Agents write the steps; they don't run
  them.

## Risks

- **A wider blast radius per token.** Any agent token can merge where GitHub's rules allow it. Mitigations:
  one-hour tokens scoped to one repository, a ruleset that requires the operator's approval on the head, and the
  hook's grant limited to `lead` and to declared Track 2 sessions. A repository without that ruleset must stay
  on Track 1: the runbook's last step checks it is enforced.
- **The private key is the new high-value secret.** If an agent session can read it, it can mint tokens. D5 keeps
  it out of the agent account's reach, and the runbook says how to check that.
- **Approval fatigue.** One tap per pull request is still one tap. The coordinator's digest batches requests in
  merge order, and the operator can leave any project on Track 1.
- **The coordinator becomes a bottleneck or a second operator.** It never approves, never merges in project
  repositories, and never relays an operator decision a lead can get from GitHub.

## Sign-off

- D1 to D8: the operator, on #135.
- U7's project choice: the operator.
