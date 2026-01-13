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
