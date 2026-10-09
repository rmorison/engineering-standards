#!/usr/bin/env python3
"""Proves scripts/claude_policy_hook.py denies what it must and allows the rest.

CI runs this on every pull request (.github/workflows/agent-hooks.yml). Each fixture
feeds the hook one Claude Code PreToolUse input on standard input, as Claude
Code does, and checks the exit code (2 denies, 0 allows) and a fragment of the
message. An allowed call must print nothing.

Every fixture runs in a temporary directory, with HOME and GIT_CONFIG_GLOBAL
pointed at temporary files and CLAUDE_AGENT_ROLE unset unless a fixture sets
it. The clones are local repositories with a made-up origin that is never
contacted: nothing here pushes, merges, or changes a setting anywhere. Nothing
here installs a hook or reads a value list.

Labels such as R5, AE4 and KTD3 in section comments refer to
docs/plans/2026-10-05-2058-feat-agent-policy-hook-plan.md.

Usage:  python3 scripts/test_claude_policy_hook.py [hook]
The optional argument runs the fixtures against another script in place of the
hook, which is how each fixture is shown to fail before it is trusted: an
allow-all stub fails every deny fixture, and a deny-all stub every allow one.
Exits non-zero if any fixture fails. Needs Python 3.10 or later and git.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REAL_HOOK = ROOT / "scripts" / "claude_policy_hook.py"
LEAK_HOOK = ROOT / "scripts" / "claude_leak_hook.py"
HOOK = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REAL_HOOK
STANDARD = ROOT / "process" / "repository-standards.md"
HOOK_TIMEOUT = 20  # seconds; one call takes well under one

STOP = "the operator does that in the GitHub web UI"
RESIDUAL_DOC = (
    "the residual is now denied: update the residual list in "
    "process/repository-standards.md (Guarding Repository Authority) and move this fixture"
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


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=SANDBOX_ENV)


SANDBOX_ENV = {}


class Sandbox:
    """A temporary HOME and global git config, and the clones the push fixtures use."""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="policy-hook-test-"))
        self.home = self.root / "home"
        self.work = self.root / "work"
        for d in (self.home, self.work):
            d.mkdir(parents=True)
        self.gitconfig = self.root / "gitconfig"
        self.gitconfig.write_text("[user]\n\tname = Fixture\n\temail = fixture@example.invalid\n"
                                  "[init]\n\tdefaultBranch = trunk\n")
        self.env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "GIT_CONFIG_GLOBAL": str(self.gitconfig),
            "GIT_CONFIG_NOSYSTEM": "1",
            "LANG": "C.UTF-8",
        }
        SANDBOX_ENV.clear()
        SANDBOX_ENV.update(self.env)
        (self.work / "body.md").write_text("A clean body.\n")
        (self.work / "merge.graphql").write_text(
            "mutation($id: ID!) {\n  mergePullRequest(input: {pullRequestId: $id}) {\n"
            "    clientMutationId\n  }\n}\n")
        (self.work / "read.graphql").write_text("query { viewer { login } }\n")
        (self.work / "resolve.graphql").write_text(
            "mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { clientMutationId } }\n")

        # R5: clones whose remote's default branch is trunk, as refs/remotes/origin/HEAD says.
        self.trunk = self.clone("on-trunk", "trunk")
        self.feat = self.clone("on-feature", "76-x")
        self.track = self.clone("tracks-trunk", "topic", upstream="trunk")
        self.matching = self.clone("matching", "76-x", config={"push.default": "matching"})
        self.optout = self.clone("opted-out", "trunk",
                                 config={"agentpolicy.allowDefaultPush": "true"})
        self.nohead = self.clone("no-origin-head", "main", origin_head=False)

    def clone(self, name, branch, upstream=None, config=None, origin_head=True):
        path = self.work / name
        path.mkdir()
        git(path, "init", "-q", "-b", "trunk")
        git(path, "commit", "-q", "--allow-empty", "-m", "fixture")
        git(path, "remote", "add", "origin", "https://example.invalid/fixture.git")
        git(path, "update-ref", "refs/remotes/origin/trunk", "HEAD")
        if origin_head:
            git(path, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
        if branch != "trunk":
            git(path, "checkout", "-q", "-b", branch)
        if upstream:
            git(path, "config", f"branch.{branch}.remote", "origin")
            git(path, "config", f"branch.{branch}.merge", f"refs/heads/{upstream}")
        for key, value in (config or {}).items():
            git(path, "config", "--local", key, value)
        return path

    def run(self, stdin, env=None, hook=None, args=()):
        try:
            proc = subprocess.run([sys.executable, str(hook or HOOK), *args], input=stdin.encode(),
                                  capture_output=True, env=dict(self.env, **(env or {})),
                                  cwd=str(self.work), timeout=HOOK_TIMEOUT)
        except subprocess.TimeoutExpired:
            return ("timeout", "", "")
        return (proc.returncode, proc.stdout.decode("utf-8", "replace"),
                proc.stderr.decode("utf-8", "replace"))

    def bash(self, command, cwd=None, env=None, hook=None):
        return self.run(json.dumps({
            "session_id": "test",
            "cwd": str(cwd or self.work),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command, "description": "fixture"},
        }), env=env, hook=hook)

    def mcp(self, tool, tool_input):
        return self.run(json.dumps({
            "session_id": "test",
            "cwd": str(self.work),
            "hook_event_name": "PreToolUse",
            "tool_name": tool,
            "tool_input": tool_input,
        }))

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def check(name, result, want, frag=None, on_fail=None):
    """want is 'deny' or 'allow' (exit 0 and no output at all)."""
    rc, out, err = result
    if want == "deny":
        if rc != 2:
            return bad(name, on_fail or f"exit {rc}, expected 2 (deny)", result)
        if STOP not in err:
            return bad(name, f"the denial does not say {STOP!r}", result)
        if frag and frag not in err:
            return bad(name, f"the denial does not say {frag!r}", result)
    else:
        if rc != 0:
            return bad(name, on_fail or f"exit {rc}, expected 0 (allow)", result)
        if out.strip() or err.strip():
            return bad(name, "an allowed call printed output", result)
    ok()


def main():
    sb = Sandbox()
    try:
        fixtures(sb)
    finally:
        sb.cleanup()
    print(f"{passed} passed, {failed} failed")
    return 1 if failed else 0


MERGE = "merging a pull request"
SETTINGS = "repository settings"
PUSH = "pushing to the default branch"
OPT_OUT = "setting agentpolicy.allowDefaultPush"


def fixtures(sb):
    # --- R1: gh pr merge, in every place the parser finds a command (AE1) -----------
    for command in [
        "gh pr merge 12 --squash",
        "gh pr merge --auto 12",
        "gh pr merge 12 --admin --merge",
        "cd /tmp && gh -R o/r pr merge 12",
        "gh --repo o/r pr merge 12",
        "gh pr -R o/r merge 12",
        "url=$(gh pr merge 12)",
        "sh -c 'gh pr merge 12'",
        "if true; then gh pr merge 12; fi",
        "env GH_PROMPT_DISABLED=1 gh pr merge 12",
        "gh pr view 12\ngh pr merge 12",
    ]:
        check(f"R1 deny: {command!r}", sb.bash(command), "deny", MERGE)

    # --- R4: gh commands that change settings ----------------------------------------
    for command, frag in [
        ("gh repo edit --enable-auto-merge", SETTINGS),
        ("gh repo edit o/r --visibility public --accept-visibility-change-consequences", SETTINGS),
        ("gh repo delete o/r --yes", "deleting a repository"),
        ("gh repo rename new-name", "renaming a repository"),
        ("gh repo archive o/r -y", "archiving a repository"),
        ("gh repo unarchive o/r -y", "unarchiving a repository"),
        ("gh repo deploy-key add key.pub", "deploy key"),
        ("gh repo deploy-key delete 1", "deploy key"),
        ("gh secret set TOKEN --body x", "secret"),
        ("gh secret delete TOKEN", "secret"),
        ("gh secret remove TOKEN", "secret"),
        ("gh variable set V --body x", "variable"),
        ("gh variable delete V", "variable"),
        ("gh workflow disable leaks.yml", "disabling a workflow"),
        ("gh workflow enable leaks.yml", "enabling a workflow"),
        ("gh ruleset create", "gh ruleset"),
        ("gh repo sync o/fork", "syncing"),
    ]:
        check(f"R4 deny: {command!r}", sb.bash(command), "deny", frag)

    # --- R2: gh api writes to the denied endpoints (AE2) -----------------------------
    for command, frag in [
        ("gh api -X PUT repos/o/r/pulls/12/merge", MERGE),
        ("gh api --method=PUT repos/o/r/pulls/12/merge -f merge_method=squash", MERGE),
        ("gh api repos/o/r/merges -f base=trunk -f head=76-x", "merging a branch"),
        ("gh api -X PATCH repos/o/r -F allow_auto_merge=true", SETTINGS),
        ("gh api -X PATCH 'repos/{owner}/{repo}' -f description=x", SETTINGS),
        ("gh api -X PATCH /repos/o/r/ -f description=x", SETTINGS),
        ("gh api -X PATCH 'repos/o/r?x=1' -f description=x", SETTINGS),
        ("gh api -X DELETE repos/o/r", SETTINGS),
        ("gh api -X POST https://api.github.com/repos/o/r/rulesets --input r.json", "rulesets"),
        ("gh api -X PUT repos/o/r/rulesets/7 --input r.json", "rulesets"),
        ("gh api -X DELETE orgs/o/rulesets/7", "rulesets"),
        ("gh api repos/o/r/rulesets < <(echo y) --input r.json", "rulesets"),  # #95
        ("gh api -X PUT repos/o/r/branches/trunk/protection --input p.json", "branch protection"),
        ("gh api -X DELETE repos/o/r/branches/trunk/protection/required_status_checks",
         "branch protection"),
        ("gh api -X PUT repos/o/r/collaborators/someone", SETTINGS),
        ("gh api -X PUT repos/o/r/actions/permissions -F enabled=false", SETTINGS),
        ("gh api -X PUT repos/o/r/topics -f 'names[]=x'", SETTINGS),
        ("gh api -X POST repos/o/r/hooks --input h.json", SETTINGS),
        ("gh api -X PATCH repos/o/r/git/refs/heads/trunk -f sha=abc -F force=true",
         "moving a branch"),
        ("gh api -X POST repos/o/r/merge-upstream -f branch=trunk", "syncing"),
        ("gh api -X POST repos/o/r/branches/trunk/rename -f new_name=x", "renaming a branch"),
        ("gh api -X PUT repos/o/r/contents/README.md -f message=m -f content=Y29udGVudA==",
         "contents API"),
        ("gh api -X PUT repos/o/r/contents/docs/a.md -f message=m -f content=eA== -f branch=main",
         "contents API"),
        ("gh api -X DELETE repos/o/r/contents/a.md -f message=m -f sha=abc -f branch=master",
         "contents API"),
        ('gh api -X PUT repos/o/r/contents/a.md -f message=m -f content=eA== -f branch="$B"',
         "contents API"),
        ("gh api -X PUT repos/o/r/contents/a.md -f message=m -f content=eA== -f branch=refs/heads/main",
         "contents API"),
    ]:
        check(f"R2 deny: {command!r}", sb.bash(command), "deny", frag)
    check("R2 deny: a contents write to the clone's own default branch",
          sb.bash("gh api -X PUT repos/o/r/contents/a.md -f message=m -f content=eA== -f branch=trunk",
                  cwd=sb.trunk), "deny", "contents API")

    # --- R3: GraphQL mutations, inline, from a file, and from a heredoc (AE3) --------
    for command, frag in [
        ("gh api graphql -f query='mutation { mergePullRequest(input: {}) { clientMutationId } }'",
         "mergePullRequest"),
        ("gh api graphql -F query=@merge.graphql -f id=PR_1", "mergePullRequest"),
        ("cat > q.graphql <<'EOF'\nmutation { enablePullRequestAutoMerge(input: {}) { clientMutationId } }\n"
         "EOF\ngh api graphql -F query=@q.graphql", "enablePullRequestAutoMerge"),
        ("gh api graphql -f query='mutation { MERGEBRANCH(input: {}) { clientMutationId } }'",
         "the GraphQL mutation mergeBranch"),
        ("gh api graphql -f query='mutation { createCommitOnBranch(input: {}) { clientMutationId } }'",
         "createCommitOnBranch"),
        ("gh api graphql -f query='mutation { enqueuePullRequest(input: {}) { clientMutationId } }'",
         "enqueuePullRequest"),
        ("cat merge.graphql | gh api graphql -F query=@-", "standard input"),
        ("gh api graphql --input - < merge.graphql", "standard input"),
        ('gh api graphql -f query="$(cat read.graphql)"', "built when the command runs"),
        ("gh api graphql -f query=$(cat read.graphql)", "built when the command runs"),
        ('gh api graphql -F query=@- <<< "$(cat merge.graphql)"', "standard input"),
        ("cat > n.md <<'EOF'\nx\nEOF\ncat merge.graphql | gh api graphql -F query=@-",
         "standard input"),
        ("cat > n.md <<'EOF'\nx\nEOF\ngh api graphql -F query=@missing.graphql", "cannot be read"),
        ("gh api graphql -f query='mutation { updateRepository(input: {}) { clientMutationId } }'",
         "updateRepository"),
        ("gh api graphql -f query='mutation { createBranchProtectionRule(input: {}) { clientMutationId } }'",
         "createBranchProtectionRule"),
        ("gh api graphql -f query='mutation { deleteRepositoryRuleset(input: {}) { clientMutationId } }'",
         "deleteRepositoryRuleset"),
        ("gh api graphql -f query='mutation { updateRefs(input: {}) { clientMutationId } }'",
         "updateRefs"),
        ("gh api graphql -F query=@missing.graphql", "cannot be read"),
    ]:
        check(f"R3 deny: {command!r}", sb.bash(command), "deny", frag)

    # --- R5: every route to the default branch (AE4) ----------------------------------
    for command, cwd in [
        ("git push origin trunk", sb.trunk),
        ("git push origin HEAD:trunk", sb.feat),
        ("git push origin +HEAD:trunk", sb.feat),
        ("git push origin 76-x:refs/heads/trunk", sb.feat),
        ("git push origin +refs/heads/76-x:refs/heads/trunk", sb.feat),
        ("git push origin refs/heads/trunk", sb.feat),
        ("git push origin +trunk", sb.feat),
        ("git push origin :trunk", sb.feat),
        ("git push --delete origin trunk", sb.feat),
        ("git push origin 'refs/heads/*:refs/heads/*'", sb.feat),
        ("git push --all origin", sb.feat),
        ("git push --branches origin", sb.feat),
        ("git push --mirror origin", sb.feat),
        ("git push", sb.trunk),
        ("git push origin", sb.trunk),
        ("git push origin HEAD", sb.trunk),
        ("git push -f", sb.trunk),
        ("git push", sb.track),
        ("git push", sb.matching),
        (f"git -C {sb.trunk} push", sb.work),
        (f"cd {sb.trunk} && git push", sb.work),
        ("git push origin main", sb.nohead),
        ("git push origin master", sb.nohead),
        # The leak hook's parser used to split a command at a <(...) or >(...),
        # leaving the operands after it in a command of their own (#95).
        ("git push < <(echo y) origin trunk", sb.feat),
        ("git push > >(tee out.log) origin HEAD:trunk", sb.feat),
        ("env -S 'git push origin HEAD:trunk'", sb.feat),  # env -S runs its string (#117 review)
        # From the fix-delta review of #117: option values clustered or long,
        # env -S operands and clusters, and a named coproc.
        ("bash -euo pipefail -c 'git push origin HEAD:trunk'", sb.feat),
        ("bash -eo pipefail -c 'git push origin HEAD:trunk'", sb.feat),
        ("bash --rcfile /dev/null -c 'git push origin HEAD:trunk'", sb.feat),
        ("bash -c -o pipefail 'git push origin HEAD:trunk'", sb.feat),
        ("env -S git push origin HEAD:trunk", sb.feat),
        ("env -iS 'git push origin HEAD:trunk'", sb.feat),
        ("coproc P { git push origin HEAD:trunk; }", sb.feat),
        # From the second fix-delta review of #117: every word after a -c is a candidate script.
        ("bash -c - 'git push origin HEAD:trunk'", sb.feat),
        ("sh -c - 'git push origin HEAD:trunk'", sb.feat),
        ("bash -login -c 'git push origin HEAD:trunk'", sb.feat),
        ("bash -noprofile -c 'git push origin HEAD:trunk'", sb.feat),
        ("bash -norc -c 'git push origin HEAD:trunk'", sb.feat),
        ("bash -rcfile /dev/null -c 'git push origin HEAD:trunk'", sb.feat),
        ("bash +o pipefail -c 'git push origin HEAD:trunk'", sb.feat),
        ("bash -c -- 'git push origin HEAD:trunk'", sb.feat),
        ("env --split='git push origin HEAD:trunk'", sb.feat),
        ("env -iS'git push origin HEAD:trunk'", sb.feat),
        ("env -uX -S 'git push origin HEAD:trunk'", sb.feat),
    ]:
        check(f"R5 deny: {command!r} in {cwd.name}", sb.bash(command, cwd=cwd), "deny", PUSH)
    check("R5 deny: a refspec built at run time", sb.bash('git push origin "$B"', cwd=sb.feat),
          "deny", "use git push -u origin HEAD")
    check("R5 deny: the current branch by substitution, on the default",
          sb.bash('git push -u origin "$(git branch --show-current)"', cwd=sb.trunk), "deny", PUSH)
    check("R5 deny: the rev-parse substitution, on the default",
          sb.bash('git push origin "$(git rev-parse --abbrev-ref HEAD)"', cwd=sb.trunk), "deny", PUSH)
    check("R5 deny: a substitution with git -C, which runs in another directory",
          sb.bash(f'git -C {sb.feat} push origin "$(git branch --show-current)"', cwd=sb.trunk),
          "deny", "built when it runs")
    check("R5 deny: an unquoted substitution is built at run time, even on a feature branch",
          sb.bash("git push origin $(git branch --show-current)", cwd=sb.feat), "deny",
          "built when it runs")
    check("R5 deny: a bare push from a branch that tracks the default says so",
          sb.bash("git push", cwd=sb.track), "deny", "which this branch tracks")
    check("R5 deny: a bare push outside a clone", sb.bash("git push", cwd=sb.home),
          "deny", "cannot be checked")
    check("R5 deny: the denial names the opt-out", sb.bash("git push origin trunk", cwd=sb.trunk),
          "deny", "git config --local agentpolicy.allowDefaultPush true")

    # --- R5a: agents don't write the opt-out (AE4a) -----------------------------------
    for command in [
        "git config agentpolicy.allowDefaultPush true",
        "git config --local agentpolicy.allowdefaultpush false",
        "git config set agentpolicy.allowDefaultPush true",
        "git config --file .git/config agentpolicy.allowDefaultPush true",
        "git -c agentpolicy.allowDefaultPush=true push origin trunk",
        "git -cagentpolicy.allowDefaultPush=true push origin trunk",
        "git --config-env=agentpolicy.allowDefaultPush=V push origin trunk",
    ]:
        check(f"R5a deny: {command!r}", sb.bash(command, cwd=sb.trunk), "deny", OPT_OUT)

    # --- R6: GitHub MCP tools (AE5) ---------------------------------------------------
    for tool, tool_input, frag in [
        ("mcp__github__merge_pull_request", {"owner": "o", "repo": "r", "pullNumber": 12}, MERGE),
        ("mcp__github__update_repository", {}, SETTINGS),
        ("mcp__github__delete_repository", {}, SETTINGS),
        ("mcp__gh__create_repository_ruleset", {}, "rulesets"),
        ("mcp__github__update_branch_protection", {}, "branch protection"),
        ("mcp__github__push_files", {"branch": "main", "files": []}, "default branch"),
        ("mcp__github__create_or_update_file", {"path": "x"}, "default branch"),
    ]:
        check(f"R6 deny: {tool}", sb.mcp(tool, tool_input), "deny", frag)

    # --- R10: a command shlex cannot split, and input that is not a command ------------
    check("R10 deny: unbalanced quotes around gh pr merge",
          sb.bash('gh pr merge 12 --body "unbalanced'), "deny", MERGE)
    check("R10 deny: unbalanced quotes around git push",
          sb.bash('git push origin trunk "x', cwd=sb.trunk), "deny", "cannot be checked")
    check("R10 deny: input that is not JSON", sb.run("not json"), "deny", "not valid JSON")
    check("R10 deny: a Bash input with no command",
          sb.run(json.dumps({"tool_name": "Bash", "tool_input": {}})), "deny", "no command")

    # --- R7: what agents do today stays allowed --------------------------------------
    for command in [
        "gh pr create --title t --body-file body.md",
        "gh pr edit 12 --body-file body.md",
        "gh pr comment 12 --body-file body.md",
        "gh pr review 12 --comment -b ok",
        "gh pr ready 12",
        "gh pr close 12",
        "gh pr reopen 12",
        "gh pr checkout 12",
        "gh pr checks 12 --watch",
        "gh pr view 12 --json closingIssuesReferences",
        "gh pr diff 12",
        "gh issue create --title t --body-file body.md",
        "gh issue comment 76 --body-file body.md",
        "gh issue edit 76 --add-label sprint-2",
        "gh label create sprint-2",
        "gh issue comment 1 --body 'the operator runs gh pr merge, not an agent'",
        "gh api repos/o/r/pulls/12/merge",
        "gh api repos/o/r",
        "gh api -X GET repos/o/r/rulesets",
        "gh api -X GET repos/o/r/pulls -f state=open",
        "gh api repos/o/r/branches/trunk/protection",
        "gh api -X POST repos/o/r/issues/12/comments -f body=hi",
        "gh api repos/o/r/pulls/12/comments/1/replies -f body=hi",
        "gh api -X POST repos/o/r/issues/12/labels -f 'labels[]=x'",
        "gh api -X POST repos/o/r/issues/comments/1/reactions -f content=+1",
        "gh api --paginate repos/o/r/pulls/12/comments",
        "gh api graphql -f query='query { viewer { login } }'",
        "gh api graphql -F query=@read.graphql",
        "gh api graphql -F query=@resolve.graphql -f id=T_1",
        "gh ruleset list",
        "gh ruleset view 7",
        "gh ruleset check trunk",
        "gh repo view o/r",
        "gh repo clone o/r",
        "gh repo set-default o/r",
        "gh repo sync",
        "gh repo deploy-key list",
        "gh secret list",
        "gh variable list",
        "gh workflow list",
        "gh workflow run leaks.yml",
        "gh run view 1 --log-failed",
        "git config --get agentpolicy.allowDefaultPush",
        "git config --list",
        "git status",
        "git commit -m 'merging is the operator job'",
        "echo git push origin trunk",
    ]:
        check(f"R7 allow: {command!r}", sb.bash(command), "allow")
    for command, cwd in [
        ("git push -u origin 76-x", sb.feat),
        ("git push --force-with-lease origin 76-x", sb.feat),
        ("git push origin HEAD", sb.feat),
        ("git push origin HEAD:refs/heads/76-x", sb.feat),
        ("git push origin trunk:76-x", sb.feat),
        ("git push origin --tags", sb.feat),
        ("git push origin refs/tags/v1", sb.feat),
        ("git push --delete origin 76-x", sb.feat),
        ("git push", sb.feat),
        ("git push --dry-run origin trunk", sb.trunk),
        ("git push origin trunk", sb.nohead),
        ('git push -u origin "$(git branch --show-current)"', sb.feat),
        ('git push origin "$(git rev-parse --abbrev-ref HEAD)"', sb.feat),
        ('git push origin "$(git symbolic-ref --short HEAD)"', sb.feat),
        ("git push -u origin HEAD", sb.track),
        ("gh api -X PUT repos/o/r/contents/a.md -f message=m -f content=eA== -f branch=76-x",
         sb.trunk),
        ("gh api graphql -F query=@- <<'EOF'\nquery { viewer { login } }\nEOF", sb.work),
        ("gh api repos/o/r/contents/README.md", sb.work),
        ("git fetch origin trunk", sb.trunk),
        ("git pull origin trunk", sb.trunk),
    ]:
        check(f"R7 allow: {command!r} in {cwd.name}", sb.bash(command, cwd=cwd), "allow")
    # D3: a clone a person opted out pushes to its default branch.
    for command in ["git push origin trunk", "git push", "git push --all origin",
                    "git push origin HEAD:trunk"]:
        check(f"D3 opt-out allow: {command!r}", sb.bash(command, cwd=sb.optout), "allow")
    for tool, tool_input in [
        ("mcp__github__get_pull_request", {"pullNumber": 12}),
        ("mcp__github__list_rulesets", {}),
        ("mcp__github__get_branch_protection", {}),
        ("mcp__github__create_pull_request", {"base": "trunk", "head": "76-x"}),
        ("mcp__github__push_files", {"branch": "76-x", "files": []}),
        ("mcp__claude-code-remote__send_message", {"message": "merge it"}),
        ("Read", {"file_path": "/tmp/x"}),
    ]:
        check(f"R7 allow: {tool}", sb.mcp(tool, tool_input), "allow")

    # --- R8, KTD3: one decision point; no role is granted anything (AE6) -------------
    for role in ["principal", "maintainer", "operator", "worker", "lead", ""]:
        check(f"KTD3 deny with CLAUDE_AGENT_ROLE={role!r}",
              sb.bash("gh pr merge 12", env={"CLAUDE_AGENT_ROLE": role}), "deny", MERGE)
    check("KTD3 deny: a role set in the command, not the environment",
          sb.bash("CLAUDE_AGENT_ROLE=principal gh pr merge 12"), "deny", MERGE)
    rc, out, _ = sb.run("", env={"CLAUDE_AGENT_ROLE": "principal"}, args=["--whoami"])
    if rc == 0 and "role principal" in out and "granted: nothing" in out:
        ok()
    else:
        bad("KTD3 --whoami names the role and grants nothing", f"exit {rc}: {out!r}")
    rc, out, _ = sb.run("", args=["--whoami"])
    if rc == 0 and "role none" in out and "granted: nothing" in out:
        ok()
    else:
        bad("KTD3 --whoami with no role", f"exit {rc}: {out!r}")

    # --- KTD4, KTD5: a broken install denies every call --------------------------------
    broken = sb.root / "broken"
    broken.mkdir()
    shutil.copy(HOOK, broken / "claude_policy_hook.py")
    check("KTD4 deny: the leak hook is missing beside it",
          sb.bash("gh pr view 12", hook=broken / "claude_policy_hook.py"), "deny",
          "could not be imported")
    (broken / "claude_leak_hook.py").write_text("def broken(:\n")
    check("KTD4 deny: the leak hook does not compile",
          sb.bash("gh pr view 12", hook=broken / "claude_policy_hook.py"), "deny",
          "could not be imported")
    planted = sb.root / "planted"
    planted.mkdir()
    shutil.copy(LEAK_HOOK, planted / "claude_leak_hook.py")
    source = HOOK.read_text().replace(
        "def check_command(command, cwd):\n",
        "def check_command(command, cwd):\n    raise RuntimeError('planted')\n", 1)
    (planted / "claude_policy_hook.py").write_text(source)
    check("KTD5 deny: a crash in the hook", sb.bash("gh pr view 12",
          hook=planted / "claude_policy_hook.py"), "deny", "the hook failed")

    # --- Residuals: documented, pinned as still allowed ----------------------------------
    for name, command in [
        ("curl", "curl -X PUT https://api.github.com/repos/o/r/pulls/1/merge"),
        ("xargs", "echo 12 | xargs gh pr merge"),
        ("a pipe into sh", "echo 'gh pr merge 12' | sh"),
        ("a gh alias", "gh pm 12"),
        ("a make target", "make push"),
        ("a heredoc fed to a shell", "bash <<'EOF'\ngh pr merge 5\nEOF"),
        ("editing the clone's config file",
         "printf '[agentpolicy]\\n\\tallowDefaultPush = true\\n' >> .git/config"),
    ]:
        check(f"residual: {name}", sb.bash(command, cwd=sb.trunk), "allow", on_fail=RESIDUAL_DOC)

    # --- KTD2: the standard lists every gh command and mutation in the tables ---------
    spec = importlib.util.spec_from_file_location("policy_tables", REAL_HOOK)
    tables = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REAL_HOOK.parent))
    spec.loader.exec_module(tables)
    text = STANDARD.read_text()
    m = re.search(r"^## Guarding Repository Authority\n(.*?)^## ", text, re.S | re.M)
    section = m.group(1) if m else ""
    names = [f"gh {g} {v}" for g, v in tables.GH_COMMANDS] + list(tables.GRAPHQL_MUTATIONS)
    missing = [n for n in names if n not in section]
    if section and not missing:
        ok()
    else:
        bad("KTD2 the standard lists the denied commands",
            "no Guarding Repository Authority section" if not section
            else f"not in the section: {', '.join(missing)}")


if __name__ == "__main__":
    sys.exit(main())
