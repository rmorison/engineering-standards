---
title: Hold a stated risk with a fixture that fails when the risk is gone
date: 2026-09-27
category: best-practices
module: check-template-kit
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - "A check deliberately keeps a known-dangerous case and a doc states that risk"
  - "Writing a fixture list for a permission or allow-list check that has intentional exceptions"
  - "A doc claims a specific rule is the one exception, or that no rule permits some dangerous input"
  - "Narrowing, removing, or rewriting a rule that a doc's accepted-risk claim depends on"
  - "Deciding whether a fixture should check for an exact rule string or for the behavior it grants"
resolution_type: tooling_addition
related_components:
  - development_workflow
  - documentation
tags: [accepted-risk, fixtures, allow-list, documentation-drift, permissions, ci, semantic-check]
---

# Hold a stated risk with a fixture that fails when the risk is gone

## Context

Issue #47 found that the Claude Code starter kit's `templates/.claude/settings.json` pre-approved `Bash(uv:*)`, which matched `uv run` followed by anything. [PR #56](https://github.com/rmorison/engineering-standards/pull/56) replaced it with named uv entries. The same PR exposed a second problem, and it is the one this learning is about.

`scripts/check-template-kit.mjs` held the kit's allow list to three fixture lists. `ALLOW_POSITIVE` requires every entry to match exactly one routine command it exists for. `ALLOW_NEGATIVE` lists commands no entry may match. `DENY_POSITIVE` requires each deny entry to match the command it exists for. All three are matched with `bashRuleMatches`, the script's own reimplementation of Claude Code's prefix rules.

The kit also keeps some entries on purpose although they approve a dangerous form. `Bash(make:*)` approves any target, including one defined on the command line: `make --eval='x: ; @cat .env' x` prints the file under GNU Make 4.3. `Bash(git grep:*)` approves `git grep -O<cmd>`, and `Bash(git fetch:*)` and `Bash(git pull:*)` approve `--upload-pack=<cmd>`, which runs `<cmd>` through the shell for a local-path remote. `templates/README.md` states these risks in the section "Why `Bash(make:*)` stays" and in the paragraph that opens "Three git entries run arbitrary commands through a flag", and the Limit bullet in the Secrets section of `code/python-standards.md` repeats them.

None of those statements was held by a fixture. `ALLOW_NEGATIVE` cannot hold them, because the entries stay on purpose and the row would fail on every run. `ALLOW_POSITIVE` proves only that `Bash(make:*)` matches `make test`, which says nothing about `make --eval`. So if an entry were narrowed or removed, the README would go on describing a risk that no longer existed, and nothing would fail. The drift ran the other way too. Before #56 the README said "`rm` appears in no allow entry, so a variant the deny rule misses still reaches a human prompt", which was false for as long as `Bash(uv:*)` approved `uv run rm -rf build`. It also said `Bash(git grep:*)` was the one entry with a known exception, which stopped being true when an `@claude` review on #56 found `--upload-pack`. Both sentences were confident, specific, and wrong, and no check could see them.

## Guidance

**When a check deliberately tolerates a dangerous case and the documentation states that risk, add a fixture asserting the dangerous case is still true.** It is the dual of a negative fixture. A negative row says "this must not be permitted". An accepted-risk row says "this is permitted, we know, and the docs say so". It fails when the fact changes, and its failure message names the document to update.

PR #56 added `ALLOW_ACCEPTED_RISK` to `scripts/check-template-kit.mjs` as `[entry, command]` pairs:

```js
const ALLOW_ACCEPTED_RISK = [
  ['Bash(make:*)', "make --eval='x: ; @cat .env' x"],
  ['Bash(git grep:*)', "git grep -O'sh -c id' needle"],
  ['Bash(git fetch:*)', "git fetch --upload-pack='id; git-upload-pack' ."],
  ['Bash(git pull:*)', "git pull --upload-pack='id; git-upload-pack' ."],
];
```

Two rules make the fixture hold the claim rather than an identifier.

1. **Assert the fact semantically, not by name.** The first version checked `allow.includes(entry)` and then `bashRuleMatches(entry, command)`. The `@claude` review on #56 pointed out that rewriting `Bash(make:*)` as the equivalent `Bash(make *)` would fail that row and tell the maintainer to update the README, although the risk was unchanged. The loop in `checkKitPermissions` now asks whether any allow entry still approves the command: `allow.some((e) => bashRuleMatches(e, command))`. The dangerous fact is "this command is auto-approved", so that is what the row checks. The entry column records which entry carries the risk today and appears in the failure message. It is documentation, not a condition.
2. **Make the failure message route to the prose.** A failing row says `no allow entry approves <command> any more, though ALLOW_ACCEPTED_RISK says the kit accepts that risk through <entry>`, then tells the maintainer to update `templates/README.md`, which states it, and remove the row. Fixing the risk then forces the doc update in the same change. The README's own description of the check says so: the statements of those risks cannot outlive the entries they describe.

A row leaves the list when its risk is removed, and it usually moves rather than disappears. Issue #57 will narrow the git entries. At that point the git rows leave `ALLOW_ACCEPTED_RISK`, and the same commands belong in `ALLOW_NEGATIVE`, because the command that was a tolerated risk is now one that must reach a human.

This does not replace proving the check can fail. The rows were verified on scratch copies of the kit, in the way [`prove-a-check-fails-before-trusting-it-passes.md`](./prove-a-check-fails-before-trusting-it-passes.md) describes, and the Examples section below records the results.

## Why This Matters

A written risk is a claim about the present. Most claims in a repository decay in one direction: the code changes and the prose stays. A negative fixture catches the case where something dangerous starts being permitted. Nothing catches the case where something dangerous stops being permitted, or where the prose describing tolerated dangers is incomplete, unless a fixture holds the tolerated fact explicitly.

Both failure directions cost something. A stale risk statement that overstates is noise, and readers learn to skim the risk section, which is where the next real risk will be written. A risk section that understates is worse. The README carried one from #44 until the review of #56 caught it: "`git grep` is the one exception" invited readers to treat every other entry as audited. An accepted-risk list also turns the documentation's scope into something enumerable. Adding a row means naming a risk, so a reviewer can compare the list against the prose and ask which statement has no row.

Matching by identifier instead of by behavior recreates the problem the fixture exists to solve. A row keyed on the exact string `Bash(make:*)` fails on a harmless rewrite and gives the wrong advice, which teaches maintainers to delete failing rows without reading them.

## When to Apply

- A check or policy that allows something known to be dangerous, where the docs explain why it stays: allow lists, lint suppressions, disabled security rules, ignored CVEs.
- A "known limitation", "not supported" or "we accept X" statement in documentation that a test or script could observe.
- A risk statement repeated in more than one document. In this repository the make and git risks appear in both `templates/README.md` and the Limit bullet in `code/python-standards.md`, and the failure message names only the README, so whoever fixes a row has to update the second place by hand.
- Any exception list where a later fix should force a docs change, not merely permit one.
- Before narrowing a tolerated entry: move its row to the negative list in the same change, so the new guarantee is held too.

## Examples

### The rows proved on scratch copies

Each edit was made to a scratch copy of the kit, and `node scripts/check-template-kit.mjs` was run against it:

```
delete Bash(make:*)                 -> the make --eval row fails
narrow git grep / fetch / pull      -> each corresponding row fails
rewrite Bash(make:*) as Bash(make *) -> passes; the risk is unchanged
```

The third line is the test of rule 1. The exact-string version of the check would have failed it.

### A known limitation outside permissions

A data importer's README says: "Rows whose first cell begins with a UTF-8 byte-order mark are skipped; strip the BOM before import." That is a tolerated defect stated in prose. Hold it with a test that feeds the importer such a row and asserts it is still skipped, with a failure message along the lines of "the importer now accepts BOM-prefixed rows; remove the limitation from the README's Known limitations section and turn this test into a regression test that the row is imported." Assert the observable behavior (the row is absent from the output), not the name of the function that drops it, so moving the parsing into another module does not trip the test. When someone fixes the BOM handling, the test fails, the README changes in the same PR, and the test is inverted rather than deleted.
