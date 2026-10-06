<!--
Skeleton CONTRIBUTING.md. Fill in every <placeholder> and delete what does
not apply. It is required once people outside the team open pull requests,
and recommended before then:
https://github.com/rmorison/engineering-standards/blob/main/process/repository-standards.md#contributing-guide
Delete this comment when done.
-->

# Contributing to <project>

## Terms

Contributions are accepted under the project's license, <license> (see `LICENSE`): inbound equals outbound.

<!-- Choose one and delete the other. The trade-offs:
https://github.com/rmorison/engineering-standards/blob/main/process/repository-standards.md#developer-certificate-of-origin -->
There is no contributor license agreement, and commits do not need a `Signed-off-by:` line.

Every commit must carry a [Developer Certificate of Origin](https://developercertificate.org/) sign-off (`git commit -s`), added by the person submitting it. <Say where the sign-off must land if pull requests are squash-merged.>

## Setup

```bash
<commands from a fresh clone to a working development environment>
```

## Before You Open a Pull Request

Open the description with At a glance; see Git Branching Strategy § PR Description: https://github.com/rmorison/engineering-standards/blob/main/process/git-branching-strategy.md#pr-description

```bash
<the checks CI runs, in the order to run them>
sh scripts/leak-gate.sh range origin/main..HEAD   # no leak in your commits
```

## Conventions

- Branches, commit messages and pull requests follow <link to the project's git conventions, or https://github.com/rmorison/engineering-standards/blob/main/process/git-branching-strategy.md>.
- <Any project-specific rules a contributor would otherwise learn in review.>

## Reporting Problems

Bugs and questions go in issues. Security problems go privately, as [SECURITY.md](SECURITY.md) describes.

## For Maintainers

Before merging a pull request that did not come from a machine holding the private value list, run the value rules over its commits from the default branch's own checkout, never the pull request's:

```bash
git fetch origin pull/<N>/head:refs/leakgate/pr-<N>
sh scripts/leak-gate.sh range origin/main..refs/leakgate/pr-<N>
```

The list and its declaration: https://github.com/rmorison/engineering-standards/blob/main/process/repository-standards.md#private-values
