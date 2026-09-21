# Project Templates

Project scaffolding and boilerplate for common application scenarios.

## Purpose

This directory contains starter templates for different technology stacks and application types. Each template implements the code quality standards defined in `../code/` and follows the process standards in `../process/`.

## Future Templates

Examples of templates that will live here:

- **python-fastapi/** - FastAPI backend service with async Python
  - Pre-configured: black/ruff, pytest, Docker, CI/CD
  - Implements standards from `code/python.md`

- **nextjs-webapp/** - Next.js web application with TypeScript
  - Pre-configured: ESLint, Prettier, testing, deployment
  - Implements standards from `code/typescript.md`

- **go-daemon/** - Go service daemon
  - Pre-configured: gofmt, golint, testing, systemd service
  - Implements standards from `code/go.md`

- **python-cli/** - Python command-line application
  - Pre-configured: Click/Typer, packaging, testing
  - Implements standards from `code/python.md`

## Template Structure

Each template should include:
- **README.md** - Usage instructions and customization guide
- **Pre-configured tooling** - Linters, formatters, pre-commit hooks matching code standards
- **Example code** - Minimal working example demonstrating best practices
- **CI/CD configuration** - GitHub Actions or similar
- **Documentation templates** - Following `process/documentation-standards.md`

## Usage

1. Copy template directory to your new project location
2. Search and replace placeholder names (project name, author, etc.)
3. Customize as needed while maintaining code standards
4. Remove example code and build your application

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
`Bash(git push --force:*)` does not cover `git push -f` or `git push origin
+main`. The same page's own table gives `Bash(git push *)` stopping
`git push origin main` and not `git -C . push origin main`.

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

## Status

**Placeholder** - Templates will be added as common patterns emerge from project work.
