# Project CLAUDE.md Template

<!-- Copy this file to your project root as CLAUDE.md and customize each section. -->

## Project Identity

**Project Name**: <!-- your project name -->

**Tech Stack**: <!-- e.g., Python 3.12, FastAPI, PostgreSQL, React -->

**Repository**: <!-- link to repo -->

## AI Behavior

### Plan Before Implement
Always read the relevant spec and existing code before making changes.
Present a plan and wait for confirmation before writing any code.

When [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin)
is in use, `/ce-plan` produces the plan and `/ce-work` executes it
iteratively against U-IDs and acceptance criteria; the `lfg` autonomous
flow runs without per-step confirmation when a complete plan exists.
See `process/compound-engineering-integration.md`.

### Permissions and Hooks
What the permission rules in `.claude/settings.json` do and do not stop, and
why a `PreToolUse` hook rather than a rule is where a check you need to hold
goes, is stated once, in the standards repository's
[`templates/README.md`](https://github.com/rmorison/engineering-standards/blob/main/templates/README.md#permissions-and-hooks).
Read it before widening the allow list.

The link is absolute on purpose. This file is copied to your project root,
where a relative `README.md` would resolve to *your* README, which has no
such section. The kit references canonical standards by URL for the same
reason its skills do: so a project that adopts the kit does not fork the
standards along with it.

### Standards References
- Feature workflow: process/feature-development-workflow.md
- Documentation: process/documentation-standards.md
- Git conventions: process/git-branching-strategy.md
- Compound-engineering integration (when CE is installed): process/compound-engineering-integration.md

### AI Architecture
This template assumes the six-layer AI architecture defined in
`ai/claude-code/README.md`. The architecture is the abstraction;
specific toolkits realize the layers:

- **Layer 1 (Rules)** is this file. A project-root `CLAUDE.md` is what
  Layer 1 looks like in Claude Code — always loaded, kept small, pointing
  at the rest of the architecture rather than restating it. The standards
  repository's own Layer 1 lives in its `ai/claude-code/rules/`, which is
  where to look for baseline rule content to draw on; it is not copied
  into your project.
- **Layer 6 (Hooks)** is `.claude/hooks/`, seeded from the example
  `PreToolUse` and `PostToolUse` scripts in the kit (vendor-neutral;
  shipped by the standards repo).
- **Layers 2 (Skills) and 3 (Agents)** have vendor-neutral baselines
  in `templates/.claude/skills/` and `templates/.claude/agents/`. When
  compound-engineering is installed, CE skills (`/ce-brainstorm`,
  `/ce-plan`, `/ce-work`, `/ce-doc-review`, `/ce-code-review`, etc.)
  and CE persona reviewers are the canonical realization of those
  layers. See `process/compound-engineering-integration.md` for what
  CE puts in each slot.
- **Layers 4 (References) and 5 (Compound)** are realized by CE today;
  non-CE projects may leave them empty or fill with hand-rolled
  implementations.

For the architectural decision and full layer descriptions, see
`docs/engineering/adr/0001-six-layer-ai-architecture.md` and
`ai/claude-code/README.md` (paths assume the standards repo is
checked out at the same level; adjust as needed for your project).

### Module Boundaries
Each module has a single responsibility. Do not move logic between modules
to make a quick fix. If a fix requires crossing a module boundary, raise it
for discussion first.

<!-- Define your project's module boundaries here. Example:
- Classification logic: classifier.py only
- Routing decisions: router.py only
- API writes: api_client.py only
- Cross-boundary changes require a plan discussion before implementation
-->

### Validation
After each meaningful change: run tests, run lint, confirm the change does
what the spec says. Do not proceed to the next task until the current one
is verified.

## Key Conventions

<!-- Project-specific conventions. Examples:
- All API endpoints require OpenAPI schema definitions
- Database migrations use Alembic with descriptive names
- Tests follow Arrange-Act-Assert pattern
-->

## Active Milestones

<!-- Current milestones and epics. Example:
- v2.0 API Redesign: issues #10-#25
-->

## Important Notes

<!-- Anything Claude Code must know about this project. Examples:
- The legacy module in src/legacy/ is frozen — do not modify
- Environment variables are documented in .env.example
- CI runs on every push; all checks must pass before merge
-->
