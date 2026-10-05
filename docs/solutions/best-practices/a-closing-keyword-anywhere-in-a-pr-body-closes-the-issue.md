---
title: A closing keyword anywhere in a pull request body closes the issue
date: 2026-10-05
category: best-practices
module: pull-requests
problem_type: workflow_issue
component: tooling
severity: medium
applies_when:
  - "One issue is delivered by several pull requests, each marked as part of it"
  - "A pull request body describes another pull request's closing line, or quotes one"
  - "A pull request is stacked on another branch and carries the issue's closing line"
  - "Editing a pull request body or a commit message before merge"
resolution_type: workflow_improvement
related_components:
  - development_workflow
tags: [github, pull-requests, issues, closing-keywords, multi-pr, stacked-prs, verification]
---

# A closing keyword anywhere in a pull request body closes the issue

## Context

Issue #75 was delivered in three pull requests. The first two were each meant to say "Part of #75", and only the third was to close the issue.

- **[PR #78](https://github.com/rmorison/engineering-standards/pull/78)**, piece 1, described the plan in its Related section. One line of that section read:

  ```text
  - Part of #75. Pieces 2 (framework entry and the missing-gitleaks check) and 3 (pre-push) follow, and the last says "Closes #75".
  ```

  GitHub read the quoted `Closes #75` as this pull request's own closing reference: its `closingIssuesReferences` is `[75]`. The pull request merged at 23:17:18 UTC on 2026-10-04. Issue #75 closed at 23:17:20, two seconds later, with two pieces still unmerged. It was reopened at 23:22:12 (issue #75's timeline).
- **[PR #79](https://github.com/rmorison/engineering-standards/pull/79)**, piece 2, had the same pattern before merge: "Piece 3 (pre-push) follows and closes #75." It was found and reworded to "Piece 3 (pre-push) is the last piece of #75." Its `closingIssuesReferences` then read `[]`, and it merged without closing anything.
- **[PR #83](https://github.com/rmorison/engineering-standards/pull/83)**, piece 3, carried the real closing line. It was stacked on piece 2's branch until #79 merged. GitHub's docs say the keywords are interpreted only on a pull request that targets the default branch, so the line could take effect only after the pull request was retargeted to `main`. `closingIssuesReferences` then read `[75]`, and merging it closed #75.

## Guidance

**GitHub does not read a pull request body for meaning. It closes the issue for any closing keyword followed by an issue number, wherever it sits. Check what GitHub parsed, not what the body says.**

1. **Know the keywords.** GitHub's docs list `close`, `closes`, `closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves` and `resolved` ([Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)). They work "in the pull request's description or in a commit message". In #78, a keyword inside quotation marks, in a sentence about a different pull request, still counted. Whether code formatting shields one was not tested here, so do not rely on it.
2. **In a pull request that is only part of an issue, put no closing keyword before the issue number anywhere.** That covers the Related section, prose that describes the plan, and the commit messages on the branch. Name the last piece another way, for example "Piece 3 is the last piece of #75."
3. **Check GitHub's answer before merge, after every edit to the body:**

   ```sh
   gh pr view <n> --json closingIssuesReferences --jq '[.closingIssuesReferences[].number]'
   ```

   A pull request that is part of an issue must print `[]`, and the one that closes it must print exactly that issue. This is the check to trust. Any text search of the body only approximates GitHub's parser.
4. **Search the body file before posting it** to catch the common case early:

   ```sh
   grep -niE '(close[sd]?|fix(e[sd])?|resolve[sd]?)[^a-z0-9]{0,3}#' body.md
   ```

   It finds `closes #75`, `Closes: #75` and a quoted `"Closes #75"`. On a pull request that is only part of an issue, any hit needs rewording. On the closing one, exactly one hit should remain.
5. **For a stacked pull request, check again after retargeting.** Its closing line does nothing while it targets another branch. After `gh pr edit <n> --base main`, step 3 should print the issue.
6. **If an issue closes by mistake, reopen it and say why on the issue.**

## Why This Matters

The issue is the record of what is done. A closed issue drops off the board and out of the sprint, so the work it still holds stops being tracked. Nothing fails loudly when this happens. The merge succeeds, the issue closes with a link to a real pull request, and everything looks deliberate. #75 was caught within five minutes only because someone was watching the issue when piece 1 merged.

The defaults make the mistake easy to repeat:
- **The PR template:** `.github/pull_request_template.md`, like the adopter copy in `templates/.github/pull_request_template.md`, prefills `- Closes: #` under Related.
- **The branching standard:** `process/git-branching-strategy.md` says merging auto-closes the issue, without saying that this depends on a keyword in the body or a commit message, or on the pull request targeting the default branch.

So a split issue starts each pull request one step from closing it early. Both texts are candidates for a follow-up. This doc does not change them.

Related learnings:
- [a-check-must-read-a-file-the-way-its-consumer-does](./a-check-must-read-a-file-the-way-its-consumer-does.md): here the consumer is GitHub's keyword parser. A grep of the body is a stand-in for it, and `closingIssuesReferences` is the parser's own answer.
- [a-corrected-claim-is-not-a-verified-claim](./a-corrected-claim-is-not-a-verified-claim.md): rewording #79's body was a correction, and re-reading `closingIssuesReferences` was what verified it.

## When to Apply

- Splitting one issue into several pull requests, including stacked ones
- Writing a pull request body that describes the plan for the remaining pieces
- Keeping the PR template's prefilled `Closes: #` line on a pull request that does not finish the issue
- Writing commit messages on a branch that will merge into the default branch
- Retargeting a stacked pull request to the default branch

## Examples

PR #78 merged with its Related line unchanged, and it still lists the issue:

```text
... and 3 (pre-push) follow, and the last says "Closes #75".   -> closingIssuesReferences [75]
```

PR #79's line was reworded before merge. The "before" text is from that edit; GitHub keeps no history of body edits:

```text
before:  Piece 3 (pre-push) follows and closes #75.
after:   Piece 3 (pre-push) is the last piece of #75.   -> closingIssuesReferences []
```

PR #83 held its closing line for #75 throughout. Its timeline shows the base changed to `main` six minutes after #79 merged. Before that, GitHub's documented rule leaves the keyword uninterpreted. After it:

```text
base main   -> closingIssuesReferences [75]
```
