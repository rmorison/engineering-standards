# AI Architecture

A six-layer model for organizing AI tooling by **context cost** and **invocation pattern**.

Architectural decision: [ADR-0001](../../docs/engineering/adr/0001-six-layer-ai-architecture.md).
Operational reference for compound-engineering adoption: [`process/compound-engineering-integration.md`](../../process/compound-engineering-integration.md).

## Why this exists

Context is the scarce resource in AI-assisted engineering, and it is spent whether or not it is spent well. Without a model for *when* each piece of guidance loads, AI tooling accumulates as an undifferentiated pile: rules that could be pointers, workflows pasted into every session, expertise that arrives too late to matter. The budget goes to content nobody needed on this turn.

The six layers exist to make that cost legible. Each layer is a slot with a distinct answer to "when does this enter context, and what does it cost while it sits there" — always loaded and therefore small, loaded on invocation, loaded partway through a workflow, or never loaded because it runs at the shell. Sorting tooling into those slots turns an implicit budget into an explicit one.

A second benefit follows from the first. Once the slots are named, they can be filled by different toolkits without renegotiating the model. The architecture is the abstraction; a specific toolkit is one realization of it.

## What motivated six layers

This repository first documented a **four-layer** model — Rules, Skills, Agents, Hooks — a useful sketch grounded in a thin, vendor-neutral toolkit.

Sustained use of a developed LLM-engineering system showed the four layers could not hold it without distortion. Three structural patterns had no slot:

- **Skill-orchestrated personas.** Review expertise dispatched *by* an orchestrating workflow, fanning out in parallel — not standalone subagents a user invokes directly.
- **Skill-loaded reference subtrees.** Documents that load neither at session start nor at invocation, but partway through a workflow as its depth grows.
- **Compounding learnings.** Captured outcomes that feed forward, so the second similar task is cheaper than the first.

The choice was to absorb these into existing layers (which produced category errors), discard the model (which loses what it got right), or evolve it. The architecture evolved: References and Compound became first-class layers, and Skills and Agents were widened to admit both thin and deep realizations. [ADR-0001](../../docs/engineering/adr/0001-six-layer-ai-architecture.md) records the full reasoning.

## The six layers

| # | Layer | Principle | Baseline in this repository |
|---|-------|-----------|------------------------------|
| 1 | Rules | **Persistence** — loaded once per session, every session | [`ai/claude-code/rules/`](./rules/) |
| 2 | Workflow Skills | **Composability** — multi-step orchestrators that compose into pipelines | [`templates/.claude/skills/`](../../templates/.claude/skills/) |
| 3 | Persona Agents | **Perspective** — multiple expertises analyze one artifact | [`templates/.claude/agents/`](../../templates/.claude/agents/) |
| 4 | References | **Progressivity** — context grows as workflow depth grows | (none yet) |
| 5 | Compound / Learnings | **Compounding** — institutional knowledge accumulates across work | (none yet) |
| 6 | Hooks | **Determinism** — non-AI enforcement at zero context cost | [`templates/.claude/hooks/`](../../templates/.claude/hooks/) |

**Layer 1 — Rules.** Compact pointers and behavioral guardrails held in context every turn. Their discipline is to stay *small* (under ~150 lines each) so the always-loaded budget stays affordable, and to direct the agent toward the rest of the architecture rather than encoding policy inline. Elsewhere this layer appears as `AGENTS.md`, a project-root `CLAUDE.md`, or IDE rule files.

**Layer 2 — Workflow Skills.** Orchestrators invoked on demand, composing into pipelines that run discovery → planning → execution → review → compounding. A Layer 2 skill is *lazy at invocation*: its content enters context only when called. Depth varies widely and the layer admits both ends — a thin template that fetches a standards URL, and a multi-round workflow that dispatches Layer 3 personas and loads Layer 4 references as it runs. Elsewhere: editor commands, hand-rolled slash commands.

**Layer 3 — Persona Agents.** Prompt templates encoding focused domain expertise — security, performance, coherence, language-specific idiom. Persona Agents are **typically dispatched by Layer 2 skills** rather than invoked directly, though simple realizations may expose them standalone. One orchestrator fanning out to many personas in parallel is what makes multi-perspective review tractable at scale.

**Layer 4 — References.** Documents loaded by a skill *during execution* — not at session start (Layer 1), not in the invocation bundle (Layer 2), but as a particular workflow branch demands them. This lets a skill stay lean at its entry point while still reaching for depth when the work calls for it. No vendor-neutral baseline yet; the pattern was surfaced by a toolkit realization and the layer is named in anticipation.

**Layer 5 — Compound / Learnings.** Outcomes captured from finished work that feed into future work, closing the loop between execution and accumulated knowledge — solution documents, retrospectives, post-mortems. The principle is that work *compounds*: the second similar task should be cheaper and better because the first one's learnings were captured and are findable. Elsewhere: retrospective archives, post-mortem repositories, an ADR series for architectural learnings.

**Layer 6 — Hooks.** Shell-level scripts on tool-use events (`PreToolUse`, `PostToolUse`) that enforce mechanical rules deterministically at zero AI context cost. They catch what needs no reasoning to verify: typos in paths, writes to protected locations, a skipped pre-commit check. Elsewhere: pre-commit hooks, CI guards, file-write linters.

### Filling the layers with a toolkit

Layers are independent slots — a project can fill some and leave others empty. A minimal project fills 1, 2 and 6. A project running a developed toolkit fills all six.

This repository names [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) (CE) as the canonical realization of Layers 2–5, because it exists, works, and is in use — not because it is mandatory. Adopters can fill those layers with another toolkit, with hand-rolled implementations, or with the vendor-neutral baselines above.

**What CE puts in each slot — skills, personas, reference subtrees, artifact paths — lives in [`process/compound-engineering-integration.md`](../../process/compound-engineering-integration.md), not here.** That document is verified against a stated CE version and carries the re-verification discipline. Keeping CE's inventory in one place means an upstream release invalidates one document rather than several.

## How the layers compose

Pipelines are composed at Layer 2 — a sequence of skill invocations carrying an artifact from discovery to compound output. A toolkit names these stages its own way; the shape is what the architecture fixes:

```
discovery ──▶ planning ──▶ execution ──▶ refinement ──▶ review ──▶ compounding
                  │            │              │            │
                  ▼            ▼              ▼            ▼
               Layer 4      Layer 4        Layer 3      Layer 3
             references   references      personas     personas
                                              │            │
                                              └────────────┴─▶  Layer 5
                                                                compound output
```

Each Layer 2 skill may dispatch Layer 3 personas (for review-shaped skills), load Layer 4 references as depth grows, and produce Layer 5 output when the work yields a durable learning. Layer 1 rules direct default behavior throughout; Layer 6 hooks enforce mechanical invariants at the shell boundary.

## Design principles

- **Context is expensive — load only what's needed, when it's needed.** Each layer specializes a distinct context-cost discipline. Layer 1 stays compact because it is always loaded; Layer 2 is lazy at invocation; Layer 4 is lazy *within* invocation; Layer 6 is free at the shell boundary.
- **Standards are enforced, not just referenced.** Layer 6 catches mechanical violations, Layer 3 catches conceptual ones, Layer 1 directs the default discipline. Together they convert standards from documentation into behavior.
- **Templates over copies.** Vendor-neutral skills reference standards by URL; agents point at standards docs. No duplicated content to keep in sync.
- **Describe structure here, inventory elsewhere.** This document defines what each layer *is*. Anything owned by an upstream project — names, counts, paths — belongs in the integration doc that tracks it against a version.

## Getting started

### In this repository

The Layer 1 rule files in [`rules/`](./rules/) load automatically when working here, directing AI tools at the standards in `process/` and `code/`. The Layer 6 example hooks in [`templates/.claude/hooks/`](../../templates/.claude/hooks/) are not active by default; they exist as templates for adopters.

### In a new project

1. Copy [`templates/.claude/`](../../templates/.claude/) into your project root as `.claude/` — baselines for Layers 2, 3 and 6, plus configuration.
2. Copy [`templates/CLAUDE.md`](../../templates/CLAUDE.md) to your project root and fill in the project-specific sections — that file is the project's Layer 1. The rule files in [`rules/`](./rules/) are this repository's own Layer 1 and are not copied; they are what to draw on when filling it in.
3. Customize hooks, skills and agents for your project's architecture.
4. To adopt compound-engineering for Layers 2–5, install the plugin and follow [`process/compound-engineering-integration.md`](../../process/compound-engineering-integration.md) for path mappings, branch naming and review discipline. Layers 1 and 6 stay owned by your project: Layer 1 as its root `CLAUDE.md`, Layer 6 as its `.claude/hooks/`.

## Where things live

| Document | Owns |
|----------|------|
| [ADR-0001](../../docs/engineering/adr/0001-six-layer-ai-architecture.md) | The architectural decision and the reasoning behind six layers |
| This document | Layer definitions, principles, and how the layers compose |
| [`process/compound-engineering-integration.md`](../../process/compound-engineering-integration.md) | Everything CE-specific: skill mappings, artifact paths, review discipline, version tracking |
| [`ai/CLAUDE.md`](../CLAUDE.md) | Quick-reference standards guide for AI tools working in this repository |
| [`templates/.claude/`](../../templates/.claude/) | The vendor-neutral baselines themselves |
