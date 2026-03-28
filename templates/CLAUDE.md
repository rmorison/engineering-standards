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

### Standards References
- Feature workflow: process/feature-development-workflow.md
- Documentation: process/documentation-standards.md
- Git conventions: process/git-branching-strategy.md

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
