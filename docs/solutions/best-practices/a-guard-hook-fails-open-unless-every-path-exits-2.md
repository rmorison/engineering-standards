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

`scripts/claude_leak_hook.py` (#77, squash-merged as `cf50604`) is a Claude Code `PreToolUse` hook. It must deny a Bash call that would post a value from the holder's private value list to GitHub, or switch off the git-side [leak gate](../../../process/repository-standards.md#leak-gate). A guard like this has two quiet ways to stop guarding, and neither shows up as a failing test of the rules it enforces. In both, the hook does not decide anything, and Claude Code then lets the call through.

Both behaviours come from the Claude Code hooks reference (https://code.claude.com/docs/en/hooks, read 2026-10-04 for Claude Code 2.1.288). Exit 2 is covered in its section on exit codes, and the timeout in its material on hook timeouts:

- **Only exit 2 blocks.** Other non-zero exit codes are non-blocking errors, and the call continues through the normal permission flow.
- **A hook that times out does not block either.** The call again continues through the normal permission flow. The default timeout for a command hook is 600 seconds.

## Guidance

**1. Make every failure end in exit 2, inside the script and outside it.**

- **Inside the script:** turn every unexpected state into a deny. In the hook, a top-level `except Exception` prints a message naming only the exception type and exits 2. Input that is not valid JSON denies, and so does Bash input with no command string (`main()` in `scripts/claude_leak_hook.py`). A value list that is declared but missing, unreadable or invalid denies outbound calls, the `gh` writes the hook checks, rather than skipping them. A list that was never declared allows them, with a note that value rules were skipped.
- **Outside the script:** the script cannot catch its own absence or its interpreter's. The settings command in `process/repository-standards.md` (Guarding Agent Sessions) is `python3 "$HOME/.claude/hooks/claude_leak_hook.py" || exit 2`, so any non-zero exit becomes 2. Without that suffix, a missing `python3` exits 127, a missing script or a syntax error exits non-zero, and every call is allowed.
- **A related rule: never print `permissionDecision: "allow"`.** This is a loud over-allow rather than a quiet failure. The same reference says it approves the call past the user's permission prompt. The hook allows by exiting 0 with no decision. Its fixtures fail any allowed call that prints one.

The install was proved from the standard's own text in #77's PR body (Testing). With `python3` missing, the script missing, a planted import failure, or a planted syntax error, the installed command exited 2. That run used `bash` and a scratch `HOME`, outside Claude Code. The step from exit 2 to a blocked call is the reference's, and #74's criterion 6 run, the install on one machine, saw Claude Code block on exit 2. The cost is real: a broken install stops every Bash call on that account. That is why the standard says how to recover: fix the interpreter or the script, or remove the entry.

**2. Bound every read the session can influence, because a hang is an allow.**

A hook that blocks until it times out lets the command through unchecked. So does one whose memory grows until the timeout comes first. Growth that ends sooner is caught: in #77, `/dev/zero` ended in a `MemoryError` that the catch-all turned into exit 2, and an out-of-memory kill exits non-zero, which the `|| exit 2` suffix catches. The Claude review of #77, of the whole PR as first opened, found that the hook read body files with no limit:

- A FIFO passed as `--body-file` blocked `open()` forever.
- `/dev/zero`, given directly or through `--body-file - < /dev/zero`, grew memory until `MemoryError`.

The fix in #77 is `read_body()`, from the branch commits "bound body-file reads" and "enforce the body-file cap after reading", both squashed into `cf50604`:

- `stat` the path first, and deny anything that is not a regular file.
- Deny a file over 10 MiB.
- Read at most 10 MiB + 1 bytes, and deny if more came back, in case the file grew after the `stat`. This check answers the later review of the fix delta (#77, issuecomment-5985326124). Only a one-off probe covers it, not a fixture.

Every message is a constant, naming neither the path nor the contents. The fixtures cover a FIFO, `/dev/zero` both ways, and an 11 MiB file. Each one failed against the pre-fix hook (#77, the answer to the Claude review, issuecomment-5985288156). One part was already true before the fix: `/dev/stdin`, `/dev/fd/0` and `/proc/self/fd/0` map to the `<` redirect target, or are dropped when there is none, so the hook never reads its own stdin a second time.

**3. Give the test harness a timeout of its own.** The first run of the FIFO fixture against the pre-fix hook did not fail. It hung, because the harness ran the hook with no timeout. In CI, that would have stalled the job until its timeout rather than failed it. `scripts/test_claude_leak_hook.py` now passes `timeout=` to each hook call and reports a timeout as a failed fixture. A timeout can never count as a pass.

**4. A settings change reaches sessions that are already running.** One observation supports this. The session that ran #74's criterion 6 started on 2026-10-04, a day before the hook was installed. After the install it was denied when it first tried to post the result to GitHub in a single command (#74, issuecomment-6004669964). That comment also repeats the earlier assumption that running sessions keep the hooks they started with. The live denial is the evidence this doc relies on. The hooks reference says that direct edits to hooks in settings files are normally picked up automatically by its file watcher. This doc recommends, beyond what the standard says:

- A broken hook stops every running session at once, not only new ones. Back up `settings.json` before installing, and test the install in a fresh `claude -p` session before relying on it.
- Fresh sessions are still the clean end-to-end test, because they rule out any state left from before the install.
- The reference's wording, "normally", does not promise a reload, so do not rely on one either way.

## Relation to other learnings

- [prove-a-check-fails-before-trusting-it-passes](./prove-a-check-fails-before-trusting-it-passes.md) says to plant the defect a check exists to catch. For a guard hook, the hook's own crash, hang and absence are among those defects. Plant them too, as #77 did with stubs, a planted import failure, a FIFO and a missing interpreter.
- [hold-a-stated-risk-with-a-fixture-that-fails-when-the-risk-is-gone](./hold-a-stated-risk-with-a-fixture-that-fails-when-the-risk-is-gone.md) pins risks a check knowingly accepts. This doc is about failures nobody accepted, and it does not extend that one. Its section on the layer a fixture observes applies here unchanged. Fixtures that drive the script directly cannot observe the settings command, so the `|| exit 2` suffix is proved by the install run, not by the suite.
- [prove-a-pasted-command-from-the-docs-own-text](./prove-a-pasted-command-from-the-docs-own-text.md) is how the install command was proved: extracted from the standard, run under a scratch `HOME`, with the failures planted.
- [a-corrected-claim-is-not-a-verified-claim](./a-corrected-claim-is-not-a-verified-claim.md) says to review the fix delta on its own. That review found the read-after-`stat` gap in `read_body()`.

## When to apply

- A hook, wrapper or gate whose job is to refuse something, where "the tool around it continues on error" is the default.
- Any hook that reads a path, a pipe or a stream named by the input it judges.
- Not for hooks that only observe or annotate, where allowing on failure is the right default.
