---
name: start-team
description: Start an agent team for this project in one step. Checks the prerequisites, adds the adoption line, and starts <project>-lead in the lead role, or makes this session the lead where no session can be started. Use when the operator asks to start, set up or run an agent team.
---

# Start an agent team

You are setting up the Agent Team Workflow for the project this session is in: <https://github.com/rmorison/engineering-standards/blob/main/process/agent-team-workflow.md>. Read its § 8 "Starting a team" and § 9 Prerequisites before you begin. They are the rules; this skill is the steps. Where they differ, the workflow wins.

Work through the steps in order. Never edit settings, install anything, commit, or push. Tell the operator what you did at the end (step 9), even if you stopped early.

## 1. The project

- **Main checkout:** the parent directory of the git common directory: `git rev-parse --path-format=absolute --git-common-dir`, or with a git older than 2.31, `realpath "$(git rev-parse --git-common-dir)"`. Use it, not this session's directory, which may be a worktree.
- **Project name:** `gh repo view --json name --jq .name` run in the main checkout, or else the main checkout's directory name. The lead is `<project>-lead`.
- **Lead record:** `<git common dir>/agent-team/lead.json`. It sits inside the git directory, so it is never tracked. If it exists, read it: it holds the board path, the route and the lead's address from an earlier run.

## 2. Is a lead already running?

Look for the lead in three places: the lead record's address, `claude agents --json --all` (when the `claude` CLI is on PATH), and ListAgents.

A session named `<project>-lead`, or at the record's address, counts as this project's lead when it runs in the main checkout or one of its worktrees. Then:

- **Live** (busy, idle or blocked): tell the operator its name, its state and how to reach it (`claude attach <id>`, or its address for SendMessage). Start nothing, and stop.
- **Exited:** name it, and go on. The new lead resumes from the board path in the record.
- **In the record but in no listing:** the lead may still be running where this session can't see it: a cloud session (route B), a session whose rename didn't take (route C), or any lead when `claude` isn't on this session's PATH. Ask the operator whether it is still running before starting another, and stop if it is.
- **Same name in another directory:** that is another project's session. Report the collision and stop. Names must be unique on the machine (§ 1).

## 3. Messaging

The team needs sessions that can message each other (§ 9). Check that SendMessage and ListAgents are available: loaded, or listed as deferred tools that ToolSearch can load. If either is missing, tell the operator so, quote § 9, and stop.

## 4. Prerequisites

Check each § 9 prerequisite without changing anything, and grade what you find:

- **Both hooks** (warn if missing). `~/.claude/settings.json` registers `PreToolUse` commands running `claude_leak_hook.py` and `claude_policy_hook.py`, each ending in `|| exit 2`. Both scripts exist, and `python3 ~/.claude/hooks/claude_policy_hook.py --whoami` exits 0. No settings file that applies here switches hooks off: `disableAllHooks` set to `true` in `~/.claude/settings.json`, in `.claude/settings.json` or `.claude/settings.local.json` under the main checkout or this session's own directory, or in a managed settings file where one exists, fails this check, and so does `allowManagedHooksOnly` set to `true` in a managed settings file, since user hooks then don't run. So does any of those files that exists but can't be read. Record whether this passed; step 7 needs it.
- **Plan review, code review and a learnings step** (warn if missing). `claude plugin list` shows `compound-engineering`, or the operator names their equivalents.
- **A way to wake the lead on a schedule** (warn if missing). A tool such as CronCreate, ScheduleWakeup or send_later is available. Without one, the operator prompts the lead with "status?".
- **One posting account** (warn if missing). `gh auth status` succeeds.

Messaging and starting sessions are steps 3 and 7.

## 5. The adoption line

Look in the main checkout's `CLAUDE.md` and `AGENTS.md`, and in a file either one imports, for a line linking `process/agent-team-workflow.md`, at any ref. If one has it, change nothing and note which file, and the URL it links: that URL, pin included, is the **workflow URL**.

Otherwise add the adoption line, copied exactly from the fenced block under § 8 "To adopt by hand", step 2, to `CLAUDE.md`, or to `AGENTS.md` if only that exists. Create `CLAUDE.md` if neither exists. Don't commit: tell the operator the file changed and needs committing in their usual way. The workflow URL is then the one in the line you added.

## 6. The board

The lead keeps its board, log and handoffs in a private place outside the repository (§ 8 step 4). Use the board path in the lead record if there is one. Otherwise ask the operator, offering `~/.claude/agent-team/<project>/` as the default, and wait for the answer. Whichever path you use, resolve it to an absolute path, with no `~` left in it, and create the directory if it doesn't exist (`mkdir -p`).

## 7. Start the lead

**Permission mode.** This one rule decides the mode of every session the team starts; the lead receives the result in its opening prompt and passes it to its workers. The mode is `auto` or `acceptEdits` only when all three hold: this session's context states its permission mode explicitly (for example, a notice that auto mode is active), that mode is `auto` or `acceptEdits`, and the hooks passed in step 4 on this machine. In every other case, and always for Route B, whose machine step 4 didn't check, it is `default`, and the operator answers the session's prompts after `claude attach <id>`. Never `bypassPermissions`.

**The opening prompt.** Fill in this text:

```text
You are <project>-lead, the lead for <project>. The Agent Team Workflow is at <workflow URL>; read it in full and act as the lead it describes. Your board, log and handoffs live in <board path>; resume from them if they exist. Permission mode for you and the sessions you start: <mode>. Prerequisites start-team found missing: <list, or none>. Check that you are reachable as <project>-lead, then follow the Starting a team steps: read the open issues and pull requests, and propose a first sprint. Stop for the operator's sign-off before starting any worker.
```

Try the routes in order, and take the first that works.

**Route A, the Claude Code CLI.** Use this when `claude` is on PATH and this session can run shell commands. Write the filled opening prompt to `<board path>/opening-prompt.md`. Check it was written and isn't empty (`test -s`); if it wasn't, Route A didn't work. Then run this from the main checkout. Leave out `--permission-mode` when the mode is `default`:

```bash
claude --bg --agent agent-team:lead -n <project>-lead --permission-mode <mode> "$(cat "<board path>/opening-prompt.md")"
```

Never paste the prompt into the command line itself. The command prints the session's id. Any failure means Route A didn't work: a non-zero exit, a refusal such as "Workspace not trusted" in a directory that never accepted the trust prompt, or a lead that `claude agents --json` doesn't list within a minute. Tell the operator what happened, stop any session it did start (`claude stop <id>`), and go to Route B. Don't retry.

The lead is up once `claude agents --json` lists it under its name. If it runs in `auto` or `acceptEdits`, also send it a SendMessage asking for its role and check the reply. In default mode it may be `blocked` on its first prompt, which is expected. Leave the role check to the operator once they attach.

**Route B, a host session tool.** Use this when a session-start tool such as `create_session` is available (Claude Code on the web, Remote Control). Start a session titled `<project>-lead` in the same environment and repository. Set its permission mode explicitly to `default`, by the rule above, rather than letting it inherit this session's. Fill the opening prompt again with `default` as its mode, even if Route A was tried with another. Before starting it, tell the operator what a cloud lead can't do (below) and ask whether to go ahead: the workflow stops a team whose sessions can't message each other, and a cloud lead's messaging is one-way, so this is their call. If they decline, go to Route C only if this session runs on the operator's own machine; otherwise stop, since a cloud session as lead has the same one-way messaging. Its prompt is:

```text
Take on the lead role: read agents/lead.md from the agent-team plugin if it is installed in your session, or else from https://github.com/rmorison/engineering-standards/blob/main/plugins/agent-team/agents/lead.md. The operator chose a cloud lead knowing its messages can't reach local sessions: rely on the scheduled GitHub check (§ 3) instead of pings, as the workflow's Starting a team step 2 allows, and say so. Then: <opening prompt>
```

The lead is up once ListAgents or the host's session list shows it. Record the address ListAgents gives it, since a title can take a while to become its listed name.

Tell the operator what a cloud lead can't do. It receives messages, but it can't send them back to local sessions, so its pings and quiet-mode messages never arrive; the operator reads it in the host's session view. It may also have no session-start tool of its own, in which case it gives the operator each worker's handoff and start command. Workers in the same cloud have the same one-way messaging, so their pings to the lead are lost too; the lead falls back to its scheduled GitHub check (§ 3).

**Route C, this session becomes the lead.** Use this only when this session runs on the operator's own machine, and then when neither route works or the operator declined Route B. A cloud session that gets here stops instead, since it would be a one-way lead the operator never chose. First check this session's own permission mode. If its context doesn't state the mode, or the mode is anything other than the one the rule above gives, tell the operator and ask them to set this session to that mode (Shift+Tab, or restart the session) and confirm it before going on; if they don't, stop. Then say plainly that this session is now `<project>-lead` and that its role was not loaded at start, so it holds only by what follows. Read the lead role at the URL in Route B and act as it from here on, taking the filled opening prompt as your own, with its permission mode for the sessions you start. Rename this session to `<project>-lead` if you can. If this session has already done a lot of other work, say that a fresh session would make a better lead. Write the filled opening prompt to `<board path>/opening-prompt.md` as Route A does, and give the operator the Route A command, so they can start a role-loaded lead later from a terminal in the main checkout.

## 8. Record the lead

Write `<git common dir>/agent-team/lead.json` as one JSON object with these keys: `project`, `route` (`A`, `B` or `C`), `name`, `address`, `sessionId` (or `null`), `board`, `workflowUrl`, `permissionMode` and `startedAt` (from `date -u`). The next run of this skill reads it in step 2.

## 9. Tell the operator

In a few lines:

- where the lead is (name, route, state), and how to reach it: `claude attach <id>` for Route A, the session link for Route B, this session for Route C;
- what start-team changed (the adoption line, the record) and what it left for the operator: committing the line, naming the branch the main checkout is on so it isn't committed into an unrelated pull request, and any prerequisites marked missing;
- if the hooks failed step 4, say plainly what nothing guards until they are installed: a merge, a change to repository settings, a push to the default branch, and a private value posted in GitHub text. Every session the team starts runs in the default mode meanwhile, and the operator's own approval of each prompt is then the only guard;
- what happens next, from § 8 "Starting a team": the lead proposes a first sprint and stops for their sign-off. If it can't start sessions, they start each worker by hand from the handoff it writes. Quiet mode is on: the lead messages them only for a pull request ready to merge, a decision, a blocker or a leak.
