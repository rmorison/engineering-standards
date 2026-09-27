# Contributing

Thanks for helping improve these standards. This repository's product is Markdown, so a broken link or a diagram that fails to render is a real defect, and CI treats it as one.

## Terms

Contributions are accepted under the repository's [MIT license](LICENSE): inbound equals outbound. There is no contributor license agreement, and commits do not need a `Signed-off-by:` line. The reasons, and when a repository should choose otherwise, are in [Developer Certificate of Origin](process/repository-standards.md#developer-certificate-of-origin).

## Before You Open a Pull Request

Every pull request runs the checks below in CI. Running them first saves a round trip. They need Node 22, Python 3.10 or later, and gitleaks 8.24.2 installed as [Adopting the Gate](process/repository-standards.md#adopting-the-gate) describes.

```bash
npm ci --prefix scripts && node scripts/check-docs.mjs   # links, anchors, Mermaid, fences
node scripts/check-template-kit.mjs                       # the starter kit's settings and hooks
python scripts/check_secret_refs.py --standard            # the Secrets rule's examples
sh scripts/test-leak-gate.sh                              # the leak gate's rules still fire
sh scripts/leak-gate.sh range origin/main..HEAD           # no leak in your commits
```

[Automated Checks](process/documentation-standards.md#automated-checks) says what each one catches.

Never write an absolute path from your own machine into a file here. Write `~/`, `$HOME/`, a `<username>` metavariable, or a repository-relative path. The leak gate fails on the first form.

## Conventions

- Branches, commit messages and pull requests follow [Git Branching Strategy](process/git-branching-strategy.md). A pull request title is a conventional commit subject, because it becomes the squash commit.
- Labels come from [Label Strategy](process/issue-tracking.md#label-strategy).
- A change to a standard updates every document that links to the rule it changes. One document owns each rule; the rest link to it.

## Reporting Problems

Bugs, gaps and questions go in GitHub issues. Security problems go privately, as [SECURITY.md](SECURITY.md) describes.

## For Maintainers

Private value rules, such as private repository names and internal hostnames, run only on a maintainer's machine, from a list declared in git config. [Private Values](process/repository-standards.md#private-values) covers the list. Before merging a pull request that did not come from a machine holding the list, run the value rules over its commits. Run from `main`'s own checkout, never the pull request's:

```bash
git fetch origin pull/<N>/head:refs/leakgate/pr-<N>
sh scripts/leak-gate.sh range origin/main..refs/leakgate/pr-<N>
```

Changes to `.gitleaks.toml`, `.gitleaksignore` and `.github/workflows/leaks.yml` can weaken the leak gate, so review them as security changes.
