# Project Templates

The starter kit for adopting these standards in a new project with Claude Code.

Two things live here and both are meant to be copied, not read:

- `.claude/` - the Claude Code configuration directory, copied into your
  project root as `.claude/`.
- `CLAUDE.md` - the project instruction file, copied to your project root and
  filled in.

[`../README.md`](../README.md#project-templates) gives the copy-and-customise
steps and how the kit maps onto the six-layer AI architecture. This file
describes what is in the directory and what the configuration actually does.

## What the kit provides

| Path | Architecture layer | What it is |
|------|--------------------|------------|
| `.claude/settings.json` | - | Permission rules and the two example hook registrations |
| `.claude/skills/` | Layer 2 (Skills) | Vendor-neutral `plan`, `spec` and `review` skills |
| `.claude/agents/` | Layer 3 (Agents) | `code-reviewer` and `spec-writer` subagents |
| `.claude/hooks/` | Layer 6 (Hooks) | One `PreToolUse` and one `PostToolUse` example, wired and working |
| `CLAUDE.md` | Layer 1 (Rules) | Project instruction template with the sections to fill in |

The layers are defined in [`../ai/claude-code/README.md`](../ai/claude-code/README.md)
and in [ADR-0001](../docs/engineering/adr/0001-six-layer-ai-architecture.md).
Layers 4 and 5 are not in this kit; when compound-engineering is installed it
fills them, per
[`../process/compound-engineering-integration.md`](../process/compound-engineering-integration.md).

The skills reference the canonical standards by URL rather than copying them, so
a project that adopts the kit does not fork the standards along with it.

## Usage

1. Copy `templates/.claude/` into your project root as `.claude/`.
2. Copy `templates/CLAUDE.md` to your project root as `CLAUDE.md` and fill in
   every commented placeholder - project identity, module boundaries,
   conventions, milestones.
3. Adjust `.claude/settings.json` to your project's toolchain. Read
   [Permissions and hooks](#permissions-and-hooks) before widening the `allow`
   list.
4. Replace the example rule in each hook with a rule your project needs, or
   delete the hooks you do not want. Both scripts are runnable from a shell:
   pipe a JSON payload to one and read the exit code.

## The example hooks

`.claude/hooks/pre-tool-use/example-block.py` refuses a `Write` or `Edit` whose
content contains `time.sleep(` - a stand-in for whatever your project wants to
keep out of its code. It exits 2, which is what tells Claude Code to block the
tool call, and prints the reason on stderr.

`.claude/hooks/post-tool-use/example-notify.py` runs after a write has already
landed and logs which file changed. `PostToolUse` cannot block; it reports.

Both read the JSON payload Claude Code writes to their stdin - not environment
variables - and both exit 0 on absent or malformed input, so a mis-wired hook
costs you the check rather than the session. Each script's docstring carries the
`settings.json` entry that registers it. Copy that shape: a hook matcher takes a
nested `hooks` array, and Claude Code rejects the entire settings file, the
`permissions` block included, when a `PreToolUse` entry is malformed.

`node scripts/check-template-kit.mjs`, run in CI, checks that shape for every
`.claude/settings.json` in this repository.

## Permissions and hooks

`.claude/settings.json` carries a `permissions` block and two example hooks.
They do different jobs, and the difference is easy to get backwards.

**A Bash permission rule matches text, not a program.** The Claude Code
permissions reference says so directly:

> A Bash rule matches the command text Claude writes ... It doesn't match the
> same program invoked in a different form, so a deny or ask rule covers the
> invocation Claude usually produces and isn't a security boundary around the
> program.

So `Bash(rm -rf:*)` does not cover `rm -fr` or `rm --recursive --force`, and
`Bash(git push --force:*)` does not cover `git push -f`, nor a `+ref` push such
as `git push origin +main`. The same page's own table gives `Bash(git push *)`
stopping `git push origin main` and not `git -C . push origin main`.

**The two `deny` entries here are defence in depth, not a guarantee.** They stop
the form the model usually writes. Read them as a speed bump on the common case;
do not read them as a fence around `rm` or around `git push`.

**What is a boundary: sandboxing, and a `PreToolUse` hook.** Sandboxing does not
depend on command text at all. A hook sees the command as written rather than as
a prefix, and it outranks the rules — the same page:

> A blocking hook also takes precedence over allow rules. A hook that exits with
> code 2 stops the tool call before permission rules are evaluated, so the block
> applies even when an allow rule would otherwise let the call proceed.

`.claude/hooks/pre-tool-use/example-block.py` is that slot. The example it ships
with inspects file content rather than commands, because a content rule is the
thing a starter kit can usefully demonstrate; a command check you need to hold
goes in the same place, reading `tool_input.command` off the payload.

**This is why `allow` names git subcommands rather than `Bash(git:*)`.** Rules
are evaluated deny, then ask, then allow, so `allow` is the last box: a command
that reaches it matched nothing else, and a broad entry there is not a
convenience, it is the decision. The asymmetry between the two `deny` entries
makes the point. `rm` appears in no `allow` entry, so a variant the deny rule
misses still reaches a human prompt — there the deny rule is decorative but
harmless. `git push -f` was a different case: `Bash(git:*)` auto-approved it, so
the deny rule was not merely incomplete, it was contradicted by the allow list
three lines above it. The listed subcommands are what a routine session needs
without a human in the loop. `push` is deliberately absent; every push reaches a
decision.

## Adding more templates

Stack-specific scaffolding - a Python service, a web application - would live
here as sibling directories. None exist yet, and this file will name them when
they do rather than before. Any such template implements the standards in
[`../code/`](../code/): [`python-standards.md`](../code/python-standards.md)
specifies ruff as both linter and formatter,
[`web-application-standards.md`](../code/web-application-standards.md) and
[`database-standards.md`](../code/database-standards.md) cover the rest.
