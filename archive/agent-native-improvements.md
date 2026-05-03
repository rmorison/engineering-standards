# Agent-Native Architecture Improvements

> **Implementation strategy superseded by [ADR-0001: Six-Layer AI Architecture](../docs/engineering/adr/0001-six-layer-ai-architecture.md).**
>
> This document analyzed agent-native principles and proposed building those abstractions in this repository. We instead adopted the six-layer AI architecture (see [ADR-0001](../docs/engineering/adr/0001-six-layer-ai-architecture.md)) with [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) as the canonical realization of Layers 2 and 3. Kept here as the evaluative framework that informed the architecture — the analysis remains the lens for re-evaluating CE adoption if circumstances change. See [`process/compound-engineering-integration.md`](../process/compound-engineering-integration.md) for the operational doc.

**Date**: 2026-01-22
**Source**: [Agent-Native Guide](https://every.to/guides/agent-native) from Every.to
**Status**: Proposed

## Overview

This document outlines suggestions for incorporating agent-native design principles into our engineering standards repository. These improvements aim to make our standards more accessible and actionable for AI assistants while maintaining human readability.

## Agent-Native Principles

The Every.to guide establishes five core principles for building agent-native applications:

1. **Parity**: Whatever the user can do through the UI, the agent should be able to achieve through tools
2. **Granularity**: Tools should be atomic primitives rather than bundling decision logic
3. **Composability**: With atomic tools and parity, new features emerge through descriptive prompts
4. **Emergent Capability**: Agents accomplish tasks designers didn't explicitly anticipate
5. **Improvement Over Time**: Applications evolve through accumulated context and prompt refinement

## Current Strengths

Our repository already embraces several agent-native concepts:

- **File-first architecture**: Extensive use of markdown documents
- **Shared workspace**: The `/ai/CLAUDE.md` guide puts AI assistants and humans in the same context
- **Transparent process**: Agent transcripts document how standards were created
- **Composability**: Modular standards that can be applied independently

## Proposed Improvements

### 1. Agent-Accessible Standard Reference System

Create a machine-readable index alongside markdown files to enable quick standard lookup.

**Implementation**:
```
/code/standards-index.json
{
  "standards": [
    {
      "id": "python-testing",
      "path": "/code/python-standards.md#testing",
      "category": "code-quality",
      "applies_to": ["python"],
      "keywords": ["pytest", "unit-tests", "coverage"],
      "atomic_rules": [
        "Use pytest as the testing framework",
        "Maintain 80% code coverage minimum"
      ]
    }
  ]
}
```

**Benefits**:
- Agents can locate specific standards without parsing entire documents
- Enables semantic search across standards
- Supports automated compliance checking

### 2. Explicit Completion Criteria

Enhance process documents with agent-checkable completion signals.

**Implementation**:
```markdown
## Feature Completion Checklist (Agent-Verifiable)

- [ ] `STATUS: implementation-complete` flag in issue
- [ ] All acceptance criteria have `[x]` checked
- [ ] CI pipeline shows green status
- [ ] `docs/` directory contains updated documentation
- [ ] CHANGELOG.md has entry for this version
```

**Benefits**:
- Agents know when tasks are truly complete
- Reduces back-and-forth asking "is this done?"
- Creates verifiable audit trail

### 3. Atomic Standard Decomposition

Break down `/ai/CLAUDE.md` into more granular, composable pieces.

**Implementation**:
```
/ai/
  ├── README.md (overview)
  ├── principles.md (core principles)
  ├── workflows/
  │   ├── feature-development.md
  │   ├── bug-fixing.md
  │   └── code-review.md
  ├── context/
  │   ├── estimation-scales.md
  │   ├── issue-patterns.md
  │   └── project-structure.md
  └── tools/
      ├── available-commands.md
      └── verification-scripts.md
```

**Benefits**:
- Agents load only relevant context for specific tasks
- Reduces token usage and improves response time
- Easier to maintain and update individual pieces

### 4. Standard Application Templates

Add agent-executable validation scripts.

**Implementation**:
```python
# /tools/validate-python-standard.py
"""
Verifies a Python project meets engineering standards.
Agents can run this to confirm compliance.
"""

def check_project_structure():
    """Returns list of violations or empty list if compliant"""
    required_files = ['pyproject.toml', 'README.md', 'tests/']
    violations = []
    # Check logic here
    return violations

def check_dependencies():
    """Validates pyproject.toml matches standards"""
    pass

def generate_compliance_report():
    """Creates markdown report of standard compliance"""
    pass
```

**Benefits**:
- Automated standard validation
- Consistent compliance checking
- Agents can verify their work meets standards

### 5. Context Injection Files

Create session-specific context files that agents can read.

**Implementation**:
```markdown
# .agent-context.md (git-ignored, ephemeral)

## Current Session
- **Task**: Implement user authentication
- **Active Branch**: feature/auth-system
- **Relevant Standards**: /code/python-standards.md#security, /process/feature-development-workflow.md
- **Recent Decisions**: Using JWT tokens (decided in issue #42)
- **Open Questions**: Session timeout duration (ask user)
```

**Update `.gitignore`**:
```
# Agent session context (ephemeral)
.agent-context.md
```

**Benefits**:
- Agents maintain context across sessions
- Reduces need to re-explain project state
- Documents decisions and rationale

### 6. Emergent Capability Documentation

Track unexpected but valuable agent behaviors.

**Implementation**:
```markdown
# /ai/emergent-patterns.md

## Discovered Agent Capabilities

### Automatic Standard Cross-Referencing
- **Emerged**: 2026-01-15
- **Description**: Agent began linking related standards across documents
- **Value**: Improved consistency checking
- **How to Replicate**: Include instruction in CLAUDE.md
- **Example**: See transcript 2026-01-15-code-review.md

### Proactive Security Scanning
- **Emerged**: 2026-01-18
- **Description**: Agent suggested security scans without being asked
- **Value**: Caught vulnerability before deployment
- **How to Replicate**: Add security checklist to code review workflow
```

**Benefits**:
- Captures valuable behaviors for replication
- Improves standards over time based on actual usage
- Creates feedback loop for continuous improvement

### 7. Parity with Human Workflows

Ensure every human process has an agent-equivalent.

**Analysis**:

| Human Action | Current Agent Access | Gap | Recommendation |
|-------------|---------------------|-----|----------------|
| Create issue from template | Can read templates | No write access to GitHub | Document issue creation checklist agents can populate |
| Run estimation meeting | Can read scale | No facilitation process | Add `/ai/workflows/estimation.md` |
| Review PR | Can read code | No approval mechanism | Document review checklist agents can populate |
| Update documentation | Can edit markdown | No doc structure guide | Add documentation templates |
| Deploy to production | Can read deploy docs | No execution access | Document pre/post-deploy checklists |

**Implementation**: Create `/ai/parity-matrix.md` tracking agent capabilities vs. human workflows.

**Benefits**:
- Identifies gaps in agent capabilities
- Ensures agents can fully participate in workflows
- Guides tool development priorities

### 8. Iterative Improvement Mechanism

Create a feedback loop for standard evolution.

**Implementation**:
```markdown
# /ai/improvements.md

## Standard Refinements Suggested by Agents

### Week of 2026-01-20
- **Suggested**: Add security scanning to Python standards
- **Context**: Agent encountered vulnerability during code review
- **Status**: Accepted, updated python-standards.md
- **PR**: #123

### Week of 2026-01-27
- **Suggested**: Clarify when to use feature vs. technical workflow
- **Context**: Agent unsure which process to follow for refactoring
- **Status**: Under review
- **Discussion**: Issue #125
```

**Benefits**:
- Standards evolve based on real usage
- Captures pain points and ambiguities
- Transparent improvement process

### 9. Enhanced Agent Transcripts

Structure transcripts for maximum learning value.

**Implementation**:
```markdown
# Format: YYYY-MM-DD-{task}-{outcome}.md

## Transcript Metadata
- **Task**: Implement user authentication
- **Standards Applied**:
  - /process/feature-development-workflow.md
  - /code/python-standards.md#security
- **Outcome**: Success (merged to main)
- **Duration**: 3 sessions over 2 days

## Completion Signals Observed
- All acceptance criteria checked
- CI pipeline green
- Documentation updated

## Tools Used
- pytest for test coverage
- ruff for linting
- mypy for type checking
- gh CLI for PR creation

## Emergent Behaviors
- Agent proactively suggested rate limiting
- Cross-referenced OWASP standards without prompting

## Improvement Suggestions
- Security checklist would have streamlined review
- Clearer guidance on when to add logging
```

**Benefits**:
- Transcripts become training material
- Patterns emerge from multiple sessions
- Identifies standard gaps and improvements

### 10. Agent-Readable Project State

Add persistent state tracking that both humans and agents maintain.

**Implementation**:
```json
# .project-status.json (committed to repo)
{
  "last_updated": "2026-01-22T14:30:00Z",
  "active_standards_version": "v1.2.0",
  "compliance_status": {
    "python": "compliant",
    "documentation": "partial",
    "security": "in-progress"
  },
  "active_work": [
    {
      "issue": "#45",
      "standard": "feature-development-workflow",
      "current_step": "implementation",
      "started": "2026-01-20"
    }
  ],
  "recent_completions": [
    {
      "issue": "#42",
      "completed": "2026-01-19",
      "standards_applied": ["python-standards", "git-branching-strategy"]
    }
  ],
  "known_issues": [
    {
      "description": "Test coverage below 80% in auth module",
      "tracking": "#46",
      "impact": "blocks release"
    }
  ]
}
```

**Benefits**:
- Agents understand project state immediately
- Reduces "what's the status?" questions
- Enables progress tracking and reporting

## Implementation Priority

### High Impact, Low Effort (Start Here)
1. **Explicit Completion Criteria** (#2)
   - Add to existing process documents
   - Immediate improvement in agent clarity

2. **Atomic Standard Decomposition** (#3)
   - Restructure `/ai/CLAUDE.md`
   - Better context loading

### Medium Priority
3. **Standards Index** (#1)
   - JSON index of all standards
   - Enables quick lookup

4. **Context Injection Files** (#5)
   - Add `.agent-context.md` template
   - Update `.gitignore`

5. **Enhanced Transcripts** (#9)
   - Add metadata template
   - Richer learning data

### Long Term
6. **Parity Analysis** (#7)
   - Document capability gaps
   - Guide future development

7. **Project State Tracking** (#10)
   - Implement `.project-status.json`
   - Maintain in workflows

8. **Validation Tools** (#4)
   - Build compliance checkers
   - Automated verification

9. **Emergent Patterns** (#6)
   - Document valuable behaviors
   - Continuous improvement

10. **Improvement Mechanism** (#8)
    - Feedback loop process
    - Standard evolution tracking

## Success Metrics

Track these indicators to measure agent-native improvements:

- **Reduced clarification questions**: Agents need less back-and-forth to understand requirements
- **Increased standard compliance**: Automated checks show higher conformance
- **Faster task completion**: Agents complete tasks with fewer iterations
- **Emergent behaviors documented**: New valuable patterns identified monthly
- **Standard updates from agent feedback**: Standards improve based on actual usage

## Next Steps

1. Review this proposal with team
2. Prioritize improvements based on current pain points
3. Create issues for approved improvements
4. Implement incrementally following our own standards
5. Document learnings in agent transcripts

## References

- [Agent-Native Guide](https://every.to/guides/agent-native) - Every.to
- `/ai/CLAUDE.md` - Current AI assistant guide
- `/agent-transcripts/` - Existing agent session records
- `/process/` - Current process standards

## Notes

These improvements align with our philosophy of:
- Lightweight process (add only what provides value)
- Spec-driven development (explicit > implicit)
- GitHub-native workflows (use built-in features)
- AI-native development (design for human-AI collaboration)

The goal is to make our standards more actionable for agents while maintaining human readability and our commitment to avoiding process overhead.
