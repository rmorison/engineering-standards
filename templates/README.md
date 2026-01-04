# Project Templates

Project scaffolding and boilerplate for common application scenarios.

## Purpose

This directory contains starter templates for different technology stacks and application types. Each template implements the code quality standards defined in `../code/` and follows the process standards in `../process/`.

## Future Templates

Examples of templates that will live here:

- **python-fastapi/** - FastAPI backend service with async Python
  - Pre-configured: black/ruff, pytest, Docker, CI/CD
  - Implements standards from `code/python.md`

- **nextjs-webapp/** - Next.js web application with TypeScript
  - Pre-configured: ESLint, Prettier, testing, deployment
  - Implements standards from `code/typescript.md`

- **go-daemon/** - Go service daemon
  - Pre-configured: gofmt, golint, testing, systemd service
  - Implements standards from `code/go.md`

- **python-cli/** - Python command-line application
  - Pre-configured: Click/Typer, packaging, testing
  - Implements standards from `code/python.md`

## Template Structure

Each template should include:
- **README.md** - Usage instructions and customization guide
- **Pre-configured tooling** - Linters, formatters, pre-commit hooks matching code standards
- **Example code** - Minimal working example demonstrating best practices
- **CI/CD configuration** - GitHub Actions or similar
- **Documentation templates** - Following `process/documentation-standards.md`

## Usage

1. Copy template directory to your new project location
2. Search and replace placeholder names (project name, author, etc.)
3. Customize as needed while maintaining code standards
4. Remove example code and build your application

## Status

**Placeholder** - Templates will be added as common patterns emerge from project work.
