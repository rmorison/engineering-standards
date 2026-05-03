# Agent-Native Adoption Roadmap

> **Implementation strategy superseded by [ADR-0001: Six-Layer AI Architecture](../docs/engineering/adr/0001-six-layer-ai-architecture.md).**
>
> This document analyzed agent-native principles and proposed building those abstractions in this repository. We instead adopted the six-layer AI architecture (see [ADR-0001](../docs/engineering/adr/0001-six-layer-ai-architecture.md)) with [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) as the canonical realization of Layers 2 and 3. Kept here as the evaluative framework that informed the architecture — the analysis remains the lens for re-evaluating CE adoption if circumstances change. See [`process/compound-engineering-integration.md`](../process/compound-engineering-integration.md) for the operational doc.

**Date**: 2026-01-24
**Status**: Active Planning
**Sources**:
- [Agent-Native Guide](https://every.to/guides/agent-native) (Every.to)
- [Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin)

## Overview

This document consolidates two separate assessments ([agent-native-improvements.md](./agent-native-improvements.md) and compound engineering analysis) into a single, practical adoption plan. Rather than 17 separate improvements, we've identified 5 core themes with incremental implementation steps.

## Core Themes (Consolidation)

### Theme 1: Knowledge Compounding
**Combines**: Agent-Native #6 (Emergent Capability), #8 (Iterative Improvement), Compound Engineering #1 (Compound Step), #2 (Learnings Repository)

**Core Idea**: Each completed task should make future tasks easier through systematic knowledge capture and reuse.

### Theme 2: Clear Completion & Quality Signals
**Combines**: Agent-Native #2 (Completion Criteria), #9 (Enhanced Transcripts), Compound Engineering #3 (Multi-Perspective Review), #7 (Retrospective)

**Core Idea**: Agents and humans need explicit signals for when work is complete and what quality means.

### Theme 3: Atomic, Composable Content
**Combines**: Agent-Native #3 (Atomic Decomposition), Compound Engineering #5 (Workflow Skills)

**Core Idea**: Break standards and workflows into small, reusable pieces that can be combined as needed.

### Theme 4: Contextual Intelligence
**Combines**: Agent-Native #1 (Standards Index), #5 (Context Injection), #10 (Project State)

**Core Idea**: Provide agents quick access to relevant standards, context, and project state without reading everything.

### Theme 5: Research & Planning Emphasis
**Combines**: Agent-Native #7 (Parity Matrix), Compound Engineering #4 (Pre-Implementation Research), #6 (80/20 Planning)

**Core Idea**: Invest more time in research and planning to make execution faster and higher quality.

---

## Phased Adoption Plan

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Establish knowledge capture habits and basic structure

#### Week 1: Add Knowledge Compounding

**Step 1.1: Add "Compound" step to workflows** ⏱️ 30 minutes
- Update `process/feature-development-workflow.md`
- Update `process/technical-work-workflow.md`
- Add Phase 7: "Compound (Knowledge Capture)" with checklist

**Step 1.2: Create learnings directory structure** ⏱️ 15 minutes
```bash
mkdir -p ai/learnings
touch ai/learnings/README.md
```

**Step 1.3: Create task retrospective template** ⏱️ 20 minutes
- Create `templates/task-retrospective.md`
- Include sections: What Went Well, Challenges, Learnings, Compound Actions

**Success metric**: Next completed task includes a retrospective and learning documentation

#### Week 2: Improve Completion Clarity

**Step 1.4: Add explicit completion checklists** ⏱️ 45 minutes
- Add "Definition of Done" checklists to both workflow documents
- Include agent-verifiable criteria (tests pass, docs updated, etc.)

**Step 1.5: Enhance agent transcript template** ⏱️ 30 minutes
- Update `agent-transcripts/README.md` with structured format
- Include: Task, Standards Applied, Outcome, Tools Used, Learnings

**Step 1.6: Create first learning document** ⏱️ 45 minutes
- Create `ai/learnings/standards-creation.md`
- Document insights from Python standards creation
- Establish pattern for future learning docs

**Success metric**: Clear criteria exist for when any task is "done"

---

### Phase 2: Practical Tools (Weeks 3-4)
**Goal**: Build reusable workflows and make content more discoverable

#### Week 3: Workflow Skills Library

**Step 2.1: Create workflow skills structure** ⏱️ 20 minutes
```bash
mkdir -p ai/workflows
touch ai/workflows/README.md
```

**Step 2.2: Build 3 essential workflows** ⏱️ 90 minutes each
- `ai/workflows/bug-investigation.md` - Systematic debugging approach
- `ai/workflows/feature-implementation.md` - Step-by-step feature building
- `ai/workflows/standard-creation.md` - Creating new standards (meta!)

**Step 2.3: Cross-reference from CLAUDE.md** ⏱️ 20 minutes
- Add "Workflow Skills" section to `ai/CLAUDE.md`
- Link to workflow directory

**Success metric**: Next bug or feature uses a workflow skill as guide

#### Week 4: Better Content Discovery

**Step 2.4: Restructure CLAUDE.md** ⏱️ 2 hours
- Split into focused files:
  - `ai/principles.md` (core principles)
  - `ai/context/estimation-scales.md`
  - `ai/context/issue-patterns.md`
- Update `ai/CLAUDE.md` to be a navigation/overview file

**Step 2.5: Add standards quick reference** ⏱️ 1 hour
- Create `ai/standards-quick-ref.md`
- Table format: Standard, When to Use, Key Points, Full Link
- Lightweight alternative to full JSON index

**Success metric**: CLAUDE.md is under 200 lines, standards are quickly findable

---

### Phase 3: Advanced Capabilities (Weeks 5-6)
**Goal**: Enable deeper agent capabilities and systematic improvement

#### Week 5: Multi-Perspective Review

**Step 3.1: Create code review standard** ⏱️ 90 minutes
- New file: `process/code-review-standards.md`
- Include review perspectives: Security, Performance, Architecture, Testing
- Add checklists for each perspective

**Step 3.2: Add research phase to technical design** ⏱️ 45 minutes
- Update `process/feature-development-workflow.md` Phase 4
- Add "Research Before Design" section
- Include: codebase patterns, external best practices, historical context

**Step 3.3: Document 80/20 planning principle** ⏱️ 30 minutes
- Add to `README.md` Philosophy section
- Add to `ai/principles.md`
- Emphasize planning investment over execution speed

**Success metric**: Next complex PR uses multi-perspective review checklist

#### Week 6: Contextual Intelligence

**Step 3.4: Create context injection template** ⏱️ 30 minutes
- Create `templates/.agent-context.md`
- Add to `.gitignore`
- Document when/how to use in `ai/CLAUDE.md`

**Step 3.5: Build lightweight project state** ⏱️ 1 hour
- Create `.project-status.json` with: active work, recent completions, known issues
- Add "update project status" to compound step checklist
- Start simple, expand over time

**Step 3.6: Create parity matrix** ⏱️ 1 hour
- New file: `ai/parity-matrix.md`
- Map human actions → agent capabilities → gaps
- Identify top 3 capability gaps to address

**Success metric**: Agents understand project state without lengthy explanations

---

### Phase 4: Continuous Improvement (Ongoing)
**Goal**: Establish feedback loops and evolving standards

#### Ongoing Activities

**Activity 4.1: Weekly learning documentation** ⏱️ 15 min/week
- Every completed task: Update relevant learning document
- Create new learning docs as domains emerge

**Activity 4.2: Monthly standard refinement** ⏱️ 1 hour/month
- Review `ai/learnings/` for patterns
- Propose standard updates based on accumulated insights
- Track in `ai/improvement-suggestions.md`

**Activity 4.3: Quarterly retrospective** ⏱️ 2 hours/quarter
- Review adoption effectiveness
- Identify successful patterns
- Prune or revise tools that aren't working
- Update adoption roadmap

**Success metric**: Standards evolve based on real usage, agent effectiveness increases over time

---

## Implementation Principles

### Start Small, Compound Over Time
Don't try to implement everything at once. Each phase builds on the previous one. The compounding effect comes from consistent application, not comprehensive adoption.

### Favor Practice Over Perfection
A simple learning document used regularly beats a comprehensive system used never. Start with basic formats and let them evolve through use.

### Measure by Effectiveness, Not Completion
Success isn't "did we implement all 17 improvements?" It's "are agents more effective? Are tasks getting easier?"

### Maintain Lightweight Philosophy
If an addition feels heavy or bureaucratic, simplify it. These tools should enable work, not create overhead.

---

## Priority Matrix

### Must Have (Do First)
- Theme 1: Knowledge Compounding (Phase 1, Week 1-2)
- Theme 2: Completion Signals (Phase 1, Week 2)

**Rationale**: These provide immediate value and establish the foundation for everything else.

### Should Have (High Value)
- Theme 3: Atomic Content (Phase 2, Week 4)
- Theme 2: Workflow Skills (Phase 2, Week 3)

**Rationale**: Make existing content more usable and add practical tools.

### Could Have (Incremental Value)
- Theme 5: Research/Planning Emphasis (Phase 3, Week 5)
- Theme 4: Contextual Intelligence (Phase 3, Week 6)

**Rationale**: Valuable but can wait until foundation is solid.

### Won't Have (Yet)
- Agent-Native #4: Validation scripts (automation premature)
- Full JSON standards index (quick-ref sufficient)

**Rationale**: These add complexity without clear immediate value. Revisit in Phase 4+ based on real needs.

---

## Success Indicators

Track these qualitative signals to assess adoption effectiveness:

### Agent Effectiveness
- ✅ Agents ask fewer clarification questions
- ✅ Agents reference learnings documents unprompted
- ✅ Agents complete tasks in fewer iterations
- ✅ Agents suggest improvements to standards

### Knowledge Accumulation
- ✅ Learning documents grow with each task
- ✅ Retrospectives capture valuable insights
- ✅ Standards improve based on real experience
- ✅ New team members/agents onboard faster

### Quality Signals
- ✅ "Definition of done" prevents incomplete work
- ✅ Review checklists catch issues earlier
- ✅ Less rework required after task completion
- ✅ Fewer repeat mistakes

### Workflow Efficiency
- ✅ Tasks start faster (less research duplicated)
- ✅ Planning phase is more thorough
- ✅ Similar tasks show measurable improvement
- ✅ Context switching is faster

---

## Decision Log

### Why This Consolidation?

**Original situation**:
- 10 agent-native improvements
- 7 compound engineering additions
- 17 total items, unclear priorities, significant overlap

**Problems**:
- Too many things to track
- Unclear what to do first
- Overlapping concepts confusing
- Risk of analysis paralysis

**Solution**:
- Consolidated into 5 core themes
- Phased adoption plan (6 weeks + ongoing)
- Time estimates for each step
- Clear success metrics

**Trade-offs**:
- Some specificity lost in consolidation
- Original documents still valuable as reference
- This is an interpretation, not gospel

### Why These Phases?

**Phase 1**: Foundation habits (compounding, completion)
- Most impactful practices
- Establish the feedback loop
- Quick wins build momentum

**Phase 2**: Practical tools (workflows, discovery)
- Support the foundation with actual tools
- Make existing content more usable
- Still relatively quick to implement

**Phase 3**: Advanced capabilities (review, context, research)
- Build on established foundation
- More sophisticated but require base practices
- Higher effort, incremental value

**Phase 4**: Continuous improvement (ongoing)
- Perpetual refinement based on Phase 1-3 experience
- The compounding effect in action

---

## Next Steps

1. **Review this roadmap** - Does it make sense? Any adjustments needed?

2. **Start Phase 1, Week 1** - Begin with knowledge compounding:
   - Update workflow documents (Step 1.1)
   - Create learnings directory (Step 1.2)
   - Create retrospective template (Step 1.3)

3. **Apply to next task** - Use the new compound step and retrospective on the very next completed task

4. **Iterate** - Adjust the roadmap based on what works and what doesn't

---

## References

- [Agent-Native Improvements](./agent-native-improvements.md) - Original assessment #1
- [Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin) - Source for assessment #2
- [Engineering Standards README](../README.md) - Our philosophy and current structure
- [CLAUDE.md](./CLAUDE.md) - Current AI assistant guide

---

**Last Updated**: 2026-01-24
**Status**: Ready for review and Phase 1 implementation
