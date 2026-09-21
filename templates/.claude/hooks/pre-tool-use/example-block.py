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

A PreToolUse hook that exits 2 stops the tool call before the permission
rules are evaluated, so it blocks even when an `allow` entry would have let
the call through. That precedence is why a hook, not a permission rule, is
the place to put a check you need to hold.

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
a bare `command` key on the matcher is not a valid entry and Claude Code
rejects the whole settings file when a PreToolUse entry is malformed:
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-tool-use/example-block.py"
          }
        ]
      }
    ]
  }
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
