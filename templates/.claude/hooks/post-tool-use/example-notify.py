#!/usr/bin/env python3
"""Example post-tool-use hook: notify after a file is written.

This hook demonstrates how to run a check or notification after Claude Code
writes or edits a file. Replace the example logic with your project's needs
(e.g., run a linter, validate selectors, trigger a build).

Hook type: PostToolUse
Triggers on: Write, Edit, MultiEdit tools

Exit codes:
  0 — success (hook ran, no issues)
  1 — warning (show output but continue)

Environment variables provided by Claude Code:
  TOOL_NAME — the tool that was invoked (e.g., "Write", "Edit")
  TOOL_INPUT — JSON string of the tool's input parameters

Usage in .claude/settings.json:
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "command": "python3 .claude/hooks/post-tool-use/example-notify.py"
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

    if tool_name not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)

    try:
        tool_input = json.loads(tool_input_raw)
    except json.JSONDecodeError:
        sys.exit(0)

    file_path = tool_input.get("file_path", "")

    # --- Replace this example with your own post-write logic ---
    # Example: log which file was modified
    if file_path:
        print(f"Hook: {tool_name} applied to {file_path}", file=sys.stderr)

    # Example: run a check on specific file types
    # if file_path.endswith("_scraper.py"):
    #     import subprocess
    #     result = subprocess.run(
    #         ["python", "-m", "myproject", "check-selectors"],
    #         capture_output=True, text=True,
    #     )
    #     if result.returncode != 0:
    #         print(f"Selector check failed:\n{result.stderr}", file=sys.stderr)
    #         sys.exit(1)
    # --- End example ---

    sys.exit(0)


if __name__ == "__main__":
    main()
