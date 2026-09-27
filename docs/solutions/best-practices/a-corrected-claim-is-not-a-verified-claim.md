---
title: A corrected claim is not a verified claim
date: 2026-09-20
last_updated: 2026-09-27
category: best-practices
module: process-standards
problem_type: best_practice
component: documentation
severity: medium
applies_when:
  - Replacing a factual claim, a rule, a count, or code that turned out to be wrong
  - Writing a justification into a standard, or citing a convention by name rather than by source
  - Trusting your own correction because the research or reproduction that exposed the error was thorough
  - Pushing fixes for review findings before calling a change merge-ready
  - Putting text a research subagent reported into quotation marks or a blockquote
resolution_type: documentation_update
related_components:
  - development_workflow
tags: [documentation, claims, code-review, review, standards, verification, quotation, subagents]
---

# A corrected claim is not a verified claim

## Context

Issue #25 proposed raising the commit subject limit from 50 to 72 characters, justified as "the widely used convention". Research refuted that: in the 50/72 pair the 72 is the body wrap width, and the string `72` appears nowhere in git's own `Documentation/git-commit.adoc`. The number survived on better evidence; the reasoning did not.

The replacement text then said git's 50 is "a soft limit for a bare summary with no prefix". Git does not say that either. `git-commit.adoc:549` reads "a single short (no more than 50 characters) line summarizing the change", with no carve-out for a `type:` prefix. The qualifier was invented, in the same sentence that had just corrected an invented claim, by the same author, minutes after doing the research that made the correction possible.

An adversarial reviewer caught it. Nothing else would have: the sentence reads as though it were sourced, because three of its four clauses were.

## Guidance

**Verify a correction the way you verified the error.** Finding that a claim is false does not make your replacement true, and the research that exposed the first error does not transfer its authority to the second. Re-check the replacement against the same primary source, as a separate act.

None of that is specific to prose. The corrected artifact can be a sentence, a rule, or a
number, and the mechanism does not change: whatever replaces the error is drafted by someone
who has just finished proving the error, and inherits the standing of that proof without
having been through it. The Examples below show all three, and a fourth: code written to fix review findings.

The failure mode is specific and worth naming: having just read the sources, you feel sourced. A correction written in that state carries the confidence of the research without having been through it. The more thorough the debunking, the stronger the feeling, and the less likely you are to pause on the sentence you wrote to replace it.

Five habits follow.

**Quote or drop.** If you cannot quote the source for a clause, do not write the clause. "Git's 50 is for a bare summary with no prefix" is a quotable claim or it is not one; it was not. Owning a departure is always available and always honest: "git suggests 50; this standard relaxes that to 72 to leave room for the prefix" needs no source beyond the one it cites, because it claims nothing about what git meant.

**Count the clauses.** A justification with four clauses needs four checks, not one. Partial sourcing is what makes an invented qualifier invisible, because the verified clauses around it supply the credibility.

**A quote you did not read at the source is a paraphrase.** When research is delegated, the words that come back have passed through a summariser, even when the delegate was told to quote verbatim. Its report is evidence about what the source says, not the source. Before text goes between quotation marks or into a blockquote, open the page and copy it from there, anchor included. If you cannot open it, drop the quotation marks and attribute the text as the delegate's summary. A delegate's report carries the authority of its research the way a correction carries the authority of the debunking, and the same scepticism applies. A delegated summary drops qualifiers and merges sentences, and the dropped part is often the one that constrains you.

**Review the fix delta on its own.** Code written to close review findings is a correction too. It is written at the moment of most confidence: the bug was just reproduced, and the new fixture just passed. The author writes it, and usually nobody else reads it. A re-review of the whole change spends its attention on the old findings again. Ask for a separate review of only the commits that made the fixes. Tell the reviewer the earlier findings are known and out of scope, and name the new logic's risky surfaces: new parsing, odd inputs, rules that now meet each other.

**Reproduce a finding before you fix it.** A reviewer that could not run the tool labels some findings Plausible. That is a claim about the tool, not a result from it. Run the real tool on a fixture first. The finding is confirmed, sharpened, or fails to reproduce, and the fix should record which.

## Why This Matters

A standard is followed without being re-derived. That is the point of writing one, and it is why a false justification inside it is worse than a false justification in a conversation: the number gets applied, the reasoning gets quoted, and the next person to question it finds a citation that does not say what it is cited for. At that point the decision reopens, which is exactly what committing it to a standard was supposed to prevent.

This repository already knew that claims drift and that corrections do not propagate. What it did not have written down is that the correction is itself a claim, drafted at the moment of least scepticism.

Code has the same gap. A fix is accepted because the finding it answers was real, and the fix itself is often the least-reviewed code in the change.

## When to Apply

- Writing any "because X says Y" into `process/` or `code/`, where adopters follow the rule without checking it
- Replacing a claim a review just refuted, which is the highest-risk moment
- Any justification naming a tool's default, a specification, or a convention by name; all three are checkable in seconds and are wrong often enough to be worth the seconds
- Reviewing a diff that corrects a factual error, where the correction deserves the same scrutiny the original error received
- Replacing a rule that classifies or filters input, where "it handles the case that prompted it" is the weakest evidence available and the corpus is the strong one
- Recomputing a count or an identity offered as proof a change was sound, where a sum that balances proves nothing unless it is sensitive to what could have gone wrong
- Pushing commits that fix review findings, before calling the change merge-ready
- Acting on a review finding marked Plausible, or from a reviewer that could not run the tool
- Adding a default or a precedence rule to a standard that already has rules; each sentence can hold alone while the combination asks for something nobody can do

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
- The Linux kernel's `Documentation/process/submitting-patches.rst` caps a patch summary at "no more than 70-75 characters"
- In the 50/72 convention, 72 is the body wrap width

Their soundness is what made the fourth clause hard to see.

The same failure twice more in [PR #41](https://github.com/rmorison/engineering-standards/pull/41),
where the corrected artifact was not a sentence either time:

```
the fence rule:  replaced, then confirmed against the file that motivated it
   REFUTED:      running the old rule and the new one over every tracked file
                 found code/python-standards.md:1325 breaking a README template
                 open on main, which no probe was aimed at

the link count:  "192 - 1 + 16 = 207", offered as evidence the fix was sound
   REFUTED:      the change has three terms, not two; the sum balanced only
                 because the third was zero, and would have balanced just the
                 same with links silently dropped
```

The first is a rule carrying the authority of the diagnosis that produced it. The second is
**count the clauses** applied to arithmetic: a justification with four clauses needs four
checks, and an identity with three terms needs three terms. A reconciliation that cannot
move when the thing it vouches for breaks is not a reconciliation.

Writing this document hit the repository's own checker in passing. The comparison above first
used `->` as its arrow, and check 3 in `scripts/check-docs.mjs` then read every line of every
file, fenced code included, flagging a line that starts with `-` followed by `>` as a list
item opening a blockquote. Check 2 had the same fence-blindness. Both were
[#37](https://github.com/rmorison/engineering-standards/issues/37), fixed in PR #41: fence
tracking now lives in one place and the checks that need to tell prose from an example read
it. The `REFUTED:` markers above survive because they read better than arrows, not because
the checker still requires them.

A quote that came back through a delegate, in [PR #56](https://github.com/rmorison/engineering-standards/pull/56). A research subagent was asked to quote Claude Code's permissions page verbatim. Its summary went into a draft of `templates/README.md` as a blockquote. The README promises its block quotes are verbatim, so the text was checked against the page before it was committed, and the drafted wording below never reached the repository:

```
as drafted:  > Development environment runners such as `devbox run`, `mise exec`,
             > `npx`, and `docker exec` are not in the list. ... so to allow work
             > inside the environment, write rules for the inner command itself.
             (anchor #bash)
   REFUTED:  the page lists `direnv exec` as well, and its advice is "write a
             specific rule that includes both the runner and the inner command,
             such as `Bash(devbox run npm test)`. Add one rule per inner command
             you want to allow." (anchor #process-wrappers)
```

The paraphrase dropped a runner, merged three sentences into one, and pointed at the wrong anchor. It also softened the one clause that constrained the change. The page recommends an exact rule per inner command, and the kit's `Bash(uv run pytest:*)` keeps a wildcard for arguments. With the real text in hand, the README states that as a departure. Under the paraphrase there was no departure to state.

The same failure in code, in [PR #61](https://github.com/rmorison/engineering-standards/pull/61), the leak gate. The [whole-PR @claude review](https://github.com/rmorison/engineering-standards/pull/61#issuecomment-5859727039) could not install gitleaks, so it marked findings Confirmed or Plausible. Both top findings were reproduced with gitleaks 8.24.2 before they were fixed, and both held. The fixes were then reviewed [on their own](https://github.com/rmorison/engineering-standards/pull/61#issuecomment-5859931612): earlier findings out of scope, the risky surfaces listed, a `:` in a path among them. That [review](https://github.com/rmorison/engineering-standards/pull/61#issuecomment-5859933263) found three bugs the fixes had made. The third was two tables in the standard that no longer agreed. The other two:

```
hidden-file scan:  copy each staged file hidden by .gitattributes with git show ":$p"
   REFUTED:        gitrevisions reads :[<n>:]<path> as a stage number (0 to 3), so a
                   file named 2:notes.md was skipped without a message, and
                   0:notes.md copied the contents of notes.md instead
   STANDS:         blob id from git --literal-pathspecs ls-files -s, read with
                   git cat-file blob (scripts/leak-gate.sh:227, :234)

two new rules:     "treat an undecided repo as one that may become public"
                   and "when two cells apply, the stricter one wins"
   REFUTED:        together they required every undecided private repo to use
                   GitHub private vulnerability reporting, which GitHub offers
                   for public repositories only
   STANDS:         leak guards apply now; items that need a GitHub feature
                   follow actual visibility (process/repository-standards.md:22)
```

Neither rule was wrong alone, and both came from fixes to separate findings. Each fix was checked against the finding that prompted it, and neither against the other. Each of these fixes gained a fixture that fails against the pre-fix code. Each review round found fewer real defects than the one before, in narrower classes, and that trend was part of the merge call. One finding in the last round, GNU grep dropping a Latin-1 line, did not reproduce locally. Its harmless fix, `grep -a`, stayed, recorded as unreproduced rather than confirmed.

It was the second time. In [PR #56](https://github.com/rmorison/engineering-standards/pull/56), a scoped @claude review after the in-session review and its fixes found that the new allow entries could be widened to a wildcard and still pass the check, and that a README sentence calling one command "the one exception" was false. In the same round, one of the fixes added a comment claiming that the first three new fixture rows ran through `make`; the first of them did not. Re-reading the diff caught it (session history).

## Related

- [`prove-a-check-fails-before-trusting-it-passes.md`](./prove-a-check-fails-before-trusting-it-passes.md) covers the same shape one layer down: a tool reporting success that does not mean what it appears to mean. This entry is about a person doing it. Its habit 4, diffing a rule's classifications across the corpus rather than checking the case that prompted the change, is this principle's concrete method when the corrected artifact is a rule.
- [`process/compound-engineering-integration.md`](../../../process/compound-engineering-integration.md) carries the drift note on corrections that fail to propagate. Propagating a correction assumes the correction is right. Its [AI-review discipline](../../../process/compound-engineering-integration.md#ai-review-discipline-not-enforced-merge-gate) asks for a second review pass in a separate session for critical changes. It does not say to scope that pass to the fixes, which is what found the defects above.
- [`a-check-must-read-a-file-the-way-its-consumer-does.md`](./a-check-must-read-a-file-the-way-its-consumer-does.md) is the same failure in a check that promised not to repeat values and never tested the promise.
