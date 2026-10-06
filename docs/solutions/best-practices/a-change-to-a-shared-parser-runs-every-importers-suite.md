---
title: A change to a shared parser runs every importer's suite
date: 2026-10-06
category: best-practices
module: claude-leak-hook
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - "Changing a function, return shape or data that another script imports, such as the leak hook's parse()"
  - "An importer of the code you are changing sits on an open pull request, so CI on your pull request cannot run its tests"
  - "Rebasing an importer onto a change to the code it imports"
  - "Reviewing a fix to a guard hook's parser"
resolution_type: workflow_improvement
related_components:
  - testing_framework
  - development_workflow
tags: [claude-code, hooks, parser, shared-module, importer, ci, review, fail-open, leak-gate, policy-hook]
---

# A change to a shared parser runs every importer's suite

## Context

Two Claude Code hooks share one shell-command parser. `scripts/claude_policy_hook.py` (#90, for #76) imports `Deny`, `option` and `parse` from `scripts/claude_leak_hook.py` (`scripts/claude_policy_hook.py:55`). A failed import exits 2, so a missing leak hook denies every call. Any exception at run time reaches the policy hook's catch-all and also exits 2 (`scripts/claude_policy_hook.py:575`).

#90's plan chose import over copy (KTD4 in `docs/plans/2026-10-05-2058-feat-agent-policy-hook-plan.md`), because a copy of the parser would drift. The plan expected that "its own tests in CI catch a rename on the same pull request that makes it." That holds once both hooks are on `main`: the "Prove the rules and the wrapper fire" step of `.github/workflows/leaks.yml` runs both suites.

It did not hold in sprint 2, because the parser changed while #90 was still an open pull request. #91, for #84 and #87, rewrote what `parse()` returns, and nothing in #91's CI exercised the policy hook. #91's first head, c3dd28b, passed all four checks with 263 leak-hook fixtures. The break showed up in two other places:

- **In review.** The Claude review of #91 (finding B) noted that `parse()` now returned an object, while #90 calls `commands, _ = parse(command, cwd)` (`scripts/claude_policy_hook.py:519`). That raises `TypeError` on every parsed command, and the catch-all turns it into a denial of every Bash call.
- **In #90's own suite, run by hand.** Restoring the tuple shape was not enough. Three of #90's tests still failed, because the new parser cut each `$(...)` inside a command word down to `$()`. The policy hook reads the word `"$(git branch --show-current)"` to recognise a push of the current branch (#91, issuecomment-6009457619). Only running the importer's tests showed this. The shape of the return value was right; its contents were not.

The fix kept the imported contract and moved the new behaviour behind a new name:
- `parse()` still returns `(commands, words)`, and its commands keep their words as written. Its docstring now says so (`scripts/claude_leak_hook.py`, `parse`).
- The leak hook itself calls `parse_command()`, which builds the words it matches in a second pass.

Results:
- #90's suite, run against #91's hook: "209 passed, 0 failed" (same comment).
- #90 was then rebased onto #91's merge (29ab5b8). Its body records the policy suite at 209 and the leak suite at 270 on the rebased head b726e81, and that the parser invariants it relies on still hold: `parse()` shape, `cd` tracking, `ValueError` on unbalanced quotes, and `option()`. It merged as 9a41630.
- #93 changed `parse_command()` again (PR #94). Both suites ran on its final head: "281 passed" and "219 passed" at 03c6cf2 (#94, issuecomment-6021760121). A fixture in the policy suite pins what the change meant for the importer: "R5 deny: an unquoted substitution is built at run time, even on a feature branch" (`scripts/test_claude_policy_hook.py`).

## Guidance

1. **Find every importer before you change shared code**, including importers on open pull requests. Search the tree for `from <module> import`. Also search the diffs of open pull requests, for example `gh pr diff <N>`, because an importer on a branch is invisible to your CI. #90 was one.
2. **Run each importer's suite against your change.** Once an importer is on `main`, CI runs its suite, provided the workflow lists it. For one on an open pull request, check out its head in a scratch worktree, copy your changed module over its copy, and run its suite. That is how #91 was checked against #90's branch (issuecomment-6009457619). #94's fix was checked against #90's head b726e81 the same way before #90 merged (#94's body), and against the merged policy suite after the rebase.
3. **Keep the imported contract, both the shape and the contents callers read.** Put new behaviour behind a new name rather than changing what importers receive. A test of the return type alone would have passed at #91's first fix and still broken three policy decisions.
4. **When a change alters what an importer sees, pin it in the importer's suite.** Show the pin failing against a stub before you trust it, as with the "unquoted substitution" fixture in #94.
5. **Land the shared change first, then rebase the importer and rerun both suites.** That was the order for #91, then #90, then #94.

## Why This Matters

A green check on the pull request that changes a shared parser proves only that the parser's own suite passes. It says nothing about callers that CI does not run. For these hooks, a contract break fails closed: the importer's catch-all denies every Bash call on the machine where both are installed. That is safe, but it stops every agent session. A contents change is quieter. Decisions can shift in either direction with no error at all, which is what the three failing #90 tests caught.

## When to Apply

- Any change to `parse()`, `parse_command()`, `Command`, `option()` or `Deny` in `scripts/claude_leak_hook.py`, while `scripts/claude_policy_hook.py` imports from it. #95, an open fail-open in the same parser, is the next such change.
- Any module in the repository that another script imports. Not for a file with no importers, where the module's own suite is the whole story.

## Examples

- **Before, #91 at c3dd28b:** the leak-hook suite passed 263/263 and CI was green. The return type had changed, and the policy hook would have denied every call once both were installed.
- **After, #94 at 03c6cf2:** the leak suite passed 281/281 and the policy suite 219/219. Ten leak fixtures, and the new policy pin against a stub, were seen failing first. The policy hook's decision on `git push origin $(git branch --show-current)` was checked against both parsers, and was unchanged.

## Reviews of the guard hook kept finding fail-opens

Each review of the leak hook this sprint found a real fail-open:
- **#91's first review** found that heredoc text the stripper missed went unmatched, a fail-open the change itself introduced. It was fixed in #91 at 314f9ea.
- **#91's review of the fix delta** found that an unquoted `$(...)` let a body file through unread. This was outside the delta and had been present since cf50604. It became #93, and #94 repaired it.
- **#94's review** found that a `$(...)` the parser cannot close did the same. This was also present on `main` before #94, and was fixed in #94 at 03c6cf2.

[a-corrected-claim-is-not-a-verified-claim](./a-corrected-claim-is-not-a-verified-claim.md) already says to review a fix delta on its own. This sprint adds one point for a guard hook's parser. Two of the three findings sat outside the lines that changed. So a parser review is scoped to the parser's handling around the change, not just to the diff.

## Relation to other learnings

- [a-guard-hook-fails-open-unless-every-path-exits-2](./a-guard-hook-fails-open-unless-every-path-exits-2.md) is why an importer break here denies rather than allows: the import and the catch-all both end in exit 2. This doc is about not shipping that break at all.
- [a-local-pass-proves-only-the-tool-versions-it-ran-on](./a-local-pass-proves-only-the-tool-versions-it-ran-on.md) has the same shape on another axis. A pass proves only what it ran against: there, the tool versions, and here, the importers. It stays separate because its fix is CI on the pushed head, which could not have caught an importer that was not on `main`.
- [prove-a-check-fails-before-trusting-it-passes](./prove-a-check-fails-before-trusting-it-passes.md) applies to the pin in step 4.
