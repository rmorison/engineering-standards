---
title: A corrected claim is not a verified claim
date: 2026-09-20
category: best-practices
module: process-standards
problem_type: best_practice
component: documentation
severity: medium
applies_when:
  - Replacing a factual claim that turned out to be wrong
  - Writing a justification into a standard that others will follow
  - Citing a convention by name rather than by source
  - Reviewing your own correction to someone else's error
resolution_type: documentation_update
related_components:
  - development_workflow
tags: [documentation, claims, justification, review, standards, verification]
---

# A corrected claim is not a verified claim

## Context

Issue #25 proposed raising the commit subject limit from 50 to 72 characters, justified as "the widely used convention". Research refuted that: in the 50/72 pair the 72 is the body wrap width, and the string `72` appears nowhere in git's own `Documentation/git-commit.adoc`. The number survived on better evidence; the reasoning did not.

The replacement text then said git's 50 is "a soft limit for a bare summary with no prefix". Git does not say that either. `git-commit.adoc:549` reads "a single short (no more than 50 characters) line summarizing the change", with no carve-out for a `type:` prefix. The qualifier was invented, in the same sentence that had just corrected an invented claim, by the same author, minutes after doing the research that made the correction possible.

An adversarial reviewer caught it. Nothing else would have: the sentence reads as though it were sourced, because three of its four clauses were.

## Guidance

**Verify a correction the way you verified the error.** Finding that a claim is false does not make your replacement true, and the research that exposed the first error does not transfer its authority to the second. Re-check the replacement against the same primary source, as a separate act.

The failure mode is specific and worth naming: having just read the sources, you feel sourced. A correction written in that state carries the confidence of the research without having been through it. The more thorough the debunking, the stronger the feeling, and the less likely you are to pause on the sentence you wrote to replace it.

Two habits follow.

**Quote or drop.** If you cannot quote the source for a clause, do not write the clause. "Git's 50 is for a bare summary with no prefix" is a quotable claim or it is not one; it was not. Owning a departure is always available and always honest: "git suggests 50; this standard relaxes that to 72 to leave room for the prefix" needs no source beyond the one it cites, because it claims nothing about what git meant.

**Count the clauses.** A justification with four clauses needs four checks, not one. Partial sourcing is what makes an invented qualifier invisible, because the verified clauses around it supply the credibility.

## Why This Matters

A standard is followed without being re-derived. That is the point of writing one, and it is why a false justification inside it is worse than a false justification in a conversation: the number gets applied, the reasoning gets quoted, and the next person to question it finds a citation that does not say what it is cited for. At that point the decision reopens, which is exactly what committing it to a standard was supposed to prevent.

This repository already knew that claims drift and that corrections do not propagate. What it did not have written down is that the correction is itself a claim, drafted at the moment of least scepticism.

## When to Apply

- Writing any "because X says Y" into `process/` or `code/`, where adopters follow the rule without checking it
- Replacing a claim a review just refuted, which is the highest-risk moment
- Any justification naming a tool's default, a specification, or a convention by name; all three are checkable in seconds and are wrong often enough to be worth the seconds
- Reviewing a diff that corrects a factual error, where the correction deserves the same scrutiny the original error received

## Examples

The claim as it was corrected, and then corrected again:

```
#25 as filed:   72 is "the widely used convention"
   REFUTED:     72 is the body wrap in 50/72; git-commit.adoc never says 72

first fix:      git's 50 is "a soft limit for a bare summary with no prefix"
   REFUTED:     git-commit.adoc:549 states 50 for the summary line, no carve-out

second fix:     git suggests 50 for the whole summary line; this standard
                relaxes that to 72 to leave room for the type prefix
   STANDS:      claims nothing about git beyond what git says
```

The three clauses that were sound the whole time, and stayed:

- `gitlint`'s `TitleMaxLength` default is 72, in `gitlint-core/gitlint/rules.py`
- The Linux kernel's `Documentation/process/submitting-patches.rst` requires a summary of 70 to 75 characters
- In the 50/72 convention, 72 is the body wrap width

Their soundness is what made the fourth clause hard to see.

Writing this document hit the repository's own checker in passing. The comparison above first used `->` as its arrow, and check 3 in `scripts/check-docs.mjs` reads every line of every file, fenced code included, flagging a line that starts with `-` followed by `>` as a list item opening a blockquote. Check 2 has the same fence-blindness, which is [#37](https://github.com/rmorison/engineering-standards/issues/37); check 3 belongs to the same fix.

## Related

- `docs/solutions/best-practices/prove-a-check-fails-before-trusting-it-passes.md` covers the same shape one layer down: a tool reporting success that does not mean what it appears to mean. This entry is about a person doing it.
- [`process/compound-engineering-integration.md`](../../../process/compound-engineering-integration.md) carries the drift note on corrections that fail to propagate. Propagating a correction assumes the correction is right.
