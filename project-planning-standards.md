# Project Planning Standards

*Breaking features into deliverable work with realistic estimates*

## Overview

Project planning transforms product and technical specs into actionable work. The goal is to sequence tasks effectively, identify dependencies and risks, and provide enough estimation to make informed decisions—without over-planning work that may change.

## Story Point Estimation

### Fibonacci Scale: 1, 2, 3, 5, 8, 13

We use story points on a Fibonacci scale to estimate effort and complexity. Story points capture:
- Implementation effort
- Technical complexity
- Uncertainty and unknowns
- Testing requirements

**Baseline: 2 points = ~1 human day of effort**

This baseline assumes a single developer working on a well-understood task with minimal blockers. Use it as a reference point, not a precise conversion.

### Scale Guidelines

- **1 point**: Trivial change
  - Simple bug fix with known cause
  - Configuration update
  - Minor documentation change
  - ~Half day or less

- **2 points**: Small, straightforward task (baseline)
  - Well-scoped feature implementation
  - Moderate bug fix requiring investigation
  - New API endpoint with clear requirements
  - ~1 day

- **3 points**: Small with some complexity
  - Feature with edge cases to handle
  - Integration with existing system
  - Requires coordination across 2-3 files/components
  - ~1.5 days

- **5 points**: Medium complexity
  - New component or service
  - Multiple integration points
  - Non-trivial state management
  - Moderate test coverage required
  - ~2-3 days

- **8 points**: Significant complexity
  - New subsystem with multiple components
  - Complex algorithm or business logic
  - Extensive testing required
  - May involve research or prototyping
  - ~3-5 days

- **13 points**: High complexity or uncertainty
  - Major architectural change
  - Multiple subsystems affected
  - Significant unknowns or research required
  - Consider breaking down further if possible
  - ~1-2 weeks

**If it's larger than 13 points, break it down.** Tasks this large carry too much risk and uncertainty.

### Estimation Process

1. **Understand the requirement**: Review product spec and technical design
2. **Identify subtasks**: What needs to be built, changed, or tested?
3. **Consider complexity factors**:
   - How well understood is this?
   - How many integration points?
   - What could go wrong?
   - How much testing is needed?
4. **Assign points**: Use Fibonacci scale, round up if uncertain
5. **Validate**: Does the total feel right for the feature? If not, reassess breakdown

### Team Estimation

For team settings, use planning poker:
- Each person estimates independently
- Reveal simultaneously
- Discuss significant differences
- Converge on consensus estimate

Individual contributors can estimate solo but should validate assumptions with technical leads.

## Task Breakdown

### Decomposition Strategy

Break features into tasks that are:
- **Independently testable**: Each task produces verifiable output
- **Incrementally valuable**: Each task moves toward the goal
- **Right-sized**: Typically 2-8 points; rarely >13
- **Clearly scoped**: Obvious when "done"

### Breakdown Pattern

For a typical feature:

1. **Data model/schema changes** (if needed)
   - Define data structures
   - Create migrations
   - Update tests

2. **Core business logic**
   - Implement algorithms or processing
   - Unit tests for logic
   - Handle error cases

3. **API/interface layer**
   - Define contracts (protobuf, REST, etc.)
   - Implement endpoints or services
   - Integration tests

4. **UI/presentation** (if applicable)
   - Implement components or views
   - Wire to backend
   - Handle user interactions

5. **Integration and validation**
   - End-to-end testing
   - Performance validation
   - Edge case verification

Each of these can be further decomposed based on complexity.

### Example Breakdown

**Feature: User Notification System (30 points total)**

- Define notification data schema (2 points)
- Implement email notification channel (3 points)
- Implement SMS notification channel (3 points)
- Implement push notification channel (5 points)
- Create notification routing service (5 points)
- Build notification preferences API (3 points)
- Implement preferences management UI (8 points)
- End-to-end testing and validation (3 points)

## Sequencing and Dependencies

### Identify Dependencies

Map tasks with prerequisite relationships:
- **Hard dependencies**: Task B requires Task A to complete
- **Soft dependencies**: Task B is easier after Task A but not blocked
- **Independent**: Can be done in parallel

### Sequencing Strategies

**Critical path first**: Tackle hard dependencies early to unblock downstream work

**Risk-first**: Address highest uncertainty tasks early to validate feasibility

**Foundational layers**: Build data models and core services before presentation layers

**Parallel tracks**: Identify independent work streams that can proceed simultaneously

### Example Dependency Map

```
[Schema] → [Email Channel] ──────────────────────→ [E2E Testing]
           ↓
[Schema] → [SMS Channel] → [Routing Service] ────→ [E2E Testing]
           ↓
[Schema] → [Push Channel] ────────────────────────→ [E2E Testing]
           ↓
[Schema] → [Preferences API] → [Preferences UI] ──→ [E2E Testing]
```

This shows:
- Schema must be done first (hard dependency)
- Three parallel tracks after schema
- E2E testing waits for all tracks (final integration)

## Risk Identification

### Common Risks

**Technical unknowns**: "We've never used this library/protocol before"
- Mitigation: Timeboxed spike or proof-of-concept
- Add buffer points to estimate

**External dependencies**: "Requires API from Team X"
- Mitigation: Early coordination, interface contract definition
- Track as explicit dependency

**Scope uncertainty**: "Requirements may change based on user feedback"
- Mitigation: Build incrementally, ship MVPs for validation
- Plan in phases with checkpoints

**Performance requirements**: "Must handle 10k requests/second"
- Mitigation: Early load testing, architecture review
- Add validation task before full implementation

**Integration complexity**: "Must work with legacy system"
- Mitigation: Research integration patterns, prototype
- Budget extra points for debugging

### Risk Documentation

For each significant risk:
- **What**: Describe the risk
- **Impact**: What happens if this materializes?
- **Likelihood**: High/Medium/Low
- **Mitigation**: What are we doing to address it?
- **Contingency**: What if mitigation fails?

Document in planning artifact or as separate risk log for complex projects.

## Planning Artifacts

### Implementation Plan Template

```markdown
# Implementation Plan: [Feature Name]

## Overview
[Brief description and link to product spec]

## Total Estimate: [X points]

## Task Breakdown

### Phase 1: [Name] ([X points])
- [ ] Task description (N points)
- [ ] Task description (N points)

### Phase 2: [Name] ([X points])
- [ ] Task description (N points)

## Dependencies
- Task B depends on Task A
- Task C depends on external API from Team X (ETA: date)

## Risks
- [Risk description]: [Mitigation strategy]

## Milestones
- Phase 1 complete: [date or sprint]
- Feature shipped: [date or sprint]
```

### When to Create Formal Plans

**Always**:
- Features >13 points total
- Work involving multiple people
- Cross-team dependencies
- Significant technical risk

**Sometimes**:
- Medium features (5-13 points) when helpful for clarity
- Work with uncertain scope

**Never**:
- Trivial tasks (1-2 points)
- Bug fixes with obvious solutions
- Documentation updates

## Tracking and Updates

### During Development

- Update task status as work progresses
- Adjust estimates if actual effort significantly differs
- Document blockers and dependencies as they're discovered
- Update risk status when circumstances change

### Retrospective

After feature completion:
- How did actual effort compare to estimates?
- What risks materialized?
- What did we miss in planning?
- What would we do differently?

Use retrospectives to calibrate future estimates and improve planning.

## Anti-Patterns

- **False precision**: Estimating to hours or converting points to exact days
- **Padding**: Doubling estimates "to be safe" instead of addressing uncertainty
- **Ignoring history**: Not learning from past estimate misses
- **Over-planning**: Detailed task breakdown for uncertain work far in the future
- **Under-planning**: Starting complex work without understanding dependencies

## Integration with Feature Development

Project planning occurs in **Phase 3** of the feature development workflow, after product requirements and before technical design. It informs how much design detail is needed and validates that scope is reasonable.

Planning artifacts live in `docs/planning/` and should be updated as implementation reveals new information.
