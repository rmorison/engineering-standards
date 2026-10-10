---
title: A guard that models a grammar exactly fails open at each edge it misses
date: 2026-10-09
category: best-practices
module: claude-leak-hook
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - "A guard decides allow or deny by parsing input in a grammar it doesn't own, such as shell options, redirects or standard input"
  - A review of a fix to the guard's parser finds a new missed form in the same mechanism
  - Choosing between following every form of a construct and refusing the forms the guard can't read plainly
  - Reviewing a guard hook whose reviewer can't run a real shell
resolution_type: code_fix
related_components:
  - testing_framework
  - development_workflow
tags: [claude-code, hooks, parser, shell, grammar, fail-open, fail-safe, over-deny, review, leak-gate, policy-hook]
---

# A guard that models a grammar exactly fails open at each edge it misses

## Context

The agent-session leak hook (`scripts/claude_leak_hook.py`) and the policy hook (`scripts/claude_policy_hook.py`, which imports the leak hook's parser) read a Bash command and decide whether it may run. The leak hook refuses a `gh` write whose text or body file holds a listed value. The policy hook refuses merges, settings writes and pushes to the default branch. Each decision depends on the parser reading the command as the shell will. For these hooks, a misread form usually means the hook never sees the `gh` write or the push, and so it allows the command.

Two pull requests closed parser gaps: #117 (for #111, interpreters, and #95, process substitution) and #118 (for #114, fd-number redirects and here-strings). Each fix began as an exact model of part of shell grammar. Each review then found a form the model got wrong, and several of those were introduced by the previous fix. After the first review, each round was a fix-delta review: a review of only the changes made to answer the previous one ([a-corrected-claim-is-not-a-verified-claim](./a-corrected-claim-is-not-a-verified-claim.md)).

**Shell `-c` scripts, #117.** The hook has to find the script that `bash -c` runs, so it can parse the commands inside.
- **First review** (issuecomment-6071735585). `bash fix.sh -c x` was read as `-c x`. In bash, options end at `fix.sh`, and `-c` is the script's argument. The fix stopped the option scan at the first word that isn't an option.
- **First fix-delta review** (issuecomment-6071882138). That fix stopped at `pipefail` in `bash -euo pipefail -c '…'`, which is a common agent idiom. The `-c` script went unparsed in both hooks, which was a regression. The fix counted one value for each `o` in an option cluster.
- **Second fix-delta review** (issuecomment-6090880221). Two more misreads.
  - In `bash -c - '…'`, the lone `-` was taken as the script.
  - Bash accepts its long options with one dash (`-login`, `-norc`, `-rcfile f`). `-login` was counted as a cluster holding `o`, so it swallowed the script. `-norc` was taken as `-c`.
- **Third fix-delta review** (issuecomment-6091149792). The redesigned rule, described under Guidance, had kept an "unless it looks like an option" filter on candidate words. That filter dropped a script that starts with `-` or `+`, as in `bash -c -- '-x; gh …'`. `+c` runs a script too, and wasn't recognised.

**Redirects and standard input, #118.** The hook had to tell `2>f` (a redirect of fd 2) from `2 > f` (an argument `2`). The parser splits a command into words with shlex, Python's shell-like tokenizer, and shlex splits both of these the same way. A dup operator, `>&` or `<&`, copies one fd onto another: `2>&1` sends fd 2 wherever fd 1 goes.
- **First review** (issuecomment-6091191012).
  - In `>& 2>/dev/null`, bash reads the `2` after `>&` as its target even across a space. The hook joined it to the next `>`, so `/dev/null` became the push's remote.
  - `--body-file - 3<dirty.md <&3` lost its standard input, so the file was never scanned.
- **Fix-delta review** (issuecomment-6091379669).
  - The test for "after a dup operator" ran on shlex's output, where quotes are gone. So a quoted word such as `X='a>&'` cancelled the next `2>`, and the `2` became the program, which neither hook checks. That was a regression from the previous fix.
  - `0>&3` sets standard input too, and the exact standard-input model didn't follow it.
- **Second fix-delta review** (issuecomment-6091551586). The dup flag survived a space or tab but not a carriage return, which shlex treats as a blank. `git push >&\r2>/dev/null origin HEAD:trunk`, in a clone whose default branch is `trunk`, became allowed again, though main had denied it.

Each fix was tested and seen failing first. The fixtures passed. The next review still found the next form, because the fixtures covered the forms already found, not the ones the model got wrong.

## Guidance

**When a guard models a grammar it doesn't own, design it to fail safe rather than exact.** Two moves do most of the work.

1. **Check every candidate reading, not the one the model picks.** In #117, the hook stopped deciding which word after `bash -c` is the script. Every word after the first option word holding a `c` (`-c`, `-lc`, `+c`) is parsed as a candidate script (`shell_candidates()`, `scripts/claude_leak_hook.py:573`). Values such as `pipefail`, and options such as `--`, parse as harmless one-word commands. A misread option can no longer hide the real script, because the real script is among the candidates whatever the options were. The reason is in the source, at `scripts/claude_leak_hook.py:564-567`: "A shell's option grammar is not modelled exactly: three attempts each opened a fail-open (#117)."
2. **Refuse what can't be read plainly.** In #118, `--body-file -` is read only from a plain `<` or `0<` file, a heredoc or a here-string. Any other redirect onto standard input (`<>`, `<&N`, `0>&N`, `<&-`, `<` from `/dev/fd/N`), and a redirect on a compound command, is denied with a "cannot follow" message rather than followed. `standard_input()` (`scripts/claude_leak_hook.py:794`) refuses the redirects. `decide()` (`scripts/claude_leak_hook.py:1076-1083`) refuses the compound-command case, when a `gh` command with no redirect of its own reads `-` and the call holds a redirect on `{ …; }`, `( … )` or `done`. § Guarding Agent Sessions in `process/repository-standards.md` states the rule.

**Keep exact grammar only where it removes a false positive you can name, and arrange it so an error there only over-denies.** A shell still counts as an interpreter unless `plain_shell_script()` (`scripts/claude_leak_hook.py:585`) finds it plainly running one `-c` script. It checks two things. The options before the script use only the letters `c`, `e`, `u`, `x`, `v`, `l` and `o` (with `o`'s value), after `-` or `+`, or are `--`. No `BASH_ENV=`, `ENV=` or `ZDOTDIR=` assignment comes before the shell, so `--rcfile` and any other option fail the letter check. That exact check exists for one reason: so that `bash -c 'echo hi'` beside a body-file post isn't refused. What keeps its misreads on the safe side is `shell_candidates()`, which parses every candidate script whatever `plain_shell_script()` decides. A misread there can only add an interpreter, and so a denial. The known exception is a startup file the check doesn't name. A `HOME=` prefix makes `bash -lc` read `$HOME/.bash_profile` and is allowed (#119, item 1). Wrapper options (`timeout --sig`, `env -iu`) stayed exact, because a fail-safe there would change what the policy hook reads as the program. The forms they still miss are listed in #119.

**Name the over-deny cost, and get it signed off.** Fail-safe refuses some commands the shell would run harmlessly:
- `bash fix.sh -c 'git push origin main'` is denied by the policy hook, though bash only passes those words to `fix.sh`;
- `--body-file - 3<f <&3` and `--body-file - <>f` are refused, though they read `f`.

Each pull request description here opens with At a glance, and its Spec drift part records what changed from the issue as filed. #117's Spec drift names its cost for the operator to confirm at merge. #118's records the design change there, and its review answer names the refused forms. Pin each accepted over-deny with a fixture, so a later change can't quietly move it either way ([hold-a-stated-risk-with-a-fixture-that-fails-when-the-risk-is-gone](./hold-a-stated-risk-with-a-fixture-that-fails-when-the-risk-is-gone.md)). As of this writing, the `<&3` and `<>` forms are pinned in the leak suite, but `bash fix.sh -c 'git push origin main'` has no policy fixture. The leak-suite `bash fix.sh -c x` fixture is a correct deny, not this over-deny. The lead is adding it to #119.

**Switch designs on the second finding in the same mechanism, not the fifth.** One missed form is a bug. A second missed form in the same mechanism, found in review of the fix for the first, means the model is the problem. In #117 the switch came after three rounds of exact fixes. In #118 the standard-input rule switched after three, and the fd-number tokenizer, which stayed exact, drew a fourth finding. Each extra round of exact fixes cost a review cycle, and most of those rounds shipped a regression of their own.

**Confirm each claimed shell behaviour with a real shell before writing its fixture.** The reviewers in the later rounds couldn't run Python or a shell, and said so. Every claim was run in bash and dash before a fixture was written, as in `echo out >&\r2>f`, which creates a file named `\r2` in bash. Where a shell wasn't available (zsh isn't installed on the machine, and `sudo` needs a password), the answer said so, and the rule erred toward denying.

**Diff the importer's decisions across the variants a reviewer would try next, not only the cases you fixed.** The `-euo pipefail` regression shipped because the decision diff in #117's answer tested `-o pipefail` written separately, and never clustered. Later rounds diffed 12 to 51 commands, including clusters, spaced and unspaced dup operators, quoted operator characters and carriage returns, and checked that nothing moved from deny to allow against main or the previous head. This is step 2 of [a-change-to-a-shared-parser-runs-every-importers-suite](./a-change-to-a-shared-parser-runs-every-importers-suite.md), applied to the variants rather than the fixed cases.

## Why This Matters

An exact model of a grammar the guard doesn't own has one failure mode per edge. Shell has many edges: one-dash long options, `+` options, clustered values, `--` and `-`, `\r` as a blank, quoting that the tokenizer removes before the next test runs, and fds that copy other fds. Each edge the model misses is a fail-open, and it fails silently. The command runs, and no test fails until someone writes the case down. Fixing edges one at a time converges slowly, and each fix adds edges of its own. In #117 and #118, the clustered `-euo pipefail`, the filtered `-`/`+` script, the quoted `>&` and the carriage return were all regressions from the previous round's fix.

A fail-safe design moves most of the cost from silent fail-opens to visible over-denies. It doesn't end the rounds. It shrinks the fail-open surface to the edge of what the rule recognises, and that edge still needs fixtures. A redirect around `sh -c '…' <f` or a function call isn't a compound command, so it isn't refused. It is listed as not seen and pinned, and the wrapper forms are in #119. An over-deny shows up the first time an agent hits it, with a message saying what to do instead. The hook's rule for that is already "write the file in one step, then post it in the next". For a guard against mistakes, that is the right direction to err. A guard that fails open is worse than none, because people trust it.

## When to Apply

- A guard, hook or check that parses a language it doesn't control in order to allow or deny: shell commands, URLs, file paths, regular expressions, or config with optional syntax.
- A review of a fix to such a parser finds another missed form in the same mechanism.
- The guard stops mistakes, not intent. § Guarding Agent Sessions says the hook "does not stop a session that sets out to get around it". An over-deny is acceptable only when the rewrite is cheap and the denial names it, as "write the file in one step, then post it in the next" does. A common idiom, such as `bash -euo pipefail -c '…'` or `2>&1`, must stay allowed, so carve it out with an exact rule and a fixture, as `plain_shell_script()` and the `2>&1` allow pin do.
- Outside shell, the same applies. A URL check that can't tell which of two parsers will read a URL should refuse a URL the two would read differently, rather than guess.
- Not when the guard can call the real consumer's parser, or diff against it. There, matching the consumer exactly is cheaper and has no over-deny cost ([a-check-must-read-a-file-the-way-its-consumer-does](./a-check-must-read-a-file-the-way-its-consumer-does.md)). Shell has no parser the hook can call without running the command.

## Examples

**Before (exact), #117 after its first fix-delta review.** The hook read a shell's options with their values, and took the first other word as the `-c` script:

```text
bash -euo pipefail -c 'git push origin main'   -> denied (values counted)
bash -c - 'git push origin main'               -> allowed: "-" taken as the script
bash -login -c 'git push origin main'          -> allowed: -login read as a cluster with o
```

**After (fail-safe), as merged in #117.** Every word after the first `c` option word is a candidate script:

```text
bash -c - 'git push origin main'               -> denied: the script is a candidate
bash -login -c 'git push origin main'          -> denied
bash +c 'git push origin main'                 -> denied
bash fix.sh -c 'git push origin main'          -> denied (the accepted over-deny)
bash -c 'echo hi' && gh pr comment 1 --body-file clean.md -> allowed (plain -c, no interpreter)
```

**Standard input, #118, with a value list declared.** With no list, the hook allows outbound commands, with a note that value rules were skipped, before it reaches this check. The exact model at the first fix-delta review followed `<&N` through the fds it copied, and missed `0>&N`. The fail-safe rule reads only plain input:

```text
gh pr comment 1 --body-file - < body.md        -> body.md is read and scanned
gh pr comment 1 --body-file - <<'EOF' ... EOF  -> the heredoc text is scanned
gh pr comment 1 --body-file - 3<body.md 0>&3   -> denied: "cannot follow"
{ gh pr comment 1 --body-file -; } < body.md   -> denied: "cannot follow"
```

## Relation to other learnings

- [a-guard-hook-fails-open-unless-every-path-exits-2](./a-guard-hook-fails-open-unless-every-path-exits-2.md) covers the hook failing to decide at all: a crash, a hang or a missing interpreter. This doc covers the hook deciding wrongly, because its model of the input is wrong. Both fail open, at different layers.
- [a-change-to-a-shared-parser-runs-every-importers-suite](./a-change-to-a-shared-parser-runs-every-importers-suite.md) is why both hooks' suites ran on every round, and why the decision diffs here compared the policy hook under each parser.
- [a-corrected-claim-is-not-a-verified-claim](./a-corrected-claim-is-not-a-verified-claim.md) says to review each fix delta on its own. That is how the regressions in #117 and #118 were caught.
- [prove-a-check-fails-before-trusting-it-passes](./prove-a-check-fails-before-trusting-it-passes.md) applies to every fixture here, and each was seen failing against the previous head.
- Residuals that take intent, outside the hooks' scope, are tracked in #119.
