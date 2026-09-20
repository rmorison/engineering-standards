# Issue Tracking and Epic Organization

**Version**: 2.1
**Date**: 2026-09-20
**Status**: Active

**Changes in v2.1**:
- Label Strategy is now the single owner of every label definition, rendered as one table with a Mode column
- Added the priority tier, `spike`, and the CE-mode reactive sub-issue labels
- Marked the team-scale label families, and named `feature`, `refactor` and `experiment` as deliberately not used

**Changes in v2.0**:
- Adopted GitHub's native sub-issue feature for epic tracking
- Added epic lifecycle management and closure process
- Added epic amendment and scope change guidelines
- Added cross-epic dependency handling
- Added epic size guidelines
- Replaced manual task lists with automatic sub-issue tracking

## Overview

This document defines how to organize issues, track epics, and manage multi-issue initiatives in GitHub. It provides a lightweight, scalable approach using GitHub's native features.

> **When compound-engineering is in use**: solo + AI work often runs at a smaller scale than the three-tier hierarchy below assumes. The standard already carries solo carve-outs at the Epic Size Guidelines section (below) — "Fewer than 3 issues: probably doesn't need an epic, just use labels", "<1 month: might not need epic structure". For CE-using solo projects, plan files (`docs/plans/...`) serve as the granular tracker via U-IDs, with reactive sub-issues filed for review residuals, bugs, and Open Question activations. See [`process/compound-engineering-integration.md`](./compound-engineering-integration.md) § 3 for the full ticket-policy pattern.

## Three-Tier Hierarchy

Use a three-tier structure to organize work from high-level initiatives down to specific implementation tasks:

```
Milestone (Initiative)
├── Epic Issue (Feature Theme)
│   ├── Implementation Issue
│   ├── Implementation Issue
│   └── Implementation Issue
└── Epic Issue (Feature Theme)
    └── ...
```

### Tier 1: Initiative (Milestone)

**Purpose**: Group multiple related epics into a release or major deliverable.

**Usage**:
- Multi-month efforts (e.g., `v2.0-api-redesign`)
- Release milestones (e.g., `v1.0-ga`)
- Major phases of work

**Example**:
```bash
gh api repos/owner/repo/milestones \
  -f title="v2.0-api-redesign" \
  -f description="API redesign and performance improvements initiative"
```

### Tier 2: Epic (Tracking Issue)

**Purpose**: Coordinate multiple related implementation issues into a cohesive feature theme.

**Structure**:
- Issue title: `[EPIC] Feature Theme Name`
- Labels: `epic`, plus `epic-{theme-slug}` and the milestone label at team scale (see [Label Strategy](#label-strategy))
- Body: Overview, scope, acceptance criteria, dependencies, notes
- Sub-issues: Use GitHub's native sub-issue feature (automatic progress tracking)

**Example** at team scale, so it carries the theme and milestone labels:
```markdown
Title: [EPIC] Authentication System Overhaul

Labels: epic, epic-auth-system, v2.0-api-redesign
Milestone: v2.0-api-redesign

Body:
## Overview
Redesign authentication system to support OAuth2, JWT tokens, and multi-factor
authentication for improved security and user experience.

## Scope
**In scope**:
- OAuth2 provider integration (Google, GitHub)
- JWT token generation and validation
- Multi-factor authentication (TOTP)
- Session management improvements

**Out of scope**:
- Single sign-on (SSO) integration (deferred to v2.1)
- Biometric authentication

## Sub-Issues
Use the "Create sub-issue" button to add implementation tasks.
GitHub automatically tracks progress (e.g., "5 of 6 completed").

## Acceptance Criteria
- [ ] OAuth2 authentication working with at least 2 providers
- [ ] JWT tokens properly validated on all endpoints
- [ ] MFA enrollment and verification functional
- [ ] All security tests passing
- [ ] Documentation updated

## Dependencies
None

## Technical Notes
- Use industry-standard libraries (avoid custom crypto)
- Ensure backwards compatibility during migration
- Plan for gradual rollout using feature flags

## Estimated Points
18 points (sum of sub-issue estimates)
```

### Tier 3: Implementation Issue

**Purpose**: Discrete, actionable work items that can be completed independently.

**Structure**:
- Standard issue format
- Reference epic in description: `Part of epic #42`
- Labels: a category label, plus the epic and milestone labels at team scale (see [Label Strategy](#label-strategy))
- Point estimate using a `points-` label at team scale. Solo + AI work expresses scope through the plan's U-IDs instead

**Example** at team scale, so it carries the theme, milestone and point labels:
```markdown
Title: Implement JWT token generation and validation

Labels: enhancement, epic-auth-system, v2.0-api-redesign, points-5
Milestone: v2.0-api-redesign

Part of epic #42 (Authentication System Overhaul)

## Description
Implement JWT token generation on login and validation middleware for
protected API endpoints.

## Implementation
- Add JWT library dependency
- Create token generation function (claims: user_id, roles, expiration)
- Create validation middleware
- Add refresh token support
- Update API documentation

## Acceptance Criteria
- Tokens generated on successful login
- Validation middleware rejects invalid/expired tokens
- Refresh token flow working
- Unit tests for generation and validation
```

## Label Strategy

This section is the only place a label is defined. Other documents tell you when to apply a label and link here for its meaning. A label named anywhere in `process/` or `ai/` that is not in this table is a defect in that document, not a label you are missing.

**Reading the Mode column.** Two independent axes decide whether a label is yours: **scale** (team-scale, or solo) and **toolchain** (CE-mode, or standards-only). `both` means create it at any scale in either mode. `team-scale` means the three-tier hierarchy above uses it and solo-scale work skips it, at either toolchain. [`process/compound-engineering-integration.md`](./compound-engineering-integration.md) § 3 prescribes the same skip for CE-mode solo work. `CE-mode` means the label exists only where compound-engineering is in use.

| Label | Meaning | Mode |
|---|---|---|
| `enhancement` | New features or improvements | both |
| `bug` | Bug fixes | both |
| `tech-debt` | Technical debt work, including refactors | both |
| `documentation` | Documentation updates | both |
| `testing` | Test additions or improvements | both |
| `spike` | Timeboxed exploratory work, per [`process/git-branching-strategy.md`](./git-branching-strategy.md#experimental-work) | both |
| `priority:high` | Blocks other work, or a defect in production | both |
| `priority:medium` | Normal scheduling priority | both |
| `priority:low` | Worth doing, under no schedule pressure | both |
| `blocked` | Cannot proceed due to an external dependency | both |
| `epic` | Applied to an epic tracking issue. At solo scale, one umbrella epic per multi-phase plan | both |
| `epic-{theme-slug}` | Applied to the epic and every child issue, for filtering. Lowercase, hyphen-separated, under 30 characters: `epic-auth-system`, `epic-api-redesign` | team-scale |
| `v1.0-ga`, `v2.0-api-redesign` | Milestone labels mirroring the GitHub Milestone that defines an initiative. Create as needed | team-scale |
| `points-1`, `points-2`, `points-3`, `points-5`, `points-8`, `points-13` | Fibonacci estimate where 2 points is roughly 1 day. See [Project Planning Standards](./project-planning-standards.md#story-point-estimation) | team-scale |
| `from-review` | Sub-issue filed for a review residual | CE-mode |
| `from-deferred-q` | Sub-issue filed when an Open Question activates | CE-mode |

**Deliberately not used.** Three labels appear in older guidance and are not part of this set. Use `enhancement` rather than `feature`. Use `tech-debt` rather than `refactor`, which is a commit type rather than an issue label (see [`process/git-branching-strategy.md`](./git-branching-strategy.md#types)). Use `spike` rather than `experiment`.

## Traceability Best Practices

### 1. Bidirectional Linking with Sub-Issues

**In epic issue**: Use GitHub's "Create sub-issue" button
- Automatically creates parent-child relationship
- Epic shows progress: "5 of 6 sub-issues completed"
- Child issues display "Parent: [Epic Name]" badge

**In implementation issue**: Automatically linked when created as sub-issue
- If created separately, add parent relationship via issue sidebar
- Optionally reference epic in description: `Part of epic #42 (Authentication System)`

### 2. Consistent Labeling

This practice is team-scale: it depends on the theme and milestone labels that [Label Strategy](#label-strategy) marks team-scale only. Apply both generic and specific labels for bulk filtering:
- Epic issue: `epic`, `epic-auth-system`, `v2.0-api-redesign`
- Child issues: `enhancement`, `epic-auth-system`, `v2.0-api-redesign`

**Why labels still matter**: Enable bulk queries and backward compatibility until GitHub CLI fully supports sub-issue queries.

### 3. Search Queries

These examples filter on team-scale labels. At solo + AI scale the plan is the granular tracker, so the equivalent query is reading the plan's units.

```bash
# View epic with progress
gh issue view {epic-number}  # Shows "5 of 6 sub-issues completed"

# All issues for specific epic
gh issue list --label epic-auth-system

# All work in milestone
gh issue list --milestone "v2.0-api-redesign"

# All blocked epics
gh issue list --label epic,blocked
```

## Epic Issue Template

Use this template when creating epic issues at team scale. The `epic-{theme-slug}` and milestone labels it carries are team-scale only; see [Label Strategy](#label-strategy).

```markdown
---
Title: [EPIC] {Feature Theme Name}
Labels: epic, epic-{theme-slug}, {milestone-label}
Milestone: {milestone-name}
---

## Overview
<!-- Brief description of the epic and its business value -->

## Scope
**In scope**:
- <!-- What's included -->

**Out of scope**:
- <!-- What's explicitly excluded or deferred -->

## Sub-Issues
<!-- Use the "Create sub-issue" button to add implementation tasks -->
<!-- GitHub will automatically track progress (e.g., "5 of 6 completed") -->

## Acceptance Criteria
<!-- What does "done" look like for this epic? -->
- [ ] Criterion 1
- [ ] Criterion 2

## Dependencies
<!-- Other epics, external factors, or prerequisites -->
<!-- Example: Depends on: #40 (Database Migration Epic) -->
<!-- Example: Blocked by: External API availability -->
None

## Technical Notes
<!-- Architecture decisions, constraints, risks, considerations -->

## Estimated Points
<!-- Sum of sub-issue estimates -->
{N} points
```

## Creating an Epic

1. **Create milestone** (if needed):
   ```bash
   gh api repos/:owner/:repo/milestones \
     -f title="v2.0-api-redesign" \
     -f description="API redesign initiative"
   ```

2. **Create epic-specific label**: `epic-{theme-slug}`, whose format [Label Strategy](#label-strategy) defines. Use it for the epic and all sub-issues

3. **Create epic issue**: Use template above, apply `epic` and `epic-{theme-slug}` labels

4. **Create sub-issues**: Use "Create sub-issue" button in epic issue, or create separately and link via sidebar

**Note**: GitHub CLI doesn't yet support creating sub-issues directly. Use web UI for parent-child linking. Create branches from implementation issues, not epic tracking issues (see [Git Branching Strategy](./git-branching-strategy.md)).

## Epic Lifecycle Management

### Closing an Epic

Close an epic when **ALL** of these conditions are met:

1. ✅ All sub-issues are closed (GitHub shows "N of N completed")
2. ✅ All acceptance criteria are checked off
3. ✅ Any blocking dependencies are resolved
4. ✅ Technical notes confirm no known issues remain
5. ✅ Maintainer approval obtained (for significant epics)

**Process**:
```bash
# 1. Verify all sub-issues complete
gh issue view 42  # Check "N of N sub-issues completed"

# 2. Verify acceptance criteria
# Review epic issue body - all checkboxes should be checked

# 3. Add closure comment
gh issue comment 42 --body "All sub-issues complete and acceptance criteria met. Closing epic."

# 4. Close epic
gh issue close 42
```

**To cancel an epic** (rather than complete): Close with a comment explaining why (e.g., "Requirements changed, superseded by #55").

### Handling Incomplete Sub-Issues

If epic has incomplete sub-issues when closing:
- **No longer needed**: Close sub-issue with explanation of scope change
- **Deferred**: Remove parent relationship, move to new epic or backlog
- **Blocked**: Keep epic open until blocker resolved, document in Dependencies section

### Epic Amendments and Scope Changes

**Adding sub-issues**: Create sub-issue via "Create sub-issue" button, apply epic label, add comment noting scope expansion.

**Removing sub-issues**: Remove parent relationship, close with explanation, update epic's estimated points.

**Splitting epics**: When epic exceeds ~20 sub-issues or has distinct themes, create new epic and move relevant sub-issues. Cross-reference in both epics.

**Merging epics**: When overlap is significant and combined epic <15 sub-issues, move sub-issues to primary epic and close secondary with reference.

### Cross-Epic Dependencies

#### Documenting Dependencies

When Epic A depends on Epic B:

**In Epic A** (the dependent epic):
```markdown
## Dependencies
Depends on: #40 (Database Migration Epic) - requires new schema before implementing data layer
```

**In Epic B** (the blocking epic):
```markdown
## Dependencies
Blocking: #42 (Authentication Epic) - database schema needed before auth can be implemented
```

#### Handling Blocking Dependencies

**If Epic A is blocked by Epic B**:
1. Add `blocked` label to Epic A
2. Document dependency in both epics
3. Prioritize Epic B in sprint/milestone planning

**Querying blocked epics**:
```bash
# Find all blocked epics
gh issue list --label epic,blocked

# Find specific epic's dependencies
gh issue view 42 | grep -A 5 "Dependencies"
```

#### Non-Blocking Dependencies

For informational dependencies (not blockers):
```markdown
## Dependencies
Related to: #48 (Monitoring Epic) - consider alignment on metrics format
See also: #50 (Performance Epic) - may benefit from perf improvements
```

### Epic Size Guidelines

Follow these heuristics for appropriate epic sizing:

**Minimum size**: 3-5 related sub-issues, ~10-20 points
- Fewer than 3 issues: probably doesn't need an epic, just use labels

**Optimal size**: 5-15 sub-issues, 20-60 points
- Manageable scope, clear theme, achievable in 1-2 months

**Maximum size**: 20 sub-issues, ~100 points
- Beyond these limits: consider splitting into multiple epics
- Exception: epics with many small, similar tasks (e.g., "Migrate all API endpoints to v2")

**Duration**: 1-3 months typical
- `<1 month`: might not need epic structure
- `>3 months`: consider splitting to enable incremental delivery

## Why This Approach?

### Advantages

- ✅ **Scalable**: Unlimited epics (unlike milestones, which have ~100 limit)
- ✅ **Automatic Traceability**: Sub-issues create explicit parent-child relationships
- ✅ **Automatic Progress**: GitHub tracks completion (e.g., "5 of 6 completed")
- ✅ **No Manual Sync**: Sub-issue relationships are data-backed, not markdown-based
- ✅ **Flexibility**: Full markdown for context, discussions in comments
- ✅ **Searchable**: Labels enable bulk filtering across epics
- ✅ **Native**: No external tools required, pure GitHub features
- ✅ **Visual Hierarchy**: Parent badges, sub-issue browsing, cross-repo support
- ✅ **API Support**: GraphQL queries for programmatic access

### Rejected Alternatives

**Labels Only**: Too minimal, no context or progress tracking

**Task Lists**: Manual markdown checklists require synchronization and can drift from reality. Sub-issues provide automatic tracking and explicit relationships.

**Milestones for Epics**: Limited quantity (~100 max), best reserved for releases and initiatives

**GitHub Projects**: Adds significant complexity and overhead. Good for teams already using Projects, but overkill for issue-centric workflows.

## References

- **Git Branching Strategy**: Use `{issue-number}-{slugified-title}` branch names (see [`process/git-branching-strategy.md`](./git-branching-strategy.md#feature-branches))
- **Commit Messages**: see [`process/git-branching-strategy.md`](./git-branching-strategy.md#commit-messages), which owns the commit format
- **Project Planning**: See [`process/project-planning-standards.md`](./project-planning-standards.md#story-point-estimation) for estimation guidance
- **GitHub Sub-Issues Documentation**: https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues
- **GitHub Sub-Issues Blog Post**: https://github.blog/engineering/architecture-optimization/introducing-sub-issues-enhancing-issue-management-on-github/
