## At a glance

<!-- For someone who uses the repository rather than contributes to it. Write it when opening the pull request, and bring it up to date before merge, Spec drift especially.
     Plain language: say what a check does, not its name; no file names or commands a user wouldn't type. Word limits are hard.
     https://github.com/rmorison/engineering-standards/blob/main/process/git-branching-strategy.md#at-a-glance -->

**Problem.** <!-- What was wrong or missing, and why it matters to that reader. 125 words or fewer. No drift here. -->

**Spec drift.** <!-- What was added, cut or changed after the issue was filed (with no issue, after the plan was written), why, and who decided. 50 to 100 words, or exactly: None. -->

**Solution.** <!-- How this pull request solves it: what it does and where it steps in, in plain language. 125 words or fewer. -->

## What

<!-- Brief description of the change -->

## Why

<!-- The technical reason for the change, for contributors (the user-facing problem is in At a glance); link the issue or spec -->

## How

<!-- Approach, and the decisions a reviewer should weigh -->

## Testing

<!-- The checks run, and anything verified by hand -->

## Related

<!-- Keep one of the two lines below. The first closes the issue when this PR merges into the default branch; "Part of" leaves it open.
     GitHub acts on a closing keyword (close, fix, resolve and their forms) followed by an issue number ANYWHERE in this body, even quoted.
     Check the body before merge: gh pr view <pr> --json closingIssuesReferences --jq '[.closingIssuesReferences[].number]'
     A keyword in a commit message on the branch acts too, once the commit reaches the default branch. -->
- Closes #<n>
- Part of #<n>

<!-- For a bug fix, also give Problem, Root cause and Fix: see process/technical-work-workflow.md -->

## Maintainer

- [ ] Private value rules run over this pull request's commits from `main`'s checkout (`CONTRIBUTING.md`, For Maintainers)
