# Git Branching Strategy

*Lightweight branch management for agile development*

## Overview

This strategy follows **[GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)** - a simple, branch-based workflow that supports continuous delivery.

**Core principle**: `main` branch is always deployable. All work happens in feature branches, merged via pull requests after review.

### Workflow Diagram

```mermaid
gitGraph
    commit id: "initial"
    commit id: "stable"
    branch 1-add-user-auth
    checkout 1-add-user-auth
    commit id: "add login"
    commit id: "add tests"
    checkout main
    merge 1-add-user-auth tag: "v1.1.0"
    commit id: "hotfix" type: HIGHLIGHT
    branch 2-add-notifications
    checkout 2-add-notifications
    commit id: "email notifs"
    checkout main
    merge 2-add-notifications tag: "v1.2.0"
```

## Guiding Principles

1. **Main is always deployable** - Never commit broken code directly to `main`
2. **Branch from main** - All work branches from and merges back to `main`
3. **Issue-driven development** - Create GitHub issues, branch from them
4. **Small, focused branches** - One feature/fix per branch, short-lived (hours to days)
5. **Merge via pull requests** - Always use PRs for review and CI validation

---

## Branch Types

### `main` - The Production Branch

**Purpose**: Represents deployable production-ready code

**Rules**:
- Always deployable and passing all tests
- Protected - requires pull request + review to merge
- No direct commits (except initial setup)
- Tagged with version numbers for releases

### Feature Branches

**Purpose**: Develop features, fix bugs, implement technical work

**Naming Convention**: Use GitHub's auto-generated branch names from issues

**Format**: `{issue-number}-{slugified-issue-title}`

**Examples**:
- Issue #1: "Write branching strategy standards doc" → `1-write-branching-strategy-standards-doc`
- Issue #42: "Fix login timeout error" → `42-fix-login-timeout-error`
- Issue #137: "Add email notifications" → `137-add-email-notifications`

**How to create**: Use GitHub's "Create a branch" feature directly from the issue

**Type classification**: Use issue labels (`feature`, `bug`, `enhancement`, `documentation`, `refactor`, etc.) instead of branch name prefixes

**Lifecycle**:
1. Create issue, assign labels
2. Create branch from issue (GitHub auto-names it)
3. Develop and commit iteratively
4. Open pull request when ready (auto-links to issue)
5. Merge to `main` when approved and CI passes
6. GitHub auto-closes issue and deletes branch

---

## Workflow

For detailed mechanics, see [GitHub Flow documentation](https://docs.github.com/en/get-started/using-github/github-flow).

### Starting Work

1. Create or find GitHub issue
2. Click "Create a branch" from the issue
3. Pull the branch locally and start working

### Keeping Branches Current

If `main` advances while working, sync your branch:

```bash
git fetch origin
git rebase origin/main  # or: git merge origin/main
git push --force-with-lease  # if rebased
```

Choose rebase (cleaner history) or merge (preserves history) and use consistently per project.

**Force push safety**:
- Always use `--force-with-lease` instead of `--force` (prevents overwriting others' work)
- Never force push to `main` (should be prevented by branch protection)
- Coordinate with teammates if sharing a feature branch

### Merging to Main

1. Open pull request (links to issue automatically)
2. Get review approval and passing CI
3. **Squash and merge** (recommended) - creates clean single commit per issue
4. Branch auto-deleted, issue auto-closed

**Note on squash merging**: When you squash and merge, all individual commits on the branch are combined into a single commit. This means:
- Individual commit messages are preserved in the squashed commit body
- The PR title becomes the final commit message summary
- Write clear, incremental commits during development for your own tracking
- Write a clear PR title since it becomes the commit message in `main`

---

## Commit Messages

### Format

```
<type>: <summary in present tense>

[optional body: context, reasoning, references]
```

### Types

Common types (simplified subset of [Conventional Commits](https://www.conventionalcommits.org)):

- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code restructuring
- `docs:` - Documentation changes
- `test:` - Test additions/updates
- `perf:` - Performance improvements
- `chore:` - Build, dependencies, tooling
- `ci:` - CI/CD pipeline changes

### Examples

```
feat: add email notification preferences

Implements notification preferences UI and API endpoint
for users to configure email notification settings.

Refs: #137, docs/engineering/designs/notification-system.md
```

```
fix: prevent login timeout on slow connections

Increase timeout from 5s to 30s and add retry logic.

Fixes: #42
```

### Guidelines

- Use present tense: "add feature" not "added feature"
- Keep first line ≤50 chars
- Reference issue number and specs when applicable
- Explain why, not what (code shows what)

See [Conventional Commits](https://www.conventionalcommits.org) for more details.

---

## Pull Request Guidelines

### PR Title

Use the issue title or a clear summary of the change:
- ✅ `Add user notification preferences UI`
- ✅ `Fix login timeout on slow connections`
- ❌ `Updates` (too vague)

### PR Description

```markdown
## What
Brief description of the change

## Why
User/business value or problem being solved (link to issue/spec)

## How
Implementation approach (reference design doc if applicable)

## Testing
How this was tested (unit tests, manual testing, edge cases)

## Related
- Closes: #123
- Spec: docs/engineering/designs/feature-name.md (if applicable)
```

### PR Size

**Target**: 200-400 lines of changes (excluding generated code)

**Why**: Smaller PRs = faster, better reviews

**How**: Break large features into multiple issues/PRs, use feature flags if needed

---

## Release and Versioning

### Semantic Versioning

Follow [semver](https://semver.org): `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Tagging Releases

```bash
git checkout main
git pull origin main
git tag -a v1.2.0 -m "Release 1.2.0: Add notification system"
git push origin v1.2.0
```

Maintain `CHANGELOG.md` or use [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github).

---

## Common Scenarios

### Hotfix for Production Bug

1. Create urgent issue with `bug` and `priority:high` labels
2. Branch from `main`: `45-fix-critical-auth-bug`
3. Fix with minimal changes, add test
4. Expedited PR review and merge
5. Tag as patch release (e.g., v1.2.1), deploy immediately

### Long-Running Feature

**Problem**: Feature takes 2+ weeks, don't want stale branch

**Solution**:
- Break into multiple issues/sub-features
- Each gets own branch and PR (keep each under 1 week)
- Use feature flags to hide incomplete UI
- Merge small increments continuously

### Experimental Work

1. Create issue labeled `experiment` or `spike`
2. Document in `docs/experiments/feature-name.md`
3. Develop on branch, timebox the exploration
4. **If successful**: Clean up, merge to `main`
5. **If unsuccessful**: Document findings in issue, close without merging

---

## Anti-Patterns

### ❌ Long-Lived Feature Branches

**Problem**: Diverge from `main`, painful merges, integration issues

**Solution**: Break work into smaller increments, merge frequently (max 1 week per branch)

### ❌ Direct Commits to Main

**Problem**: Skips review and CI validation

**Solution**: Protect `main` branch, require PRs (configure in repository settings)

### ❌ Large, Multi-Purpose PRs

**Problem**: Hard to review, slow feedback, risky merges

**Solution**: One issue per PR, use feature flags for incremental merges

### ❌ Branches Without Issues

**Problem**: No context, hard to track, unclear purpose

**Solution**: Create issue first (even for small fixes), use issue-based branching

### ❌ Stale Branches Not Synced

**Problem**: Merge conflicts, integration problems discovered late

**Solution**: Rebase/merge from `main` regularly (daily for active branches)

---

## Integration with AI Development

This strategy works well with AI-assisted development:

**AI benefits from clear context**:
- Issue descriptions provide full context for AI agents
- Branch names tied to issues help AI understand intent
- Specs linked in issues give AI complete requirements

**Best practices with AI tools**:
- Provide issue description and specs as context to AI
- Keep branches focused so AI maintains context
- Generate code in small increments (commit frequently)
- Always review and test AI-generated code before pushing
- Document AI-generated approaches in commit messages

**Example**: When asking AI to implement a feature, reference the issue number and include links to relevant specs from `docs/` directory.

---

## Branch Protection Configuration

Configure these rules for `main` branch in repository settings:

- ✅ Require pull request before merging
- ✅ Require at least 1 approval
- ✅ Require status checks to pass (CI/tests)
- ✅ Require branches to be up to date before merging
- ✅ Delete head branches automatically after merge

See [GitHub branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches) for setup details.

---

## When to Deviate

This strategy assumes:
- Continuous delivery model
- Small to medium team
- Web services / cloud deployments

**Consider alternatives if**:
- Multiple production versions maintained simultaneously → Use [GitFlow](https://nvie.com/posts/a-successful-git-branching-model/)
- Regulated deployments with long certification cycles → Add release branches
- Very large team (100+ developers) → May need coordination branches

Document deviations and rationale in project README.

---

## References

- [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)
- [Creating branches from issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/creating-a-branch-for-an-issue)
- [Semantic Versioning](https://semver.org)
- [Conventional Commits](https://www.conventionalcommits.org)

---

## Status

**Draft** - This standard is in active development and subject to revision based on practical experience.
