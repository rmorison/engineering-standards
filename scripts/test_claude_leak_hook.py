#!/usr/bin/env python3
"""Proves scripts/claude_leak_hook.py denies what it must and allows the rest.

CI runs this on every pull request (.github/workflows/leaks.yml). Each fixture
feeds the hook one Claude Code PreToolUse input on standard input, as Claude
Code does, and checks three things: the exit code (2 denies, 0 allows), a
fragment of the message, and that nothing the hook printed contains a planted
value. The hook's output reaches the model, which can post it to GitHub, so a
message that repeats a value would be the leak it guards against.

Planted values are assembled at run time, so this file holds none of them. Every
fixture runs in a temporary directory, with GIT_CONFIG_GLOBAL and HOME pointed
at temporary files, so no real value list is ever read. Nothing here installs a
hook, writes under .git/hooks or sets core.hooksPath.

The list-parity fixtures also run scripts/leak-gate.sh over the same lists, so
the two read a list the same way. They set GITLEAKS to a stand-in script that
exits 0, so they need no gitleaks, and LC_ALL=C, so a value's length is counted in bytes whichever shell
is sh.

Labels such as R1, AE3 and KTD4 in section comments and fixture names refer to
docs/plans/2026-10-04-1353-feat-claude-leak-hook-plan.md.

Usage:  python3 scripts/test_claude_leak_hook.py [hook]
The optional argument runs the fixtures against another script in place of the
hook, which is how each fixture is shown to fail before it is trusted.
Exits non-zero if any fixture fails. Needs Python 3.10 or later, git and sh.
"""

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "scripts" / "claude_leak_hook.py"
LEAK_GATE = ROOT / "scripts" / "leak-gate.sh"
HOOK_TIMEOUT = 20  # seconds; one call takes well under one

# Planted values. The prefix is split so this file never holds a whole one.
CANARY_A = "cn" + "ry-a" + secrets.token_hex(4)
CANARY_B = "cn" + "ry-b" + secrets.token_hex(4)
APOS = "o'" + "cn" + "ry" + secrets.token_hex(3)
CANARIES = [CANARY_A, CANARY_B, APOS]

# The standard list: line 3 is CANARY_A, line 5 CANARY_B, line 6 APOS.
STANDARD_LIST = "\n".join(
    ["# fixture list: canaries only", "", CANARY_A, "   ", CANARY_B, APOS]
).encode() + b"\n"

BYPASS = "don't bypass"
RESIDUAL_DOC = (
    "the residual is now denied: update the residual list in "
    "process/repository-standards.md (Guarding Agent Sessions) and move this fixture"
)

passed = 0
failed = 0


def bad(name, why, result=None):
    global failed
    failed += 1
    print(f"FAIL: {name}: {why}", file=sys.stderr)
    if result is not None:
        rc, out, err = result
        print(f"    exit {rc}", file=sys.stderr)
        for line in (out + err).splitlines():
            print(f"    {line}", file=sys.stderr)


def ok():
    global passed
    passed += 1


class Sandbox:
    """A temporary HOME, global git config and working directory."""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="leak-hook-test-"))
        self.home = self.root / "home"
        self.work = self.root / "work"
        self.lists = self.root / "lists"
        for d in (self.home, self.work / "sub", self.lists):
            d.mkdir(parents=True)
        self.gitconfig = self.root / "gitconfig"
        self.gitconfig.write_text("")
        self.env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "GIT_CONFIG_GLOBAL": str(self.gitconfig),
            "GIT_CONFIG_NOSYSTEM": "1",
            "LANG": "C.UTF-8",
        }
        (self.work / "clean.md").write_text("Nothing to see here.\n")
        (self.work / "dirty.md").write_text(f"Body text.\nSee {CANARY_A.upper()} for more.\n")
        (self.work / "two.md").write_text(f"{CANARY_A}\nand\n{CANARY_B}\n")
        (self.work / "sub" / "rel.md").write_text(f"rel {CANARY_A}\n")
        (self.work / "reused.md").write_text("An old, clean body.\n")
        (self.home / "home.md").write_text(f"{CANARY_A}\n")
        locked = self.work / "locked.md"
        locked.write_text(f"{CANARY_A}\n")
        locked.chmod(0)

    def declare(self, value):
        """Declare the global list: None unsets it; a str is written as the path.

        The file is written directly: git config's own writes lock and sync the
        file, and took most of this script's run time.
        """
        if value is None:
            self.gitconfig.write_text("")
        else:
            quoted = value.replace("\\", "\\\\").replace('"', '\\"')
            self.gitconfig.write_text(f'[leakgate]\n\tvalues = "{quoted}"\n')

    def write_list(self, name, content):
        path = self.lists / name
        path.write_bytes(content)
        return str(path)

    def hook(self, command, cwd=None, tool="Bash", stdin=None, env=None):
        if stdin is None:
            stdin = json.dumps({
                "session_id": "test",
                "cwd": str(cwd or self.work),
                "hook_event_name": "PreToolUse",
                "tool_name": tool,
                "tool_input": {"command": command, "description": "fixture"},
            })
        try:
            proc = subprocess.run([sys.executable, str(HOOK)], input=stdin.encode(),
                                  capture_output=True, env=dict(self.env, **(env or {})),
                                  cwd=str(cwd or self.work), timeout=HOOK_TIMEOUT)
        except subprocess.TimeoutExpired:
            # A hook that hangs does not block the command in Claude Code, so a
            # hang fails the fixture rather than the whole run.
            return ("timeout", "", "")
        return (proc.returncode, proc.stdout.decode("utf-8", "replace"),
                proc.stderr.decode("utf-8", "replace"))

    def cleanup(self):
        (self.work / "locked.md").chmod(0o600)  # pipe.md and huge.md go with the tree
        shutil.rmtree(self.root, ignore_errors=True)


def leaked(result, extra=()):
    _, out, err = result
    text = (out + err).casefold()
    return [c for c in [*CANARIES, *extra] if c.casefold() in text]


def lines_named(err):
    m = re.search(r"list lines? ([0-9][0-9, ]*)", err)
    return {int(n) for n in re.findall(r"[0-9]+", m.group(1))} if m else None


def expect(name, good, why):
    if good:
        ok()
    else:
        bad(name, why)


def check(name, result, want, frag=None, lines=None, extra_secrets=(), on_fail=None):
    """want is 'deny', 'allow' (no output at all) or 'note' (allowed, skipped note)."""
    rc, out, err = result
    hits = leaked(result, extra_secrets)
    if hits:
        return bad(name, "a planted value appears in the hook's output")
    if want == "deny":
        if rc != 2:
            return bad(name, on_fail or f"exit {rc}, expected 2 (deny)", result)
        if BYPASS not in err:
            return bad(name, f"the denial does not end with {BYPASS!r}", result)
        if frag and frag not in err:
            return bad(name, f"the denial does not say {frag!r}", result)
        if lines is not None and lines_named(err) != set(lines):
            return bad(name, f"expected list lines {sorted(lines)}, got {lines_named(err)}", result)
    else:
        if rc != 0:
            return bad(name, on_fail or f"exit {rc}, expected 0 (allow)", result)
        if "permissionDecision" in out:
            return bad(name, "an allowed call printed a permission decision", result)
        if want == "allow" and (out.strip() or err.strip()):
            return bad(name, "an allowed call printed output", result)
        if want == "note":
            try:
                note = json.loads(out).get("systemMessage", "")
            except ValueError:
                note = ""
            if "value rules skipped" not in note:
                return bad(name, "no 'value rules skipped' note in systemMessage", result)
    ok()


def run_leak_gate(sb, repo, list_path):
    # leak-gate.sh refuses a GITLEAKS that is not an executable file before it
    # reads the list, so the stand-in is a script that exits 0.
    fake = sb.root / "fake-gitleaks"
    if not fake.exists():
        fake.write_text("#!/bin/sh\nexit 0\n")
        fake.chmod(0o755)
    env = dict(sb.env, GITLEAKS=str(fake), LC_ALL="C")
    env.pop("LANG", None)
    sb.declare(list_path)
    proc = subprocess.run(["sh", str(LEAK_GATE), "staged"], capture_output=True,
                          env=env, cwd=str(repo))
    return proc.returncode, proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")


def scratch_repo(sb, name):
    repo = sb.root / name
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "--template=", str(repo)], check=True, env=sb.env)
    return repo


def main():
    sb = Sandbox()
    try:
        fixtures(sb)
    finally:
        sb.cleanup()
    print(f"claude leak hook fixtures: {passed} passed, {failed} failed")
    return 1 if failed else 0


def fixtures(sb):
    A, B = CANARY_A, CANARY_B
    standard = sb.write_list("standard", STANDARD_LIST)
    root = os.geteuid() == 0

    # --- Outbound text: denied with the list line, never the value (R1, R8) ----
    sb.declare(standard)
    denied = [
        ("AE1: body file, value in upper case", "gh pr create --title t --body-file dirty.md", {3}),
        ("issue comment, inline body", f'gh issue comment 1 --body "see {A}"', {3}),
        ("api PATCH with -f", f"gh api -X PATCH repos/o/r/issues/1 -f body=x{A}x", {3}),
        ("value in the title only", f'gh pr create --title "{A}" --body-file clean.md', {3}),
        ("upper-cased inline value", f'gh issue comment 1 --body "{A.upper()}"', {3}),
        ("api -F key=@file", "gh api repos/o/r/issues/1/comments -F body=@dirty.md", {3}),
        ("api --input file", "gh api repos/o/r/issues/1/comments --input dirty.md", {3}),
        ("body file from stdin redirect", "gh pr comment 1 --body-file - < dirty.md", {3}),
        ("AE2: heredoc, gh on its own line",
         f"cat > new.md <<'EOF'\n{A}\nEOF\ngh pr create --body-file new.md", {3}),
        ("AE2: heredoc, gh on the opening line",
         f"cat > new.md <<'EOF' && gh pr create --body-file new.md\n{A}\nEOF", {3}),
        ("cd, then a relative body file", "cd sub && gh pr comment 1 -F rel.md", {3}),
        ("bash -c", f"bash -c 'gh issue comment 1 --body {A}'", {3}),
        ("gh by full path", f"/usr/bin/gh issue comment 1 --body {A}", {3}),
        ("release notes file", "gh release create v1 --notes-file dirty.md", {3}),
        ("pr review -b", f"gh pr review 1 --comment -b {A}", {3}),
        ("issue new (alias of create)", f"gh issue new --title t --body {A}", {3}),
        ("issue close --comment", f"gh issue close 1 --comment {A}", {3}),
        ("pr reopen -c", f"gh pr reopen 1 -c {A}", {3}),
        ("timeout wrapper", f"timeout 60 gh issue comment 1 --body {A}", {3}),
        ("--body-file=F", "gh pr create --title t --body-file=dirty.md", {3}),
        ("--input=F", "gh api repos/o/r/issues --input=dirty.md", {3}),
        ("-XPATCH with --raw-field=", f"gh api -XPATCH repos/o/r/issues/1 --raw-field=body=x{A}", {3}),
        ("--method= with --field=", f"gh api --method=PATCH repos/o/r/issues/1 --field=body=x{A}", {3}),
        ("apostrophe value written with '\\'' quoting",
         "gh issue comment 1 --body 'thanks " + APOS.replace("'", "'\\''") + "'", {6}),
        ("backslash-newline continuation", "gh pr create --title t \\\n  --body-file dirty.md", {3}),
        ("two values in one body", "gh issue comment 1 --body-file two.md", {3, 5}),
        ("unbalanced quote falls back to the raw text", f'gh issue comment 1 --body "{A}', {3}),
        ("pr edit", "gh pr edit 1 --body-file dirty.md", {3}),
        ("issue edit", "gh issue edit 1 --body-file dirty.md", {3}),
        ("release edit", "gh release edit v1 --notes-file dirty.md", {3}),
        ("pr new", "gh pr new --title t --body-file dirty.md", {3}),
        ("release new", "gh release new v1 --notes-file dirty.md", {3}),
        ("pr close --comment", f"gh pr close 1 --comment {A}", {3}),
        ("attached -F file", "gh issue comment 1 -Fdirty.md", {3}),
        ("body file under ~", "gh pr comment 1 --body-file ~/home.md", {3}),
        ("/dev/stdin with a redirect", "gh pr comment 1 --body-file /dev/stdin < dirty.md", {3}),
        ("api --input /dev/stdin", "gh api repos/o/r/issues --input /dev/stdin < dirty.md", {3}),
        ("-R between group and verb", "gh issue -R o/r comment 1 --body-file dirty.md", {3}),
        ("--repo= between group and verb", "gh pr --repo=o/r comment 1 --body-file dirty.md", {3}),
        ("after if/then", f"if true; then gh pr comment 1 --body {A}; fi", {3}),
        ("after for/do", "for f in a; do gh issue comment 1 --body-file dirty.md; done", {3}),
        ("inside { }", f"{{ gh issue comment 1 --body {A}; }}", {3}),
        ("after else", "if gh pr view 1; then gh pr edit 1 --body-file clean.md; "
                       "else gh pr create --body-file dirty.md; fi", {3}),
        ("# comment with an apostrophe after the command",
         "gh pr comment 1 --body-file dirty.md # it's done", {3}),
        ("# comment with an apostrophe on the line before",
         "# don't forget\ngh pr comment 1 --body-file dirty.md", {3}),
        ('quoted $(gh ...)', 'url="$(gh pr create --title t --body-file dirty.md)"', {3}),
        ("backticks in double quotes", 'echo "Created `gh pr create --title t --body-file dirty.md`"', {3}),
        ("unquoted backticks", "echo `gh pr create --title t --body-file dirty.md`", {3}),
    ]
    for name, command, lines in denied:
        check(name, sb.hook(command), "deny", "matches private value list line", lines)

    if root:
        print("note: running as root, so the unreadable-file fixtures are skipped")
    else:
        check("a named file that cannot be read", sb.hook("gh issue comment 1 --body-file locked.md"),
              "deny", "cannot be read")
    os.mkfifo(sb.work / "pipe.md")
    with open(sb.work / "huge.md", "wb") as f:
        f.truncate(11 * 1024 * 1024)
    unbounded = [
        ("a FIFO as the body file", "gh pr comment 1 --body-file pipe.md", "not a regular file"),
        ("/dev/zero as the body file", "gh pr comment 1 --body-file /dev/zero", "not a regular file"),
        ("/dev/zero through a stdin redirect", "gh pr comment 1 --body-file - < /dev/zero",
         "not a regular file"),
        ("a body file over 10 MiB", "gh pr comment 1 --body-file huge.md", "larger than 10 MiB"),
    ]
    for name, command, frag in unbounded:
        check(name, sb.hook(command), "deny", frag)
    check("a named file that does not exist yet",
          sb.hook("cp clean.md gone.md && gh pr comment 1 --body-file gone.md"),
          "deny", "does not exist yet")
    written = [
        ("an existing body file overwritten by cp", "cp dirty.md reused.md && gh pr create --body-file reused.md"),
        ("an existing body file overwritten by a redirect",
         "cat dirty.md > reused.md && gh pr comment 1 --body-file reused.md"),
        ("a heredoc-written file then appended to",
         "cat > new.md <<'EOF'\nclean\nEOF\ncat dirty.md >> new.md\ngh pr create --body-file new.md"),
        ("an unbalanced quote with a body file", 'gh pr comment 1 --body-file clean.md --title "x'),
        ("a heredoc plus another input file",
         "cat dirty.md - > new.md <<'EOF'\nclean\nEOF\ngh pr create --body-file new.md"),
        ("a heredoc replaced by a later < file",
         "cat > new.md <<'EOF' < dirty.md\nclean\nEOF\ngh pr create --body-file new.md"),
    ]
    for name, command in written:
        check(name, sb.hook(command), "deny", "cannot be")

    # --- Clean text is allowed, with no decision of the hook's own (R2) ---------
    allowed = [
        ("clean body file", "gh pr create --title t --body-file clean.md"),
        ("clean inline body", 'gh issue comment 1 --body "all good"'),
        ("clean api PATCH", "gh api -X PATCH repos/o/r/issues/1 -f body=fine"),
        ("clean api --input", "gh api repos/o/r/issues --input clean.md"),
        ("clean heredoc, AE2 shape", "cat > new.md <<'EOF'\nclean\nEOF\ngh pr create --body-file new.md"),
        ("clean issue close --comment", "gh issue close 1 --comment done"),
        ("clean release notes", "gh release create v1 --notes-file clean.md"),
        ("clean issue create", "gh issue create --title t --body-file clean.md"),
        ("clean pr edit", "gh pr edit 1 --body-file clean.md"),
        ("clean issue edit", "gh issue edit 1 --body-file clean.md"),
        ("clean pr review", "gh pr review 1 --comment --body-file clean.md"),
        ("clean release edit", "gh release edit v1 --notes-file clean.md"),
        # Not outbound, so not scanned even though the value is present.
        ("echo is not outbound", f"echo {A}"),
        ("gh issue view is not outbound", f"echo {A} && gh issue view 1"),
        ("gh api GET is not outbound", f"gh api repos/o/r/issues?q={A}"),
        ("git log is not outbound", f"git log --grep {A}"),
        ("api -f key=@text is text, not a file",
         "gh api -X POST repos/o/r/issues/1/comments -f 'body=@someone please look'"),
        ("# comment with an apostrophe, clean body", "gh pr comment 1 --body-file clean.md # it's fine"),
        ("single-quoted backticks are literal",
         "gh issue comment 1 --body 'never run `git commit --no-verify`'"),
    ]
    for name, command in allowed:
        check(name, sb.hook(command), "allow")

    # Mixed-case values match in any case.
    mixed = "Cn" + "Ry-Mixed" + secrets.token_hex(3)
    sb.declare(sb.write_list("mixed", f"{mixed}\n".encode()))
    for variant in (mixed.lower(), mixed.upper()):
        check("a mixed-case list value matches " + ("lower" if variant.islower() else "upper") + " case",
              sb.hook(f"gh issue comment 1 --body {variant}"), "deny",
              "matches private value list line", {1}, extra_secrets=[mixed])
    sb.declare(standard)

    # --- Global list only (R3, AE3) ---------------------------------------------
    repo = scratch_repo(sb, "local-none")
    subprocess.run(["git", "-C", str(repo), "config", "--local", "leakgate.values", "none"],
                   check=True, env=sb.env)
    check("AE3: a clone's local 'none' does not switch the hook off",
          sb.hook(f"gh issue comment 1 --body {A}", cwd=repo), "deny",
          "matches private value list line", {3})

    # --- The list declared with ~/, and failures that must deny (KTD6) ---------
    (sb.home / "lists").mkdir()
    shutil.copy(standard, sb.home / "lists" / "standard")
    sb.declare("~/lists/standard")
    check("a list declared under ~/", sb.hook(f"gh issue comment 1 --body {A}"), "deny",
          "matches private value list line", {3})
    sb.gitconfig.write_text("[leakgate\n")
    check("an unreadable git config denies outbound", sb.hook("gh issue comment 1 --body hi"),
          "deny", "could not read")
    sb.declare(standard)
    check("git missing from PATH denies outbound", sb.hook("gh issue comment 1 --body hi",
          env={"PATH": str(sb.root / "empty")}), "deny", "could not be run")
    # JSON nested past the parser's recursion limit raises RecursionError, an
    # error the hook does not expect, so this exercises its catch-all.
    check("an unexpected hook error denies", sb.hook("", stdin="[" * 100000), "deny", "the hook failed")

    # --- List states (R6, R7, AE5) ----------------------------------------------
    out_cmd = "gh issue comment 1 --body hello"
    sb.declare(None)
    check("no list declared: outbound allowed with a note", sb.hook(out_cmd), "note")
    sb.declare("none")
    check("global 'none': outbound allowed with a note", sb.hook(out_cmd), "note")

    empty = sb.write_list("empty", b"")
    comments = sb.write_list("comments", b"# only a comment\n\n")
    unreadable = sb.write_list("unreadable", STANDARD_LIST)
    os.chmod(unreadable, 0)
    broken = [
        ("declared list missing", str(sb.lists / "missing"), "does not exist"),
        ("declared list is a directory", str(sb.lists), "does not exist"),
        ("declared list empty", empty, "has no values"),
        ("declared list holds only comments", comments, "has no values"),
        ("declared list path is relative", "lists/standard", "absolute"),
    ]
    if not root:
        broken.append(("declared list unreadable", unreadable, "cannot be read"))
    for name, path, frag in broken:
        sb.declare(path)
        check(f"{name}: outbound denied", sb.hook(out_cmd), "deny", frag)
        check(f"{name}: non-outbound allowed", sb.hook("gh issue view 1"), "allow")
    sb.declare(str(sb.lists / "missing"))
    check("AE5: missing list, gh issue close without a comment is allowed",
          sb.hook("gh issue close 1"), "allow")
    os.chmod(unreadable, 0o600)

    # --- List parity with leak-gate.sh (KTD4) -----------------------------------
    repo = scratch_repo(sb, "parity")
    shutil.copy(ROOT / ".gitleaks.toml", repo / ".gitleaks.toml")
    invalid = [
        ("shorter than 4 bytes", b"abc"),
        ("holds \\E", b"abc\\Edef"),
        ("holds '''", b"ab'''cd"),
        ("holds a control character", b"abc\x01def"),
        ("not valid UTF-8", b"abc\xffdef"),
        ("leading no-break space", " abcdef".encode()),
        ("trailing ideographic space", "abcdef　".encode()),
        ("leading U+2005 space", " abcdef".encode()),
    ]
    for name, line in invalid:
        path = sb.write_list("invalid", b"# parity\n" + line + b"\n")
        rc, out = run_leak_gate(sb, repo, path)  # declares path as the list
        expect(f"parity, {name}: leak-gate.sh", rc == 2 and "value list line 2" in out,
               f"exit {rc}, expected 2 naming line 2: {out.strip()}")
        check(f"parity, {name}: hook", sb.hook(out_cmd), "deny", "value list line 2")

    accepted = [
        ("a 2-character, 4-byte value", "éé".encode() + b"\n",
         'gh issue comment 1 --body "xÉÉx"', {1}, ["éé"]),
        ("CRLF line ends", b"# c\r\n" + A.encode() + b"\r\n" + B.encode() + b"\r\n",
         f"gh issue comment 1 --body {B}", {3}, []),
        ("lone CR line ends", b"# c\r" + A.encode() + b"\r" + B.encode(),
         f"gh issue comment 1 --body {B}", {3}, []),
        ("byte-order mark", b"\xef\xbb\xbf" + A.encode() + b"\n",
         f"gh issue comment 1 --body {A}", {1}, []),
        ("inner tab", b"cn\t" + B.encode() + b"\n",
         f'gh issue comment 1 --body "cn\t{B}"', {1}, []),
    ]
    for name, content, command, lines, extra in accepted:
        path = sb.write_list("accepted", content)
        rc, out = run_leak_gate(sb, repo, path)  # declares path as the list
        expect(f"parity, {name}: leak-gate.sh", rc == 0, f"exit {rc}, expected 0: {out.strip()}")
        check(f"parity, {name}: hook matches the value", sb.hook(command), "deny",
              "matches private value list line", lines, extra_secrets=extra)

    # --- Gate escapes (R4), with no list and with a broken list -----------------
    escapes = [
        ("git commit --no-verify", "git commit --no-verify -m x", "--no-verify"),
        ("git commit -n", "git commit -n -m x", "git commit -n"),
        ("git push --no-verify", "git push --no-verify", "--no-verify"),
        ("git merge --no-verify", "git merge --no-verify topic", "--no-verify"),
        ("git -C d commit --no-verify", "git -C d commit --no-verify", "--no-verify"),
        ("cd && git commit -n", "cd d && git commit -n", "git commit -n"),
        ("git -c core.hooksPath=", "git -c core.hooksPath=/dev/null commit -m x", "core.hooksPath"),
        ("key compared case-insensitively", "git -c CORE.HOOKSPATH=x commit", "core.hooksPath"),
        ("git --config-env=", "git --config-env=core.hooksPath=V commit", "core.hooksPath"),
        ("git config core.hooksPath value", "git config core.hooksPath /dev/null", "core.hooksPath"),
        ("git config --global core.hooksPath", "git config --global core.hooksPath x", "core.hooksPath"),
        ("git config set core.hooksPath", "git config set core.hooksPath x", "core.hooksPath"),
        ("SKIP= on git", "SKIP=leak-gate git commit -m x", "SKIP="),
        ("SKIP= on pre-commit", "SKIP=x pre-commit run", "SKIP="),
        ("env SKIP=", "env SKIP=x git commit -m x", "SKIP="),
        ("export SKIP=", "export SKIP=x", "SKIP="),
        ("sh -c", "sh -c 'git commit -n'", "git commit -n"),
        ("timeout wrapper", "timeout 60 git commit -n", "git commit -n"),
        ("next line after git status", "git status\ngit commit -n", "git commit -n"),
        ("next line after cd", "cd d\ngit commit -n", "git commit -n"),
        ("# inside a word", "git commit -m fix#1 --no-verify", "--no-verify"),
        ("unbalanced quote falls back to the raw text", 'git commit --no-verify -m "x', "--no-verify"),
        ("after if/then", "if true; then git commit -n; fi", "git commit -n"),
        ("after !", "! git commit -n -m x", "git commit -n"),
        ("inside { }", "{ git commit --no-verify -m x; }", "--no-verify"),
        ("retry after a failed commit", "if ! git commit -m x; then git commit --no-verify -m x; fi",
         "--no-verify"),
        ("export SKIP after setting it", "SKIP=leak-gate; export SKIP", "SKIP="),
        ("git -C d commit -n", "git -C d commit -n -m x", "git commit -n"),
        ("git -c other config, commit -n", "git -c user.name=x commit -n", "git commit -n"),
        ("git config --add core.hooksPath", "git config --add core.hooksPath x", "core.hooksPath"),
        ("git config --file f core.hooksPath", "git config --file f core.hooksPath x", "core.hooksPath"),
        ("after a here-string", "cat <<< x\ngit commit -n", "git commit -n"),
        ("# comment with an apostrophe", "git commit -n -m x # it's fine", "git commit -n"),
    ]
    for state, value in (("no list", None), ("broken list", str(sb.lists / "missing"))):
        sb.declare(value)
        for name, command, frag in escapes:
            check(f"escape ({state}): {name}", sb.hook(command), "deny", frag)

    # --- Lookalikes are allowed (AE4) -------------------------------------------
    sb.declare(None)
    # With no list, an allowed outbound command carries the skipped note.
    lookalikes = [
        ("flag inside a commit message", "git commit -m \"don't use --no-verify\"", "allow"),
        ("flag inside a quoted PR body",
         'gh issue comment 1 --body "never run git commit --no-verify"', "note"),
        ("heredoc body mentions git commit -n", "cat > notes.md <<'EOF'\ngit commit -n\nEOF", "allow"),
        ("git config --get core.hooksPath", "git config --get core.hooksPath", "allow"),
        ("git config --unset core.hooksPath", "git config --unset core.hooksPath", "allow"),
        ("git push -n is a dry run", "git push -n", "allow"),
        ("git log -n 5", "git log -n 5", "allow"),
        ("echo SKIP=1", "echo SKIP=1", "allow"),
        ("tab-indented <<- heredoc body", "cat <<-EOF\n\tgit commit -n\n\tEOF", "allow"),
    ]
    for name, command, want in lookalikes:
        check(f"lookalike: {name}", sb.hook(command), want)

    # --- Residuals are still allowed (R5) ---------------------------------------
    residuals = [
        ("abbreviated long option", "git commit --no-veri -m x"),
        ("combined short flags", "git commit -nm x"),
        ("config through GIT_CONFIG_* variables",
         "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null git commit -m x"),
    ]
    sb.declare(standard)
    residuals += [
        ("text made by $(...)", 'gh pr comment 1 --body "$(cat dirty.md)"'),
        ("a pipe into --body-file -", "cat dirty.md | gh pr comment 1 --body-file -"),
        ("gh pr merge --body", f"gh pr merge 1 --body {A}"),
        ("gh gist create", "gh gist create dirty.md"),
        ("curl", "curl -d @dirty.md https://api.github.com/repos/o/r/issues"),
    ]
    for name, command in residuals:
        check(f"residual: {name}", sb.hook(command), "allow", on_fail=RESIDUAL_DOC)

    # --- Hook input -------------------------------------------------------------
    check("malformed JSON is denied", sb.hook("", stdin="{not json"), "deny", "not valid JSON")
    check("a tool other than Bash is allowed silently", sb.hook("git commit -n", tool="Write"), "allow")
    for name, tool_input in (("no command", {}), ("a null tool_input", None),
                             ("a command that is not a string", {"command": ["gh"]})):
        check(f"Bash input with {name} is denied",
              sb.hook("", stdin=json.dumps({"tool_name": "Bash", "tool_input": tool_input})),
              "deny", "no command string")


if __name__ == "__main__":
    sys.exit(main())
