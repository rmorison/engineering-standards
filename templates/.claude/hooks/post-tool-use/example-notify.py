#!/usr/bin/env python3
"""Example post-tool-use hook: notify after a file is written.

This hook demonstrates how to run a check or notification after Claude Code
writes or edits a file. Replace the example logic with your project's needs
(e.g., run a linter, validate selectors, trigger a build).

Hook type: PostToolUse
Triggers on: Write, Edit tools

Exit codes:
  0 - success (hook ran, no issues)
  2 - the hook's stderr is fed back to Claude as feedback

PostToolUse runs after the tool has already succeeded, so it cannot stop the
write - the file is on disk by the time this script starts. Exit 2 does not
undo it; it reports the problem to Claude so the next turn can act on it. Any
other non-zero exit is a non-blocking error: stderr goes to the user and the
session continues.

Input: Claude Code writes a JSON object to this script's stdin. It does not
put the tool payload in the environment. The fields used below were captured
from a running session:

  hook_event_name - "PostToolUse"
  tool_name       - "Write" or "Edit"
  tool_input      - Write: {"file_path": ..., "content": ...}
                    Edit:  {"file_path": ..., "old_string": ...,
                            "new_string": ..., "replace_all": ...}
  tool_response   - what the tool returned, including "filePath"

The environment carries CLAUDE_PROJECT_DIR (the project root), which is what
the settings entry below uses to find this file from any working directory.

Usage in .claude/settings.json - the matcher object takes a `hooks` array;
a bare `command` key on the matcher is not a valid entry. Observed under
Claude Code 2.1.278: a malformed PreToolUse entry made Claude Code reject
the whole settings file, the `permissions` block with it. That is an
observation of one version's behaviour, not a documented guarantee; the
shape below is correct regardless of whether it still holds.

  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "hook=\"${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/post-tool-use/example-notify.py\"; [ -f \"$hook\" ] || exit 0; exec python3 \"$hook\""
          }
        ]
      }
    ]
  }

Copy that command shape, not just the path. Every error path in this script
exits 0, so a mis-wired hook costs you the notification rather than the
session -- and the registration has to fail open too, or the care taken here
is undone one line above it. Two things in the command do that:

  ${CLAUDE_PROJECT_DIR:-.}  If the variable is unset OR empty, the path
                            would begin at `/`. `:-` (not `-`) covers both.
  [ -f "$hook" ] || exit 0  If the script has been moved or deleted while
                            this entry stayed behind, exit 0 and say nothing.

Without them the command is `python3 /.claude/hooks/...`, python3 cannot
open the file, and CPython exits 2. PostToolUse cannot block, so here that
only puts a spurious `can't open file` in front of Claude every time a file
is written -- but the identical entry under PreToolUse refuses every Write
and Edit in the session. The two entries are copied together and should be
written the same way. Verified under Claude Code 2.1.278 on 2026-09-22.

`exec` replaces the shell, so python3's exit code is the hook's exit code.
"""

import json
import sys


def main() -> None:
    # Absent or malformed stdin must not break the session: a mis-wired hook
    # should cost you the notification, not the ability to work.
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

    if tool_name not in ("Write", "Edit"):
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
    #         # Exit 2 reports the failure back to Claude. The write already
    #         # happened; this asks for a follow-up, it does not undo it.
    #         print(f"Selector check failed:\n{result.stderr}", file=sys.stderr)
    #         sys.exit(2)
    # --- End example ---

    sys.exit(0)


if __name__ == "__main__":
    main()
