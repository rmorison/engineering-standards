---
title: Scrub Private References from the Public Corpus - Plan
type: fix
date: 2026-09-21
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
origin: https://github.com/rmorison/engineering-standards/issues/26
---

# Scrub Private References from the Public Corpus - Plan

## Goal Capsule

- Objective: a reader of this repository's documents learns nothing about its author's private repositories or local machine, and every cross-document citation they follow lands where it says it will.
- Means: redact the two identifying values in place, convert two prose heading citations into CI-verified anchors, and make one shape of leak a build failure (KD1, KD3, KTD4).
- Authority: the R-IDs govern. Where a document's current text conflicts with an R, the R wins and the text changes. The two Key Decisions below are judgement calls, not findings — the user overrides either by dropping the unit that implements it.
- Execution profile: documentation edits plus one bounded addition to `scripts/check-docs.mjs`. No repository settings changes, no git-history rewrite (KD2), no GitHub tracker changes.
- Stop conditions: stop and ask if a redaction would change what a historical record *decided* rather than what it *discloses*; if the working tree turns out to contain an identifying value this plan's inventory does not list; or if any credential, token, or key is found, which is a different and more urgent class of problem than this one.
- Finishes the work: `ce-work` or a human, shipped as one PR closing #26.

**Discipline this document observes, and the implementer must keep.** This plan will be committed to the same public repository the issue is about. It therefore cites *locations* and describes *pattern classes*, and never reproduces the two offending values. Two shorthand labels are used throughout:

- **PRIVATE-NAME** — the private downstream repository named in prose at `process/compound-engineering-integration.md`, under "Real-world deployment example".
- **PERSONAL-PATH** — the absolute home-directory path in the External References bullet of `docs/plans/2026-05-03-002-refactor-ai-architecture-6-layer-model-plan.md`, which discloses a local username and directory layout.

Both values are readable in the working tree at the locations this plan names. Neither is written here, in a commit message, in a PR body, or in any file this plan adds.

---

## Product Contract

### Summary

Redact PRIVATE-NAME and PERSONAL-PATH from all four documents that carry them, delete the two links into the private repository along with the line-range citations that point inside it, upgrade two prose heading citations in `process/compound-engineering-integration.md` to verified anchor links, and add one shape-based check to `scripts/check-docs.mjs` so an absolute home-directory path cannot reach `main` again.

The judgement call the issue asks for is made: the historical plan files are redacted in place rather than accepted as history (KD1), and git history is not rewritten (KD2). Both are recorded as decisions the user can reverse, not as defaults arrived at by omission.

### Problem Frame

This repository is public and its stated purpose is to be copied. Four tracked documents disclose the name of a private downstream repository, two of them link to a file inside it that returns 404 for every reader who is not its owner, and one discloses an absolute personal home-directory path — a local username and directory layout, leaked from a repository whose README invites strangers to clone it.

Two of the four mentions already argue for themselves: `process/compound-engineering-integration.md` and `docs/engineering/adr/0001-six-layer-ai-architecture.md` each state that the repository is named as deployment context only and that everything load-bearing is inlined, so a reader without access can apply the document end-to-end. That reasoning is sound and those two mentions are the least harmful. They still disclose a private repository's name to satisfy no reader need.

The dead links are worse than the name. A reader who follows `docs/plans/2026-05-03-001-feat-compound-engineering-integration-plan.md`'s "canonical working example" link gets a 404, and the line-range citations beside it point into a file they cannot open — the citation is unusable to everyone except the one person who does not need it.

PERSONAL-PATH is worse still, and the external review that produced this issue did not report it. It was found during verification.

### Key Decisions

- KD1. Redact the historical plan files in place rather than leaving the name as a historical artifact — a redaction alters what a record discloses, not what it decided. Governs R3, R4. Full reasoning and the reversal path: A1.
- KD2. Do not rewrite git history; the redaction is forward-looking only, and the plan says so out loud rather than leaving it unsaid. Governs R3. Reasoning: KTD6.
- KD3. Ship the shape-based half of a leak gate — the half whose pattern list cannot itself leak — and leave the value-based denylist to the public/open-source repository standard (ES-8). Governs R7, R9. Reasoning: KTD2.

### Requirements

Private-reference removal

- R1. No absolute personal filesystem path appears in any tracked file.
- R2. No link to a file inside a private repository appears in any tracked file, and no citation points into a file only its owner can open.
- R3. Wherever PRIVATE-NAME is named, the text refers to a private downstream project generically instead, in every tracked file.
- R4. Each redacted dated historical record — the two plan files and the ADR — carries a dated note stating that identifying details were removed for public consumption and that no decision, date, or rationale was altered. `process/compound-engineering-integration.md` is a living document and takes no such note.
- R5. The redaction to `docs/engineering/adr/0001-six-layer-ai-architecture.md` is recorded in that ADR's existing Amendment section, so the change to a frozen record is visible rather than silent.

Cross-reference durability

- R6. The two cross-references in `process/compound-engineering-integration.md` that cite a section of another document resolve by heading anchor, so `scripts/check-docs.mjs` fails when either target heading is renamed.

Recurrence prevention

- R7. An absolute home-directory path in any tracked Markdown file fails `scripts/check-docs.mjs`, including in the three directories the existing checks skip as link sources.
- R8. The new check is shown to fail on a planted defect before it is trusted, per `docs/solutions/best-practices/prove-a-check-fails-before-trusting-it-passes.md`.
- R9. No file this change adds or edits contains PRIVATE-NAME or PERSONAL-PATH — including the new check's own pattern.

Verification

- R10. A search of the working tree for both values returns nothing, run from values held in shell variables that are never written to a file.

### Scope Boundaries

- The two values remain in git history and in the GitHub pull-request diffs that introduced them. That is a decision (KD2), not an oversight, and R3 is satisfied by the working tree rather than by the object store.
- The owner's GitHub username is not redacted. It is the namespace of this public repository, appears in its clone URL, and discloses nothing that the repository's existence does not already disclose.
- The `status:` frontmatter fields on the two historical plan files are left alone. They predate the current plan contract and correcting them is not this issue's business.

#### Deferred to Follow-Up Work

- The configurable, value-based leak denylist, and the question of where a denylist lives so it does not itself become the leak. That is ES-8's gate; this issue is the one-time cleanup (KD3).
- Coverage of tracked non-Markdown files (`.json`, `.yml`, `.py`, `.gitignore`). The new check's universe deliberately matches `.github/workflows/docs.yml`'s `**/*.md` trigger, so widening it needs a workflow path-filter change as well (KTD1). The at-risk surface is specific and worth naming rather than leaving as "non-Markdown": `.claude/settings.json`, `templates/.claude/settings.json`, and the two hook scripts under `templates/.claude/hooks/`. Hook commands and permission rules are where an absolute home path arrives naturally — a hook is written against the author's machine and a permission rule is written against the path it must allow. None of those four files carries either value today; the exposure is that nothing stops one arriving. The blocker is two-sided: widening the script's universe is necessary but not sufficient, because `.github/workflows/docs.yml` triggers only on `**/*.md` and the checker's own files, so a pull request touching only `templates/.claude/settings.json` does not run the check at all today. Both sides have to move in the same change.
- The brittle line-number citations that remain elsewhere in the corpus — the two historical plan files cite this repository's own files by line range in roughly thirty places, and both `docs/solutions/best-practices/*.md` entries cite `scripts/check-docs.mjs` and `.github/workflows/docs.yml` by line. None of these point into a private file, so #26 does not reach them. They are a real drift surface and worth their own issue.

### Success Criteria

- A reader with no access to any private repository can read all four edited documents end to end and find nothing they cannot follow.
- Re-introducing PERSONAL-PATH's shape anywhere in the Markdown corpus turns CI red, and the person who proves that has seen it go red.

### Sources

- Issue #26, which deliberately cites locations rather than values; this plan keeps that discipline.
- `docs/solutions/best-practices/prove-a-check-fails-before-trusting-it-passes.md` — a check that fails open is worse than no check; plant the defect, and treat skip lists and path filters as the parts of a check that remove work silently. Both habits shape U6.
- `docs/solutions/best-practices/a-corrected-claim-is-not-a-verified-claim.md` — the replacement text is a claim too. The generic wording R3 substitutes must not assert anything about the private project that the original did not.
- `process/compound-engineering-integration.md`, "Version drift" and the paragraphs after it — this repository's own rule that a correction must be grepped for across every document that restates it, and that ADR bodies are frozen with dated amendments. Both apply directly (KTD3, U4).
- `scripts/check-docs.mjs` — `SKIP_PATHS` excludes `archive`, `docs/plans` and `scripts` as link sources. Those are exactly the directories holding 63 of the 66 occurrences (KTD1).

---

## Planning Contract

### Verified inventory

Counts are occurrences, not matching lines, taken from the working tree at `610944c`. Line numbers move as edits land, so U1 regenerates them rather than trusting this table.

| File | PRIVATE-NAME | PERSONAL-PATH | Private-repo links |
|------|--------------|---------------|--------------------|
| `docs/plans/2026-05-03-001-feat-compound-engineering-integration-plan.md` | 41 (30 lines) | 0 | 2 |
| `docs/plans/2026-05-03-002-refactor-ai-architecture-6-layer-model-plan.md` | 22 (15 lines) | 1 | 1 (inside PERSONAL-PATH) |
| `process/compound-engineering-integration.md` | 2 (1 line) | 0 | 0 |
| `docs/engineering/adr/0001-six-layer-ai-architecture.md` | 1 (1 line) | 0 | 0 |

Where the plan-file occurrences sit, by enclosing section, so the implementer can work section by section rather than line by line:

| File | Sections carrying occurrences |
|------|------------------------------|
| `...-001-...-plan.md` | Implementation Units (11), Requirements Trace (6), Risks & Dependencies (3), the abandonment banner above the H1 (2), Problem Frame (2), Sources & References (2), Overview (1), Relevant Code and Patterns (1), Institutional Learnings (1), Documentation / Operational Notes (1) |
| `...-002-...-plan.md` | Implementation Units (8), Requirements Trace (2), External References (1, and this is PERSONAL-PATH's line), Key Technical Decisions (1), Risks & Dependencies (1), Sources & References (1), Documentation / Operational Notes (1) |

Three corrections to the issue's claims, all found by checking the tree rather than the issue:

1. Part 2 is already fixed. `process/compound-engineering-integration.md` cited `process/issue-tracking.md` "lines 359–373" and `process/project-planning-standards.md` "line 86" at `efd17c4`, exactly as #26 reports. Commit `ac0cea9` replaced both with bold heading names plus quoted anchoring phrases. The citations are correct and no longer line-based. What remains is that they are *prose*, so CI cannot verify them — which U5 fixes and which is a smaller change than the issue anticipates.
2. The occurrence counts are higher than the issue's "29 and 15". Those figures count matching lines; counting occurrences gives 41 and 22.
3. The sweep found no location the issue missed, and no second personal path. Every tracked file was searched for the name in three spellings, for `/home/` and `/Users/` absolute paths, for `~/`, for Windows drive paths, and for `file://` URLs. Only the five cited locations matched.

### Key Technical Decisions

- KTD1. The new check walks tracked Markdown files directly rather than reusing the checker's `markdownFiles()` collector. `SKIP_PATHS` excludes `archive`, `docs/plans` and `scripts`, and `docs/plans` is where 63 of the 66 occurrences live — a leak check that inherited that skip list would report green on the exact files this issue is about. Its universe is every tracked `.md` file, which matches `.github/workflows/docs.yml`'s `**/*.md` trigger so the check's coverage and the workflow's coverage cannot drift apart; non-Markdown files are out, and Deferred says so.
- KTD2. The committed pattern is shape-based — an absolute home-directory path — not value-based. A value-based denylist would have to contain PRIVATE-NAME and PERSONAL-PATH to work, which makes the pattern list itself the leak it is guarding against. Shape-based patterns satisfy R7 and R9 together and need no storage outside the script. Instantiates KD3, governs R7, R9.
- KTD3. The ADR's body is edited and the edit is recorded as an entry in its existing Amendment section. `process/compound-engineering-integration.md` establishes that an ADR's history is frozen and corrections are appended, never edited in — but that rule protects the record's *claims* from retroactive improvement, and a redaction asserts nothing new. An amendment alone cannot solve this: the name would still be sitting in the body. So the body changes and the amendment records that it did, which satisfies both the rule's purpose and R1 through R5. Instantiates KD1 for the ADR, governs R5.
- KTD4. The two cross-references become anchor links (`./issue-tracking.md#epic-size-guidelines`, `./project-planning-standards.md#team-estimation`) rather than staying as quoted phrases. Since PR #41, `scripts/check-docs.mjs` verifies that a link's fragment names a real heading; it cannot verify a phrase quoted in prose. An anchor turns a citation that is merely correct today into one CI keeps correct. Both anchors were generated with the checker's own `github-slugger` against the current files and neither target has a duplicate slug. Governs R6.
- KTD5. The implementer regenerates every edit location with `git grep` at implementation time instead of working from this plan's line numbers. This plan cannot quote the values, the tree has moved since `efd17c4`, and the repository's own standard prefers path-plus-pattern references over line numbers. The Verification Contract gives the derivation commands. Governs R1, R2, R3.
- KTD6. History is not rewritten. Nothing disclosed is a credential; a repository name and a home-directory layout grant no access, and rotation is not a concept that applies to them. Against that, a rewrite changes every commit SHA in the repository, and this corpus cites SHAs — the issue itself is anchored to `efd17c4`, and `docs/solutions/best-practices/*.md` cite commits and PRs by number. It also invalidates every existing clone and does not retract what GitHub already serves from pull-request refs, so it would not even achieve the erasure it costs so much to attempt. The decision inverts if a credential is ever found: then a rewrite plus rotation is mandatory and this reasoning does not apply. Instantiates KD2, governs R3.

### Sign-Off Record

The four decisions this plan referred to the repository owner were settled on 2026-09-21, each as recommended. A1, A2, A5 and A6 below are therefore decisions, not open judgement calls, and their reversal paths stand as recorded should the owner revisit one.

- D1. **Redact the historical plan files in place**, rather than leaving the name as a historical artifact. Confirms A1 and KD1; implemented by U4.
- D2. **Do not rewrite git history.** Confirms A2 and KD2. Sensitivity was assessed before deciding: nothing disclosed is a credential, a token, a hostname, or third-party data, and GitHub already serves the values from the merged pull requests that introduced them, so a rewrite would not retract what is already public. Recorded so the next reader sees a decision rather than an omission.
- D3. **The shape-based leak check is in scope** as U6; the configurable gate stays with ES-8. Confirms A5.
- D4. **U5 is an upgrade, not the fix #26 describes**, since Part 2 landed in `ac0cea9`. It ships anyway, and the PR body says so plainly so that closing #26 does not read as an oversight. Confirms A6.

### Assumptions and open questions

A1, A2, A5 and A6 were referred to the owner and are settled above; the rest were resolved by judgement. Each names the unit that implements it, so reversing one means dropping or changing that unit and nothing else.

- A1. Settled by D1. Option 1 from the issue — redact the plan files in place — is the recommendation, implemented by U4. The issue frames this as a genuine fork and it is: `docs/plans/*` are dated records of decisions already made, and a redacted record is a slightly less faithful transcript of what its author wrote in May. Three things decide it anyway. A redaction alters no decision, date, requirement, or rationale, so the record's evidential value — the only reason to keep it unaltered — survives intact. The alternative leaves a known privacy defect standing in a repository whose README asks people to copy it, in the two files that carry 63 of the 66 occurrences. And a partial scrub makes the issue's own acceptance criterion unassertable: R10's sweep can never return clean, and ES-8's eventual value-based gate would have to ship with a permanent two-file allowlist, which is a gate with a hole in it by construction. **Reverse by dropping U4** — the other units stand on their own, and R3 then narrows to the two non-plan documents.
- A2. Settled by D2. Git history is not rewritten (KD2, KTD6). Recorded as a decision rather than left unsaid, which is what the issue asks for. **Reverse by filing a separate issue**; a history rewrite is not a unit inside this PR.
- A3. The replacement wording is "a private downstream project" (or a close variant that fits each sentence). It asserts nothing about the project that the original text did not, which `a-corrected-claim-is-not-a-verified-claim.md` warns is the easy mistake to make while fixing someone else's.
- A4. Redaction notes are dated 2026-09-21 and phrased as record annotations, matching the existing archive banners and ADR amendment in this repository rather than inventing a new form.
- A5. Settled by D3. The shape-based check (U6) is in scope. The issue assigns the leak gate to ES-8 and that boundary is confirmed for the *configurable* gate — but without U6 the acceptance criterion "a grep returns clean" is verified exactly once, by hand, and never again. U6 is roughly fifteen lines in a file that already has five checks. **Reverse by dropping U6** and carrying R7 through R9 to ES-8 entire.
- A6. Settled by D4. U5 is an upgrade, not the fix #26 describes, because Part 2 already landed in `ac0cea9`. It is included because the anchor check exists now and makes the difference between a correct citation and a maintained one. **Reverse by dropping U5**, closing #26's Part 2 as already-resolved in the PR body.
- A7. Non-Markdown tracked files are outside U6's coverage (KTD1). The alternative widens `.github/workflows/docs.yml`'s path filters, which changes what that workflow is for.
- A8. #26 is closed by this PR. No follow-up issue is filed for ES-8, which is assumed already tracked; the Deferred list names what belongs to it.

No question here blocks implementation.

### Sequencing

U1 first and alone: it is the most sensitive value, it is one line, and it should not wait behind 63 edits. U2 and U3 are independent of everything else. U4 is the bulk and depends on nothing, but runs after U3 so that the smaller, less contested edits are already settled if U4 is dropped. U5 is independent. U6 runs last, because R10's clean sweep is what it locks in — a check added before the corpus is clean fails on the corpus it was added to protect.

### System-Wide Impact

- `docs/plans/` is skipped as a link *source* by `scripts/check-docs.mjs`, but its headings are still read as anchor targets for links from checked files. U4's redaction notes are prose and add no headings, so no anchor moves. The notes do shift line numbers inside both plan files; nothing in the corpus cites those files by line.
- U5 makes two headings in `process/issue-tracking.md` and `process/project-planning-standards.md` load-bearing for CI. Renaming "Epic Size Guidelines" or "Team Estimation" will fail the build from then on. That is the intended effect and worth stating where those documents' maintainers will see it.
- U6 is the first check in `scripts/check-docs.mjs` that looks at content rather than rendering, and the first with a file universe of its own. The header comment enumerating the checks and the Automated Checks table in `process/documentation-standards.md` both become wrong the moment it lands, and are updated in the same unit.

---

## Implementation Units

### U1. Remove the personal filesystem path

Goal: R1 satisfied — no absolute home-directory path anywhere in the tree.

Requirements: R1, R2 (the path contains a private-repo path segment), R10.

Dependencies: none.

Files: `docs/plans/2026-05-03-002-refactor-ai-architecture-6-layer-model-plan.md`.

Approach:

1. Locate the External References bullet under `## Context & Research` that names a working example by absolute local path. The Verification Contract's shape grep finds it without the value being typed.
2. Replace the path with nothing — not with a relative path, not with a repository URL. The bullet's remaining sentences already say what the reference contributed and that it is not a content reference; they stand on their own once the locator is gone.
3. Redact PRIVATE-NAME in the same bullet under U4's wording, or leave the bullet to U4 if U4 is being dropped — in which case this unit still removes the path and the bullet keeps the bare name.

Patterns to follow: the parallel bullet in `docs/engineering/adr/0001-six-layer-ai-architecture.md`'s References section, which describes the same deployment without a path.

Test scenarios:

- `git grep -nIE '/(home|Users)/[A-Za-z0-9._-]+/'` over the whole tree returns nothing.
- The edited bullet still reads as a complete sentence and still says what the deployment contributed.

Verification: the shape grep is empty and the bullet reads cleanly.

### U2. Remove the dead private links and the citations into them

Goal: R2 satisfied — no reader is sent to a 404, and no citation points inside a file they cannot open.

Requirements: R2.

Dependencies: none.

Files: `docs/plans/2026-05-03-001-feat-compound-engineering-integration-plan.md`.

Approach:

1. In the Problem Frame paragraph that names the private project and links its configuration file, drop the link, keeping the prose. The sentence's point — that the project absorbed the gaps locally during real use — does not need the URL, and the paragraph that follows already explains that the load-bearing content is inlined precisely because a public reader cannot follow it.
2. In the Relevant Code and Patterns bullet, drop the link and the four line-range citations into the private file. Keep the named sections it lists — Documentation Paths table, Review Gate paragraph, Ticket Policy, branch-naming carve-out — since those name what was lifted, which is the useful part; the line ranges locate it in a file no reader can open.
3. Do not replace either link with a note explaining that a link was removed. U4's redaction note covers the file as a whole.

Patterns to follow: the "inline the load-bearing content rather than pointing readers at a 404" argument already made two sentences later in the same file.

Test scenarios:

- `git grep -nIE 'github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+' -- '*.md'` lists only public targets; the private-repo entries are gone.
- No "lines N–M" citation remains in the file that points outside this repository.

Verification: both greps are clean and each edited sentence still parses.

### U3. Redact the name in the process document and the ADR

Goal: R3 satisfied for the two documents that name the project as deployment context.

Requirements: R3, R4, R5.

Dependencies: none.

Files: `process/compound-engineering-integration.md`, `docs/engineering/adr/0001-six-layer-ai-architecture.md`.

Approach:

1. In `process/compound-engineering-integration.md`, rewrite the "Real-world deployment example" section so the project is described generically. Keep both of the section's existing claims: that the wording of the layer-realization mapping, the Ticket Policy block and the AI-review discipline framing came from iterating against a real workload, and that everything load-bearing is inlined so a public reader can apply the document end to end. The second claim is stronger once the name is gone, not weaker. Retitle the section only if the generic phrasing makes the current heading read oddly; if it is retitled, check for links to its anchor first, since CI verifies them.
2. In `docs/engineering/adr/0001-six-layer-ai-architecture.md`, redact the "Real-world deployment example" bullet in the References list the same way.
3. Add an entry to that ADR's existing Amendment section, dated 2026-09-21, recording that an identifying detail was removed from the References list for public consumption and that no decision, claim, or date in the record changed (KTD3). Follow the form of the amendment already there — it states what changed and why, and leaves the body above it as written except for the redaction itself.

Patterns to follow: the existing `## Amendment — 2026-09-20` entry in the same ADR, and the "ADRs are a special case, not an exemption" paragraph in `process/compound-engineering-integration.md`.

Test scenarios:

- Neither file matches the name in any spelling.
- Both documents still state that the deployment context was real and that nothing load-bearing depends on access to it.
- `node scripts/check-docs.mjs` passes, which catches a retitled heading that some other document links to.

Verification: the name grep is clean for both files, the ADR carries a dated redaction entry, and the doc checks pass.

### U4. Redact the name across the two historical plan files

Goal: R3 satisfied for the remaining 63 occurrences, with the record's shape preserved.

Requirements: R3, R4.

Dependencies: U1, U2 (both edit lines inside these files; doing them first avoids a redaction pass re-touching the same sentences).

Files: `docs/plans/2026-05-03-001-feat-compound-engineering-integration-plan.md`, `docs/plans/2026-05-03-002-refactor-ai-architecture-6-layer-model-plan.md`.

Approach:

1. Work section by section using the inventory table above, regenerating exact positions with `git grep` (KTD5). The heaviest clusters are Implementation Units in both files and Requirements Trace in the 001 plan.
2. Replace each occurrence with a generic description. The right phrasing varies with position — a requirement trace bullet reads differently from a code-fence path or a possessive ("its absorbed wording"). Keep each sentence grammatical rather than applying one substitution mechanically.
3. Watch the two occurrences in the 001 plan's abandonment banner, which sit above the H1. The banner narrates that a privacy concern about this very project was surfaced in review round 1 and resolved by inlining. That narration must survive the redaction — it is the record of a decision, and it is also the direct ancestor of this issue.
4. Add a dated redaction note to each file, immediately below the frontmatter and above the existing banner or H1: identifying details were removed on 2026-09-21 for public consumption; no decision, date, requirement, or rationale was altered; git history retains the original text. Keep it to two or three sentences and do not add headings (anchors in these files are read by the checker even though the files are skipped as link sources).
5. Do not touch the `status:`, `abandoned:`, `completed:` or `prior_plan:` frontmatter fields.

Patterns to follow: the archive banners in `archive/` and the ADR amendment in U3 — both annotate a record without rewriting it.

Test scenarios:

- Neither file matches the name in any spelling, and the total occurrence count across the repository is zero.
- The 001 plan's abandonment banner still records that a privacy concern was raised and how it was resolved.
- Reading each file's Requirements Trace and Implementation Units sections end to end surfaces no sentence left ungrammatical by the substitution.
- Both files still parse as Markdown: `node scripts/check-docs.mjs` passes, which exercises the fence and heading collectors over these files as anchor targets.

Verification: the name grep is clean repository-wide, both files carry a dated redaction note, and a read-through finds no broken sentence.

### U5. Make the two cross-references verifiable

Goal: R6 satisfied — CI fails when either cited heading is renamed.

Requirements: R6.

Dependencies: none.

Files: `process/compound-engineering-integration.md`.

Approach:

1. Under "Issue-tracking modes", the sentence citing the standards' solo carve-outs already links `process/issue-tracking.md` and already names the section in bold. Append the fragment to the existing href so it becomes `./issue-tracking.md#epic-size-guidelines`.
2. Under "Solo-scale adaptations", the Estimation bullet already links `process/project-planning-standards.md` and names the section in bold. Append `#team-estimation`.
3. Keep the quoted anchoring phrases in the first citation. They survive a heading rename that the anchor check would catch anyway, and they tell the reader what they are looking for once they arrive.
4. Both anchors were generated with `github-slugger` against the current target files and verified against every heading in each: `### Epic Size Guidelines` at `process/issue-tracking.md` and `### Team Estimation` at `process/project-planning-standards.md`. Neither file has a duplicate slug, so neither anchor carries a disambiguation suffix.

Patterns to follow: `ai/CLAUDE.md`, which already cites `process/issue-tracking.md#label-strategy` and `process/git-branching-strategy.md#commit-messages` this way; and the same file's own `#2-artifact-location-mapping` self-link.

Test scenarios:

- `node scripts/check-docs.mjs --verbose` reports a verified-anchor count two higher than before and passes.
- Renaming `### Epic Size Guidelines` in `process/issue-tracking.md` makes the checker report a dead anchor at the citing line; restoring it clears the failure. Repeat for `### Team Estimation`.

Verification: the anchor count rises by two, the checker passes, and the rename probe fails and recovers in both directions.

### U6. Make a leaked home-directory path a build failure

Goal: R7 through R9 satisfied — the most sensitive shape of leak cannot reach `main` again, and the guard cannot itself leak.

Requirements: R7, R8, R9.

Dependencies: U1 (the check fails on the current tree until U1 lands).

Files: `scripts/check-docs.mjs`, `process/documentation-standards.md`.

Execution note: prove it fails before trusting that it passes. The probe that matters is planted inside `docs/plans/`, because that directory is on `SKIP_PATHS` and a check that silently inherited the skip list would report green on it.

Approach:

1. Add a sixth check reporting any absolute home-directory path — a `/home/<name>/` or `/Users/<name>/` prefix — in a tracked Markdown file. Report file, line, and the check name, using the existing `fail()` collector so it joins the same failure summary.
2. Give it a file list that does not inherit `SKIP_PATHS` (KTD1). Either ask git for tracked `.md` files, or parameterize the existing recursive walker so the skip list can be turned off for this one check — the second is smaller and adds no dependency on git being present at check time. Whichever is chosen, an empty file list must fail loudly rather than pass: a leak check that silently covers zero files is the exact defect `prove-a-check-fails-before-trusting-it-passes.md` documents.
3. Decide deliberately whether the check reads fenced lines. It should: an example of a leaked path in documentation is still a leaked path, which is the opposite of the reasoning that makes checks 2 through 4 fence-aware. Record that reasoning next to the check, since it inverts the file's established convention and the next reader will otherwise assume it is a bug.
4. Keep the pattern shape-based (KTD2). Do not add PRIVATE-NAME, PERSONAL-PATH, or any derived fragment of either to the script, to `package.json`, or to any new file.
5. Update the check enumeration in the `scripts/check-docs.mjs` header comment and the Automated Checks table in `process/documentation-standards.md` § Automated Checks, adding a row naming what this check catches and why a public repository needs it. Note there that the check reads fenced blocks, unlike the link and list checks, since that section already tells readers the opposite about the others.

Patterns to follow: `checkFencesClosed()` for a check that needs a file universe different from the others; the `SKIP_PATHS` comment block for recording why a scoping decision was made the way it was.

Test scenarios:

- Plant a file under `docs/plans/` containing an absolute home-directory path; the check fails and names that file. Remove it; the check passes. This is the probe that proves the skip list was not inherited.
- Plant the same path inside a fenced code block in a checked directory; the check still fails, confirming the deliberate fence behavior.
- Plant it in `archive/` and in `scripts/`; the check fails in both, covering the other two skipped paths.
- A relative path containing the word `home` (for example a link to a `home/` subdirectory) does not fail, so the pattern is anchored to an absolute prefix.
- The check does not fire on the documents that describe it — this plan, `process/documentation-standards.md`'s new row, and the script's own header comment all discuss the pattern, and a check that flags its own documentation is unusable. Confirm by running the finished check over the clean tree and getting zero findings.
- Run the checker over every tracked Markdown file before and after this unit and diff the per-file verdicts. The only change should be the planted probes — per `a-corrected-claim-is-not-a-verified-claim.md`, the corpus finds what the probes were not aimed at.
- `git grep -nIF` for either value over `scripts/` and `process/documentation-standards.md` returns nothing, proving the guard did not become the leak.

Verification: the probes fail and recover as specified, the corpus diff shows no unexpected verdict change, the header comment and the standards table describe six checks, and the full checker passes on the clean tree.

---

## Verification Contract

Commands the implementer runs. The two value-specific searches take their needle from the pre-change tree into a shell variable, so neither value is ever typed into a file, a commit message, or a PR body (R9, R10).

| Gate | What proves it | Applies to |
|------|----------------|------------|
| Doc checks pass | `node scripts/check-docs.mjs --verbose` from the repository root, after `npm ci --no-audit --no-fund` in `scripts/` | all units |
| No absolute personal paths | The shape sweep below returns nothing | U1, U6 |
| No private-repo links | The URL sweep below lists only public targets, confirmed by eye | U2 |
| No private-repo name | The needle sweep below returns nothing, with a non-empty needle | U3, U4 |
| Anchors verified | The `--verbose` summary's verified-anchor count rises from 34 to 36 | U5 |
| Anchor drift caught | Rename each cited heading, confirm the checker reports a dead anchor, restore it | U5 |
| Leak check fails on a plant | Plant an absolute home path under `docs/plans/`, `archive/` and `scripts/`; confirm a failure in each; remove them | U6 |
| Corpus diff | Run the checker over every tracked Markdown file before and after U6 and diff the per-file verdicts | U6 |
| CI green | The Documentation checks workflow passes on the PR | all units |

The three sweeps, run from the repository root:

```bash
# Shape sweep — any absolute home-directory path, in any tracked file (R1).
git grep -nIE '/(home|Users)/[A-Za-z0-9._-]+/'

# URL sweep — every GitHub target the Markdown corpus links to, deduplicated (R2).
git grep -nohIE 'github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+' -- '*.md' | sort -u

# Needle sweep — the private repository's name, lifted from the pre-change blob so
# it is never typed into a file, a branch name, a commit message or a PR (R3, R9).
NEEDLE=$(git show 610944c:docs/engineering/adr/0001-six-layer-ai-architecture.md \
  | sed -n 's/.*example:\** *`\([a-z0-9-]*\)`.*/\1/p' | head -1)
test -n "$NEEDLE" || { echo 'needle capture failed — the sweep below proves nothing'; }
git grep -inIF -- "$NEEDLE"
```

The `test -n` guard is not decoration. If the `sed` extracts nothing, `git grep -F ""` matches every line rather than none, so the failure is loud — but only if someone reads the output instead of the exit code. Confirm the needle is the expected value before trusting a clean sweep. This is `prove-a-check-fails-before-trusting-it-passes.md` habit 2 applied to the verification of this very change.

---

## Definition of Done

| # | Criterion |
|---|-----------|
| 1 | Every R1–R10 requirement holds against the working tree, each proved by its Verification Contract gate rather than by inspection. |
| 2 | No file added or changed by this PR contains either offending value, and neither appears in the new check's pattern, the branch name, the commit messages, the PR title, or the PR body. |
| 3 | The two redacted historical plan files and the ADR each carry a dated note recording the redaction and stating that no decision or rationale changed. |
| 4 | The new check has been shown to fail on a planted defect in each of the three skipped directories, and to pass once the plants are removed. |
| 5 | `scripts/check-docs.mjs`'s header comment and the Automated Checks table in `process/documentation-standards.md` both describe the check set as it now stands. |
| 6 | The probe files, the corpus-diff scratch output, and any other experimental artifact are removed from the tree. |
| 7 | The PR body records the two decisions the user may want to revisit — redacting the historical plan files rather than accepting them as history, and not rewriting git history — so reversing either is a conversation rather than an archaeology exercise. |
| 8 | The PR notes that #26's Part 2 was already resolved in `ac0cea9` and that U5 upgrades the citations rather than fixing them, so the issue can be closed without the discrepancy looking like an oversight. |
