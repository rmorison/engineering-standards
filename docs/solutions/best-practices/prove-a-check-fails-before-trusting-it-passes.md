---
title: Prove a check fails before trusting that it passes
date: 2026-09-20
category: best-practices
module: documentation-checks
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - Adding a CI check meant to block a class of defect
  - Reading a command's exit code as a yes/no answer
  - Pinning a dependency whose exact version is the point of the check
  - Reviewing a check that has never reported a failure
resolution_type: workflow_improvement
related_components:
  - documentation
  - development_workflow
tags: [ci, verification, false-negative, exit-codes, gitignore, lockfile, tooling]
---

# Prove a check fails before trusting that it passes

## Context

[PR #36](https://github.com/rmorison/engineering-standards/pull/36) added this repository's
first automated checks, after three Markdown defects reached `main` and were found by eye.

Three separate verification steps *in that same branch* reported success while not doing
what they claimed. Two were caught by a final scrub review; one was caught only because
the conclusion it produced contradicted other evidence. None of them failed loudly. Each
returned the same output it would have returned if it were working.

A check that fails open is worse than no check. No check at least leaves intact the
vigilance that would otherwise catch the defect. A check that silently passes retires that
vigilance and returns nothing in its place.

## Guidance

**Before trusting a check, construct the failure it exists to catch and confirm the check
reports it.** Green on a clean tree is not evidence. Green is the same answer a check that
never ran gives.

Three habits follow from it:

1. **Plant the defect.** Write the broken case into the tree, run the check, confirm it
   fails, then remove it. This is the only observation that distinguishes a working check
   from a check whose scope quietly excludes the file you care about.
2. **Do not read "the command succeeded" as "the command answered yes."** Many tools exit
   `0` for *any* well-formed query, including one whose answer is no. Find the flag or the
   companion command that distinguishes the two.
3. **Make a pin real rather than declared.** Naming an exact version in a manifest does not
   pin anything if the install step resolves a fresh tree. If the version is the point of
   the check, the lockfile is part of the check.

## Why This Matters

The whole value of these checks is negative evidence: nothing was found, therefore this
class of defect is not present. That inference is only as good as the check's ability to
find something. A check that cannot fail converts an unknown into a false assurance, and
false assurance is what stops anyone from looking again.

This is sharper for checks added *after* a defect ships. They are written in reaction to a
known miss, so they are trusted immediately and rarely revisited. The two defective checks
here were both written on the same branch as the defects they were meant to prevent, and
both shipped in the same commit as the rule that would have caught them.

## When to Apply

- Adding any check to `scripts/check-docs.mjs` or to a workflow under `.github/workflows/`
- Adding or changing a skip list, an ignore pattern, or a path filter, since these are the
  parts of a check that remove work silently
- Reading exit codes from `git` plumbing commands, which answer questions rather than
  perform actions
- Reviewing a check that has run for a while and never failed

## Examples

### A skip list matched basenames instead of paths

`scripts/check-docs.mjs` skipped `archive`, `plans` and `scripts` by directory *name* at any
depth. A future `process/plans/` or a `scripts/` directory inside a template would have
dropped out of every check with nothing in the output saying so.

Found by planting the defect. `process/plans/` does not exist in this repository and was
created only for the probe, because its basename `plans` was on the skip list:

```bash
mkdir -p process/plans
echo '[broken](./does-not-exist.md)' > process/plans/probe.md
node scripts/check-docs.mjs   # reported green
rm -rf process/plans
```

The fix matches repo-relative paths, and the same probe now fails as it should. See the
`SKIP_PATHS` comment in `scripts/check-docs.mjs`, which records why these are paths and not
names.

Writing this document surfaced a fourth instance of the same problem, and the paragraph you
are reading is the evidence. The probe above was originally a `printf` split across two
arguments, contorted so its broken link would not be literal Markdown: the link check read
every line of every file, fenced code blocks included, so it could not distinguish an example
of a broken link from a broken link. Check 4 tracked fences; check 2 did not.

Issue #37 fixed it. Fence tracking now lives in one place and every check that needs to tell
prose from an example reads it, so the probe is a plain `echo` again. The same pass found that
the check had never verified a link's anchor either — `#branch-naming`, pointing at a heading
renamed to "Feature Branches", had already shipped green and was caught by eye. A check that
cannot be shown its own defect is a check nobody can plant a defect in.

### `git check-ignore -v` exits 0 for both answers

Verifying the `.gitignore` negation produced the wrong conclusion: the exception looked
broken when it had worked. The cause is worth knowing precisely, because the flag added to
get *more* information is what removed the answer.

Plain `check-ignore` discriminates correctly. In a minimal repository with
`package-lock.json` ignored and `!scripts/package-lock.json` negating it, both files
untracked:

```
$ git check-ignore scripts/package-lock.json   # negated, so not ignored
exit=1

$ git check-ignore package-lock.json           # ignored
package-lock.json
exit=0
```

Add `-v` to see *which* pattern matched, and exit `0` widens to mean "matched some pattern",
negations included:

```
$ git check-ignore -v scripts/package-lock.json
.gitignore:2:!scripts/package-lock.json	scripts/package-lock.json
exit=0

$ git check-ignore -v package-lock.json
.gitignore:1:package-lock.json	package-lock.json
exit=0
```

The `-v` output does disclose the difference, in the leading `!`. The exit code does not.
`git add --dry-run` answers the question that was actually being asked, and its exit codes
differ in that same minimal repository: `0` for the tracked-able path, `1` for the ignored
one.

The transcripts above are a minimal reproduction, not this repository. Reproducing them here
needs `--no-index`, because `scripts/package-lock.json` is now tracked and `check-ignore`
skips tracked paths entirely, exiting `1` whatever the patterns say. That is a third way for
the same command to hand back a confident and misleading answer.

### A pin that was declared but not installed

`.github/workflows/docs.yml` carried a comment calling the Mermaid version load-bearing,
because the point of the check is to reproduce the parser behavior GitHub applies. The step ran `npm install` against a lockfile that `.gitignore` excluded, so the
transitive tree resolved fresh on every run and the parser under test was whatever npm
picked that day.

The pin is real now: `scripts/package-lock.json` is committed behind an explicit exception
at `.gitignore:60-63`, and the workflow installs with `npm ci`
(`.github/workflows/docs.yml:32-39`).

## Related

- `scripts/check-docs.mjs`: the four checks and the defect class each one exists for
- [`process/documentation-standards.md`](../../../process/documentation-standards.md): the Automated Checks section and the local command
- [`process/compound-engineering-integration.md`](../../../process/compound-engineering-integration.md): the drift note, on the related problem of corrections that do not propagate
