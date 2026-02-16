# Code Quality Standards

Language and stack-specific code quality standards and best practices.

## Purpose

This directory contains standards for code quality, formatting, linting, testing, and conventions specific to programming languages and technology stacks.

## Standards

### [Python Project Standards](./python-standards.md)

Modern tooling and practices for Python command-line and library projects:
- **Tool stack** - uv, pyenv, make, ruff, mypy, pytest, pre-commit
- **Project structure** - src-layout, test organization, documentation
- **Code quality** - Linting, formatting, type checking, Google-style docstrings
- **Testing** - pytest with coverage (80%+ target), unit and integration tests
- **Security** - detect-secrets, pip-audit vulnerability scanning
- **Docker** - Multi-stage builds with python-slim, non-root user
- **CI/CD** - GitHub Actions with matrix testing across Python versions

**Key principle**: Automated, consistent development environment with fast feedback and security scanning.

### [Database Standards](./database-standards.md)

PostgreSQL conventions and practices for application database design:
- **Engine** - PostgreSQL with standard extensions (pg_trgm, pgcrypto)
- **Schema design** - Per-domain schemas forming a DAG, no circular dependencies
- **Naming conventions** - snake_case, plural tables, prefixed constraints (`pk_`, `fk_`, `uq_`, `idx_`, `ck_`)
- **Standard columns** - UUID v7 primary keys, `created_at`/`updated_at` with triggers
- **Data access** - Direct SQL with psycopg 3, Pydantic models for validation (no ORM)
- **Migrations** - golang-migrate with per-schema directories, up/down pairs
- **Security** - Parameterized queries, least-privilege database roles, secrets via environment variables

**Key principle**: The database is the source of truth for data integrity. Use SQL directly, let PostgreSQL enforce constraints.

## Future Standards

Examples of standards that will be added:

- **go.md** - Go code standards (gofmt, golint, error handling, conventions)
- **typescript.md** - TypeScript/JavaScript standards (ESLint, Prettier, React conventions)
- **rust.md** - Rust code standards (rustfmt, clippy, conventions)

## Relationship to Templates

Code standards defined here should be pre-configured in corresponding project templates:
- `code/python-standards.md` standards → implemented in `templates/python-cli/` or `templates/python-fastapi/`
- `code/typescript.md` standards → implemented in `templates/nextjs-webapp/`

## Status

**Active** - Python standards complete. Additional language standards will be added as projects adopt specific stacks.
