#!/usr/bin/env python3
"""Example pre-tool-use hook: block a dangerous pattern in writes.

This hook demonstrates how to prevent Claude Code from writing code that
contains a specific pattern. Replace the example logic with your project's
rules.

Hook type: pre-tool-use
Triggers on: Write, Edit tools

Exit codes:
  0 — allow the tool use (pattern not found)
  2 — block the tool use with an error message (pattern found)

Environment variables provided by Claude Code:
  TOOL_NAME — the tool being invoked (e.g., "Write", "Edit")
  TOOL_INPUT — JSON string of the tool's input parameters

Usage in .claude/settings.json:
  "hooks": {
    "pre-tool-use": [
      {
        "matcher": "Write|Edit",
        "command": "python3 .claude/hooks/pre-tool-use/example-block.py"
      }
    ]
  }
"""

import json
import os
import sys


def main() -> None:
    tool_name = os.environ.get("TOOL_NAME", "")
    tool_input_raw = os.environ.get("TOOL_INPUT", "{}")

    # Only check Write and Edit tools
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    try:
        tool_input = json.loads(tool_input_raw)
    except json.JSONDecodeError:
        sys.exit(0)

    # Get the content being written
    content = tool_input.get("content", "") or tool_input.get("new_string", "")

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
