# Top 3 Agent-Native Enhancements

> **Implementation strategy superseded by [ADR-0001: Six-Layer AI Architecture](../docs/engineering/adr/0001-six-layer-ai-architecture.md).**
>
> This document analyzed agent-native principles and proposed building those abstractions in this repository. We instead adopted the six-layer AI architecture (see [ADR-0001](../docs/engineering/adr/0001-six-layer-ai-architecture.md)) with [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) as the canonical realization of Layers 2 (Workflow Skills), 3 (Persona Agents), 4 (References), and 5 (Compound / Learnings). Kept here as the evaluative framework that informed the architecture — the analysis remains the lens for re-evaluating CE adoption if circumstances change. See [`process/compound-engineering-integration.md`](../process/compound-engineering-integration.md) for the operational doc.

**Date**: 2026-01-24
**Status**: Approved for Implementation

Based on analysis of the [Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin) and [Every.to Agent-Native Guide](https://every.to/guides/agent-native), these are the 3 highest-impact additions to this repository:

---

## 1. Knowledge Compounding (The "Compound" Step)

**Problem**: Each task starts fresh. We don't systematically capture what we learn, so we repeat mistakes and duplicate research.

**Solution**: Add a "Compound" step after task completion to capture learnings.

**Implementation**:
1. Add Phase 7 "Compound" to both workflow documents
2. Create `/ai/learnings/` directory structure
3. Create `templates/task-retrospective.md`

**What to capture**:
- Challenges encountered and solutions found
- Code patterns that worked well
- Gotchas and pitfalls to avoid
- Standards gaps discovered
- Tools/techniques that proved valuable

**Where to document**:
- Quick insights → `/ai/learnings/{domain}.md` (e.g., python.md, testing.md)
- Significant decisions → ADR in `docs/engineering/adr/`
- Workflow improvements → PR to relevant standard
- Novel behaviors → `/ai/emergent-patterns.md`

**Example**:
```markdown
# /ai/learnings/python.md

## Testing Patterns

### Async Test Fixtures (Issue #42, 2026-01-20)
- **Challenge**: Async database tests were flaky
- **Solution**: Use `pytest-asyncio` with `scope="function"`
- **Gotcha**: Don't mix sync and async fixtures in same test
- **Code**: See `tests/conftest.py:25-40`
```

**Impact**: Future similar tasks start with accumulated knowledge instead of from scratch.

**Effort**: ~1 hour setup + 10-15 min per task to document learnings

---

## 2. Explicit Completion Criteria

**Problem**: Ambiguity about when work is "done" leads to incomplete tasks, back-and-forth clarification, and quality issues.

**Solution**: Add clear, agent-verifiable "Definition of Done" checklists to all workflows.

**Implementation**:
Add to both `process/feature-development-workflow.md` and `process/technical-work-workflow.md`:

```markdown
## Definition of Done

A task is complete when ALL of these criteria are met:

**Code Complete**:
- [ ] All acceptance criteria from spec are implemented
- [ ] Code follows language standards (e.g., `code/python-standards.md`)
- [ ] No compiler/linter warnings introduced

**Quality Verified**:
- [ ] Tests written and passing (unit + integration as needed)
- [ ] Code coverage meets standards (80% for new code)
- [ ] Manual testing completed (if UI/integration work)
- [ ] Security review completed (if security-relevant)

**Documentation Current**:
- [ ] Code comments added where logic is non-obvious
- [ ] README/docs updated if behavior changed
- [ ] ADR created if significant technical decision made

**Integration Ready**:
- [ ] CI/CD pipeline passing (all checks green)
- [ ] Branch rebased on latest main (no conflicts)
- [ ] PR description complete with summary and testing notes

**Knowledge Captured**:
- [ ] Retrospective completed (if non-trivial task)
- [ ] Learnings documented in `/ai/learnings/`
- [ ] Any standards gaps noted as issues
```

**Impact**: Clear finish line reduces rework, catches incomplete work early, creates consistent quality bar.

**Effort**: ~30 minutes to add checklists

---

## 3. Workflow Skills Library

**Problem**: Common tasks (debugging, feature implementation, refactoring) are done inconsistently. Each time we reinvent the approach.

**Solution**: Create reusable workflow guides for frequent task types.

**Implementation**:
Create `/ai/workflows/` directory with these essential workflows:

### `/ai/workflows/bug-investigation.md`
```markdown
## Bug Investigation Workflow

### 1. Reproduce (Goal: Minimal repro case)
- [ ] Document exact steps to trigger bug
- [ ] Identify affected versions/environments
- [ ] Create minimal code example that reproduces issue

### 2. Research (Goal: Context and similar issues)
- [ ] Search issue tracker for similar reports
- [ ] Review recent changes: `git log --since="2 weeks ago" -- {affected_files}`
- [ ] Check `/ai/learnings/` for related gotchas
- [ ] Search framework/library issue trackers

### 3. Investigate (Goal: Root cause hypothesis)
- [ ] Add logging to narrow scope
- [ ] Use debugger to examine state at failure point
- [ ] Form hypothesis of root cause
- [ ] Verify hypothesis with targeted test

### 4. Document (Goal: Clear record for fix)
- [ ] Update issue with reproduction steps
- [ ] Document root cause analysis in issue comments
- [ ] Create failing test that demonstrates bug
- [ ] Note any related bugs that might exist

### 5. Fix & Compound (Goal: Prevent recurrence)
- [ ] Implement fix
- [ ] Verify fix with reproduction test
- [ ] Add to `/ai/learnings/` if gotcha discovered
- [ ] Search codebase for similar patterns that might have same bug
```

### `/ai/workflows/feature-implementation.md`
```markdown
## Feature Implementation Workflow

### 1. Understand Spec (Goal: Clear requirements)
- [ ] Read product spec in `docs/product/features/`
- [ ] Read technical design in `docs/engineering/design/`
- [ ] Review acceptance criteria
- [ ] List any unclear requirements (ask before coding)

### 2. Research (Goal: Informed approach)
- [ ] Search codebase for similar features: `grep -r "similar pattern"`
- [ ] Review `/ai/learnings/` for relevant insights
- [ ] Check ADRs for relevant architectural decisions
- [ ] Review framework best practices

### 3. Plan (Goal: Implementation strategy)
- [ ] List files to create/modify
- [ ] Identify reusable components
- [ ] Note dependencies or blockers
- [ ] Estimate effort (compare to original story points)

### 4. Implement (Goal: Working code)
- [ ] Write tests first (TDD) or alongside code
- [ ] Follow language standards (e.g., `code/python-standards.md`)
- [ ] Keep commits logical and atomic
- [ ] Run tests frequently

### 5. Verify (Goal: Meets acceptance criteria)
- [ ] All acceptance criteria met
- [ ] Tests passing (unit, integration, e2e as needed)
- [ ] Manual testing completed
- [ ] Performance acceptable

### 6. Document (Goal: Maintainable)
- [ ] Add/update code comments for complex logic
- [ ] Update README if user-facing changes
- [ ] Create ADR if significant decision made

### 7. Compound (Goal: Make next feature easier)
- [ ] Complete retrospective
- [ ] Update `/ai/learnings/` with insights
- [ ] Note any standards improvements needed
```

### `/ai/workflows/code-review.md`
```markdown
## Code Review Workflow

### Security Perspective
- [ ] Input validation on all external data
- [ ] Authentication/authorization checks present
- [ ] No secrets in code or logs
- [ ] SQL injection / XSS prevention

### Performance Perspective
- [ ] No N+1 queries
- [ ] Database queries have appropriate indexes
- [ ] Caching used where beneficial
- [ ] No blocking operations in critical paths

### Architecture Perspective
- [ ] Follows established patterns
- [ ] Appropriate abstraction level (not over/under-engineered)
- [ ] Dependencies point in correct direction
- [ ] No circular dependencies

### Testing Perspective
- [ ] Edge cases covered
- [ ] Error paths tested
- [ ] Test quality (not just coverage)
- [ ] Integration tests for external dependencies

### Standards Compliance
- [ ] Follows language standards
- [ ] Commit messages follow conventions
- [ ] PR description complete
- [ ] Documentation updated
```

**Impact**: Consistent, thorough approach to common tasks. Less reinvention, fewer missed steps, better quality.

**Effort**: ~2 hours to create initial 3 workflows

---

## Implementation Order

1. **Start with #2 (Completion Criteria)** - 30 minutes, immediate clarity
2. **Then #1 (Knowledge Compounding)** - 1 hour setup, start documenting learnings
3. **Then #3 (Workflow Skills)** - 2 hours, practical tools ready to use

**Total setup time**: ~3.5 hours
**Ongoing time**: 10-15 min per task for retrospective/learnings

---

## Success Metrics

After 1 month of using these enhancements:

- ✅ At least 3 learning documents exist with real insights
- ✅ Completed tasks consistently meet all completion criteria
- ✅ Workflow skills are referenced when doing relevant tasks
- ✅ Agents ask fewer clarification questions
- ✅ Similar tasks are completed faster than initial implementation

---

## References

- [Adoption Roadmap](./adoption-roadmap.md) - Full phased plan with all enhancements
- [Agent-Native Improvements](./agent-native-improvements.md) - Complete analysis of agent-native principles
- [Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin)
- [Every.to Agent-Native Guide](https://every.to/guides/agent-native)
