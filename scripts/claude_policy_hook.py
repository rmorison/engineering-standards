#!/usr/bin/env python3
"""A Claude Code PreToolUse hook: agent sessions don't merge or change repository settings.

process/repository-standards.md owns the rules this enforces (Guarding Repository
Authority). It assumes a human in the loop, the operator, who signs off on work,
merges in the GitHub web UI and owns repository settings. Every agent session
posts as the operator's account, so GitHub cannot tell a session from the
operator; this hook is what keeps the merge and the settings with the operator.

It is installed at user scope beside scripts/claude_leak_hook.py, runs before
every Bash command and every MCP tool call, and applies to every agent session:
there is no role marker to go missing. It exits 2 to deny, with the reason on
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
role could later be granted an action (GRANTS); today nothing is granted, and a
missing or unknown role never grants anything. A call the hook cannot check is
denied outside it, so no grant ever lets an unchecked call through.

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
import subprocess
import sys

STOP = ("Agent sessions don't merge, push to a default branch or change repository settings; "
        "the operator does that in the GitHub web UI. Say what you need in the issue or "
        "pull request, and stop.")

sys.dont_write_bytecode = True  # no __pycache__ beside the installed hooks
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
try:
    from claude_leak_hook import Deny, option, parse
except Exception as error:  # fail closed: the parser is required
    sys.stderr.write(f"policy hook: denied: claude_leak_hook.py could not be imported "
                     f"({type(error).__name__}); install both hooks. {STOP}\n")
    sys.exit(2)


# --- What is denied ------------------------------------------------------------------
#
# The categories a role could one day be granted, and the rows that map each
# command form to one of them with the words a denial uses.

MERGE = "merge"
SETTINGS = "settings"
RULESETS = "rulesets"
PROTECTION = "branch-protection"
DEFAULT_PUSH = "default-push"
OPT_OUT = "policy-opt-out"

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
DEFAULT_PUSH_NOUN = "pushing to the default branch"


# --- Deciding ------------------------------------------------------------------------

# Roles granted a category. Empty: no role is granted anything. A later grant is
# one row, such as "principal": {MERGE}, plus CLAUDE_AGENT_ROLE=principal in the
# environment the session's Claude Code process starts with.
GRANTS = {}
ROLE_VAR = "CLAUDE_AGENT_ROLE"


def role():
    """The session's role, read only from the hook's own environment, or None."""
    return os.environ.get(ROLE_VAR) or None


def decide(category, noun):
    """The one decision point: raises Deny unless the session's role is granted the category."""
    if category in GRANTS.get(role(), ()):
        return
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


def gh_command(cmd):
    """Checks one gh command. Raises Deny."""
    words = skip_flags(cmd.words[1:], GH_WITH_VALUE)
    if not words:
        return
    group, rest = words[0], skip_flags(words[1:], GH_WITH_VALUE)
    verb = rest[0] if rest else ""
    if (group, verb) in GH_COMMANDS:
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
    path = re.sub(r"^https?://[^/]+/(api/v3/)?", "", path)
    return path.split("?", 1)[0].strip("/")


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
        branches = [f.split("=", 1)[1] for f in fields if f.startswith("branch=")]
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
    if any("$(" in f or "`" in f for f in fields if f.startswith("query=")):
        raise Deny("a GraphQL query built when the command runs, so it cannot be checked")
    for name in files:
        if name == "-":
            # stdin: only a heredoc's text is in the command, which raw_text holds.
            if "<<" not in cmd.raw_text:
                raise Deny("a GraphQL query read from standard input, so it cannot be checked")
            continue
        if not os.path.isabs(name) and cmd.cwd is None:
            raise Deny(unread)
        try:
            with open(os.path.join(cmd.cwd or "", name), encoding="utf-8", errors="replace") as f:
                texts.append(f.read(1024 * 1024))
        except OSError:
            # A file the same command writes from a heredoc has its text in the command.
            if "<<" not in cmd.raw_text:
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
            decide(OPT_OUT, "setting agentpolicy.allowDefaultPush")
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
        decide(OPT_OUT, "setting agentpolicy.allowDefaultPush")
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
        decide(OPT_OUT, "setting agentpolicy.allowDefaultPush")


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
    (re.compile(r"agentpolicy\.allowdefaultpush", re.I), OPT_OUT,
     "setting agentpolicy.allowDefaultPush"),
    (re.compile(r"\bgit\b[^\n;&|]*\bpush\b"), DEFAULT_PUSH,
     "a push that cannot be split into words, so its destination cannot be checked"),
]


def check_command(command, cwd):
    """Raises Deny for a Bash command that does something in the tables."""
    try:
        commands, _ = parse(command, cwd)
    except ValueError:
        for pattern, category, noun in FALLBACK:
            if pattern.search(command):
                decide(category, noun + "; rewrite it with balanced quotes")
        return
    for cmd in commands:
        cmd.raw_text = command
        if cmd.program == "gh":
            gh_command(cmd)
        elif cmd.program == "git":
            git_command(cmd)


def main():
    if sys.argv[1:] == ["--whoami"]:
        r = role()
        granted = sorted(GRANTS.get(r, ()))
        print(f"policy hook: role {r or 'none'} ({ROLE_VAR} "
              f"{'is set' if r else 'is not set'}); granted: {', '.join(granted) or 'nothing'}.")
        return 0
    try:
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
        sys.stderr.write(f"policy hook: denied: {reason}. {STOP}{hint}\n")
        return 2
    except Exception as error:  # fail closed, naming nothing from the input
        sys.stderr.write(f"policy hook: denied: the hook failed ({type(error).__name__}) "
                         f"and cannot check this call. {STOP}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
