#!/usr/bin/env python3
"""Example pre-tool-use hook: block a dangerous pattern in writes.

This hook demonstrates how to prevent Claude Code from writing code that
contains a specific pattern. Replace the example logic with your project's
rules.

Hook type: PreToolUse
Triggers on: Write, Edit tools

Exit codes:
  0 - allow the tool use (pattern not found, or nothing to check)
  2 - block the tool use; stderr is shown to Claude as the reason

Exit code 2 is reserved, and that reservation is easy to break by accident.
`argparse` exits 2 on a usage error, and CPython exits 2 when it cannot open
the script it was handed. Either one, reached from inside a PreToolUse hook,
blocks the tool call -- so a hook that merely fails to parse its own arguments
refuses every Write and Edit in the session. Keep every path that is not a
deliberate block on 0, and never let a library choose the exit code for you.

A PreToolUse hook that exits 2 blocks the tool call, and does so ahead of
the `allow` list. Why that makes a hook, and not a permission rule, the
place for a check you need to hold is stated once, in `templates/README.md`
under "Permissions and hooks" -- see
https://github.com/rmorison/engineering-standards/blob/main/templates/README.md#permissions-and-hooks

Input: Claude Code writes a JSON object to this script's stdin. It does not
put the tool payload in the environment. The fields used below were captured
from a running session:

  hook_event_name - "PreToolUse"
  tool_name       - "Write" or "Edit"
  tool_input      - Write: {"file_path": ..., "content": ...}
                    Edit:  {"file_path": ..., "old_string": ...,
                            "new_string": ..., "replace_all": ...}

The environment carries CLAUDE_PROJECT_DIR (the project root), which is what
the settings entry below uses to find this file from any working directory.

Usage in .claude/settings.json - the matcher object takes a `hooks` array;
a bare `command` key on the matcher is not a valid entry. Observed under
Claude Code 2.1.278: a malformed PreToolUse entry made Claude Code reject
the whole settings file, the `permissions` block with it. That is an
observation of one version's behaviour, not a documented guarantee; the
shape below is correct regardless of whether it still holds.

  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "hook=\"${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/pre-tool-use/example-block.py\"; [ -f \"$hook\" ] || exit 0; exec python3 \"$hook\""
          }
        ]
      }
    ]
  }

Copy that command shape, not just the path. Every error path in this script
exits 0, so a mis-wired hook costs you the check rather than the session --
and the registration has to fail open too, or the care taken here is undone
one line above it. Two things in the command do that:

  ${CLAUDE_PROJECT_DIR:-.}  If the variable is unset OR empty, the path
                            would begin at `/`. `:-` (not `-`) covers both.
  [ -f "$hook" ] || exit 0  If the script has been moved or deleted while
                            this entry stayed behind, exit 0 and allow.

Without them the command is `python3 /.claude/hooks/...`, python3 cannot
open the file, and CPython exits 2 -- which on PreToolUse means *block*.
Every Write and Edit in the session is then refused, with `can't open file`
as the stated reason. Verified under Claude Code 2.1.278 on 2026-09-22:
the unguarded form exits 2, the guarded form exits 0.

`exec` is what keeps the block working when the script IS present: it
replaces the shell, so python3's exit code is the hook's exit code.
"""

import json
import sys


def main() -> None:
    # Absent or malformed stdin must not break the session: a mis-wired hook
    # should cost you the enforcement, not the ability to work.
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, OSError):
        sys.exit(0)

    if not isinstance(payload, dict):
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        sys.exit(0)

    # The matcher already narrows this, but a hook is also runnable by hand
    # and may be wired to a wider matcher in your own project.
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    # Write carries the whole file in "content"; Edit carries the replacement
    # text in "new_string".
    if tool_name == "Write":
        content = tool_input.get("content", "")
    else:
        content = tool_input.get("new_string", "")
    if not isinstance(content, str):
        sys.exit(0)

    # --- Replace this example rule with your own ---
    # Example: block time.sleep() in pipeline code
    blocked_pattern = "time.sleep("
    if blocked_pattern in content:
        # Exit code 2 tells Claude Code to block the tool use
        print(
            f"BLOCKED: '{blocked_pattern}' detected. "
            "Use the project's async delay mechanism instead.",
            file=sys.stderr,
        )
        sys.exit(2)
    # --- End example rule ---

    sys.exit(0)


if __name__ == "__main__":
    main()
