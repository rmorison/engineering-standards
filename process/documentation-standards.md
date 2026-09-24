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

- **`docs/experiments/`** - Experiment and spike briefs
  - One brief per timeboxed exploration
  - Question, approach, success signal, and timebox
  - Findings recorded in the brief when the exploration closes

- **`docs/operations/`** - Deployment, monitoring, and operational knowledge
  - Deployment guides
  - Runbooks and incident response
  - Monitoring and alerting setup
  - Infrastructure as code documentation

> **When compound-engineering is in use**: CE-skill outputs add the following paths to the documentation tree — `docs/ideation/`, `docs/plans/` (subsumes `docs/planning/`; carries both `ce-brainstorm` and `ce-plan` output), `docs/solutions/`. Legacy `docs/brainstorms/` is still read but no longer written. See [`process/compound-engineering-integration.md`](./compound-engineering-integration.md) § 2 for the full path mapping and precedence rule.

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

### Automated Checks

This repository's product is Markdown, so a rendering defect is a production defect. `scripts/check-docs.mjs` runs on every pull request touching a `.md` file, and each check exists because the defect it looks for reached the default branch. The last row is the one exception, described below:

| Check | Catches |
|-------|---------|
| Mermaid diagrams parse | A diagram that shows an error box instead of a graph on GitHub |
| Relative links resolve | A link to a moved or renamed file |
| Link anchors name a real heading | A link to `#section` whose heading was renamed, in this file or another |
| No blockquote inside a list item | `- >3 months` renders as a quote block with the `>` swallowed |
| No unmarked marker lists | Marker-prefixed lines with no list marker collapse into one paragraph |
| Every code fence is closed | An unterminated fence makes the rest of the file invisible to the checks above |
| No fence nested in one the same length | A quoted template whose own fences are the same length ends early, spilling the rest into the document |
| No absolute home-directory path | A path out of a contributor's machine, disclosing a local username and directory layout to every reader of a public repository |
| Template kit hook entries register and behave | A `.claude/settings.json` hook entry with no `hooks` array, an unknown key on the matcher, a command naming a script that is not in the tree, a permission rule that auto-approves what the kit's own prose says reaches a human, or a hook command that exits 2 when its path fails to resolve — which on `PreToolUse` refuses every write |
| Secret reference examples hold only references | A `secret-refs.env` example in `code/python-standards.md` that holds a literal, quotes, `$`, an inline comment, a browser-exposed key, a repeated key, or a key its `example.env` example also defines. A pass means only that the examples are well-formed |

The anchor check matters here because this repository routes rules through "one
document owns it, the others link to it": renaming a heading breaks links in
files that did not change. Slugs come from `github-slugger`, the library
GitHub's own Markdown pipeline uses, so what CI accepts is what GitHub renders.

The link, blockquote and marker-list checks skip fenced code blocks, and the
link check also ignores inline code spans. That is deliberate: documentation has
to be able to show a defect without committing one, and a check that cannot be
shown its own defect is a check nobody can plant a defect in. The blockquote and
marker-list checks read the raw line, because a leading code span already
displaces the marker they look for.

The home-directory check is the deliberate exception on both counts: it reads
fenced lines, and it ignores the skip list that keeps `archive/`, `docs/plans/`
and `scripts/` out of the checks above. An example of a leaked path still
discloses the path, and those three directories are exactly where the one that
reached the default branch was sitting. Its pattern is a shape rather than a
list of forbidden strings, because a denylist would have to contain the values
it exists to keep out of the repository.

When it fires, write `~/`, `$HOME/`, or a `<username>` metavariable in place of
the home prefix, or a repository-relative path when the target is in this
repository. Paths whose user directory names a service or a placeholder rather
than a person — `/home/runner/` in a GitHub Actions log excerpt,
`/home/linuxbrew/` in a Homebrew setup line, `/home/vscode/`, `/home/node/`,
`/home/user/`, `/Users/you/` — are allowed verbatim, from a short allowlist in
the script. The allowlist exists because those paths have no substitute
spelling: a Homebrew prefix quoted as `~/` is wrong, and a log excerpt is
evidence only verbatim. A rule with no answer for the legitimate case gets
suppressed by deleting the check.

Run them before pushing:

```bash
npm ci --prefix scripts && node scripts/check-docs.mjs
```

The template kit row is not a Markdown check. `scripts/check-template-kit.mjs`
runs as a second job in the same workflow, over every `.claude/settings.json` in
the tree, because the starter kit in `templates/.claude/` is copied into adopters'
projects and both of its hook entries were malformed from the day it shipped.

It does three kinds of work, not one. Most assertions are structural and read
the JSON. The permission sweep matches every `allow` entry against commands that
must be approved and commands that must not, so the kit's prose about what
reaches a human is checked rather than asserted. And for the kit's own settings
file it *runs* the hook commands, because the defect that shipped hardest — a
command that exits 2 when its path fails to resolve, refusing every write — is
invisible to any amount of reading. That last part executes content from the
checkout, which is why the job must never be given secrets or a write token.
It needs no dependencies:

```bash
node scripts/check-template-kit.mjs
```

The secret reference row is not a Markdown check either, and no shipped defect
prompted it: it is preventive. `scripts/check-secret-refs.mjs` holds the rule in
[Secrets](../code/python-standards.md#secrets), that a committed `secret-refs.env`
contains references into a secret manager and never a secret. It runs as a third
job with no dependencies, proves its line classifier against built-in fixtures
before it reads any file, and with `--standard` checks the standard's own
example blocks, so the standard cannot show an example its rule rejects. A
project that adopts the rule runs the same script on its own files. A pass does
not mean a reference resolves or that no secret sits elsewhere in the tree:

```bash
node scripts/check-secret-refs.mjs --standard
node scripts/check-secret-refs.mjs secret-refs.env --config example.env
```

The Mermaid check calls mermaid's `parse()` rather than rendering, because the two disagree — the render path accepts diagrams GitHub's parser rejects. Dependencies are pinned and installed from a committed lockfile so the check reproduces one specific parser.

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
