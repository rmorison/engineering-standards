# ADR-0003: A Coordinator Above the Leads, and the Lead Merges on Track 2

**Date:** 2026-11-20
**Status:** Accepted

## Decision

**D1. The role above the leads is called "coordinator" in the standard.** It is optional, there is one per operator across all of their projects, and a local name for it stays local. Like the lead and worker, it is an **orchestration pattern over the six layers**, not a layer: [ADR-0002](./0002-agent-team-roles.md)'s reasoning holds unchanged. It ships as a third role file in the [`agent-team` plugin](../../../plugins/agent-team/README.md).

**D2. On Track 2 of [Merge authority](../../../process/agent-team-workflow.md#11-merge-authority), the project's lead merges**, not the coordinator and not a separate integration agent. The coordinator sets the merge order across projects and checks the Done gate on sensitive pull requests before the operator's review is requested. It never approves or merges.

## Context

[#135](https://github.com/rmorison/engineering-standards/issues/135) asked for the role a long-lived session above the leads had already been playing for two weeks: working ideas before a repository exists, setting projects up, relaying between the operator and the leads, curating the standards, pre-reviewing sensitive changes and watching shared infrastructure. [#113](https://github.com/rmorison/engineering-standards/issues/113) asked who agents act as on GitHub. Its spike showed a GitHub App as the author, the operator's approval required by a ruleset, and a merge allowed only after that approval, with a rebase that changed no content keeping it.

The two land together because they share one point: the operator's attention, spent once per pull request, on an approval GitHub records in the operator's own name.

**Naming (D1).** The standard names the role for what it does across projects. An operator may call their own session something else, such as a job title; that name stays in their own notes, and the standard and its roles say "coordinator".

**Placement (D1).** The three options in ADR-0002 were weighed again. A coordinator is who a whole session is for its lifetime, its peers are other sessions, and it adds no context-cost principle. It is a role, like the other two.

**Who merges (D2).** Three candidates were considered:

- **The coordinator.** It sees every project, but merging would put it inside each repository's work, against its rule of reaching a project only through issues, pull requests and the lead. It would also make one session the merge point for every project.
- **A dedicated integration agent.** #113 proposed one to merge in order and rebase after each merge. The spike's main worry for it was that every rebase would need a fresh approval. It doesn't: a rebase with no content change kept the approval. So nothing is left that a lead can't do.
- **The project's lead.** It already runs the Done gate and knows the merge order inside its project. Chosen.

## Consequences

**What changes:**

- The workflow gains an optional coordinator row in § 1, its subsection "Coordinating several projects", its place in § 6 and § 7, and § 11 Merge authority with two tracks. Track 1, the operator merges, stays the default.
- The `agent-team` plugin gains `agents/coordinator.md`, linking the workflow rather than restating it. `start-team` doesn't start a coordinator; the operator does.
- The policy hook gains one grant, in its own pull request: a lead may merge, without an administrator bypass, only in a session that declares Track 2. The coordinator and workers get nothing.

**What stays unchanged:**

- The six layers, ADR-0001 and ADR-0002.
- A project with no coordinator, and a project on Track 1: they follow the workflow as before.
- Approval stays with the operator on both tracks.

**Maintenance liability:**

- Track 2 is piloted until a pilot on a real project reports on #113. Its setup runbook, and the token helper's contract, come in later pull requests.
- On Track 2, any agent token can merge where GitHub's rules allow it, so the ruleset is the control and the hook the second line. A repository without the enforced ruleset stays on Track 1.
- An integration agent stays future work. If leads merging in order proves too slow or error-prone, it is reconsidered.

## References

- **Origin issues:** [#135](https://github.com/rmorison/engineering-standards/issues/135) (part 1) and [#113](https://github.com/rmorison/engineering-standards/issues/113), including its spike results.
- **Plan:** [`docs/plans/2026-11-20-0053-feat-coordinator-and-merge-authority-plan.md`](../../plans/2026-11-20-0053-feat-coordinator-and-merge-authority-plan.md), decisions D1 to D8, signed off by the operator on [#141](https://github.com/rmorison/engineering-standards/pull/141).
- **Architecture:** [ADR-0001](./0001-six-layer-ai-architecture.md), [ADR-0002](./0002-agent-team-roles.md) and [`ai/claude-code/README.md`](../../../ai/claude-code/README.md).
