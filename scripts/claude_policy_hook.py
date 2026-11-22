#!/usr/bin/env python3
"""A Claude Code PreToolUse hook: agent sessions don't merge or change repository settings.

process/repository-standards.md owns the rules this enforces (Guarding Repository
Authority). It assumes a human in the loop, the operator, who signs off on work
and owns repository settings. On Track 1, the default, the operator also merges
in the GitHub web UI, and sessions post as the operator's account, so GitHub
cannot tell a session from the operator; this hook is what keeps the merge and
the settings with the operator. On Track 2, a ruleset requires the operator's
approval on the head, and a lead session may merge with gh pr merge after it.

It is installed at user scope beside scripts/claude_leak_hook.py, runs before
every Bash command and every MCP tool call, and applies to every agent session.
A session with no role, or no track, is denied everything below, so a marker
that goes missing never lets anything through. It exits 2 to deny, with the reason on
standard error, and 0 to allow. It never returns a permission decision of its
own, so an allowed command still goes through the session's normal permission
prompts.

  1. Merges: `gh pr merge`, and `gh api` or GraphQL calls that merge.
  2. Settings, rulesets and branch protection: the `gh` commands, `gh api`
     endpoints and GraphQL mutations in the tables below, and GitHub MCP tools
     with those names.
  3. A push to the remote's default branch, by any refspec, `--all`,
     `--mirror`, or a bare push from a branch that is or tracks the default.
     A clone whose local config sets agentpolicy.allowDefaultPush to true is
     exempt. A person sets that outside the session; this hook denies agents
     writing it.

Everything the hook denies is listed once, in the tables under "What is
denied", and every policy denial goes through decide(). That is the one place a
role is granted an action (GRANTS). One row grants anything: a lead whose
session declares Track 2 of the workflow's merge authority may run gh pr merge
without --admin. A missing or unknown role, or a missing or unknown track,
never grants anything. A call the hook cannot check is denied outside it, so no
grant ever lets an unchecked call through.

The command xargs, parallel, find -exec, script -c, watch or flock runs, and a
script a shell reads on standard input, is checked like any other, and a gh
alias or extension is denied. A check that runs past DEADLINE seconds is
denied, so no input can keep the hook running until the host gives up on it.

It parses commands with the leak hook's parser, imported from the same
directory, so both scripts must be installed. Without the leak hook, every call
is denied. Nothing this prints contains the command or a file's contents.

Written in Python 3.10+, standard library only. scripts/test_claude_policy_hook.py
proves each rule.
"""

import fnmatch
import json
import os
import re
import shlex
import signal
import subprocess
import sys
from collections import Counter
from urllib.parse import unquote

STOP = ("Agent sessions don't merge, push to a default branch or change repository settings; "
        "the operator does that in the GitHub web UI. Say what you need in the issue or "
        "pull request, and stop.")
# A Track 2 lead denied a merge route: it may merge, but only one way.
LEAD_STOP = ("A Track 2 lead merges only with gh pr merge, written out in full and without "
             "--admin, once the operator has approved the current head on GitHub. Merging any "
             "other way, pushing to a default branch and changing repository settings are the "
             "operator's, in the GitHub web UI; say what you need in the pull request, and stop.")

sys.dont_write_bytecode = True  # no __pycache__ beside the installed hooks
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
try:
    from claude_leak_hook import (EXPORTERS, SHELLS, STDIN_PATHS, Deny, option, parse,
                                  parse_command, shell_candidates)
except Exception as error:  # fail closed: the parser is required
    sys.stderr.write(f"policy hook: denied: claude_leak_hook.py could not be imported "
                     f"({type(error).__name__}); install both hooks. {STOP}\n")
    sys.exit(2)


# --- What is denied ------------------------------------------------------------------
#
# The categories a role can be granted, and the rows that map each command
# form to one of them with the words a denial uses.

MERGE = "merge"  # every merge route; granted to no role
PR_MERGE = "pr-merge"  # gh pr merge with no --admin, the one form a role can be granted
SETTINGS = "settings"
RULESETS = "rulesets"
PROTECTION = "branch-protection"
DEFAULT_PUSH = "default-push"
OPT_OUT = "policy-opt-out"
TRACK = "merge-track"  # setting CLAUDE_MERGE_TRACK, which only the operator does

# gh <group> <verb>. None as the verb set means every verb but those in READ_VERBS.
GH_COMMANDS = {
    ("pr", "merge"): (MERGE, "merging a pull request"),
    ("repo", "edit"): (SETTINGS, "editing repository settings"),
    ("repo", "delete"): (SETTINGS, "deleting a repository"),
    ("repo", "rename"): (SETTINGS, "renaming a repository"),
    ("repo", "archive"): (SETTINGS, "archiving a repository"),
    ("repo", "unarchive"): (SETTINGS, "unarchiving a repository"),
    ("secret", "set"): (SETTINGS, "setting a repository secret"),
    ("secret", "delete"): (SETTINGS, "deleting a repository secret"),
    ("secret", "remove"): (SETTINGS, "deleting a repository secret"),
    ("variable", "set"): (SETTINGS, "setting a repository variable"),
    ("variable", "delete"): (SETTINGS, "deleting a repository variable"),
    ("workflow", "enable"): (SETTINGS, "enabling a workflow"),
    ("workflow", "disable"): (SETTINGS, "disabling a workflow"),
}
GH_DEPLOY_KEY_WRITES = {"add", "delete"}  # gh repo deploy-key <verb>
# gh's own commands (gh 2.86), with their cobra aliases, gh's default alias co,
# and its help topics.
# Any other first word is a user alias or an extension, which runs a command the
# hook cannot see, so it is denied, as are defining an alias and running an
# extension by name.
GH_BUILTINS = {"auth", "browse", "codespace", "cs", "gist", "issue", "org", "pr", "project",
               "release", "repo", "cache", "run", "workflow", "agent-task", "alias", "api",
               "attestation", "completion", "config", "copilot", "extension", "extensions",
               "ext", "gpg-key", "label", "preview", "ruleset", "search", "secret", "ssh-key",
               "status", "variable", "help", "version", "accessibility", "a11y",
               "actions", "environment", "reference", "exit-codes", "formatting", "mintty",
               "licenses"}  # the last line: help topics, which print text
GH_ALIAS_WRITES = {"set", "import"}
GH_UNCHECKED = "a gh alias or extension, which runs a command the hook cannot check"
GH_RULESET_READS = {"list", "ls", "view", "check"}  # every gh ruleset verb today

# gh api endpoints, matched when the call writes. S is one path segment.
S = r"[^/]+"
API_PATHS = [
    (re.compile(rf"repos/{S}/{S}/pulls/{S}/merge"), MERGE, "merging a pull request through the API"),
    (re.compile(rf"repos/{S}/{S}/merges"), MERGE, "merging a branch through the API"),
    (re.compile(rf"repos/{S}/{S}/git/refs(/.*)?"), DEFAULT_PUSH, "moving a branch through the API"),
    (re.compile(rf"repos/{S}/{S}/merge-upstream"), DEFAULT_PUSH,
     "syncing a remote repository's branch through the API"),
    (re.compile(rf"repos/{S}/{S}/branches/.+/rename"), SETTINGS, "renaming a branch"),
    (re.compile(rf"repos/{S}/{S}/rulesets(/.*)?"), RULESETS, "a write to repository rulesets"),
    (re.compile(rf"orgs/{S}/rulesets(/.*)?"), RULESETS, "a write to organization rulesets"),
    (re.compile(rf"repos/{S}/{S}/branches/.+/protection(/.*)?"), PROTECTION,
     "a write to branch protection"),
    (re.compile(rf"repos/{S}/{S}"), SETTINGS, "a write to repository settings"),
    (re.compile(rf"repos/{S}/{S}/(transfer|topics|collaborators|teams|hooks|keys|environments"
                rf"|pages|actions/permissions|actions/secrets|actions/variables"
                rf"|vulnerability-alerts|automated-security-fixes"
                rf"|private-vulnerability-reporting)(/.*)?"), SETTINGS,
     "a write to repository settings"),
]

# GraphQL mutations, matched as words in a `gh api graphql` query.
GRAPHQL_MUTATIONS = {
    "mergePullRequest": MERGE,
    "enablePullRequestAutoMerge": MERGE,
    "mergeBranch": MERGE,
    "enqueuePullRequest": MERGE,
    "createCommitOnBranch": DEFAULT_PUSH,
    "updateRef": DEFAULT_PUSH,
    "updateRefs": DEFAULT_PUSH,
    "updateRepository": SETTINGS,
    "archiveRepository": SETTINGS,
    "unarchiveRepository": SETTINGS,
    "createBranchProtectionRule": PROTECTION,
    "updateBranchProtectionRule": PROTECTION,
    "deleteBranchProtectionRule": PROTECTION,
    "createRepositoryRuleset": RULESETS,
    "updateRepositoryRuleset": RULESETS,
    "deleteRepositoryRuleset": RULESETS,
}

# GitHub MCP tools, by the tool part of mcp__<server>__<tool>.
MCP_READ = re.compile(r"^(get|list|search)_")
MCP_TOOLS = [
    (re.compile(r"merge_pull_request$"), MERGE, "merging a pull request"),
    (re.compile(r"(^|_)(update|delete|archive|transfer)_repository$"), SETTINGS,
     "changing repository settings"),
    (re.compile(r"branch_protection"), PROTECTION, "changing branch protection"),
    (re.compile(r"ruleset"), RULESETS, "changing rulesets"),
]
MCP_BRANCH_WRITES = re.compile(r"^(push_files|create_or_update_file|delete_file)$")

OPT_OUT_KEY = "agentpolicy.allowdefaultpush"  # git compares keys case-insensitively
OPT_OUT_NOUN = "setting agentpolicy.allowDefaultPush"  # the policy canary's denial
DEFAULT_PUSH_NOUN = "pushing to the default branch"


# --- Deciding ------------------------------------------------------------------------

# Roles, each with the categories it is granted and the merge track each grant
# needs. Both come only from the environment the session's Claude Code process
# starts with: CLAUDE_AGENT_ROLE and CLAUDE_MERGE_TRACK. A role not listed here,
# or a grant whose track the session doesn't declare, grants nothing. The
# project's ruleset, not this table, is what makes a Track 2 merge safe
# (process/repository-standards.md, Guarding Repository Authority).
TRACK_1, TRACK_2 = "1", "2"
GRANTS = {
    "lead": {PR_MERGE: TRACK_2},
    "coordinator": {},
    "worker": {},
}
ROLE_VAR = "CLAUDE_AGENT_ROLE"
TRACK_VAR = "CLAUDE_MERGE_TRACK"


def role():
    """The session's role, read only from the hook's own environment, or None."""
    return os.environ.get(ROLE_VAR) or None


def track():
    """The session's merge track, read only from the hook's own environment.

    Only the exact value 2 is Track 2; a missing, empty or unrecognised value is Track 1.
    """
    return TRACK_2 if os.environ.get(TRACK_VAR) == TRACK_2 else TRACK_1


def granted(category):
    """Whether the session's role is granted the category on the session's track."""
    grants = GRANTS.get(role(), {})
    return category in grants and grants[category] == track()


class LeadMergeDeny(Deny):
    """A merge route denied to a session that may merge by gh pr merge."""


def decide(category, noun):
    """The one decision point: raises Deny unless the session's role is granted the category."""
    if granted(category):
        return
    if category == MERGE and granted(PR_MERGE):
        raise LeadMergeDeny(noun)
    raise Deny(noun)


# --- gh ------------------------------------------------------------------------------

GH_WITH_VALUE = {"-R", "--repo", "--hostname"}
GH_API_WITH_VALUE = {"-X", "--method", "-f", "-F", "--field", "--raw-field", "-H", "--header",
                     "--input", "-q", "--jq", "-t", "--template", "--hostname", "-p",
                     "--preview", "--cache"}


def skip_flags(words, with_value):
    """Drops leading options, and the values of those that take one."""
    while words and words[0].startswith("-") and words[0] != "-":
        words = words[2:] if words[0] in with_value else words[1:]
    return words


def admin_flag(word):
    """gh's --admin, which merges past the branch rules; pflag also takes --admin=<bool>."""
    return word == "--admin" or word.startswith("--admin=")


# Characters by which the shell can still turn a word into another: substitution,
# brace expansion, globs, extended globs and the tilde (~, ~-, ~+, ~1 read
# variables an earlier command can set). The parser splits an unquoted
# extended glob such as --@(admin) at its parenthesis, leaving a word that ends
# in the glob's @, +, ! (or ?, *), so a word ending in one counts too.
EXPANDS = re.compile(r"[$`{}*?\[\]()~]|[@+!]$")


def gh_pr_merge(cmd):
    """gh pr merge: a Track 2 lead may run it, never with --admin."""
    noun = GH_COMMANDS[("pr", "merge")][1]
    # Any word counts, even a value or one after --, so nothing that reads as
    # --admin is let through. A word the shell could still expand, by a
    # substitution, a brace or a glob, could become --admin, so it can't be
    # checked. The words have lost their quotes, so a quoted $ counts too.
    if any(admin_flag(w) for w in cmd.words[1:]):
        decide(MERGE, noun + " with --admin, which bypasses the branch rules"
               if granted(PR_MERGE) else noun)
    if RUNTIME_ARGS[0]:
        decide(MERGE, "a gh pr merge run by xargs, parallel or find, which add arguments "
               "when it runs, so it cannot be checked; run gh pr merge on its own"
               if granted(PR_MERGE) else noun)
    if any(EXPANDS.search(w) for w in cmd.words[1:]):
        decide(MERGE, "a gh pr merge with a word the shell could expand, so it cannot be "
               "checked; write the number and flags out, put a body that needs $, `, {, }, "
               "*, ?, [, ], (, ) or ~, or ends in !, + or @, in a file for -F named without ~, "
               "and reword a "
               "subject that needs one or leave it out" if granted(PR_MERGE) else noun)
    decide(PR_MERGE, noun)


def gh_command(cmd):
    """Checks one gh command. Raises Deny."""
    words = skip_flags(cmd.words[1:], GH_WITH_VALUE)
    if not words:
        return
    group, rest = words[0], skip_flags(words[1:], GH_WITH_VALUE)
    verb = rest[0] if rest else ""
    if group not in GH_BUILTINS:
        decide(MERGE, GH_UNCHECKED)
    if (group == "alias" and verb in GH_ALIAS_WRITES) or (group in ("extension", "extensions", "ext")
                                                           and verb == "exec"):
        decide(MERGE, GH_UNCHECKED)
    if (group, verb) == ("pr", "merge"):
        gh_pr_merge(cmd)
    elif (group, verb) in GH_COMMANDS:
        decide(*GH_COMMANDS[(group, verb)])
    elif group == "repo" and verb == "deploy-key":
        sub = skip_flags(rest[1:], GH_WITH_VALUE)
        if sub and sub[0] in GH_DEPLOY_KEY_WRITES:
            decide(SETTINGS, "changing a repository deploy key")
    elif group == "repo" and verb == "sync":
        if [w for w in skip_flags(rest[1:], {"-b", "--branch", "-s", "--source"})
                if not w.startswith("-")]:
            decide(DEFAULT_PUSH, "syncing a remote repository's branch")
    elif group == "ruleset" and verb and verb not in GH_RULESET_READS:
        decide(RULESETS, "a gh ruleset command that is not a read")
    elif group == "api":
        gh_api(cmd, words[1:])


def endpoint(words):
    """Returns the gh api endpoint: the first word that is not an option or its value."""
    i = 0
    while i < len(words):
        w = words[i]
        if w.startswith("-") and w != "-":
            i += 2 if w in GH_API_WITH_VALUE else 1
            continue
        return w
    return None


def normalize(path):
    """The endpoint as GitHub routes it: no host, query or fragment, percent escapes
    decoded, and no empty, . or .. segments, so repos//o/r/pulls/1/./%6Derge#x
    reads as repos/o/r/pulls/1/merge."""
    path = re.sub(r"^https?://[^/]+/(api/v3/)?", "", path)
    for _ in range(4):  # an escape that decodes to another escape is decoded again
        path = re.split(r"[?#]", path, maxsplit=1)[0]
        decoded = unquote(path)
        if decoded == path:
            break
        path = decoded
    path = re.split(r"[?#]", path, maxsplit=1)[0]
    segments = []
    for part in path.split("/"):
        if part == "..":
            if segments:
                segments.pop()
        elif part not in ("", "."):
            segments.append(part)
    return "/".join(segments)


def gh_api(cmd, words):
    path = endpoint(words)
    if path is None:
        return
    path = normalize(path)
    if path == "graphql":
        return graphql(cmd, words)
    methods = [m.upper() for m in option(words, {"-X", "--method"})]
    sends = list(option(words, {"-f", "-F", "--field", "--raw-field", "--input"}))
    method = methods[-1] if methods else ("POST" if sends else "GET")
    if method in ("GET", "HEAD"):
        return
    if CONTENTS.fullmatch(path):
        # A contents write commits to the branch its branch field names, or to the
        # default branch when there is none.
        fields = option(words, {"-f", "-F", "--field", "--raw-field"})
        branches = [f.split("=", 1)[1].removeprefix("refs/heads/") for f in fields
                    if f.startswith("branch=")]
        defaults = {"main", "master"} | default_branches(Clone(cmd.cwd, []), "origin")
        if not branches or any(b in defaults or "$" in b or "`" in b for b in branches):
            decide(DEFAULT_PUSH, "a commit to the default branch through the contents API")
    for pattern, category, noun in API_PATHS:
        if pattern.fullmatch(path):
            decide(category, noun)


CONTENTS = re.compile(rf"repos/{S}/{S}/contents/.+")
MUTATION_WORDS = re.compile(r"\b(" + "|".join(GRAPHQL_MUTATIONS) + r")\b", re.I)
MUTATION_BY_NAME = {name.casefold(): category for name, category in GRAPHQL_MUTATIONS.items()}
CANONICAL = {name.casefold(): name for name in GRAPHQL_MUTATIONS}


def graphql(cmd, words):
    """Denies a GraphQL call that names a mutation in GRAPHQL_MUTATIONS."""
    texts = list(words)
    typed = list(option(words, {"-F", "--field"}))
    files = list(option(words, {"--input"})) + [f.split("=@", 1)[1] for f in typed if "=@" in f]
    unread = "a GraphQL query file that cannot be read, so it cannot be checked"
    fields = option(words, {"-f", "-F", "--field", "--raw-field"})
    # The leak hook's parser reads an unquoted query=$(cat q) as the word
    # query=$(), but past its depth limit it still splits it into query=$.
    if any("$(" in f or "`" in f or f.endswith("$") for f in fields if f.startswith("query=")):
        raise Deny("a GraphQL query built when the command runs, so it cannot be checked")
    for name in files:
        if name == "-":
            # stdin: only a heredoc's text is in the command, which raw_text holds.
            if not any(op == "<<" for op, _ in cmd.redirects):
                raise Deny("a GraphQL query read from standard input, so it cannot be checked")
            continue
        if not os.path.isabs(name) and cmd.cwd is None:
            raise Deny(unread)
        try:
            with open(os.path.join(cmd.cwd or "", name), encoding="utf-8", errors="replace") as f:
                texts.append(f.read(1024 * 1024))
        except OSError:
            # A file this call writes from a heredoc has its text in the command.
            if os.path.normpath(os.path.join(cmd.cwd or "", name)) not in cmd.heredoc_files:
                raise Deny(unread)
    texts.append(cmd.raw_text)
    for match in MUTATION_WORDS.finditer("\n".join(texts)):
        name = CANONICAL[match.group(1).casefold()]
        decide(MUTATION_BY_NAME[name.casefold()], f"the GraphQL mutation {name}")


# --- git -----------------------------------------------------------------------------

GIT_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env",
                  "--super-prefix", "--exec-path"}
PUSH_WITH_VALUE = {"--repo", "-o", "--push-option", "--receive-pack", "--exec"}
PUSH_EVERYTHING = {"--all", "--branches", "--mirror"}
DRY_RUN = {"-n", "--dry-run"}
CONFIG_WRITES = {"set", "--add", "--replace-all"}
CONFIG_READS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l", "get",
                "list", "--unset", "--unset-all", "unset", "--remove-section"}
CONFIG_WITH_VALUE = {"--file", "-f", "--blob", "--type", "--default", "--comment"}


def opt_out_key(kv):
    return kv.split("=", 1)[0].casefold() == OPT_OUT_KEY


def git_command(cmd):
    """Checks one git command. Raises Deny."""
    words = cmd.words[1:]
    prefix = []  # global options, passed on to the git calls that read the clone
    i = 0
    while i < len(words) and words[i].startswith("-"):
        w = words[i]
        value = words[i + 1] if w in GIT_WITH_VALUE and i + 1 < len(words) else None
        if ((w in ("-c", "--config-env") and value and opt_out_key(value))
                or (w.startswith("--config-env=") and opt_out_key(w[len("--config-env="):]))
                or (w.startswith("-c") and not w.startswith("--") and len(w) > 2
                    and opt_out_key(w[2:]))):
            decide(OPT_OUT, OPT_OUT_NOUN)
        step = 2 if w in GIT_WITH_VALUE else 1
        prefix += words[i:i + step]
        i += step
    if i >= len(words):
        return
    sub, rest = words[i], words[i + 1:]
    if sub == "config":
        git_config(rest)
    elif sub == "push":
        git_push(cmd, prefix, rest)


def git_config(rest):
    if not any(r.casefold() == OPT_OUT_KEY for r in rest):
        return
    if any(r in CONFIG_WRITES for r in rest):
        decide(OPT_OUT, OPT_OUT_NOUN)
    if any(r in CONFIG_READS for r in rest):
        return
    positional = []
    j = 0
    while j < len(rest):
        if rest[j] in CONFIG_WITH_VALUE:
            j += 2
            continue
        if not rest[j].startswith("-"):
            positional.append(rest[j])
        j += 1
    keys = [k for k, p in enumerate(positional) if p.casefold() == OPT_OUT_KEY]
    if keys and keys[0] + 1 < len(positional):
        decide(OPT_OUT, OPT_OUT_NOUN)


class Clone:
    """Reads a clone's config with the same global options and directory as the push."""

    def __init__(self, cwd, prefix):
        self.cwd = cwd
        self.prefix = prefix

    def git(self, *args):
        if self.cwd is None or not os.path.isdir(self.cwd):
            return None
        try:
            proc = subprocess.run(["git", *self.prefix, *args], cwd=self.cwd,
                                  capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0:
            return None
        return proc.stdout.decode("utf-8", "replace").strip()

    def lines(self, *args):
        out = self.git(*args)
        return out.splitlines() if out else []


def default_branches(clone, remote):
    """The remote's default branch from refs/remotes/<remote>/HEAD, else main and master."""
    ref = clone.git("symbolic-ref", "-q", f"refs/remotes/{remote}/HEAD")
    prefix = f"refs/remotes/{remote}/"
    if ref and ref.startswith(prefix):
        return {ref[len(prefix):]}
    return {"main", "master"}


def destination(refspec, current):
    """Returns the branch a refspec writes, "" for a non-branch ref, or None when unknown."""
    spec = refspec[1:] if refspec.startswith("+") else refspec
    src, colon, dst = spec.partition(":")
    if not colon or not dst:
        dst = src
        if dst in ("HEAD", "@"):
            return current
    if dst.startswith("refs/heads/"):
        return dst[len("refs/heads/"):]
    if dst.startswith("refs/"):
        return ""
    return dst


# A substitution that names the current branch, as in git push -u origin "$(git branch --show-current)".
CURRENT_BRANCH = re.compile(r"\$\(\s*git\s+(branch\s+--show-current|rev-parse\s+--abbrev-ref\s+HEAD"
                            r"|symbolic-ref\s+--short\s+HEAD)\s*\)")


def git_push(cmd, prefix, rest):
    """Denies a push that reaches the remote's default branch, unless the clone opted out."""
    if any(w in DRY_RUN for w in rest):
        return
    # The substitution runs in the shell's directory, so it names HEAD only when
    # the push does not name another clone.
    if not any(p == "-C" or p.split("=", 1)[0] in ("--git-dir", "--work-tree") for p in prefix):
        rest = [CURRENT_BRANCH.sub("HEAD", w) for w in rest]
    if any("$" in w or "`" in w for w in rest):
        return deny_push(cmd, prefix, None, "a push whose destination is built when it runs, "
                                            "so it cannot be checked; to push the current "
                                            "branch, use git push -u origin HEAD")
    positional, everything = [], False
    i = 0
    while i < len(rest):
        w = rest[i]
        if w == "--":
            positional += rest[i + 1:]
            break
        if w.startswith("-"):
            everything |= w in PUSH_EVERYTHING
            i += 2 if w in PUSH_WITH_VALUE else 1
            continue
        positional.append(w)
        i += 1
    clone = Clone(cmd.cwd, prefix)
    current = clone.git("symbolic-ref", "-q", "--short", "HEAD")
    if positional:
        remote, refspecs = positional[0], positional[1:]
    else:
        remote, refspecs = None, []
    if remote is None:
        remote = ((current and clone.git("config", f"branch.{current}.pushRemote"))
                  or clone.git("config", "remote.pushDefault")
                  or (current and clone.git("config", f"branch.{current}.remote"))
                  or "origin")
    defaults = default_branches(clone, remote)
    if everything:
        return deny_push(cmd, prefix, defaults, DEFAULT_PUSH_NOUN)
    if not refspecs:
        refspecs = clone.lines("config", "--get-all", f"remote.{remote}.push")
    if not refspecs:
        # A bare push: the current branch goes to its upstream, or, under
        # push.default=matching, every branch the remote also has.
        if clone.git("rev-parse", "--git-dir") is None:
            return deny_push(cmd, prefix, defaults, "a push whose branch cannot be worked out, "
                                                    "so it cannot be checked")
        if clone.git("config", "push.default") == "matching":
            return deny_push(cmd, prefix, defaults, DEFAULT_PUSH_NOUN)
        merge = current and clone.git("config", f"branch.{current}.merge")
        upstream = destination(merge, current) if merge else None
        if current in defaults:
            return deny_push(cmd, prefix, defaults, DEFAULT_PUSH_NOUN)
        if upstream in defaults:
            return deny_push(cmd, prefix, defaults, DEFAULT_PUSH_NOUN + ", which this branch "
                             "tracks; push it to its own name with git push -u origin HEAD")
        return
    for spec in refspecs:
        dst = destination(spec, current)
        if dst is None:
            return deny_push(cmd, prefix, defaults, "a push whose branch cannot be worked out, "
                                                    "so it cannot be checked")
        if "*" in dst:
            if any(fnmatch.fnmatchcase(d, dst) for d in defaults):
                return deny_push(cmd, prefix, defaults, DEFAULT_PUSH_NOUN)
        elif dst in defaults or dst == "HEAD":
            return deny_push(cmd, prefix, defaults, DEFAULT_PUSH_NOUN)


def deny_push(cmd, prefix, defaults, noun):
    """Denies a default-branch push, unless the clone has the person-set opt-out."""
    clone = Clone(cmd.cwd, prefix)
    if clone.git("config", "--local", "--type=bool", "--get", "agentpolicy.allowDefaultPush") == "true":
        return
    decide(DEFAULT_PUSH, noun)


# --- The merge track ----------------------------------------------------------------
#
# A session that set CLAUDE_MERGE_TRACK for a child it starts could make that
# child a Track 2 lead, so only the operator sets it, outside any session. This
# is best effort: the ruleset that requires the operator's approval is the guard.

TRACK_NOUN = "setting CLAUDE_MERGE_TRACK, which only the operator sets"
# The name as an identifier, not read as $NAME, ${NAME}, ${#NAME} or ${!NAME}.
TRACK_ID = r"(?<![$A-Za-z0-9_{#!])CLAUDE_MERGE_TRACK(?![A-Za-z0-9_])"
TRACK_NAME = re.compile(TRACK_ID)
# The name followed by an assignment operator, or with ++ or -- against it: an
# assignment, a let or (( )) expression, an array subscript or ${v:NAME=2}. It
# is matched in a command's words joined, since the parser splits
# (( NAME = 2 )) into words, so prose that reads NAME= matches too. Inside
# ${NAME...} only = and := assign; ${NAME-=} and ${NAME/=/x} read.
TRACK_WRITE = re.compile(r"\$\{CLAUDE_MERGE_TRACK:?="
                         r"|(?<![$A-Za-z0-9_#!{])CLAUDE_MERGE_TRACK\s*(:|[-+*/%&|^]|<<|>>)?=(?!=)"
                         r"|" + TRACK_ID + r"(\+\+|--)|(?<![-+])(\+\+|--)CLAUDE_MERGE_TRACK\b")
# A settings env block, as passed inline to claude --settings or written by jq or
# printf, in any command but a search for the key: "NAME": in JSON, or NAME: as
# a jq or YAML key, but not ${NAME:-x}, which reads it. JSON \u escapes are
# decoded first.
TRACK_JSON_KEY = re.compile(r"\"CLAUDE_MERGE_TRACK\"\s*:"
                            r"|(?<![$A-Za-z0-9_#!])(?<!\$\{)CLAUDE_MERGE_TRACK\s*:(?![-=?+])")
JSON_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")
TRACK_SEARCHES = {"grep", "egrep", "fgrep", "rg", "ag", "ack"}
# Builtins whose words can name a variable they set: as a name, NAME=v, an
# arithmetic expression (let), a nameref's target, or getopts' and wait -p's NAME.
TRACK_NAMERS = EXPORTERS | {"let", "for", "select", "read", "mapfile", "readarray",
                            "getopts", "wait"}
# declare/typeset -p print it, and +x removes the export; export -n removes the
# export (declare -n is a nameref).
TRACK_READS = {"declare": {"-p", "+x"}, "typeset": {"-p", "+x"}, "export": {"-p", "-n"}}
# Words that set an environment variable named by the next word: tmux setenv and
# set-environment, screen -X setenv, launchctl setenv, systemctl
# import-environment, and csh's setenv.
TRACK_SETENV = {"setenv", "set-environment", "import-environment"}
# Shells whose scripts this does not parse: any mention of the name is denied.
OTHER_SHELLS = {"fish", "csh", "tcsh"}
# An innermost brace group, not ${...}: {a,b} or a sequence {x..y} or {x..y..n}.
# The comma form can match only one way, so a search takes linear time.
BRACE = re.compile(r"(?<!\$)\{([^{},]*(?:,[^{},]*)+|-?\w+\.\.-?\w+(\.\.-?\d+)?)\}")
MAX_FORMS = 256
MAX_WORD = 4096  # a longer word with a brace group is not expanded
MAX_EXPANSION = 1 << 20  # characters of forms one run makes before it stops expanding
NUMBER = re.compile(r"-?[0-9]{1,18}")
expanded = [0]  # characters of forms made so far, against MAX_EXPANSION


def alternatives(group):
    """What one brace group expands to, at most MAX_FORMS + 1 of them; a sequence
    as bash reads it, or itself."""
    if "," in group:
        return group.split(",", MAX_FORMS + 1)[:MAX_FORMS + 1]
    a, b = group.split("..")[:2]
    if NUMBER.fullmatch(a) and NUMBER.fullmatch(b):
        lo, hi = sorted((int(a), int(b)))
        return [str(n) for n in range(lo, min(hi, lo + MAX_FORMS) + 1)]
    if len(a) == 1 and len(b) == 1:
        lo, hi = sorted((ord(a), ord(b)))
        return [chr(c) for c in range(lo, min(hi, lo + MAX_FORMS) + 1)]
    return ["{" + group + "}"]


def forms(word):
    """The word, and what brace expansion makes of it, so that CLAUDE_MERGE_TRAC{K,}
    and CLAUDE_MERGE_{TRACK,X} read as the name. Three limits keep the time this
    takes linear in the command's length. A word with more than MAX_FORMS forms
    reads as setting the name if it holds =. A word longer than MAX_WORD, one
    with a group of more than MAX_FORMS alternatives, or one met after
    MAX_EXPANSION characters of forms, isn't fully expanded: it reads as naming
    it, and as setting it if it holds =."""
    if "{" not in word or not BRACE.search(word):
        return [word]
    unchecked = [word, TRACK_VAR] + ([TRACK_VAR + "="] if "=" in word else [])
    if len(word) > MAX_WORD or expanded[0] > MAX_EXPANSION:
        return unchecked
    out, todo = [word], [word]
    while todo:
        w = todo.pop()
        m = BRACE.search(w)
        if not m:
            continue
        if m.group(1).count(",") > MAX_FORMS:  # alternatives() keeps only the first ones
            return out + unchecked[1:]
        for alt in alternatives(m.group(1)):
            new = w[:m.start()] + alt + w[m.end():]
            if new == w:
                continue
            out.append(new)
            todo.append(new)
            expanded[0] += len(new)
        if expanded[0] > MAX_EXPANSION:
            return out + unchecked[1:]
        if len(out) > MAX_FORMS:  # as many as a name needs; =, though, can't be checked
            return out + ([TRACK_VAR + "="] if "=" in word else [])
    return out


def searches(cmd):
    if cmd.program in TRACK_SEARCHES:
        return True
    sub = skip_flags(cmd.words[1:], GIT_WITH_VALUE) if cmd.program == "git" else []
    return bool(sub) and sub[0] == "grep"


def unjson(text):
    return JSON_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), text)


def names_track(text):
    """Whether script text names the variable at all, after brace expansion: as a
    write, an identifier or a JSON key."""
    tokens = [f for t in re.split(r"[\s;&|()]+", text) for f in forms(t)]
    return (any(TRACK_NAME.search(f) or TRACK_WRITE.search(f) for f in tokens)
            or TRACK_WRITE.search(text) or TRACK_JSON_KEY.search(unjson(text)))


# A NAME=value word whose NAME the shell could still expand to the variable: one
# with a $ or a backtick, or a glob or brace that matches it, as in
# export CLAUDE_MERGE_TRAC?=2 or env ${X}=2. It may stand after an option, as in
# --env=NAME=v or -eNAME=v.
EXPANDS_TO_NAME = re.compile(r"[$`]")
ARRAY_ELEMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\[.*\]")
# Options that set an environment variable from their value: docker -e, tmux -e,
# systemd-run -E and --setenv, and the like.
ENV_OPTIONS = {"-e", "--env", "-E", "--setenv", "--set-env"}
# Programs whose -e or -E is a pattern or a script, not a variable.
PATTERN_PROGRAMS = TRACK_SEARCHES | {"sed", "gsed", "perl", "awk", "gawk", "mawk", "jq", "echo"}
GLOBS = re.compile(r"[*?\[{]")


# Where a word with a subscript, a[$i]=x, sets a shell array element: a bare
# assignment on its own, or these builtins. After env, sudo or export, or before a
# command, the subscript's $ counts as for any other name.
ARRAY_SETTERS = {"declare", "local", "typeset"}


def could_name_track(word, unknown=True, array=False):
    """Whether a word could reach a setter as CLAUDE_MERGE_TRACK=value once the shell
    expands it. With unknown false, a $ or backtick in the name does not count. With
    array true, a subscript is an array element's, whatever it holds."""
    candidates = [word]
    if word.startswith("-"):
        attached = [word.partition("=")[2], word[2:] if word[1:2] != "-" else ""]
        # An option's attached value, as tmux -eNAME=2: the name written out counts.
        if any(a.partition("=")[0] == TRACK_VAR and "=" in a for a in attached):
            return True
        candidates += attached
    for candidate in candidates:
        name, eq, _ = candidate.partition("=")
        if not eq or not name or re.search(r"[\s/]", name):
            continue
        # A glob first: in env's or export's word, TRAC[K] can match a file named for the track.
        if GLOBS.search(name) and any(fnmatch.fnmatchcase(TRACK_VAR, f) for f in forms(name)):
            return True
        subscript = ARRAY_ELEMENT.fullmatch(name)
        if subscript and subscript.group(1) == TRACK_VAR:  # CLAUDE_MERGE_TRACK[0]=2 sets it
            return True
        if subscript and array:  # arr[$i]=x sets an element of arr, whatever the subscript
            name = subscript.group(1)
        if unknown and EXPANDS_TO_NAME.search(name):
            return True
    return False


SETTERS = EXPORTERS | {"env", "sudo", "let"}


def track_command(cmd):
    """Denies a command that sets CLAUDE_MERGE_TRACK, in any form the parser reads.

    Best effort, and broad: text that reads NAME= is denied even as an argument."""
    words, args = cmd.words, cmd.words[1:]
    every = [f for w in cmd.assigns + words for f in forms(w)]
    text = " ".join(every)
    targets = [f for _, t in cmd.redirects for f in forms(t)]
    if (TRACK_WRITE.search(text)
            or any(TRACK_WRITE.search(t) for t in targets)
            or any(TRACK_NAME.search(f) for a in cmd.assigns for f in forms(a.split("=", 1)[1]))
            or (not searches(cmd) and TRACK_JSON_KEY.search(unjson(text)))):
        decide(TRACK, TRACK_NOUN)
    # A name the shell could still expand to it, where a setter reads NAME=value:
    # the program's place (env stops there), a setter's arguments, and option values.
    for k, w in enumerate(words):
        sets_env = cmd.program not in PATTERN_PROGRAMS
        after_option = sets_env and k > 0 and words[k - 1] in ENV_OPTIONS
        attached = sets_env and (w.startswith(("-e", "-E")) or w.split("=", 1)[0] in ENV_OPTIONS)
        unknown = k == 0 or cmd.program in SETTERS or after_option or attached
        # The parser keeps a[$i]=x as the program word, after env or sudo too, so only a
        # word that is the whole command is a bare assignment.
        array = (k == 0 and len(words) == 1) or (k > 0 and cmd.program in ARRAY_SETTERS
                                                 and not w.startswith("-"))
        if could_name_track(w, unknown, array):
            decide(TRACK, TRACK_NOUN)
    named = [f for w in args if w[:1] not in ("-", "+") for f in forms(w)]
    if cmd.program in TRACK_NAMERS and any(TRACK_NAME.search(f) for f in named):
        options = {w for w in args if w[:1] in ("-", "+")}
        reads = options and options <= TRACK_READS.get(cmd.program, set())
        if not reads or any("=" in f for f in named):  # export -n r=NAME points a nameref
            decide(TRACK, TRACK_NOUN)
    if cmd.program in OTHER_SHELLS and any(names_track(w) for w in args):
        decide(TRACK, TRACK_NOUN)
    for k, w in enumerate(words):
        if w in TRACK_SETENV and any(TRACK_NAME.search(f) for v in words[k + 1:] for f in forms(v)):
            decide(TRACK, TRACK_NOUN)
    if cmd.program == "printf":
        for i, w in enumerate(args):
            nxt = forms(args[i + 1]) if i + 1 < len(args) else []
            if (w == "-v" and TRACK_VAR in nxt) or TRACK_VAR in [f.removeprefix("-v") for f in forms(w)
                                                                 if f.startswith("-v")]:
                decide(TRACK, TRACK_NOUN)
        # A format that puts the name in a key or an assignment, as printf '{"%s":"2"}' NAME.
        if (any("%" in w and re.search(r"[{:=]", w) for w in args)
                and any(TRACK_NAME.search(f) for w in args for f in forms(w))):
            decide(TRACK, TRACK_NOUN)


# --- Commands inside commands ----------------------------------------------------
#
# A script a shell reads on standard input, a heredoc body no command reads, and
# the command xargs, parallel, find -exec or script -c runs are checked as
# commands too, to MAX_NESTING levels; past that, the call is denied.

MAX_NESTING = 3
STDIN_SHELLS = SHELLS | {"source", "."}
SHELL_OPTION_VALUES = "oO"  # bash -o pipefail, -O extglob: the next word is a value


def reads_stdin(cmd):
    """Whether this runs a script from standard input: a shell with no -c and no
    script operand, or with -s, or source or . of standard input."""
    words = cmd.words
    if cmd.program in ("source", "."):
        return len(words) < 2 or words[1] in STDIN_PATHS | {"-"}
    if cmd.program not in SHELLS or shell_candidates(words):
        return False
    k = 1
    while k < len(words):
        w = words[k]
        if w == "--":
            return k + 1 >= len(words)
        if w.startswith("--"):  # a long option, such as --norc
            k += 1
            continue
        if w[:1] not in ("-", "+"):
            return False  # a script file
        if w[0] == "-" and "s" in w[1:]:
            return True
        k += 1 + sum(w[1:].count(letter) for letter in SHELL_OPTION_VALUES)
    return True


def stdin_scripts(found, command):
    """The scripts a shell or source runs from standard input: a here-string, and,
    when the command holds a heredoc, the text after the first line with one. That
    covers a heredoc the shell reads itself, one piped into it through any
    stages, groups or wrappers, and one whose delimiter the parser can't read."""
    readers = [c for c in found.commands if reads_stdin(c)]
    texts = [t for c in readers for op, t in c.redirects if op == "<<<"]
    if readers:
        lines = command.split("\n")
        first = next((k for k, line in enumerate(lines) if "<<" in line.replace("<<<", "")), None)
        if first is not None:
            texts.append("\n".join(lines[first + 1:]))
    return texts


def unconsumed_heredocs(found):
    """The heredoc bodies a parsed command may not read as a heredoc: for any
    delimiter with more bodies than readers, every body with it, since which one
    is unread can't be told. The parser finds both alike, so this is a safety net
    for a body it would otherwise hide."""
    readers = Counter(t.lstrip("-") for c in found.commands for op, t in c.redirects
                      if op.endswith("<<") and not op.endswith("<<<"))
    bodies = Counter(delim.lstrip("-") for delim, _, _ in found.heredocs)
    short = {d for d, count in bodies.items() if count > readers[d]}
    return [body for delim, body, _ in found.heredocs if delim.lstrip("-") in short]


# A command substitution the shell runs while it expands a heredoc body: $( (and
# $(( ), ${ or ${| followed by a blank (bash 5.3), or a backtick, after an even number of backslashes (\\ is one literal \).
CONTINUATION = re.compile(r"(?<!\\)((?:\\\\)*)\\\n")
SUBSTITUTION = re.compile(r"(?<!\\)(?:\\\\)*(?:\$\(|\$\{[ \t\n|]|`)")
EXPANDED_BODY = ("a heredoc body that runs a command substitution, which the hook cannot "
                 "check; quote the delimiter (<<'EOF') so the body stays text, or run the "
                 "command on its own")


def expanded_substitution(found):
    """Whether a heredoc with an unquoted delimiter holds a substitution: the shell
    runs it when it expands the body, and the parser reads the body only as text."""
    # The shell drops an unescaped backslash-newline in such a body first, so $\<newline>( opens one too.
    return any(not quoted and SUBSTITUTION.search(CONTINUATION.sub(r"\1", body))
               for _, body, quoted in found.heredocs)


XARGS_WITH_VALUE = {"-a", "--arg-file", "-d", "--delimiter", "-E", "-I", "-L", "-n", "--max-args",
                    "-P", "--max-procs", "-s", "--max-chars", "--process-slot-var"}
PARALLEL_ENDS = {":::", "::::", ":::+", "::::+"}
FIND_EXEC = {"-exec", "-execdir", "-ok", "-okdir"}
CHECKED_PROGRAMS = {"gh", "git"}


# Above zero while a command xargs, parallel or find -exec {} runs is checked:
# those add arguments when they run, which the hook never sees.
RUNTIME_ARGS = [0]


def first_command(words, with_value):
    """Where the command after a runner's options starts: past its options, and
    the values of those that take one."""
    i = 0
    while i < len(words) and words[i].startswith("-") and words[i] != "-":
        if words[i] == "--":
            return i + 1
        # A bundle such as -0a or -ka takes a value when its last letter does.
        bundled = re.fullmatch(r"-[^-]+", words[i]) and "-" + words[i][-1] in with_value
        i += 2 if words[i] in with_value or bundled else 1
    return i


def inner(cmd):
    """Yields (script, runtime) for each script this command runs, as text: the
    command after xargs, parallel or find -exec, joined back into a command line,
    or a script's text. Each is then checked as a whole command, sh -c and all.
    runtime is true where the runner adds arguments when it runs."""
    words, prog = cmd.words, cmd.program
    if " " in prog or "\t" in prog or "\n" in prog:  # watch 'gh ...', flock f -c 'gh ...'
        yield " ".join(words), False
    if prog in ("xargs", "parallel"):
        rest = words[1:]
        end = next((k for k, w in enumerate(rest) if prog == "parallel" and w in PARALLEL_ENDS),
                   len(rest))
        start = first_command(rest[:end], XARGS_WITH_VALUE)
        if start < end:
            yield shlex.join(rest[start:end]), True
        # An option this does not know may take a value: check the first gh or git too.
        known = next((k for k in range(end) if os.path.basename(rest[k]) in CHECKED_PROGRAMS), None)
        if known is not None and known != start:
            yield shlex.join(rest[known:end]), True
        if prog == "parallel" and start >= end:  # parallel ::: 'cmd' runs each argument
            # With a second source, or one read from a file (::::), parallel joins
            # values the command does not show into each command line.
            joined = (sum(w in PARALLEL_ENDS for w in rest[end:]) > 1 or rest[end:end + 1] != [":::"]
                      or any(w == "--arg-file" or w.startswith("--arg-file=")
                             or re.match(r"-[^-]*a", w) for w in rest[:end]))  # -a, or bundled as -ka
            for w in rest[end + 1:]:
                if w not in PARALLEL_ENDS:
                    yield w, joined
    elif prog == "find":
        k = 0
        while k < len(words):
            if words[k] in FIND_EXEC:
                end = k + 1
                while end < len(words) and words[end] not in (";", "+") and words[end] not in FIND_EXEC:
                    end += 1
                if end > k + 1:
                    yield shlex.join(words[k + 1:end]), any("{}" in w for w in words[k + 1:end]) \
                        or (end < len(words) and words[end] == "+")
                k = end
            else:
                k += 1
    elif prog == "script":  # each distinct -c command, once
        scripts = list(option(words[1:], {"-c", "--command"}))
        scripts += [words[k + 1] for k, w in enumerate(words[:-1])
                    if k > 0 and w != "-c" and re.fullmatch(r"-[a-zA-Z]*c", w)]
        yield from ((script, False) for script in dict.fromkeys(scripts))


def check_one(cmd, depth):
    """Checks one simple command, and the commands it runs. Raises Deny."""
    track_command(cmd)
    if cmd.program == "gh":
        gh_command(cmd)
    elif cmd.program == "git":
        git_command(cmd)
    elif cmd.program == "alias":
        if any(re.search(r"\b(gh|git)\b", w.partition("=")[2]) for w in cmd.words[1:]):
            decide(MERGE, "an alias for gh or git, which runs a command the hook cannot check")
    for script, runtime in inner(cmd):
        if depth >= MAX_NESTING:
            raise Deny("commands nested too deep to check")
        RUNTIME_ARGS[0] += runtime
        try:
            check_command(script, cmd.cwd, depth + 1)
        finally:
            RUNTIME_ARGS[0] -= runtime


# --- MCP tools -----------------------------------------------------------------------


def mcp_tool(name, tool_input):
    tool = name.split("__", 2)[-1]
    if MCP_BRANCH_WRITES.match(tool):
        branch = tool_input.get("branch") if isinstance(tool_input, dict) else None
        if not isinstance(branch, str) or branch in ("main", "master"):
            decide(DEFAULT_PUSH, "writing to the default branch through an MCP tool")
        return
    if MCP_READ.match(tool):
        return
    for pattern, category, noun in MCP_TOOLS:
        if pattern.search(tool):
            decide(category, noun)


# --- A command shlex cannot split ------------------------------------------------------

FALLBACK = [
    (re.compile(r"\bgh\b[^\n;&|]*\bpr\b[^\n;&|]*\bmerge\b"), MERGE, "merging a pull request"),
    (re.compile(r"\bgh\b[^\n;&|]*\b(repo\s+(edit|delete|rename|archive|unarchive|deploy-key)"
                r"|secret\s+(set|delete|remove)|variable\s+(set|delete)"
                r"|workflow\s+(enable|disable)|ruleset)\b"), SETTINGS,
     "a gh command that may change repository settings"),
    (re.compile(r"\bgh\b[^\n;&|]*\bapi\b"), SETTINGS,
     "a gh api call that cannot be split into words"),
    (re.compile(r"agentpolicy\.allowdefaultpush", re.I), OPT_OUT, OPT_OUT_NOUN),
    (re.compile(TRACK_WRITE.pattern + r"|" + TRACK_JSON_KEY.pattern + r"|\b("
                + "|".join(sorted(TRACK_NAMERS)) + r"|printf)\b[^\n;&|]*" + TRACK_ID),
     TRACK, TRACK_NOUN),
    (re.compile(r"\bgit\b[^\n;&|]*\bpush\b"), DEFAULT_PUSH,
     "a push that cannot be split into words, so its destination cannot be checked"),
]


def check_command(command, cwd, depth=0):
    """Raises Deny for a Bash command that does something in the tables."""
    try:
        found = parse_command(command, cwd)
    except ValueError:
        for pattern, category, noun in FALLBACK:
            if pattern.search(command):
                decide(category, noun + "; rewrite it with balanced quotes")
        return
    commands = found.commands
    heredoc_files = set()
    for cmd in commands:
        if cmd.cwd is not None and any(op == "<<" for op, _ in cmd.redirects):
            targets = [t for op, t in cmd.redirects if op in (">", ">>", ">|")]
            if cmd.program == "tee":
                targets += [w for w in cmd.words[1:] if not w.startswith("-")]
            heredoc_files.update(os.path.normpath(os.path.join(cmd.cwd, t)) for t in targets)
    if expanded_substitution(found):
        raise Deny(EXPANDED_BODY)
    scripts = stdin_scripts(found, command)
    if any(names_track(t) for t in scripts):
        decide(TRACK, TRACK_NOUN)
    for cmd in commands:
        cmd.raw_text = command
        cmd.heredoc_files = heredoc_files
        check_one(cmd, depth)
    for script in scripts + unconsumed_heredocs(found):
        if depth >= MAX_NESTING:
            raise Deny("commands nested too deep to check")
        check_command(script, cwd, depth + 1)


# The permission modes Claude Code names in a hook's input. The policy canary's denial reports
# the session's mode from the host's own field, so a session can confirm its mode without a
# notice in its context (process/agent-team-workflow.md, § 4, the mode check). Any other value,
# or none, reads as unknown, so nothing from the input is echoed.
PERMISSION_MODES = {"default", "acceptEdits", "plan", "auto", "dontAsk", "bypassPermissions"}


def permission_mode(data):
    """The session's permission mode as the host gave it to this hook, or "unknown"."""
    mode = data.get("permission_mode") if isinstance(data, dict) else None
    return mode if isinstance(mode, str) and mode in PERMISSION_MODES else "unknown"


DEADLINE = 20  # seconds: well under the host's hook timeout, so a slow input is denied


def start_deadline():
    """Denies the call if the check runs past DEADLINE seconds of wall-clock or CPU
    time, so no input can keep the hook running until the host gives up on it."""
    def expire(signum, frame):
        sys.stderr.write(f"policy hook: denied: the check ran past its {DEADLINE}-second "
                         f"deadline, so the call cannot be checked. {STOP}\n")
        sys.stderr.flush()
        os._exit(2)
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(DEADLINE)
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
        if hard == resource.RLIM_INFINITY or hard > DEADLINE:
            signal.signal(signal.SIGXCPU, expire)
            resource.setrlimit(resource.RLIMIT_CPU, (DEADLINE, hard))
    except (ImportError, ValueError, OSError):
        pass  # the wall-clock deadline still holds


def main():
    if sys.argv[1:] == ["--whoami"]:
        r = role()
        known = "" if r is None or r in GRANTS else ", an unknown role"
        held = sorted(c for c in GRANTS.get(r, {}) if granted(c))
        print(f"policy hook: role {r or 'none'} ({ROLE_VAR} "
              f"{'is set' if r else 'is not set'}{known}); track {track()} ({TRACK_VAR} "
              f"{'is set' if os.environ.get(TRACK_VAR) else 'is not set'}); "
              f"granted: {', '.join(held) or 'nothing'}.")
        return 0
    data = None
    try:
        start_deadline()
        try:
            data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
        except ValueError:
            raise Deny("the hook input is not valid JSON, so the call cannot be checked")
        if not isinstance(data, dict):
            raise Deny("the hook input is not a JSON object, so the call cannot be checked")
        tool = data.get("tool_name")
        tool_input = data.get("tool_input")
        if isinstance(tool, str) and tool.startswith("mcp__"):
            mcp_tool(tool, tool_input)
            return 0
        if tool != "Bash":
            return 0
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str):
            raise Deny("the hook input has no command string, so the command cannot be checked")
        cwd = data.get("cwd") if isinstance(data.get("cwd"), str) else os.getcwd()
        check_command(command, cwd)
        return 0
    except Deny as reason:
        hint = ""
        if DEFAULT_PUSH_NOUN in str(reason):
            hint = (" A clone that commits straight to its default branch can be exempted by a "
                    "person, outside the session: git config --local agentpolicy.allowDefaultPush true.")
        if OPT_OUT_NOUN in str(reason):
            hint += f" (permission mode: {permission_mode(data)})"
        stop = LEAD_STOP if isinstance(reason, LeadMergeDeny) else STOP
        sys.stderr.write(f"policy hook: denied: {reason}. {stop}{hint}\n")
        return 2
    except Exception as error:  # fail closed, naming nothing from the input
        sys.stderr.write(f"policy hook: denied: the hook failed ({type(error).__name__}) "
                         f"and cannot check this call. {STOP}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
