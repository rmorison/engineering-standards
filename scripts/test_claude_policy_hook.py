#!/usr/bin/env python3
"""Proves scripts/claude_policy_hook.py denies what it must and allows the rest.

CI runs this on every pull request (.github/workflows/agent-hooks.yml). Each fixture
feeds the hook one Claude Code PreToolUse input on standard input, as Claude
Code does, and checks the exit code (2 denies, 0 allows) and a fragment of the
message. An allowed call must print nothing.

Every fixture runs in a temporary directory, with HOME and GIT_CONFIG_GLOBAL
pointed at temporary files and CLAUDE_AGENT_ROLE and CLAUDE_MERGE_TRACK unset
unless a fixture sets them. The clones are local repositories with a made-up origin that is never
contacted: nothing here pushes, merges, or changes a setting anywhere. Nothing
here installs a hook or reads a value list.

Labels such as R5, AE4 and KTD3 in section comments refer to
docs/plans/2026-10-05-2058-feat-agent-policy-hook-plan.md; "U4" sections refer to
docs/plans/2026-11-20-0053-feat-coordinator-and-merge-authority-plan.md (R6, AE3).

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
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REAL_HOOK = ROOT / "scripts" / "claude_policy_hook.py"
LEAK_HOOK = ROOT / "scripts" / "claude_leak_hook.py"
HOOK = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REAL_HOOK
STANDARD = ROOT / "process" / "repository-standards.md"
HOOK_TIMEOUT = 20  # seconds; one call takes well under one

STOP = "the operator does that in the GitHub web UI"
LEAD_STOP = "A Track 2 lead merges only with gh pr merge"
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

    def merge_rule_only(self, command, env=None):
        """Runs only the hook's gh rule on a command, past its other rules: "denied",
        "allowed", or what went wrong."""
        probe = (
            "import sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "import importlib.util\n"
            "spec = importlib.util.spec_from_file_location('hook', sys.argv[2])\n"
            "hook = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(hook)\n"
            "for cmd in hook.parse(sys.argv[3], sys.argv[1])[0]:\n"
            "    cmd.raw_text, cmd.heredoc_files = sys.argv[3], set()\n"
            "    try:\n"
            "        hook.gh_command(cmd)\n"
            "    except hook.Deny:\n"
            "        print('denied')\n"
            "        sys.exit(0)\n"
            "print('allowed')\n")
        proc = subprocess.run([sys.executable, "-c", probe, str(Path(HOOK).parent), str(HOOK),
                               command], capture_output=True, env=dict(self.env, **(env or {})),
                              cwd=str(self.work), timeout=HOOK_TIMEOUT)
        out = proc.stdout.decode("utf-8", "replace").strip()
        return out if out in ("denied", "allowed") else (
            f"exit {proc.returncode}: {proc.stderr.decode('utf-8', 'replace').strip()}")

    def bash(self, command, cwd=None, env=None, hook=None, extra=None):
        return self.run(json.dumps({
            "session_id": "test",
            "cwd": str(cwd or self.work),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command, "description": "fixture"},
            **(extra or {}),
        }), env=env, hook=hook)

    def mcp(self, tool, tool_input, env=None):
        return self.run(json.dumps({
            "session_id": "test",
            "cwd": str(self.work),
            "hook_event_name": "PreToolUse",
            "tool_name": tool,
            "tool_input": tool_input,
        }), env=env)

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def check(name, result, want, frag=None, on_fail=None, stop=None):
    """want is 'deny' or 'allow' (exit 0 and no output at all)."""
    rc, out, err = result
    stop = stop or STOP
    if want == "deny":
        if rc != 2:
            return bad(name, on_fail or f"exit {rc}, expected 2 (deny)", result)
        if stop not in err:
            return bad(name, f"the denial does not say {stop!r}", result)
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
        # From the third fix-delta review of #117: a script starting with - or +, and +c.
        ("bash -c -- '-x; git push origin HEAD:trunk'", sb.feat),
        ("sh -c - '+x; git push origin HEAD:trunk'", sb.feat),
        ("bash +c 'git push origin HEAD:trunk'", sb.feat),
        ("sh +c 'git push origin HEAD:trunk'", sb.feat),
        # An fd number joined to a redirect is part of it, not the remote (#114).
        ("git push 2>/dev/null origin HEAD:trunk", sb.feat),
        ("git push 2>&1 origin HEAD:trunk", sb.feat),
        ("git push 1>out.log origin HEAD:trunk", sb.feat),
        ("git push &>out.log origin HEAD:trunk", sb.feat),
        ("git push 2>>err.log origin HEAD:trunk", sb.feat),
        ("git push 0</dev/null origin HEAD:trunk", sb.feat),
        ("git push 10>out.log origin HEAD:trunk", sb.feat),
        # A here-string is a redirect, not a separator (#114).
        ("git push <<< y origin HEAD:trunk", sb.feat),
        # The digits after >& are the fd duplicated, not an fd number (#118 review).
        ("git push 2>&1>/dev/null origin HEAD:trunk", sb.feat),
        ("git push >&2>/dev/null origin HEAD:trunk", sb.feat),
        # Even across a space (#118 review).
        ("git push >& 2>/dev/null origin HEAD:trunk", sb.feat),
        ("git push 2>& 1>/dev/null origin HEAD:trunk", sb.feat),
        ("git push <& 0</dev/null origin HEAD:trunk", sb.feat),
        # env reads --un as --unset, which takes a value (#118 review).
        ("env --un FOO git push origin HEAD:trunk", sb.feat),
        # From the fix-delta review of #118: a quoted or escaped >& is not a dup
        # operator, and wrappers' options are read as getopt reads them.
        ("X='a>&' 2>/dev/null git push origin HEAD:trunk", sb.feat),
        ("git -c 'x.y=a>&' 2>/dev/null push origin HEAD:trunk", sb.feat),
        ("git push <<< 'x>&' 2>/dev/null origin HEAD:trunk", sb.feat),
        ("echo a\\>&2>/dev/null git push origin HEAD:trunk", sb.feat),
        ("timeout --sig KILL 5 git push origin HEAD:trunk", sb.feat),
        ("nice --adj 5 git push origin HEAD:trunk", sb.feat),
        ("sudo --us root git push origin HEAD:trunk", sb.feat),
        ("env -iu FOO git push origin HEAD:trunk", sb.feat),
        ("env --un X -S 'git push origin HEAD:trunk'", sb.feat),  # the rebase onto #117
        # shlex treats a carriage return as a blank, so the dup flag must too (#118 review).
        ("git push >&\r2>/dev/null origin HEAD:trunk", sb.feat),
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

    # --- The policy canary reports the host's permission mode (issue 137) --------------
    # Claude Code puts the session's mode in every hook's input. The canary's denial names
    # it, so the guardrail check's mode check reads it from the host, not from a notice.
    canary = "git -c agentpolicy.allowDefaultPush=true --version"
    for mode in ["default", "acceptEdits", "plan", "auto", "dontAsk", "bypassPermissions"]:
        check(f"137 canary names mode {mode}",
              sb.bash(canary, extra={"permission_mode": mode}), "deny",
              f"(permission mode: {mode})")
    for name, extra in [
        ("absent", {}),
        ("not a known mode", {"permission_mode": "Auto"}),
        ("text that would forge a mode", {"permission_mode": "plan) (permission mode: auto"}),
        ("not a string", {"permission_mode": ["auto"]}),
    ]:
        result = sb.bash(canary, extra=extra)
        check(f"137 canary mode {name} reads unknown", result, "deny",
              "(permission mode: unknown)")
        if "(permission mode: auto)" in result[2]:
            bad(f"137 canary mode {name}", "the input's text reached the denial", result)
    result = sb.bash("gh pr merge 12 --squash", extra={"permission_mode": "auto"})
    check("137 other denials name no mode", result, "deny", MERGE)
    if "permission mode" in result[2]:
        bad("137 other denials name no mode", "a denial other than the canary's names the mode",
            result)

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
        ("git push 2>/dev/null -u origin 76-x", sb.feat),  # #114
        ("echo 2 > f.txt", sb.feat),  # with a space, 2 is an argument (#114)
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

    # --- R8, KTD3: one decision point; a role outside the grant grants nothing (AE6) --
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

    # --- U4, R6, AE3: a Track 2 lead may run gh pr merge, without --admin -------------
    lead2 = {"CLAUDE_AGENT_ROLE": "lead", "CLAUDE_MERGE_TRACK": "2"}
    for command in [
        "gh pr merge 12 --squash",
        "gh pr merge --auto 12 --squash",
        "gh -R o/r pr merge 12 --rebase -d",
        "gh pr merge 12 --merge --match-head-commit abc123",
        "gh pr merge 12 --disable-auto",
        "sh -c 'gh pr merge 12 --squash'",
    ]:
        check(f"U4 allow, Track 2 lead: {command!r}", sb.bash(command, env=lead2), "allow")
    for command in [
        "gh pr merge 12 --admin",
        "gh pr merge 12 --admin --squash",
        "gh pr merge 12 --admin=false --squash",
        "gh -R o/r pr merge --admin 12",
        "gh pr merge 12 --squash -- --admin",
        "sh -c 'gh pr merge 12 --admin'",
    ]:
        check(f"U4 deny --admin, Track 2 lead: {command!r}", sb.bash(command, env=lead2),
              "deny", "with --admin", stop=LEAD_STOP)
    # A word built when the command runs could become --admin.
    for command in [
        "F=--admin; gh pr merge 12 $F",
        'gh pr merge 12 "$(echo --admin)"',
        "gh pr merge 12 `echo --admin`",
        'bash -c "gh pr merge 12 \\$X"',
        'gh pr merge "$PR" --squash',
        "gh pr merge 12 --{admin,squash}",
        "gh pr merge 12 --adm?n",
        "gh pr merge 12 --admi[n]",
        "gh pr merge 12 --a*",
        "shopt -s extglob\ngh pr merge 12 --@(admin)",
        "gh pr merge 12 --+(admin)",
        "HOME=--admin; gh pr merge 12 ~",
        "OLDPWD=--admin; gh pr merge 12 --squash ~-",
        "pushd -n /tmp; DIRSTACK[1]=--admin; gh pr merge 12 ~1",
        'bash -c "HOME=--admin; gh pr merge 12 --squash ~"',
        "gh pr merge 12 --!(squash|merge|rebase)",
        "gh pr merge 12 --squash -t 'feat: x (#12)'",
        "gh pr merge 12 --squash -t 'cost $5'",  # a quoted $ can't be told apart
    ]:
        check(f"U4 deny a word the shell could expand, Track 2 lead: {command!r}",
              sb.bash(command, env=lead2), "deny", "could expand", stop=LEAD_STOP)
    check("U4 deny, Track 2 lead: a subject ending in + is named in the advice",
          sb.bash('gh pr merge 12 --squash -t "Support C++"', env=lead2), "deny",
          "ends in !, + or @", stop=LEAD_STOP)
    check("U4 deny, Track 2 lead: a body file named with ~ is named in the advice",
          sb.bash("gh pr merge 12 --squash -F ~/body.md", env=lead2), "deny",
          "named without ~", stop=LEAD_STOP)
    check("U4 allow, Track 2 lead: a subject or body from a file",
          sb.bash("gh pr merge 12 --squash -t 'Fix the cost' -F body.md", env=lead2), "allow")
    # Every other route to a merge stays denied, granted to no role, and the
    # Track 2 lead is told the one way it may merge.
    for command, frag in [
        ("gh api -X PUT repos/o/r/pulls/12/merge", MERGE),
        ("gh api graphql -F query=@merge.graphql -f id=x", "mergePullRequest"),
        ("gh api graphql -f query='mutation { enablePullRequestAutoMerge(input: {}) { clientMutationId } }'",
         "enablePullRequestAutoMerge"),
        ("gh pr merge 12 --squash '", MERGE),  # cannot be split: the fallback
    ]:
        check(f"U4 deny, Track 2 lead: {command!r}", sb.bash(command, env=lead2), "deny", frag,
              stop=LEAD_STOP)
    check("U4 deny, Track 2 lead: MCP merge_pull_request",
          sb.mcp("mcp__github__merge_pull_request", {"pullNumber": 12}, env=lead2), "deny", MERGE,
          stop=LEAD_STOP)
    for command, frag in [
        ("gh repo edit --enable-auto-merge", SETTINGS),
        ("gh api -X PUT repos/o/r/rulesets/1 -f name=x", "rulesets"),
        ("git -c agentpolicy.allowDefaultPush=true --version", OPT_OUT),
    ]:
        check(f"U4 deny, Track 2 lead: {command!r}", sb.bash(command, env=lead2), "deny", frag)
    check("U4 deny, Track 2 lead: git push origin trunk",
          sb.bash("git push origin trunk", cwd=sb.trunk, env=lead2), "deny", PUSH)
    # Any other role, or a lead not on Track 2, is denied both forms with today's message.
    sessions = [("coordinator", "2"), ("worker", "2"), ("principal", "2"), ("Lead", "2"),
                ("", "2"), ("lead", None), ("lead", ""), ("lead", "1"), ("lead", "two"),
                ("lead", " 2"), ("lead", "2 "), ("lead", "Track 2")]
    for role, track in sessions:
        env = {"CLAUDE_AGENT_ROLE": role}
        if track is not None:
            env["CLAUDE_MERGE_TRACK"] = track
        for command in ["gh pr merge 12 --squash", "gh pr merge 12 --admin"]:
            rc, out, err = result = sb.bash(command, env=env)
            name = f"U4 deny role={role!r} track={track!r}: {command!r}"
            if "with --admin" in err or LEAD_STOP in err:
                bad(name, "the denial is a Track 2 lead's, not today's message", result)
            else:
                check(name, result, "deny", MERGE)
    check("U4 deny: a track set in the command, not the environment",
          sb.bash("CLAUDE_MERGE_TRACK=2 gh pr merge 12 --squash",
                  env={"CLAUDE_AGENT_ROLE": "lead"}), "deny", "setting CLAUDE_MERGE_TRACK")
    # The track rule denies that command first, so check the merge rule on its own:
    # it must deny the same command to a lead whose environment has no track.
    verdict = sb.merge_rule_only("CLAUDE_MERGE_TRACK=2 gh pr merge 12 --squash",
                                 env={"CLAUDE_AGENT_ROLE": "lead"})
    if verdict == "denied":
        ok()
    else:
        bad("U4 the merge rule ignores a track set in the command", verdict)
    for name, env, want in [
        ("names the coordinator, granted nothing", {"CLAUDE_AGENT_ROLE": "coordinator",
                                                     "CLAUDE_MERGE_TRACK": "2"},
         ["role coordinator", "track 2", "granted: nothing"]),
        ("a Track 2 lead is granted pr-merge", lead2, ["role lead", "track 2", "granted: pr-merge"]),
        ("a lead with no track is granted nothing", {"CLAUDE_AGENT_ROLE": "lead"},
         ["role lead", "track 1", "granted: nothing"]),
        ("an unknown role is named as unknown", {"CLAUDE_AGENT_ROLE": "principal"},
         ["role principal", "unknown", "granted: nothing"]),
    ]:
        rc, out, _ = sb.run("", env=env, args=["--whoami"])
        if rc == 0 and all(w in out for w in want):
            ok()
        else:
            bad(f"U4 --whoami {name}", f"exit {rc}: {out!r}")

    # --- U4, from #144's review: only the operator sets CLAUDE_MERGE_TRACK ---------
    # A session that set it for a child could start a Track 2 lead. Every form the
    # parser reads is denied to every role; env -u and the role alone stay allowed.
    TRACK_SET = "setting CLAUDE_MERGE_TRACK"
    for command in [
        "CLAUDE_AGENT_ROLE=lead CLAUDE_MERGE_TRACK=2 claude -p x",
        "CLAUDE_MERGE_TRACK=1 claude -p x",
        "env CLAUDE_MERGE_TRACK=2 claude -p x",
        "env -i PATH=/usr/bin CLAUDE_MERGE_TRACK=2 claude -p x",
        "sudo CLAUDE_MERGE_TRACK=2 claude -p x",
        "export CLAUDE_MERGE_TRACK=2; claude -p x",
        "export CLAUDE_MERGE_TRACK",
        "declare -x CLAUDE_MERGE_TRACK=2",
        "typeset -x CLAUDE_MERGE_TRACK=2",
        "readonly CLAUDE_MERGE_TRACK=2",
        "local CLAUDE_MERGE_TRACK=2",
        "CLAUDE_MERGE_TRACK=2; export CLAUDE_MERGE_TRACK; claude -p x",
        "CLAUDE_MERGE_TRACK+=2 claude -p x",
        "printf -v CLAUDE_MERGE_TRACK 2",
        "read CLAUDE_MERGE_TRACK <<< 2",
        "sh -c 'CLAUDE_MERGE_TRACK=2 claude -p x'",
        "env -S 'CLAUDE_MERGE_TRACK=2 claude -p x'",
        "if true; then export CLAUDE_MERGE_TRACK=2; fi",
        "X+=1 CLAUDE_MERGE_TRACK=2 claude -p x",
        "set -a; let CLAUDE_MERGE_TRACK=2; claude -p x",
        "set -a; : ${CLAUDE_MERGE_TRACK:=2}; claude -p x",
        "set -a; : ${CLAUDE_MERGE_TRACK=2}; claude -p x",
        "set -a; for CLAUDE_MERGE_TRACK in 2; do claude -p x; done",
        "declare -n r=CLAUDE_MERGE_TRACK; export r=2; claude -p x",
        "printf -vCLAUDE_MERGE_TRACK 2",
        "xargs env CLAUDE_MERGE_TRACK=2 claude -p x </dev/null",
        "setsid env CLAUDE_MERGE_TRACK=2 claude -p x",
        "tmux new -d -e CLAUDE_MERGE_TRACK=2 claude",
        "systemd-run --user -E CLAUDE_MERGE_TRACK=2 claude",
        "claude -p x --settings '{\"env\":{\"CLAUDE_MERGE_TRACK\":\"2\"}}'",
        "set -a; let CLAUDE_MERGE_TRACK++ CLAUDE_MERGE_TRACK++; claude -p x",
        "set -a; let 'CLAUDE_MERGE_TRACK = 2'; claude -p x",
        "set -a; (( CLAUDE_MERGE_TRACK = 2 )); claude -p x",
        "set -a; getopts 2 CLAUDE_MERGE_TRACK -2; claude -p x",
        "sleep 1 & wait -p CLAUDE_MERGE_TRACK",
        "set -a; declare -n r; r=CLAUDE_MERGE_TRACK; r=2; claude -p x",
        "setsid claude -p x --settings '{\"env\":{\"CLAUDE_MERGE_TRACK\":\"2\"}}'",
        "xargs claude -p x --settings '{\"env\":{\"CLAUDE_MERGE_TRACK\":\"2\"}}' </dev/null",
        "npx claude -p x --settings '{\"env\":{\"CLAUDE_MERGE_TRACK\":\"2\"}}'",
        "set -a; ((++CLAUDE_MERGE_TRACK)); ((++CLAUDE_MERGE_TRACK)); claude -p x",
        "set -a; (( x = 1, CLAUDE_MERGE_TRACK = 2 )); claude -p x",
        "set -a; : $(( CLAUDE_MERGE_TRACK++ )); claude -p x",
        "set -a; a[CLAUDE_MERGE_TRACK=2]=1; claude -p x",
        "set -a; v=x; : ${v:CLAUDE_MERGE_TRACK=2}; claude -p x",
        "tmux new -d \"CLAUDE_MERGE_TRACK=2 claude -p x\"",
        "gh pr comment 1 --body 'the lead runs with CLAUDE_MERGE_TRACK=2'",  # prose: broad on purpose
        "set -a; read {CLAUDE_MERGE_TRACK,} <<< 2; claude -p x",
        "export CLAUDE_MERGE_TRAC{K,}=2; claude -p x",
        "printf -v {CLAUDE_MERGE_TRACK,} 2",
        "export CLAUDE_MERGE_{TRACK,X}=2; claude -p x",
        "export {X,CLAUDE_MERGE_TRACK}=2; claude -p x",
        "export CLAUDE_{MERGE,X}_{TRACK,Y}=2; claude -p x",
        "declare -n r; export -n r=CLAUDE_MERGE_TRACK; r=2; export r; claude -p x",
        "bash <<< 'CLAUDE_MERGE_TRACK=2 claude -p x'",
        "source /dev/stdin <<< 'CLAUDE_MERGE_TRACK=2'",
        "bash <<'EOF'\nCLAUDE_MERGE_TRACK=2 claude -p x\nEOF",
        "export {" + "," * 300 + "}CLAUDE_MERGE_TRAC{K,}=2; claude -p x",
        "export {" + "a," * 300 + "}CLAUDE_MERGE_{TRACK,X}=2; claude -p x",
        "export CLAUDE_MERGE_TRAC{K..K}=2; claude -p x",
        "export {" + "," * 300 + "}{C,}LAUDE_{M,}ERGE_{T,}RACK=2; claude -p x",
        "export CLAUDE_MERGE_TRAC{J..L}=2; claude -p x",
        "cat <<'EOF' | bash\nCLAUDE_MERGE_TRACK=2 claude -p x\nEOF",
        "cat <<'EOF' | tee /dev/null | bash\nCLAUDE_MERGE_TRACK=2 claude -p x\nEOF",
        "cat <<'EOF' | sudo bash\nCLAUDE_MERGE_TRACK=2 claude -p x\nEOF",
        "cat <<'EOF' | env bash\nCLAUDE_MERGE_TRACK=2 claude -p x\nEOF",
        "bash <<< 'export CLAUDE_MERGE_TRAC{K,}=2; claude -p x'",
        "bash <<< 'declare -n r=CLAUDE_MERGE_TRACK; r=2; export r; claude -p x'",
        "bash <<< 'printf -v CLAUDE_MERGE_TRACK 2; export CLAUDE_MERGE_TRACK; claude -p x'",
        "claude -p x --settings '{\"env\":{\"CLAUDE_MERGE_\\u0054RACK\":\"2\"}}'",
        "((CLAUDE_MERGE_TRACK++)); echo '",  # cannot be split: the fallback
        "(( CLAUDE_MERGE_TRACK *= 1 )); echo '",  # cannot be split: the fallback
        "claude -p 'x\nCLAUDE_MERGE_TRACK=2 claude -p y '\"",  # cannot be split: the fallback
    ]:
        for role, env in [("none", {}), ("worker", {"CLAUDE_AGENT_ROLE": "worker"}),
                          ("Track 2 lead", lead2)]:
            check(f"U4 deny setting the track, {role}: {command!r}", sb.bash(command, env=env),
                  "deny", TRACK_SET)
    for command in [
        "env -u CLAUDE_MERGE_TRACK CLAUDE_AGENT_ROLE=worker claude --bg --agent agent-team:worker",
        "env --unset=CLAUDE_MERGE_TRACK claude -p x",
        "CLAUDE_AGENT_ROLE=worker claude -p x",
        "unset CLAUDE_MERGE_TRACK",
        "echo \"$CLAUDE_MERGE_TRACK\"",
        "grep -n CLAUDE_MERGE_TRACK process/repository-standards.md",
        "git commit -q -m 'docs: only the operator sets CLAUDE_MERGE_TRACK'",
        "declare -p CLAUDE_MERGE_TRACK",
        "typeset -p CLAUDE_MERGE_TRACK",
        "export -n CLAUDE_MERGE_TRACK",
        "printf '%s\\n' CLAUDE_MERGE_TRACK",
        "grep -n '\"CLAUDE_MERGE_TRACK\":' .claude/settings.json",
        "X=$CLAUDE_MERGE_TRACK; echo \"$X\"",
        "X=${#CLAUDE_MERGE_TRACK}; Y=${!CLAUDE_MERGE_TRACK}; Z=${CLAUDE_MERGE_TRACK:-1}",
        "test \"$CLAUDE_MERGE_TRACK\" = 2 && echo two",
        "rg -n '\"CLAUDE_MERGE_TRACK\":' .",
        "git grep -n '\"CLAUDE_MERGE_TRACK\":'",
        "grep -rn CLAUDE_MERGE_TRACK --include=*.py .",
        "git log -S CLAUDE_MERGE_TRACK -- scripts",
        "unset -v -- CLAUDE_MERGE_TRACK",
        "echo ${CLAUDE_MERGE_TRACK-=} ${CLAUDE_MERGE_TRACK/=/x}",
        "echo {a,b}=1 CLAUDE_MERGE_TRACK",
        "cat <<'EOF' > notes.md\nThe operator sets CLAUDE_MERGE_TRACK=2.\nEOF",
        "bash -s <<< 'make test'; echo CLAUDE_MERGE_TRACK",
        "echo {²..3}",
        "touch CLAUDE{1..300}.md",
        "echo {1..300}TRACE",
        "cat <<'EOF' > notes.md\nCLAUDE_MERGE_TRACK docs\nEOF\nbash build.sh",
    ]:
        check(f"U4 allow, Track 2 lead: {command!r}", sb.bash(command, env=lead2), "allow")

    # --- #145's round at 54948e6: the reviews' findings, each seen failing there ------
    worker = {"CLAUDE_AGENT_ROLE": "worker"}
    # C1: a << the shell does not read as a heredoc hides no line after it.
    for name, command, cwd, frag in [
        ("a <<X in a comment", "# see <<X\ngh pr merge 12\nX", None, MERGE),
        ("a <<X in double quotes", 'echo "<<X"; true\ngit push origin HEAD:trunk\nX', sb.feat, PUSH),
        ("a <<X in single quotes", "echo '<<X'\ngh pr merge 12\nX", None, MERGE),
        ("a << in arithmetic", ": $((1<<a))\ngh pr merge 12\na", None, MERGE),
    ]:
        check(f"C1 deny the line after {name}", sb.bash(command, cwd=cwd, env=worker), "deny", frag)
    for name, command in [
        ("a heredoc into cat", "cat <<'EOF' > notes.md\ngh pr merge 12\nEOF"),
        ("a heredoc in a quoted $(cat)",
         "gh pr comment 1 --body \"$(cat <<'EOF'\nit's time to gh pr merge 12\nEOF\n)\""),
        ("a <<- heredoc", "cat <<-EOF\n\tgh pr merge 12\n\tEOF"),
    ]:
        check(f"C1 allow {name}", sb.bash(command, env=worker), "allow")
    # The safety net: with a parser planted to read << in a comment as a heredoc, the
    # body it hides, which no command reads, is still checked as a command.
    netted = sb.root / "netted"
    netted.mkdir()
    shutil.copy(HOOK, netted / "claude_policy_hook.py")
    (netted / "claude_leak_hook.py").write_text((HOOK.parent / "claude_leak_hook.py").read_text().replace(
        'elif c == "#" and (i == 0 or text[i - 1] in COMMENT_START):', "elif False:", 1))
    check("C1 deny a heredoc body no command reads (the safety net)",
          sb.bash("# see <<X\ngh pr merge 12\nX", env=worker, hook=netted / "claude_policy_hook.py"),
          "deny", MERGE)

    # A deadline: the host does not block a call when a hook times out, so the hook
    # denies first. This runs it with a one-second deadline and a check that sleeps.
    probe = (
        "import sys, time\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "import importlib.util\n"
        "spec = importlib.util.spec_from_file_location('hook', sys.argv[2])\n"
        "hook = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(hook)\n"
        "hook.DEADLINE = 1\n"
        "hook.check_command = lambda *a, **k: time.sleep(5)\n"
        "sys.exit(hook.main())\n")
    try:
        proc = subprocess.run([sys.executable, "-c", probe, str(HOOK.parent), str(HOOK)],
                              input=json.dumps({"tool_name": "Bash", "cwd": str(sb.work),
                                                "tool_input": {"command": "gh pr view 12"}}).encode(),
                              capture_output=True, env=sb.env, cwd=str(sb.work), timeout=HOOK_TIMEOUT)
        result = (proc.returncode, proc.stdout.decode("utf-8", "replace"),
                  proc.stderr.decode("utf-8", "replace"))
    except subprocess.TimeoutExpired:
        result = ("timeout", "", "")
    check("deny a check past the deadline", result, "deny", "deadline")

    # P1, H2: input built to make a check slow takes linear time, and is denied.
    for name, command, env, limit, stop in [
        ("8 KB of <<a| after a shell", "bash -c : ; " + "<<a|" * 2000 + "\ngh pr merge 12 --admin",
         worker, 1.0, None),
        ("a 60 KB brace group", "echo {" + ",a" * 30000 + "; gh pr merge 12 --admin", lead2, 2.0,
         LEAD_STOP),
    ]:
        started = time.monotonic()
        result = sb.bash(command, env=env)
        took = time.monotonic() - started
        check(f"timing: deny {name}", result, "deny", stop=stop)
        if took < limit:
            ok()
        else:
            bad(f"timing: {name}", f"took {took:.1f} s, more than {limit} s")

    # M3, M4, L7: more ways to set the track, each denied to every role.
    for command in [
        ": > 'CLAUDE_MERGE_TRACK=2'; env CLAUDE_MERGE_TRAC?=2 CLAUDE_AGENT_ROLE=lead claude -p 'merge 12'",
        "env CLAUDE_MERGE_TRAC[K]=2 claude",
        "export $'CLAUDE_MERGE_TRACK=2'",
        "export $(echo CLAUDE_MERGE_TRACK)=2",
        "export ${X}=2",
        "tmux new -e 'CLAUDE_MERGE_TRAC*=2'",
        "jq -n '{env:{CLAUDE_MERGE_TRACK:\"2\"}}' > .claude/settings.local.json",
        "printf '%s' '{env:{CLAUDE_MERGE_TRACK:\"2\"}}' > .claude/settings.local.json",
        "printf '{\"env\":{\"%s\":\"2\"}}' CLAUDE_MERGE_TRACK > .claude/settings.local.json",
        "tmux setenv CLAUDE_MERGE_TRACK 2",
        "tmux set-environment -g CLAUDE_MERGE_TRACK 2",
        "systemctl --user import-environment CLAUDE_MERGE_TRACK",
        "screen -X setenv CLAUDE_MERGE_TRACK 2",
        "fish -c 'set -gx CLAUDE_MERGE_TRACK 2'",
        "tcsh -c 'setenv CLAUDE_MERGE_TRACK 2'",
    ]:
        for label, env in (("worker", worker), ("Track 2 lead", lead2)):
            check(f"M3/M4/L7 deny, {label}: {command!r}", sb.bash(command, env=env), "deny",
                  "setting CLAUDE_MERGE_TRACK")
    for command in ["typeset +x CLAUDE_MERGE_TRACK", "declare +x CLAUDE_MERGE_TRACK",
                    "awk -F= '{print $2}' body.md", "echo \"${CLAUDE_MERGE_TRACK:0:1}\""]:
        check(f"track allow: {command!r}", sb.bash(command, env=worker), "allow")

    # M5, P3: aliases, extensions, runners and wrappers that run a command.
    gh_unchecked = "a gh alias or extension"
    for command, frag in [
        ("gh alias set mm 'pr merge'", gh_unchecked),
        ("gh alias import aliases.yml", gh_unchecked),
        ("gh mm 12", gh_unchecked),
        ("gh extension exec merge-it 12", gh_unchecked),
        ("shopt -s expand_aliases; alias m='gh pr merge 12'\nm", "an alias for gh or git"),
        ("echo 12 | xargs gh pr merge", MERGE),
        ("echo 12 | xargs -n 1 -I{} gh pr merge {}", MERGE),
        ("find . -maxdepth 0 -exec gh pr merge 12 \\;", MERGE),
        ("parallel gh pr merge ::: 12", MERGE),
        ("parallel ::: 'gh pr merge 12'", MERGE),
        ("bash <<<'gh pr merge 12'", MERGE),
        ("bash <<'EOF'\ngh pr merge 5\nEOF", MERGE),
        ("cat <<'EOF' | bash\ngh pr merge 5\nEOF", MERGE),
        ("setsid gh pr merge 12", MERGE),
        ("stdbuf -o0 gh pr merge 12", MERGE),
        ("watch -n1 gh pr merge 12", MERGE),
        ("watch -n1 'gh pr merge 12'", MERGE),
        ("flock /tmp/l gh pr merge 12", MERGE),
        ("flock /tmp/l -c 'gh pr merge 12'", MERGE),
        ("script -qc 'gh pr merge 12' /dev/null", MERGE),
        ("ionice -c2 -n0 gh pr merge 12", MERGE),
        ("chrt 10 gh pr merge 12", MERGE),
        ("taskset 0x1 gh pr merge 12", MERGE),
    ]:
        check(f"M5/P3 deny, worker: {command!r}", sb.bash(command, env=worker), "deny", frag)
    for command, frag in [
        ("gh alias set mm 'pr merge --admin'\ngh mm 12", gh_unchecked),
        ("shopt -s expand_aliases; alias m='gh pr merge 12 --admin'\nm", "an alias for gh or git"),
        ("echo 12 | xargs gh pr merge --admin", "with --admin"),
        ("bash <<<'gh pr merge 12 --admin'", "with --admin"),
        ("setsid gh pr merge 12 --admin", "with --admin"),
        ("script -qc 'gh pr merge 12 --admin' /dev/null", "with --admin"),
    ]:
        check(f"M5/P3 deny, Track 2 lead: {command!r}", sb.bash(command, env=lead2), "deny", frag,
              stop=LEAD_STOP)
    for command in ["gh pr checkout 12", "gh extension list", "alias ll='ls -l'",
                    "git ls-files | xargs grep -n gh", "find . -name '*.md' -exec wc -l {} +",
                    "script -q /dev/null", "setsid -f sleep 1", "watch -n1 gh pr checks 12"]:
        check(f"M5/P3 allow: {command!r}", sb.bash(command, env=worker), "allow")

    # L6: a merge endpoint spelt another way GitHub may route the same.
    for path in ["repos/o/r/pulls/12/merge#x", "repos/o/r//pulls/12/merge", "repos/o/r/pulls/12/./merge",
                 "repos//o/r/pulls/12/merge", "repos/o/r/pulls/1/%6Derge",
                 "repos/o/r/pulls/12/x/../merge", "repos/o/r/pulls/12/merge?x=1"]:
        check(f"L6 deny: gh api {path!r} -X PUT", sb.bash(f"gh api '{path}' -X PUT", env=worker),
              "deny", "merging a pull request through the API")

    # m1, m8: a second fixture for the --admin= form and for words after --.
    for command in ["gh pr merge --admin=true 12", "gh pr merge -- 12 --admin"]:
        check(f"U4 deny --admin, Track 2 lead: {command!r}", sb.bash(command, env=lead2),
              "deny", "with --admin", stop=LEAD_STOP)

    # The review of this round's fix: runners that start a shell, a shell fed a heredoc
    # from a group, an array element, an -e that is a pattern, and gh's help topics.
    for command in ["echo 12 | xargs sh -c 'gh pr merge 12'",
                    "find . -maxdepth 0 -exec sh -c 'gh pr merge 12' \\;",
                    "parallel sh -c 'gh pr merge 12' ::: 1",
                    "echo 12 | xargs env -S 'gh pr merge 12'",
                    "{ bash; } <<'EOF'\ngh pr merge 5\nEOF",
                    "( bash ) <<'EOF'\ngh pr merge 5\nEOF"]:
        check(f"review deny, worker: {command!r}", sb.bash(command, env=worker), "deny", MERGE)
    check("review deny: an element of the track's own name",
          sb.bash("CLAUDE_MERGE_TRACK[0]=2 claude", env=worker), "deny", "setting CLAUDE_MERGE_TRACK")
    for command in ["arr[$i]=1", "m[$key]=x; export m", "grep -e \"$pat=1\" notes.md", "gh actions"]:
        check(f"review allow: {command!r}", sb.bash(command, env=worker), "allow")
    started = time.monotonic()
    result = sb.bash("script " + "-qc 'echo hi' " * 16000 + "/dev/null; gh pr merge 12", env=worker)
    took = time.monotonic() - started
    check("timing: deny 220 KB of script -qc", result, "deny", MERGE)
    if took < 3.0:
        ok()
    else:
        bad("timing: 220 KB of script -qc", f"took {took:.1f} s, more than 3.0 s")

    # --- #145's round 2 at 79b9363 ------------------------------------------------
    # A heredoc body the shell expands runs its substitutions; a quoted delimiter
    # keeps the body text, and a plain variable runs nothing.
    expanded = "a heredoc body that runs a command substitution"
    for command in ["cat <<EOF\n$(gh pr merge 12)\nEOF",
                    "cat <<EOF > notes.md\n`git push origin HEAD:trunk`\nEOF",
                    "cat <<-EOF\n\t$((1 + 2)) $(gh pr merge 12)\n\tEOF",
                    "cat <<EOF\n\\\\$(gh pr merge 12)\nEOF",
                    "cat <<EOF\n$\\\n(gh pr merge 12)\nEOF"]:
        for label, env in (("worker", worker), ("Track 2 lead", lead2)):
            check(f"round 2 deny, {label}: {command!r}", sb.bash(command, cwd=sb.feat, env=env),
                  "deny", expanded)
    for command in ["cat <<'EOF'\n$(gh pr merge 12)\nEOF", "cat <<\"EOF\"\n`gh pr merge 12`\nEOF",
                    "cat <<\\EOF\n$(gh pr merge 12)\nEOF", "cat <<EOF > notes.md\nplain text, $HOME\nEOF",
                    "cat <<EOF\n\\$(not run) \\`nor this\\`\nEOF"]:
        check(f"round 2 allow: {command!r}", sb.bash(command, env=worker), "allow")

    # Arguments xargs, parallel or find add when they run reach a Track 2 lead's merge.
    for command in ["echo --admin | xargs gh pr merge 12", "xargs -a args.txt gh pr merge 12",
                    "parallel gh pr merge 12 ::: --admin",
                    "find . -name x -exec gh pr merge 12 +",
                    "echo 12 | xargs sh -c 'gh pr merge \"$@\"' _",
                    "parallel ::: 'gh pr merge 12' ::: --admin"]:
        check(f"round 2 deny, Track 2 lead: {command!r}", sb.bash(command, env=lead2), "deny",
              "run by xargs, parallel or find", stop=LEAD_STOP)
    for command in ["echo 12 | xargs gh pr view", "find . -name x -exec gh pr merge 12 \\;",
                    "parallel ::: 'gh pr merge 12'"]:
        check(f"round 2 allow, Track 2 lead: {command!r}", sb.bash(command, env=lead2), "allow")

    # gh co is gh's default alias, which gh's config file can redefine.
    for label, env, stop in (("worker", worker, None), ("Track 2 lead", lead2, LEAD_STOP)):
        check(f"round 2 deny, {label}: gh co 12", sb.bash("gh co 12", env=env), "deny", gh_unchecked,
              stop=stop)

    # The array-element allow holds only where a shell array is set; the track's name
    # attached to an option's value is denied as the separate form is.
    for command in ["env a[$X]=2 claude", "sudo a[$X]=1 claude", "export a[$X]=1",
                    "a[$X]=2 claude", "tmux new -eCLAUDE_MERGE_TRACK=2 claude",
                    "docker run -eCLAUDE_MERGE_TRACK=2 img"]:
        check(f"round 2 deny, worker: {command!r}", sb.bash(command, env=worker), "deny",
              "setting CLAUDE_MERGE_TRACK")
    for command in ["declare a[$i]=1", "local m[$k]=x"]:
        check(f"round 2 allow: {command!r}", sb.bash(command, env=worker), "allow")

    # --- #145's round 3 at 7a58648 ------------------------------------------------
    # bash 5.3's ${ cmd; } and ${| cmd; } run commands, in a word or an expanded body.
    for command in ["echo ${ gh pr merge 12; }", "x=${| gh pr merge 12; }",
                    "echo \"${ gh pr merge 12; }\""]:
        check(f"round 3 deny: {command!r}", sb.bash(command, env=worker), "deny", MERGE)
    for command in ["cat <<EOF\n${ gh pr merge 12; }\nEOF", "cat <<EOF\n${| gh pr merge 12; }\nEOF"]:
        check(f"round 3 deny: {command!r}", sb.bash(command, env=worker), "deny", expanded)
    for command in ["echo ${HOME} ${HOME:-x}", "cat <<EOF\n${HOME} ${HOME:-x}\nEOF",
                    "echo '${ gh pr merge 12; }'"]:
        check(f"round 3 allow: {command!r}", sb.bash(command, env=worker), "allow")
    # parallel -a adds a source the command does not show.
    for command in ["parallel -a args.txt ::: 'gh pr merge 12'",
                    "parallel --arg-file=args.txt ::: 'gh pr merge 12'",
                    "parallel -ka args.txt ::: 'gh pr merge 12'"]:
        check(f"round 3 deny, Track 2 lead: {command!r}", sb.bash(command, env=lead2), "deny",
              "run by xargs, parallel or find", stop=LEAD_STOP)

    # --- #145's round 3b at adb6eba: -Ia is -I with the value a, so the command
    # starts at the next word, a wrapper here, as getopt reads the bundle.
    for command, frag in [
        ("echo 1 | xargs -Ia timeout 5 sh -c 'gh pr merge 12 --admin'", "with --admin"),
        ("echo 1 | xargs -Ia timeout 5 sh -c 'gh pr merge 12'", "run by xargs, parallel or find"),
        ("parallel -Ia timeout 5 sh -c 'gh pr merge 12 --admin' ::: x", "with --admin"),
        ("echo 1 | xargs -Ia timeout 5 sh -c 'git push origin main'", "default branch"),
        ("parallel -Ia timeout 5 sh -c 'git push origin main' ::: x", "default branch"),
    ]:
        check(f"round 3b deny, worker: {command!r}", sb.bash(command, env=worker), "deny")
        check(f"round 3b deny, Track 2 lead: {command!r}", sb.bash(command, env=lead2),
              "deny", frag, stop=None if frag == "default branch" else LEAD_STOP)
    for command in ["parallel -0a args.txt ::: 'gh pr merge 12'", "parallel -ka args.txt ::: 'gh pr merge 12'"]:
        check(f"round 3b deny, Track 2 lead: {command!r}", sb.bash(command, env=lead2), "deny",
              "run by xargs, parallel or find", stop=LEAD_STOP)
    check("round 3b allow: xargs -0n 1 gh pr view", sb.bash("echo 1 | xargs -0n 1 gh pr view", env=worker),
          "allow")

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
    source = re.sub(r"(def check_command\([^)]*\):\n)",
                    r"\1    raise RuntimeError('planted')\n", HOOK.read_text(), count=1)
    (planted / "claude_policy_hook.py").write_text(source)
    check("KTD5 deny: a crash in the hook", sb.bash("gh pr view 12",
          hook=planted / "claude_policy_hook.py"), "deny", "the hook failed")

    # --- Residuals: documented, pinned as still allowed ----------------------------------
    for name, command in [
        ("curl", "curl -X PUT https://api.github.com/repos/o/r/pulls/1/merge"),
        ("a pipe into sh", "echo 'gh pr merge 12' | sh"),
        ("a make target", "make push"),
        ("a program named by a variable", "G=gh; $G pr merge 12"),
        ("a shell function", "m() { \"$@\"; }; m gh pr merge 12"),
        ("a heredoc in a substitution eval runs", "eval \"$(cat <<'EOF'\ngh pr merge 12\nEOF\n)\""),
        ("a program that runs its arguments", "strace -f gh pr merge 12"),
        ("a program that runs a command it is given", "fd -x gh pr merge 12"),
        ("a command given as a string", "trap 'gh pr merge 12' EXIT"),
        ("a substitution run while expanding a value", "x='$(gh pr merge 12)'; echo \"${x@P}\""),
        ("editing the clone's config file",
         "printf '[agentpolicy]\\n\\tallowDefaultPush = true\\n' >> .git/config"),
    ]:
        check(f"residual: {name}", sb.bash(command, cwd=sb.trunk), "allow", on_fail=RESIDUAL_DOC)
    # A redirect the parser does not read as one leaves its fd among the words (#114).
    check("residual: a named fd redirect", sb.bash("git push {fd}>/dev/null origin HEAD:trunk", cwd=sb.feat),
          "allow", on_fail=RESIDUAL_DOC)

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
