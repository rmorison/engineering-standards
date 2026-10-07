# Quickstart

How to adopt these standards in a project: a path for a [new project](#new-project) and one for an [existing project](#existing-project). Each step says what to do, gives a snippet to copy where there is something to type, and links to the section that explains it. Steps marked **Optional** can be skipped. Steps marked **You do this** write outside the project's repository, to your account or your machine, so you run them yourself rather than handing them to an agent.

Each path opens with a prompt you can paste into a Claude Code session in your project, to have the agent carry the path out. It does what lies inside the repository, hands you the **You do this** steps, tells you what it changed, and asks before it commits.

Run the snippets from your project's root unless a step says otherwise. A snippet marked as a copy of a standard is kept identical to its source by `node scripts/check-docs.mjs`, so the two cannot drift apart. The snippets were run under `sh` and `bash` on Linux on 2026-10-07. They were not run under zsh or on macOS.

## Before You Start

Clone this repository outside your project. The snippets below read it from `~/engineering-standards`; if you keep it somewhere else, change that path in them.

```bash
git clone https://github.com/rmorison/engineering-standards.git ~/engineering-standards
```

## New Project

**To have an agent do it,** paste this into a Claude Code session in the project:

```text
Set up this project with the engineering standards. Follow the New Project path in
~/engineering-standards/QUICKSTART.md one step at a time, reading each step's
linked section before you act on it.

- Work only inside this project's repository. A step marked "You do this" writes
  outside it: don't run it. Give me its snippets, then wait until I say it's done.
- Ask me before doing a step marked "Optional".
- After each step, tell me what you created or changed, file by file.
- Before any commit, show me the files and the message, and wait for my go.
```

### 1. Copy the Starter Kit

Copy the Claude Code configuration and the project instruction file into the project root. The snippet is for a project with no `.claude/` yet; otherwise merge, as in [existing-project step 5](#5-merge-in-the-starter-kit). Then fill in every placeholder in `CLAUDE.md`: [Project Templates](./README.md#project-templates).

```bash
cp -R ~/engineering-standards/templates/.claude . && cp ~/engineering-standards/templates/CLAUDE.md .
```

**Optional:** skeletons of `SECURITY.md`, `CONTRIBUTING.md` and the issue and pull request templates: [Repository baseline files](./templates/README.md#repository-baseline-files).

```bash
cp ~/engineering-standards/templates/SECURITY.md ~/engineering-standards/templates/CONTRIBUTING.md . && cp -R ~/engineering-standards/templates/.github .
```

### 2. Create the Docs Tree

Product specs go in `docs/product/` and architecture decisions in `docs/engineering/adr/`. Write a strategic vision in `docs/product/strategic-vision.md`, and add an ADR each time you make an architecture decision: [Documentation Standards](./process/documentation-standards.md#directory-structure).

```bash
mkdir -p docs/product docs/engineering/adr
```

### 3. Add the Leak Gate to CI

Copy the gate's rules, wrapper, installer, workflow and tests: [Adopting the Gate](./process/repository-standards.md#adopting-the-gate). The copied workflow's test step also runs this repository's own tests of the agent-session hooks, which read this repository's standards and fail anywhere else, so the snippet drops those two lines from the copy.

```bash
es=~/engineering-standards && mkdir -p scripts .github/workflows &&
cp "$es/.gitleaks.toml" . &&
cp "$es/scripts/gitleaks-report.tmpl" "$es/scripts/leak-gate.sh" "$es/scripts/install-gitleaks.sh" \
  "$es/scripts/test-leak-gate.sh" "$es/scripts/test-install-gitleaks.sh" scripts/ &&
grep -v 'python3 scripts/test_claude_' "$es/.github/workflows/leaks.yml" > leaks.yml.tmp &&
mv leaks.yml.tmp .github/workflows/leaks.yml
```

Give `.gitleaks.toml`, `.gitleaksignore`, `.gitattributes`, `scripts/install-gitleaks.sh` and the workflow required review, as the section explains.

### 4. Set Up the Leak Gate on Your Machine

**You do this,** on each machine that commits to the project. Install the pinned gitleaks:

<!-- copy-of: process/repository-standards.md | sh scripts/install-gitleaks.sh -->
```bash
sh scripts/install-gitleaks.sh
```

It prints where it installed gitleaks. If it says that directory is not first on `PATH`, add the directory to `PATH` in your shell profile, or set `GITLEAKS` to the path it printed: [Adopting the Gate](./process/repository-standards.md#adopting-the-gate).

If you hold private values, such as private repository names or internal hostnames, declare your value list once per machine. A public repository requires it: [Private Values](./process/repository-standards.md#private-values).

<!-- copy-of: process/repository-standards.md | git config --global leakgate.values -->
```bash
git config --global leakgate.values ~/.config/leakgate/values
```

Then install the commit-time hook and the push-time hook: [Running It Locally](./process/repository-standards.md#running-it-locally). If the project uses the pre-commit framework, use its entries from that section instead.

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

**Optional:** if AI agents work on the project. **You do this,** once per OS account. Two Claude Code hooks: one stops agent sessions from posting your private values to GitHub, and one keeps merges, repository settings and pushes to the default branch with you. They apply to every Claude Code session on the account, in every repository: [Guarding Agent Sessions](./process/repository-standards.md#guarding-agent-sessions) and [Guarding Repository Authority](./process/repository-standards.md#guarding-repository-authority).

Copy them from the standards clone on `main`, never from your project or a pull request's branch:

```bash
cd ~/engineering-standards && git switch main && git pull --ff-only
```

<!-- copy-of: process/repository-standards.md | claude_policy_hook.py ~/.claude/hooks/ -->
```bash
mkdir -p ~/.claude/hooks && install -m 755 scripts/claude_leak_hook.py scripts/claude_policy_hook.py ~/.claude/hooks/
```

Then `cd` back to your project, and make the `hooks` entry in `~/.claude/settings.json` hold this, merged with any hooks already there:

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

The leak hook reads the value list from step 4. Without one, it only stops sessions from switching the git-side gate off. A project whose agents push straight to its default branch needs [the exemption](./process/repository-standards.md#guarding-repository-authority).

### 6. Write Pull Requests with At a Glance

Branch from an issue, write conventional commits, and open every pull request description with At a glance: [Git Branching Strategy](./process/git-branching-strategy.md#pr-description). The description template:

<!-- copy-of: process/git-branching-strategy.md | **Spec drift.** What changed -->
```markdown
## At a glance

**Problem.** What was wrong or missing, for a user (125 words or fewer)

**Spec drift.** What changed after the issue (or plan), why, and who decided (50-100 words), or: None.

**Solution.** How this change solves it, in plain language (125 words or fewer)

## What
Brief description of the change

## Why
The technical reason for the change, for contributors (the user-facing problem is in At a glance); link the issue or spec

## How
Implementation approach (reference design doc if applicable)

## Testing
How this was tested (unit tests, manual testing, edge cases)

## Related
<!-- Keep one line: the first closes the issue on merge, the second leaves it open -->
- Closes #123
- Part of #123
- Spec: docs/engineering/designs/feature-name.md (if applicable)
```

### 7. Follow the Feature Workflow

Build features through the [Feature Development Workflow](./process/feature-development-workflow.md): intent, spec, plan, execute, validate.

**Optional:** if you adopt compound-engineering, [`process/compound-engineering-integration.md`](./process/compound-engineering-integration.md) gives its paths (`docs/plans/`, `docs/solutions/`, `docs/ideation/`) and its review discipline.

### 8. Run an Agent Team

**Optional:** one human directing several AI agent sessions, with a lead that coordinates them: [Agent Team Workflow](./process/agent-team-workflow.md). Step 5's hooks are a prerequisite; the rest are in [Prerequisites](./process/agent-team-workflow.md#9-prerequisites).

Add [the adoption line](./process/agent-team-workflow.md#8-adopting-and-declining) to the project's `CLAUDE.md` or `AGENTS.md`:

<!-- copy-of: process/agent-team-workflow.md | the operator starts one lead session -->
```markdown
This project runs an agent team (see [Agent Team Workflow](https://github.com/rmorison/engineering-standards/blob/main/process/agent-team-workflow.md)): the operator starts one lead session with that document, and the lead starts each worker with a handoff.
```

Then start a new session and give it the opening prompt, filling in the placeholders: [Starting a team](./process/agent-team-workflow.md#starting-a-team).

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

Adopt one step at a time, in this order. Each step stands alone, says what it changes, and says how to back it out. Don't retrofit everything at once.

**To have an agent do it,** paste this into a Claude Code session in the project:

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
```

### 1. Start with Pull Requests

Open every pull request description with At a glance, using the template in [new-project step 6](#6-write-pull-requests-with-at-a-glance). It changes no files. To back out, stop.

### 2. Guard Agent Sessions

**Optional:** if AI agents work on the project. **You do this.** Declare your value list first, if you hold private values, with the `git config --global` snippet in [new-project step 4](#4-set-up-the-leak-gate-on-your-machine). Then install the hooks and the settings entry from [new-project step 5](#5-install-the-agent-session-hooks).

The hooks write only to your account's `~/.claude/`, but they apply to every Claude Code session on the account, in every repository. If the project's agents push straight to its default branch, set up [the exemption](./process/repository-standards.md#guarding-repository-authority) first. To back out, remove the hook entries from `~/.claude/settings.json`.

### 3. Add the Leak Gate to CI

Copy the files with the snippet in [new-project step 3](#3-add-the-leak-gate-to-ci). Install gitleaks and put it on `PATH` as in [new-project step 4](#4-set-up-the-leak-gate-on-your-machine); **you do this** part. Then scan the existing history once, before the first push. CI scans the whole tree, and this also finds what earlier commits already published:

<!-- copy-of-line: process/repository-standards.md | leak-gate.sh history -->
```bash
sh scripts/leak-gate.sh history
```

It prints each finding as file, line and rule, never the matched text. Fix what it finds: [When a Leak Is Found](./process/repository-standards.md#when-a-leak-is-found). The step adds the copied files; to back out, delete them.

### 4. Add the Leak Gate Hooks

**You do this,** on each machine that commits to the project. Install the commit-time and push-time hooks with the snippets in [new-project step 4](#4-set-up-the-leak-gate-on-your-machine), or the pre-commit framework entries from [Running It Locally](./process/repository-standards.md#running-it-locally) if the project already uses that framework. They change only the clone's hooks, and refuse a commit or a push that would publish a leak. To back out, delete the hook files or the entries.

### 5. Merge in the Starter Kit

Merge the starter kit into the project's own `.claude/` and `CLAUDE.md` rather than overwriting them: [Project Templates](./README.md#project-templates). Compare first:

```bash
diff -ru ~/engineering-standards/templates/.claude .claude; diff -u ~/engineering-standards/templates/CLAUDE.md CLAUDE.md
```

To back out, revert the commit.

### 6. Write Docs Going Forward

Record new decisions as ADRs and write specs for the next features, without retrofitting old ones: [Documentation Standards](./process/documentation-standards.md). Update the standards based on what works and what doesn't. There is nothing to back out.

### 7. Run an Agent Team

**Optional.** As in [new-project step 8](#8-run-an-agent-team). To stop, remove the adoption line and archive the lead.
