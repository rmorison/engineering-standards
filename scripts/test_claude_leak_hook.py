#!/usr/bin/env python3
"""Proves scripts/claude_leak_hook.py denies what it must and allows the rest.

CI runs this on every pull request (.github/workflows/agent-hooks.yml). Each fixture
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

    # --- Words that only name a file or directory are not matched (#84) ---------
    # D is a directory whose name holds a listed value, as a home directory or
    # scratchpad path can. The path never reaches GitHub; text and contents do.
    D = sb.root / f"d-{A}-one"
    D.mkdir()
    (D / "clean.md").write_text("Nothing to see here.\n")
    (D / "dirty.md").write_text(f"See {A}.\n")
    path_allowed = [
        ("an absolute body file under a listed path", f"gh pr create --title t --body-file {D}/clean.md"),
        ("cd into a listed path", f"cd {D} && gh pr comment 1 --body-file clean.md"),
        ("a heredoc written under a listed path",
         f"cat > {D}/new.md <<'EOF'\nclean\nEOF\ngh pr create --body-file {D}/new.md"),
        ("--notes-file under a listed path", f"gh release create v1 --notes-file {D}/clean.md"),
        ("--input under a listed path", f"gh api repos/o/r/issues --input {D}/clean.md"),
        ("api -F key=@ under a listed path", f"gh api repos/o/r/issues/1/comments -F body=@{D}/clean.md"),
        ("attached -F under a listed path", f"gh issue comment 1 -F{D}/clean.md"),
        ("stdin redirect from a listed path", f"gh pr comment 1 --body-file - < {D}/clean.md"),
        ("a listed path inside $(gh ...)", f'url="$(gh pr create --title t --body-file {D}/clean.md)"'),
        ("a listed path inside bash -c", f"bash -c 'cd {D} && gh pr comment 1 --body-file clean.md'"),
        ("a listed path after an unquoted $(...)",
         f"gh pr create --title $(git log -1 --format=%s) --body-file {D}/clean.md"),
    ]
    for name, command in path_allowed:
        check(name, sb.hook(command), "allow")
    path_denied = [
        ("an absolute body file under a listed path, value inside", f"gh pr comment 1 --body-file {D}/dirty.md"),
        ("value in the title beside an absolute body file",
         f'gh pr create --title "{A}" --body-file {D}/clean.md'),
        ("value in the body beside an absolute body file",
         f'gh pr create --title t --body "{A}" --body-file {D}/clean.md'),
        ("value as an api -F key", f"gh api repos/o/r/issues/1/comments -F {A}=@clean.md"),
        ("api -F value with =@ after its first =, sent as written",
         f"gh api repos/o/r/issues/1/comments -F body=see=@{D}/clean.md"),
        ("single-quoted $(...) is text", f"gh issue comment 1 --body 'literal $({A})'"),
        ("heredoc inside --body $(cat ...)", f"gh pr comment 1 --body \"$(cat <<'EOF'\n{A}\nEOF\n)\""),
        ("$'...' body the comment stripper cuts",
         "gh pr comment 1 --body $'Fixed.\\nIt\\'s tested, part of #84.\\nSeen at " + A + ".'"),
        ("unquoted $(...)# the comment stripper cuts", f"gh pr comment 1 --body $(echo hi)#{A}"),
        ("here-string into --body-file -", f'gh pr comment 1 --body-file - <<< "{A}"'),
        ("echo piped into --body-file -", f"echo {A} | gh pr comment 1 --body-file -"),
        ("value in a variable", f'X={A}; gh issue comment 1 --body "$X"'),
        ("value in a wrapper option", f'env -S "echo {A}" | gh pr comment 1 --body-file -'),
        ("release asset under a listed path (gh sends its name)",
         f"gh release create v1 {D}/clean.md --notes-file clean.md"),
        ("git -C under a listed path is still matched",
         f"git -C {D} status && gh pr comment 1 --body-file clean.md"),
        ("unbalanced quote after a cd into a listed path", f'cd {D} && gh issue comment 1 --body "x'),
        ("value in a substitution that is not gh", f'gh issue comment 1 --body "$(echo {A})"'),
        # Unquoted, the parentheses of $(...) used to split the command, so the
        # options after it formed a command of their own and the file went unread.
        ("body file after an unquoted $(...)",
         "gh pr create --title $(git log -1 --format=%s) --body-file dirty.md"),
        ("body file after an unquoted $(...) in --body",
         "gh pr comment 1 --body $(git log -1 --format=%s) --body-file dirty.md"),
        ("body file after an unquoted $(...) as the number",
         "gh pr comment $(gh pr view --json number -q .number) --body-file dirty.md"),
        ("body file after unquoted backticks",
         "gh pr create --title `git log -1 --format=%s` --body-file dirty.md"),
        ("body file after nested unquoted $(...)",
         "gh pr create --title $(echo $(git log -1 --format=%s)) --body-file dirty.md"),
        ("body file after an attached --title=$(...)",
         "gh pr create --title=$(git log -1 --format=%s) --body-file dirty.md"),
        ("api --input after an unquoted $(...) in the endpoint",
         "gh api repos/o/r/issues/$(echo 1)/comments --input dirty.md"),
        ("api -F key=@ after an unquoted $(...) in the endpoint",
         "gh api repos/o/r/issues/$(echo 1)/comments -F body=@dirty.md"),
        ("notes file after an unquoted $(...)", "gh release create v1 --notes $(date) --notes-file dirty.md"),
        # A heredoc the stripper cannot follow must not leave its body to be read
        # as commands, where "> name" puts the name in a redirect target.
        ("<<\\EOF heredoc body", f"gh pr comment 1 --body-file - <<\\EOF\nrenamed it -> {A}\nEOF"),
        ("heredoc with a delimiter the stripper does not read",
         f"gh pr comment 1 --body-file - <<'END BODY'\nrenamed it -> {A}\nEND BODY"),
        ("heredoc with no terminator", f"gh pr comment 1 --body-file - <<'EOF'\nrenamed it -> {A}\n  EOF"),
        ("$'...' body with > before the value", "gh pr comment 1 --body $'It\\'s for > " + A + ", see #84.'"),
    ]
    for name, command in path_denied:
        check(name, sb.hook(command), "deny", "matches private value list line", {3})
    # The parenthesis inside the quotes leaves the $(...) open as the hook counts,
    # so the options after it would never reach the gh command.
    check("a $(...) the hook cannot close", sb.hook(
        'gh pr create --title $(echo "fix (wip") --body-file dirty.md'), "deny", "does not close")

    # --- Directory changes the hook follows, and says when it can't (R7) ----------
    P = sb.root / "pushed"
    P.mkdir()
    (P / "same.md").write_text(f"{A}\n")
    (sb.work / "same.md").write_text("A clean file with the same name.\n")
    for twin in ("two1", "two2"):
        (sb.root / f"d-{A}-{twin}").mkdir()
    check("cd to a glob matching one directory",
          sb.hook(f"cd {sb.root}/d-*-one && gh pr comment 1 --body-file clean.md"), "allow")
    check("pushd into a listed path", sb.hook(f"pushd {D} && gh pr comment 1 --body-file clean.md"), "allow")
    check("pushd, then popd back", sb.hook(f"pushd {P} && popd && gh pr comment 1 --body-file same.md"),
          "allow")
    check("pushd, then a relative body file there", sb.hook(f"pushd {P} && gh pr comment 1 --body-file same.md"),
          "deny", "matches private value list line", {3})
    unfollowed = "could not follow a change of directory"
    check("cd to a glob matching two directories",
          sb.hook(f"cd {sb.root}/d-*-two? && gh pr comment 1 --body-file clean.md"), "deny", unfollowed)
    check("popd with nothing pushed", sb.hook("popd; gh pr comment 1 --body-file clean.md"), "deny",
          unfollowed)
    check("cd -", sb.hook("cd - && gh pr comment 1 --body-file clean.md"), "deny", unfollowed)
    check("cd to a variable", sb.hook('cd "$SCRATCH" && gh pr comment 1 --body-file clean.md'), "deny",
          unfollowed)

    # --- In-place editors are same-command writes (#87) -------------------------
    then_post = " && gh pr comment 1 --body-file reused.md"
    in_place = [
        "sed -i 's/a/b/' reused.md",
        "gsed -i 's/a/b/' reused.md",
        "sed -i.bak 's/a/b/' reused.md",
        "sed --in-place 's/a/b/' reused.md",
        "sed --in-place=.bak 's/a/b/' reused.md",
        "sed -Ei 's/a/b/' reused.md",
        "sed -i '' 's/a/b/' reused.md",
        "perl -i -pe 's/a/b/' reused.md",
        "perl -pi -e 's/a/b/' reused.md",
        "perl -i.bak -pe 's/a/b/' reused.md",
        "sed -i 's/a/b/' *.md",
        'F=reused.md; sed -i \'s/a/b/\' "$F"',
    ]
    for edit in in_place:
        check(f"in-place edit: {edit}", sb.hook(edit + then_post), "deny", "written by the same command")
    check("sed without -i is not a write", sb.hook("sed -n p reused.md" + then_post), "allow")
    check("sed -i on another file", sb.hook("sed -i 's/a/b/' clean.md" + then_post), "allow")

    # --- An interpreter in the command can rewrite any body file (#111) ----------
    # reused.md is clean, so each is allowed unless the interpreter counts as a write.
    interpreted = "An interpreter"
    interpreters = [
        "python3 - <<'PYEOF'\np = 'reused.md'\nopen(p, 'w').write(open(p).read())\nPYEOF\n",
        "python3 -c 'open(\"reused.md\", \"a\")'; ",
        "python -c 1 && ",
        "python3.12 -c 1 && ",
        "node -e 1 && ",
        "nodejs -e 1 && ",
        "deno eval 1 && ",
        "bun -e 1 && ",
        "perl -e 1 && ",
        "ruby -e 1 && ",
        "php -r 1; ",
        "awk 'BEGIN{}' && ",
        "awk -i inplace '{print}' reused.md && ",
        "bash fix.sh && ",
        "sh <<'EOF'\nsed -i s/a/b/ reused.md\nEOF\n",
        "./fix.py && ",
        "./fix.rb && ",
        "tools/fix.mjs && ",
        "source fix.sh && ",
        ". ./fix.sh; ",
        "pypy3 -c 1 && ",
        "lua5.4 -e 1 && ",
        "luajit -e 1 && ",
        "Rscript -e 1 && ",
        "gawk 'BEGIN{}' && ",
        "scripts/edit.sh && ",
        "env FOO=1 python3 -c 1 && ",
        "timeout 5 node -e 1 && ",
        "bash -c 'python3 -c 1' && ",
        "n=$(python3 -c 'print(1)'); ",
        # From the review of #117: the hiding places it named.
        "bash fix.sh -c x; ",
        "sh gen.sh -config prod && ",
        "PY=$(which python3); $PY fix.py; ",
        '"$(which python3)" fix.py && ',
        '"$SHELL" fix.sh && ',
        'bash -c "$CMD" && ',
        'eval "$CMD"; ',
        "env -S 'python3 fix.py' && ",
        "env --split-string='python3 fix.py' && ",
        "function f { python3 fix.py; }; f; ",
        "coproc python3 fix.py; ",
        "builtin source fix.sh; ",
        "sh -c \"sh -c \\\"sh -c 'eval python3 fix.py'\\\"\"; ",
        "ruby3.1 -e 1 && ",
        "Python3 -c 1 && ",
        "./FIX.PY && ",
        "./fix.zsh && ",
        "eval python3 fix.py; ",
        "x=`python3 -c 1`; ",
        "sudo python3 fix.py && ",
        "nohup python3 fix.py && ",
        "nice -n 5 python3 fix.py && ",
        "command python3 fix.py && ",
        "time python3 fix.py && ",
        # From the fix-delta review of #117.
        "coproc P { python3 fix.py; }; ",
        "bash -euo pipefail -c 'python3 fix.py' && ",
        # From the second fix-delta review of #117: a startup file runs too.
        "bash --rcfile fix.sh -i; ",
        "BASH_ENV=fix.sh bash -c 'echo hi' && ",
        "ENV=fix.sh sh -c 'echo hi' && ",
        # From the third fix-delta review of #117: a startup file set without a prefix.
        "export BASH_ENV=fix.sh; bash -c 'echo hi'; ",
        "declare -x BASH_ENV=fix.sh; bash -c 'echo hi'; ",
        "export ENV=fix.sh; sh -c 'echo hi'; ",
        "ZDOTDIR=. zsh -c 'echo hi' && ",
    ]
    posts = [
        "gh pr edit 1 --body-file reused.md",
        "gh pr comment 1 -F reused.md",
        "gh issue create --title t --body-file reused.md",
        "gh release create v1 --notes-file reused.md",
        "gh api repos/o/r/issues/1/comments --input reused.md",
        "gh api repos/o/r/issues/1/comments -F body=@reused.md",
    ]
    for run in interpreters:
        check(f"interpreter: {run.splitlines()[0].strip(' &;')}", sb.hook(run + posts[0]), "deny", interpreted)
    for post in posts[1:]:
        for run in ("python3 -c 1 && ", "node -e 1 && ", "perl -e 1 && ", "ruby -e 1 && ",
                    "python3 - <<'PYEOF'\nprint(1)\nPYEOF\n"):
            check(f"interpreter: {run.splitlines()[0].strip(' &;')}, then {post}", sb.hook(run + post), "deny",
                  interpreted)
    check("interpreter after the post", sb.hook(posts[0] + " && python3 -c 1"), "deny", interpreted)
    check("interpreter beside a file written from a heredoc",
          sb.hook("cat > new.md <<'EOF'\nclean\nEOF\npython3 -c 1 && gh pr create --body-file new.md"),
          "deny", interpreted)
    check("interpreter inside >(...)", sb.hook("gh pr comment 1 --body-file clean.md 2> >(python3 -c 1)"),
          "deny", interpreted)
    no_file = [
        ("interpreter, not outbound", "python3 -c 'print(1)' && node -e 1"),
        ("interpreter and gh view", "python3 -c 1 && gh pr view 1"),
        ("interpreter and an inline --body", "python3 -c 1 && gh pr comment 1 --body 'all good'"),
        ("interpreter and an api -f field", "node -e 1 && gh api -X PATCH repos/o/r/issues/1 -f body=fine"),
        ("interpreter and close --comment", "python3 -c 1 && gh issue close 1 --comment done"),
        ("sh -c is parsed, not an interpreter", "sh -c 'echo hi' && gh pr comment 1 --body-file clean.md"),
        ("bash -o pipefail -c is parsed, not an interpreter",
         "bash -o pipefail -c 'echo hi' && gh pr comment 1 --body-file clean.md"),
        ("env -S is parsed, not an interpreter", "env -S 'echo hi' && gh pr comment 1 --body-file clean.md"),
        ("bash -lc is parsed, not an interpreter", "bash -lc 'echo hi' && gh pr comment 1 --body-file clean.md"),
        ("bash -euo pipefail -c is parsed, not an interpreter",
         "bash -euo pipefail -c 'echo hi' && gh pr comment 1 --body-file clean.md"),
        ("interpreter named as a word", "echo python3 && gh pr comment 1 --body-file clean.md"),
        ("interpreter in a comment", "gh pr comment 1 --body-file clean.md # then python3 -c 1"),
        ("interpreter in a heredoc body", "cat > new.md <<'EOF'\npython3 -c 1\nEOF\ngh pr create --body-file new.md"),
    ]
    for name, command in no_file:
        check(name, sb.hook(command), "allow")
    check("interpreter beside an inline --body holding a value",
          sb.hook(f"python3 -c 1 && gh pr comment 1 --body {A}"), "deny", "matches private value list line",
          {3})

    # --- <(...) and >(...) no longer split a gh command (#95) --------------------
    # Unparsed, the parentheses put the options after them in a command of their own.
    after_substitution = [
        ("body file after 2> >(...)", "gh pr create --title t 2> >(tee err.log) --body-file dirty.md"),
        ("body file after < <(...)", "gh pr create --title t < <(echo y) --body-file dirty.md"),
        ("body file after a <(...) argument", "gh pr create --assignee <(echo me) --body-file dirty.md"),
        ("notes file after >(...)", "gh release create v1 > >(tee out.log) --notes-file dirty.md"),
        ("api --input after <(...)", "gh api repos/o/r/issues/1/comments < <(echo y) --input dirty.md"),
        ("api -F key=@ after >(...)", "gh api repos/o/r/issues/1/comments 2> >(cat) -F body=@dirty.md"),
        ("value inline after <(...)", f"gh pr comment 1 < <(echo y) --body {A}"),
        ("value inside <(...)", f"cat <(echo {A}) && gh pr comment 1 --body-file clean.md"),
        ("a gh write inside env -S", "env -S 'gh pr comment 1 --body-file dirty.md'"),
        # A shell's option values, clustered or long, are not its script (fix-delta review of #117).
        ("a gh write in bash -euo pipefail -c", "bash -euo pipefail -c 'gh pr comment 1 --body-file dirty.md'"),
        ("a gh write in bash -eo pipefail -c", "bash -eo pipefail -c 'gh pr create --body-file dirty.md'"),
        ("a gh write in bash -co pipefail", "bash -co pipefail 'gh pr comment 1 --body-file dirty.md'"),
        ("a gh write in bash -c -o pipefail", "bash -c -o pipefail 'gh pr comment 1 --body-file dirty.md'"),
        # With a startup file or an option the hook does not read, the shell also counts as an
        # interpreter, so an inline value shows the -c string is still parsed.
        ("a value inline in bash --rcfile f -c", f"bash --rcfile /dev/null -c 'gh pr comment 1 --body {A}'"),
        ("a value inline in zsh --emulate sh -c", f"zsh --emulate sh -c 'gh pr comment 1 --body {A}'"),
        ("a value inline in bash -euo pipefail -c", f"bash -euo pipefail -c 'gh pr comment 1 --body {A}'"),
        # env runs its split string with the words after it.
        ("a gh write split across env -S and its operands", "env -S gh pr comment 1 --body-file dirty.md"),
        ("a gh write after a quoted env -S string", "env -S 'gh pr comment 1' --body-file dirty.md"),
        ("a gh write in env -iS", "env -iS 'gh pr comment 1 --body-file dirty.md'"),
        ("a gh write in env -vS", "env -vS 'gh pr comment 1 --body-file dirty.md'"),
        # Every word after a -c is a candidate script (second fix-delta review of #117).
        ("a value inline in bash -c -", f"bash -c - 'gh pr comment 1 --body {A}'"),
        ("a value inline in sh -c -", f"sh -c - 'gh pr comment 1 --body {A}'"),
        ("a value inline in bash -login -c", f"bash -login -c 'gh pr comment 1 --body {A}'"),
        ("a value inline in bash -noprofile -c", f"bash -noprofile -c 'gh pr comment 1 --body {A}'"),
        ("a value inline in bash -norc -c", f"bash -norc -c 'gh pr comment 1 --body {A}'"),
        ("a value inline in bash -posix -c", f"bash -posix -c 'gh pr comment 1 --body {A}'"),
        ("a value inline in bash -rcfile f -c", f"bash -rcfile /dev/null -c 'gh pr comment 1 --body {A}'"),
        ("a value inline in bash -init-file f -c", f"bash -init-file /dev/null -c 'gh pr comment 1 --body {A}'"),
        ("a gh write in bash +o pipefail -c", "bash +o pipefail -c 'gh pr comment 1 --body-file dirty.md'"),
        ("a gh write in bash -c --", "bash -c -- 'gh pr comment 1 --body-file dirty.md'"),
        ("a gh write in env --split=", "env --split='gh pr comment 1 --body-file dirty.md'"),
        ("a gh write in env --s=", "env --s='gh pr comment 1 --body-file dirty.md'"),
        ("a gh write in env -iS joined", "env -iS'gh pr comment 1 --body-file dirty.md'"),
        ("a gh write in env -uX -S", "env -uX -S 'gh pr comment 1 --body-file dirty.md'"),
        # A script may start with - or +, and +c runs one too (third fix-delta review of #117).
        ("a gh write in a -c script starting with -", "bash -c -- '-x; gh pr comment 1 --body-file dirty.md'"),
        ("a value inline in a sh -c - script starting with +", f"sh -c - '+x; gh pr comment 1 --body {A}'"),
        ("a value inline in bash +c", f"bash +c 'gh pr comment 1 --body {A}'"),
        ("a value inline in sh +c", f"sh +c 'gh pr comment 1 --body {A}'"),
    ]
    for name, command in after_substitution:
        check(name, sb.hook(command), "deny", "matches private value list line", {3})
    substituted = "is a process substitution"
    for name, command in (
            ("body file <(...)", "gh pr create --title t --body-file <(cat clean.md)"),
            ("-F <(...)", "gh pr comment 1 -F <(cat clean.md)"),
            ("--body-file=<(...)", "gh pr comment 1 --body-file=<(cat clean.md)"),
            ("api --input <(...)", "gh api repos/o/r/issues --input <(cat clean.md)"),
            ("api -F key=@<(...)", "gh api repos/o/r/issues -F body=@<(cat clean.md)"),
            ("--body-file - < <(...)", "gh pr comment 1 --body-file - < <(cat clean.md)")):
        check(name, sb.hook(command), "deny", substituted)
    check("a <(...) the hook cannot close",
          sb.hook('gh pr create --assignee <(echo "fix (wip") --body-file clean.md'), "deny", "does not close")
    for name, command in (
            ("<(...) not outbound", "diff <(cat clean.md) <(cat reused.md)"),
            ("<(...) beside a clean post", "diff <(cat clean.md) <(cat reused.md); gh pr comment 1 --body-file clean.md"),
            ("2> >(...) on a clean post", "gh pr create --title t 2> >(tee err.log) --body-file clean.md"),
            ("<( in double quotes is text", 'gh pr comment 1 --body "use <(cat f) here" --body-file clean.md'),
            ("<( in single quotes is text", "gh pr comment 1 --body 'use <(cat f) here'"),
            ("an unclosed <( in double quotes is text",
             'gh pr comment 1 --body "use <(cat f here" --body-file clean.md'),
            ("an unclosed >( in double quotes is text",
             'gh pr comment 1 --body "use >(tee f here" --body-file clean.md')):
        check(name, sb.hook(command), "allow")

    # --- fd numbers and here-strings are redirects (#114) ------------------------
    # shlex splits 2>f like 2 > f; only the first is a redirect of fd 2.
    for name, command in (
            ("standard input is the plain <, not 3<", "gh pr comment 1 --body-file - < dirty.md 3< clean.md"),
            ("body file after a here-string", "gh pr create --title t <<< y --body-file dirty.md"),
            ("body file after 2>/dev/null", "gh pr create --title t 2>/dev/null --body-file dirty.md"),
            ("body file after 2>&1", "gh pr create --title t 2>&1 --body-file dirty.md"),
            ("body file after 1>out.log", "gh pr create --title t 1>out.log --body-file dirty.md"),
            ("body file read from 0<", "gh pr comment 1 --body-file - 0< dirty.md"),
            # The digits after >& or <& are the fd duplicated, not an fd number (#118 review).
            ("standard input after 2>&1", "gh pr comment 1 --body-file - 2>&1<dirty.md"),
            ("standard input after >&2", "gh pr comment 1 --body-file - >&2<dirty.md"),
            ("a here-string on fd 3 is text", f'gh pr comment 1 --body "ok" 3<<< "{A}"')):
        check(name, sb.hook(command), "deny", "matches private value list line", {3})
    check("2>&1>F on the body file is a same-command write",
          sb.hook("gh pr comment 1 --body-file reused.md 2>&1>reused.md"), "deny", "written by the same command")
    check("a command holding the fd mark cannot be split", sb.hook("gh pr comment 1 --body-file clean.md \ue0002>x"),
          "deny", "cannot be split")
    check("2> on the body file is a same-command write",
          sb.hook("gh pr comment 1 --body-file reused.md 2>reused.md"), "deny", "written by the same command")
    for name, command in (
            ("3< is not standard input", "gh pr comment 1 --body-file - < clean.md 3< dirty.md"),
            ("echo 2 > f: 2 is an argument", "echo 2 > f.txt && gh pr comment 1 --body-file clean.md"),
            ('"2>" in quotes is text', 'gh pr comment 1 --body "use 2>/dev/null to quiet it"')):
        check(name, sb.hook(command), "allow")

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
        ("sort -o on the body file", "sort -o reused.md reused.md && gh pr comment 1 --body-file reused.md"),
        ("an interpreter through uv run", "uv run python -c 1 && gh pr comment 1 --body-file reused.md"),
        ("an interpreter through xargs", "echo 1 | xargs python3 -c && gh pr comment 1 --body-file reused.md"),
        ("a named fd read as standard input", "gh pr comment 1 --body-file - < dirty.md {fd}< clean.md"),
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
