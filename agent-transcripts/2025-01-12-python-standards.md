# Python Standards Agent Transcript

*A conversation log documenting the creation of Python project standards*

---

## Initial Request: Python Project Standards

**User:** I'm going to start a Python based computational engine project. I want to establish a project template, tools, libraries and practices for command line and library projects into a standards document. Among the standard items I want to establish...
- uv package manager
- make (gnu featured) for setup, builds, test, lint, common commands, etc.
- ruff for both code formatting and linting
- pre-commit for checks before commits
- pytest with coverage for unit and integration test platform
- python-slim based docker builds, for compatibility

In this standard we'll be neutral about library selection, leaving that as an application decision.

**AI Agent:** Great start! Here are additional items that should be covered:

**Essential Additions:**
- **Type Checking** - mypy or pyright for static type checking
- **Project Structure** - src/ vs flat layout, directory conventions
- **Dependency Management Details** - pyproject.toml structure, lock file management
- **Documentation Standards** - Docstring style (Google/NumPy/Sphinx)
- **Security** - Dependency scanning, secrets management
- **Version Management** - Semantic versioning strategy
- **CI/CD Integration** - GitHub Actions examples

**User additions:**
- mypy for type checking
- docs/ for documentation (per existing documentation-standards.md)
- pyenv for Python version management (installed outside of project)
- Virtual env via uv in .venv, built by "make setup"
- Google style docstrings
- detect-secrets pre-commit module
- uv-secure for dependency vulnerability scans
- GitHub Actions for CI/CD, unit and integration tests on all pushes

---

## Document Creation and Structure

**AI Agent:** I'll create `code/python-standards.md` following the format of existing standards in the repository. The document will cover:
- Philosophy and modern tooling choices
- Complete tool stack with rationale
- Project structure (src-layout)
- Development environment setup
- Code quality (ruff, mypy, docstrings)
- Testing with pytest
- Pre-commit hooks
- Security scanning
- Docker builds
- CI/CD with GitHub Actions
- Integration with existing process standards

**Decision:** Place in `code/` directory since it's language-specific code standards, not process standards.

---

## Following Process Standards

**User:** Lets follow the standards in process: create an issue for this work, commit it to a feature branch, and create a PR.

**AI Agent:** Following the git-branching-strategy standard:
1. Created issue #5: "Add Python project standards document"
2. Created feature branch: `5-add-python-project-standards-document`
3. Committed changes with conventional commit format
4. Created PR #6 with comprehensive description

---

## Review Comment 1: uv-secure Tool Status

**Issue:** uv-secure appears to be a community tool, not officially maintained. As of Jan 2025, pip-audit is the well-established PyPA tool.

**Research findings:**
- uv-secure exists on PyPI and GitHub but is community-maintained
- pip-audit is the official PyPA tool, actively maintained
- Native `uv audit` command is under consideration (issue #9189)

**Decision:** Replace uv-secure with pip-audit as primary tool, mention uv-secure as alternative for uv.lock-specific scanning.

**Changes:**
- Updated tool stack table
- Changed Makefile security target
- Updated all pyproject.toml examples
- Updated CI/CD workflow
- Added note about uv-secure as alternative

---

## Review Comment 2: Python Version Support Clarity

**Issue:** "Support last 3 minor versions" needs clarification with current date context.

**Decision:** Add explicit dates and rationale:
- As of early 2025: Python 3.13 (Oct 2024), 3.12 (Oct 2023), 3.11 (Oct 2022)
- Note Python 3.10 EOL date (Oct 2025)
- Add guidance on when to review/update policy
- Explain rationale for 3-version support window

---

## Review Comment 3: Coverage Pattern Typo

**Issue:** Line 531 has incorrect regex: `if __name__ == .__main__.:`

**Fix:** Correct to: `if __name__ == "__main__":`

Simple typo fix in coverage configuration exclude pattern.

---

## Review Comment 4: Pre-commit Version Pins

**Issue:** Hook versions (v4.5.0, v0.6.0, etc.) will become outdated quickly.

**Decision:** Add maintenance guidance and tooling:
- Add note after pre-commit config about quarterly updates
- Create `make update-hooks` target
- Add to Best Practices section
- Update Setup and Usage section

**Rationale:** Prevents projects from running outdated hooks that may miss new checks or have compatibility issues.

---

## Review Comment 5: Coverage Thresholds Need Enforcement

**Issue:** States "80% for new projects, 90% target" but no enforcement strategy or guidance on what to do when coverage drops.

**User request:** Add Makefile variables for min coverage thresholds, one for unit tests and one for integration tests. Use in make targets and CI to fail when below threshold. Default 80%, easily adjustable.

**Decision:** Implement configurable coverage enforcement:

**Makefile variables:**
```makefile
COVERAGE_MIN_UNIT ?= 80
COVERAGE_MIN_INTEGRATION ?= 80
```

**Test targets:**
- Add `--cov-fail-under=$(COVERAGE_MIN_UNIT)` to test targets
- Tests fail locally if coverage drops below minimum

**CI/CD:**
- Add coverage threshold env vars to GitHub Actions
- Enforce thresholds in CI test steps
- Builds fail when coverage drops below threshold

**Documentation:**
- Explain enforcement strategy and rationale
- Show how to adjust thresholds (temporarily or permanently)
- Document what shouldn't be tested (exclude_lines)
- Add coverage enforcement to CI best practices

**Rationale:** Ensures coverage doesn't regress without explicit decision to lower thresholds, preventing gradual quality degradation.

---

## Review Comment 6: Environment Variables and Secrets

**User:** We need guidance on env vars. What I'm thinking is an example.env with required vars. Make setup could copy that to .env (if not exists). Secrets should be distinguished somehow to make infrastructure handling clear (config vs secrets). More complex needs can use yaml or json files, but reference those files via paths in env vars (and equivalent path to infrastructure configs and secrets).

**Initial approach:** File-based secrets pattern
- `DATABASE_PASSWORD_PATH=./secrets/db_password`
- Secrets stored as files (infrastructure-compatible)
- Use `_PATH` suffix for secret paths

**User:** Lets remove the .txt from the secrets files, keeping in mind those paths may be replaced by infrastructure secrets paths.

**Change:** Remove file extensions from secrets (e.g., `secrets/db_password` not `.txt`)

**User:** In the same vein, replace the _FILE with _PATH in the secrets env vars, more applicable to either file or infra secrets paths.

**Change:** Use `_PATH` suffix instead of `_FILE` (e.g., `DATABASE_PASSWORD_PATH`)

---

## Review Comment 7: Organized Secrets Structure

**Issue:** Current flat secrets/ directory. Projects using multiple services benefit from organization.

**Decision:** Show both simple and complex project structures:

**Simple projects:**
```
secrets/
├── .gitkeep
├── db_password
└── api_key
```

**Complex projects:**
```
secrets/
├── .gitkeep
├── anthropic/
│   ├── api_key
│   └── api_key_backup
├── database/
│   ├── db_password
│   └── db_ssl_cert
└── external/
    └── stripe_api_key
```

**User question:** How are configs and secrets handled across infrastructure envs (dev, stage, prod)?

**Initial approach:** Multi-environment strategy with:
- Config files per environment (dev.yaml, stage.yaml, prod.yaml)
- Different secret paths per environment
- Infrastructure provides environment-specific values

---

## Major Refactoring: Direct Secret Injection

**User:** Before we commit, for a practical example, summarize how we would handle dev, stage, and prod in AWS using secrets manager.

**Analysis revealed a problem:**
- ECS/Fargate inject secrets as **environment variables**, not file paths
- Current pattern: `DATABASE_PASSWORD_PATH=/run/secrets/db_password`
- ECS pattern: `DATABASE_PASSWORD=actual-secret-value`

**Discovery:** Two conflicting patterns:
- **Pattern A:** File-based secrets (Kubernetes with volumes)
- **Pattern B:** Direct injection (ECS, Lambda, most cloud platforms)

**User question:** Can direct injection also work with Kubernetes via the AWS SDK and secrets manager?

**Research findings:**
- AWS Secrets Store CSI Driver can inject as environment variables
- External Secrets Operator syncs AWS Secrets Manager → K8s Secrets → env vars
- Direct injection works universally across all platforms

**User decision:** Lets refactor for the secrets store driver.

---

## Refactoring: Direct Injection Pattern

**Philosophy change:** Secrets are injected directly as environment variables (not file paths). This works universally across AWS, Kubernetes, Docker, and local development.

**Major changes:**

1. **Secrets are values, not paths:**
   - Before: `DATABASE_PASSWORD_PATH=./secrets/db_password`
   - After: `DATABASE_PASSWORD=actual-password-value`

2. **No secrets/ directory needed:**
   - Removed from project structure
   - Secrets come from infrastructure (env vars)
   - Local dev uses .env file with development credentials

3. **Simplified code:**
   ```python
   def get_secret(key: str) -> str:
       """Get secret from environment variable."""
       value = os.getenv(key)
       if not value:
           raise ValueError(f"Required secret {key} not set")
       return value
   ```

4. **Infrastructure examples:**
   - AWS ECS/Fargate with Secrets Manager
   - Kubernetes with AWS Secrets Store CSI Driver
   - Kubernetes with External Secrets Operator
   - Docker with -e flags
   - Local dev with .env

5. **AWS Secrets Manager organization:**
   ```
   myapp/dev/database-password
   myapp/dev/anthropic-api-key
   myapp/stage/database-password
   myapp/stage/anthropic-api-key
   myapp/prod/database-password
   myapp/prod/anthropic-api-key
   ```

6. **Multi-environment table:**
   | Environment | DATABASE_HOST | DATABASE_PASSWORD | APP_CONFIG_FILE |
   |-------------|---------------|-------------------|-----------------|
   | Development | localhost | local-dev-password | ./config/dev.yaml |
   | Staging | stage-db.rds.amazonaws.com | (from secrets manager) | ./config/stage.yaml |
   | Production | prod-db.rds.amazonaws.com | (from secrets manager) | ./config/prod.yaml |

**Rationale:**
- Universal pattern across all platforms
- Simpler code and configuration
- Industry standard approach
- Matches how cloud platforms actually work
- No file path resolution complexity

---

## PR Merge and Completion

**User:** Ok, review is clean. Squash merge the PR into main.

**AI Agent:** Executed:
```bash
gh pr merge 6 --squash --delete-branch
```

**Final commit:** "Add Python project standards document (#6)"
- Includes all review feedback
- Complete refactoring to direct injection pattern
- Comprehensive documentation with AWS/Kubernetes examples
- 1,719 lines of comprehensive Python standards

**Files created:**
- `code/python-standards.md` - Complete Python standards
- `code/README.md` - Updated to reference Python standards
- Issue #5 automatically closed by PR merge
- Feature branch automatically deleted

---

## Key Decisions Summary

1. **Tool Selection:** Modern Python tooling (uv, ruff, mypy, pytest)
2. **Package Management:** pip-audit over uv-secure (official PyPA tool)
3. **Coverage Enforcement:** Configurable Makefile variables with CI enforcement
4. **Secret Management:** Direct injection pattern (env vars, not file paths)
5. **Infrastructure Compatibility:** Works with ECS, Kubernetes (CSI Driver/External Secrets), Docker
6. **Multi-Environment:** Same variable names, different values per environment
7. **Configuration:** YAML files for complex settings, env vars for simple values
8. **Documentation:** Google-style docstrings, integration with existing docs standards

---

## Evolution of Thinking

**Initial concept:** File-based secrets with `_PATH` suffix
- **Reasoning:** Seemed infrastructure-compatible, explicit path handling
- **Problem discovered:** ECS/Fargate don't support this pattern

**Refined approach:** Direct injection as primary pattern
- **Reasoning:** Universal support across all platforms
- **Trade-off:** Simpler code, matches industry standards
- **Result:** Works seamlessly from local dev through production

**Key insight:** Research into actual cloud platform behavior (ECS, Kubernetes CSI Driver, External Secrets Operator) revealed that direct injection is the universal pattern, not file-based secrets.

---

## Impact

This standard establishes:
- Consistent Python project structure across the organization
- Modern tooling choices with clear rationale
- Security-first approach with automated scanning
- Multi-environment configuration strategy
- Infrastructure-agnostic secret management
- Comprehensive CI/CD integration
- Strong type safety and code quality practices

The standard is production-ready and can be immediately applied to new Python projects.
