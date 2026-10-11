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
- **Adoption line:** look in the main checkout's `CLAUDE.md` and `AGENTS.md`, and in a file either one imports, for a line linking `process/agent-team-workflow.md`, at any ref. If one has it, note which file, and the URL it links: that URL, pin included, is the **workflow URL**. If none has it, step 5 adds the line, and the workflow URL is the one in that line.
- **Role URLs:** a workflow URL of the form `https://github.com/<owner>/<repo>/blob/<ref>/process/agent-team-workflow.md` gives each role's URL by swapping the path for `plugins/agent-team/agents/lead.md` or `plugins/agent-team/agents/worker.md`, same owner, repository and ref, so the roles match the workflow the project pinned. Check each one exists there: `gh api "repos/<owner>/<repo>/contents/plugins/agent-team/agents/<role>.md?ref=<ref>" --silent`. If it fails with `HTTP 404`, the pin has no such role file (it predates the plugin, or the ref doesn't exist): use the role's URL at `main` of `rmorison/engineering-standards` instead, and tell the operator in step 9 that the role may be newer than their pin, so where the two differ, the workflow they pinned wins. If it fails any other way (`gh` signed out, no network), keep the pinned URL and tell the operator the pin couldn't be checked. A workflow URL of any other form gets both roles at `main`.

## 2. Is a lead already running?

Look for the lead in three places: the lead record's address, `claude agents --json --all` (when the `claude` CLI is on PATH), and ListAgents.

A session named `<project>-lead`, or at the record's address, counts as this project's lead when it runs in the main checkout or one of its worktrees. Then:

- **Live** (busy, idle or blocked): tell the operator its name, its state and how to reach it (`claude attach <id>`, or its address for SendMessage). Start nothing, and stop.
- **Exited:** name it, and go on. The new lead resumes from the board path in the record.
- **In the record but in no listing:** the lead may still be running where this session can't see it: a cloud session (route B), a session whose rename didn't take (route C), or any lead when `claude` isn't on this session's PATH. Ask the operator whether it is still running before starting another, and stop if it is.
- **Same name in another directory:** that is another project's session. Report the collision and stop. Names must be unique on the machine (§ 1).

**No lead record.** A lead started by hand, from the workflow document, writes no record, and may run under another name or be offline. So when there is no record:

- **No adoption line** (step 1): this is the project's first team. Go on without asking.
- **An adoption line:** the project may already run a lead. List the sessions that could be one: `claude agents --json` (running sessions only) whose `cwd` is the main checkout or one of its worktrees (`git worktree list`), whatever their name, leaving out this session; and ListAgents names ending in `-lead` or containing the project name. Ask the operator whether a lead is already running for this project, naming those sessions, and wait for the answer. If one is, tell them how to reach it, start nothing, and stop. If not, go on.

## 3. Messaging

The team needs sessions that can message each other (§ 9). Check that SendMessage and ListAgents are available: loaded, or listed as deferred tools that ToolSearch can load. If either is missing, tell the operator so, quote § 9, and stop.

## 4. Prerequisites

Check each § 9 prerequisite without changing anything, and grade what you find:

- **Both hooks** (warn if missing). `~/.claude/settings.json` registers `PreToolUse` commands running `claude_leak_hook.py` and `claude_policy_hook.py`, each ending in `|| exit 2`: both under the `Bash` matcher, and the policy hook under an `mcp__.*` matcher too. The guardrail check's canaries later show the `Bash` registration fires; only this step checks the `mcp__.*` one. Both scripts exist, and `python3 ~/.claude/hooks/claude_policy_hook.py --whoami` exits 0. No settings file that applies here switches hooks off: `disableAllHooks` set to `true` in `~/.claude/settings.json`, in `.claude/settings.json` or `.claude/settings.local.json` under the main checkout or this session's own directory, or in a managed settings file where one exists, fails this check, and so does `allowManagedHooksOnly` set to `true` in a managed settings file, since user hooks then don't run. So does any of those files that exists but can't be read. Record whether this passed; step 7 needs it.
- **Plan review, code review and a learnings step** (warn if missing). `claude plugin list` shows `compound-engineering`, or the operator names their equivalents.
- **A way to wake the lead on a schedule** (warn if missing). A tool such as CronCreate, ScheduleWakeup or send_later is available. Without one, the operator prompts the lead with "status?".
- **One posting account** (warn if missing). `gh auth status` succeeds.
- **A private-value list** (warn if `none` or `broken`). Run the value-list command in the workflow's § 4 "The guardrail check", step 3, exactly as written: it reports only whether a list is declared and its file is present, and never opens the list. `none`: the leak hook still blocks the gate escapes but checks no private values in what the team posts to GitHub; the operator declares a list as [the leak hook's section](https://github.com/rmorison/engineering-standards/blob/main/process/repository-standards.md#guarding-agent-sessions) says, or sets `none` on purpose. `broken`: the leak hook will deny every command that posts to GitHub until the list is fixed. Neither changes the mode in step 7.
- **The plugin matches the pin** (warn if not). Route A and the lead's command-line workers load their roles from the installed plugin, not from the role URLs. Compare its version, `version` of the `agent-team@…` entries in `claude plugin list --json` (each one, if it is installed at more than one scope), with the version at the workflow URL's ref: `gh api -H "Accept: application/vnd.github.raw" "repos/<owner>/<repo>/contents/plugins/agent-team/.claude-plugin/plugin.json?ref=<ref>" --jq .version`. Skip this when the workflow URL isn't of the github.com form in step 1, when step 1 couldn't check the pin, or when the ref has no plugin. If they differ, warn that those roles come from the installed version, and that the pinned workflow wins where they differ. To match them, the operator adds the marketplace from a source at the pin and updates the plugin, which moves it down as well as up: `claude plugin marketplace add rmorison/engineering-standards@<branch-or-tag>`, since `@` takes a branch or tag and not a commit; for a commit pin, a local clone checked out at it, `claude plugin marketplace add <path>`. Then `claude plugin update agent-team@engineering-standards` (observed on Claude Code 2.1.296).

Messaging and starting sessions are steps 3 and 7.

## 5. The adoption line

If step 1 found the adoption line, change nothing.

Otherwise add the adoption line, copied exactly from the fenced block under § 8 "To adopt by hand", step 2, to `CLAUDE.md`, or to `AGENTS.md` if only that exists. Create `CLAUDE.md` if neither exists. Don't commit: tell the operator the file changed and needs committing in their usual way. The workflow URL is then the one in the line you added, and both role URLs are at `main`.

## 6. The board

The lead keeps its board, log and handoffs in a private place outside the repository (§ 8 step 4). Use the board path in the lead record if there is one. Otherwise ask the operator, offering `~/.claude/agent-team/<project>/` as the default, and wait for the answer. Whichever path you use, resolve it to an absolute path, with no `~` left in it, and create the directory if it doesn't exist (`mkdir -p`).

## 7. Start the lead

**Permission mode.** This one rule decides the mode of every session the team starts. The lead receives the result in its opening prompt and passes it to its workers, and no session gets more.

- **The ceiling.** The mode is `auto` or `acceptEdits` only when all four hold: this session's context states its permission mode explicitly (for example, a notice that auto mode is active); that mode is `auto` or `acceptEdits`; the hooks passed in step 4 on this machine; and the operator hasn't said the last lead's guardrail check failed. Otherwise it is `default`. Never `bypassPermissions`.
- **Where the session lands, not the route, decides the rest.** A session on the operator's own machine, by Route A or by a host session tool that starts sessions there, may get the ceiling. It keeps that mode only if it passes the workflow's guardrail check (§ 4 "The guardrail check") as its first step, which shows its own hooks fire. A cloud session always gets `default`: step 4 never checked its machine, and its messages can't come back.
- In `default`, the operator answers the session's prompts in the app, or for Route A after `claude attach <id>` if it isn't there.

**The opening prompt.** Fill in this text:

```text
You are <project>-lead, the lead for <project>. The Agent Team Workflow is at <workflow URL>; read it in full and act as the lead it describes. Your board, log and handoffs live in <board path>; resume from them if they exist. The worker role for the sessions you start is at <worker role URL>. Permission mode for you and the sessions you start: <mode>. Prerequisites start-team found missing: <list, or none>. Unless this prompt says you run in the cloud and `get_session` agrees, first run the guardrail check in the workflow's § 4, whatever your mode, and give its result in your first message. If it fails, tell the operator which part failed; then stop, unless you run in default and only a canary failed. Check that you are reachable as <project>-lead, then follow the Starting a team steps: read the open issues and pull requests, and propose a first sprint. Stop for the operator's sign-off before starting any worker.
```

Try the routes in order, and take the first that works. The lead's routes put the CLI first, though its workers put the host session tool first (§ 1). The CLI sets the lead's mode exactly, `auto` included, while a host session tool can't pass `auto` from a session the host records as `default`. A CLI lead started as below appears in the operator's app too, and the operator can always reach it with `claude attach <id>`.

**Route A, the Claude Code CLI.** Use this when `claude` is on PATH and this session can run shell commands. Write the filled opening prompt to `<board path>/opening-prompt.md`. Check it was written and isn't empty (`test -s`); if it wasn't, Route A didn't work. Then run this from the main checkout. Always pass `--permission-mode`, `default` included: without it, the session takes this machine's own `defaultMode`, which can be higher than the rule's mode.

```bash
claude --bg --agent agent-team:lead --name <project>-lead --remote-control <project>-lead --permission-mode <mode> "$(cat "<board path>/opening-prompt.md")"
```

`--name` sets the title the app shows, and `--remote-control` with the same name connects the session to Remote Control, so the lead appears in the operator's app with no further step. That was observed on Claude Code 2.1.296 ([#123](https://github.com/rmorison/engineering-standards/issues/123)); the Claude Code docs describe `--remote-control` for interactive sessions only. Always give the name after `--remote-control`: its value is optional, so without one the next word would be read as the name. Where Remote Control isn't available, the lead still starts and runs, but isn't in the app, and neither `claude agents` nor ListAgents shows the difference. Step 9 says what to tell the operator.

Never paste the prompt into the command line itself. The command prints the session's id. If it refuses with a message about Remote Control, stop any `<project>-lead` it did start (`claude stop <id>`), run it once more without `--remote-control <project>-lead`, and tell the operator the lead is in a terminal only. A later restart of that lead leaves the flag out too. Otherwise, any failure means Route A didn't work: a non-zero exit, a refusal such as "Workspace not trusted" in a directory that never accepted the trust prompt, or a lead that `claude agents --json` doesn't list within a minute. Tell the operator what happened, stop any session it did start (`claude stop <id>`), and go to Route B. Don't retry.

The lead is up once `claude agents --json` lists it under its name. If it runs in `auto` or `acceptEdits`, also send it a SendMessage asking for its role and its guardrail check result, and check the reply. Act on the lead's result by the table in the workflow's § 4 "The guardrail check" (the lead column). A lead above `default` with no result within five minutes counts as a fail. Where the table says to restart it, stop it with `claude stop <id>` and restart it as below. In default mode it may be `blocked` on its first prompt, which is expected. Leave the role check to the operator once they open it, in the app or after `claude attach <id>` if it isn't there, and ask them for the lead's guardrail result.

Restart a failed lead once, and only once, as follows. Fill the opening prompt again with `default` as its mode, rewrite `<board path>/opening-prompt.md` with it, set `permissionMode` to `default` in the lead record (step 8), and start the lead again by the same route with the mode set explicitly. This restart and the retry without Remote Control are the only exceptions to Route A's "Don't retry". If the restarted lead stops again, for any part, don't restart it again: tell the operator, and stop.

**Route B, a host session tool.** Use this when a session-start tool such as `create_session` is available (Claude Code on the web, Remote Control). Start a session titled `<project>-lead` in this project's repository. First find where it would land. The host's environment list gives each environment's kind: `bridge` is a machine connected by Remote Control, and `anthropic_cloud` is the cloud. `get_session` with no ID gives this session's own environment and kind.

- **On this machine:** this session's own environment, when its kind is `bridge`. It alone may get the rule's ceiling, since step 4 checked only this machine. Fill the opening prompt with the rule's mode. When that mode is `default`, set `permission_mode` to `default`. When it is `auto` or `acceptEdits`, leave `permission_mode` out. The host refuses a mode above its own record of this session's mode, and it records a session started from the app or by another session as `default`, whatever mode the session runs in. Left out, the new session runs under that machine's own `defaultMode`, and the guardrail check's mode check in the opening prompt catches a mode other than the rule's. Its prompt is the first one below.
- **Another machine:** an environment of kind `bridge` that isn't this session's own, such as another machine the operator names. Step 4 never checked it, so set `permission_mode` to `default` and fill the opening prompt with `default`. Its prompt is the first one below.
- **In the cloud:** set `permission_mode` to `default`, and fill the opening prompt with `default`, even if Route A was tried with another. Before starting it, tell the operator what a cloud lead can't do (below) and ask whether to go ahead. The workflow stops a team whose sessions can't message each other, and a cloud lead's messaging is one-way, so this is their call. If they decline, go to Route C only if this session runs on the operator's own machine; otherwise stop, since a cloud session as lead has the same one-way messaging. Its prompt is the second one below.

```text
Take on the lead role: read it at <lead role URL>, or if that can't be read, agents/lead.md from the agent-team plugin if it is installed in your session. Then: <opening prompt>
```

```text
Take on the lead role: read it at <lead role URL>, or if that can't be read, agents/lead.md from the agent-team plugin if it is installed in your session. The operator chose a cloud lead knowing its messages can't reach local sessions: rely on the scheduled GitHub check (§ 3) instead of pings, as the workflow's Starting a team step 2 allows, and say so. Then: <opening prompt>
```

The lead is up once ListAgents or the host's session list shows it, and the host shows it connected. A started session can stay pending and never connect: if it hasn't connected within five minutes, archive it, tell the operator, and go to Route C. Record the address ListAgents gives it, since a title can take a while to become its listed name. The lead reports its own guardrail check in its first message: read it in the host's session view, or ask the lead with SendMessage. Act on that result by the table in § 4 (the lead column). A lead above `default` with no result within five minutes counts as a fail. Where the table says to restart it, archive it and restart it as Route A says ("Restart a failed lead once").

Tell the operator what a cloud lead can't do. It receives messages, but it can't send them back to local sessions, so its pings and quiet-mode messages never arrive; the operator reads it in the host's session view. It may also have no session-start tool of its own, in which case it gives the operator each worker's handoff and start command. Workers in the same cloud have the same one-way messaging, so their pings to the lead are lost too; the lead falls back to its scheduled GitHub check (§ 3).

**Route C, this session becomes the lead.** Use this only when this session runs on the operator's own machine, and then when neither route works or the operator declined Route B. A cloud session that gets here stops instead, since it would be a one-way lead the operator never chose. First check this session's own permission mode. If its context doesn't state the mode, or the mode is anything other than the one the rule above gives, tell the operator and ask them to set this session to that mode (Shift+Tab, or restart the session) and confirm it before going on; if they don't, stop. Then say plainly that this session is now `<project>-lead` and that its role was not loaded at start, so it holds only by what follows. Read the lead role at the lead role URL (step 1) and act as it from here on, taking the opening prompt as your own, filled again with step 7's own result as its mode, so this session, the prompt and the prompt file agree on the mode for the sessions you start. Rename this session to `<project>-lead` if you can. If this session has already done a lot of other work, say that a fresh session would make a better lead. Write the filled opening prompt to `<board path>/opening-prompt.md` as Route A does, and give the operator the Route A command, so they can start a role-loaded lead later from a terminal in the main checkout.

## 8. Record the lead

Write `<git common dir>/agent-team/lead.json` as one JSON object with these keys: `project`, `route` (`A`, `B` or `C`), `name`, `address`, `sessionId` (or `null`), `board`, `workflowUrl`, `permissionMode` and `startedAt` (from `date -u`). The next run of this skill reads it in step 2.

## 9. Tell the operator

In a few lines:

- the lead's guardrail check result, if it has given one (a lead in `default` may still be waiting on its first prompt);
- where the lead is (name, route, state), and how to reach it: in the app as `<project>-lead` or by `claude attach <id>` for Route A, the session link for Route B, this session for Route C;
- for Route A, unless the retry dropped `--remote-control`, ask the operator to look for `<project>-lead` in their app. It is grouped under the repository when the folder has a GitHub remote. If it isn't there, Remote Control isn't available on this machine, and the lead runs in a terminal only: reach it with `claude attach <id>`, and once the cause is fixed, `/remote-control` in that session connects it. The [Remote Control docs](https://code.claude.com/docs/en/remote-control) give these causes:
  - not signed in through claude.ai, or signed in with an API key;
  - a Free plan: Remote Control needs Pro, Max, Team or Enterprise;
  - a sign-in still tied to an earlier Team or Enterprise organization (`/status` shows which; log out and in again);
  - Amazon Bedrock, Google Vertex or Microsoft Foundry, or a gateway set through `ANTHROPIC_BASE_URL`;
  - `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` or `DISABLE_GROWTHBOOK` set;
  - the `disableRemoteControl` setting;
  - an organization with Zero Data Retention or the HIPAA configuration, or a Team or Enterprise plan whose owner hasn't turned Remote Control on;
  - Trusted Devices required, on a device that isn't enrolled;
- what start-team changed (the adoption line, the record) and what it left for the operator: committing the line, naming the branch the main checkout is on so it isn't committed into an unrelated pull request, and any prerequisites marked missing. Give the value-list and plugin-version warnings from step 4 in their own words, and say where a role comes from `main` rather than the pin, or the pin couldn't be checked (step 1);
- if the hooks failed step 4, say plainly what nothing guards until they are installed: a merge, a change to repository settings, a push to the default branch, and a private value posted in GitHub text. Every session the team starts runs in the default mode meanwhile, and the operator's own approval of each prompt is then the only guard;
- what happens next, from § 8 "Starting a team": the lead proposes a first sprint and stops for their sign-off. If it can't start sessions, they start each worker by hand from the handoff it writes. Quiet mode is on: the lead messages them only for a pull request ready to merge, a decision, a blocker or a leak.
