# ADR-0001: Six-Layer AI Architecture

**Date:** 2026-05-03
**Status:** Accepted

## Decision

This repository adopts a **six-layer AI architecture** as the conceptual model for AI tooling integrated with software engineering workflows. The architecture is the abstraction; specific implementations — most concretely [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) (CE) for [Claude Code](https://claude.ai/code) — fill the layers as canonical realizations. Vendor-neutral baselines remain in place for projects that do not adopt a specific toolkit; the layering itself preserves vendor-neutrality.

## Context

This repository previously documented a four-layer AI architecture (Rules / Skills / Agents / Hooks) introduced via PRs [#16](https://github.com/rmorison/engineering-standards/issues/16), [#19](https://github.com/rmorison/engineering-standards/issues/19), and [#21](https://github.com/rmorison/engineering-standards/issues/21). The four-layer model was a useful first sketch grounded in a thin, vendor-neutral toolkit (web-fetch-based skills and a small set of agents).

Active use of compound-engineering across `rmorison` projects revealed that the four-layer model — taken literally — does not accommodate a developed LLM-engineering system without distortion. Three structural patterns visible in CE are absent from the original taxonomy:

1. **Skill-orchestrated personas.** CE persona reviewers are prompt templates dispatched by orchestrator skills (`ce-doc-review`, `ce-code-review`); they are not standalone subagents in the original Layer 3 sense.
2. **Skill-loaded reference subtrees.** CE skills ship `references/*.md` directories that progressively load context during workflow execution — neither at session start nor at invocation, but as workflow depth grows.
3. **Compound / learnings.** CE captures institutional knowledge through `ce-compound`, `ce-compound-refresh`, and the `docs/solutions/` artifact pattern — a feedback loop that lets work compound rather than restart from blank.

The right move is not to absorb CE's idiosyncrasies into the existing layers (which led to category errors during prior planning) and not to displace the four-layer wholesale (which loses the principle the original captured). The right move is to **evolve the architecture itself** to absorb the patterns CE has surfaced — keeping the abstraction general enough that other LLM-engineering toolkits, present or future, can fit the same slots.

## The Architecture

Each layer specializes a distinct **principle** for how AI capability composes with engineering work. The six principles together capture what makes LLM-based engineering function in practice today.

| # | Layer | Principle | Vendor-neutral baseline | Canonical realization (CE) |
|---|-------|-----------|-------------------------|----------------------------|
| **1** | Rules | **Persistence** — load once per session, every session | `ai/claude-code/rules/*.md` (this repo) | Not provided by CE; standards repo retains ownership |
| **2** | Workflow Skills | **Composability** — multi-step orchestrators that compose into pipelines | `templates/.claude/skills/{spec,plan,review}/` (this repo) | CE skills: `/ce-brainstorm`, `/ce-plan`, `/ce-work`, `/ce-doc-review`, `/ce-code-review`, `/ce-debug`, `/ce-compound`, `lfg`, … |
| **3** | Persona Agents | **Perspective** — multiple expertises analyze the same artifact | `templates/.claude/agents/{code-reviewer,spec-writer}.md` (this repo) | ~20 CE persona reviewers (coherence, feasibility, adversarial, security, scope-guardian, language-specific style enforcers, …) |
| **4** | References | **Progressivity** — context grows as workflow depth grows | (no vendor-neutral baseline yet) | CE skills' `references/*.md` subtrees, loaded during skill execution |
| **5** | Compound / Learnings | **Compounding** — institutional knowledge accumulates across work | (no vendor-neutral baseline yet) | `docs/solutions/` populated by `ce-compound` and `ce-compound-refresh` |
| **6** | Hooks | **Determinism** — non-AI enforcement at zero context cost | `templates/.claude/hooks/` (this repo) | Not provided by CE; standards repo retains ownership |

### Layer descriptions

**Layer 1 — Rules.** Compact pointers and behavioral guardrails kept in agent context every turn. Files in this layer load at session start and remain visible across all work; their discipline is to stay *small* (under ~150 lines each) so that the always-loaded budget stays affordable. Layer 1 typically directs the agent to the rest of the architecture rather than encoding policy inline.

**Layer 2 — Workflow Skills.** Multi-step orchestrators invoked on demand by user or orchestrator. Skills compose into pipelines: discovery → planning → execution → review → compounding. A Layer 2 skill is *lazy-loaded* (its content enters context only when invoked), but implementations vary in depth: a vendor-neutral skill may be a thin URL-fetch template; a deeper realization may run multi-round workflows that dispatch Layer 3 personas and load Layer 4 references during execution.

**Layer 3 — Persona Agents.** Specialized prompt templates that encode focused domain expertise (security, performance, coherence, framework-specific style, etc.). Persona Agents are typically **dispatched by Layer 2 skills** rather than invoked directly, though simple realizations may include standalone-invocable agents. The pattern of "one skill orchestrates many persona agents in parallel" is what makes multi-perspective review tractable.

**Layer 4 — References.** Documents *loaded by skills during execution* — not at session start (Layer 1), not at invocation (Layer 2's initial bundle), but as workflow depth grows. References allow a Layer 2 skill to remain lean at the entry point while still being able to reach for deeper context when a particular workflow branch demands it. The vendor-neutral baseline for this layer is empty today; the pattern was surfaced by CE.

**Layer 5 — Compound / Learnings.** Outcomes captured from completed work that feed forward into future work — closing the loop between execution and accumulated knowledge. Layer 5 artifacts include solution documents, retrospective notes, and post-mortem records. The principle is that work *compounds*: the second similar task should be cheaper and higher-quality than the first because the first's learnings are captured and findable.

**Layer 6 — Hooks.** Shell-level scripts that run on tool-use events (pre/post invocation), enforcing rules deterministically and without consuming AI context. Layer 6 catches mechanical mistakes (typos in file paths, write attempts to protected paths, missing pre-commit checks) at zero AI cost.

### How the layers compose

Layers are independent slots: a project can fill some and leave others empty. A typical CE-using project fills all six. A minimal project might fill only Layers 1, 2, and 6.

Pipelines are composed at Layer 2: a sequence of skill invocations (e.g., `ce-brainstorm → ce-plan → ce-work → ce-doc-review → ce-code-review → ce-compound`) carries an artifact from discovery to compound output. Each Layer 2 skill in the pipeline may dispatch Layer 3 personas (for review-shaped skills), load Layer 4 references (as workflow depth grows), and produce Layer 5 compound output (as learnings worth preserving). Layer 1 rules direct default behavior across all of the above; Layer 6 hooks enforce mechanical invariants at the shell boundary.

## Why compound-engineering as canonical realization

This ADR names CE specifically because:

- CE is the most developed LLM-engineering implementation in active use across `rmorison` projects, with deep realizations of Layers 2 (~30 skills), 3 (~20 personas), 4 (skill reference subtrees), and 5 (compound + solutions).
- Describing the architecture in CE's terms gives concrete grounding for adopters, while the layer definitions stay abstract enough that other realizations (Cursor commands, Aider, hand-rolled implementations) fit the same slots without contradiction.
- CE is actively maintained at v3.x and follows a release cadence the architecture description can track.

This is not exclusive: the architecture is intentionally vendor-neutral. Adopters can fill Layers 2–5 with a different toolkit, with hand-rolled implementations, or with the vendor-neutral baselines this repository provides. CE is named as canonical because it exists, works, and is in use — not because it is mandatory.

**Upgrade discipline.** Pin to CE 3.x. Re-evaluate the integration at CE 4.x major version. Within 3.x, skill-name churn is a one-row change in the cross-reference table maintained by [`process/compound-engineering-integration.md`](../../../process/compound-engineering-integration.md).

## Consequences

**What changes:**

- The architecture description names six layers (was four), with **References** (Layer 4) and **Compound / Learnings** (Layer 5) promoted to first-class layers.
- Layer 2 (Workflow Skills) and Layer 3 (Persona Agents) acknowledge depth and orchestration variation: vendor-neutral baselines are thin and standalone; canonical realizations may be deeper and skill-orchestrated. Both fit the layer.
- Solo / AI-driven workflows become a first-class scale alongside team-scale assumptions in existing standards.
- AI-review (`ce-code-review` + `ce-doc-review`) is documented as **review discipline**, not an enforced merge gate. There is no CI check or branch-protection rule that enforces it. The discipline is process-level; failure modes are named explicitly in the integration doc so adopters know what they are trading.
- An artifact-path precedence rule with a provenance clause governs the boundary between standards-mode and CE-mode paths.

**What stays unchanged:**

- ADR location and format (this very document follows the conventions in `process/documentation-standards.md`).
- Semantic versioning, conventional commits, PR-based merges, GitHub Flow.
- Code quality principles in `code/`.
- The four-layer model's stated principle — *"Context is expensive — only load what's needed, when it's needed"* — is preserved and extended. Six layers, six specializations of context-cost discipline.
- The vendor-neutral baselines (`templates/.claude/skills/`, `templates/.claude/agents/`, `templates/.claude/hooks/`, `ai/claude-code/rules/`) remain in place. They are not deprecated; they fill the layers for projects that do not adopt a deeper toolkit.

**Maintenance liability:**

- Naming a canonical realization (CE) creates a tracking obligation against an upstream this repository does not control. The integration doc describes CE skill behavior alongside skill names so name-churn within 3.x is a one-row table edit; major version transitions warrant a re-evaluation of the canonical-realization claim.
- Layer 4 (References) and Layer 5 (Compound) currently have only a CE realization. The architecture describes what those layers are *structurally*; vendor-neutral realizations may emerge over time and would fit the same slots.

## References

- **Origin issue:** [rmorison/engineering-standards#22 (rescoped)](https://github.com/rmorison/engineering-standards/issues/22)
- **Built on:** PRs [#16](https://github.com/rmorison/engineering-standards/issues/16), [#19](https://github.com/rmorison/engineering-standards/issues/19), [#21](https://github.com/rmorison/engineering-standards/issues/21) — the original four-layer architecture this work refines.
- **Related issue:** [#12](https://github.com/rmorison/engineering-standards/issues/12) (Phase 0 — partially addressed by the integration doc's `docs/brainstorms/` declaration for CE-using projects).
- **Operational reference:** [`process/compound-engineering-integration.md`](../../../process/compound-engineering-integration.md) — describes CE's realization of each layer plus path mappings, branch-naming reconciliation, AI-review discipline, and ticket-tracking modes.
- **Architectural reference:** [`ai/claude-code/README.md`](../../../ai/claude-code/README.md) — canonical layer-by-layer description.
- **Compound-engineering plugin:** https://github.com/EveryInc/compound-engineering-plugin (v3.1.0).
- **Agent-native foundation:** https://every.to/guides/agent-native — the conceptual antecedent that informed both the four-layer model and CE.
- **Archived prior proposals:** [`archive/`](../../../archive/) — three earlier `ai/*.md` documents that proposed building agent-native abstractions in this repository rather than adopting an existing toolkit. Preserved as the evaluative framework that informed this decision.
- **Real-world deployment example:** `books-ops` (private rmorison repository) — informed the integration doc's wording during real use of the brainstorm → plan → ce-doc-review → lfg pipeline. Named as deployment context, not as a documentation reference.
