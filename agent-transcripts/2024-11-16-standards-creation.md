# Engineering Standards Agent Transcript

*A conversation log documenting the creation and evolution of these engineering standards*

---

## Initial Request: Creating Documentation and SDLC Standards

**User:** I want to create a lightweight standard for documentation practices. We have top level docs/engineering and docs/product directories. I want a short set of guidelines for the docs tree, so you can suggest other high level docs dirs. Within each section I want an SDLC that works from product concept, product requirements and UI design (wireframes, when appropriate), to project planning, estimation and sequencing, and then finally technical design, architecture and implementation plans.

We'll need at least 2 documents to this end, perhaps more: a documentation standards document and an SDLC document. These will eventually migrate to a separate engineering standards repo.

**AI Agent:** I'll analyze the current docs structure and create lightweight, agile-friendly standards that incorporate useful concepts while staying lightweight and agile.

**User:** I should mention, there's a body of practices generally labelled "spec driven development". You can research that and pull in useful concepts. However, don't let external sources pull in heavyweight or overly complex process. This is an early stage project and needs to stay agile.

**AI Agent:** Let me research spec-driven development and then create lightweight, agile-friendly standards that incorporate the useful concepts.

*[Research on spec-driven development and agile documentation practices conducted]*

**Key findings from research:**
- Spec-Driven Development follows: Intent → Spec → Plan → Execution
- Core principle: Write specifications before code
- Agile documentation: Document late/continuously, not big upfront
- Keep documentation as simple as possible
- Executable specifications where possible (TDD)

---

## Document Structure Decisions

**AI Agent:** I'll create three documents:

1. **README.md** - Overview and purpose
2. **documentation-standards.md** - How to structure and write documentation
3. **sdlc.md** - Software development lifecycle

For documentation standards, I'm proposing:
- **Core directories:** `docs/product/`, `docs/engineering/`
- **Optional directories:** `docs/architecture/`, `docs/planning/`, `docs/operations/`

The SDLC will have six phases:
1. Product Concept
2. Product Requirements & UI Design
3. Project Planning & Sequencing
4. Technical Design & Architecture
5. Implementation
6. Validation & Iteration

**Pattern:** Intent → Spec → Plan → Execute → Validate

---

## File Permissions Discussion

**User:** I noticed new documents have 600 access bits. Is that how you are creating them? My standard practice for regular files is 664.

**AI Agent:** You're right—the Write tool creates files with 600 permissions by default. I'll fix all the files I created to 664 and remember to do this going forward.

*[Files updated to 664 permissions]*

---

## Wireframe Approach Update

**User:** In documentation standards we'll use high fidelity HTML mocks for wireframes in most cases. Hand or design tool drawn mocks remain a secondary option.

**AI Agent:** I'll update the documentation standards to make HTML mocks the primary approach for wireframes.

**Rationale added:**
- Version control friendly (clear diffs, easy review)
- Interactive and responsive preview
- Direct translation to implementation
- Can be committed directly to repository

---

## Lightening the SDLC and Adding Story Points

**User:** The SDLC doc is good, but should be a little lighter, just less text, the phasing and general intent is fine. Along with that, I want estimation to be in story points on a 1-13 fibonacci scale. 2 is a baseline, "about 1 human day of effort". Let's add a new standards doc covering the work involved in the Project Planning & Sequencing section of the SDLC doc. We can lighten up the text there and direct the reader to the new doc for details, in the spirit of project management being a significant sub discipline of software engineering.

**AI Agent:** I'll:
1. Create a new `project-planning-standards.md` document with detailed guidance on:
   - Story point estimation (Fibonacci 1-13 scale, 2 points = ~1 day baseline)
   - Task breakdown strategies
   - Sequencing and dependencies
   - Risk identification

2. Update the SDLC to be lighter (~60% less text) while keeping structure and intent

3. Have the SDLC Phase 3 reference the project planning doc for details

**Story Point Scale Guidelines:**
- 1 point: Trivial (~half day or less)
- 2 points: Baseline (~1 day)
- 3 points: Small with complexity (~1.5 days)
- 5 points: Medium complexity (~2-3 days)
- 8 points: Significant complexity (~3-5 days)
- 13 points: High complexity (~1-2 weeks)

If larger than 13 points, break it down.

---

## Technical Work vs Feature Work Discussion

**User:** Let's discuss how we would handle technical tasks, tech debt, and bug fixes. Do these standards provide enough guidance for such work? Can we incorporate those into this SDLC and doc standard? Or do we need another SDLC path for that kind of work?

**AI Agent:** Current coverage analysis:

**Bug Fixes:** Briefly mentioned in "Workflow Variations" but doesn't address:
- How to triage bug severity/complexity
- When a bug needs investigation documentation
- Complex bugs spanning multiple systems

**Tech Debt:** Not explicitly addressed at all.

**Infrastructure/DevOps:** Mentioned briefly but minimal guidance.

**Key differences from feature work:**

The main SDLC assumes:
- Product concept with user value
- Product requirements from product perspective
- UI/UX concerns

But tech debt/infrastructure work has:
- Technical concept (what's wrong with current system?)
- Technical requirements (what technical outcomes needed?)
- No UI (usually)
- Different stakeholders (engineering team, not end users)
- Different success metrics (performance, maintainability, reliability)

**Three options:**

**Option 1:** Expand Workflow Variations section

**Option 2:** Separate "Technical Work Standards" document (recommended)
- The existing SDLC is feature-oriented and that's good
- Tech debt/bugs/infrastructure need different thinking
- Acknowledges this is a discipline like project planning
- Avoids bloating the SDLC

**Option 3:** Create parallel technical SDLC (risky - confusion about which to use)

**My recommendation:** Option 2 - separate document.

**User:** Yes, option 2. In addition to your justifications, feature and tech work are typically driven by separate stakeholders: features by product or business interests, tech work by engineering directives and engineers directly. Go ahead and create a new doc and update the "feature" SDLC accordingly.

---

## Technical Work Standards Created

**AI Agent:** I've created `technical-work-standards.md` covering:

**Bug Fixes:**
- Classification by severity (P0-P3) and complexity (simple/moderate/complex)
- Process by type:
  - Simple bugs (1-2 pts): PR with good description
  - Moderate bugs (3-5 pts): Investigation doc
  - Complex bugs (8+ pts): Investigation + design doc
- Critical bug process with post-incident and post-mortem

**Technical Debt:**
- What qualifies as tech debt
- Proposal template requiring business impact justification
- Prioritization factors (pain, trend, risk, enablement, ROI)
- Small vs large tech debt handling

**Infrastructure and Tooling:**
- Infrastructure specification template
- Adapted workflow phases
- Operational impact considerations

**Security Fixes:**
- Handling by severity
- Confidential documentation practices

**Key distinction emphasized:** Feature work driven by product/business stakeholders; technical work driven by engineering directives and engineers directly.

---

## Renaming and Terminology Cleanup

**User:** Given this new tech work doc, we should rename and retitle sdlc.md. In fact, I propose to avoid using SDLC in all of the standards text due to its breadth and ambiguity of meaning, now that we have topical workflows.

**AI Agent:** Good call - "SDLC" is too broad now that we have specific workflows. I'll:
1. Rename `sdlc.md` to `feature-development-workflow.md`
2. Remove all "SDLC" references throughout standards
3. Replace with specific terminology

**Rationale:** Both documents describe processes/workflows with supporting guidance, so consistent naming creates better alignment and clarity.

*[All SDLC references replaced throughout the standards documents]*

---

## Title Alignment and Workflow Diagrams

**User:** Let's make the title section of technical-work-standards.md read more like that of the feature workflow. And for each, a mermaid diagram of the workflow would be a great addition.

**AI Agent:** I'll update both documents with:
1. Matching title section styles
2. Workflow diagrams

**Feature Development Workflow diagram:**
- Linear flow showing 6 phases
- Color-coded by phase type
- Shows iteration loop from Validation back to Requirements

**Technical Work Standards diagram:**
- Decision tree showing how work type determines process
- Shows all paths: simple bugs, moderate bugs, complex bugs, refactoring, infrastructure, security
- Each path flows to appropriate phases
- Demonstrates that process adapts based on work type and complexity

**User:** Should we call the technical-work-standards.md a workflow instead of a work standard, to better align it with the feature workflow?

**AI Agent:** Yes, that makes sense. Both documents describe processes/workflows with supporting guidance, so calling it "Technical Work Workflow" would create better alignment.

*[Renamed to `technical-work-workflow.md` with all references updated]*

---
## Addendum: Tools and Technology

These engineering standards were developed through an interactive conversation with an AI agent.

**Tool:** Claude Code (Anthropic's official CLI for Claude)

**Model:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)

**Date:** November 2024

The AI agent assisted with:
- Research on spec-driven development and agile documentation practices
- Document structure and organization
- Content creation and iteration based on feedback
- Cross-referencing and consistency checking
- Generalization of domain-specific examples

The conversation demonstrates AI-assisted technical writing where the human provides direction, requirements, and judgment while the AI handles research, drafting, and iteration.

---

*This transcript documents the conversation that created these engineering standards. It captures the reasoning behind decisions and the evolution of thinking as the standards took shape.*
