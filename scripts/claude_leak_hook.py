#!/usr/bin/env python3
"""A Claude Code PreToolUse hook: the leak gate for text agent sessions post to GitHub.

process/repository-standards.md owns the rules this enforces (Leak Gate, Guarding
Agent Sessions). It is installed at user scope on each machine that runs agent
sessions, runs before every Bash command, and reads the command from the hook
input on standard input. It exits 2 to deny, with the reason on standard error,
and 0 to allow. It never returns a permission decision of its own, so an allowed
command still goes through the session's normal permission prompts.

  1. Outbound text. A command that runs `gh pr|issue create|edit|comment`,
     `gh pr|issue close|reopen --comment`, `gh pr review`,
     `gh release create|edit`, or a writing `gh api` call is denied when its
     text, or a file it passes as the body, contains a value from the private
     value list. Matching is literal and case-insensitive. A body file that does
     not exist yet is denied, unless the same command writes it from a heredoc,
     whose text is part of the command.
  2. Gate escapes. Denied in every list state: `--no-verify` on any git
     command, `git commit -n`, `git -c core.hooksPath=...`, a `git config`
     write of core.hooksPath, and `SKIP=` on git or pre-commit. These are the
     forms an agent reaches for when the git-side gate refuses a commit. Forms
     that take intent, such as `--no-veri`, `-nm` or GIT_CONFIG_* variables, are
     documented residuals and pass.
  3. The list. Only the global list is read (git config --global
     leakgate.values): the text goes to GitHub, not into a clone, so a clone's
     own setting does not apply. Its lines are read and checked exactly as
     scripts/leak-gate.sh reads them. With no list declared, or "none", outbound
     commands are allowed with a note that value rules were skipped. With a
     declared list that is missing, unreadable, empty or holds a bad line,
     outbound commands are denied.

Nothing this prints contains a value, the command, or a file's contents. Values
are named by list line number. GitHub MCP write tools are not scanned yet.

Written in Python 3.10+, standard library only: it needs json and shlex, which
POSIX sh lacks. scripts/test_claude_leak_hook.py proves each rule.
"""

import json
import os
import re
import shlex
import subprocess
import sys

BYPASS = "Remove the value from the text, or fix the list; don't bypass."
LIST_KEY = "git config --global leakgate.values"


class Deny(Exception):
    pass


# --- The command: heredocs, continuations, tokens, simple commands -----------------

HEREDOC = re.compile(r"(?<!<)<<(-?)\s*(['\"]?)([A-Za-z0-9_.-]+)\2")


def strip_heredocs(text):
    """Returns the command without heredoc bodies, so a body is never read as a command."""
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        # The lookbehind keeps a here-string (<<<) from reading as a heredoc.
        for dash, _, delim in HEREDOC.findall(line):
            end = i
            while end < len(lines):
                candidate = lines[end].lstrip("\t") if dash else lines[end]
                if candidate == delim:
                    break
                end += 1
            if end == len(lines):
                break  # no terminator: leave the rest visible
            i = end + 1
    return "\n".join(out)


def join_continuations(text):
    """Removes backslash-newline outside single quotes, as the shell does."""
    out = []
    quote = None
    i = 0
    while i < len(text):
        c = text[i]
        if quote == "'":
            if c == "'":
                quote = None
        elif c == "\\" and i + 1 < len(text):
            if text[i + 1] == "\n":
                i += 2
                continue
            out.append(text[i:i + 2])
            i += 2
            continue
        elif c in "'\"":
            if quote is None:
                quote = c
            elif quote == c:
                quote = None
        out.append(c)
        i += 1
    return "".join(out)


def tokenize(text):
    # shlex's defaults would treat a newline as plain whitespace, merging a
    # command on the next line into the one before it, and would read "#"
    # inside a word as the start of a comment.
    lex = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


REDIRECTS = {"<", ">", ">>", "<<", ">&", "<&", "&>", "&>>", ">|", "<>"}
SEPARATOR_CHARS = set(";&|()\n")


def simple_commands(tokens):
    """Splits tokens into simple commands: (words, redirects)."""
    commands = []
    words, redirects = [], []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in REDIRECTS:
            target = tokens[i + 1] if i + 1 < len(tokens) else ""
            redirects.append((t, target))
            i += 2
            continue
        if t and set(t) <= SEPARATOR_CHARS | set("<>"):
            if words or redirects:
                commands.append((words, redirects))
            words, redirects = [], []
            i += 1
            continue
        words.append(t)
        i += 1
    if words or redirects:
        commands.append((words, redirects))
    return commands


ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
# Wrappers skipped to find the program, with their options that take a value.
WRAPPERS = {
    "env": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"},
    "command": set(),
    "exec": {"-a"},
    "nohup": set(),
    "time": {"-f", "--format", "-o", "--output"},
    "nice": {"-n", "--adjustment"},
    "sudo": {"-u", "--user", "-g", "--group", "-C", "--close-from", "-D", "--chdir",
             "-h", "--host", "-p", "--prompt", "-r", "--role", "-t", "--type", "-U", "--other-user"},
    "timeout": {"-s", "--signal", "-k", "--kill-after"},
}


class Command:
    def __init__(self, assigns, words, redirects, cwd):
        self.assigns = assigns
        self.words = words
        self.redirects = redirects
        self.cwd = cwd

    @property
    def program(self):
        return os.path.basename(self.words[0]) if self.words else ""


def unwrap(words):
    """Returns (assignments, words) with leading assignments and wrappers removed."""
    assigns = []
    i = 0
    while i < len(words):
        w = words[i]
        if ASSIGNMENT.match(w):
            assigns.append(w)
            i += 1
            continue
        name = os.path.basename(w)
        if name not in WRAPPERS:
            break
        takes_value = WRAPPERS[name]
        i += 1
        while i < len(words) and words[i].startswith("-") and words[i] != "-":
            opt = words[i]
            i += 1
            if opt == "--":
                break
            if opt in takes_value:
                i += 1
        if name == "timeout" and i < len(words):
            i += 1  # the duration
        while name in ("env", "sudo") and i < len(words) and ASSIGNMENT.match(words[i]):
            assigns.append(words[i])
            i += 1
    return assigns, words[i:]


def expand(path, cwd):
    """Resolves a path as the shell would, or returns None when it cannot be known."""
    path = os.path.expanduser(os.path.expandvars(path))
    if "$" in path or "`" in path:
        return None
    if not os.path.isabs(path):
        if cwd is None:
            return None
        path = os.path.join(cwd, path)
    return os.path.normpath(path)


def parse(text, cwd, depth=0):
    """Returns (commands, words) for a command string, descending into sh -c and eval."""
    tokens = tokenize(join_continuations(strip_heredocs(text)))
    commands, all_words = [], list(tokens)
    for words, redirects in simple_commands(tokens):
        assigns, words = unwrap(words)
        cmd = Command(assigns, words, redirects, cwd)
        commands.append(cmd)
        if cmd.program == "cd":
            target = words[1] if len(words) > 1 else "~"
            cwd = expand(target, cwd) if target != "-" else None
        if depth < 3 and cmd.program in SHELLS:
            for j, w in enumerate(words[1:], 1):
                if w.startswith("-") and not w.startswith("--") and "c" in w:
                    script = next((x for x in words[j + 1:] if not x.startswith("-")), None)
                    if script is not None:
                        sub, sub_words = parse(script, cwd, depth + 1)
                        commands += sub
                        all_words += sub_words
                    break
        if depth < 3 and cmd.program == "eval" and len(words) > 1:
            sub, sub_words = parse(" ".join(words[1:]), cwd, depth + 1)
            commands += sub
            all_words += sub_words
    return commands, all_words


# --- Gate escapes ---------------------------------------------------------------------

def hookspath_key(kv):
    return kv.split("=", 1)[0].casefold() == "core.hookspath"


GIT_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                         "--config-env", "--super-prefix", "--exec-path"}
CONFIG_READS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--unset",
                "--unset-all", "--list", "-l", "get", "unset", "list", "--remove-section"}
CONFIG_WRITES = {"set", "--add", "--replace-all"}
CONFIG_WITH_VALUE = {"--file", "-f", "--blob", "--type", "--default", "--comment"}


def escape(cmd):
    """Returns what makes this command a gate escape, or None."""
    prog = cmd.program
    if prog in ("git", "pre-commit") and any(a.startswith("SKIP=") for a in cmd.assigns):
        return "SKIP="
    if prog == "export" and any(w.startswith("SKIP=") for w in cmd.words[1:]):
        return "SKIP="
    if prog != "git":
        return None
    words = cmd.words[1:]
    i = 0
    while i < len(words) and words[i].startswith("-"):
        w = words[i]
        if w in ("-c", "--config-env") and i + 1 < len(words) and hookspath_key(words[i + 1]):
            return "a core.hooksPath override"
        if w.startswith("--config-env=") and hookspath_key(w[len("--config-env="):]):
            return "a core.hooksPath override"
        if w.startswith("-c") and len(w) > 2 and not w.startswith("--") and hookspath_key(w[2:]):
            return "a core.hooksPath override"
        i += 2 if w in GIT_GLOBAL_WITH_VALUE else 1
    if i >= len(words):
        return None
    sub, rest = words[i], words[i + 1:]
    if "--no-verify" in rest:
        return "--no-verify"
    if sub == "commit" and "-n" in rest:
        return "git commit -n"
    if sub == "config" and any(r.casefold() == "core.hookspath" for r in rest):
        if any(r in CONFIG_WRITES for r in rest):
            return "a core.hooksPath override"
        if any(r in CONFIG_READS for r in rest):
            return None
        positional = []
        j = 0
        while j < len(rest):
            if rest[j] in CONFIG_WITH_VALUE:
                j += 2
                continue
            if not rest[j].startswith("-"):
                positional.append(rest[j])
            j += 1
        keys = [k for k, p in enumerate(positional) if p.casefold() == "core.hookspath"]
        if keys and keys[0] + 1 < len(positional):
            return "a core.hooksPath override"
    return None


FALLBACK_ESCAPES = [
    (re.compile(r"--no-verify\b"), "--no-verify"),
    (re.compile(r"\bcommit\b[^\n;&|]*\s-n\b"), "git commit -n"),
    (re.compile(r"core\.hookspath", re.I), "a core.hooksPath override"),
    (re.compile(r"(^|[\s;&|(])SKIP="), "SKIP="),
]


# --- Outbound commands and the text they send -------------------------------------------

GH_TEXT_VERBS = {
    "pr": {"create", "new", "edit", "comment", "review"},
    "issue": {"create", "new", "edit", "comment"},
    "release": {"create", "new", "edit"},
}
GH_FILE_FLAGS = {"--body-file", "-F", "--notes-file"}
GH_API_FIELDS = {"-f", "-F", "--field", "--raw-field"}


def option(words, names):
    """Yields each value given to any of the named options, in every spelling."""
    for i, w in enumerate(words):
        for n in names:
            if w == n and i + 1 < len(words):
                yield words[i + 1]
            elif n.startswith("--") and w.startswith(n + "="):
                yield w[len(n) + 1:]
            elif not n.startswith("--") and w.startswith(n) and len(w) > len(n):
                yield w[len(n):]


def outbound_files(cmd):
    """Returns (outbound, files) for a gh command: the paths of files it sends."""
    if cmd.program != "gh":
        return False, []
    args = cmd.words[1:]
    while args and args[0].startswith("-"):
        args = args[1:]
    if not args:
        return False, []
    group, rest = args[0], args[1:]
    verb = rest[0] if rest else ""
    files = []
    if group in GH_TEXT_VERBS and verb in GH_TEXT_VERBS[group]:
        files = list(option(rest, GH_FILE_FLAGS))
    elif group in ("pr", "issue") and verb in ("close", "reopen"):
        if not list(option(rest, {"--comment", "-c"})):
            return False, []
    elif group == "api":
        methods = [m.upper() for m in option(rest, {"-X", "--method"})]
        fields = list(option(rest, GH_API_FIELDS))
        inputs = list(option(rest, {"--input"}))
        if not (fields or inputs or any(m != "GET" for m in methods)):
            return False, []
        files = inputs + [f.split("=@", 1)[1] for f in fields if "=@" in f]
    else:
        return False, []
    stdin = [t for op, t in cmd.redirects if op == "<"]
    files = [stdin[-1] if f == "-" and stdin else f for f in files if f != "-" or stdin]
    return True, files


# --- The value list, read the way scripts/leak-gate.sh reads it ---------------------------

NONASCII_SPACE = re.compile(rb"^(\xc2\xa0|\xe3\x80\x80|\xe2\x80[\x80-\x8a])|"
                            rb"(\xc2\xa0|\xe3\x80\x80|\xe2\x80[\x80-\x8a])$")


def read_list():
    """Returns None when no list is declared, else [(line number, value)]. Raises Deny."""
    try:
        proc = subprocess.run(["git", "config", "--global", "--get", "leakgate.values"],
                              capture_output=True)
    except OSError:
        raise Deny("git could not be run to read the value list declaration "
                   f"({LIST_KEY}).")
    if proc.returncode == 1:
        return None
    if proc.returncode != 0:
        raise Deny(f"git could not read the value list declaration ({LIST_KEY}).")
    declared = proc.stdout.decode("utf-8", "replace").strip()
    if declared in ("", "none"):
        return None
    if declared.startswith("~/"):
        declared = os.path.join(os.path.expanduser("~"), declared[2:])
    if not os.path.isabs(declared):
        raise Deny(f"the global value list ({LIST_KEY}) must be an absolute path or start with ~/.")
    if not os.path.isfile(declared):
        raise Deny(f"the global value list ({LIST_KEY}) does not exist.")
    try:
        with open(declared, "rb") as f:
            content = f.read()
    except OSError:
        raise Deny(f"the global value list ({LIST_KEY}) cannot be read.")

    # leak-gate.sh: a byte-order mark is dropped from the first line, a CR before
    # each newline is dropped, then any other CR ends a line.
    if content.startswith(b"\xef\xbb\xbf"):
        content = content[3:]
    lines = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    entries = []
    for n, line in enumerate(lines, 1):
        value = line.strip(b" \t\n\v\f\r")  # [[:space:]] in the C locale
        if not value or value.startswith(b"#"):
            continue
        if NONASCII_SPACE.search(value):
            raise Deny(f"value list line {n} starts or ends with a non-ASCII space.")
        try:
            text = value.decode("utf-8")
        except UnicodeDecodeError:
            raise Deny(f"value list line {n} is not valid UTF-8.")
        if re.search(rb"[\x00-\x08\x0a-\x1f\x7f]", value):
            raise Deny(f"value list line {n} holds a control character.")
        if b"\\E" in value or b"'''" in value:
            raise Deny(f"value list line {n} contains \\E or ''', which cannot be quoted as a literal.")
        # Bytes, as dash's ${#value} counts them in leak-gate.sh.
        if len(value) < 4:
            raise Deny(f"value list line {n} is shorter than 4 characters and would match almost every file.")
        entries.append((n, text.casefold()))
    if not entries:
        raise Deny(f"the global value list ({LIST_KEY}) has no values.")
    return entries


# --- Deciding --------------------------------------------------------------------------

def decide(command, cwd):
    """Returns None to allow, or a note to show. Raises Deny."""
    try:
        commands, words = parse(command, cwd)
    except ValueError:
        commands, words = None, []

    if commands is None:
        for pattern, what in FALLBACK_ESCAPES:
            if pattern.search(command) and ("git" in command or what == "SKIP="):
                raise Deny(f"{what} switches off the git hooks that run the leak gate.")
        outbound = re.search(r"(^|[\s;&|(/])gh\s", command) is not None
        files, heredoc_written = [], set()
    else:
        for cmd in commands:
            what = escape(cmd)
            if what:
                raise Deny(f"{what} switches off the git hooks that run the leak gate.")
        outbound = False
        files = []
        heredoc_written = set()
        for cmd in commands:
            if any(op == "<<" for op, _ in cmd.redirects):
                targets = [t for op, t in cmd.redirects if op in (">", ">>", ">|")]
                if cmd.program == "tee":
                    targets += [w for w in cmd.words[1:] if not w.startswith("-")]
                heredoc_written.update(p for p in (expand(t, cmd.cwd) for t in targets) if p)
            is_out, named = outbound_files(cmd)
            if is_out:
                outbound = True
                files += [(f, expand(f, cmd.cwd)) for f in named]
    if not outbound:
        return None

    entries = read_list()
    if entries is None:
        return ("leak hook: value rules skipped: no global value list declared "
                f"({LIST_KEY}), so the text this command sends to GitHub was not checked.")

    texts = [command, " ".join(words)]
    for name, path in files:
        if path is None or not os.path.exists(path):
            if path in heredoc_written:
                continue
            raise Deny("a file this command sends to GitHub does not exist yet, so it cannot be "
                       "checked. Write the file in one step, then post it in the next.")
        try:
            with open(path, "rb") as f:
                texts.append(f.read().decode("utf-8", "replace"))
        except OSError:
            raise Deny("a file this command sends to GitHub cannot be read, so it cannot be checked.")

    haystack = "\n".join(texts).casefold()
    hits = [n for n, value in entries if value in haystack]
    if hits:
        which = f"line {hits[0]}" if len(hits) == 1 else "lines " + ", ".join(map(str, hits))
        raise Deny(f"the text this command sends to GitHub matches private value list {which}.")
    return None


def main():
    try:
        try:
            data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
        except ValueError:
            raise Deny("the hook input is not valid JSON, so the command cannot be checked.")
        if not isinstance(data, dict) or data.get("tool_name") != "Bash":
            return 0
        command = (data.get("tool_input") or {}).get("command")
        if not isinstance(command, str):
            return 0
        cwd = data.get("cwd") if isinstance(data.get("cwd"), str) else os.getcwd()
        note = decide(command, cwd)
        if note:
            print(json.dumps({
                "systemMessage": note,
                "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": note},
            }))
        return 0
    except Deny as reason:
        sys.stderr.write(f"leak hook: denied: {reason} {BYPASS}\n")
        return 2
    except Exception as error:  # fail closed, naming nothing from the input
        sys.stderr.write(f"leak hook: denied: the hook failed ({type(error).__name__}) "
                         f"and cannot check this command. {BYPASS}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
