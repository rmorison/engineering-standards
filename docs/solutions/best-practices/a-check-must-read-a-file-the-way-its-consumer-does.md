---
title: A check must read a file the way its consumer does
date: 2026-09-24
category: best-practices
module: secret-refs-check
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - Writing a check for a file that another program parses at runtime
  - Reimplementing a subset of a parser instead of depending on the real one
  - Normalising line endings, comments or encodings inside a check
  - A check's failure messages quote part of the input they reject
  - Trusting a check because it passes mutation testing
resolution_type: code_fix
related_components:
  - development_workflow
  - documentation
tags: [secrets, ci, tokenisation, false-negative, dotenv, output-channel, mutation-testing, verification]
---

# A check must read a file the way its consumer does

## Context

Issue #30 added `scripts/check-secret-refs.mjs`, a dependency-free Node check that decides whether a committed `secret-refs.env` holds only secret-manager references (`op://...`) and no literal secret. The check does not own the file's format. Other programs read the file at runtime: python-dotenv 1.2.3, through the application's `dotenv_values` start-up check, and a secret-manager runner. The plan chose to write a strict subset of dotenv in the check and not to import a dotenv parser (plan KTD5, `docs/plans/2026-09-24-0028-feat-no-secrets-at-rest-plan.md:132`). The check therefore runs its own model of a format that some other program defines.

The check had strong verification by the usual measures. It runs its classifier against in-script fixtures before it reads any file (`selfTest` in `scripts/check-secret-refs.mjs`). Two mutation-testing passes caught every mutation in the end: 21 in the first pass and 24 in the second, as the session's runs record. In each pass one mutant survived at first and was turned into a fixture. The first survivor was an indented comment (now a `LINE_FIXTURES` row). The second was a fenced-block marker that matched by prefix only (now a `BLOCK_FIXTURES` row). Code review, with a validator reproducing each case, still found three defects that let a secret through or printed it. Mutation testing could not have found them. It measures whether the fixtures pin down the code, and all three defects were in the fixtures' model of the world. Two came from the check disagreeing with the systems around the file. The third came from the check's own output.

1. **Line splitting did not match the consumer.** `linesOf` split on `/\r?\n/`. python-dotenv 1.2.3 ends a line at CRLF, LF or a lone CR (`_newline = (\r\n|\n|\r)` and `_end_of_line` at `parser.py` in the python-dotenv 1.2.3 wheel). The file `'# note\rSTRIPE_API_KEY=sk_fake_value\nA=op://dev/a/b\n'` was one comment line plus one reference to the check, which exited 0. To dotenv it was a comment, then `STRIPE_API_KEY=sk_fake_value`, then `A`. `dotenv_values` returns `{'STRIPE_API_KEY': 'sk_fake_value', 'A': 'op://dev/a/b'}` for that file. The session's validator reproduced this, and it was re-run against the wheel while this doc was being written. The plan's KTD5 had called line endings "normalised". That normalisation followed the check's own idea of a line, not the consumer's. The standard's `.gitattributes` rule (`code/python-standards.md:805`, `secret-refs.env text eol=lf`) does not close the gap. In a scratch repository, `git add` rewrote the CRLF to LF and left the lone CR in the index unchanged.
2. **A commented-out secret passed.** Every line starting with `#` was a comment (the pre-fix `classifyLine`). `# STRIPE_API_KEY=sk_fake_old`, left behind after moving a key to the manager, passed. dotenv ignores the line (`parse_key` in the same file returns `None` on `#`), so matching the parser would never have caught it. The secret is still committed to the repository.
3. **The check printed the secret it guards.** Failure messages named the text before the first `=` as the line's key. On a line holding a pasted padded base32 or base64 secret, such as `JBSWY3DPEHPK3PXPJBSWY3DP====`, that text is the secret. `/^([A-Za-z0-9_]+)=(.*)$/` read `JBSWY3DPEHPK3PXPJBSWY3DP` as an UPPER_SNAKE_CASE key and `===` as its value. When the pre-fix script (the commit before "fix(review): apply review findings") was run on that line, it printed ``leak.env:1  [literal] `JBSWY3DPEHPK3PXPJBSWY3DP` has a value that is not a reference`` to stderr, which is a CI log. The script's header had promised never to repeat a value.

The fixes were written proof-first. Fixtures for all three were added and watched fail (9 red) before the code changed.

## Guidance

**A check that guards a file for another program must split that file into lines, comments and entries exactly as the program does, must cover what the repository stores as well as what the program reads, and must treat its own messages as a channel that can leak the thing it guards.**

1. **Tokenise like the consumer, and cite where its rules come from.** Where the check can be stricter than the consumer, being stricter is safe. A rejected line fails loudly. Tokenisation is the exception: it decides what a line is before any strict rule runs, so a strict classifier running on the wrong tokens can still pass the file. The check fails closed on each line it sees. It cannot fail on a line it never sees because two of the consumer's lines reached it as one. Write the consumer's rule into the code with its source. The fix does this in `linesOf`, whose comment names python-dotenv as the reason a lone CR ends a line. Add a fixture for each case where the two could disagree: a lone CR hiding an entry, and lone-CR endings on an otherwise valid file (`FILE_FIXTURES`). `configurationKeys` calls the same `linesOf`, so one splitter serves both file types, and a later fix cannot reach one and miss the other.
2. **Guard what the file holds as well as what the consumer reads.** Matching the parser covers only what it reads. The rule here is that the repository holds no secret, and the repository keeps lines the parser skips. `classifyComment` now fails a commented-out `KEY=value` whose value is not a reference. A commented-out reference still passes, and free text in a comment is still not read (the script's header says so). That limit is written down, not left unstated.
3. **Treat messages as output about the guarded data.** Any field a message takes from input that failed validation may be the secret. Name only what validation has shown is not one. Here that is a key whose value parsed as a well-formed reference: `classifyLine` returns `key` only on the `exposed` and `reference` paths. A `literal` or `malformed` line gets no key, and the report says "This line" instead. The cost is real. `STRIPE_API_KEY=hunter2` is now reported by line number without its key name. That is the right trade for a file whose failure case is a secret.
4. **Test that the check does not leak, not only that it reaches the right verdict.** A verdict fixture asks whether a line fails. A leak fixture asks what the failure printed. `LEAK_FIXTURES` holds secret-shaped lines. The self-test requires each to fail and fails itself if any message contains any `=`-separated part of 4 or more characters. The substring test is a heuristic. It proves that these five lines are not echoed, not that no line ever will be, and it runs before any file is read, like every other fixture.
5. **Where you can, diff against the real consumer.** Mutation testing asks whether the fixtures pin down the code, and they can pin it down to the wrong behaviour. Defect 1 was found by running the actual parser over the case, and that is the only kind of test that asks whether the check agrees with the consumer. This is habit 4 of [prove-a-check-fails-before-trusting-it-passes](./prove-a-check-fails-before-trusting-it-passes.md), applied to the consumer where that doc applies it to a corpus. If shipping the consumer is ruled out, as it is for a dependency-free check, run the comparison once while developing, turn each disagreement into a fixture, and pin the consumer version the fixtures were checked against.

## Why This Matters

A check like this one exists so that no one has to read the file. A pass gets read as "this file is safe", and the review that would have caught a literal gets skipped. Defect 1 hid behind exactly that trust: a line that looked like a comment, in a file the check had passed. The check's strictness gave no protection here. KTD5 argued the check "cannot pass a file because of a line it skipped". That holds only if the check and the consumer agree on what a line is, and until the fix they did not.

Defect 3 is worse than a false pass, because the check itself caused the harm. With no check, a secret pasted into `secret-refs.env` sits in one file that needs repository access to read. With the pre-fix check, that secret is also copied into the CI log of every run, where more people can read it. For any check over sensitive input, the report is a second copy of what it reports on. A check that promises in its header not to repeat values and never tests the promise has the same problem as [a corrected claim that was never verified](./a-corrected-claim-is-not-a-verified-claim.md): the sentence claims more than was checked.

All three defects survived a self-test and two mutation passes that caught every mutation. Those tools measure a check against its own specification. None of them asks whether the specification matches the consumer, the repository, or the log reader.

## When to Apply

- Writing any check, linter or validator for a file another program parses: `.env` files, CODEOWNERS, `.gitattributes`, YAML read by a CI runner, lockfiles, crontabs
- Choosing to reimplement a parser subset rather than depend on the real one, which is when tokenisation disagreements become possible
- Adding "normalisation" of line endings, whitespace, encodings or a byte-order mark to a check. Normalise to the consumer's rules, not to what looks tidy
- Any check whose input may contain secrets, credentials or personal data and whose output reaches a log, a PR comment or a chat channel
- Reviewing a check that passes mutation testing. Ask what its fixtures were checked against

## Examples

### A lone CR turned a comment into an entry

```text
bytes:     # note \r STRIPE_API_KEY=sk_fake_value \n A=op://dev/a/b \n
check:     [# note\rSTRIPE_API_KEY=sk_fake_value]  [A=op://dev/a/b]   -> comment, reference: exit 0
dotenv:    [# note]  [STRIPE_API_KEY=sk_fake_value]  [A=op://dev/a/b] -> comment, entry, entry
```

Before the fix, `linesOf` was `text.replace(/^\uFEFF/, '').split(/\r?\n/)`. It is now:

```js
return text.replace(/^\uFEFF/, '').split(/\r\n|\r|\n/);
```

(`linesOf` in `scripts/check-secret-refs.mjs`). The CRLF alternative comes first, so a CRLF pair still ends one line, not two. The `CRLF endings` fixture holds the check to that.

### A commented-out entry after a migration

```text
# STRIPE_API_KEY=sk_fake_old            <- dotenv ignores it; git keeps it
STRIPE_API_KEY=op://dev/stripe/credential
```

`LINE_FIXTURES` now requires `# STRIPE_API_KEY=hunter2`, `#STRIPE_API_KEY=hunter2` and `# STRIPE_API_KEY=` to be `literal`, and `# STRIPE_API_KEY=op://dev/stripe/credential` to stay a `comment`.

### The "key" was the secret

The same input, `JBSWY3DPEHPK3PXPJBSWY3DP====` followed by one valid entry, run through both versions:

```text
pre-fix:  leak.env:1  [literal] `JBSWY3DPEHPK3PXPJBSWY3DP` has a value that is not a reference
fixed:    leak.env:1  [literal] This line has a value that is not a reference
```

The regex matched because base32 is uppercase letters and digits, which also makes a valid UPPER_SNAKE_CASE key, and its `=` padding supplied the separator. Base64 with `=` padding, and anything else shaped like `word=word`, fits the same regex. `LEAK_FIXTURES` holds one of each shape, plus a commented-out entry, so that a change which starts naming keys again fails before any file is checked.

### What the mutation passes did catch

Mutation testing still found real gaps, and each surviving mutant became a fixture. An indented `  # comment` was being treated as a comment when the rule allows only full-line comments. The example-block finder matched `# m, and more` as the marker `# m`. Both were gaps in the fixtures against the check's own specification, which is the kind of gap mutation testing finds. The three review defects were gaps in the specification itself, and only a comparison with the real parser and a check of the check's own output found those.
