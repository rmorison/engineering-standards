# Engineering Standards

Lightweight development practices and standards for software projects.

## Purpose

This repository defines engineering standards for building software. The standards are intentionally lightweight to support early-stage agile development while providing enough structure to maintain quality and enable effective collaboration—both human-to-human and human-to-AI.

## Quickstart

Each step is one line here, and its link holds the detail.

### New Project

1. **Starter kit.** Copy `templates/.claude/` and `templates/CLAUDE.md` into the project root, then fill `CLAUDE.md` in: [Project Templates](#project-templates). The `SECURITY.md`, `CONTRIBUTING.md` and `.github/` skeletons are optional: [Repository baseline files](./templates/README.md#repository-baseline-files).
2. **Docs tree.** Create `docs/product/` and `docs/engineering/adr/`, and write a strategic vision in `docs/product/strategic-vision.md`: [Documentation Standards](./process/documentation-standards.md#directory-structure).
3. **Leak gate in CI.** Copy the files listed in [Adopting the Gate](./process/repository-standards.md#adopting-the-gate), `.github/workflows/leaks.yml` included.
4. **Leak gate on each machine.** From the project root, install the pinned gitleaks:

   ```bash
   sh scripts/install-gitleaks.sh
   ```

   Then add the commit-time and push-time hooks from [Running It Locally](./process/repository-standards.md#running-it-locally).
5. **Agent-session hooks**, if agents work on the project. Once per OS account, from the default branch's checkout of this repository, copy the leak hook and the policy hook:

   ```bash
   mkdir -p ~/.claude/hooks && install -m 755 scripts/claude_leak_hook.py scripts/claude_policy_hook.py ~/.claude/hooks/
   ```

   Then register both in `~/.claude/settings.json`: [Guarding Agent Sessions](./process/repository-standards.md#guarding-agent-sessions) and [Guarding Repository Authority](./process/repository-standards.md#guarding-repository-authority).
6. **Pull requests.** Branch from issues, use conventional commits, and open every pull request description with At a glance: [PR Description](./process/git-branching-strategy.md#pr-description).
7. **Feature work.** Follow the [Feature Development Workflow](#feature-development-workflow). If you adopt compound-engineering, see [`process/compound-engineering-integration.md`](./process/compound-engineering-integration.md) for its paths (`docs/plans/`, `docs/solutions/`, `docs/ideation/`) and review discipline.
8. **Run an agent team** (optional). Add the adoption line to `CLAUDE.md` or `AGENTS.md`, and start a lead with the opening prompt: [Starting a team](./process/agent-team-workflow.md#starting-a-team). Steps 5 and 6 are its prerequisites.

### Existing Project

Each step stands alone, so adopt one at a time, in this order. Don't retrofit everything at once.

1. **Pull requests.** Open every pull request description with At a glance: [PR Description](./process/git-branching-strategy.md#pr-description). It changes no files; to back out, stop.
2. **Agent-session hooks.** Run the copy command in new-project step 5 and register both hooks. They change only the account's `~/.claude/`, never the repository; to back out, remove their entries from `~/.claude/settings.json`.
3. **Leak gate in CI.** Copy the files as in new-project step 3, install gitleaks with new-project step 4's command, and scan the existing history once before the first push. CI scans the whole tree, and this also finds what earlier commits already published:

   ```bash
   sh scripts/leak-gate.sh history
   ```

   Fix what it finds: [When a Leak Is Found](./process/repository-standards.md#when-a-leak-is-found). The step adds the copied files and a workflow; to back out, delete them.
4. **Leak gate on each machine.** Add the commit-time and push-time hooks from [Running It Locally](./process/repository-standards.md#running-it-locally), or its pre-commit framework entries if the project already uses that framework. To back out, delete the hook files or the entries.
5. **Starter kit.** Merge `templates/.claude/` and `templates/CLAUDE.md` into the project's own rather than overwriting them: [Project Templates](#project-templates). To back out, revert the commit.
6. **Docs, going forward.** Record new decisions as ADRs, and write specs for the next features to validate the approach: [Documentation Standards](./process/documentation-standards.md). Update the standards based on what works.
7. **Run an agent team** (optional), as in new-project step 8. To stop, remove the adoption line and archive the lead.

## Repository Structure

- **[process/](./process/)** - Software process and SDLC standards (workflows, git, planning, documentation)
- **[code/](./code/)** - Language and stack-specific code quality standards ([Python](./code/python-standards.md), [Database](./code/database-standards.md), [Web Application](./code/web-application-standards.md))
- **[ai/](./ai/)** - AI assistant configuration and Claude Code integration ([details](./ai/claude-code/README.md))
- **[templates/](./templates/)** - Project starter kit with Claude Code configuration (`.claude/` directory template)
- **[agent-transcripts/](./agent-transcripts/)** - Historical development logs
- **[scripts/](./scripts/)** - Documentation checks and the leak gate, run in CI ([how to run them locally](./process/documentation-standards.md#automated-checks))
- **[SECURITY.md](./SECURITY.md)** and **[CONTRIBUTING.md](./CONTRIBUTING.md)** - How to report a vulnerability privately, and how to contribute

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
- **Label strategy** - One table defining every label, tagged by the scale and toolchain it applies to
- **Epic lifecycle** - Creating, amending, closing, and cancelling epics
- **Cross-epic dependencies** - Documenting and handling blocking relationships

**Key principle**: Use GitHub's native features (sub-issues, labels, milestones) for lightweight, scalable issue organization without external tools.

### [Repository Baseline Standards](./process/repository-standards.md)

What every repository needs besides its code, public or private:
- **Triggers** - Each item applies when the repository is public, takes outside contributions, or ships code others use, and is required or recommended under that trigger
- **License, SECURITY.md, CONTRIBUTING.md, templates** - What each must contain, including private vulnerability reporting and DCO as an option
- **Leak gate** - gitleaks with committed credential and shape rules in CI, and private value rules that run only on a maintainer's machine
- **Going public** - Sweeping history before a private repository changes visibility

**Key principle**: Start from the smallest required set, and say plainly what each check cannot see.

### [Compound Engineering Integration](./process/compound-engineering-integration.md)

Operational reference for adopting [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) (CE) as the canonical realization of Layers 2–5 of the [six-layer AI architecture](./ai/claude-code/README.md). Covers artifact path mapping, ticket-tracking modes (team-scale and solo + AI), branch-naming reconciliation, AI-review discipline, and the CE skill ↔ standards doc cross-reference. Self-contained — usable by any adopter without rmorison context.

**Key principle**: The architecture is the abstraction; CE is one canonical realization. Vendor-neutral baselines remain in place for projects that don't adopt the plugin.

### [Agent Team Workflow](./process/agent-team-workflow.md)

An opt-in operating model for one human directing several AI agent sessions: the operator signs off and merges, a lead coordinates, and one worker runs each ticket. Covers roles, the sprint loop, traffic between parallel tickets, a worker handoff template, the lead's Done-gate checklist, operator interaction (quiet mode), and how to adopt or decline it.

To start one, see [Quickstart](#quickstart).

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

| # | Layer | Principle | Vendor-neutral baseline |
|---|-------|-----------|-------------------------|
| 1 | **Rules** | Persistence — always-loaded session context | `ai/claude-code/rules/` (this repo); `templates/CLAUDE.md` (an adopter's) |
| 2 | **Workflow Skills** | Composability — multi-step orchestrators | `templates/.claude/skills/` |
| 3 | **Persona Agents** | Perspective — multiple expertises | `templates/.claude/agents/` |
| 4 | **References** | Progressivity — context grows with workflow depth | *(none yet)* |
| 5 | **Compound / Learnings** | Compounding — institutional knowledge accumulates | *(none yet)* |
| 6 | **Hooks** | Determinism — non-AI enforcement at zero context cost | `templates/.claude/hooks/` |

CE fills Layers 2–5. What it puts in each slot — skills, personas, reference subtrees, artifact paths — lives in [`process/compound-engineering-integration.md`](./process/compound-engineering-integration.md), which tracks it against a stated CE version. Layers 1 and 6 stay owned by your project: Layer 1 as its root `CLAUDE.md`, Layer 6 as its `.claude/hooks/`.

**Key principle**: Context is expensive — only load what's needed, when it's needed. The six layers each specialize this principle for a different context-cost slot.

For the architectural decision and full layer descriptions, see [ADR-0001](./docs/engineering/adr/0001-six-layer-ai-architecture.md) and [`ai/claude-code/README.md`](./ai/claude-code/README.md). For CE adoption operational details, see [`process/compound-engineering-integration.md`](./process/compound-engineering-integration.md).

### [Project Templates](./templates/)

Starter kit for adopting these standards in new projects with Claude Code:

1. Copy `templates/.claude/` into your project root as `.claude/` — provides Layers 2 (skills), 3 (agents), 6 (hooks) baselines plus configuration.
2. Copy `templates/CLAUDE.md` to your project root and fill in the placeholder sections — this is the project's Layer 1 (rules). The `ai/claude-code/rules/` baseline in the table above is *this* repository's own Layer 1 and is not copied; draw on it when filling `CLAUDE.md` in.
3. If you adopt compound-engineering, install the plugin and consult [`process/compound-engineering-integration.md`](./process/compound-engineering-integration.md) for the operational details. CE specializes Layers 2, 3, 4, and 5 with deep implementations; Layers 1 and 6 stay owned by your project — Layer 1 as its root `CLAUDE.md`, Layer 6 as its `.claude/hooks/`.
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
