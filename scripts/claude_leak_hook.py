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
     value list. Matching is literal and case-insensitive. Words that only name
     a file or a directory are not matched: the files gh sends, redirect
     targets, and cd, pushd and popd operands. gh sends a file's contents, which
     are matched, never its path. A body file that does not exist yet, or that
     the same command writes, is denied, unless the command writes it only from
     a heredoc, whose text is part of the command. sed -i, gsed -i and perl -i
     count as writes, and an interpreter or a script run in the command counts
     as writing every file. A body file that is a <(...) or >(...) is denied.
     Commands after shell keywords (if, then, do, {, !), inside $(...),
     backticks, <(...) or >(...), and inside sh -c or eval are checked like any
     other.
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

import fnmatch
import glob
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
HEREDOC = re.compile(r"(?<!<)<<(-?)\s*\\?(['\"]?)([A-Za-z0-9_.-]+)\2")
HEREDOC_OPERATOR = re.compile(r"(?<!<)<<(?!<)")


def strip_heredocs(text):
    """Returns (command, bodies): the command without heredoc bodies, so a body is
    never read as a command, and the bodies, which are still text to match.

    A heredoc this cannot follow, with a delimiter it does not read or no
    terminator, leaves the rest of the text in the command, and adds it to the
    bodies too: read as commands, a body line such as "> name" would otherwise
    put its text where a redirect target goes, which is not matched.
    """
    lines = text.split("\n")
    out, bodies = [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        found = HEREDOC.findall(line)
        if len(HEREDOC_OPERATOR.findall(line)) > len(found):
            bodies.append("\n".join(lines[i:]))
        for dash, _, delim in found:
            end = i
            while end < len(lines):
                candidate = lines[end].lstrip("\t") if dash else lines[end]
                if candidate == delim:
                    break
                end += 1
            if end == len(lines):
                bodies.append("\n".join(lines[i:]))
                break  # no terminator: leave the rest visible
            bodies.append("\n".join(lines[i:end]))
            i = end + 1
    return "\n".join(out), bodies


def strip_comments_and_continuations(text):
    """Removes # comments and backslash-newlines outside quotes, as the shell does.

    A comment is dropped before tokenizing, because an apostrophe in one, as in
    "# it's done", would otherwise leave shlex with an unclosed quote. Returns
    (command, comments): what this takes for a comment may be text the shell
    sends, as in $'it\\'s #1', so the comments are still text to match.
    """
    if "\\\n" not in text and "#" not in text:
        return text, []
    out, comments = [], []
    quote = None
    i = 0
    while i < len(text):
        c = text[i]
        if quote == "'":
            if c == "'":
                quote = None
        elif quote is None and c == "#" and (i == 0 or text[i - 1] in " \t\n;&|()<>"):
            end = text.find("\n", i)
            end = len(text) if end == -1 else end
            comments.append(text[i:end])
            i = end
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
    return "".join(out), comments


PUNCTUATION = ";&|()<>\n"
FD_MARK = "\ue000"  # a private-use character that marks an fd number before shlex runs
PRIVATE_MARKS = "\ue000\ue001\ue002\ue003"  # FD_MARK and the standard-input marks below
BLANKS = " \t\r"  # what tokenize() gives shlex as whitespace
FD_NUMBER = re.compile(r"[0-9]+(?=[<>])")
FD_NUMBER_MARKED = re.compile(FD_MARK + r"[0-9]+$")
WORD_START = " \t\r\n;&|()"


def mark_fd_numbers(text):
    """Returns text with FD_MARK before each fd number: digits that start a word,
    outside quotes, and touch a redirect operator, as in 2>/dev/null or 2>&1.

    shlex splits 2>f and 2 > f alike, so the mark is what keeps them apart: in
    echo 2 > f, the 2 is an argument. A text that already holds the mark cannot
    be read this way, and raises ValueError, as an unbalanced quote does.
    """
    if any(c in text for c in PRIVATE_MARKS):
        raise ValueError("the text holds a character the parser uses as a mark")
    out, quote, i = [], None, 0
    start = True  # whether text[i] starts a word: after an unquoted, unescaped separator
    arrow = False  # whether the last character was an unquoted, unescaped < or >
    # After an unquoted >& or <&, the next word is the fd it duplicates, even
    # across blanks, as the 1 in 2>&1>f or the 2 in >& 2>f: never an fd number.
    dup = False
    while i < len(text):
        c = text[i]
        if quote is None and start and not dup:
            fd = FD_NUMBER.match(text, i)
            if fd:
                out.append(FD_MARK + fd.group())
                i, start, arrow = fd.end(), False, False
                continue
        unquoted = quote is None
        if quote == "'":
            quote = None if c == "'" else quote
        elif c == "\\":
            out.append(text[i:i + 2])
            i, start, arrow, dup = i + 2, False, False, False
            continue
        elif c in "'\"":
            quote = None if quote == c else (quote or c)
        out.append(c)
        i += 1
        closes_dup = unquoted and c == "&" and arrow
        if unquoted and c not in BLANKS:
            dup = closes_dup
        elif not unquoted:
            dup = False
        arrow = unquoted and quote is None and c in "<>"
        start = quote is None and c in WORD_START and not closes_dup
    return "".join(out)


def tokenize(text):
    # shlex's defaults would treat a newline as plain whitespace, merging a
    # command on the next line into the one before it, and would read "#"
    # inside a word as the start of a comment.
    lex = shlex.shlex(mark_fd_numbers(text), posix=True, punctuation_chars=PUNCTUATION)
    lex.whitespace = BLANKS
    lex.whitespace_split = True
    lex.commenters = ""
    tokens = []
    for t in lex:
        # A marked fd number joins the operator after it, as 2> or 2>&, and keeps
        # the mark, so that simple_commands() can tell it from a quoted "2>".
        if tokens and FD_NUMBER_MARKED.match(tokens[-1]) and t in REDIRECTS:
            t = tokens.pop() + t
        tokens.append(t)
    return [t[len(FD_MARK):] if FD_NUMBER_MARKED.match(t) else t for t in tokens]


REDIRECTS = {"<", ">", ">>", "<<", "<<<", ">&", "<&", "&>", "&>>", ">|", "<>"}
FD_REDIRECT = re.compile(FD_MARK + r"([0-9]+)(.+)$")


def redirect(t):
    """Returns the operator a redirect token is stored as, or None for a word.

    An fd redirect comes from tokenize() marked, as FD_MARK + "2>". An output fd
    is stored as the plain operator, since any fd writes its target. An input
    fd other than 0 keeps its number, as 3<, so it is never read as standard
    input.
    """
    if t in REDIRECTS:
        return t
    fd = FD_REDIRECT.match(t)
    if not fd or fd.group(2) not in REDIRECTS:
        return None
    number, op = fd.groups()
    if op == ">&" and int(number) == 0:
        return "0>&"  # n>&m and n<&m both copy fd m onto fd n, so 0>&3 sets standard input
    return op if op.startswith(">") or int(number) == 0 else number + op


def simple_commands(tokens):
    """Splits tokens into simple commands: (words, redirects)."""
    commands = []
    words, redirects = [], []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        op = redirect(t)
        if op:
            target = tokens[i + 1] if i + 1 < len(tokens) else ""
            if FD_REDIRECT.match(target):  # the parser lost its place: 2> cannot be a target
                raise ValueError("a redirect's target is itself an fd redirect")
            redirects.append((op, target))
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
    "env": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string", "-a", "--argv0"},
    "command": set(),
    "exec": {"-a"},
    "nohup": set(),
    "time": {"-f", "--format", "-o", "--output"},
    "nice": {"-n", "--adjustment"},
    "sudo": {"-u", "--user", "-g", "--group", "-C", "--close-from", "-D", "--chdir",
             "-h", "--host", "-p", "--prompt", "-r", "--role", "-t", "--type", "-U", "--other-user",
             "-R", "--chroot", "-T", "--command-timeout"},
    "timeout": {"-s", "--signal", "-k", "--kill-after"},
    "builtin": set(),
}
# Their long options that take no value, so that an abbreviation is read as
# getopt_long reads it: --sig is --signal, which takes a value; --fore is not.
WRAPPER_FLAGS = {
    "env": {"--ignore-environment", "--null", "--debug", "--help", "--version",
            "--list-signal-handling", "--block-signal", "--default-signal", "--ignore-signal"},
    "time": {"--append", "--verbose", "--portability", "--quiet", "--help", "--version"},
    "nice": {"--help", "--version"},
    "sudo": {"--askpass", "--background", "--bell", "--edit", "--help", "--login", "--list",
             "--non-interactive", "--preserve-env", "--preserve-groups", "--remove-timestamp",
             "--reset-timestamp", "--set-home", "--shell", "--stdin", "--validate", "--version"},
    "timeout": {"--foreground", "--preserve-status", "--verbose", "--help", "--version"},
}


class Command:
    def __init__(self, assigns, words, redirects, cwd):
        self.assigns = assigns
        self.words = words
        self.redirects = redirects
        self.cwd = cwd
        self.outbound, self.files, self.unmatched = gh_outbound(self)

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
        if w == "function":  # function f { ...; }: the name is not a program
            i += 2
            continue
        if w == "coproc":  # coproc NAME { ...; } names the coprocess; coproc cmd does not
            i += 2 if i + 2 < len(words) and words[i + 2] == "{" else 1
            continue
        name = os.path.basename(w)
        if name not in WRAPPERS or (name == "env" and env_split_string(words, i + 1)):
            break  # env -S runs a script, which nested_script() returns
        i += 1
        while i < len(words) and words[i].startswith("-") and words[i] != "-":
            opt = words[i]
            i += 1
            if opt == "--":
                break
            if wrapper_option_takes_value(name, opt):
                i += 1
        if name == "timeout" and i < len(words):
            i += 1  # the duration
        while name in ("env", "sudo") and i < len(words) and ASSIGNMENT.match(words[i]):
            assigns.append(words[i])
            i += 1
    return assigns, words[i:]


def env_split_string(words, i=1):
    """Returns (string, position) for the value of env's -S or --split-string in
    the options from words[i] on, or None: in a cluster such as -iS, and attached
    or as the next word. A -u or -C in a cluster takes the rest of the word."""
    while i < len(words) and words[i].startswith("-") and words[i] not in ("-", "--"):
        w = words[i]
        name, eq, value = w.partition("=")
        if len(name) > 2 and "--split-string".startswith(name):  # getopt_long takes --s, --split
            if eq:
                return value, i
            return (words[i + 1], i + 1) if i + 1 < len(words) else None
        if not w.startswith("--"):
            for k, letter in enumerate(w[1:], 1):
                if letter == "S":
                    if w[k + 1:]:
                        return w[k + 1:], i
                    return (words[i + 1], i + 1) if i + 1 < len(words) else None
                if letter in "uC":
                    break
        i += 2 if wrapper_option_takes_value("env", w) else 1
    return None


def wrapper_option_takes_value(name, opt):
    """Whether a wrapper's option word takes the next word as its value: one of
    its value options, an abbreviation getopt_long would expand to one (--un for
    env's --unset, --sig for timeout's --signal), or a cluster of short options
    whose last letter takes a value, as -iu FOO for env."""
    values = WRAPPERS[name]
    if opt in values:
        return True
    if opt.startswith("--"):
        if "=" in opt:
            return False
        longs = {o for o in values if o.startswith("--")} | WRAPPER_FLAGS.get(name, set())
        return any(o in values for o in longs if o.startswith(opt))
    short = {o[1] for o in values if len(o) == 2}
    for k, letter in enumerate(opt[1:], 1):
        if letter in short:  # it takes the rest of the word, or the next word if none is left
            return k == len(opt) - 1
    return False


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


GLOB_CHARS = set("*?[")


def enter(target, cwd):
    """Returns the directory cd or pushd enters, or None when it cannot be known.

    A glob is followed when it matches exactly one directory, as the shell does.
    """
    path = expand(target, cwd)
    if path is None or not GLOB_CHARS & set(path):
        return path
    matches = [m for m in glob.glob(path) if os.path.isdir(m)]
    return os.path.normpath(matches[0]) if len(matches) == 1 else None


class Parsed:
    """What parse_command() finds: the simple commands, the words to match, the text the
    parser stripped before splitting words, and whether a directory change was lost."""

    def __init__(self):
        self.commands = []
        self.words = []
        self.stripped = []
        self.lost_dir = False
        self.unclosed = False  # a $(...) or backtick span whose end was not found
        self.opaque = False  # a script nested past MAX_DEPTH, which is not parsed


def parse(text, cwd):
    """Returns (commands, words) for a command string, as parse_command() finds them.

    scripts/claude_policy_hook.py imports this, so its shape stays fixed.
    """
    found = parse_command(text, cwd)
    return found.commands, found.words


def parse_command(text, cwd, depth=0, found=None):
    """Returns a Parsed for a command string, descending into $(...), sh -c and eval.

    Words that only name a file or a directory are left out of found.words: the
    files an outbound gh command sends, cd, pushd and popd operands, and redirect
    targets, which simple_commands() keeps apart. So are scripts this parses on
    their own, whose words are added from that parse. Everything else is matched.
    """
    found = found if found is not None else Parsed()
    text, bodies = strip_heredocs(text)
    text, comments = strip_comments_and_continuations(text)
    found.stripped += bodies + comments
    # The commands keep their words as written, as callers that read them
    # expect, except that an unquoted $(...) becomes "$()", and a <(...) or
    # >(...) becomes "<(...)" or ">(...)", which holds a character that is not
    # punctuation, so it stays a word: their parentheses would otherwise split the
    # command around them, and the options after them, such as --body-file,
    # would land in a command of their own. The words matched come from a
    # second pass with every parsed span cut out, since its own parse matches
    # what it holds.
    command_text = matched_text = text
    if depth < MAX_DEPTH:
        spans = substitutions(text)
        found.unclosed = found.unclosed or not all(span[4] for span in spans)
        for _, _, script, _, _ in spans:
            parse_command(script, cwd, depth + 1, found)
        for start, end, _, quoted, _ in reversed(spans):
            cut = text[start] + "(...)" if text[start] in "<>" else "$()"
            cut = cut if quoted else f'"{cut}"'  # unquoted, the parentheses split words
            matched_text = matched_text[:start] + cut + matched_text[end:]
            if not quoted:
                command_text = command_text[:start] + cut + command_text[end:]
    elif substitutions(text):
        found.opaque = True
    stack = []
    for words, redirects in simple_commands(tokenize(command_text)):
        assigns, unwrapped = unwrap(words)
        cmd = Command(assigns, unwrapped, redirects, cwd)
        found.commands.append(cmd)
        if cmd.program in ("cd", "pushd", "popd"):
            args = [w for w in unwrapped[1:] if w == "-" or not w.startswith("-")]
            if cmd.program == "popd":
                cwd = stack.pop() if stack else None
            elif cmd.program == "pushd":
                stack.append(cwd)
                cwd = enter(args[0], cwd) if args else None
            else:
                cwd = None if args[:1] == ["-"] else enter(args[0] if args else "~", cwd)
            found.lost_dir = found.lost_dir or cwd is None
        script, _ = nested_script(cmd)
        if script is not None and depth < MAX_DEPTH:
            parse_command(script, cwd, depth + 1, found)
        elif script is not None:
            found.opaque = True
    for words, redirects in simple_commands(tokenize(matched_text)):
        # A here-string's target is text the command sends, not a file name.
        found.words += [t for op, t in redirects if op.endswith("<<<")]
        assigns, unwrapped = unwrap(words)
        cmd = Command(assigns, unwrapped, redirects, None)
        unmatched = dict(cmd.unmatched)
        if cmd.program in ("cd", "pushd", "popd"):
            unmatched.update((k, None) for k in range(1, len(unwrapped)))
        script, at = nested_script(cmd)
        if script is not None and depth < MAX_DEPTH:
            unmatched.update((k, None) for k in at)
        skipped = len(words) - len(unwrapped)  # assignments and wrappers stay matched
        for k, w in enumerate(words):
            w = unmatched.get(k - skipped, w) if k >= skipped else w
            if w is not None:
                found.words.append(w)
    return found


def substitutions(text):
    """Returns (start, end, script, quoted, closed) for each $(...) and backtick
    span outside single quotes, and each <(...) and >(...) process substitution
    outside any quotes: quoted says whether it is inside double quotes, and
    closed whether its end was found. Parentheses are counted without reading
    quotes, so "fix (wip" inside $(...) leaves the span unclosed.

    The shell runs them, quoted in double quotes or not, as in
    url="$(gh pr create ...)". Inside single quotes they are literal text, as
    in a PR body that quotes `git commit -n`. Inside double quotes, <( and >(
    are literal text too.
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
            bodies.append((i, min(end + 1, len(text)), text[i + 1:end], quote == '"', end < len(text)))
            i = end
        elif text.startswith("$(", i) or (quote is None and text[i:i + 2] in ("<(", ">(")):
            depth, j = 1, i + 2
            while j < len(text) and depth:
                depth += {"(": 1, ")": -1}.get(text[j], 0)
                j += 1
            bodies.append((i, j, text[i + 2:j - 1] if depth == 0 else text[i + 2:], quote == '"',
                           depth == 0))
            i = j - 1
        i += 1
    return bodies


# A shell's option grammar is not modelled exactly: three attempts each opened a
# fail-open (#117). Every word after the first that could be a -c is parsed as a
# script, and a shell counts as an interpreter unless plain_shell_script() names
# its one script, which only removes the false positive of a -c beside a post.
PLAIN_SHELL_LETTERS = set("ceuxvlo")
STARTUP_VARIABLES = ("BASH_ENV=", "ENV=", "ZDOTDIR=")  # each names a file a shell runs at start
EXPORTERS = {"export", "declare", "typeset", "readonly", "local"}  # -e -u -x -v -l -o and -c, none a bash long option


def shell_candidates(words):
    """Returns the positions of every word a shell could run as a -c script: each
    word after the first option word, -c or +c in any cluster, that holds a c.
    Values such as pipefail, and options such as --, are parsed too, harmlessly;
    a script may itself start with - or +, as in bash -c -- '-x; ...'."""
    first = next((j for j, w in enumerate(words[1:], 1)
                  if w[:1] in ("-", "+") and not w.startswith("--") and "c" in w), None)
    if first is None:
        return []
    return list(range(first + 1, len(words)))


def plain_shell_script(cmd):
    """Whether this shell runs exactly one -c script, with only the options in
    PLAIN_SHELL_LETTERS before it and no startup file: bash -c '...' or
    bash -euo pipefail -c '...'. Anything else counts as an interpreter."""
    if any(a.startswith(STARTUP_VARIABLES) for a in cmd.assigns):
        return False
    words, j, run = cmd.words, 1, False
    while j < len(words) and words[j][:1] in ("-", "+"):
        w = words[j]
        if w == "--":
            j += 1
            break
        if len(w) < 2 or not set(w[1:]) <= PLAIN_SHELL_LETTERS:
            return False
        run = run or (w[0] == "-" and "c" in w)
        j += 1 + w[1:].count("o")
    return run and j < len(words)


def nested_script(cmd):
    """Returns (script, positions): the script that sh -c, eval or env -S runs, or
    None, and the positions of the words that hold it.

    For a shell, the script is every word shell_candidates() finds, one per
    line. env runs its split string with the words after it.
    """
    if cmd.program == "eval" and len(cmd.words) > 1:
        return " ".join(cmd.words[1:]), range(1, len(cmd.words))
    if cmd.program == "env":  # unwrap() leaves env in place only for -S
        found = env_split_string(cmd.words)
        if found is None:
            return None, []
        script, at = found
        rest = [shlex.quote(w) for w in cmd.words[at + 1:]]
        return " ".join([script] + rest), range(at, len(cmd.words))
    if cmd.program in SHELLS:
        at = shell_candidates(cmd.words)
        if at:
            return "\n".join(cmd.words[k] for k in at), at
    return None, []


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
FD_PATH = re.compile(r"^/(dev|proc/[^/]+)/fd/[0-9]+$")


def option_at(words, names):
    """Yields (value, position, kept) for each value given to any of the named
    options, in every spelling: the position of the word that holds the value, and
    what is left of that word without it (None when the value is the whole word)."""
    for i, w in enumerate(words):
        for n in names:
            if w == n and i + 1 < len(words):
                yield words[i + 1], i + 1, None
            elif n.startswith("--") and w.startswith(n + "="):
                yield w[len(n) + 1:], i, n + "="
            elif not n.startswith("--") and w.startswith(n) and len(w) > len(n):
                yield w[len(n):], i, n


def option(words, names):
    """Yields each value given to any of the named options, in every spelling."""
    return (value for value, _, _ in option_at(words, names))


def gh_outbound(cmd):
    """Returns (outbound, files, unmatched): whether this is a gh write, the files
    it sends, and the words that only name those files, as {position in cmd.words:
    what of the word stays matched}. gh sends a file's contents, never its path.
    """
    if cmd.program != "gh":
        return False, [], {}
    args = cmd.words[1:]
    while args and args[0].startswith("-"):
        args = args[1:]
    if not args:
        return False, [], {}
    group, rest = args[0], args[1:]
    while rest and rest[0].startswith("-"):  # gh issue -R o/r comment ...
        rest = rest[2:] if rest[0] in ("-R", "--repo") else rest[1:]
    verb = rest[0] if rest else ""
    base = len(cmd.words) - len(rest)
    files, unmatched = [], {}

    def named(names):
        for value, at, kept in option_at(rest, names):
            files.append(value)
            unmatched[base + at] = kept

    if group in GH_TEXT_VERBS and verb in GH_TEXT_VERBS[group]:
        named(GH_FILE_FLAGS)
    elif group in ("pr", "issue") and verb in ("close", "reopen"):
        if not list(option(rest, {"--comment", "-c"})):
            return False, [], {}
    elif group == "api":
        methods = [m.upper() for m in option(rest, {"-X", "--method"})]
        fields = list(option(rest, GH_API_FIELDS))
        inputs = list(option(rest, {"--input"}))
        if not (fields or inputs or any(m != "GET" for m in methods)):
            return False, [], {}
        named({"--input"})
        # Only -F/--field reads a file: when the value after its first = starts
        # with @, as gh's magicFieldValue does. -f/--raw-field sends text as it is.
        for value, at, _ in option_at(rest, {"-F", "--field"}):
            path = value.partition("=")[2]
            if path.startswith("@"):
                files.append(path[1:])
                word = rest[at]
                unmatched[base + at] = word[:len(word) - len(path)]
    else:
        return False, [], {}
    stdin = PIPED_STDIN if (s := standard_input(cmd.redirects)) is None else s
    files = ["-" if f in STDIN_PATHS else f for f in files]
    files = [f for f in (stdin if f == "-" else f for f in files) if f != HEREDOC_STDIN]
    return True, files, unmatched


UNKNOWN_STDIN = "\ue001"  # a standard input the hook cannot follow, such as <&3 with fd 3 unknown


HEREDOC_STDIN = "\ue002"  # standard input is a heredoc or here-string, whose text is in the command
PIPED_STDIN = "\ue003"  # no redirect sets standard input: a pipe, or a compound command's redirect


def standard_input(redirects):
    """Returns what a command's standard input reads: the file of its last plain
    < (0< is stored as <), HEREDOC_STDIN, None when no redirect sets it, or
    UNKNOWN_STDIN for any other redirect onto fd 0: <>, <&N or 0>&N.

    Fail-safe rather than exact (#118): a dup onto standard input is not
    followed through the fds it copies, so it is denied."""
    stdin = None
    for op, target in redirects:
        if op == "<":
            # /dev/stdin, /dev/fd/N and /proc/*/fd/N reopen an fd the hook does not follow.
            stdin = UNKNOWN_STDIN if target in STDIN_PATHS or FD_PATH.match(target) else target
        elif op in ("<<", "<<<"):
            stdin = HEREDOC_STDIN
        elif op in ("<>", "<&", "0>&"):  # redirect() keeps a number on any fd but 0
            stdin = UNKNOWN_STDIN
    return stdin


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
UNFOLLOWED = ("The hook could not follow a change of directory in this command, such as one to "
              "a variable, cd -, popd, or a glob that matches no directory or several, so a "
              "relative path after it does not resolve.")
INTERPRETED = ("An interpreter, such as python3, node or perl, a script, a program named by a "
               "variable, or a command nested too deep for the hook to read runs in this "
               "command, and can rewrite any file.")
PROCESS_SUBSTITUTIONS = {"<(...)", ">(...)"}  # the words parse_command() leaves for <(...) and >(...)
FALLBACK_FILE_FLAGS = re.compile(r"--body-file|--notes-file|--input|\s-F|=@")


WRITE_REDIRECTS = {">", ">>", ">|", "&>", "&>>"}
COPIERS = {"cp", "mv", "install", "ln"}  # the last operand is written
IN_PLACE_EDITORS = {"sed", "gsed", "perl"}


def edits_in_place(cmd):
    """Whether sed or perl edits its files in place: -i, -i<suffix>, an option
    cluster holding i such as -Ei or -pi, or sed's --in-place[=<suffix>]."""
    if cmd.program not in IN_PLACE_EDITORS:
        return False
    for w in cmd.words[1:]:
        if w == "--":
            return False
        if cmd.program != "perl" and w.startswith("--in-place"):
            return True
        if w.startswith("-") and not w.startswith("--") and "i" in w[1:]:
            return True
    return False


# Programs that run code the hook cannot read, which can write any file (#111).
# Case-insensitive, since macOS's file system runs Python3 as python3.
INTERPRETER = re.compile(r"^(python|pypy|perl|php|lua|ruby|node|nodejs)[0-9.]*$|"
                         r"^(deno|bun|luajit|rscript|awk|gawk|mawk|nawk)$", re.I)
SCRIPT_EXTENSIONS = (".py", ".pyw", ".sh", ".bash", ".zsh", ".ksh", ".js", ".mjs", ".cjs", ".jsx",
                     ".ts", ".mts", ".cts", ".tsx", ".rb", ".pl", ".php", ".lua", ".r", ".awk")


def interprets(cmd):
    """Whether this command runs code the hook cannot read: an interpreter, with
    its code given inline, in a heredoc or in a file; a shell that runs a script
    or standard input, or with options beyond the plain ones (plain_shell_script()); a
    script read by source or .; a script run by its path; or a program named
    when the command runs, as in $PY fix.py, which may be any of these."""
    if INTERPRETER.match(cmd.program):
        return True
    # A startup file set anywhere, as in export BASH_ENV=f; bash -c '...', runs
    # in any shell the command starts later.
    if any(a.startswith(STARTUP_VARIABLES) for a in cmd.assigns) or (
            cmd.program in EXPORTERS and any(w.startswith(STARTUP_VARIABLES) for w in cmd.words[1:])):
        return True
    if cmd.words and ("$" in cmd.words[0] or "`" in cmd.words[0]):
        return True
    if cmd.program in ("source", ".") and len(cmd.words) > 1:
        return True
    if cmd.program in SHELLS:
        return not plain_shell_script(cmd)
    return bool(cmd.words) and "/" in cmd.words[0] and cmd.words[0].lower().endswith(SCRIPT_EXTENSIONS)


class Written:
    """The paths the commands write: from a heredoc, any other way, as globs,
    whether an in-place editor names a file the hook cannot resolve, and whether
    an interpreter runs, which can write any file."""

    def __init__(self):
        self.heredoc, self.other, self.globs = set(), set(), []
        self.unknown = False
        self.interpreter = False

    def rewrites(self, path):
        return (path in self.other or self.unknown or self.interpreter
                or any(fnmatch.fnmatchcase(path, g) for g in self.globs))


def written_paths(cmd, written):
    """Adds the paths a command writes to written.

    A file written from a heredoc, as in cat > F <<'EOF', holds text that is
    part of the command itself. A file written any other way holds text the
    hook cannot see until the command runs. An in-place editor writes every
    file it names, and the hook cannot tell its script from its files, so every
    operand counts; a glob counts for each file it matches, and an operand the
    hook cannot resolve counts for every file. An interpreter counts for every
    file.
    """
    written.interpreter = written.interpreter or interprets(cmd)
    targets = [t for op, t in cmd.redirects if op in WRITE_REDIRECTS]
    operands = [w for w in cmd.words[1:] if not w.startswith("-")]
    if cmd.program == "tee":
        targets += operands
    elif cmd.program in COPIERS and operands:
        targets.append(operands[-1])
    elif edits_in_place(cmd):
        for op in operands:
            path = expand(op, cmd.cwd)
            if path is None:
                written.unknown = True
            elif GLOB_CHARS & set(op):
                written.globs.append(path)
            else:
                targets.append(op)
    paths = [p for p in (expand(t, cmd.cwd) for t in targets) if p]
    # Only cat or tee with no input file but the heredoc, as in cat > F <<'EOF'.
    # cat header.md - > F <<'EOF' also writes header.md, and a later < file
    # replaces the heredoc as stdin; the hook cannot see either file's text.
    inputs = operands if cmd.program == "cat" else []
    ops = [op for op, _ in cmd.redirects]
    if ("<<" in ops and not {"<", "<>", "<&"} & set(ops) and cmd.program in ("cat", "tee")
            and all(w == "-" for w in inputs)):
        written.heredoc.update(paths)
    else:
        written.other.update(paths)

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
            data = f.read(MAX_BODY_BYTES + 1)
    except OSError:
        raise Deny("a file this command sends to GitHub cannot be read, so it cannot be checked.")
    if len(data) > MAX_BODY_BYTES:  # it grew after the stat
        raise Deny("a file this command sends to GitHub is larger than 10 MiB, so it is not checked.")
    return data.decode("utf-8", "replace")


def decide(command, cwd):
    """Returns None to allow, or a note to show. Raises Deny."""
    try:
        found = parse_command(command, cwd)
    except ValueError:
        found = None

    outbound = False
    files = []  # resolved paths, None where the path cannot be known
    substituted = False  # a file sent is a <(...) or >(...)
    unknown_stdin = False  # --body-file - reads a standard input the hook cannot follow
    piped_stdin = False  # --body-file - reads a standard input no redirect on its command sets
    written = Written()
    if found is None:
        has_git = "git" in command
        for pattern, what, needs_git in FALLBACK_ESCAPES:
            if pattern.search(command) and (has_git or not needs_git):
                raise Deny(f"{what} {ESCAPE_REASON}")
        outbound = re.search(r"(^|[\s;&|(/`])gh\s", command) is not None
        if outbound and FALLBACK_FILE_FLAGS.search(command):
            raise Deny("this command cannot be split into words, so the files it sends to "
                       "GitHub cannot be checked. Rewrite it with balanced quotes.")
    else:
        for cmd in found.commands:
            what = escape(cmd)
            if what:
                raise Deny(f"{what} {ESCAPE_REASON}")
        written.interpreter = found.opaque
        for cmd in found.commands:
            written_paths(cmd, written)
            if cmd.outbound:
                outbound = True
                unknown_stdin = unknown_stdin or UNKNOWN_STDIN in cmd.files
                piped_stdin = piped_stdin or PIPED_STDIN in cmd.files
                files += [expand(f, cmd.cwd) for f in cmd.files if f not in (UNKNOWN_STDIN, PIPED_STDIN)]
                substituted = substituted or any(f in PROCESS_SUBSTITUTIONS for f in cmd.files)
    if not outbound:
        return None
    entries = read_list()
    if entries is None:
        return ("leak hook: value rules skipped: no global value list declared "
                f"({LIST_KEY}), so the text this command sends to GitHub was not checked.")

    if found is not None and found.unclosed:
        # The span runs to the end of the text, so the options after it never
        # reach the gh command, and its files would go unread.
        raise Deny("a $(...), <(...), >(...) or backtick substitution in this command does not "
                   "close where the hook can tell, so the files it sends to GitHub cannot be "
                   "checked. Balance its parentheses, quotes included, or build the text in an "
                   "earlier step.")
    if substituted:
        raise Deny("a file this command sends to GitHub is a process substitution, <(...) or "
                   ">(...), whose text is made when the command runs, so it cannot be checked. "
                   "Write the file in one step, then post it in the next.")

    # A redirect on a compound command, { ...; } <f or while ...; done <f, sets
    # the standard input of the gh command inside it, which the hook does not
    # follow: } and done are not programs, and ( ... ) <f leaves no words at all.
    if piped_stdin and found is not None and any(
            not cmd.words and any(op.lstrip("0123456789").startswith("<") or op == "0>&"
                                  for op, _ in cmd.redirects)
            for cmd in found.commands):
        unknown_stdin = True
    if unknown_stdin:
        raise Deny("this command sends its standard input to GitHub from a redirect the hook cannot "
                   "follow, such as <&3, so it cannot be checked. Write the file in one step, then "
                   "post it with --body-file in the next.")

    # A parsed command is matched without the words that only name a file or a
    # directory (parse_command()); one that cannot be split is matched whole.
    texts = [command] if found is None else found.stripped + [" ".join(found.words)]
    if "$'" in command:  # the parser does not read $'...' quoting, so match it whole
        texts.append(command)
    for path in files:
        rewritten = path is not None and written.rewrites(path)
        if rewritten or path is None or not os.path.exists(path):
            if path in written.heredoc and not rewritten:
                continue
            lost = (UNFOLLOWED + " ") if path is None and found is not None and found.lost_dir else ""
            if written.interpreter:
                lost += INTERPRETED + " "
            raise Deny("a file this command sends to GitHub is written by the same command, or "
                       f"does not exist yet, so it cannot be checked. {lost}Write the file in one "
                       "step, then post it in the next.")
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
