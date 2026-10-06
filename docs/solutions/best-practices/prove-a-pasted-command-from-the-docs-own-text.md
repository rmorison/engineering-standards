---
title: Prove a pasted command from the document's own text, in the reader's shell
date: 2026-09-28
category: best-practices
module: leak-gate
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - "Writing a standard or README that tells a reader to paste a shell command"
  - "Verifying a documented command by retyping it instead of running the document's own text"
  - "A command must work in an interactive paste (no set -e, possibly zsh) as well as under CI's bash -e without pipefail"
  - "Proving a command under the author's shell, HOME, PATH or TMPDIR instead of the reader's"
  - "Reviewing a hook installer, a download-and-install snippet, or a CI checksum step"
resolution_type: workflow_improvement
related_components:
  - development_workflow
  - documentation
tags: [shell, verification, ci, interactive-shell, zsh, set-e, extraction, fail-closed, install, pre-commit-hook]
---

# Prove a pasted command from the document's own text, in the reader's shell

## Context

[PR #61](https://github.com/rmorison/engineering-standards/pull/61) added the leak gate to `process/repository-standards.md`, with a pre-commit hook and install pointers for adopters to paste. Its CI install step followed the one in `code/python-standards.md`, which the Python standard recorded as run against a tampered tarball: "The CI step above was run on 2026-09-26: it read `8.24.2` from the hook's `rev`, verified the checksum, failed on a tampered tarball, and exited 1 on a committed secret" (as of #61; #69 reworded it). Issue #62 then found that an adopter who followed the standard literally was broken on every commit. The documented hook ran `sh scripts/leak-gate.sh` unconditionally, so it exited 127 on branches that predate the gate, and worktrees share one hooks directory, so those branches are common. Nothing in the standard put gitleaks on `PATH` either, so the wrapper reported `gitleaks exited 127` and refused every commit. The commands worked on the maintainer's machine, where gitleaks was installed and the hook had been written by hand. They had not been run as a reader runs them: copied from the page into a fresh shell.

[PR #69](https://github.com/rmorison/engineering-standards/pull/69) closed #62. Its proof and review found more gaps of the same kind in text a reader pastes, and one in the proof itself. The Examples below walk through them. None of them shows up when the author runs a retyped copy in the author's own shell. Two details in the Examples come from the session rather than the PR record: the harness's first, wrong block match, and the plan's first draft of the install.

A reader and CI run the same words under different rules. A reader pastes into an interactive shell. It has no `set -e`, and on macOS it is zsh. CI runs a `run:` block under GitHub's default `bash -e`, without `pipefail`. The author's shell has the author's `HOME`, `PATH` and `TMPDIR`, and usually a tool already installed.

## Guidance

**A shell command a standard tells readers to paste is proved only by running the document's own text, extracted rather than retyped, under the conditions the reader will run it in.** A retyped copy is a different command. A run in the author's shell proves the command works for the author.

Five habits follow from it:

1. **Extract, don't retype.** Pull the block out of the Markdown or YAML with a script and run what came out. For PR #69 a small harness read the `run:` text of `.github/workflows/leaks.yml` with a YAML parser, the fenced `yaml` CI step in `code/python-standards.md`, and the fenced `bash` blocks of the standard. Match on a string unique to the block you mean, not on a word several blocks share.
2. **Run under the reader's conditions.** A CI step runs under `bash -e` with no `pipefail`, in a fresh `RUNNER_TEMP`. Give each run a scratch `HOME` without the directories your own machine already has, and a `PATH` without the tool being installed. A paste differs from a script in two ways, and a script run reproduces only the first:
   - **No `-e`.** Running the block as a script, as `sh block.sh`, reproduces this.
   - **Interactive parsing.** A pasted block is read by an interactive shell, and a script run is not. Interactive-only behaviour includes zsh's handling of `#` (its `interactivecomments` option), bash's history expansion of `!`, and aliases. Here, `$-` held `i` and `H` when bash read the block with `bash -i` on standard input, and neither when bash ran it as a script. So a script run under zsh says nothing about how zsh reads a paste. Check interactive parsing with an interactive shell reading the block on standard input, such as `zsh -i`, or list it as not run under habit 5.

   A run under bash says nothing about zsh, either way.
3. **Plant the failure the command must refuse.** For an install that checks a hash, that failure is a tampered download. Put a `curl` stand-in first on `PATH` that downloads the real tarball and then changes one byte, and confirm nothing is extracted or installed. For a step that reads its version from elsewhere, move the version without moving the hash and confirm the step fails.
4. **Print what was extracted, and what the command left behind.** Log the extracted text before running it, and after it runs, show the file it was meant to create. A wrong match then shows on the page instead of passing quietly.
5. **Say which shells and platforms the run covered, and mark the rest not run.** The standard does this for the install: "The Linux command was run on 2026-09-28, including against a tarball with one changed byte, which it refused before installing. The macOS variant was not run on macOS." (`process/repository-standards.md`, Adopting the Gate).

The proof scripts were kept out of the repository. Their output is in PR #69's body.

## Why This Matters

A command block in a standard exists to be pasted, often without being read line by line. So every defect in a pasted command reaches every adopter, and a defect in an install or a hook fails closed on the reader's work, or fails open on the check the command installs. In #62 it failed closed: every commit was refused. The hash-check gap below would have failed open. A tampered binary would have been installed on `PATH` and run on every commit.

Pasted commands are also where the author's and the reader's conditions differ most. The author has the tool installed, the directory on `PATH`, and a shell that stops on the first error. A run that inherits those conditions passes for reasons the reader does not have.

## When to Apply

- Adding or changing a fenced shell block a standard, README or runbook tells the reader to paste.
- Adding or changing a CI `run:` block that another document tells adopters to copy.
- Writing an install step, a hook, or anything else that fetches, verifies or writes outside the working tree.
- Stating in a document that a command "was run", "installs", or "refuses" something.
- Reviewing a command block the author says was tested, when the test was not run from the document's text.

## Examples

### One step per line is safe under `bash -e` and unsafe in a paste

The CI step in `.github/workflows/leaks.yml` puts each step on its own line:

```bash
cd "$RUNNER_TEMP"
curl -sSfLO "$U/$F"
echo "$GITLEAKS_SHA256  $F" | sha256sum -c -
tar xzf "$F" gitleaks
```

That is correct where it runs. GitHub's default shell is `bash -e`, and `sha256sum -c` is the last command of its pipeline, so a mismatch ends the step. The extracted text was run under `bash -e` against the tampered tarball: `FAILED`, exit 1, nothing extracted. `code/python-standards.md` (Using gitleaks Instead) states the dependency: "`sha256sum -c` is the last command of its pipeline, so a mismatch fails the step under the runner's `bash -e`."

The first draft of the plan for the local install reused that shape. The plan's document review (a `ce-doc-review` pass, recorded in the plan sign-off comment on #62) found the problem, and the plan records it (`docs/plans/2026-09-27-1708-fix-leak-gate-adoption-gaps-plan.md`, KTD5): "A developer pastes the command into an interactive shell, which has no `-e`. So KTD4's reliance on the runner's `bash -e` does not carry over." Pasted, the hash line prints `FAILED`, and the next lines still run `tar` and `install`. The shipped command chains every step:

```bash
d=$(mktemp -d) && cd "$d" && curl -sSfLO "https://github.com/gitleaks/gitleaks/releases/download/v$V/$F" &&
echo "$SHA  $F" | sha256sum -c - && tar xzf "$F" gitleaks &&
mkdir -p ~/.local/bin && install -m 755 gitleaks ~/.local/bin/gitleaks && ...
```

That document review also found a claim that would have been false the first time. A newly created `~/.local/bin` reaches `PATH` only in a new login shell, and only where the shell profile adds it, as Debian's and Ubuntu's default profile does; macOS does not add it. The command now ends by checking `command -v gitleaks` and printing what to do when it is not the one just installed.

### The extractor ran the wrong block and the walkthrough passed

This gap was in the proof, not in the pasted text. § Running It Locally in `process/repository-standards.md` has two `bash` blocks that mention `pre-commit`. The first lists the wrapper's modes:

```bash
sh scripts/leak-gate.sh staged                 # what is staged: run it as a pre-commit hook
```

The second installs the hook, starting `hook="$(git rev-parse --git-path hooks)/pre-commit"`. The harness first selected the first block containing `pre-commit`. It ran the modes block, which executed the wrapper once and installed nothing. The later steps of the walkthrough "passed", since commits went through, but they went through because no hook existed. The run was caught only because the harness printed the installed hook, and `cat .git/hooks/pre-commit` reported no such file. The fix matched on `hooks)/pre-commit"`, a string only the installer contains. The published run still prints the installed hook, which is what caught this; it does not print the extracted text, which habit 4 recommends as well.

### zsh, by default, runs a pasted `#` as a command

A draft of the macOS install picked the tarball with commented lines, in this shape:

```bash
F=gitleaks_${V}_darwin_arm64.tar.gz   # Apple silicon
# F=gitleaks_${V}_darwin_x64.tar.gz   # Intel
```

zsh is the default macOS shell, and its `interactivecomments` option is off by default, so in a default setup a pasted `#` is read as a command name rather than a comment. Some zsh configurations turn the option on, so the defect is certain only for zsh's defaults. The code review run before PR #69 was opened (`ce-code-review`, focused depth, run `20260927-1800-62lg`, recorded in PR #69's body) found this. The proof run did not, because it ran under `sh` and `bash` on a Linux host without zsh; even under zsh, a script run would have passed the draft (habit 2). The zsh behavior was not run in this work. It rests on that review and on zsh's documented default. This follows the "Reproduce a finding before you fix it" habit's fallback in `a-corrected-claim-is-not-a-verified-claim.md`: the fix is cheap, and the document says it is unreproduced. The shipped block carries no comments and chooses with `case $(uname -m)` (hashes shortened here):

```bash
case $(uname -m) in
  arm64) F=gitleaks_${V}_darwin_arm64.tar.gz SHA=90d1...bea0 ;;
  *) F=gitleaks_${V}_darwin_x64.tar.gz SHA=bc3c...742c ;;
esac
```

The standard gives the reason in place: the command "carries no comments, because zsh, the default macOS shell, reads `#` as a command when pasted" (`process/repository-standards.md`, Adopting the Gate). It also says the macOS variant was not run on macOS. That line is habit 5: the run covered Linux shells, and the document says so.

### `cd "$(mktemp -d)"` does not stop when `mktemp` fails

The scoped Claude review on PR #69 flagged this and marked it unverified. It was then run. If `mktemp` fails, the substitution is empty, and in bash `cd ""` succeeds without changing directory:

```
$ bash -c 'cd "" && echo ok'
ok
```

So the download would land in the current directory, usually the repository. The fix assigns first, so the `&&` sees `mktemp`'s status:

```bash
# before
cd "$(mktemp -d)" && curl -sSfLO ...
# after
d=$(mktemp -d) && cd "$d" && curl -sSfLO ...
```

It was proved with `TMPDIR` set to a directory that does not exist: `mktemp` failed, the command exited 1, and nothing was downloaded or installed. The same pass moved `V`, `SHA` and `F` inside the subshell, so a paste leaves no variables in the reader's shell. The same review asked what an empty hash does. `echo "  f" | sha256sum -c -` prints "no properly formatted SHA256 checksum lines found" and exits 1, so it fails closed; that was also run.

## Related

- [`prove-a-check-fails-before-trusting-it-passes.md`](./prove-a-check-fails-before-trusting-it-passes.md): plant the defect, read exit codes carefully, and know what `set -e` ignores. Habit 3 here is that entry's habit 1 applied to an install. This entry adds the question of *whose* text and *whose* shell: a check can fail correctly in the author's run and still not be the command the reader pastes.
- [`a-corrected-claim-is-not-a-verified-claim.md`](./a-corrected-claim-is-not-a-verified-claim.md): a correction, whether prose or code, is re-verified as its own act, and a finding is reproduced before it is fixed. The `mktemp` example follows that "Reproduce a finding before you fix it" habit, and the zsh example uses its fallback for a finding that could not be run. That entry covers verifying corrections; this one covers where and how a documented command is run.
- [`a-check-must-read-a-file-the-way-its-consumer-does.md`](./a-check-must-read-a-file-the-way-its-consumer-does.md): the closest rule. A check must parse its input exactly as the consuming program does. Here the consumer is the reader's shell, and the input it parses is the command itself rather than a data file.
- [`a-local-pass-proves-only-the-tool-versions-it-ran-on.md`](./a-local-pass-proves-only-the-tool-versions-it-ran-on.md): habit 5 here, applied to scripts, their fixtures and CI. This entry asks whose shell and environment ran a pasted command; that one asks which tool versions and implementations ran a test suite, such as a git that refuses a fixture's setup or a `sh` that is dash rather than bash.
