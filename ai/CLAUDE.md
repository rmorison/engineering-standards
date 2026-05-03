# Engineering Standards Reference

**For AI Assistants** - Quick reference to engineering standards and workflows.

**Usage Note**: This file serves as both documentation for this repository and a template for projects following these standards. Copy and adapt the "Project-Specific Context" section for your project.

## Architecture

This repository follows a **six-layer AI architecture** (see [`ai/claude-code/README.md`](./claude-code/README.md) for the canonical description). The architecture is the abstraction; specific toolkits realize the layers.

- **Layers 1 (Rules) and 6 (Hooks)** are owned by this repository and apply in standards-only mode and CE-mode alike.
- **Layers 2 (Skills) and 3 (Agents)** have vendor-neutral baselines in [`templates/.claude/`](../templates/.claude/) for projects that don't run a specific toolkit. When [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) (CE) is installed, CE skills and persona reviewers are the canonical realization of those layers.
- **Layers 4 (References) and 5 (Compound)** are realized by CE today; non-CE projects may leave them empty or fill them with hand-rolled implementations.

This file holds Layer 1-style quick-reference guidance. Multi-mode rules (standards-mode default and CE-mode addendum) are noted inline below; for the CE-mode operational details, see [`process/compound-engineering-integration.md`](../process/compound-engineering-integration.md). For the architectural decision, see [ADR-0001](../docs/engineering/adr/0001-six-layer-ai-architecture.md).

---

## Core Principles

**Spec-Driven Development**: Write specifications before code. Specs clarify intent, enable validation, and serve as source of truth.

**Lightweight Process**: Use judgment. Trivial changes need less process; major features benefit from full workflow.

**GitHub-Native**: Use built-in features (issues, sub-issues, labels, milestones, PRs) over external tools.

**Iterative Delivery**: Ship small increments frequently. Validate early. Learn and iterate.

---

## Quick Reference

### Feature Development Workflow

**Standards mode** (default — applies to non-CE projects):
1. **Product Concept** → `docs/product/concepts/{feature}.md`
2. **Requirements & Design** → `docs/product/features/{feature}.md`
3. **Project Planning** → Break into issues with point estimates
4. **Technical Design** → `docs/engineering/designs/{feature}.md` or ADR
5. **Implementation** → Code that implements the spec
6. **Validation** → Verify against acceptance criteria

**When CE is in use** (additional Phase 0; CE skill outputs replace standards paths for Phases 3–4):
- **Phase 0 (discovery)** → `docs/brainstorms/{topic}-requirements.md` (output of `/ce-brainstorm`); Phase 1 is seeded from this artifact
- **Phase 3–4 outputs** → `docs/plans/...` (output of `/ce-plan`); subsumes `docs/planning/` for CE-using projects

📄 [Full workflow](../process/feature-development-workflow.md) | [Planning standards](../process/project-planning-standards.md) | [CE integration](../process/compound-engineering-integration.md)

### Issue Organization
- **Milestones**: Initiatives/releases (e.g., `v2.0-api-redesign`)
- **Epics**: `[EPIC] Feature Theme` with sub-issues, labels: `epic`, `epic-{slug}`
- **Implementation Issues**: Point estimates (`points-1` to `points-13`), epic label

📄 [Issue tracking details](../process/issue-tracking.md)

### Branching & Commits
- **Branch naming**:
  - **Standards mode**: `{issue-number}-{slugified-title}` (use GitHub's auto-generated names)
  - **When CE is in use**: also accepts topic-style `feat/...` / `fix/...` for `lfg` and `ce-work` autonomous flows without a parent issue. File an issue retroactively if review surfaces something worth tracking.
- **Commit format**: `type(scope): description` (conventional commits)
- **Main branch**: Always deployable, all work via PRs
- **Versioning**: Semantic versioning (vMAJOR.MINOR.PATCH)

📄 [Git branching strategy](../process/git-branching-strategy.md) | [CE integration](../process/compound-engineering-integration.md)

### Common Labels
- **Category**: `enhancement`, `bug`, `tech-debt`, `documentation`, `testing`
- **Epic**: `epic`, `epic-{theme-slug}`
- **Status**: `blocked`
- **Points**: `points-1`, `points-2`, `points-3`, `points-5`, `points-8`, `points-13` (Fibonacci, 2 pts ≈ 1 day)

### Documentation Structure

**Standards mode** (human-authored content):
```
docs/
├── product/
│   ├── strategic-vision.md
│   ├── concepts/{feature}.md
│   └── features/{feature}.md
└── engineering/
    ├── designs/{feature}.md
    └── adr/{number}-{title}.md
```

**When CE is in use** (CE-skill-produced artifacts; precedence: CE owns when CE produced the file):
```
docs/
├── ideation/      (ce-ideate output)
├── brainstorms/   (ce-brainstorm output — Phase 0 / requirements)
├── plans/         (ce-plan output — subsumes docs/planning/)
└── solutions/     (ce-compound, ce-compound-refresh — Layer 5 artifacts)
```

Both trees coexist. Human-authored ADRs and design docs stay at the standards paths; CE skill outputs land at CE paths. For the precedence rule and provenance clause, see [`process/compound-engineering-integration.md`](../process/compound-engineering-integration.md).

📄 [Documentation standards](../process/documentation-standards.md) | [CE integration](../process/compound-engineering-integration.md)

---

## Technical Work (Non-Feature)

- **Bug fixes**: Classify severity, document investigation
- **Technical debt**: Write proposal, justify ROI
- **Infrastructure**: Spec operational requirements
- **Security**: Handle by severity level

📄 [Technical work workflow](../process/technical-work-workflow.md)

---

## Project-Specific Context

<!-- **Projects using this template**: Customize this section with project-specific information.
     Also update the repository link at the bottom of this file. -->

**Project Name**: Engineering Standards Repository

**Tech Stack**: Markdown documentation

**Key Conventions**:
- Agent transcripts stored in `agent-transcripts/` directory
- Standards evolve through PR discussions
- Keep standards lightweight and practical

**Active Milestones**: None currently

**Important Notes**:
- This repository defines the standards themselves
- Standards are in active development (Draft status)
- Propose changes via pull requests

---

## When to Use What

**Write a spec when**:
- Feature has UI/UX components
- Multiple implementation approaches exist
- Work spans multiple PRs or developers
- Requirements need stakeholder validation

**Skip the spec when**:
- Trivial changes (typo fixes, simple bugs)
- Obvious implementation (clear issue description suffices)
- Experiments (write brief experiment doc instead)

**Create an epic when**:
- 3+ related implementation issues
- Work spans multiple themes or areas
- Progress tracking across issues is valuable

**Write an ADR when**:
- Significant technical decision with alternatives
- Architecture choice that constrains future work
- Third-party tool/library selection

---

## Estimation Scale

| Points | Complexity | Typical Duration |
|--------|------------|------------------|
| 1 | Trivial | Few hours |
| 2 | Simple | ~1 day |
| 3 | Moderate | ~1.5 days |
| 5 | Complex | ~2.5 days |
| 8 | Very complex | ~4 days |
| 13 | Needs breakdown | >5 days (split it) |

Points are for complexity, not hours. Use for planning, not performance measurement.

---

## When using compound-engineering

When the [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) (CE) plugin is installed, CE skills and persona reviewers are the canonical realization of Layers 2 and 3 of the AI architecture (see [`ai/claude-code/README.md`](./claude-code/README.md)). CE-mode addendums:

- **Artifact paths**: CE owns the artifacts it produces (`docs/brainstorms/`, `docs/plans/`, `docs/solutions/`, `docs/ideation/`); standards conventions own human-authored artifacts. Default: first-skill-touched-the-file wins. Override: `provenance:` frontmatter (`ce-plan` or `hand-authored`).
- **Branch naming**: standards' `{issue-number}-{slugified-title}` applies when an issue exists; topic-style `feat/...` / `fix/...` is acceptable for `lfg` / `ce-work` autonomous flows without a parent issue.
- **Phase 0 (discovery)**: `docs/brainstorms/<topic>-requirements.md` from `ce-brainstorm` IS the discovery artifact for the feature workflow; Phase 1 (Product Concept) is seeded from it.
- **AI-review**: `ce-code-review` and `ce-doc-review` provide review **discipline** (not an enforced merge gate). Failure modes the discipline doesn't catch are named in [`process/compound-engineering-integration.md`](../process/compound-engineering-integration.md).

Full operational details: [`process/compound-engineering-integration.md`](../process/compound-engineering-integration.md). Architectural decision: [ADR-0001](../docs/engineering/adr/0001-six-layer-ai-architecture.md).

---

## Quick Links

- [AI Architecture (six-layer model)](./claude-code/README.md)
- [ADR-0001: Six-Layer AI Architecture](../docs/engineering/adr/0001-six-layer-ai-architecture.md)
- [Compound Engineering Integration](../process/compound-engineering-integration.md)
- [Documentation Standards](../process/documentation-standards.md)
- [Feature Development Workflow](../process/feature-development-workflow.md)
- [Project Planning Standards](../process/project-planning-standards.md)
- [Technical Work Workflow](../process/technical-work-workflow.md)
- [Git Branching Strategy](../process/git-branching-strategy.md)
- [Issue Tracking and Epic Organization](../process/issue-tracking.md)

---

**Questions?** Open an issue or PR in the [engineering-standards](https://github.com/rmorison/engineering-standards) repository.
