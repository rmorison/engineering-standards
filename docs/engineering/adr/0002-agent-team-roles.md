# ADR-0002: Agent-Team Roles Are an Orchestration Pattern Over the Six Layers

**Date:** 2026-10-07
**Status:** Accepted

## Decision

The lead and worker roles of the [Agent Team Workflow](../../../process/agent-team-workflow.md) are an **orchestration pattern over the six layers**. They are not a seventh layer, and they don't widen Layer 3. A role is how one whole session is configured; every one of the six layers applies inside that session as usual.

The roles ship as the [`agent-team` plugin](../../../plugins/agent-team/README.md). It holds a `start-team` skill and two role files in Claude Code's subagent format. A role file runs as a whole session with `claude --agent`, not as a subagent dispatched inside one. [ADR-0001](./0001-six-layer-ai-architecture.md) stands unchanged.

## Context

[#101](https://github.com/rmorison/engineering-standards/issues/101) asked for a one-step way to start an agent team, with packaged lead and worker roles, and for a record of where those roles sit in the six-layer model. Three placements were considered:

- **Widen Layer 3.** Layer 3 is persona agents: perspectives that a Layer 2 skill dispatches inside one session, such as a security reviewer. A role is a different kind of thing. It is who a whole session is for its lifetime, and its peers are other sessions it messages. Putting both under one layer would blur the layer's principle, *Perspective*, and invite the category errors ADR-0001 was written to remove.
- **Add a seventh layer.** Each layer in ADR-0001 specializes a context-cost principle: when context loads and how much it costs. Roles add none. A role's prompt loads once at session start, as Layer 1 does, and it reaches its rules by link, as the vendor-neutral skills do. A layer with no principle of its own isn't a layer.
- **Record roles as an orchestration pattern.** Roles configure sessions, and sessions coordinate through messages and GitHub. That is a level above the layers, which describe what loads inside one session. Chosen.

The mechanism was chosen from scratch runs under Claude Code 2.1.288 and 2.1.293, recorded on #101. `claude --agent` loads a role's prompt for the whole session, and the project's `CLAUDE.md`, skills and user-scope hooks still apply. Other routes lost: a project `CLAUDE.md` section would give workers the lead's rules, and `--append-system-prompt` copies the rules into the start command rather than linking them.

## Consequences

**What changes:**

- The repository ships its first Claude Code plugin, `plugins/agent-team/`, and a marketplace manifest, `.claude-plugin/marketplace.json`. An adopter installs it; nothing is copied into their project, and an adopter who declines the agent team gets no files.
- The role files reuse two existing formats: a Layer 2 skill (`start-team`) and the subagent file format of Layer 3. They change neither layer's meaning. A role file is a subagent definition used at session scope.
- `scripts/check-template-kit.mjs` reads plugin agents and skills as well as the kit's, since a role file Claude Code can't read is skipped without a word.

**What stays unchanged:**

- The six layers, their principles and ADR-0001.
- The Agent Team Workflow's rules. The roles link to them rather than restating them, so the workflow document remains the one place they are written.
- The starter kit in `templates/`.

**Maintenance liability:**

- `--agent`, `--bg`, `claude agents` and plugin-scoped agent names are recent Claude Code surfaces. The plugin README names the version it was proved on, and a change to those surfaces is a change to the plugin, not to this decision.
- Any session with the plugin installed also sees the roles as subagents. Their descriptions say not to dispatch them, but nothing enforces that.

## References

- **Origin issue:** [#101](https://github.com/rmorison/engineering-standards/issues/101). It supersedes the role-agents spike in [#49](https://github.com/rmorison/engineering-standards/issues/49).
- **Plan:** [`docs/plans/2026-10-07-1608-feat-start-agent-team-plan.md`](../../plans/2026-10-07-1608-feat-start-agent-team-plan.md), decisions D1 to D5.
- **Architecture:** [ADR-0001](./0001-six-layer-ai-architecture.md) and [`ai/claude-code/README.md`](../../../ai/claude-code/README.md).
