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
     not exist yet, or that the same command writes, is denied, unless the
     command writes it only from a heredoc, whose text is part of the command.
     Commands after shell keywords (if, then, do, {, !), inside $(...) or
     backticks, and inside sh -c or eval are checked like any other.
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
import stat
import sys

BYPASS = "Remove the value from the text, or fix the list; don't bypass."
LIST_KEY = "git config --global leakgate.values"
MAX_DEPTH = 3  # how deep sh -c and eval are followed
MAX_BODY_BYTES = 10 * 1024 * 1024  # a body file larger than this is denied unread


class Deny(Exception):
    pass


# --- The command: heredocs, continuations, tokens, simple commands -----------------

# The lookbehind keeps a here-string (<<<) from reading as a heredoc.
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


def strip_comments_and_continuations(text):
    """Removes # comments and backslash-newlines outside quotes, as the shell does.

    A comment is dropped before tokenizing, because an apostrophe in one, as in
    "# it's done", would otherwise leave shlex with an unclosed quote.
    """
    if "\\\n" not in text and "#" not in text:
        return text
    out = []
    quote = None
    i = 0
    while i < len(text):
        c = text[i]
        if quote == "'":
            if c == "'":
                quote = None
        elif quote is None and c == "#" and (i == 0 or text[i - 1] in " \t\n;&|()<>"):
            end = text.find("\n", i)
            i = len(text) if end == -1 else end
            continue
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


PUNCTUATION = ";&|()<>\n"


def tokenize(text):
    # shlex's defaults would treat a newline as plain whitespace, merging a
    # command on the next line into the one before it, and would read "#"
    # inside a word as the start of a comment.
    lex = shlex.shlex(text, posix=True, punctuation_chars=PUNCTUATION)
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


REDIRECTS = {"<", ">", ">>", "<<", ">&", "<&", "&>", "&>>", ">|", "<>"}


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
        # Any other run of punctuation separates commands: ; && || | & ( ) and newlines.
        if t and set(t) <= set(PUNCTUATION):
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
# Shell reserved words that can stand before a command: if ...; then gh ...
RESERVED = {"!", "{", "}", "if", "then", "else", "elif", "while", "until", "do",
            "fi", "done", "esac"}
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
        if w in RESERVED:
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
    text = strip_comments_and_continuations(strip_heredocs(text))
    tokens = tokenize(text)
    commands, all_words = [], list(tokens)
    for script in substitutions(text):
        if depth < MAX_DEPTH:
            sub, sub_words = parse(script, cwd, depth + 1)
            commands += sub
            all_words += sub_words
    for words, redirects in simple_commands(tokens):
        assigns, words = unwrap(words)
        cmd = Command(assigns, words, redirects, cwd)
        commands.append(cmd)
        if cmd.program == "cd":
            target = words[1] if len(words) > 1 else "~"
            cwd = expand(target, cwd) if target != "-" else None
        script = nested_script(cmd)
        if script is not None and depth < MAX_DEPTH:
            sub, sub_words = parse(script, cwd, depth + 1)
            commands += sub
            all_words += sub_words
    return commands, all_words


def substitutions(text):
    """Returns the scripts in $(...) and backticks outside single quotes.

    The shell runs them, quoted in double quotes or not, as in
    url="$(gh pr create ...)". Inside single quotes they are literal text, as
    in a PR body that quotes `git commit -n`.
    """
    bodies = []
    quote = None
    i = 0
    while i < len(text):
        c = text[i]
        if quote == "'":
            if c == "'":
                quote = None
        elif c == "\\":
            i += 1
        elif c == "'" and quote is None:
            quote = "'"
        elif c == '"':
            quote = None if quote == '"' else '"'
        elif c == "`":
            end = text.find("`", i + 1)
            end = len(text) if end == -1 else end
            bodies.append(text[i + 1:end])
            i = end
        elif text.startswith("$(", i):
            depth, j = 1, i + 2
            while j < len(text) and depth:
                depth += {"(": 1, ")": -1}.get(text[j], 0)
                j += 1
            bodies.append(text[i + 2:j - 1] if depth == 0 else text[i + 2:])
            i = j - 1
        i += 1
    return bodies


def nested_script(cmd):
    """Returns the script that sh -c or eval runs, or None."""
    if cmd.program == "eval" and len(cmd.words) > 1:
        return " ".join(cmd.words[1:])
    if cmd.program in SHELLS:
        for j, w in enumerate(cmd.words[1:], 1):
            if w.startswith("-") and not w.startswith("--") and "c" in w:
                return next((x for x in cmd.words[j + 1:] if not x.startswith("-")), None)
    return None


# --- Gate escapes ---------------------------------------------------------------------

NO_VERIFY = "--no-verify"
COMMIT_N = "git commit -n"
HOOKSPATH = "a core.hooksPath override"
SKIP = "SKIP="
HOOKSPATH_KEY = "core.hookspath"  # git compares config keys case-insensitively


def hookspath_key(kv):
    return kv.split("=", 1)[0].casefold() == HOOKSPATH_KEY


GIT_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                         "--config-env", "--super-prefix", "--exec-path"}
CONFIG_READS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--unset",
                "--unset-all", "--list", "-l", "get", "unset", "list", "--remove-section"}
CONFIG_WRITES = {"set", "--add", "--replace-all"}
CONFIG_WITH_VALUE = {"--file", "-f", "--blob", "--type", "--default", "--comment"}


def escape(cmd):
    """Returns what makes this command a gate escape, or None."""
    prog = cmd.program
    if prog in ("git", "pre-commit") and any(a.startswith(SKIP) for a in cmd.assigns):
        return SKIP
    if prog == "export" and any(w.startswith(SKIP) or w == SKIP[:-1] for w in cmd.words[1:]):
        return SKIP
    if prog != "git":
        return None
    words = cmd.words[1:]
    i = 0
    while i < len(words) and words[i].startswith("-"):
        w = words[i]
        if ((w in ("-c", "--config-env") and i + 1 < len(words) and hookspath_key(words[i + 1]))
                or (w.startswith("--config-env=") and hookspath_key(w[len("--config-env="):]))
                or (w.startswith("-c") and not w.startswith("--") and len(w) > 2
                    and hookspath_key(w[2:]))):
            return HOOKSPATH
        i += 2 if w in GIT_GLOBAL_WITH_VALUE else 1
    if i >= len(words):
        return None
    sub, rest = words[i], words[i + 1:]
    if NO_VERIFY in rest:
        return NO_VERIFY
    if sub == "commit" and "-n" in rest:
        return COMMIT_N
    if sub == "config" and any(r.casefold() == HOOKSPATH_KEY for r in rest):
        if any(r in CONFIG_WRITES for r in rest):
            return HOOKSPATH
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
        keys = [k for k, p in enumerate(positional) if p.casefold() == HOOKSPATH_KEY]
        if keys and keys[0] + 1 < len(positional):
            return HOOKSPATH
    return None


# For a command shlex cannot split: (pattern, what it is, whether it needs "git" too).
FALLBACK_ESCAPES = [
    (re.compile(r"--no-verify\b"), NO_VERIFY, True),
    (re.compile(r"\bcommit\b[^\n;&|]*\s-n\b"), COMMIT_N, True),
    (re.compile(r"core\.hookspath", re.I), HOOKSPATH, True),
    (re.compile(r"(^|[\s;&|(])SKIP="), SKIP, False),
]


# --- Outbound commands and the text they send -------------------------------------------

GH_TEXT_VERBS = {
    "pr": {"create", "new", "edit", "comment", "review"},
    "issue": {"create", "new", "edit", "comment"},
    "release": {"create", "new", "edit"},
}
GH_FILE_FLAGS = {"--body-file", "-F", "--notes-file"}
GH_API_FIELDS = {"-f", "-F", "--field", "--raw-field"}
STDIN_PATHS = {"/dev/stdin", "/dev/fd/0", "/proc/self/fd/0"}


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


def gh_outbound(cmd):
    """Returns (outbound, files): whether this is a gh write, and the files it sends."""
    if cmd.program != "gh":
        return False, []
    args = cmd.words[1:]
    while args and args[0].startswith("-"):
        args = args[1:]
    if not args:
        return False, []
    group, rest = args[0], args[1:]
    while rest and rest[0].startswith("-"):  # gh issue -R o/r comment ...
        rest = rest[2:] if rest[0] in ("-R", "--repo") else rest[1:]
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
        # Only -F/--field reads @<path>; -f/--raw-field sends the text as it is.
        typed = list(option(rest, {"-F", "--field"}))
        files = inputs + [f.split("=@", 1)[1] for f in typed if "=@" in f]
    else:
        return False, []
    stdin = [t for op, t in cmd.redirects if op == "<"]
    files = ["-" if f in STDIN_PATHS else f for f in files]
    files = [stdin[-1] if f == "-" and stdin else f for f in files if f != "-" or stdin]
    return True, files


# --- The value list, read the way scripts/leak-gate.sh reads it ---------------------------

NONASCII_SPACE = re.compile(rb"^(\xc2\xa0|\xe3\x80\x80|\xe2\x80[\x80-\x8a])|"
                            rb"(\xc2\xa0|\xe3\x80\x80|\xe2\x80[\x80-\x8a])$")
CONTROL_CHARS = re.compile(rb"[\x00-\x08\x0a-\x1f\x7f]")  # [[:cntrl:]] less tab


def read_list():
    """Returns None when no list is declared, else [(line number, value)]. Raises Deny."""
    import subprocess  # only outbound commands get here; it is slow to import

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
        if CONTROL_CHARS.search(value):
            raise Deny(f"value list line {n} holds a control character.")
        if b"\\E" in value or b"'''" in value:
            raise Deny(f"value list line {n} contains \\E or ''', which cannot be quoted as a literal.")
        # Bytes, as dash's ${#value} counts them in leak-gate.sh. Where sh is
        # bash, as on macOS, the wrapper counts characters in a UTF-8 locale.
        if len(value) < 4:
            raise Deny(f"value list line {n} is shorter than 4 characters and would match almost every file.")
        entries.append((n, text.casefold()))
    if not entries:
        raise Deny(f"the global value list ({LIST_KEY}) has no values.")
    return entries


# --- Deciding --------------------------------------------------------------------------

ESCAPE_REASON = "switches off the git hooks that run the leak gate."
FALLBACK_FILE_FLAGS = re.compile(r"--body-file|--notes-file|--input|\s-F|=@")


WRITE_REDIRECTS = {">", ">>", ">|", "&>", "&>>"}
COPIERS = {"cp", "mv", "install", "ln"}  # the last operand is written


def written_paths(cmd):
    """Returns (from_heredoc, other): the paths a command writes.

    A file written from a heredoc, as in cat > F <<'EOF', holds text that is
    part of the command itself. A file written any other way holds text the
    hook cannot see until the command runs.
    """
    targets = [t for op, t in cmd.redirects if op in WRITE_REDIRECTS]
    operands = [w for w in cmd.words[1:] if not w.startswith("-")]
    if cmd.program == "tee":
        targets += operands
    elif cmd.program in COPIERS and operands:
        targets.append(operands[-1])
    paths = [p for p in (expand(t, cmd.cwd) for t in targets) if p]
    # Only cat or tee with no input file but the heredoc, as in cat > F <<'EOF'.
    # cat header.md - > F <<'EOF' also writes header.md, which the hook cannot see.
    inputs = operands if cmd.program == "cat" else []
    if (any(op == "<<" for op, _ in cmd.redirects) and cmd.program in ("cat", "tee")
            and all(w == "-" for w in inputs)):
        return paths, []
    return [], paths

def read_body(path):
    """Returns a body file's text. Raises Deny for anything but a readable regular file.

    A FIFO, a device such as /dev/zero, or a huge file could otherwise hang the
    hook or exhaust its memory, and a hook that times out does not block.
    """
    try:
        info = os.stat(path)
        if not stat.S_ISREG(info.st_mode):
            raise Deny("a file this command sends to GitHub is not a regular file, so it cannot "
                       "be checked.")
        if info.st_size > MAX_BODY_BYTES:
            raise Deny("a file this command sends to GitHub is larger than 10 MiB, so it is not "
                       "checked.")
        with open(path, "rb") as f:
            return f.read(MAX_BODY_BYTES + 1).decode("utf-8", "replace")
    except OSError:
        raise Deny("a file this command sends to GitHub cannot be read, so it cannot be checked.")


def decide(command, cwd):
    """Returns None to allow, or a note to show. Raises Deny."""
    try:
        commands, words = parse(command, cwd)
    except ValueError:
        commands, words = None, []

    outbound = False
    files = []  # resolved paths, None where the path cannot be known
    heredoc_written, other_written = set(), set()
    if commands is None:
        has_git = "git" in command
        for pattern, what, needs_git in FALLBACK_ESCAPES:
            if pattern.search(command) and (has_git or not needs_git):
                raise Deny(f"{what} {ESCAPE_REASON}")
        outbound = re.search(r"(^|[\s;&|(/`])gh\s", command) is not None
        if outbound and FALLBACK_FILE_FLAGS.search(command):
            raise Deny("this command cannot be split into words, so the files it sends to "
                       "GitHub cannot be checked. Rewrite it with balanced quotes.")
    else:
        for cmd in commands:
            what = escape(cmd)
            if what:
                raise Deny(f"{what} {ESCAPE_REASON}")
        for cmd in commands:
            from_heredoc, other = written_paths(cmd)
            heredoc_written.update(from_heredoc)
            other_written.update(other)
            is_out, named = gh_outbound(cmd)
            if is_out:
                outbound = True
                files += [expand(f, cmd.cwd) for f in named]
    if not outbound:
        return None

    entries = read_list()
    if entries is None:
        return ("leak hook: value rules skipped: no global value list declared "
                f"({LIST_KEY}), so the text this command sends to GitHub was not checked.")

    texts = [command, " ".join(words)]
    for path in files:
        if path in other_written or path is None or not os.path.exists(path):
            if path in heredoc_written and path not in other_written:
                continue
            raise Deny("a file this command sends to GitHub is written by the same command, or "
                       "does not exist yet, so it cannot be checked. Write the file in one step, "
                       "then post it in the next.")
        texts.append(read_body(path))

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
        tool_input = data.get("tool_input")
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str):
            raise Deny("the hook input has no command string, so the command cannot be checked.")
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
