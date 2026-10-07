# agent-team

A Claude Code plugin that starts an agent team in one step, for projects that follow the [Agent Team Workflow](https://github.com/rmorison/engineering-standards/blob/main/process/agent-team-workflow.md). It holds:

- **`start-team`**, a skill. From a session in your project, run `/agent-team:start-team` or ask for an agent team. It checks the workflow's prerequisites and adds the adoption line to `CLAUDE.md` or `AGENTS.md`. Then it starts `<project>-lead` in the lead role, or makes the current session the lead where no session can be started, and tells you what happens next.
- **`lead`** and **`worker`**, two roles that each run as a whole session (`claude --agent agent-team:lead`). They link to the workflow's rules rather than copying them. Don't dispatch them as subagents.

## Install

```bash
claude plugin marketplace add rmorison/engineering-standards
claude plugin install agent-team@engineering-standards
```

To pin a version, add the marketplace at a ref, as you pin the hooks: `claude plugin marketplace add rmorison/engineering-standards@<ref>`. The adoption line can pin the workflow document too. Each role reads the workflow at the URL in that line, so a pin holds.

To pick up a newer version, run `claude plugin marketplace update engineering-standards` and then `claude plugin update agent-team@engineering-standards`. Claude Code caches an installed plugin by its version, so whoever changes anything in `plugins/agent-team/` also raises the version in its `.claude-plugin/plugin.json`; otherwise the update reports the plugin current and keeps the old copy (observed on 2.1.293).

To stop using it, follow the workflow's "To decline or stop", then run `claude plugin uninstall agent-team@engineering-standards`. Nothing in your repository depends on the plugin.

## How the lead is started

`start-team` takes the first of these that works and tells you which it used:

1. **The Claude Code CLI:** `claude --bg --agent agent-team:lead -n <project>-lead`, run from the project's main checkout. Reach the lead with `claude attach <id>`. The project must be one where Claude Code's trust prompt was accepted.
2. **A host session tool**, such as `create_session` in Claude Code on the web: a new session titled `<project>-lead`, which loads the lead role from this plugin or from its URL. A cloud session can receive messages but can't send them to local sessions, so you read the lead in the host's session view, and it falls back to its scheduled GitHub check for workers' news.
3. **The current session**, which becomes the lead and says so. It also prints the command for starting a role-loaded lead later.

A background session started in the default mode waits on its first permission prompt until you attach. The skill's step 7 holds the one rule for which mode started sessions get; in short, never `bypassPermissions`, and `auto` or `acceptEdits` only when both hooks are installed.

Proved on Claude Code 2.1.293; see [#101](https://github.com/rmorison/engineering-standards/issues/101) for the runs.
