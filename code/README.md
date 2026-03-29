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
- **Engine** - PostgreSQL 18+ with standard extensions (pg_trgm, pgcrypto)
- **Schema design** - Per-domain schemas forming a DAG, no circular dependencies
- **Naming conventions** - snake_case, plural tables, prefixed constraints (`pk_`, `fk_`, `uq_`, `idx_`, `ck_`)
- **Standard columns** - UUID v7 primary keys, `created_at`/`updated_at` with triggers
- **Data access** - Direct SQL with psycopg 3, Pydantic models for validation (no ORM)
- **Migrations** - golang-migrate with per-schema directories, up/down pairs
- **Security** - Parameterized queries, least-privilege database roles, secrets via environment variables

**Key principle**: The database is the source of truth for data integrity. Use SQL directly, let PostgreSQL enforce constraints.

### [Web Application Standards](./web-application-standards.md)

Full-stack web application standards for Next.js + FastAPI projects in a Turborepo monorepo:
- **Monorepo structure** - Turborepo for TypeScript, Make for Python, npm workspaces
- **Frontend** - Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query
- **Backend** - FastAPI, Pydantic, psycopg 3 (follows Python and Database standards)
- **API integration** - Auto-generated TypeScript client from FastAPI's OpenAPI schema
- **Authentication** - Auth.js with JWT tokens issued by FastAPI
- **Testing** - Vitest for components, Playwright for E2E, pytest for backend
- **CI/CD** - GitHub Actions with API client staleness checks
- **Docker** - Multi-stage builds, Docker Compose for full stack

**Key principle**: The OpenAPI schema is the contract between frontend and backend. Auto-generate the TypeScript client so the two sides stay in sync without manual effort.

## Future Standards

Examples of standards that will be added:

- **go.md** - Go code standards (gofmt, golint, error handling, conventions)
- **typescript.md** - Standalone TypeScript/JavaScript standards (ESLint, Prettier, non-web conventions)
- **rust.md** - Rust code standards (rustfmt, clippy, conventions)

## Relationship to Templates

Code standards defined here should be pre-configured in corresponding project templates:
- `code/python-standards.md` standards → implemented in `templates/python-cli/` or `templates/python-fastapi/`
- `code/typescript.md` standards → implemented in `templates/nextjs-webapp/`

## Status

**Active** - Python, Database, and Web Application standards complete. Additional language standards will be added as projects adopt specific stacks.
