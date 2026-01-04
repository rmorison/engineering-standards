# Engineering Standards Reference

**For AI Assistants** - Quick reference to engineering standards and workflows.

**Usage Note**: This file serves as both documentation for this repository and a template for projects following these standards. Copy and adapt the "Project-Specific Context" section for your project.

---

## Core Principles

**Spec-Driven Development**: Write specifications before code. Specs clarify intent, enable validation, and serve as source of truth.

**Lightweight Process**: Use judgment. Trivial changes need less process; major features benefit from full workflow.

**GitHub-Native**: Use built-in features (issues, sub-issues, labels, milestones, PRs) over external tools.

**Iterative Delivery**: Ship small increments frequently. Validate early. Learn and iterate.

---

## Quick Reference

### Feature Development Workflow
1. **Product Concept** → `docs/product/concepts/{feature}.md`
2. **Requirements & Design** → `docs/product/features/{feature}.md`
3. **Project Planning** → Break into issues with point estimates
4. **Technical Design** → `docs/engineering/design/{feature}.md` or ADR
5. **Implementation** → Code that implements the spec
6. **Validation** → Verify against acceptance criteria

📄 [Full workflow](../process/feature-development-workflow.md) | [Planning standards](../process/project-planning-standards.md)

### Issue Organization
- **Milestones**: Initiatives/releases (e.g., `v2.0-api-redesign`)
- **Epics**: `[EPIC] Feature Theme` with sub-issues, labels: `epic`, `epic-{slug}`
- **Implementation Issues**: Point estimates (`points-1` to `points-13`), epic label

📄 [Issue tracking details](../process/issue-tracking.md)

### Branching & Commits
- **Branch naming**: `{issue-number}-{slugified-title}` (use GitHub's auto-generated names)
- **Commit format**: `type(scope): description` (conventional commits)
- **Main branch**: Always deployable, all work via PRs
- **Versioning**: Semantic versioning (vMAJOR.MINOR.PATCH)

📄 [Git branching strategy](../process/git-branching-strategy.md)

### Common Labels
- **Category**: `enhancement`, `bug`, `tech-debt`, `documentation`, `testing`
- **Epic**: `epic`, `epic-{theme-slug}`
- **Status**: `blocked`
- **Points**: `points-1`, `points-2`, `points-3`, `points-5`, `points-8`, `points-13` (Fibonacci, 2 pts ≈ 1 day)

### Documentation Structure
```
docs/
├── product/
│   ├── strategic-vision.md
│   ├── concepts/{feature}.md
│   └── features/{feature}.md
└── engineering/
    ├── design/{feature}.md
    └── adr/{number}-{title}.md
```

📄 [Documentation standards](../process/documentation-standards.md)

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

## Quick Links

- [Documentation Standards](../process/documentation-standards.md)
- [Feature Development Workflow](../process/feature-development-workflow.md)
- [Project Planning Standards](../process/project-planning-standards.md)
- [Technical Work Workflow](../process/technical-work-workflow.md)
- [Git Branching Strategy](../process/git-branching-strategy.md)
- [Issue Tracking and Epic Organization](../process/issue-tracking.md)

---

**Questions?** Open an issue or PR in the [engineering-standards](https://github.com/rmorison/engineering-standards) repository.
