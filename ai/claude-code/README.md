# AI Architecture

This directory describes the **AI architecture** for projects following these standards: a six-layer model that organizes AI tooling by context cost and invocation pattern.

The architecture is the **abstraction**. Specific toolkits — most concretely [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) (CE) for [Claude Code](https://claude.ai/code) — fill the layers as **canonical realizations**. Vendor-neutral baselines live in this repository for projects that do not adopt a specific toolkit; the layering itself preserves vendor-neutrality.

Architectural decision: [ADR-0001](../../docs/engineering/adr/0001-six-layer-ai-architecture.md). Operational reference for CE adoption: [`process/compound-engineering-integration.md`](../../process/compound-engineering-integration.md).

## The Six Layers

Each layer specializes a distinct **principle** for how AI capability composes with engineering work. The layers are independent slots: a project can fill some and leave others empty.

### Layer 1 — Rules

**Principle: persistence.** Load once per session, every session.

Compact pointers and behavioral guardrails kept in agent context every turn. Layer 1 files load at session start and remain visible across all work. Their discipline is to stay *small* (under ~150 lines each) so the always-loaded budget stays affordable. Layer 1 typically directs the agent to the rest of the architecture rather than encoding policy inline.

| | |
|---|---|
| **Vendor-neutral baseline** | [`ai/claude-code/rules/*.md`](./rules/) (this repo) — engineering-standards pointers, SDLC behavioral guardrails |
| **CE realization** | Not provided by CE; the standards repo retains ownership of Layer 1 |
| **Other realizations** | `AGENTS.md`, project-root `CLAUDE.md`, IDE rule files |

### Layer 2 — Workflow Skills

**Principle: composability.** Multi-step orchestrators that compose into pipelines.

Skills are slash-commands or invocable workflows that orchestrate multi-step processes. They compose into pipelines: discovery → planning → execution → review → compounding. A Layer 2 skill is *lazy-loaded* (its content enters context only when invoked), but implementations vary in depth — a vendor-neutral skill may be a thin URL-fetch template; a deeper realization may run multi-round workflows that dispatch Layer 3 personas and load Layer 4 references during execution. Both fit Layer 2.

| | |
|---|---|
| **Vendor-neutral baseline** | [`templates/.claude/skills/{spec,plan,review}/`](../../templates/.claude/skills/) — three thin URL-fetch skills that work in any project |
| **CE realization** | ~30 skills: `/ce-brainstorm`, `/ce-plan`, `/ce-work`, `/ce-doc-review`, `/ce-code-review`, `/ce-debug`, `/ce-compound`, `lfg`, … |
| **Other realizations** | Cursor commands, Aider commands, hand-rolled slash commands |

### Layer 3 — Persona Agents

**Principle: perspective.** Multiple expertises analyze the same artifact.

Agents are subagent prompt templates that encode focused domain expertise — security, performance, coherence, framework-specific style, language-specific idioms, and so on. Persona Agents are **typically dispatched by Layer 2 skills** (one orchestrator skill fans out to many personas in parallel), though simple realizations may include standalone-invocable agents. The pattern of "one skill orchestrates many personas in parallel" is what makes multi-perspective review tractable at scale.

| | |
|---|---|
| **Vendor-neutral baseline** | [`templates/.claude/agents/{code-reviewer,spec-writer}.md`](../../templates/.claude/agents/) — two standalone-invocable agents |
| **CE realization** | ~20 persona reviewers: coherence, feasibility, adversarial, security-lens, scope-guardian, kieran-rails, dhh-rails-style, julik-frontend-races, kieran-typescript, kieran-python, performance, reliability, … |
| **Other realizations** | Hand-rolled subagent prompts, expertise-encoded templates |

### Layer 4 — References

**Principle: progressivity.** Context grows as workflow depth grows.

References are documents *loaded by skills during execution* — not at session start (Layer 1), not at invocation (Layer 2's initial bundle), but as workflow depth grows. References allow a Layer 2 skill to remain lean at the entry point while still being able to reach for deeper context when a particular workflow branch demands it.

| | |
|---|---|
| **Vendor-neutral baseline** | (none yet — pattern surfaced by CE; the architecture names the layer in anticipation of vendor-neutral implementations) |
| **CE realization** | CE skills' `references/*.md` subtrees, e.g., `ce-plan/references/{plan-handoff,deepening-workflow,visual-communication,universal-planning}.md` |
| **Other realizations** | Any progressive-loading reference pattern; Anthropic's [`Skill`](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) framework supports this idiomatically |

### Layer 5 — Compound / Learnings

**Principle: compounding.** Institutional knowledge accumulates across work.

Outcomes captured from completed work that feed forward into future work — closing the loop between execution and accumulated knowledge. Layer 5 artifacts include solution documents, retrospective notes, and post-mortem records. The principle is that work *compounds*: the second similar task should be cheaper and higher-quality than the first because the first's learnings are captured and findable.

| | |
|---|---|
| **Vendor-neutral baseline** | (none yet — pattern surfaced by CE) |
| **CE realization** | `docs/solutions/` populated by `ce-compound` (capture) and `ce-compound-refresh` (audit and consolidate) |
| **Other realizations** | Hand-rolled learning docs, retrospective archives, post-mortem repositories, ADR series for architectural learnings |

### Layer 6 — Hooks

**Principle: determinism.** Non-AI enforcement at zero context cost.

Shell-level scripts that run automatically on tool-use events (`PreToolUse`, `PostToolUse`). Hooks enforce mechanical rules deterministically and consume zero AI context. They catch the kinds of mistakes (typos in file paths, write attempts to protected paths, missing pre-commit checks) that don't need AI reasoning to verify.

| | |
|---|---|
| **Vendor-neutral baseline** | [`templates/.claude/hooks/`](../../templates/.claude/hooks/) — example pre/post-tool-use scripts |
| **CE realization** | Not provided by CE; the standards repo retains ownership of Layer 6 |
| **Other realizations** | Pre-commit hooks, CI guards, file-write linters, audit logs |

## How the Layers Compose

Layers are independent slots. A typical CE-using project fills all six. A minimal project might fill only Layers 1, 2, and 6.

Pipelines are composed at Layer 2 — a sequence of skill invocations that carries an artifact from discovery to compound output:

```
brainstorm  ──▶  plan  ──▶  work  ──▶  doc-review  ──▶  code-review  ──▶  compound
                  │           │             │                 │
                  ▼           ▼             ▼                 ▼
              (Layer 4   Layer 4       Layer 3            Layer 3
              references) references)   personas          personas
                                            │                 │
                                            └─────────────────┴─▶  Layer 5
                                                                    compound output
```

Each Layer 2 skill in the pipeline may dispatch Layer 3 personas (for review-shaped skills), load Layer 4 references (as workflow depth grows), and produce Layer 5 compound output (as learnings worth preserving). Layer 1 rules direct default behavior across all of the above; Layer 6 hooks enforce mechanical invariants at the shell boundary.

## Design Principles

- **Context is expensive — only load what's needed, when it's needed.** Each layer specializes a distinct context-cost discipline. Layer 1 stays compact because it is always loaded; Layer 2 is lazy at invocation; Layer 4 is lazy *within* invocation; Layer 6 is zero-cost at the shell boundary.
- **Standards are enforced, not just referenced.** Layer 6 hooks catch mechanical violations. Layer 3 personas catch conceptual ones. Layer 1 rules direct the default discipline. Together the layers convert standards from documentation into operational behavior.
- **Templates over copies.** Vendor-neutral skills (Layer 2) reference standards via URL; agents (Layer 3) point at standards docs. No content duplication to keep in sync.
- **Projects customize, templates provide structure.** The template layer (`templates/.claude/`) gives a starting point; each project extends it. Adopting CE is one such extension.

## How to Use

### For this repository

The Layer 1 rule files in [`rules/`](./rules/) are loaded automatically when working in this repo. They direct AI tools at the standards in `process/` and `code/`. The Layer 6 example hooks in [`../../templates/.claude/hooks/`](../../templates/.claude/hooks/) are not active in this repo by default; they exist as templates for adopters.

### For new projects

1. Copy [`templates/.claude/`](../../templates/.claude/) into your project root as `.claude/` — provides Layers 2 (skills), 3 (agents), 6 (hooks) baselines plus configuration.
2. Copy [`templates/CLAUDE.md`](../../templates/CLAUDE.md) to your project root and fill in the project-specific sections.
3. If you adopt compound-engineering, install the plugin and consult [`process/compound-engineering-integration.md`](../../process/compound-engineering-integration.md) for the operational details (path mappings, branch-naming, AI-review discipline). CE specializes Layers 2, 3, 4, and 5 with deep implementations when present; Layers 1 and 6 remain owned by your project's `.claude/`.
4. Customize hooks, skills, agents, and settings for your project's architecture.

## See Also

- [ADR-0001: Six-Layer AI Architecture](../../docs/engineering/adr/0001-six-layer-ai-architecture.md) — the architectural decision
- [`process/compound-engineering-integration.md`](../../process/compound-engineering-integration.md) — operational reference for CE adoption
- [`ai/CLAUDE.md`](../CLAUDE.md) — quick-reference engineering-standards guide for AI tools
