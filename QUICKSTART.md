# Quickstart

Two paths: [new project](#new-project) and [existing project](#existing-project). Each opens with a prompt to paste into Claude Code, which carries the path out for you. Or follow the steps by hand: each one gives what to do, a snippet, and a link to the detail.

- **Optional** steps can be skipped.
- **You do this** steps write outside the project's repository, to your account or machine. An agent hands them to you rather than running them.

Run snippets from the project root unless a step says otherwise. Snippets copied from a standard are checked against it by `node scripts/check-docs.mjs`. All were run under `sh` and `bash` on Linux on 2026-10-07, not under zsh or on macOS.

## Prerequisites

- git, and the project on GitHub (the leak gate's CI runs on GitHub Actions).
- `curl`, `tar`, and `sha256sum` or `shasum`, for the gitleaks installer.
- [Claude Code](https://claude.com/claude-code), for the prompts and the agent-session hooks. The hooks need Python 3.10 or later.
- The [GitHub CLI](https://cli.github.com) (`gh`), for an agent team.
- The [compound-engineering plugin](https://github.com/EveryInc/compound-engineering-plugin) for Claude Code: optional for the standards, required for an agent team, whose workers' plan review, code review and learnings steps it provides (or equivalents): [Prerequisites](./process/agent-team-workflow.md#9-prerequisites).
- A clone of this repository outside your project. The snippets read it from `~/engineering-standards`; change that path if yours is elsewhere.

<!-- own -->
```bash
git clone https://github.com/rmorison/engineering-standards.git ~/engineering-standards
```

If you already have a clone, update it on `main`, since the snippets copy from whatever it has checked out:

<!-- own -->
```bash
(cd ~/engineering-standards && git switch main && git pull --ff-only)
```

## New Project

**With an agent:** paste this into a Claude Code session in the project.

<!-- own -->
```text
Set up this project with the engineering standards. Follow the New Project path in
~/engineering-standards/QUICKSTART.md one step at a time, reading each step's
linked section before you act on it.

- Work only inside this project's repository. A step marked "You do this" writes
  outside it: don't run it. Give me its snippets, then wait until I say it's done.
- Ask me before doing a step marked "Optional".
- After each step, tell me what you created or changed, file by file.
- Before any commit, show me the files and the message, and wait for my go.
- Don't push, open a pull request, or change repository settings unless I ask.
- Never add disableAllHooks, a broad permissions.allow entry, or anything else that
  loosens a hook or the leak gate. If the project already has one, point it out.
```

### 1. Copy the Starter Kit

Copy the Claude Code configuration and `CLAUDE.md`, then fill in `CLAUDE.md`'s placeholders: [Project Templates](./README.md#project-templates). If the project already has a `.claude/`, merge instead, as in [existing-project step 4](#4-merge-in-the-starter-kit).

<!-- own -->
```bash
cp -R ~/engineering-standards/templates/.claude . && cp ~/engineering-standards/templates/CLAUDE.md .
```

**Optional:** `SECURITY.md`, `CONTRIBUTING.md`, and issue and pull request templates: [Repository baseline files](./templates/README.md#repository-baseline-files).

<!-- own -->
```bash
cp ~/engineering-standards/templates/SECURITY.md ~/engineering-standards/templates/CONTRIBUTING.md . && cp -R ~/engineering-standards/templates/.github .
```

### 2. Create the Docs Tree

Specs go in `docs/product/`, ADRs in `docs/engineering/adr/`. Start with a strategic vision in `docs/product/strategic-vision.md`, and add an ADR for each architecture decision: [Documentation Standards](./process/documentation-standards.md#directory-structure).

<!-- own -->
```bash
mkdir -p docs/product docs/engineering/adr
```

### 3. Add the Leak Gate to CI

Copy the gate's files: [Adopting the Gate](./process/repository-standards.md#adopting-the-gate). The snippet leaves two lines out of `leaks.yml` that run this repository's own hook tests, which fail anywhere else (#109).

<!-- own -->
```bash
es=~/engineering-standards && mkdir -p scripts .github/workflows &&
cp "$es/.gitleaks.toml" . &&
cp "$es/scripts/gitleaks-report.tmpl" "$es/scripts/leak-gate.sh" "$es/scripts/install-gitleaks.sh" \
  "$es/scripts/test-leak-gate.sh" "$es/scripts/test-install-gitleaks.sh" scripts/ &&
grep -v 'python3 scripts/test_claude_' "$es/.github/workflows/leaks.yml" > leaks.yml.tmp &&
mv leaks.yml.tmp .github/workflows/leaks.yml
```

Name reviewers for the gate's files in a `CODEOWNERS` file, as the section explains. **You do this:** require that review in the repository's settings.

### 4. Set Up the Leak Gate on Your Machine

**You do this,** on each machine that commits. Install gitleaks:

<!-- copy-of: process/repository-standards.md | sh scripts/install-gitleaks.sh -->
```bash
sh scripts/install-gitleaks.sh
```

If it says its directory is not first on `PATH`, add it to `PATH` in your shell profile, or set `GITLEAKS` to the path it printed.

If you hold private values, such as private repository names or hostnames, declare your value list. A public repository requires one: [Private Values](./process/repository-standards.md#private-values).

<!-- copy-of: process/repository-standards.md | git config --global leakgate.values -->
```bash
git config --global leakgate.values ~/.config/leakgate/values
```

Install the commit-time and push-time hooks, or the pre-commit framework entries if the project uses that framework: [Running It Locally](./process/repository-standards.md#running-it-locally).

<!-- copy-of: process/repository-standards.md | hooks)/pre-commit" -->
```bash
hook="$(git rev-parse --git-path hooks)/pre-commit"
cat > "$hook" <<'EOF'
#!/bin/sh
[ -f scripts/leak-gate.sh ] && exec sh scripts/leak-gate.sh staged
if git cat-file -e HEAD:scripts/leak-gate.sh 2>/dev/null; then
  echo "leak-gate: HEAD has scripts/leak-gate.sh but the working tree does not; commit refused" >&2
  exit 1
fi
echo "leak-gate: this branch has no scripts/leak-gate.sh; check skipped" >&2
EOF
chmod +x "$hook"
```

<!-- copy-of: process/repository-standards.md | hooks)/pre-push" -->
```bash
hook="$(git rev-parse --git-path hooks)/pre-push"
cat > "$hook" <<'EOF'
#!/bin/sh
if [ -f scripts/leak-gate.sh ]; then
  grep -q 'pre-push)' scripts/leak-gate.sh && exec sh scripts/leak-gate.sh pre-push "$@"
  echo "leak-gate: this branch's scripts/leak-gate.sh has no pre-push mode; push not checked" >&2
  exit 0
fi
if git cat-file -e HEAD:scripts/leak-gate.sh 2>/dev/null; then
  echo "leak-gate: HEAD has scripts/leak-gate.sh but the working tree does not; push refused" >&2
  exit 1
fi
echo "leak-gate: this branch has no scripts/leak-gate.sh; push not checked" >&2
EOF
chmod +x "$hook"
```

### 5. Install the Agent-Session Hooks

**Optional,** if AI agents work on the project. **You do this,** once per OS account. One hook stops sessions posting your private values to GitHub. The other keeps merges, settings and pushes to the default branch with you. Both apply to every Claude Code session on the account: [Guarding Agent Sessions](./process/repository-standards.md#guarding-agent-sessions), [Guarding Repository Authority](./process/repository-standards.md#guarding-repository-authority).

Copy them from the clone on `main`, never from your project:

<!-- own -->
```bash
cd ~/engineering-standards && git switch main && git pull --ff-only
```

<!-- copy-of: process/repository-standards.md | claude_policy_hook.py ~/.claude/hooks/ -->
```bash
mkdir -p ~/.claude/hooks && install -m 755 scripts/claude_leak_hook.py scripts/claude_policy_hook.py ~/.claude/hooks/
```

`cd` back to your project, and merge this into `~/.claude/settings.json`:

<!-- copy-of: process/repository-standards.md | "matcher": "mcp__.*" -->
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/.claude/hooks/claude_leak_hook.py\" || exit 2"
          },
          {
            "type": "command",
            "command": "python3 \"$HOME/.claude/hooks/claude_policy_hook.py\" || exit 2"
          }
        ]
      },
      {
        "matcher": "mcp__.*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/.claude/hooks/claude_policy_hook.py\" || exit 2"
          }
        ]
      }
    ]
  }
}
```

Without step 4's value list, the leak hook only stops sessions switching the git-side gate off. If agents push straight to the default branch, set [the exemption](./process/repository-standards.md#guarding-repository-authority) yourself, outside any agent session.

### 6. Follow the Feature Workflow

Build features through the [Feature Development Workflow](./process/feature-development-workflow.md). **Optional:** with compound-engineering, see [`process/compound-engineering-integration.md`](./process/compound-engineering-integration.md) for its paths and review discipline.

### 7. Run an Agent Team

**Optional:** one human directing several agent sessions through a lead: [Agent Team Workflow](./process/agent-team-workflow.md). It needs step 5's hooks and the compound-engineering plugin (or equivalent review steps); the rest is in [Prerequisites](./process/agent-team-workflow.md#9-prerequisites).

Add [the adoption line](./process/agent-team-workflow.md#8-adopting-and-declining) to `CLAUDE.md` or `AGENTS.md`:

<!-- copy-of: process/agent-team-workflow.md | the operator starts one lead session -->
```markdown
This project runs an agent team (see [Agent Team Workflow](https://github.com/rmorison/engineering-standards/blob/main/process/agent-team-workflow.md)): the operator starts one lead session with that document, and the lead starts each worker with a handoff.
```

Then start a new session with the opening prompt, placeholders filled in: [Starting a team](./process/agent-team-workflow.md#starting-a-team).

<!-- copy-of: process/agent-team-workflow.md | You are <project>-lead -->
```text
You are <project>-lead, the lead for <project>. This project runs an agent team:
read the adoption line in CLAUDE.md (or AGENTS.md) and the Agent Team Workflow
it links to, and act as the lead it describes. Keep your board, log and handoffs in <private path>.
Check the prerequisites, read the open issues and pull requests, and propose a
first sprint. Stop for my sign-off before starting any worker.
```

To stop, remove the line and archive the lead.

## Existing Project

Adopt one step at a time, in this order. Each says how to back it out.

**With an agent:** paste this into a Claude Code session in the project.

<!-- own -->
```text
Adopt the engineering standards in this project. Follow the Existing Project path
in ~/engineering-standards/QUICKSTART.md, reading each step's linked section
before you act on it. Do one step, then stop and ask me before the next.

- Work only inside this project's repository. A step marked "You do this" writes
  outside it: don't run it. Give me its snippets, then wait until I say it's done.
- Ask me before doing a step marked "Optional".
- Never overwrite a file the project already has. Show me how it differs from the
  standards' copy and propose a merge.
- After each step, tell me what you created or changed, file by file.
- Before any commit, show me the files and the message, and wait for my go.
- Don't push, open a pull request, or change repository settings unless I ask.
- Never add disableAllHooks, a broad permissions.allow entry, or anything else that
  loosens a hook or the leak gate. If the project already has one, point it out.
```

### 1. Guard Agent Sessions

**Optional,** if AI agents work on the project. **You do this:** declare your value list ([new-project step 4](#4-set-up-the-leak-gate-on-your-machine)), then install the hooks and settings entry ([new-project step 5](#5-install-the-agent-session-hooks)). They write only to `~/.claude/`, but apply to every session on the account. If the project's agents push straight to its default branch, set [the exemption](./process/repository-standards.md#guarding-repository-authority) first, yourself, outside any agent session. To back out, remove the entries from `~/.claude/settings.json`.

### 2. Add the Leak Gate to CI

Copy the files ([new-project step 3](#3-add-the-leak-gate-to-ci)). **You do this:** install gitleaks and put it on `PATH` ([new-project step 4](#4-set-up-the-leak-gate-on-your-machine)). Then, before the first push, scan the history once. CI scans the whole tree, and this also finds what earlier commits already published:

<!-- copy-of-line: process/repository-standards.md | leak-gate.sh history -->
```bash
sh scripts/leak-gate.sh history
```

Findings print as file, line and rule: [When a Leak Is Found](./process/repository-standards.md#when-a-leak-is-found). To back out, delete the added files and revert any merges.

### 3. Add the Leak Gate Hooks

**You do this,** on each machine that commits: the hooks from [new-project step 4](#4-set-up-the-leak-gate-on-your-machine). The snippets replace an existing `pre-commit` or `pre-push` hook, so merge by hand if the clone has one. To back out, delete the hook files.

### 4. Merge in the Starter Kit

Merge the kit into the project's `.claude/` and `CLAUDE.md` rather than overwriting them ([Project Templates](./README.md#project-templates)). Compare first:

<!-- own -->
```bash
diff -ru ~/engineering-standards/templates/.claude .claude; diff -u ~/engineering-standards/templates/CLAUDE.md CLAUDE.md
```

To back out, revert the commit.

### 5. Write Docs Going Forward

Record new decisions as ADRs and write specs for the next features, without retrofitting: [Documentation Standards](./process/documentation-standards.md). Adjust the standards to what works.

### 6. Run an Agent Team

**Optional,** as in [new-project step 7](#7-run-an-agent-team), with the hooks and the compound-engineering plugin installed. To stop, remove the adoption line and archive the lead.

## Pull Requests

Branch from an issue, write conventional commits, and open every pull request description with At a glance, using the [description template](./process/git-branching-strategy.md#pr-description). The starter kit's optional [pull request template](./templates/.github/pull_request_template.md) holds it too.
