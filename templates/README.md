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

Layer 1 is `CLAUDE.md`, the file copied to your project root. That follows
the layer definition in [`../ai/claude-code/README.md`](../ai/claude-code/README.md):
Layer 1 is the always-loaded context, and of it that file says: "Elsewhere
this layer appears as `AGENTS.md`, a project-root `CLAUDE.md`, or IDE rule
files." The `ai/claude-code/rules/` directory named as Layer 1's
vendor-neutral baseline in
[`../README.md`](../README.md#six-layer-ai-architecture) is *this* repository's
own Layer 1; it is not copied into your project, and it is the place to look for
baseline rule content to draw on when filling `CLAUDE.md` in. Copying `.claude/`
alone therefore gives you Layers 2, 3 and 6; Layer 1 arrives with `CLAUDE.md`,
in step 2 below.

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
`settings.json` entry that registers it. Copy the whole entry, not just the
path. A hook matcher takes a nested `hooks` array, and the command is guarded:

```
hook="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/pre-tool-use/example-block.py"; [ -f "$hook" ] || exit 0; exec python3 "$hook"
```

Both halves of that guard are load-bearing, and an unguarded
`python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/...` is worse than no hook at all.
If the variable is unset or empty the path becomes `/.claude/hooks/...`; python3
cannot open it and CPython exits 2 - and on `PreToolUse`, exit 2 means *block*.
Every `Write` and `Edit` in the session is then refused, with `can't open file`
as the stated reason. The same happens if you delete a hook script and leave its
`settings.json` entry behind. `${VAR:-.}` covers unset *and* empty, `[ -f ]`
covers the missing script, and `exec` keeps python3's exit code as the hook's so
a real block still blocks. Measured under Claude Code 2.1.278 on 2026-09-22: the
unguarded form exits 2 with `CLAUDE_PROJECT_DIR` unset, the guarded form exits 0.

The scripts themselves take the same care - every error path exits 0 - and the
registration has to match it, or that care is undone one line above.

**A malformed `PreToolUse` entry appears to void the whole file.** Under Claude
Code **2.1.278** a `PreToolUse` entry with `command` on the matcher object made
Claude Code reject the entire settings file, `permissions` block included, so
this kit shipped with no permission rules either. That is an observation of one
version's behaviour on a binary this repository does not control, dated here
rather than stated as a law. Nothing in the kit depends on it staying true: the
entry shape above is the documented one whether or not a malformed one is
punished that harshly.

`node scripts/check-template-kit.mjs`, run in CI, checks that shape for every
`.claude/settings.json` in this repository. For this kit specifically it also
*runs* both hook commands: once with `CLAUDE_PROJECT_DIR` unset and once with it
empty, where neither may exit 2, and once wired correctly, where the
`PreToolUse` hook must still exit 2 on a payload it is meant to refuse and 0 on
one it is not. The last of those is the one that matters most - a hook that
exits 0 on everything looks exactly like no hook at all, which is the state this
kit was in for its whole life before this. The same script checks that every
`permissions` entry matches the commands it is meant to match.

## Permissions and hooks

`.claude/settings.json` carries a `permissions` block and two example hooks.
They do different jobs, and the difference is easy to get backwards.

Every claim here about how Claude Code behaves is sourced to the permissions
reference, <https://code.claude.com/docs/en/permissions>, retrieved 2026-09-22
against Claude Code 2.1.278. Block quotes and quoted phrases are verbatim from
that page; everything outside quotation marks - including every judgement about
what belongs in this kit - is this repository's own, and carries no more
authority than its reasoning does.

**A Bash permission rule matches text, not a program.** From
[Bash rule limits](https://code.claude.com/docs/en/permissions#bash), retrieved
2026-09-22:

> A Bash rule matches the command text Claude writes … It doesn't match the
> same program invoked in a different form, so a deny or ask rule covers the
> invocation Claude usually produces and isn't a security boundary around the
> program.

(The elision drops "after Claude Code splits compound commands and strips
wrappers", which qualifies the first clause without changing this point.)

So `Bash(rm -rf:*)` does not cover `rm -fr` or `rm --recursive --force`, and
`Bash(git push --force:*)` does not cover `git push -f`, nor a `+ref` push such
as `git push origin +main`. The same page's own table gives `Bash(git push *)`
matching `git push origin main` and not `git -C . push origin main`,
`git -c push.default=current push origin main` or `git 'push' origin main`.

**On `:*` versus a space.** That table writes `Bash(git push *)` while this
kit's `settings.json` writes `Bash(git push --force:*)`. Neither is wrong -
they are the same rule. The page states it directly: "The `:*` suffix is an
equivalent way to write a trailing wildcard, so `Bash(ls:*)` matches the same
commands as `Bash(ls *)`." The kit uses the `:*` form throughout; quotations
from the docs keep whichever form the docs used. One caveat, from the same
paragraph: the `:*` form is recognized only at the *end* of a pattern, so in
`Bash(git:* push)` the colon is a literal and matches no git command.

**The two `deny` entries here are defence in depth, not a guarantee.** They stop
the form the model usually writes. Read them as a speed bump on the common case;
do not read them as a fence around `rm` or around `git push`.

**What is a boundary: sandboxing, and a `PreToolUse` hook.** Sandboxing is
OS-level rather than textual - the permissions page sends you to it for
"filesystem and network enforcement that doesn't depend on the command text",
and describes it as enforcement that "restricts shell commands' filesystem and
network access", applying to Bash, PowerShell and Monitor commands and their
child processes. Turning it on is its own page:
<https://code.claude.com/docs/en/sandboxing>. A hook, meanwhile, sees the
command as written rather than as a prefix, and it outranks the allow list -
from [Extend permissions with
hooks](https://code.claude.com/docs/en/permissions#extend-permissions-with-hooks),
retrieved 2026-09-22:

> A blocking hook also takes precedence over allow rules. A hook that exits with
> code 2 stops the tool call before permission rules are evaluated, so the block
> applies even when an allow rule would otherwise let the call proceed.

Note what that does *not* say. The same page adds that "Hook decisions don't
bypass permission rules": a hook returning `"allow"` does not override a `deny`
or `ask` rule. It is exit code 2 specifically, in the blocking direction, that
gets there first.

`.claude/hooks/pre-tool-use/example-block.py` is that slot. The example it ships
with inspects file content rather than commands, because a content rule is the
thing a starter kit can usefully demonstrate; a command check you need to hold
goes in the same place, reading `tool_input.command` off the payload.

### Why `allow` names git subcommands rather than `Bash(git:*)`

Rules are evaluated deny, then ask, then allow. The permissions page states it
under [Manage permissions](https://code.claude.com/docs/en/permissions#manage-permissions),
retrieved 2026-09-22:

> Rules are evaluated in order: deny, then ask, then allow. The first match in
> that order determines the outcome, and rule specificity doesn't change the
> order.

So `allow` is the last box: a command that reaches it matched nothing else, and
a broad entry there is not a convenience, it is the decision. The asymmetry
between the two `deny` entries makes the point. `rm` appears in no `allow`
entry, so a variant the deny rule misses, typed as `rm`, still reaches a human
prompt - there the deny rule is decorative but harmless. `git push -f` was a
different case: `Bash(git:*)` auto-approved it, so the deny rule was not merely
incomplete, it was contradicted by the allow list three lines above it.

`rm` typed as `rm` is the only form that holds for. Any command reaches the
shell through `make`, which the allow list approves whatever follows it - see
[Why `Bash(make:*)` stays](#why-bashmake-stays). Until the uv entries were
narrowed, `uv run rm -rf build` was approved the same way; see the next section.

The listed subcommands are what a routine session needs without a human in the
loop. `push` is deliberately absent; every push reaches a decision.

**Read-only subcommands are listed generously, on purpose.** `rev-parse`,
`ls-files`, `blame`, `describe` and `grep` are read-only in the forms a session
actually writes, and an adopter who is prompted ten times an hour for `git
rev-parse --show-toplevel` widens the list straight back to `Bash(git:*)` -
which is the failure this whole section exists to prevent. Making the narrowing
livable is what makes it survive.

**`Bash(git grep:*)` is the one entry with a known exception, and it is stated
rather than fenced.** `git grep -O<cmd>` and `git grep
--open-files-in-pager=<cmd>` run `<cmd>`, so that entry auto-approves arbitrary
execution through a subcommand listed above as a read-only staple. Verified
against git 2.43.0: `git grep -O'<cmd>' needle` ran `<cmd>` and exited 0. This
is **not** fixed here, because it cannot be. These are prefix patterns; they
match on what a command starts with, and a flag can appear anywhere after the
prefix, so no spelling of `Bash(git grep ...)` excludes `-O` while still
admitting `git grep -n TODO`. A `deny` entry would catch `git grep -O` written
in exactly that position and miss `git grep -n -O`, which is the decorative kind
of rule this file warns about two sections up. What closes it is a `PreToolUse`
hook reading `tool_input.command`, or sandboxing - the two things named above as
boundaries. Weigh that when you copy the entry; do not read the narrowing of
`remote` and `worktree` as meaning every other entry on the list has been
audited flag by flag.

**Two entries are scoped because the subcommand splits read from write.** These
are prefix patterns, so `Bash(git worktree:*)` would admit `worktree remove`
alongside `worktree list`, and `Bash(git remote:*)` would admit `remote add`,
`set-url` and `remove` alongside a bare listing. Neither bare form is in the
kit. Instead:

- `Bash(git worktree list:*)` - the read form only. `add` and `remove` reach a
  human.
- `Bash(git remote)` and `Bash(git remote -v)` - the two listing forms, both
  with no wildcard at all, so each matches that exact command string and nothing
  else. Any `remote` invocation with anything after it reaches a human.

  `-v` carries no wildcard **because `git remote -v` is not a prefix of the
  listing forms only**. In `git remote`, `-v` goes *between* `remote` and the
  subcommand - git's own option documentation says "NOTE: This must be placed
  between `remote` and subcommand." So `Bash(git remote -v:*)`, which is what
  this entry used to be, auto-approved `git remote -v add`, `git remote -v
  set-url`, `git remote -v remove` and `git remote -v update --prune`. All four
  were run against git 2.43.0 and all four succeeded: the remote was added, its
  URL changed, and the remote deleted. That entry was added specifically to
  avoid the `Bash(git:*)` hole and had the same hole; the text here used to
  claim it did not. `scripts/check-template-kit.mjs` now holds all four of those
  forms in `ALLOW_NEGATIVE`, so the claim is checked rather than asserted.

**A note on what this list does not weigh.** `checkout`, `restore`, `stash` and
`branch -D` can each destroy uncommitted work that no remote holds, while a
`push` is recoverable from the local history that produced it. The list is not
sorted by that asymmetry: it is sorted by what a routine session needs, and the
entries above were signed off as they stand. If you are adapting the kit and
your own work is more often uncommitted than pushed, that is the trade to
revisit first.

### Why `allow` names uv commands rather than `Bash(uv:*)`

`uv run` is a command launcher, not a tool: it runs whatever follows it in the
project's environment. So `Bash(uv:*)`, which this kit used to carry, approved
`uv run cat .env`, `uv run env`, `uv run bash -c ...` and `uv run rm -rf build`
without a prompt, and the `rm -rf` deny rule never saw the last of those,
because it starts with `uv`. Claude Code does not strip `uv run` before
matching. From
[Wrappers](https://code.claude.com/docs/en/permissions#process-wrappers),
retrieved 2026-09-25:

> This wrapper list is built in and is not configurable. Development environment
> runners such as `direnv exec`, `devbox run`, `mise exec`, `npx`, and `docker
> exec` are not in the list. Because these tools execute their arguments as a
> command, a rule like `Bash(devbox run *)` matches whatever comes after `run`,
> including `devbox run rm -rf .`. To approve work inside an environment runner,
> write a specific rule that includes both the runner and the inner command,
> such as `Bash(devbox run npm test)`. Add one rule per inner command you want
> to allow.

The page does not name uv. `uv run` is in the same class, and the kit follows
that advice, with one departure for arguments noted below:

- `Bash(uv run pytest:*)`, `Bash(uv run ruff:*)` and `Bash(uv run mypy:*)` - the
  test, lint and type-check tools the Python standard's Makefile and CI run
  through uv. They keep a wildcard for arguments, where the page's example is an
  exact rule, because test and lint invocations vary by path and flag. A flag
  written between `run` and the tool - `uv run --with x pytest`,
  `uv run --env-file .env pytest` - does not match, and reaches a human.
- `Bash(uv sync)`, `Bash(uv sync --all-extras)`, `Bash(uv lock)` and
  `Bash(uv lock --upgrade)` - the four forms the Python standard documents, with
  no wildcard. A wildcard would approve uv's index, `--script`, `--project` and
  `--directory` options, which install or build packages from a source nobody
  chose.

What reaches a human by design: `uv add` and `uv remove`, which change the
dependency set; `uvx`, `uv tool run`, `uv pip` and `uv run python`; and the
`uv run` forms of `detect-secrets`, `pip-audit`, `pre-commit` and `mkdocs`. The
first three of those have `make` targets in the Python standard, which is how a
routine session reaches them.

**A named entry controls which program starts, not what it does.** `uv sync`
and `uv lock` build the project, and uv's docs say a build backend may run
arbitrary Python code. `uv run pytest` imports the project's tests and every
`conftest.py`. These entries are narrower than `Bash(uv:*)`; they are not safe
in any stronger sense than the code they run.

### Why `Bash(make:*)` stays

`Bash(make:*)` approves any target, including one written on the command line.
`make --eval='x: ; @cat .env' x` defines a target and runs it; verified against
GNU Make 4.3, it printed the file and exited 0. So `make` is a route to any
command, and the secrets rule in the Python standard already says never to let a
Makefile target an agent can reach invoke the secret manager.

The entry stays because make targets belong to each project. A kit cannot list
targets its adopters do not have yet, and an adopter prompted for `make test`
every few minutes widens the list back. If your Makefile is settled, replace the
entry with your own targets - `Bash(make test)`, `Bash(make lint)` - and update
the fixtures below.

`node scripts/check-template-kit.mjs` holds the list to both directions: every
entry must match the command it exists for, and no entry may match `git push`,
`git push -f`, `git push --force origin main`, `git push origin +main`, or any
of the `uv` forms named above as reaching a human. `ALLOW_ACCEPTED_RISK` holds
the `make --eval` form in the other direction: the check fails if `Bash(make:*)`
stops matching it, so this section cannot outlive the entry it describes.

## Adding more templates

Stack-specific scaffolding - a Python service, a web application - would live
here as sibling directories. None exist yet, and this file will name them when
they do rather than before. Any such template implements the standards in
[`../code/`](../code/): [`python-standards.md`](../code/python-standards.md)
specifies ruff as both linter and formatter,
[`web-application-standards.md`](../code/web-application-standards.md) and
[`database-standards.md`](../code/database-standards.md) cover the rest.
