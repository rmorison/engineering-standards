---
title: A guard hook fails open unless every path ends in exit 2
date: 2026-10-05
category: best-practices
module: claude-leak-hook
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - "Writing or reviewing a Claude Code PreToolUse hook that must deny a tool call"
  - "A hook reads files, pipes or other input whose size or availability the session controls"
  - "Writing the settings command that installs a guard hook"
  - "Testing a hook with a harness that runs it as a subprocess"
  - "Installing or changing a hook on a machine where agent sessions are already running"
resolution_type: code_fix
related_components:
  - development_workflow
  - testing_framework
tags: [claude-code, hooks, pretooluse, fail-closed, timeout, exit-code, leak-gate, guard]
---

# A guard hook fails open unless every path ends in exit 2

## Context

`scripts/claude_leak_hook.py` (#77, squash-merged as `cf50604`) is a Claude Code `PreToolUse` hook. It must deny a Bash call that would post a private value to GitHub, or switch off the git-side leak gate. A guard like this has two quiet ways to stop guarding, and neither shows up as a failing test of the rules it enforces. In both, the hook does not decide anything, and Claude Code then lets the call through.

Both behaviours come from the Claude Code hooks reference (https://code.claude.com/docs/en/hooks, "Exit code semantics", read 2026-10-04 for Claude Code 2.1.288):

- **Only exit 2 blocks.** Other non-zero exit codes are non-blocking errors, and the call continues through the normal permission flow.
- **A hook that times out does not block either.** The call again continues through the normal permission flow. The default timeout for a command hook is 600 seconds.

## Guidance

**1. Make every failure end in exit 2, inside the script and outside it.**

- **Inside the script:** turn every unexpected state into a deny. In the hook, a top-level `except Exception` prints a message naming only the exception type and exits 2. Input that is not valid JSON denies, and so does Bash input with no command string (`main()` in `scripts/claude_leak_hook.py`). A missing, unreadable or invalid value list denies outbound calls rather than skipping them.
- **Outside the script:** the script cannot catch its own absence or its interpreter's. The settings command in `process/repository-standards.md` (Guarding Agent Sessions) is `python3 "$HOME/.claude/hooks/claude_leak_hook.py" || exit 2`, so any non-zero exit becomes 2. Without that suffix, a missing `python3` exits 127, a missing script or a syntax error exits non-zero, and every call is allowed.
- **Never print `permissionDecision: "allow"`.** The same reference says it approves the call past the user's permission prompt. The hook allows by exiting 0 with no decision. Its fixtures fail any allowed call that prints one.

The install was proved from the standard's own text in #77's PR body (Testing). With `python3` missing, the script missing, a planted import failure, or a planted syntax error, the installed command denied every Bash call. The cost is real: a broken install stops every Bash call on that account. That is why the standard says how to recover: fix the interpreter or the script, or remove the entry.

**2. Bound every read the session can influence, because a hang is an allow.**

A hook that blocks until it times out lets the command through unchecked. So does one that grows until it is killed, unless the `|| exit 2` suffix catches the exit. The Claude review of #77, of the whole PR as first opened, found that the hook read body files with no limit:

- A FIFO passed as `--body-file` blocked `open()` forever.
- `/dev/zero`, given directly or through `--body-file - < /dev/zero`, grew memory until `MemoryError`.

The fix in #77 (branch commits "bound body-file reads" and "enforce the body-file cap after reading", both in `cf50604`) is `read_body()`:

- `stat` the path first, and deny anything that is not a regular file.
- Deny a file over 10 MiB.
- Read at most 10 MiB + 1 bytes, and deny if more came back, in case the file grew after the `stat`.

Every message is a constant, naming neither the path nor the contents. The fixtures cover a FIFO, `/dev/zero` both ways, and an 11 MiB file. Each one failed against the pre-fix hook (#77, the answer to the Claude review, issuecomment-5985288156). The same applies to any input the hook reads: `/dev/stdin` and `/dev/fd/0` are mapped to the `<` redirect target, so the hook never reads its own stdin a second time.

**3. Give the test harness a timeout of its own.** The first run of the FIFO fixture against the pre-fix hook did not fail. It hung, because the harness ran the hook with no timeout. In CI, that would have stalled the job rather than failed it. `scripts/test_claude_leak_hook.py` now passes `timeout=` to each hook call and reports a timeout as a failed fixture. A timeout can never count as a pass.

**4. A settings change reaches sessions that are already running.** When the hook was installed for #74's criterion 6, a session started before the install was denied by it on its next Bash call (#74, issuecomment-6004669964). The hooks reference says direct edits to hooks in settings files are normally picked up by its file watcher. Two consequences:

- A broken hook stops every running session at once, not only new ones. Back up `settings.json` before installing, and test the install in a fresh `claude -p` session before relying on it.
- Fresh sessions are still the clean end-to-end test, because they rule out any state left from before the install.

## Relation to other learnings

- [prove-a-check-fails-before-trusting-it-passes](./prove-a-check-fails-before-trusting-it-passes.md) says to plant the defect a check exists to catch. For a guard hook, the hook's own crash, hang and absence are among those defects. Plant them too, as #77 did with stubs, a planted import failure, a FIFO and a missing interpreter.
- [hold-a-stated-risk-with-a-fixture-that-fails-when-the-risk-is-gone](./hold-a-stated-risk-with-a-fixture-that-fails-when-the-risk-is-gone.md) pins risks a check knowingly accepts. This doc is about failures nobody accepted, and it does not extend that one. Its section on the layer a fixture observes applies here unchanged. Fixtures that drive the script directly cannot observe the settings command, so the `|| exit 2` suffix is proved by the install run, not by the suite.
- [prove-a-pasted-command-from-the-docs-own-text](./prove-a-pasted-command-from-the-docs-own-text.md) is how the install command was proved: extracted from the standard, run under a scratch `HOME`, with the failures planted.

## When to apply

- A hook, wrapper or gate whose job is to refuse something, where "the tool around it continues on error" is the default.
- Any hook that reads a path, a pipe or a stream named by the input it judges.
- Not for hooks that only observe or annotate, where allowing on failure is the right default.
