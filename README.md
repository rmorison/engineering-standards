# Engineering Standards

Lightweight development practices and standards for software projects.

## Purpose

This repository defines engineering standards for building software. The standards are intentionally lightweight to support early-stage agile development while providing enough structure to maintain quality and enable effective collaboration—both human-to-human and human-to-AI.

## Repository Structure

- **[process/](./process/)** - Software process and SDLC standards (workflows, git, planning, documentation)
- **[code/](./code/)** - Language and stack-specific code quality standards ([Python](./code/python-standards.md), [Database](./code/database-standards.md), [Web Application](./code/web-application-standards.md))
- **[ai/](./ai/)** - AI assistant configuration and Claude Code integration ([details](./ai/claude-code/README.md))
- **[templates/](./templates/)** - Project starter kit with Claude Code configuration (`.claude/` directory template)
- **[agent-transcripts/](./agent-transcripts/)** - Historical development logs

## Process Standards

### [Documentation Standards](./process/documentation-standards.md)

Defines how and when to create documentation:
- Repository structure (`docs/` directory organization)
- File naming conventions
- Documentation types (product specs, technical designs, ADRs)
- Best practices for spec-driven development
- Markdown formatting and diagram tools

**Key principle**: Documentation is the source of truth. Write specs before code, keep them current, focus on decisions and context rather than implementation details.

### [Feature Development Workflow](./process/feature-development-workflow.md)

Defines the process for product/business-driven feature work from concept to production:
1. **Product Concept** - Articulate the problem and opportunity
2. **Product Requirements & UI Design** - Define what to build
3. **Project Planning & Sequencing** - Break work into implementable increments
4. **Technical Design & Architecture** - Specify how to implement
5. **Implementation** - Write code that implements the spec
6. **Validation & Iteration** - Verify and improve

**Key principle**: Intent → Spec → Plan → Execute → Validate. Small scoped changes, continuous validation, spec-driven development.

### [Project Planning Standards](./process/project-planning-standards.md)

Detailed guidance for Phase 3 of the feature development workflow:
- **Story point estimation** - Fibonacci scale (1-13), baseline 2 points = ~1 day
- **Task breakdown** - Decomposition strategies and patterns
- **Sequencing and dependencies** - Critical path, parallel tracks, dependency mapping
- **Risk identification** - Common risks and mitigation strategies

Project management as a discipline deserves its own detailed standard while keeping the feature development workflow lightweight.

### [Technical Work Workflow](./process/technical-work-workflow.md)

Engineering-driven work separate from product features:
- **Bug fixes** - Classification, triage, investigation documentation
- **Technical debt** - Proposals, justification, prioritization
- **Infrastructure and tooling** - Specifications, operational requirements
- **Security fixes** - Handling by severity, documentation requirements

**Key distinction**: Feature work is driven by product/business stakeholders; technical work is driven by engineering directives and engineers directly.

### [Git Branching Strategy](./process/git-branching-strategy.md)

Branch management and version control workflow:
- **GitHub Flow** - Simple branch-based workflow with `main` + feature branches
- **Issue-based branching** - Use GitHub's auto-generated branch names from issues
- **Commit conventions** - Clear, conventional commit message format
- **Pull request guidelines** - Size, description, and review practices
- **Release versioning** - Semantic versioning and tagging

**Key principle**: `main` is always deployable. All work happens in issue-based feature branches merged via pull requests.

### [Issue Tracking and Epic Organization](./process/issue-tracking.md)

How to organize issues, track epics, and manage multi-issue initiatives in GitHub:
- **Three-tier hierarchy** - Milestones (initiatives), epics (feature themes), implementation issues
- **Epic structure** - Native GitHub sub-issues with automatic progress tracking
- **Label strategy** - Category, epic, milestone, estimation, and status labels
- **Epic lifecycle** - Creating, amending, closing, and cancelling epics
- **Cross-epic dependencies** - Documenting and handling blocking relationships

**Key principle**: Use GitHub's native features (sub-issues, labels, milestones) for lightweight, scalable issue organization without external tools.

### [Compound Engineering Integration](./process/compound-engineering-integration.md)

Operational reference for adopting [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) (CE) as the canonical realization of Layers 2–5 of the [six-layer AI architecture](./ai/claude-code/README.md). Covers artifact path mapping, ticket-tracking modes (team-scale and solo + AI), branch-naming reconciliation, AI-review discipline, and the CE skill ↔ standards doc cross-reference. Self-contained — usable by any adopter without rmorison context.

**Key principle**: The architecture is the abstraction; CE is one canonical realization. Vendor-neutral baselines remain in place for projects that don't adopt the plugin.

### [Agent Transcripts](./agent-transcripts/)

Conversation logs documenting the development and evolution of these standards through AI agent collaboration.

**What's included:**
- Decision-making processes and rationale
- Design alternatives considered
- Lessons learned during development
- Questions addressed and resolved

These transcripts provide historical context and reasoning behind the standards, useful for understanding why certain approaches were chosen and how to adapt them appropriately.

## AI / Claude Code Integration

### [Six-Layer AI Architecture](./ai/claude-code/README.md)

Defines how AI tooling integrates with software engineering workflows. The architecture is the **abstraction**; specific toolkits — most concretely [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) (CE) for [Claude Code](https://claude.ai/code) — fill the layers as **canonical realizations**. Vendor-neutral baselines live in this repository for projects that don't adopt a specific toolkit.

| # | Layer | Principle | Vendor-neutral baseline | Canonical realization (CE) |
|---|-------|-----------|-------------------------|----------------------------|
| 1 | **Rules** | Persistence — always-loaded session context | `ai/claude-code/rules/` | *(not provided by CE)* |
| 2 | **Workflow Skills** | Composability — multi-step orchestrators | `templates/.claude/skills/` | `/ce-brainstorm`, `/ce-plan`, `/ce-work`, `/ce-doc-review`, `/ce-code-review`, `/ce-debug`, `/ce-compound`, `lfg`, … |
| 3 | **Persona Agents** | Perspective — multiple expertises | `templates/.claude/agents/` | ~20 CE persona reviewers (coherence, feasibility, adversarial, security, …) |
| 4 | **References** | Progressivity — context grows with workflow depth | *(none yet)* | CE skills' `references/*.md` subtrees |
| 5 | **Compound / Learnings** | Compounding — institutional knowledge accumulates | *(none yet)* | `docs/solutions/`, `ce-compound`, `ce-compound-refresh` |
| 6 | **Hooks** | Determinism — non-AI enforcement at zero context cost | `templates/.claude/hooks/` | *(not provided by CE)* |

**Key principle**: Context is expensive — only load what's needed, when it's needed. The six layers each specialize this principle for a different context-cost slot.

For the architectural decision and full layer descriptions, see [ADR-0001](./docs/engineering/adr/0001-six-layer-ai-architecture.md) and [`ai/claude-code/README.md`](./ai/claude-code/README.md). For CE adoption operational details, see [`process/compound-engineering-integration.md`](./process/compound-engineering-integration.md).

### [Project Templates](./templates/)

Starter kit for adopting these standards in new projects with Claude Code:

1. Copy `templates/.claude/` into your project root as `.claude/` — provides Layers 2 (skills), 3 (agents), 6 (hooks) baselines plus configuration.
2. Copy `templates/CLAUDE.md` to your project root and fill in the placeholder sections.
3. If you adopt compound-engineering, install the plugin and consult [`process/compound-engineering-integration.md`](./process/compound-engineering-integration.md) for the operational details. CE specializes Layers 2, 3, 4, and 5 with deep implementations; Layers 1 and 6 stay owned by your project's `.claude/`.
4. Customize hooks, skills, agents, and settings for your project's architecture.

The vendor-neutral skills reference the canonical standards via URL, so they stay in sync without duplication.

## Philosophy

### Lightweight, Not Heavyweight

These standards prioritize working software over process compliance. Use judgment:
- For trivial changes: A good PR description may be sufficient
- For experiments: A brief experiment doc beats formal specs
- For major features: Follow the full workflow to avoid rework

### Spec-Driven Development

Write specifications before code. Specs:
- Clarify intent and surface questions early
- Enable AI-assisted development with clear context
- Serve as contracts for testing and validation
- Document decisions for future reference

The spec is source of truth. Code implements the spec.

### Agile and Iterative

Ship small increments frequently. Validate early. Learn from users. Iterate based on feedback. Don't over-engineer for hypothetical future requirements.

### AI-Native Workflow

Modern development increasingly involves AI coding assistants. These standards work well with AI:
- Clear specs give AI better context
- Small scopes reduce AI errors
- Validation catches AI-generated bugs
- Iteration is cheaper with AI assistance

## Applying These Standards

### For New Projects

1. Create `docs/` directory with `product/` and `engineering/` subdirectories
2. Write a strategic vision in `docs/product/strategic-vision.md`
3. Add architecture decisions to `docs/engineering/adr/` as you make them
4. Follow the feature development workflow for new features
5. If adopting compound-engineering, see [`process/compound-engineering-integration.md`](./process/compound-engineering-integration.md) for path mapping (CE adds `docs/brainstorms/`, `docs/plans/`, `docs/solutions/` to the documentation tree) and review discipline.

### For Existing Projects

1. Introduce standards gradually—don't retrofit everything at once
2. Start with ADRs to document new decisions going forward
3. Write specs for next features to validate the approach
4. Update standards based on what works and what doesn't

### When to Deviate

These are standards, not laws. Deviate when:
- The standard adds no value for the situation
- Time constraints require faster iteration
- You have a better approach that you'll document

When deviating intentionally, document why in the commit message or PR description.

## Maintenance

These standards will evolve:
- Propose changes via pull requests
- Update based on lessons learned
- Keep lightweight—resist adding complexity
- Review quarterly for relevance

## Status

**Draft** - These standards are in active development and subject to revision based on practical experience.

## Questions or Feedback

Open an issue or submit a PR to discuss improvements to these standards.
