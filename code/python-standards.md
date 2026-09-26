# Python Project Standards

*Modern tooling and practices for Python libraries, command-line tools, services and tooling repositories*

## Overview

This document defines standards for Python projects, covering project structure, tooling, code quality, testing, and deployment. It is written for packaged projects (libraries, command-line tools and services), and [Project Profiles](#project-profiles) says what changes for a tooling or operations repository that runs from its checkout. These standards prioritize:

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
| **uv** | Package and Python version manager | Installs and pins interpreters, resolves dependencies and manages the environment in one tool |
| **make** | Build automation | Simple, universal task runner for setup, test, lint, etc. |
| **ruff** | Linter & formatter | Fast, comprehensive linting and formatting in one tool |
| **mypy** | Type checker | Static type checking for improved correctness |
| **pytest** | Test framework | Industry standard with excellent plugin ecosystem |
| **pytest-cov** | Coverage reporting | Integrated coverage measurement |
| **pre-commit** | Git hooks | Automated quality checks before commits |
| **Secret scanner** (detect-secrets by default) | Secret scanning | Block committed credentials in pre-commit and in CI; see [Secret Detection](#secret-detection) |
| **pip-audit** | Vulnerability scanner | Check dependencies for known security vulnerabilities |

### Development Environment

- **Virtual environment**: `.venv/` managed by uv
- **Python version**: `.python-version` pins the version and is committed. `uv python pin <version>` writes it, and `make setup` runs `uv python install`, which installs it. The interpreters themselves are not committed. The pin names a minor version, such as `3.11`, so patch levels can differ between machines.
- **pyenv users**: pyenv reads the same `.python-version`, but uv prefers the interpreter it installed itself unless `UV_PYTHON_PREFERENCE=only-system` is set.
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
├── config/                     # Configuration files (committed)
│   └── .gitkeep
├── scripts/                    # Development/deployment scripts
├── .venv/                      # Virtual environment (gitignored)
├── .env                        # Local configuration (gitignored)
├── example.env                 # Configuration template (committed)
├── secret-refs.env             # Secret references, no values (committed)
├── .pre-commit-config.yaml     # Pre-commit hook configuration
├── .python-version             # Pinned Python version (commit this)
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

**`config/`** - Configuration files (committed to git)
- YAML/JSON configuration files (dev.yaml, stage.yaml, prod.yaml)
- Structured application settings
- Environment-specific configs referenced via APP_CONFIG_FILE env var

**`scripts/`** - Utilities for development and deployment
- Database migrations, data processing, deployment automation
- Not part of the installed package

---

## Project Profiles

This standard is written for a packaged project. A tooling or operations repository follows the same standard with the relaxations below, so adopting it does not mean deviating from it.

- **Packaged project (library, CLI or service)**: the code is built and installed as a package: published to an index, installed as a command, or copied into a container image. This is the default, and everything in this standard applies as written.
- **Tooling/ops repo**: the code runs straight from the git checkout, as scripts, scheduled jobs, git hooks or a service started from its working tree, and is never built or installed. Runtime dependencies are allowed, and many such repositories have none.

A convention not in this table applies to both profiles as written.

| Convention | Packaged project | Tooling/ops repo |
|------------|------------------|------------------|
| Layout | `src/project_name/` (src-layout) | One top-level package directory in the checkout, such as `opstool/`, next to `tests/` |
| `SRC_DIR` in the Makefile | `src/project_name` | The package directory, such as `opstool` |
| `[build-system]`, `[project.scripts]`, `py.typed` | As written | Omitted. Without `[build-system]`, uv installs the dependencies and does not build or install the project |
| Runtime dependencies | As needed | Allowed, in `[project] dependencies`; often none |
| pytest configuration | As written | Adds `pythonpath = ["."]` to `[tool.pytest.ini_options]`. The package is not installed, so without it test collection fails with `ModuleNotFoundError` |
| Loading configuration | `config.py` with python-dotenv (see [Loading Environment Variables](#loading-environment-variables)) | Code reads `os.environ`, and whatever starts it loads the files, for example `uv run --env-file .env`. A `PROJECT_ROOT`, if the code needs one, is computed for this layout and never resolves above the checkout |
| Docker | As written | Not applicable |
| `.python-version`, dev dependencies, pre-commit, secret scanning, coverage thresholds, CI | As written | As written |

Neither profile changes how secrets are handled: [Secrets](#secrets) applies to both, including which tier a repository may use.

---

## Development Environment Setup

### Prerequisites

**Install uv** (one-time setup per machine). uv also installs the Python interpreter, so no separate version manager is needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Project Setup

**Initial setup** (developers and CI):

```bash
make setup
```

This command:
1. Installs the Python version pinned in `.python-version` (`uv python install`)
2. Creates the virtual environment in `.venv/` and installs dependencies, dev dependencies included (`uv sync --all-extras`)
3. Installs pre-commit hooks
4. Copies `example.env` to `.env` if `.env` does not exist

It runs no tests: a new project has none, and pytest exits non-zero when it collects nothing. Run `make check` once the first test exists.

### Makefile Targets

Standard `Makefile` should provide these targets:

```makefile
# The one directory or package that coverage, lint, format and type checking
# read. Its value depends on the project profile (see Project Profiles).
SRC_DIR ?= src/project_name

# Coverage thresholds (adjust as needed)
COVERAGE_MIN_UNIT ?= 80
COVERAGE_MIN_INTEGRATION ?= 80

.PHONY: setup
setup:  ## Initial project setup (install Python, deps, pre-commit, .env)
	uv python install
	uv sync --all-extras
	uv run pre-commit install
	@if [ ! -f .env ]; then \
		cp example.env .env; \
		echo "Created .env from example.env (configuration only; secrets come from secret-refs.env)"; \
	fi

.PHONY: test
test:  ## Run unit tests with coverage
	uv run pytest tests/unit/ --cov=$(SRC_DIR) --cov-report=term --cov-report=html --cov-report=xml --cov-fail-under=$(COVERAGE_MIN_UNIT)

.PHONY: test-integration
test-integration:  ## Run integration tests with coverage
	uv run pytest tests/integration/ --cov=$(SRC_DIR) --cov-report=term --cov-report=html --cov-report=xml --cov-fail-under=$(COVERAGE_MIN_INTEGRATION)

.PHONY: test-all
test-all:  ## Run all tests with coverage
	uv run pytest tests/ --cov=$(SRC_DIR) --cov-report=term --cov-report=html --cov-report=xml --cov-fail-under=$(COVERAGE_MIN_UNIT)

.PHONY: lint
lint:  ## Run ruff linter
	uv run ruff check $(SRC_DIR) tests

.PHONY: format
format:  ## Format code with ruff
	uv run ruff format $(SRC_DIR) tests

.PHONY: format-check
format-check:  ## Check code formatting without changes
	uv run ruff format --check $(SRC_DIR) tests

.PHONY: typecheck
typecheck:  ## Run mypy type checking
	uv run mypy $(SRC_DIR)

.PHONY: security
security:  ## Scan tracked files for secrets, check the allowlist is reviewed, audit dependencies
	uv run detect-secrets-hook --baseline .secrets.baseline $$(git ls-files)
	@uv run python -c "import json, sys; bad = [(f, s['line_number']) for f, ss in json.load(open('.secrets.baseline'))['results'].items() for s in ss if s.get('is_secret') is not False]; [print(f'{f}:{n}: baseline entry not audited as a false positive', file=sys.stderr) for f, n in bad]; sys.exit(bool(bad))"
	@! git grep -noE 'pragma: (allow|white)list (nextline )?secret|gitleaks:allow' -- ':!tests/' ':!Makefile' || { echo 'allowlist pragma outside tests/: move the finding to the reviewed allowlist' >&2; exit 1; }
	uv run pip-audit

.PHONY: pre-commit
pre-commit:  ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

.PHONY: update-hooks
update-hooks:  ## Update pre-commit hook versions
	uv run pre-commit autoupdate

.PHONY: check
check: lint format-check typecheck security test  ## Run all checks (CI runs these plus test-integration)

.PHONY: clean
clean:  ## Remove generated files
	rm -rf .venv/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/ coverage.xml
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

**`SRC_DIR`** names the one directory or package that coverage, lint, format and type checking read. `--cov` takes one path, and a path to a single file collects nothing, so `SRC_DIR` is always a directory. Each profile gives its value (see [Project Profiles](#project-profiles)), and CI reaches these commands through `make`, so the Makefile is the only place it is set.

**`security`** runs the secret scanner over every tracked file, then fails if any entry in `.secrets.baseline` has not been audited as a false positive, then fails if an allowlist pragma appears outside `tests/`, then audits dependencies. [Secret Detection](#secret-detection) explains each step and its exit codes.

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
    "detect-secrets>=1.5.0",
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

**Enforcement strategy**:
- Coverage thresholds are enforced via `--cov-fail-under` in the make targets, which CI runs
- Tests fail if coverage drops below the configured minimum
- Configured via Makefile variables (see Makefile Targets section):
  - `COVERAGE_MIN_UNIT` - Unit test coverage threshold (default: 80%)
  - `COVERAGE_MIN_INTEGRATION` - Integration test coverage threshold (default: 80%)

**Adjusting thresholds**:

```bash
# Temporarily lower threshold for a single run
make test COVERAGE_MIN_UNIT=70

# Or set in Makefile for project-specific thresholds
# At top of Makefile:
COVERAGE_MIN_UNIT ?= 85
COVERAGE_MIN_INTEGRATION ?= 75
```

**What shouldn't be tested**:
- Use `exclude_lines` configuration (see below) for code that shouldn't count against coverage
- Common exclusions: `if __name__ == "__main__":`, `TYPE_CHECKING` blocks, abstract methods, debug-only code

**Coverage configuration**:

```toml
[tool.coverage.run]
# No source setting: make passes --cov=$(SRC_DIR), so the path has one home
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
    "if __name__ == \"__main__\":",
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

  # A local hook runs the detect-secrets pinned in uv.lock, so the hook and
  # make security cannot drift to different versions.
  - repo: local
    hooks:
      - id: detect-secrets
        name: detect-secrets
        entry: uv run detect-secrets-hook
        args: ['--baseline', '.secrets.baseline']
        language: system
```

**Note on versions**: Hook versions shown above are examples and will become outdated. Update hooks quarterly or when adopting new Python versions using `make update-hooks` (see Makefile targets). The detect-secrets hook has no `rev`: its version comes from `uv.lock`, so `make update-hooks` does not touch it. A separately pinned remote hook drifts from the dev dependency, and the v1.4.0 hook crashes on a baseline created by detect-secrets 1.5.0.

### Setup and Usage

```bash
# Install pre-commit hooks (part of make setup)
uv run pre-commit install

# Run hooks manually on all files
uv run pre-commit run --all-files

# Update hook versions (or use: make update-hooks)
uv run pre-commit autoupdate

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

A commit made with `--no-verify`, through a web UI, or in a clone where `make setup` never ran skips every hook. CI's `make security` is the backstop for secrets (see [Secret Detection](#secret-detection)).

### Secrets Baseline

The detect-secrets hook needs `.secrets.baseline` to exist, and exits 2 without it. Create it once, with the project's files staged, and audit it before committing it:

```bash
git add .
uv run detect-secrets scan $(git ls-files) > .secrets.baseline
uv run detect-secrets audit .secrets.baseline
git add .secrets.baseline
```

[Secret Detection](#secret-detection) covers updating it and what the audit means.

---

## Security

### Secret Detection

**Requirement**: every project scans for secrets in four ways:

1. A pre-commit hook scans staged changes and blocks the commit on a finding.
2. CI scans every tracked file and fails on any finding that is not in a reviewed allowlist committed to the repository. The hook is skipped by `git commit --no-verify`, by commits made in a web UI, and in any clone where the hooks were never installed, so CI is the check that cannot be bypassed.
3. Only a person adds a finding to the allowlist. No hook, `make` target or CI step does.
4. The scanner's version has one source, so the hook and the CI scan cannot disagree.

detect-secrets is the default, and the rest of this section describes it. gitleaks is a sanctioned alternative; see [Using gitleaks Instead](#using-gitleaks-instead).

**A secret that reached a commit is rotated first and removed from history second.** Once pushed, it can have been cloned, cached or read by an agent, and rewriting history does not undo that. See [Secrets](#secrets).

#### How detect-secrets Meets It

- **Pre-commit**: the local hook under [Pre-commit Hooks](#pre-commit-hooks) runs `detect-secrets-hook` on the staged files.
- **CI and `make security`**: `uv run detect-secrets-hook --baseline .secrets.baseline $(git ls-files)` scans every tracked file. `uv run detect-secrets scan --baseline .secrets.baseline` is not a check: it writes each new finding into the baseline and exits 0, so it cannot fail. Running the hook through `pre-commit run` is not used either, because pre-commit runs hooks from the git root. In a project that sits in a subdirectory of a monorepo, the hook then looks for `.secrets.baseline` in the wrong directory and exits 2.
- **Allowlist**: `.secrets.baseline`, committed. It holds a hash of each accepted finding, never the value, and the audit decision for each.
- **One version**: the hook and `make security` both run the detect-secrets in `uv.lock`.

`detect-secrets-hook` exit codes (detect-secrets 1.5.0):

| Exit | Meaning | What to do |
|------|---------|------------|
| 0 | No finding outside the baseline | Nothing |
| 1 | A finding that is not in the baseline, or `.secrets.baseline` has unstaged changes | Remove the secret and move it to the secret manager; or, for a false positive, follow the workflow below. For unstaged changes, stage the baseline |
| 2 | `.secrets.baseline` does not exist | Create it (see [Secrets Baseline](#secrets-baseline)) |
| 3 | The hook rewrote the baseline without adding a finding: a baselined line moved, or the installed detect-secrets version differs from the baseline's `version` | Stage `.secrets.baseline` and run again. In CI, exit 3 means the committed baseline is stale: run `make security` locally and commit the rewritten baseline. A commit that upgrades detect-secrets includes it |

A failure names the file, the line and the detector type, never the value. The hook suggests an inline `pragma: allowlist secret` comment. Use the baseline instead, except as allowed below.

**The baseline is reviewed, and CI enforces it.** The hook ignores every finding that has an entry in the baseline, whatever its audit says. `make security` therefore also fails when any entry is not audited as a false positive (`"is_secret": false`). That covers an entry never audited and one audited as a real secret. The check reads only the baseline, so it prints a file and line number, never a value. `make security` also fails on an allowlist pragma comment (`pragma: allowlist secret`, its `nextline` and legacy `whitelist` forms, or `gitleaks:allow`) in any tracked file outside `tests/`, because a pragma is an allowlist entry nobody audits. It prints the file, line and the pragma, never the line's value.

**Handling a false positive**:

```bash
# With the flagged file staged, add its finding to the baseline, unaudited
uv run detect-secrets scan --baseline .secrets.baseline $(git ls-files)

# Answer each prompt: y marks the finding as a false positive
uv run detect-secrets audit .secrets.baseline

# Stage it, review the diff, then confirm the check passes
git add .secrets.baseline
git diff --cached .secrets.baseline
make security
```

- The audit shows each flagged line on screen, so a person runs it, not an agent, which would copy the value into its transcript. For the same reason `detect-secrets audit --report`, which prints flagged values, never runs in CI or behind a `make` target.
- A finding in `secret-refs.env` or `example.env` goes into the baseline. Never put a pragma comment in a `*.env` file: `check-secret-refs.mjs` rejects inline comments, and a `pragma: allowlist nextline secret` comment hides the next line from the scanner.
- An inline `# pragma: allowlist secret` is acceptable only under `tests/`, on a line that holds an obvious fake. `make security` enforces the location.

#### Using gitleaks Instead

gitleaks meets the same requirement with a different allowlist and no baseline file. Only these parts change:

| Part | detect-secrets (default) | gitleaks |
|------|--------------------------|----------|
| Install | dev dependency, pinned in `uv.lock` | one version, pinned in both places it runs: the hook's `rev` (pre-commit builds it from source) and the CI binary download |
| Pre-commit hook | local hook, `entry: uv run detect-secrets-hook` | `repo: https://github.com/gitleaks/gitleaks`, `rev: v8.24.2`, `id: gitleaks` |
| CI scan | `make security` | `gitleaks dir .`, as the first step after checkout |
| `make security` | as written | delete the `detect-secrets-hook` line and the baseline audit check; keep the pragma check and `pip-audit`. The tree scan stays a separate CI step, because run locally `gitleaks dir` also scans `.venv/` |
| Allowlist | `.secrets.baseline`, audited | `.gitleaksignore`, one finding fingerprint per line, added and reviewed by a person |

- Remove detect-secrets from the dev dependencies and delete `.secrets.baseline`. CI keeps its `make security` step, so `pip-audit` still runs.
- The hook scans staged changes only. `pre-commit run gitleaks --all-files` passes on a tree with a committed secret, so it cannot stand in for the CI scan.
- `gitleaks dir` does not read `.gitignore`. Run it straight after `actions/checkout` and before `uv sync`, or it scans `.venv/` and any other untracked files as well.
- A fingerprint for `gitleaks dir` has the form `path:rule-id:line`, so it stops matching when the line moves.
- A `gitleaks:allow` comment follows the pragma rule above: under `tests/` only, never a `*.env` file. The `make security` pragma check enforces it.
- `gitleaks/gitleaks-action` needs a `GITLEAKS_LICENSE` secret for repositories owned by an organization; the binary does not.

CI step:

```yaml
      - name: Secret scan
        run: |
          curl -sSfL https://github.com/gitleaks/gitleaks/releases/download/v8.24.2/gitleaks_8.24.2_linux_x64.tar.gz | tar xz gitleaks
          ./gitleaks dir .
```

gitleaks 8.24.2 was run on 2026-09-25 for these claims: the hook, the committed-secret gap, `gitleaks dir` failing on a committed secret and scanning a gitignored `.venv/`, the release URL, and a `.gitleaksignore` fingerprint clearing a finding. The `GITLEAKS_LICENSE` requirement comes from the gitleaks README (fetched 2026-09-24) and was not run.

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
2. **Keep secrets out of the working tree** - See [Secrets](#secrets); `.gitignore` stops commits, not reads
3. **Scan for secrets in pre-commit and in CI** - See [Secret Detection](#secret-detection); the hook alone can be skipped
4. **Scan dependencies regularly** - Weekly or on each PR
5. **Pin dependencies** - Lock file ensures reproducible, scannable builds
6. **Review direct and transitive dependencies** - Understand what you depend on

---

## Configuration Management

### Secrets

**Rule**: A secret reaches the process that uses it from a secret manager, when that process starts. It is not kept in the working tree, where any tool with filesystem access can read it, an AI agent included.

A *secret* is a credential that grants access to something outside the developer's machine: a third-party API key, test-mode keys included; the password of a shared or cloud database; a key that signs tokens other services accept. A throwaway credential for a service that exists only on the developer's machine, such as the password of a Docker Postgres on localhost, grants access to nothing. It is configuration, and it stays in `example.env`.

The rule covers application secrets supplied to a process as environment variables. Developer-tool credentials, such as cloud CLI profiles, `gh` tokens, package-registry tokens and SSH keys, stay in their tools' own stores and are out of scope.

`.gitignore` is a git convention, not an access-control boundary. It keeps `.env` out of commits and does nothing about a process that reads the file. In a repository an agent works in, that is the ordinary case: an agent that runs `cat .env`, greps for a setting or summarises a directory has read the secrets, and they can then land in a transcript, a log or an issue body.

**Tiers**, in order of preference:

| Tier | Where the value lives | Protects against | Does not protect against |
|------|-----------------------|------------------|--------------------------|
| 1 (recommended) | In the secret manager. A runner resolves references when the process starts and puts the values in the environment of the command it launches, which that command's child processes inherit. A runner that meets the contract under Runner writes none to disk; whether `op run` does was not verified (2026-09-24) | A secret in the working tree; file reads by agents, editors and indexers; accidental commit | An agent calling the manager's CLI (see [The limit](#the-limit)); anything the process prints, logs or passes to a container; the same user reading the process's environment while it runs |
| 2 (fallback) | A file outside the working tree, at mode `0600` | Accidental commit; tools that read only the working tree | Any process running as the developer, an agent with a shell included, which reads this file as easily as one in the tree |
| 3 (no agent access only) | An in-tree, gitignored `.env` | Accidental commit | Anything that reads the working tree |

A repository that commits a `secret-refs.env` supports tiers 1 and 2, and each developer picks one. Tier 3 is a choice for the whole repository, made by committing no `secret-refs.env`. It applies only where no agent has access to the working tree, counting IDE assistants and any tool that reads workspace contents for a model. If you are unsure, the condition is not met. A project using this repository's AI starter kit does not meet it.

#### Tier 1: Resolve at Start

**Reference file.** The repository commits `secret-refs.env` next to `example.env`. It holds secret keys only, and each value is a reference to the secret, not the secret:

```bash
STRIPE_API_KEY=op://dev/stripe/credential
```

The full example is under [example.env Template](#exampleenv-template). A reference file follows these rules:

- It contains only full-line comments, blank lines and `KEY=reference` lines: no quotes, no `export`, no `$`, no inline comment, no whitespace in a value and no repeated key. Dotenv parsers disagree about each of these, and a file that means one thing to a check and another to a runner defeats the check.
- It shares no key with `example.env`. Configuration and secrets live in separate files.
- No key has a browser-exposed prefix (`NEXT_PUBLIC_`, `VITE_`, `REACT_APP_`, `PUBLIC_`): a build tool inlines such a value into client bundles.
- A secret embedded in a larger value, such as the password inside the `DATABASE_URL` of a shared database, is stored whole as one manager field and referenced as one value.
- It needs required review, for example through CODEOWNERS, because repointing a key can send one service's secret to another.
- `.gitattributes` holds `secret-refs.env text eol=lf`.

`scripts/check-secret-refs.mjs` checks these rules (see [Automated Checks](../process/documentation-standards.md#automated-checks)). A pass means only that the named files are well-formed. It does not show that a reference resolves, that a value shaped like a reference is not a pasted secret, or that the free text of a comment holds no secret.

**Reference syntax.** 1Password is the named default, and its references take the form `op://<vault-name>/<item-name>[/<section-name>]/<field-name>`. Keep vault, item, section and field names to letters, digits, `.`, `_` and `-`; the check rejects anything else, spaces included. Doppler, sops and HashiCorp Vault are sanctioned alternatives: a project using one adds that tool's reference grammar, with its source, to the check's allowlist, and its prefix to `REFERENCE_PREFIXES` in the configuration example.

References point at a shared team vault that holds development and test credentials only, and onboarding includes access to it.

**Runner.** A runner resolves every reference, fails closed by launching nothing if any reference does not resolve, and puts the values in the environment of the one command it launches. Nothing sources a reference file into a shell. The command a runner launches is the application or an integration-test target. It is never an agent, an editor, a terminal multiplexer, a general-purpose `make` target, or a shell-integration tool such as direnv, because each of those passes the values to everything it starts.

1Password's usual runner is `op run`. Its flags, whether it fails closed and whether it masks output could not be verified when this section was written (2026-09-24), so this standard states none of them and does not rely on masking. Check `op run --help` for the version you install.

To resolve one value by hand, `op read <reference>` prints it. Run by an agent, the value enters the session transcript.

#### Tier 2: A File Outside the Tree

The file:

- is not named `.env` and sits in no directory above a working tree. Called without a path, `load_dotenv()` searches upward from the calling file for `.env`, so a `.env` in a parent directory is loaded without anyone asking for it.
- is not under version control, in a dotfiles repository or in a synced folder.
- has mode `0600`.

Load it into the one launched process, for example `uv run --env-file ~/.config/project-name/secrets.env -- python -m project_name`. `uv run --env-file` leaves a variable that is already set untouched and refuses to run when the file is missing.

#### Tier 3: An In-Tree `.env`

Under the condition above, `.env` holds the secret values as well as configuration, and `example.env` holds a safe placeholder for each secret. The rest of Configuration Management applies unchanged.

#### The Limit

An agent running commands as the developer can call the manager's CLI and read the environment it resolves into. Tier 1 turns retrieval into an explicit call rather than a file read; it does not prevent it.

- In this repository's starter kit, `Bash(uv:*)` pre-approves `uv run op read <reference>`, `uv run env` and `uv run cat <file>`, where a bare `op read` or `cat .env` prompts, and `Bash(make:*)` pre-approves every `make` target. This was checked with the permission-rule matcher in `scripts/check-template-kit.mjs` on 2026-09-24.
- An agent can reach everything the signed-in manager identity can read, which can be more than a tier 3 `.env` held: the developer's personal vault and every vault shared with them, whatever the references point at. Hold staging and production access under a different identity from the one signed in during daily development.
- Never add a manager CLI to an agent's allow list, and never let a Makefile target or script that an agent's allow list reaches invoke the runner or the manager CLI. Under `Bash(make:*)` such a target is an allow-list entry for the manager. Type the runner command yourself.
- The explicit call assumes interactive sign-in. A manager token exported in the shell or a profile reaches every command an agent starts, and is itself a secret at rest.
- Whether the manager logs CLI access depends on the manager and the plan. This standard does not claim that retrieval is audited.

**Moving to tier 1.** Rotate every secret that sat in a file an agent could read. Moving the file does not un-read it.

#### CI

CI never resolves the references in `secret-refs.env`. Secrets CI needs come from the CI platform's secret store under the same names, and throwaway service credentials stay literal configuration.

- Expose a CI secret to the one step that needs it, never to a job that runs an agent or runs PR-authored code under `pull_request_target`.
- A secret available to a same-repository `pull_request` run can be read by anyone who can push a branch, agents included, so CI secrets are development and test credentials only.
- A test that needs a third-party secret skips when the secret is absent only on runs where the platform withholds secrets, such as a pull request from a fork. On any other run, an absent secret fails the test. A smoke test that starts the application is such a test: the test skips, and `validate_config()` stays strict.

#### Sources

Every tool behaviour stated in this section was checked on 2026-09-24 against:

- `@1password/sdk` 0.5.0 (npm, published by 1Password): the `op://` reference syntax.
- `@1password/op-js` 0.1.13 (npm, same publisher): `op read <reference>`, as that wrapper invokes it, returns the value on standard output.
- `python-dotenv` 1.2.3, `dotenv/main.py`: `load_dotenv()` defaults to `override=False`, so a variable already set wins; without a path it calls `find_dotenv()`, which walks up from the calling file's directory to the filesystem root; `dotenv_values()` of a missing file returns no keys.
- `uv` 0.8.17: `uv run --env-file`, by running it.

Not verified: any `op run` flag or behaviour, 1Password item-ID syntax in references, and whether `op read` adds a trailing newline.

### Environment Variables Strategy

**Philosophy**: Values are injected directly as environment variables (not file paths). This works universally across AWS, Kubernetes, Docker, and local development.

**Pattern**:
- `example.env` committed as the template and documentation for configuration; `make setup` copies it to a gitignored `.env`
- `secret-refs.env` committed with a reference for each secret (see [Secrets](#secrets))
- Secrets injected as environment variables by infrastructure in deployed environments
- Complex configuration in YAML/JSON files, referenced via env vars

### Naming Conventions

**Configuration values** (non-sensitive):
```bash
# Infrastructure
DATABASE_HOST=localhost
DATABASE_PORT=5432
REDIS_URL=redis://localhost:6379

# Application behavior
LOG_LEVEL=INFO
API_TIMEOUT_SECONDS=30
FEATURE_FLAG_NEW_UI=true
ENVIRONMENT=development
```

**Secrets** (grant access to something outside the developer's machine; see [Secrets](#secrets)):
```bash
# In secret-refs.env: a reference to each secret, never its value
ANTHROPIC_API_KEY=op://dev/anthropic/credential
STRIPE_API_KEY=op://dev/stripe/credential
```

A credential for a service that exists only on the developer's machine, such as `DATABASE_PASSWORD` for a local Docker database, is configuration and uses the same names in every environment.

**Complex configuration** (YAML/JSON files):
```bash
# Path to structured config file
APP_CONFIG_FILE=./config/app.yaml
LOGGING_CONFIG_FILE=./config/logging.json
```

### Project Structure

```
project-name/
├── config/                     # Configuration files (committed)
│   ├── dev.yaml               # Development config
│   ├── stage.yaml             # Staging config
│   ├── prod.yaml              # Production config
│   └── logging.json           # Shared logging config
├── .env                        # Local configuration (gitignored)
├── example.env                 # Configuration template (committed)
├── secret-refs.env             # Secret references, no values (committed)
├── .gitignore                  # Git exclusions
└── ...
```

**Note**: No `secrets/` directory: secret values come from the secret manager locally and from infrastructure when deployed.

### example.env Template

`example.env` holds configuration, including credentials for services that exist only on the developer's machine. `make setup` copies it to `.env`.

```bash
# example.env
# Copied to .env by make setup. Configuration only: secrets are in secret-refs.env.

# Infrastructure and application behavior
DATABASE_HOST=localhost
DATABASE_PORT=5432
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
ENVIRONMENT=development

# Local-only credentials: the local Docker stack's database and this
# app's own token signing, neither of which grants access outside the machine
DATABASE_PASSWORD=local-dev-password
JWT_SECRET=local-dev-jwt-secret

# Configuration file (environment-specific)
APP_CONFIG_FILE=./config/dev.yaml
```

`secret-refs.env` holds a reference for each secret and shares no key with `example.env` (see [Secrets](#secrets)):

```bash
# secret-refs.env
# References to the team's development vault. No values.

ANTHROPIC_API_KEY=op://dev/anthropic/credential
STRIPE_API_KEY=op://dev/stripe/credential
```

`node scripts/check-secret-refs.mjs --standard` holds these two blocks to the reference-file rules.

### Makefile Integration

The `setup` recipe under [Makefile Targets](#makefile-targets) copies `example.env` to `.env` when `.env` does not exist, and never overwrites an existing `.env`.

### .gitignore Entries

```gitignore
# Environment: configuration, plus secret values only under tier 3 (see Secrets)
.env
.env.local
.env.*.local

# Configuration overrides (if using local config files)
config/local.yaml
```

### Loading Environment Variables

**Use python-dotenv for local development**:

```python
# src/project_name/config.py
import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # src/project_name/config.py -> checkout root
ENV_FILE = PROJECT_ROOT / ".env"
SECRET_REFS_FILE = PROJECT_ROOT / "secret-refs.env"
REFERENCE_PREFIXES = ("op://",)

# An explicit path: called without one, load_dotenv() also searches parent
# directories. override=False, the default, lets a value the runner already
# put in the environment win. A missing file loads nothing.
load_dotenv(ENV_FILE)


def get_config(key: str, default: str | None = None) -> str:
    """Get a configuration value from the environment."""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Required environment variable {key} not set")
    return value


def get_secret(key: str) -> str:
    """Get a secret the runner put in the environment.

    Call it where the secret is used, not at import, so code that never
    needs the secret runs without a secret-manager session.
    """
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required secret {key} not set")
    if value.startswith(REFERENCE_PREFIXES):
        raise ValueError(f"Secret {key} is an unresolved reference; start the app through the runner")
    return value


def validate_config() -> None:
    """Fail fast at start-up. Call from the entrypoint, never at import.

    A project with no secret-refs.env (tier 3) has no secret keys to check.
    Errors name keys, never values.
    """
    secret_keys = set(dotenv_values(SECRET_REFS_FILE))
    in_dotenv = sorted(secret_keys & set(dotenv_values(ENV_FILE)))
    if in_dotenv:
        raise RuntimeError(
            f".env defines secret keys {in_dotenv}: remove them, since secrets "
            "come from secret-refs.env through the runner"
        )
    for key in sorted(secret_keys):
        get_secret(key)
```

`PROJECT_ROOT` counts parent directories from this file, so it depends on the layout. In a tooling/ops repo, where no `src/` level exists, compute it for that layout and check that it never resolves above the checkout (see [Project Profiles](#project-profiles)).

Call `validate_config()` from the entrypoint, and resolve each secret where it is used:

```python
# src/project_name/__main__.py
from anthropic import Anthropic

from project_name.config import get_secret, validate_config


def main() -> None:
    validate_config()
    client = Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))
    ...
```

`validate_config()` refuses to start when `.env` defines a key that `secret-refs.env` holds, so an entrypoint that calls it refuses to start rather than use a real value typed into `.env`. It reads its list of secrets from `secret-refs.env`, so that file ships with the application; see the Dockerfile below. Unit tests never call it. They set fakes instead, and need no secret-manager session:

```python
# tests/unit/test_config.py
import pytest

from project_name.config import get_secret


def test_get_secret_rejects_unresolved_reference(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "op://dev/anthropic/credential")
    with pytest.raises(ValueError, match="unresolved reference"):
        get_secret("ANTHROPIC_API_KEY")
```

Add to dev dependencies:

```bash
uv add python-dotenv
```

### Infrastructure Compatibility

This pattern works across all platforms:

**Local Development**: a runner resolves `secret-refs.env` and puts the values in the application's environment; `.env` holds configuration (see [Secrets](#secrets)).

**Docker**:
```bash
# Direct environment variable injection
docker run \
  -e DATABASE_HOST=postgres \
  -e DATABASE_PASSWORD=prod-password \
  -e ANTHROPIC_API_KEY=sk-ant-prod-key \
  myapp
```

**ECS/Fargate** (AWS Secrets Manager):
```json
{
  "containerDefinitions": [{
    "environment": [
      {"name": "DATABASE_HOST", "value": "prod-db.rds.amazonaws.com"},
      {"name": "APP_CONFIG_FILE", "value": "/app/config/prod.yaml"}
    ],
    "secrets": [
      {
        "name": "DATABASE_PASSWORD",
        "valueFrom": "arn:aws:secretsmanager:us-east-1:123:secret:myapp/prod/database-password"
      },
      {
        "name": "ANTHROPIC_API_KEY",
        "valueFrom": "arn:aws:secretsmanager:us-east-1:123:secret:myapp/prod/anthropic-api-key"
      }
    ]
  }]
}
```

**Kubernetes with AWS Secrets Store CSI Driver**:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123:role/myapp-secrets-role

---
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: myapp-aws-secrets
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: "myapp/prod/database-password"
        objectType: "secretsmanager"
        objectAlias: "database-password"
      - objectName: "myapp/prod/anthropic-api-key"
        objectType: "secretsmanager"
        objectAlias: "anthropic-api-key"
  secretObjects:
  - secretName: myapp-secrets
    type: Opaque
    data:
    - objectName: "database-password"
      key: "database-password"
    - objectName: "anthropic-api-key"
      key: "anthropic-api-key"

---
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: myapp-sa
  containers:
  - name: myapp
    env:
    - name: DATABASE_HOST
      value: "postgres.prod.svc.cluster.local"
    - name: DATABASE_PASSWORD
      valueFrom:
        secretKeyRef:
          name: myapp-secrets
          key: database-password
    - name: ANTHROPIC_API_KEY
      valueFrom:
        secretKeyRef:
          name: myapp-secrets
          key: anthropic-api-key
    - name: APP_CONFIG_FILE
      value: "/app/config/prod.yaml"
    volumeMounts:
    - name: secrets-store
      mountPath: "/mnt/secrets"
      readOnly: true
  volumes:
  - name: secrets-store
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: "myapp-aws-secrets"
```

**Kubernetes with External Secrets Operator**:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secretsmanager
  namespace: prod
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: myapp-sa

---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-secrets
  namespace: prod
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: myapp-secrets
  data:
  - secretKey: database-password
    remoteRef:
      key: myapp/prod/database-password
  - secretKey: anthropic-api-key
    remoteRef:
      key: myapp/prod/anthropic-api-key

---
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: myapp
    env:
    - name: DATABASE_PASSWORD
      valueFrom:
        secretKeyRef:
          name: myapp-secrets
          key: database-password
    - name: ANTHROPIC_API_KEY
      valueFrom:
        secretKeyRef:
          name: myapp-secrets
          key: anthropic-api-key
```

### Complex Configuration Files

For structured configuration, use YAML or JSON files:

**config/dev.yaml** (committed):
```yaml
# Development configuration
features:
  new_ui: true
  beta_features: true
  debug_mode: true

rate_limiting:
  enabled: false
  requests_per_minute: 1000

anthropic:
  model: "claude-3-5-sonnet-20241022"
  max_tokens: 4096
  temperature: 0.7

database:
  pool_size: 5
  timeout_seconds: 30

logging:
  level: DEBUG
  format: detailed
```

**config/prod.yaml** (committed):
```yaml
# Production configuration
features:
  new_ui: true
  beta_features: false
  debug_mode: false

rate_limiting:
  enabled: true
  requests_per_minute: 100

anthropic:
  model: "claude-3-5-sonnet-20241022"
  max_tokens: 4096
  temperature: 0.3

database:
  pool_size: 20
  timeout_seconds: 10

logging:
  level: INFO
  format: json
```

**Load in code**:
```python
import yaml
from pathlib import Path

def load_config() -> dict:
    config_file = os.getenv("APP_CONFIG_FILE", "./config/dev.yaml")
    with Path(config_file).open() as f:
        return yaml.safe_load(f)

# Usage
config = load_config()
model = config["anthropic"]["model"]
pool_size = config["database"]["pool_size"]
```

### Multi-Environment Strategy

**Philosophy**: Application code is environment-agnostic. Infrastructure provides environment-specific values.

**How it works**:

1. **Same variable names everywhere** - `DATABASE_PASSWORD`, not `DATABASE_PASSWORD_DEV`
2. **Infrastructure sets values** - Different values per environment
3. **Config files for complex settings** - `APP_CONFIG_FILE=./config/prod.yaml`
4. **No environment logic in code** - Application doesn't know about dev/stage/prod

**Example across environments**:

| Environment | DATABASE_HOST | DATABASE_PASSWORD | APP_CONFIG_FILE |
|-------------|---------------|-------------------|-----------------|
| **Development** (`.env`; secrets through the runner) | localhost | local-dev-password (local Docker database) | ./config/dev.yaml |
| **Staging** (AWS Secrets Mgr) | stage-db.rds.amazonaws.com | (from secrets manager) | ./config/stage.yaml |
| **Production** (AWS Secrets Mgr) | prod-db.rds.amazonaws.com | (from secrets manager) | ./config/prod.yaml |

**Secret organization**:
```
Development (team vault in the secret manager, referenced from secret-refs.env):
  op://dev/anthropic/credential
  op://dev/stripe/credential

Staging:
  myapp/stage/database-password
  myapp/stage/anthropic-api-key
  myapp/stage/stripe-api-key

Production:
  myapp/prod/database-password
  myapp/prod/anthropic-api-key
  myapp/prod/stripe-api-key
```

**Key principles**:
1. **No environment logic in application code** - App doesn't know about dev/stage/prod
2. **Same variable names** across all environments
3. **Infrastructure provides values** - ECS, Kubernetes, or Docker Compose
4. **Config files** for environment-specific behavior (dev.yaml, prod.yaml)
5. **Sensible defaults** - Development configuration in example.env, development secret references in secret-refs.env

**What NOT to do**:
- ❌ Don't create `.env.dev`, `.env.stage`, `.env.prod` - use infrastructure
- ❌ Don't put environment logic in code (`if env == 'prod'`) - use config files
- ❌ Don't hardcode environment-specific values - always use env vars or config files
- ❌ Don't use file-based secrets with `_PATH` suffix - use direct injection

### Best Practices

1. **Keep secrets out of the working tree** - Resolve them from a secret manager at start (see [Secrets](#secrets)); `.gitignore` only stops commits
2. **Use direct injection** - Secrets as environment variables, not file paths
3. **Provide example.env** - Clear documentation with safe development values
4. **Default to development-safe values** - example.env should work for local dev
5. **Simple values in environment variables, complex in files** - Don't put JSON in environment variables
6. **Document all variables** - Comment example.env thoroughly
7. **Validate on startup** - Fail fast if required config/secrets missing
8. **Keep code environment-agnostic** - No `if env == 'prod'` logic
9. **Use infrastructure for secrets** - AWS Secrets Manager, Kubernetes Secrets, etc.
10. **Separate by environment in secret manager** - myapp/dev/*, myapp/stage/*, myapp/prod/*

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

# secret-refs.env holds references only, never values. validate_config()
# reads it for the list of secrets to check at start; without it, no secret
# is checked.
COPY secret-refs.env /app/secret-refs.env

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

````markdown
# Project Name

Brief description (1-2 sentences).

## Features

- Key feature 1
- Key feature 2

## Quick Start

### Prerequisites

- Python 3.11+ (installed by `make setup`)
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
````

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
    # Every uv command in this leg uses this version instead of the
    # .python-version pin, and uv downloads it if it is missing.
    env:
      UV_PYTHON: ${{ matrix.python-version }}

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Run linting
        run: make lint

      - name: Check formatting
        run: make format-check

      - name: Type checking
        run: make typecheck

      - name: Run unit tests
        run: make test

      - name: Run integration tests
        run: make test-integration

      - name: Security scan
        run: make security

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### CI Best Practices

1. **Test on all supported Python versions** - Use a matrix, and set `UV_PYTHON` per leg: with `.python-version` committed, every leg otherwise runs the pinned version
2. **Run all checks** - Lint, format, type check, test, security
3. **Enforce coverage thresholds** - The `make` test targets pass `--cov-fail-under`, so CI and developers use the same thresholds
4. **Fast feedback** - Fail fast, parallelize when possible
5. **Coverage reporting** - Use codecov or similar
6. **Dependency caching** - Cache `.venv/` to speed up builds
7. **Scope secrets to the step that needs them** - See [Secrets](#secrets) for CI

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

1. **Src layout** - Use `src/project_name/` structure (a tooling/ops repo uses one top-level package; see [Project Profiles](#project-profiles))
2. **Small modules** - One class or a few related functions per file
3. **Clear imports** - Absolute imports, organized by stdlib/third-party/local
4. **Avoid circular imports** - Restructure if needed

### Dependency Management

1. **Pin dependencies** - Commit `uv.lock` for reproducibility
2. **Update regularly** - Weekly or bi-weekly dependency updates
3. **Update pre-commit hooks** - Quarterly with `make update-hooks`
4. **Minimize dependencies** - Each dependency is a liability
5. **Audit new dependencies** - Check license, maintenance, security

### Testing Strategy

1. **Write tests first** - TDD when appropriate
2. **Test public APIs** - Internal implementation can change
3. **Mock external dependencies** - Unit tests should be fast
4. **Integration tests for workflows** - Test real interactions
5. **Aim for high coverage** - But don't obsess over 100%

### Security

1. **Never commit secrets** - See [Secrets](#secrets)
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
- One of the two [Project Profiles](#project-profiles): a packaged project, or a tooling/ops repo run from its checkout
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
printf '%s\n' .venv/ '*.pyc' __pycache__/ .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/ .coverage coverage.xml .env > .gitignore

# Pin the Python version (make setup installs it)
uv python pin 3.11

# Create project structure: uv builds the package, which needs __init__.py
mkdir -p src/my_project tests/{unit,integration} docs/{product,engineering} scripts .github/workflows
touch src/my_project/__init__.py src/my_project/py.typed

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
    "detect-secrets>=1.5.0",
    "pip-audit>=2.7.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF

# Now copy in this standard's blocks: the Makefile from Makefile Targets
# (with SRC_DIR ?= src/my_project), .pre-commit-config.yaml from Pre-commit
# Hooks, and example.env from example.env Template

# Install Python and dependencies, install the hooks, create .env
make setup

# Stage everything, then create and audit the secrets baseline
git add .
uv run detect-secrets scan $(git ls-files) > .secrets.baseline
uv run detect-secrets audit .secrets.baseline
git add .secrets.baseline

# First commit: every hook runs
git commit -m "feat: initial project setup"
```

The audit asks about the two local-only credentials in `example.env`; answer `y` to each. Create the baseline only after `git add .`: a baseline created earlier is empty, and the first commit then fails on those two lines. Run `make check` once the first unit test exists.

---

## References

### Tools
- [uv - Python package manager](https://github.com/astral-sh/uv)
- [ruff - Linter and formatter](https://github.com/astral-sh/ruff)
- [mypy - Static type checker](https://mypy-lang.org/)
- [pytest - Testing framework](https://pytest.org/)
- [pre-commit - Git hook framework](https://pre-commit.com/)
- [detect-secrets - Secret scanning (default)](https://github.com/Yelp/detect-secrets)
- [gitleaks - Secret scanning (sanctioned alternative)](https://github.com/gitleaks/gitleaks)
- [pip-audit - Dependency vulnerability scanning](https://github.com/pypa/pip-audit)

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
