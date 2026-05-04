# Documentation Standards

*Lightweight practices for early-stage agile development*

## Philosophy

Documentation serves as the source of truth for both humans and AI agents. Keep it as simple as possible, write what's necessary when it's necessary, and update continuously as understanding evolves. Early-stage projects prioritize working software over comprehensive documentation—but the right documentation at the right time accelerates development.

## Directory Structure

Repository documentation lives under `docs/` with the following top-level directories:

### Core Directories

- **`docs/product/`** - Product vision, strategy, requirements, and user-facing design
  - Strategic vision and mission
  - Feature specifications and requirements
  - UI/UX design artifacts (wireframes, mockups, user flows)
  - User research and feedback

- **`docs/engineering/`** - Technical documentation, architecture decisions, and development guides
  - Architecture Decision Records (ADRs)
  - Technical design documents
  - API documentation and schemas
  - Development guides and tutorials
  - Technology evaluations and references

### Optional Directories (Add as Needed)

- **`docs/architecture/`** - System-level design and cross-cutting concerns
  - System architecture diagrams
  - Infrastructure design
  - Data models and schemas
  - Integration patterns

- **`docs/planning/`** - Project management and execution artifacts
  - Project plans and roadmaps
  - Sprint/iteration plans
  - Estimates and sequencing
  - Retrospectives and post-mortems

- **`docs/operations/`** - Deployment, monitoring, and operational knowledge
  - Deployment guides
  - Runbooks and incident response
  - Monitoring and alerting setup
  - Infrastructure as code documentation

> **When compound-engineering is in use**: CE-skill outputs add the following paths to the documentation tree — `docs/ideation/`, `docs/brainstorms/`, `docs/plans/` (subsumes `docs/planning/`), `docs/solutions/`. See [`process/compound-engineering-integration.md`](./compound-engineering-integration.md) § 2 for the full path mapping and precedence rule.

## File Naming Conventions

- Use lowercase kebab-case: `feature-name.md`, `api-design.md`
- Be descriptive: `grpc-bidirectional-streaming.md` not `grpc.md`
- Date-prefix for time-sensitive docs: `2025-01-q1-roadmap.md`
- Version-suffix when needed: `api-spec-v2.md`

## Documentation Types and When to Create Them

### Product Specifications

**When:** Before building a feature that involves user interaction or business logic

**Format:** Lightweight spec covering:
- **Intent**: What problem does this solve and why?
- **Requirements**: What must this do? (functional requirements)
- **Constraints**: What must this NOT do or work within? (non-functional requirements)
- **UI/UX**: Wireframes or mockups for user-facing features
- **Success criteria**: How do we know it works?

**Location:** `docs/product/features/feature-name.md`

### Technical Design Documents

**When:** Before implementing complex technical features, architectural changes, or integrations

**Format:** Spec-driven approach:
- **Context**: What's the technical problem or requirement?
- **Approach**: Proposed solution and alternatives considered
- **Design**: Key components, data flow, APIs, protocols
- **Implementation plan**: Sequenced steps, dependencies, milestones
- **Testing strategy**: How to validate correctness

**Location:** `docs/engineering/designs/feature-name.md`

### Architecture Decision Records (ADRs)

**When:** Making significant technical decisions with long-term implications

**Format:** Brief record:
- **Decision**: What was decided?
- **Context**: What factors influenced this?
- **Consequences**: What are the tradeoffs?

**Location:** `docs/engineering/adr/NNNN-decision-name.md` (numbered sequentially)

### API Documentation

**When:** Defining or changing public APIs, gRPC services, REST endpoints

**Format:** Schema-first approach:
- Protocol buffer definitions (`.proto` files)
- OpenAPI/Swagger specs
- Usage examples and integration guides

**Location:** `docs/engineering/api/` or co-located with code

## Best Practices

### Write Specifications Before Code

For any non-trivial feature, write a spec first. This clarifies intent, surfaces questions early, and serves as a contract for AI-assisted development. The spec becomes the source of truth—code implements the spec, not the other way around.

### Keep It Current

Documentation that falls out of sync with reality is worse than no documentation. When code changes, update the relevant spec or design doc. When decisions change, update the ADR with a new entry rather than editing history.

### Document Decisions, Not Obvious Facts

Don't document what the code already makes clear. Document *why* decisions were made, what alternatives were considered, and what constraints exist. Context and rationale age better than implementation details.

### Use Diagrams Sparingly

A good diagram is worth a thousand words. A bad diagram creates confusion. Only add diagrams when they genuinely clarify structure or flow. ASCII art and mermaid diagrams in Markdown work well for simple cases.

### README.md Files

Each `docs/` subdirectory should have a `README.md` that:
- Explains what goes in that directory
- Links to key documents
- Provides navigation for new contributors

## Maintenance

### Review Cycle

Documentation should be reviewed during:
- Code review: Does this PR need documentation updates?
- Sprint retrospectives: What documentation would have helped?
- Quarterly audits: What's stale or missing?

### Archival

When documentation becomes obsolete, don't delete it—move it to `docs/archive/` with a note explaining why and when it was superseded. Historical context has value.

## Anti-Patterns to Avoid

- **Documentation Theater**: Writing docs that nobody reads to satisfy process
- **Premature Documentation**: Detailed specs for features that may never be built
- **Duplicated Information**: Maintaining the same information in multiple places
- **Overly Formal Process**: Heavyweight templates and approval workflows for early-stage work
- **Stale Documentation**: Docs that haven't been updated and no longer reflect reality

## Tools and Formats

### Primary Format: Markdown

All documentation uses Markdown (`.md`) for:
- Version control friendly (clear diffs)
- Human readable in any text editor
- Widely supported rendering (GitHub, VS Code, static site generators)

### Diagrams

- **Mermaid**: For sequence diagrams, flowcharts, and simple architecture diagrams embedded in Markdown
- **Draw.io/Excalidraw**: For complex system diagrams, export as SVG and commit with source
- **ASCII art**: For simple protocol flows and data structures

### Wireframes and Mockups

- **HTML mockups**: Primary approach for wireframes and UI design. High-fidelity HTML/CSS provides:
  - Version control friendly (clear diffs, easy review)
  - Interactive and responsive preview
  - Direct translation to implementation
  - Can be committed directly to repository
- **Hand-drawn sketches**: Secondary option for very early exploration, scan or photograph and include in specs
- **Design tools (Figma/Sketch/Excalidraw)**: Secondary option when HTML is impractical, export as images and commit, link to source files

## Getting Started

For a new repository:

```bash
mkdir -p docs/{product,engineering}
echo "# Project Documentation" > docs/README.md
```

Add subdirectories only when needed. Start minimal, expand as complexity grows.
