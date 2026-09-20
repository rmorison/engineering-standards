# Fence-Aware Documentation Checks

```yaml
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
issue: 37
branch: 37-fence-aware-doc-checks
created: 2026-09-20
```

## Problem

`scripts/check-docs.mjs` runs four checks over every Markdown file in the
repository. Check 4 tracks fenced code blocks and skips them. Checks 2 and 3 do
not: they read every line of every file, so they cannot distinguish **an example
of a defect from the defect itself**. Documenting a broken link requires
contorting the document so the example is not literal Markdown — which is what
`docs/solutions/best-practices/prove-a-check-fails-before-trusting-it-passes.md`
had to do, splitting a `printf` across two arguments so its probe link would not
trip the checker it was describing.

A second gap sits in the same function. `scripts/check-docs.mjs:116` excludes
same-file anchors at the regex (`(?!https?:|mailto:|#)`), and `:117` strips the
fragment off cross-file links (`match[1].split('#')[0]`). Anchors are therefore
never checked in either direction. The repository currently carries **18
cross-file anchor links and 16 same-file anchor links**, almost all of them
carrying the "one document owns a rule, the others link to it" pattern that
issue #27 established. CI verifies none of them. One dead anchor
(`#branch-naming`, where the heading is `Feature Branches`) was caught by hand
during PR #39 review and would otherwise have shipped green.

## Outcome

Both gaps closed in one pass over `checkLinks`, with fence tracking written once
and shared by every check that needs it — including the new heading collector,
which needs it for the same reason checks 2 and 3 do.

## Requirements

| ID | Requirement |
|----|-------------|
| R1 | Fence tracking for telling prose from an example exists in exactly one place and is consumed by every check that needs it. No check re-derives it. |
| R2 | Check 2 (relative links) ignores links inside fenced code blocks. |
| R3 | Check 3 (accidental blockquote) ignores lines inside fenced code blocks. |
| R4 | Check 4 (unmarked lists) keeps its current behavior, now sourced from the shared tracker rather than its own copy. |
| R5 | Links inside inline code spans are not checked, because they do not render as links. |
| R6 | Masking a code span must not change whether check 3 fires on the surrounding line. |
| R7 | Same-file anchors (`#foo`) are counted and verified against the target file's headings. |
| R8 | Cross-file anchors (`./bar.md#foo`) are verified against `bar.md`'s headings, in addition to the existing file-exists check. |
| R9 | Heading slugs match what GitHub generates, including its duplicate-heading disambiguation. |
| R10 | Headings inside fenced code blocks are not collected, because GitHub does not generate anchors for them. |
| R11 | A probe confirms both directions for fences: a broken link inside a fence passes, the same link outside a fence fails. |
| R12 | A probe confirms both directions for anchors: a dead anchor fails, a live anchor passes. |
| R13 | The `printf` workaround in the learning document reverts to a plain `echo`, and the paragraph recording the fence gap as unfixed is updated. |
| R14 | `process/documentation-standards.md` describes what the checks now cover. |
| R15 | An unterminated code fence fails rather than silently removing the rest of the file from checks 2 through 4. |

## Key Decisions

### KD1 — Absorb the anchor gap into this change *(session-settled: user-directed)*

Both gaps are in `checkLinks`. Fixing them separately means two passes over the
same function and two probes over the same corpus. The anchor gap is also the
larger one by count: 34 unverified anchor links against zero current instances
of the inline-code-span case.

The 18/16 split above is counted, not grepped. The first pass read it off
`grep -n`, which reports matching *lines*: `process/git-branching-strategy.md:120`
carries two same-file anchors on one line and was counted once. The totals
reconcile against the checker itself — main's version reports 192 links
including one inside a fence, and 192 − 1 + 16 = 207.

### KD2 — Vendor `github-slugger`, do not hand-roll the slugifier *(session-settled: user-directed)*

A false-positive-prone anchor check is worse than no anchor check: it trains
people to ignore the output. This repository's headings are hostile to a naive
slugifier — `### ❌ Long-Lived Feature Branches`, `` ### `main` - The Production
Branch ``, `## CI/CD`, `### Phase 1: [Name] ([X points])` — and
`process/issue-tracking.md` has three `## Acceptance Criteria` headings whose
disambiguation suffixes depend on document order.

`github-slugger@2.0.0` is the library GitHub's own Markdown pipeline uses.
Probed against the headings above it produces `-long-lived-feature-branches`,
`main---the-production-branch`, `cicd`, `phase-1-name-x-points`, and the
`acceptance-criteria` / `acceptance-criteria-1` pair. Fidelity by construction
rather than by re-derivation.

It also fits the pattern `.github/workflows/docs.yml` already documents: pinned
in `scripts/package.json`, installed from the committed `scripts/package-lock.json`
via `npm ci`.

### KD3 — Mask inline code spans rather than strip them *(session-settled: user-directed)*

Issue #37 asks that inline code spans be decided rather than left unnoticed.
They are the same defect class as fences — `` `[text](./foo.md)` `` renders as
literal text, not a link — so they should be excluded.

Removal is the obvious implementation and it is wrong. `` - `foo` > bar ``
would collapse to `-  > bar`, which **matches** check 3's `/^\s*[-*+]\s*>/` and
would report a blockquote that does not exist. Verified rather than assumed:
against that line the raw form and a same-length-filler form both test `false`,
the stripped form tests `true`.

So masking replaces each span with filler of the same length, which hides the
link syntax from check 2 without moving anything toward the start of the line.
Check 3 reads the raw line as well, since wrapping the comparison in backticks
is the fix it prescribes and it must keep seeing them (R6).

### KD4 — Fence tracking is a property of a line, not a loop *(session-settled: user-directed)*

Check 4 tracks fences with a local `inFence` boolean inside its own
`forEach`. Copying that into checks 2 and 3 and the heading collector would be
four copies of the thing #37 asks to have once.

Instead, read each file once into a list of `{ number, raw, masked, fenced }`
records and cache it. Checks become filters over that list. This also removes
the current four-reads-per-file, which is incidental but real.

## Units

### U1 — Shared fence-aware line model

Add a `markdownLines(file)` reader returning one record per line:

- `number` — 1-based line number, so every check stops doing `i + 1`.
- `raw` — the line as written. Check 3 needs this.
- `masked` — the line with every inline code span replaced by same-length
  filler. Check 2 uses this.
- `fenced` — whether the line sits inside a fenced code block.

Fence detection keeps check 4's existing rule (a trimmed line starting with
```` ``` ```` toggles), because the corpus has 9059 backtick fences and zero
tilde or indented fences. The fence delimiter lines themselves count as fenced.

Cache results in a module-level `Map` keyed by path; the file set is fixed for
a run.

Rewire checks 2, 3 and 4 onto it: check 2 skips `fenced` records and reads
`masked`, check 3 skips `fenced` records and reads `raw`, check 4 keeps reading
`raw`. Check 4's flush-on-fence-delimiter behavior
must be preserved: a run of marker lines interrupted by a fence is two runs, not
one.

Skipping fenced lines creates a new way for a file to drop out of the checks
quietly: an unterminated fence makes everything after it look like one long
example. That is the same silent-skip defect the basename skip list already
shipped once, so add a fifth check that counts fence delimiters per file and
fails on an odd count.

Satisfies R1, R2, R3, R4, R5, R6, R15.

### U2 — Anchor verification

Add a `headingSlugs(file)` collector: walk `markdownLines(file)`, skip `fenced`
records, match ATX headings (`/^#{1,6}\s+(.*)$/`), and feed the text through a
fresh `GithubSlugger` per file so duplicate disambiguation matches GitHub's.

Widen check 2's regex to admit same-file anchors, and keep the fragment instead
of discarding it:

- No fragment — current behavior, file must exist.
- Fragment, no path — verify against this file's slugs.
- Fragment and path — verify the file exists, then, when it is a `.md` file,
  verify against that file's slugs.

A fragment on a non-Markdown target or a directory is not checkable; skip it
rather than guess. Report a dead anchor with the target and the fragment, and
count anchor-bearing links in the summary line.

Add `github-slugger` at `2.0.0` to `scripts/package.json` and regenerate
`scripts/package-lock.json` with `npm install`, so `npm ci` in CI resolves it.

Satisfies R7, R8, R9, R10.

### U3 — Prove it fails before trusting it passes

This repository's own standard, and #37's acceptance criteria encode it. Four
probes, each run against the built checker, each reverted afterwards:

1. A broken relative link **inside** a fence — must pass.
2. The same link **outside** a fence — must fail.
3. A link to a heading that does not exist — must fail.
4. A link to a heading that does exist — must pass.

Then revert the workaround in
`docs/solutions/best-practices/prove-a-check-fails-before-trusting-it-passes.md`:
the split `printf` becomes a plain `echo` with the probe link written literally,
and the closing paragraph that records the fence gap as "still true of the check
today" is rewritten to say it was fixed and how.

Satisfies R11, R12, R13.

### U4 — Say what the checks cover

Update the Automated Checks table in `process/documentation-standards.md` so the
link row names anchor verification, and note that examples inside fenced blocks
and inline code spans are not checked — which is the property that lets the
repository document its own defects.

Update the four-line check summary in the `scripts/check-docs.mjs` header
comment to match.

Satisfies R14.

## Known Technical Debt

| ID | Item |
|----|------|
| KTD1 | Fence detection is a toggle, not CommonMark. A fence opened with four backticks and closed with three would be mis-tracked. Zero instances in the corpus; revisit if one appears. |
| KTD2 | Inline code-span masking uses a single-backtick pattern. Double-backtick spans (`` `` ` `` ``) are not masked. Zero instances in the corpus. |
| KTD3 | Anchors on non-Markdown targets and directories are skipped rather than verified. There is nothing to verify them against without rendering. |
| KTD4 | Setext headings (`===` / `---` underlines) are not collected. The repository uses ATX exclusively. |
| KTD5 | Check 1 scans for ```` ```mermaid ```` blocks with its own loop rather than the shared model. It consumes fenced content instead of skipping it, so it needs block boundaries the line model does not carry. Not a second copy of the prose/example rule. |
| KTD6 | `archive/` and `docs/plans/` are still skipped as link *sources*, but a link from a checked file into them will now have its anchors read. That is intentional — the target's headings are real — but it means an anchor can break when a skipped file changes. |

## System-Wide Impact

- `.github/workflows/docs.yml` already triggers on `scripts/package.json`, so
  the new dependency is covered without a workflow change.
- Every existing anchor link in the repository becomes load-bearing on first
  run. Any that are already dead will surface as failures in this change's own
  PR — which is the point, and they get fixed here.
- The masking and fence rules mean documentation can now contain literal
  examples of every defect the checker catches. That is what made this change
  worth doing beyond the immediate bug.

## Verification

1. `node scripts/check-docs.mjs --verbose` reports a non-zero anchor count and
   passes on a clean tree.
2. The four U3 probes behave as specified.
3. An unterminated fence fails; closing it passes.
4. CI green on the PR, which exercises the checker on the full corpus including
   the reverted learning document.
