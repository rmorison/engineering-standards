# Technical Work Workflow

*Process for engineering-driven technical work*

## Overview

This workflow covers work driven by engineering needs rather than product requirements: bug fixes, technical debt reduction, infrastructure improvements, tooling, and security fixes. While the [Feature Development Workflow](./feature-development-workflow.md) covers feature work driven by product stakeholders, technical work is driven by engineering directives and engineers directly.

**Key difference**: Technical work optimizes for system quality, maintainability, performance, and reliability rather than user-facing features.

### Workflow Diagram

The process varies by work type and complexity:

```mermaid
flowchart TD
    Start([Technical Work]) --> Classify{Work Type?}

    Classify -->|Simple Bug<br/>1-2 pts| Bug1[Fix & PR]
    Classify -->|Moderate Bug<br/>3-5 pts| Bug2[Investigation Doc]
    Classify -->|Complex Bug<br/>8+ pts| Bug3[Investigation +<br/>Design Doc]

    Classify -->|Small Refactor<br/>1-5 pts| TD1[Opportunistic<br/>w/ PR notes]
    Classify -->|Large Refactor<br/>8+ pts| TD2[Tech Debt<br/>Proposal]

    Classify -->|Infrastructure<br/>Any size| Infra[Infrastructure<br/>Spec]

    Classify -->|Security<br/>Critical| Sec1[Immediate Fix +<br/>Post-mortem]
    Classify -->|Security<br/>Other| Sec2[Per severity<br/>process]

    Bug2 --> Plan[Planning]
    Bug3 --> Design[Design]
    TD2 --> Plan
    Infra --> Design

    Design --> Plan
    Plan --> Impl[Implementation]
    Bug1 --> Impl
    TD1 --> Impl
    Sec1 --> Impl
    Sec2 --> Impl

    Impl --> Val[Validation]

    style Start fill:#e1e1e1
    style Classify fill:#fff4e1
    style Bug1 fill:#e1ffe1
    style Bug2 fill:#ffe1e1
    style Bug3 fill:#ffe1e1
    style TD1 fill:#e1f5ff
    style TD2 fill:#e1f5ff
    style Infra fill:#f5e1ff
    style Sec1 fill:#ffcccc
    style Sec2 fill:#ffcccc
    style Plan fill:#fff4e1
    style Design fill:#ffe1f5
    style Impl fill:#e1ffe1
    style Val fill:#f5e1ff
```

## Stakeholders and Success Metrics

### Stakeholders
- **Primary**: Engineering team, technical leads, infrastructure owners
- **Secondary**: Product team (impact on delivery), operations (reliability), security (risk)

### Success Metrics
- System performance (latency, throughput, resource utilization)
- Code maintainability (complexity, test coverage, documentation)
- Reliability (uptime, error rates, recovery time)
- Developer productivity (build times, deployment frequency, debugging ease)
- Security posture (vulnerabilities addressed, attack surface reduced)

---

## Bug Fixes

### Bug Classification

Bugs fall into categories that determine the level of process needed:

**Severity Levels:**
- **Critical (P0)**: System down, data loss, security breach - immediate action
- **High (P1)**: Major functionality broken, significant user impact
- **Medium (P2)**: Feature degraded, workaround exists
- **Low (P3)**: Minor issue, cosmetic, edge case

**Complexity Levels:**
- **Simple**: Known cause, obvious fix, single component
- **Moderate**: Investigation needed, multiple components, requires testing
- **Complex**: Unknown cause, architectural issues, cross-system impact

### Process by Type

#### Simple Bugs (1-2 points)
**Process**: Fix and PR, no separate documentation needed

**PR Description must include:**
- **Problem**: What was broken?
- **Root cause**: Why did it happen?
- **Fix**: What changed?
- **Testing**: How was it verified?

**Example:**
```markdown
## Problem
User timezone offset calculation fails for GMT+13

## Root cause
Timezone parser assumes max offset of GMT+12

## Fix
Updated timezone validation to support GMT-12 to GMT+14 range

## Testing
- Added unit test for GMT+13, GMT+14
- Verified existing timezone tests still pass
```

#### Moderate Bugs (3-5 points)
**Process**: Investigation doc + implementation

**Investigation doc** (`docs/engineering/bugs/ISSUE-NNN-title.md`):
- **Symptoms**: What users/systems experience
- **Investigation**: Steps taken, findings, data collected
- **Root cause**: Technical explanation of why this occurs
- **Proposed fix**: Approach to resolve, alternatives considered
- **Risk assessment**: What could go wrong with the fix
- **Testing plan**: How to verify fix and prevent regression

**When to write**: Investigation takes >2 hours or touches multiple components

#### Complex Bugs (8+ points)
**Process**: Full investigation doc + design doc if architectural changes needed

Treat like a small feature - may need:
- Investigation documentation
- Technical design if solution is non-trivial
- ADR if significant decisions are made
- Coordination with affected teams

**Example**: Database query causing production slowdown under certain load patterns may need full performance analysis, query redesign, and migration plan.

### Critical Bug Process (P0)

Speed matters, but documentation still required:

1. **Immediate response**: Fix quickly, ship to production
2. **Post-incident documentation** (within 24-48 hours):
   - Timeline of events
   - Root cause analysis
   - Fix applied
   - Follow-up work needed (tech debt items)
3. **Post-mortem** (within 1 week):
   - What went wrong
   - What went right
   - Action items to prevent recurrence

Document in `docs/engineering/incidents/YYYY-MM-DD-incident-name.md`

---

## Technical Debt

### What Qualifies as Tech Debt?

- **Code quality**: Duplication, complexity, poor structure that slows development
- **Architecture**: Design decisions that no longer fit current needs
- **Testing**: Missing or inadequate test coverage
- **Documentation**: Outdated or missing critical docs
- **Dependencies**: Outdated libraries, deprecated APIs
- **Performance**: Known inefficiencies that impact user experience or costs
- **Security**: Non-critical vulnerabilities, security hardening opportunities

### Tech Debt Proposal

Not all tech debt is worth addressing. Proposals justify the investment.

**Template** (`docs/engineering/tech-debt/proposal-title.md`):

```markdown
# Tech Debt Proposal: [Title]

## Current State
[Describe the problem - what's inefficient, fragile, or holding us back?]

## Business Impact
[Why should we care? What's the cost of NOT fixing this?]
- Development velocity impact
- Operational costs
- Risk exposure
- Team morale / onboarding difficulty

## Proposed Solution
[What would we do to address this?]

## Effort Estimate
[Story points - see breakdown below]

## Benefits
[Quantifiable improvements expected]
- Faster feature development (how much?)
- Reduced incidents (current rate vs expected)
- Cost savings (infrastructure, debugging time)
- Improved metrics (specific performance targets)

## Risks
[What could go wrong? Migration risks? Downtime?]

## Alternatives Considered
[Why not other approaches?]

## Task Breakdown
[Story-pointed tasks per project planning standards]

## Success Criteria
[How do we know it worked?]
```

### Prioritization Factors

Engineering leads prioritize tech debt based on:
- **Pain level**: How much does this slow us down today?
- **Trend**: Getting worse or stable?
- **Risk**: What's the blast radius if this breaks?
- **Enablement**: Does this unblock important features?
- **ROI**: Effort vs benefit ratio

### Small vs Large Tech Debt Work

**Small refactoring (1-5 points)**: Can be tackled opportunistically
- "Boy scout rule": Leave code better than you found it
- Refactor while working on related features
- Brief note in PR description justifying the cleanup

**Large refactoring (8+ points)**: Needs formal proposal
- Competes with feature work for priority
- Requires buy-in from engineering leadership
- Full planning and design docs

---

## Infrastructure and Tooling

### When This Applies

- CI/CD pipeline improvements
- Build system optimization
- Monitoring and observability setup
- Development environment tooling
- Database migrations
- Cloud infrastructure changes
- Performance optimization
- Deployment automation

### Infrastructure Specification

**Template** (`docs/engineering/infrastructure/spec-title.md`):

```markdown
# Infrastructure Spec: [Title]

## Problem
[What's not working well? What capability are we missing?]

## Requirements

### Functional
- What must this infrastructure do?
- What integrations are needed?
- What APIs or interfaces does it expose?

### Non-Functional
- Performance targets (throughput, latency)
- Reliability targets (uptime, recovery time)
- Security requirements
- Cost constraints
- Scalability needs

## Proposed Design
[Architecture, components, data flow, technologies]

## Alternatives Considered
[Other approaches and why not chosen]

## Migration Plan
[If changing existing infrastructure]
- Rollout strategy
- Rollback plan
- Data migration (if applicable)
- Downtime requirements

## Operational Impact
- Monitoring and alerting changes needed
- Runbook updates required
- On-call implications
- Maintenance overhead

## Success Criteria
[How do we measure success?]
- Performance benchmarks
- Reliability metrics
- Cost targets
- Developer productivity improvements

## Task Breakdown
[Story-pointed tasks]
```

### Infrastructure Work Follows Adapted Workflow

1. **Problem Definition** (like Product Concept)
   - What engineering problem are we solving?
   - What's the current pain point?

2. **Requirements & Design** (combines Phase 2 & 4)
   - What does the infrastructure need to do?
   - How will it work technically?

3. **Planning** (Phase 3)
   - Task breakdown, dependencies, story points
   - See [Project Planning Standards](./project-planning-standards.md)

4. **Implementation** (Phase 5)
   - Build, test, validate
   - Infrastructure as code when possible

5. **Validation** (Phase 6)
   - Does it meet performance/reliability targets?
   - Runbooks documented?
   - Team trained on operation?

---

## Security Fixes

### Classification

**Critical Security Issues**: Active exploits, data exposure, authentication bypass
- Immediate fix, may need confidential handling
- Follow Critical Bug Process (P0)
- Security post-mortem required

**High Priority**: Significant vulnerabilities with no known exploit
- Fix within sprint
- Investigation doc for complex issues

**Routine Security Work**: Library updates, hardening, security tech debt
- Plan like tech debt proposals
- May be driven by security audits or compliance

### Security Fix Documentation

**For vulnerabilities:**
- Document in private channel until fixed and deployed
- After deployment, document in `docs/engineering/security/YYYY-MM-vulnerability-name.md`
- Include: vulnerability description, impact, fix, remediation steps

**For security improvements:**
- Use tech debt proposal format
- Justify based on risk reduction
- Include threat model if applicable

---

## Story Point Estimation for Technical Work

Use the same Fibonacci scale (1-13) from [Project Planning Standards](./project-planning-standards.md), but complexity factors differ:

### Technical Work Complexity Factors

- **Investigation effort**: Unknown root causes add points
- **System knowledge required**: Unfamiliar codebases add points
- **Cross-system impact**: More systems = more complexity
- **Testing difficulty**: Hard-to-test scenarios add points
- **Risk**: Risky changes (migrations, data, auth) add points
- **Coordination**: Cross-team work adds points

### Examples

- **Fix typo in error message** (1 pt): Trivial
- **Update library dependency** (2 pts): Straightforward if tests exist
- **Debug intermittent cache issue** (5 pts): Investigation + fix + verification
- **Refactor auth middleware** (8 pts): High risk, extensive testing needed
- **Migrate database schema** (13 pts): Complex, risky, coordination required

---

## Documentation Requirements

### Always Document

- **Complex bug investigations** (3+ points)
- **Tech debt proposals** (8+ points)
- **Infrastructure specifications** (all)
- **Security fixes** (all)
- **Critical incidents** (P0)

### Sometimes Document

- **Moderate bugs** (when investigation takes >2 hours)
- **Small refactoring** (brief PR description)
- **Routine maintenance** (changelog/release notes)

### Never Document Separately

- **Trivial fixes** (typos, formatting, simple bugs) - PR description sufficient
- **Dependency updates** (no code changes) - PR description + automated changelog

---

## Integration with Feature Work

### Technical Work Visibility

Product stakeholders should understand:
- **What**: High-level description (not technical details)
- **Why**: Business impact (velocity, reliability, cost, risk)
- **When**: Timeline and any feature work impact

Engineering should communicate:
- Tech debt that blocks planned features
- Infrastructure work that enables future capabilities
- Security work that reduces business risk

### Balancing Feature vs Technical Work

Common approaches:
- **Dedicated capacity**: Reserve 20-30% of sprint for tech debt/bugs
- **Rotation**: Dedicated engineer or rotation for bug triage and fixes
- **Opportunistic**: Fix tech debt when working in related code
- **Quarterly initiatives**: Larger tech debt addressed as planned work

This is an engineering leadership decision, not dictated by these standards.

---

## Anti-Patterns

- **"While we're at it" scope creep**: Bug fix turns into unplanned refactor
- **Skipping justification**: "Trust me, we need to refactor this" without business impact
- **Analysis paralysis**: Over-investigating simple bugs
- **Undocumented incidents**: Critical bug fixed but no post-mortem
- **Technical work hoarding**: Not making tech debt visible to stakeholders
- **Zero tech debt time**: All capacity on features, technical quality degrades

---

## Quick Reference

| Work Type | Complexity | Documentation | Estimation |
|-----------|-----------|---------------|------------|
| Simple bug | 1-2 pts | PR description | Quick |
| Moderate bug | 3-5 pts | Investigation doc | Hours to days |
| Complex bug | 8+ pts | Investigation + design | Days to week |
| Critical bug | Varies | Incident + post-mortem | Immediate |
| Small refactor | 1-5 pts | PR description | Opportunistic |
| Large refactor | 8+ pts | Tech debt proposal | Planned work |
| Infrastructure | 2-13 pts | Infrastructure spec | Planned work |
| Security fix | Varies | Per severity | Varies |

---

## Examples

See `docs/engineering/examples/` for:
- Bug investigation template
- Tech debt proposal example
- Infrastructure spec example
- Incident post-mortem template
