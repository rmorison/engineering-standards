# Python Project Standards

*Modern tooling and practices for Python command-line and library projects*

## Overview

This document defines standards for Python-based computational engine projects, covering project structure, tooling, code quality, testing, and deployment. These standards prioritize:

- **Developer experience** - Fast setup, consistent tooling, clear workflows
- **Code quality** - Type safety, linting, formatting, security scanning
- **Automation** - Pre-commit checks, CI/CD, reproducible builds
- **Maintainability** - Clear structure, comprehensive testing, documentation

**Core principle**: Establish a consistent, automated development environment that catches issues early and enables confident iteration.

## Philosophy

### Modern Python Tooling

Use contemporary tools that solve problems better than traditional approaches:
- **uv** over pip/pip-tools - Faster, simpler dependency management
- **ruff** over pylint/black/isort - Single tool for formatting and linting
- **pyproject.toml** over setup.py/setup.cfg - Standardized project metadata

### Automation First

Automate everything that can be automated:
- Environment setup via `make setup`
- Quality checks via pre-commit hooks
- Testing and validation via CI/CD
- Security scanning as part of the workflow

### Type Safety Without Ceremony

Use type hints for public APIs and complex logic, but don't over-annotate:
- Type hints improve IDE support and catch bugs
- mypy validates type correctness
- Focus on interfaces and contracts, not every variable

### Library Neutrality

These standards focus on project structure and development workflow, not application frameworks. Library choices (web frameworks, ETL tools, CLI parsers) are intentionally left to individual projects.

---

## Tool Stack

### Core Tools

| Tool | Purpose | Rationale |
|------|---------|-----------|
| **uv** | Package manager | Fast, reliable dependency resolution and environment management |
| **pyenv** | Python version manager | Manage multiple Python versions (installed outside project) |
| **make** | Build automation | Simple, universal task runner for setup, test, lint, etc. |
| **ruff** | Linter & formatter | Fast, comprehensive linting and formatting in one tool |
| **mypy** | Type checker | Static type checking for improved correctness |
| **pytest** | Test framework | Industry standard with excellent plugin ecosystem |
| **pytest-cov** | Coverage reporting | Integrated coverage measurement |
| **pre-commit** | Git hooks | Automated quality checks before commits |
| **detect-secrets** | Secret scanning | Prevent committing credentials and sensitive data |
| **pip-audit** | Vulnerability scanner | Check dependencies for known security vulnerabilities |

### Development Environment

- **Virtual environment**: `.venv/` managed by uv
- **Python versions**: Managed by pyenv (not committed to repository)
- **Configuration**: `pyproject.toml` (primary), `.pre-commit-config.yaml`, `Makefile`

### Containerization

- **Base image**: `python:3.x-slim` (official Python slim images)
- **Multi-stage builds**: Builder stage + minimal runtime stage
- **Non-root user**: Run containers as non-root for security

### CI/CD

- **Platform**: GitHub Actions
- **Triggers**: All pushes and pull requests
- **Checks**: Unit tests, integration tests, linting, type checking, coverage

---

## Project Structure

### Standard Layout

```
project-name/
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI/CD pipeline
│       └── release.yml         # Release automation (optional)
├── docs/                       # Documentation per documentation-standards.md
│   ├── product/
│   └── engineering/
├── src/
│   └── project_name/           # Package source (use underscores)
│       ├── __init__.py
│       ├── py.typed            # PEP 561 marker for type hints
│       └── ...
├── tests/
│   ├── unit/                   # Unit tests (fast, isolated)
│   ├── integration/            # Integration tests (slower, dependencies)
│   └── conftest.py             # Shared pytest fixtures
├── scripts/                    # Development/deployment scripts
├── .venv/                      # Virtual environment (gitignored)
├── .pre-commit-config.yaml     # Pre-commit hook configuration
├── .python-version             # Python version for pyenv
├── pyproject.toml              # Project metadata and tool configuration
├── uv.lock                     # Locked dependencies (commit this)
├── Makefile                    # Development task automation
├── Dockerfile                  # Production container image
├── .dockerignore               # Docker build exclusions
├── .gitignore                  # Git exclusions
└── README.md                   # Project overview and quick start
```

### Directory Conventions

**`src/project_name/`** - Source code in src-layout
- Prevents accidental imports of source code without installation
- Clearer separation between source and tests
- Better support for building distributions

**`tests/unit/` and `tests/integration/`** - Separate test types
- Unit tests: Fast, no external dependencies, mock extensively
- Integration tests: Test real interactions, may require services

**`docs/`** - Follow [documentation-standards.md](../process/documentation-standards.md)
- Product specs, technical designs, ADRs
- Keep code and docs in same repository

**`scripts/`** - Utilities for development and deployment
- Database migrations, data processing, deployment automation
- Not part of the installed package

---

## Development Environment Setup

### Prerequisites

**Install pyenv** (one-time setup per machine):

```bash
# macOS
brew install pyenv

# Linux
curl https://pyenv.run | bash
```

Add to shell profile (`~/.bashrc`, `~/.zshrc`):

```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

**Install uv** (one-time setup per machine):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Project Setup

**Initial setup** (developers and CI):

```bash
make setup
```

This command:
1. Installs the Python version specified in `.python-version` via pyenv
2. Creates virtual environment in `.venv/` via uv
3. Installs dependencies (including dev dependencies)
4. Installs pre-commit hooks
5. Runs initial tests to verify setup

### Makefile Targets

Standard `Makefile` should provide these targets:

```makefile
.PHONY: setup
setup:  ## Initial project setup (install Python, deps, pre-commit)
	# Check for pyenv and install Python version
	# Create .venv with uv
	# Install dependencies
	# Install pre-commit hooks
	# Run tests to verify

.PHONY: test
test:  ## Run unit tests with coverage
	uv run pytest tests/unit/ --cov=src/project_name --cov-report=term --cov-report=html

.PHONY: test-integration
test-integration:  ## Run integration tests
	uv run pytest tests/integration/

.PHONY: test-all
test-all:  ## Run all tests with coverage
	uv run pytest tests/ --cov=src/project_name --cov-report=term --cov-report=html

.PHONY: lint
lint:  ## Run ruff linter
	uv run ruff check src/ tests/

.PHONY: format
format:  ## Format code with ruff
	uv run ruff format src/ tests/

.PHONY: format-check
format-check:  ## Check code formatting without changes
	uv run ruff format --check src/ tests/

.PHONY: typecheck
typecheck:  ## Run mypy type checking
	uv run mypy src/

.PHONY: security
security:  ## Run security scans (secrets and vulnerabilities)
	uv run detect-secrets scan --baseline .secrets.baseline
	uv run pip-audit

.PHONY: pre-commit
pre-commit:  ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

.PHONY: check
check: lint format-check typecheck security test  ## Run all checks (CI equivalent)

.PHONY: clean
clean:  ## Remove generated files
	rm -rf .venv/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +

.PHONY: help
help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
```

**Default target**: Show help when running `make` without arguments

```makefile
.DEFAULT_GOAL := help
```

---

## Dependency Management with uv

### pyproject.toml Structure

```toml
[project]
name = "project-name"
version = "0.1.0"
description = "Brief project description"
readme = "README.md"
requires-python = ">=3.11"
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
license = {text = "MIT"}  # or Apache-2.0, GPL-3.0, etc.

# Runtime dependencies
dependencies = [
    "requests>=2.31.0",
    # Add application dependencies here
]

# Optional dependencies for extras
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.6.0",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
    "detect-secrets>=1.4.0",
    "pip-audit>=2.7.0",
]

# Entry points for CLI tools
[project.scripts]
project-cli = "project_name.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# Tool configurations below
[tool.ruff]
# See Ruff Configuration section

[tool.mypy]
# See Type Checking section

[tool.pytest.ini_options]
# See Testing section
```

### Dependency Commands

```bash
# Add runtime dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Install all dependencies (including dev)
uv sync --all-extras

# Install only runtime dependencies
uv sync

# Update dependencies
uv lock --upgrade

# Remove dependency
uv remove package-name
```

### Lock File Management

- **Commit `uv.lock`** - Ensures reproducible builds across environments
- **Update regularly** - Run `uv lock --upgrade` periodically and test
- **Security patches** - Update lock file when vulnerabilities detected

### Python Version Support

**Policy**: Support last 3 stable minor versions of Python

**Rationale**: Balances adoption of new features with compatibility for users who haven't upgraded yet.

**As of early 2025**: Python 3.13 (Oct 2024), 3.12 (Oct 2023), 3.11 (Oct 2022) are the current stable versions. Python 3.10 reaches end-of-life in October 2025.

**Specify in pyproject.toml**:

```toml
# Support last 3 stable versions (update as new versions release)
requires-python = ">=3.11"
```

**Test in CI against all supported versions** (see CI/CD section)

**When to update**: Review version support policy annually or when a new major/minor Python version is released.

---

## Code Quality

### Ruff Configuration

Ruff handles both linting and formatting. Configure in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

# Source and test directories
src = ["src", "tests"]

[tool.ruff.lint]
# Enable rule sets
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort (import sorting)
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking
    "Q",      # flake8-quotes
]

# Disable specific rules if needed
ignore = [
    "E501",   # Line too long (handled by formatter)
]

# Per-file ignores
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "S101",   # Allow assert in tests
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Type Checking with mypy

Configure in `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
disallow_subclassing_any = true
disallow_untyped_calls = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true

# Relax for tests
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
disallow_untyped_calls = false
```

**Type hint guidelines**:

1. **Always type public APIs** - Functions, classes, methods in src/
2. **Type complex internal logic** - Helps catch bugs and improves IDE support
3. **Use `py.typed` marker** - Include empty `src/project_name/py.typed` file (PEP 561)
4. **Tests can be more relaxed** - Strict typing in tests often unnecessary

### Docstring Style: Google Format

```python
def calculate_metrics(data: list[dict], threshold: float = 0.5) -> dict[str, float]:
    """Calculate summary metrics from input data.

    Processes a list of data points and computes aggregate metrics
    based on the specified threshold.

    Args:
        data: List of data point dictionaries with 'value' keys.
        threshold: Minimum value threshold for inclusion. Defaults to 0.5.

    Returns:
        Dictionary with metric names as keys and computed values.

    Raises:
        ValueError: If data is empty or threshold is negative.

    Example:
        >>> data = [{"value": 0.8}, {"value": 0.3}]
        >>> calculate_metrics(data, threshold=0.5)
        {'count': 1, 'mean': 0.8}
    """
    if not data:
        raise ValueError("Data cannot be empty")
    # Implementation...
```

**Guidelines**:
- **Public functions and classes**: Always include docstrings
- **Private functions**: Docstrings optional but recommended for complex logic
- **One-line docstrings**: For simple, obvious functions
- **Multi-line docstrings**: Include Args, Returns, Raises sections as needed

---

## Testing with pytest

### Test Organization

```
tests/
├── conftest.py           # Shared fixtures
├── unit/                 # Fast, isolated tests
│   ├── test_parser.py
│   └── test_utils.py
└── integration/          # Slower, real dependencies
    └── test_workflow.py
```

### pytest Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",  # Show summary of all test outcomes
]

# Markers for categorizing tests
markers = [
    "unit: Unit tests (fast, isolated)",
    "integration: Integration tests (slower, dependencies)",
    "slow: Tests that take significant time",
]
```

### Coverage Requirements

**Minimum coverage**: 80% for new projects, 90% target for mature projects

**Coverage configuration**:

```toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/.venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

**Run tests with coverage**:

```bash
make test  # Unit tests only
make test-integration  # Integration tests only
make test-all  # All tests with coverage report
```

### Test Guidelines

**Unit tests**:
- Test one function/class per test file
- Mock external dependencies
- Fast execution (milliseconds per test)
- Use parametrize for multiple test cases

**Integration tests**:
- Test real interactions between components
- May require database, files, or external services
- Slower execution acceptable
- Use fixtures for setup/teardown

**Example**:

```python
import pytest
from project_name.parser import parse_config


@pytest.mark.unit
def test_parse_config_valid():
    """Test parsing valid configuration."""
    config_str = '{"key": "value"}'
    result = parse_config(config_str)
    assert result == {"key": "value"}


@pytest.mark.unit
@pytest.mark.parametrize("invalid_input", [
    "",
    "not json",
    "{'single': 'quotes'}",
])
def test_parse_config_invalid(invalid_input):
    """Test parsing invalid configuration raises ValueError."""
    with pytest.raises(ValueError):
        parse_config(invalid_input)


@pytest.mark.integration
def test_workflow_end_to_end(tmp_path):
    """Test complete workflow from input to output."""
    input_file = tmp_path / "input.txt"
    input_file.write_text("test data")

    result = run_workflow(input_file)

    assert result.success
    assert result.output_path.exists()
```

---

## Pre-commit Hooks

### Configuration

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: []  # Add type stub packages if needed
        args: [--strict, --ignore-missing-imports]

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

### Setup and Usage

```bash
# Install pre-commit hooks (part of make setup)
uv run pre-commit install

# Run hooks manually on all files
uv run pre-commit run --all-files

# Update hook versions
uv run pre-commit autoupdate

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

### Secrets Baseline

Initialize detect-secrets baseline:

```bash
uv run detect-secrets scan --baseline .secrets.baseline
```

**Review and commit `.secrets.baseline`** - Contains hashes of known false positives

**Update baseline when adding new files**:

```bash
uv run detect-secrets scan --baseline .secrets.baseline
```

---

## Security

### Secret Detection

**Tool**: detect-secrets pre-commit hook

**Purpose**: Prevent committing API keys, passwords, tokens

**Configuration**: See pre-commit section

**Handling false positives**:
1. Add to baseline: `detect-secrets scan --baseline .secrets.baseline`
2. Inline pragma: `password = "fake_password"  # pragma: allowlist secret`

### Dependency Vulnerability Scanning

**Tool**: pip-audit (official PyPA tool)

**Run manually**:

```bash
make security
# or
uv run pip-audit
```

**CI integration**: Include in GitHub Actions workflow

**Alternative**: [uv-secure](https://github.com/owenlamont/uv-secure) is a community tool specifically designed for uv.lock files. Native `uv audit` command is [under consideration](https://github.com/astral-sh/uv/issues/9189).

**Handling vulnerabilities**:
1. Update affected package: `uv add package-name@latest`
2. If no fix available, assess risk and document decision
3. Consider alternative packages if vulnerability is severe

### Best Practices

1. **Never commit secrets** - Use environment variables or secret management services
2. **Use `.env` files locally** - Add to `.gitignore`
3. **Scan dependencies regularly** - Weekly or on each PR
4. **Pin dependencies** - Lock file ensures reproducible, scannable builds
5. **Review direct and transitive dependencies** - Understand what you depend on

---

## Docker Builds

### Multi-stage Dockerfile

Use `python:3.x-slim` base for smaller, more secure images:

```dockerfile
# Builder stage
FROM python:3.11-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies to /app/.venv
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ /app/src/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Command
CMD ["python", "-m", "project_name"]
```

### .dockerignore

```
.venv/
.git/
.github/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
dist/
*.egg-info/
__pycache__/
*.pyc
*.pyo
*.pyd
.DS_Store
.env
.env.local
```

### Build and Run

```bash
# Build image
docker build -t project-name:latest .

# Run container
docker run -it --rm project-name:latest

# Development: mount source for live reload
docker run -it --rm -v $(pwd)/src:/app/src project-name:latest
```

### Best Practices

1. **Use slim base images** - Smaller attack surface, faster builds
2. **Multi-stage builds** - Separate build dependencies from runtime
3. **Non-root user** - Security best practice
4. **Layer caching** - Copy dependency files before source code
5. **Pin Python version** - `python:3.11-slim`, not `python:slim`

---

## Documentation

### Code Documentation

**Follow [documentation-standards.md](../process/documentation-standards.md)**:

- `docs/product/` - Product specs and features
- `docs/engineering/` - Technical designs and ADRs
- `docs/engineering/api/` - API documentation

### README.md Template

```markdown
# Project Name

Brief description (1-2 sentences).

## Features

- Key feature 1
- Key feature 2

## Quick Start

### Prerequisites

- Python 3.11+ (managed via pyenv)
- uv package manager
- make

### Installation

```bash
make setup
```

### Usage

```bash
# Command line
project-cli --help

# Library
from project_name import main_function
```

## Development

```bash
make help           # Show all available commands
make test           # Run unit tests
make test-all       # Run all tests with coverage
make lint           # Run linter
make format         # Format code
make typecheck      # Type check
```

## Documentation

See `docs/` directory for:
- Architecture decisions
- Technical designs
- API documentation

## License

[License Name] - See LICENSE file
```

### API Documentation

**For libraries with public APIs**:

1. **Docstrings in code** - Google style
2. **Type hints** - Enables auto-generated docs
3. **Sphinx or mkdocs** (optional) - Generated HTML documentation

**Example with mkdocs**:

```bash
# Add to dev dependencies
uv add --dev mkdocs mkdocs-material

# Create docs/api/ directory
mkdir -p docs/api

# Generate from docstrings
uv run mkdocs build
```

---

## CI/CD with GitHub Actions

### Workflow Configuration

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: |
          uv sync --all-extras

      - name: Run linting
        run: uv run ruff check src/ tests/

      - name: Check formatting
        run: uv run ruff format --check src/ tests/

      - name: Type checking
        run: uv run mypy src/

      - name: Run unit tests
        run: uv run pytest tests/unit/ --cov=src/project_name --cov-report=xml

      - name: Run integration tests
        run: uv run pytest tests/integration/

      - name: Security scan
        run: |
          uv run detect-secrets scan --baseline .secrets.baseline
          uv run pip-audit

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### CI Best Practices

1. **Test on all supported Python versions** - Use matrix strategy
2. **Run all checks** - Lint, format, type check, test, security
3. **Fast feedback** - Fail fast, parallelize when possible
4. **Coverage reporting** - Use codecov or similar
5. **Dependency caching** - Cache `.venv/` to speed up builds

### Required Status Checks

Configure branch protection for `main`:
- ✅ Require CI workflow to pass
- ✅ Require up-to-date branches
- ✅ Require at least 1 approval for PRs

---

## Best Practices

### Development Workflow

1. **Start with specs** - Write docs/engineering/designs/ before code
2. **Use virtual environments** - Always work in `.venv/`
3. **Run tests frequently** - `make test` after changes
4. **Type check early** - Catch type errors before commit
5. **Let pre-commit do its job** - Don't skip hooks

### Code Organization

1. **Src layout** - Use `src/project_name/` structure
2. **Small modules** - One class or a few related functions per file
3. **Clear imports** - Absolute imports, organized by stdlib/third-party/local
4. **Avoid circular imports** - Restructure if needed

### Dependency Management

1. **Pin dependencies** - Commit `uv.lock` for reproducibility
2. **Update regularly** - Weekly or bi-weekly dependency updates
3. **Minimize dependencies** - Each dependency is a liability
4. **Audit new dependencies** - Check license, maintenance, security

### Testing Strategy

1. **Write tests first** - TDD when appropriate
2. **Test public APIs** - Internal implementation can change
3. **Mock external dependencies** - Unit tests should be fast
4. **Integration tests for workflows** - Test real interactions
5. **Aim for high coverage** - But don't obsess over 100%

### Security

1. **Never commit secrets** - Use environment variables
2. **Scan dependencies** - Run security checks in CI
3. **Update dependencies promptly** - Apply security patches quickly
4. **Use type checking** - Prevents many runtime errors
5. **Run containers as non-root** - Security best practice

---

## Anti-Patterns

### ❌ Committing Virtual Environment

**Problem**: `.venv/` in git makes repository huge and causes conflicts

**Solution**: Add `.venv/` to `.gitignore`, use `uv.lock` for reproducibility

### ❌ Missing Type Hints on Public APIs

**Problem**: No IDE support, easy to misuse, bugs at runtime

**Solution**: Always type public functions/classes, use mypy to validate

### ❌ Skipping Pre-commit Hooks

**Problem**: Broken code reaches PR, wastes reviewer time

**Solution**: Let hooks run, fix issues locally before pushing

### ❌ Not Testing Edge Cases

**Problem**: Production failures from unexpected inputs

**Solution**: Use parametrize for multiple test cases, test error paths

### ❌ Outdated Dependencies

**Problem**: Security vulnerabilities, missing bug fixes

**Solution**: Update dependencies regularly, use pip-audit to scan

### ❌ Overly Broad Dependency Specifications

**Problem**: `package>=1.0` can pull incompatible versions

**Solution**: Let uv manage versions, commit lock file

### ❌ No Coverage for Critical Paths

**Problem**: Core functionality breaks in production

**Solution**: Prioritize testing critical paths, aim for 80%+ coverage

### ❌ Large Monolithic Modules

**Problem**: Hard to test, difficult to understand

**Solution**: Break into smaller modules with clear responsibilities

---

## Integration with Project Workflows

### Feature Development

When implementing features per [feature-development-workflow.md](../process/feature-development-workflow.md):

1. **Product Spec** → Clarify requirements
2. **Technical Design** → Reference this standard for tooling decisions
3. **Implementation** → Follow code quality and testing practices here
4. **Validation** → Use CI checks to validate quality

### Issue Tracking

Branch naming from issues (per [git-branching-strategy.md](../process/git-branching-strategy.md)):

```bash
# GitHub generates branch name from issue
git checkout 42-add-data-validation
```

CI runs on all branches, provides automated validation before PR review.

---

## When to Deviate

These standards assume:
- Python 3.11+ projects
- Library or command-line applications
- Team development with CI/CD

**Consider alternatives if**:
- **Python 2 or <3.11** - Use older tooling, adjust type checking
- **Very small scripts** - May skip full setup (but still use ruff, basic tests)
- **Embedded/constrained environments** - Docker slim images may be too large
- **Enterprise with different standards** - Follow organizational requirements, adapt where possible

**When deviating**:
- Document rationale in project README
- Consider creating an ADR in `docs/engineering/adr/`
- Maintain consistency within the project

---

## Example Project Setup

```bash
# Create project directory
mkdir my-project
cd my-project

# Initialize git
git init
echo ".venv/\n*.pyc\n__pycache__/\n.pytest_cache/\n.mypy_cache/\n.ruff_cache/" > .gitignore

# Set Python version
echo "3.11" > .python-version
pyenv install 3.11

# Create project structure
mkdir -p src/my_project tests/{unit,integration} docs/{product,engineering} scripts .github/workflows

# Initialize pyproject.toml
cat > pyproject.toml << 'EOF'
[project]
name = "my-project"
version = "0.1.0"
description = "Description"
requires-python = ">=3.11"

dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.6.0",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
    "detect-secrets>=1.4.0",
    "pip-audit>=2.7.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF

# Create Makefile (see Makefile section for full content)
touch Makefile

# Create pre-commit config (see Pre-commit section)
touch .pre-commit-config.yaml

# Run setup
make setup

# Initialize git
git add .
git commit -m "feat: initial project setup"
```

---

## References

### Tools
- [uv - Python package manager](https://github.com/astral-sh/uv)
- [pyenv - Python version management](https://github.com/pyenv/pyenv)
- [ruff - Linter and formatter](https://github.com/astral-sh/ruff)
- [mypy - Static type checker](https://mypy-lang.org/)
- [pytest - Testing framework](https://pytest.org/)
- [pre-commit - Git hook framework](https://pre-commit.com/)
- [detect-secrets - Secret scanning](https://github.com/Yelp/detect-secrets)

### Standards
- [PEP 8 - Style Guide](https://peps.python.org/pep-0008/)
- [PEP 257 - Docstring Conventions](https://peps.python.org/pep-0257/)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [PEP 518 - pyproject.toml](https://peps.python.org/pep-0518/)
- [PEP 561 - Distributing Type Information](https://peps.python.org/pep-0561/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Semantic Versioning](https://semver.org/)

### Related Documentation
- [Documentation Standards](../process/documentation-standards.md)
- [Feature Development Workflow](../process/feature-development-workflow.md)
- [Git Branching Strategy](../process/git-branching-strategy.md)
- [Issue Tracking](../process/issue-tracking.md)

---

## Status

**Draft** - This standard is in active development and subject to revision based on practical experience.
