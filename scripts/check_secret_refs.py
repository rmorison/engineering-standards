#!/usr/bin/env python3
"""Checks that a secret reference file holds references and nothing else.

The rule lives in code/python-standards.md (Configuration Management >
Secrets): a project commits `secret-refs.env`, whose every value is a
reference into a secret manager, never the secret itself. Unlike its two
sibling scripts, this check is preventive: no shipped defect prompted it. It
exists so that the rule's central promise, "this file holds no secret", is
decided by a program rather than trusted to review.

It is written in Python, with the standard library only, so that a Python
project adopting the rule runs it with the interpreter it already has. Copy it
into the project's `scripts/` directory; `make security` runs it when
`secret-refs.env` exists.

  1. The line classifier passes its built-in fixtures before it reports on any
     file (LINE_FIXTURES, FILE_FIXTURES), as do the argument parser
     (ARGV_FIXTURES), the example-block finder (BLOCK_FIXTURES) and the rule
     that messages never repeat a pasted secret (LEAK_FIXTURES). A classifier
     that is wrong would otherwise pass a literal as confidently as it passes
     a reference.
  2. Every line of a reference file is a full-line comment, a blank line, or
     `KEY=reference`, where the reference matches one grammar in
     REFERENCE_GRAMMARS and is the whole value. A commented-out entry whose
     value is not a reference fails too. Anything else fails: quotes,
     `export`, `$`, an inline comment, whitespace in a value, a YAML-style
     `KEY: value`. Dotenv parsers disagree about each of those, so a file
     that one of them reads differently from this check is not safe to pass.
  3. No key repeats, and no key has a browser-exposed prefix: a build tool
     inlines NEXT_PUBLIC_ and similar values into client bundles.
  4. Every named file exists, and a reference file has at least one entry. A
     check over nothing reports the same "passed" as a check over everything.
  5. No key appears in both a reference file and a configuration file, and at
     least one configuration file is named, so the rule cannot be skipped by
     leaving the configuration file out. Configuration files are read
     leniently, but a line this script cannot read as a key fails, because a
     skipped line could hide a shared key.
  6. With --standard, the `# secret-refs.env` and `# example.env` example
     blocks in code/python-standards.md each appear exactly once and pass
     checks 2-5, so the standard cannot show an example its own rule rejects.

A pass means only that the named files are well-formed. It does not mean a
reference resolves, that no secret sits in some other file, that every key in
the reference file really is a secret, or that a value shaped like a
reference is not a pasted secret: `op://dev/stripe/<pasted key>` passes. A
comment is checked only for a commented-out entry; other free text in a
comment is not read.

Messages name the file and line, and a key only when the line's value is a
well-formed reference; never the value. On any other line the text before
`=` may be the secret itself, and messages reach CI logs.

Usage:  python3 scripts/check_secret_refs.py --standard
        python3 scripts/check_secret_refs.py <reference-file>... --config <configuration-file>...
Exits non-zero if any check fails. Python 3.10 or later, standard library only.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STANDARD = os.path.join(REPO_ROOT, "code", "python-standards.md")

# Character classes are spelled out rather than taken from `\s`, `\w` or `.`:
# Python's are Unicode-aware and differ from the ones this rule was first
# written against, and a difference there is a difference in which lines pass.
WHITESPACE = (
    "\t\n\v\f\r \u00a0\u1680"
    + "".join(chr(code) for code in range(0x2000, 0x200B))
    + "\u2028\u2029\u202f\u205f\u3000\ufeff"
)
NOT_LINE_END = "[^\n\r\u2028\u2029]"

# The reference grammars this check accepts. Each entry records where its
# syntax was verified. Only 1Password's ships; a project using doppler, sops or
# HashiCorp Vault adds an entry with its own source, which keeps the rule
# tool-neutral while the shipped default stays verified.
#
# A segment admits only letters, digits, `.`, `_` and `-`. Listing what a
# segment may contain, rather than what it may not, keeps out shell
# metacharacters, control characters and non-ASCII, any of which would make a
# committed file dangerous to source by mistake.
SEGMENT = r"[A-Za-z0-9._-]+"
REFERENCE_GRAMMARS: list[dict[str, Any]] = [
    {
        "name": "1Password",
        # op://<vault-name>/<item-name>[/<section-name>]/<field-name>
        "source": "@1password/sdk 0.5.0 (npm, published by 1Password), checked 2026-09-24",
        "pattern": re.compile(rf"op://{SEGMENT}/{SEGMENT}(?:/{SEGMENT})?/{SEGMENT}"),
    },
]

KEY = re.compile(r"[A-Z_][A-Z0-9_]*")
BROWSER_EXPOSED_PREFIXES = ("NEXT_PUBLIC_", "VITE_", "REACT_APP_", "PUBLIC_")

BLANK = re.compile(r"[ \t]*")
ENTRY = re.compile(rf"([A-Za-z0-9_]+)=({NOT_LINE_END}*)")
COMMENTED_ENTRY = re.compile(
    rf"#[#{WHITESPACE}]*(?:export[{WHITESPACE}]+)?[A-Za-z_][A-Za-z0-9_]*[{WHITESPACE}]*=({NOT_LINE_END}*)"
)
CONFIG_ENTRY = re.compile(r"(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*=")
FENCE_OPEN = re.compile(r"(`{3,}|~{3,})")
FENCE_CLOSE = re.compile(r"(`{3,}|~{3,})[ \t]*")
LINE_BREAK = re.compile(r"\r\n|\r|\n")


def is_reference(value: str) -> bool:
    return any(grammar["pattern"].fullmatch(value) for grammar in REFERENCE_GRAMMARS)


def trim(value: str) -> str:
    """Strips what JavaScript's String.prototype.trim strips, which differs from str.strip()."""
    return value.strip(WHITESPACE)


@dataclass
class Line:
    kind: str
    key: str | None = None
    reason: str | None = None


def classify_line(line: str) -> Line:
    """Classifies one reference-file line as blank, comment, reference, literal,
    exposed or malformed. Only blank, comment and reference pass. `reason` says
    why a line failed without repeating its value. `key` is returned only when
    the value is a well-formed reference: on any other line, the text before the
    first `=` may itself be a pasted secret, such as padded base32 or base64.
    """
    if BLANK.fullmatch(line):
        return Line("blank")
    if line.startswith("#"):
        return classify_comment(line)

    entry = ENTRY.fullmatch(line)
    if not entry or not KEY.fullmatch(entry.group(1)):
        return Line(
            "malformed",
            reason="is not a comment, a blank line or an UPPER_SNAKE_CASE KEY=reference",
        )
    key, value = entry.group(1), entry.group(2)
    if not is_reference(value):
        return Line("literal", reason=literal_reason(value))
    if key.startswith(BROWSER_EXPOSED_PREFIXES):
        return Line(
            "exposed",
            key=key,
            reason="has a browser-exposed prefix, so a build tool would inline it into client code",
        )
    return Line("reference", key=key)


def classify_comment(line: str) -> Line:
    """A comment passes unless it is a commented-out entry whose value is not a
    reference, such as `# STRIPE_API_KEY=<old value>` left behind after a
    migration. The match is deliberately loose (repeated `#`, `export`, spaces
    around `=`, any case), so a free-text comment shaped like `name=value` fails
    too. Other free text in a comment is not checked.
    """
    entry = COMMENTED_ENTRY.fullmatch(line)
    if entry and not is_reference(trim(entry.group(1))):
        return Line("literal", reason="is a commented-out entry whose value is not a reference")
    return Line("comment")


def literal_reason(value: str) -> str:
    """Why a value is not a reference, in words that do not repeat the value."""
    if value == "":
        return "has an empty value"
    if value[:1] in ('"', "'"):
        return "has a quoted value"
    if "$" in value:
        return "has a `$` in its value"
    if re.search(r"[ \t]#", value):
        return "has an inline comment"
    if re.search(f"[{WHITESPACE}]", value):
        return "has whitespace in its value"
    if value.startswith("op://"):
        return "has an op:// value that is not a well-formed reference"
    return "has a value that is not a reference"


def lines_of(text: str) -> list[str]:
    """Splits file text into lines, dropping a byte-order mark. CRLF, a lone CR
    and LF each end a line, as they do for python-dotenv; splitting on LF alone
    would let a CR hide an entry inside a comment.
    """
    if text.startswith("\ufeff"):
        text = text[1:]
    return LINE_BREAK.split(text)


Report = Callable[[int | None, str, str], None]


def check_reference_text(text: str, report: Report) -> dict[str, int]:
    """Checks a reference file's text. `report(index, check, message)` receives
    the zero-based line index, or None for a whole-file failure. Returns the
    keys the file defines, each mapped to its line index.
    """
    keys: dict[str, int] = {}
    for index, line in enumerate(lines_of(text)):
        result = classify_line(line)
        if result.kind in ("malformed", "literal", "exposed"):
            subject = f"`{result.key}`" if result.key else "This line"
            report(index, result.kind, f"{subject} {result.reason}")
            continue
        if result.kind != "reference":
            continue
        assert result.key is not None
        if result.key in keys:
            report(
                index,
                "duplicate",
                f"`{result.key}` is also defined on line {keys[result.key] + 1} of this file",
            )
            continue
        keys[result.key] = index
    if not keys:
        report(
            None, "empty", "defines no references; a reference file with no entries checks nothing"
        )
    return keys


def configuration_keys(text: str, report: Report) -> dict[str, int]:
    """Reads a configuration file's keys, failing on any line it cannot read."""
    keys: dict[str, int] = {}
    for index, line in enumerate(lines_of(text)):
        if BLANK.fullmatch(line) or re.match(r"[ \t]*#", line):
            continue
        entry = CONFIG_ENTRY.match(line)
        if not entry:
            report(
                index, "unreadable", "is not a KEY=value line, so a key it holds could be missed"
            )
            continue
        keys.setdefault(entry.group(1), index)
    return keys


@dataclass
class Keyed:
    keys: dict[str, int]
    label: str = ""
    path: str = ""


def check_disjoint(
    references: list[Keyed],
    configurations: list[Keyed],
    report: Callable[[Keyed, int, str, str], None],
) -> None:
    """Fails every key a reference file shares with a configuration file."""
    for ref in references:
        for key, index in ref.keys.items():
            for config in configurations:
                if key in config.keys:
                    report(
                        ref,
                        index,
                        "shared-key",
                        f"`{key}` is also defined in {config.label}; secrets and configuration share no key",
                    )


# Line fixtures: (line, expected kind). Every must-fail case the plan names is
# here, so a change that loosens the classifier fails before any file is read.
# Literal values are obviously fake and in no provider's format, so they cannot
# trip GitHub push protection.
LINE_FIXTURES: list[tuple[str, str]] = [
    # Happy path
    ("STRIPE_API_KEY=op://dev/stripe/credential", "reference"),
    ("API_KEY=op://dev/app/api/key", "reference"),
    ("KEY=op://dev.vault/my_item/field-1", "reference"),
    ("# rotated 2026-09", "comment"),
    ("# STRIPE_API_KEY=op://dev/stripe/credential", "comment"),
    ("# STRIPE_API_KEY = op://dev/stripe/credential", "comment"),
    ("# rotated=2026-09 by ops", "literal"),
    ("# see https://example.com/?a=b", "comment"),
    ("#", "comment"),
    ("", "blank"),
    ("   ", "blank"),
    # Known limit, recorded rather than hidden: a secret pasted in as segments
    # passes, because it is shaped like a reference. See the header.
    ("KEY=op://hunter2/hunter2/hunter2", "reference"),
    # Literals
    ("KEY=hunter2", "literal"),
    ("KEY=", "literal"),
    ("KEY=not-a-reference", "literal"),
    # Rejected syntax
    ('KEY="op://dev/a/b"', "literal"),
    ("KEY='op://dev/a/b'", "literal"),
    ("export KEY=op://dev/a/b", "malformed"),
    ("KEY=${OTHER}", "literal"),
    ("KEY=op://${VAULT}/a/b", "literal"),
    ("KEY=op://dev/a/b # note", "literal"),
    # A reference that is not the whole value
    ("DATABASE_URL=postgres://u:op://dev/a/b@h/d", "literal"),
    ("KEY=hunter2 op://dev/a/b", "literal"),
    # Malformed references
    ("KEY=op://My Vault/a/b", "literal"),
    ("KEY=op://dev/a", "literal"),
    ("KEY=op://a/b/c/d/e", "literal"),
    ("KEY=op://dev//b", "literal"),
    ("KEY=op://dev/a/b?attribute=otp", "literal"),
    ("KEY=https://user:pass@host", "literal"),
    ("KEY=OP://dev/a/b", "literal"),
    # Shell metacharacters, a control character and non-ASCII inside a segment
    *[
        (f"KEY=op://dev/stripe/a{ch}b", "literal")
        for ch in [
            ";",
            "`",
            "|",
            "&",
            "'",
            '"',
            "\\",
            "(",
            ")",
            "<",
            ">",
            "#",
            "*",
            "\u0007",
            "\u00e9",
        ]
    ],
    # Browser exposure
    ("NEXT_PUBLIC_STRIPE_KEY=op://dev/stripe/credential", "exposed"),
    ("VITE_API_KEY=op://dev/a/b", "exposed"),
    ("REACT_APP_KEY=op://dev/a/b", "exposed"),
    ("PUBLIC_KEY=op://dev/a/b", "exposed"),
    # Malformed lines
    ("op://dev/a/b", "malformed"),
    ("KEY: op://dev/a/b", "malformed"),
    ("KEY = op://dev/a/b", "malformed"),
    ("1KEY=op://dev/a/b", "malformed"),
    ("lower=op://dev/a/b", "malformed"),
    ("  KEY=op://dev/a/b", "malformed"),
    ("  # an indented comment", "malformed"),
    # A commented-out entry left behind after a migration still holds its value
    ("# STRIPE_API_KEY=hunter2", "literal"),
    ("#STRIPE_API_KEY=hunter2", "literal"),
    ("# STRIPE_API_KEY=", "literal"),
    ("# export STRIPE_API_KEY=hunter2", "literal"),
    ("# STRIPE_API_KEY = hunter2", "literal"),
    ("## STRIPE_API_KEY=hunter2", "literal"),
    ("# stripe_api_key=hunter2", "literal"),
    ("KEY-NAME=op://dev/a/b", "malformed"),
    # Characters whose regex class differs between languages. A value holding a
    # Unicode line separator is not a whole-line entry; a non-ASCII letter is
    # not a key character.
    ("KEY=op://dev/a/b\u2028", "malformed"),
    ("# STRIPE_API_KEY=op://dev/a/b\u00a0", "comment"),
    ("KEY=op://dev/a/b\u00a0", "literal"),
    ("K\u00c9Y=op://dev/a/b", "malformed"),
    # A commented-out entry's value is trimmed of JavaScript's whitespace set,
    # which includes a byte-order mark but not the \x1c-\x1f separators.
    ("# KEY=op://dev/a/b\ufeff", "comment"),
    ("# KEY=op://dev/a/b\x1c", "literal"),
]

# File fixtures: a reference file, the configuration files beside it, and the
# checks expected to fail. An empty list means the fixture must pass.
FILE_FIXTURES: list[dict[str, Any]] = [
    {
        "name": "valid file",
        "refs": "A=op://dev/a/b\n# c\n\nB=op://dev/b/c\n",
        "configs": ["C=1\n"],
        "fails": [],
    },
    {
        "name": "CRLF endings",
        "refs": "A=op://dev/a/b\r\nB=op://dev/b/c\r\n",
        "configs": ["C=1\r\n"],
        "fails": [],
    },
    {
        "name": "byte-order mark",
        "refs": "\ufeffA=op://dev/a/b\n",
        "configs": ["C=1\n"],
        "fails": [],
    },
    # python-dotenv ends a line at a lone CR, so a literal hidden behind one in a
    # comment is a real entry to it and must be one here.
    {
        "name": "lone CR hides an entry",
        "refs": "# note\rA=hunter2\nB=op://dev/b/c\n",
        "configs": ["C=1\n"],
        "fails": ["literal"],
    },
    {
        "name": "lone CR endings",
        "refs": "A=op://dev/a/b\rB=op://dev/b/c\r",
        "configs": ["C=1\r"],
        "fails": [],
    },
    {
        "name": "repeated key",
        "refs": "A=op://dev/a/b\nA=op://dev/a/c\n",
        "configs": ["C=1\n"],
        "fails": ["duplicate"],
    },
    {
        "name": "no entries",
        "refs": "# only a comment\n\n",
        "configs": ["C=1\n"],
        "fails": ["empty"],
    },
    {"name": "empty file", "refs": "", "configs": ["C=1\n"], "fails": ["empty"]},
    {
        "name": "shared key",
        "refs": "A=op://dev/a/b\n",
        "configs": ["A=local\n"],
        "fails": ["shared-key"],
    },
    {
        "name": "shared key, export form",
        "refs": "A=op://dev/a/b\n",
        "configs": ["export A=local\n"],
        "fails": ["shared-key"],
    },
    {
        "name": "unreadable configuration line",
        "refs": "A=op://dev/a/b\n",
        "configs": ["not a key line\n"],
        "fails": ["unreadable"],
    },
]

# Argument fixtures: (argv, expected mode). Every run goes through parse_args,
# so a regression here would fail every adopter's invocation.
ARGV_FIXTURES: list[tuple[list[str], str]] = [
    (["--standard"], "standard"),
    (["refs.env", "--config", "example.env"], "files"),
    (["a.env", "b.env", "--config", "x.env", "--config", "y.env"], "files"),
    ([], "usage"),
    (["refs.env"], "usage"),
    (["refs.env", "--config"], "usage"),
    (["--standard", "refs.env"], "usage"),
    (["--verbose", "refs.env", "--config", "example.env"], "usage"),
]

# Block fixtures: Markdown lines, and the bodies marked_blocks finds for `# m`.
BLOCK_FIXTURES: list[dict[str, Any]] = [
    {"name": "one block", "lines": ["```bash", "# m", "A=1", "```"], "bodies": ["# m\nA=1\n"]},
    {"name": "no marker", "lines": ["```bash", "A=1", "```"], "bodies": []},
    {"name": "marker outside a fence", "lines": ["# m", "A=1"], "bodies": []},
    {"name": "marker is the whole line", "lines": ["```", "# m, and more", "```"], "bodies": []},
    {
        "name": "two blocks",
        "lines": ["```", "# m", "```", "text", "```", "# m", "```"],
        "bodies": ["# m\n", "# m\n"],
    },
    {
        "name": "shorter fence does not close",
        "lines": ["````", "# m", "```", "````"],
        "bodies": ["# m\n```\n"],
    },
    {
        "name": "other fence character does not close",
        "lines": ["~~~", "# m", "```", "~~~"],
        "bodies": ["# m\n```\n"],
    },
]

# Leak fixtures: lines that are a pasted secret, not an entry. Each must fail,
# and no message may repeat any part of it, since messages reach CI logs.
LEAK_FIXTURES = [
    "JBSWY3DPEHPK3PXPJBSWY3DP====",
    "dGhpc2lzYXNlY3JldGtleWJvZHk=",
    "lowercasesecretvalue=abcd",
    "KEY=hunter2hunter2",
    "# OLD_TOKEN=hunter2hunter2",
]


def check_texts(
    refs_text: str, config_texts: list[str], report: Callable[[str, str], None]
) -> None:
    """Runs the reference and configuration checks on in-memory texts."""
    refs = Keyed(
        check_reference_text(refs_text, lambda i, c, m: report(c, m)), label="the reference file"
    )
    configs = [
        Keyed(
            configuration_keys(text, lambda i, c, m: report(c, m)),
            label=f"configuration file {n + 1}",
        )
        for n, text in enumerate(config_texts)
    ]
    check_disjoint([refs], configs, lambda ref, i, c, m: report(c, m))


def self_test() -> list[str]:
    """Check 1: the classifier and file rules must pass their fixtures first."""
    problems = []
    for line, expected in LINE_FIXTURES:
        kind = classify_line(line).kind
        if kind != expected:
            problems.append(
                f"line fixture {json.dumps(line)} classified as {kind}, expected {expected}"
            )
    for fixture in FILE_FIXTURES:
        seen: list[str] = []

        def record(check: str, message: str, seen: list[str] = seen) -> None:
            seen.append(check)

        check_texts(fixture["refs"], fixture["configs"], record)
        got = ", ".join(sorted(set(seen))) or "no failures"
        want = ", ".join(sorted(fixture["fails"])) or "no failures"
        if got != want:
            problems.append(f'file fixture "{fixture["name"]}" produced {got}, expected {want}')
    for argv, expected in ARGV_FIXTURES:
        mode = parse_args(argv)["mode"]
        if mode != expected:
            problems.append(
                f"argument fixture {json.dumps(argv)} parsed as {mode}, expected {expected}"
            )
    for fixture in BLOCK_FIXTURES:
        got_bodies = [block["text"] for block in marked_blocks(fixture["lines"], "# m")]
        if got_bodies != fixture["bodies"]:
            problems.append(
                f'block fixture "{fixture["name"]}" found {json.dumps(got_bodies)}, expected {json.dumps(fixture["bodies"])}'
            )
    for line in LEAK_FIXTURES:
        messages: list[str] = []

        def collect(
            index: int | None, check: str, message: str, messages: list[str] = messages
        ) -> None:
            messages.append(message)

        # The valid entry keeps the file from failing as empty, so only the line counts.
        check_reference_text(f"{line}\nZ=op://dev/z/z\n", collect)
        parts = [part for part in line.split("=") if len(part) >= 4]
        if not messages:
            problems.append(f"leak fixture {json.dumps(line)} passed; it must fail")
        if any(part in message for message in messages for part in parts):
            problems.append(f"leak fixture {json.dumps(line)} is repeated in a failure message")
    return problems


def display_path(path: str) -> str:
    """A path as the person running the check would type it."""
    try:
        relative = os.path.relpath(path)
    except ValueError:  # on Windows, a path on another drive has no relative form
        return path
    return path if relative == "." else relative


@dataclass
class Failure:
    file: str
    line: int | None
    check: str
    message: str


failures: list[Failure] = []


def fail(file: str | None, line: int | None, check: str, message: str) -> None:
    failures.append(Failure(display_path(file) if file else "-", line, check, message))


def read_named(path: str) -> str | None:
    """Reads a named file, recording a failure when it cannot be read.

    newline="" passes line endings through unchanged, so lines_of alone
    decides where a line ends.
    """
    try:
        with open(path, encoding="utf-8", errors="replace", newline="") as handle:
            return handle.read()
    except FileNotFoundError:
        fail(path, None, "missing", "does not exist")
    except OSError:
        fail(path, None, "missing", "could not be read")
    return None


def file_reporter(path: str) -> Report:
    """Reports a failure against `path`, turning a zero-based index into a line number."""

    def report(index: int | None, check: str, message: str) -> None:
        fail(path, None if index is None else index + 1, check, message)

    return report


def check_files(ref_paths: list[str], config_paths: list[str]) -> int:
    """Checks reference files against configuration files, both given as paths."""
    refs = []
    for path in ref_paths:
        text = read_named(path)
        if text is None:
            continue
        keys = check_reference_text(text, file_reporter(path))
        refs.append(Keyed(keys, path=path))
    configs = []
    for path in config_paths:
        text = read_named(path)
        if text is None:
            continue
        keys = configuration_keys(text, file_reporter(path))
        configs.append(Keyed(keys, label=display_path(path), path=path))
    check_disjoint(
        refs, configs, lambda ref, i, check, message: fail(ref.path, i + 1, check, message)
    )
    return len(refs) + len(configs)


def marked_blocks(lines: list[str], marker: str) -> list[dict[str, Any]]:
    """Finds the fenced blocks whose first line is exactly `marker`. Returns each
    block's text and the Markdown line number of its first line. Only this much
    fence handling is needed, because the marker line identifies the block.
    """
    blocks = []
    for i in range(1, len(lines)):
        opened = FENCE_OPEN.match(lines[i - 1])
        if not opened or lines[i] != marker:
            continue
        fence = opened.group(1)

        def closes(line: str, fence: str = fence) -> bool:
            close = FENCE_CLOSE.fullmatch(line)
            return (
                close is not None
                and close.group(1)[0] == fence[0]
                and len(close.group(1)) >= len(fence)
            )

        body = []
        j = i
        while j < len(lines) and not closes(lines[j]):
            body.append(lines[j])
            j += 1
        blocks.append({"text": "\n".join(body) + "\n", "first_line": i + 1})
    return blocks


def check_standard() -> int:
    """Check 6: the standard's own example blocks."""
    text = read_named(STANDARD)
    if text is None:
        return 0
    lines = lines_of(text)
    found: dict[str, dict[str, Any] | None] = {}
    for marker in ("# secret-refs.env", "# example.env"):
        blocks = marked_blocks(lines, marker)
        if len(blocks) != 1:
            fail(
                STANDARD,
                blocks[1]["first_line"] if len(blocks) > 1 else None,
                "example",
                f"expected exactly one fenced block starting with `{marker}`, found {len(blocks)}",
            )
        found[marker] = blocks[0] if blocks else None
    refs_block = found["# secret-refs.env"]
    config_block = found["# example.env"]
    if not refs_block or not config_block:
        return 0

    def at(block: dict[str, Any]) -> Report:
        return lambda i, check, message: fail(
            STANDARD, block["first_line"] if i is None else block["first_line"] + i, check, message
        )

    refs = Keyed(check_reference_text(refs_block["text"], at(refs_block)))
    configs = [
        Keyed(
            configuration_keys(config_block["text"], at(config_block)),
            label="the `# example.env` block",
        )
    ]
    check_disjoint(
        [refs], configs, lambda ref, i, check, message: at(refs_block)(i, check, message)
    )
    return 2


def parse_args(argv: list[str]) -> dict[str, Any]:
    """Parses arguments into a mode, or records a usage failure."""
    if argv == ["--standard"]:
        return {"mode": "standard"}
    refs: list[str] = []
    configs: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] == "--config" and i + 1 < len(argv):
            configs.append(os.path.abspath(argv[i + 1]))
            i += 1
        elif argv[i].startswith("--"):
            return {"mode": "usage", "message": f"unknown or incomplete option {argv[i]}"}
        else:
            refs.append(os.path.abspath(argv[i]))
        i += 1
    if not refs:
        return {"mode": "usage", "message": "no reference file named"}
    if not configs:
        return {
            "mode": "usage",
            "message": "no --config file named, so the shared-key rule could not run",
        }
    return {"mode": "files", "refs": refs, "configs": configs}


def main(argv: list[str]) -> int:
    problems = self_test()
    if problems:
        print(
            f"\nThe classifier failed {len(problems)} of its own fixture(s), so no file was checked:\n",
            file=sys.stderr,
        )
        for problem in problems:
            print(f"  [self-test] {problem}", file=sys.stderr)
        print("", file=sys.stderr)
        return 1

    args = parse_args(argv)
    checked = 0
    if args["mode"] == "usage":
        fail(
            None,
            None,
            "usage",
            f"{args['message']}. Usage: check_secret_refs.py --standard | <reference-file>... --config <configuration-file>...",
        )
    elif args["mode"] == "standard":
        checked = check_standard()
    else:
        checked = check_files(args["refs"], args["configs"])

    if failures:
        print(f"\n{len(failures)} problem(s) found:\n", file=sys.stderr)
        for f in failures:
            line = "-" if f.line is None else f.line
            print(f"  {f.file}:{line}  [{f.check}] {f.message}", file=sys.stderr)
        print("", file=sys.stderr)
        return 1

    print(
        f"Checked {checked} file(s) or example block(s) against {len(REFERENCE_GRAMMARS)} reference "
        f"grammar(s), after {len(LINE_FIXTURES)} line, {len(FILE_FIXTURES)} file, {len(ARGV_FIXTURES)} "
        f"argument, {len(BLOCK_FIXTURES)} block and {len(LEAK_FIXTURES)} leak fixtures passed."
    )
    print(
        "All secret reference checks passed. That means the files are well-formed, not that no secret is present."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
