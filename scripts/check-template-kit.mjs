#!/usr/bin/env node
/**
 * Checks for every `.claude/settings.json` in this repository — structural for
 * all of them, and behavioural for the starter kit, which is also run.
 *
 * The starter kit in `templates/.claude/` is copied into adopters' projects,
 * so a defect in it ships to every one of them. Each check here exists because
 * the defect it looks for reached the default branch:
 *
 *   1. The file parses as JSON.
 *   2. Every key under `hooks` is a Claude Code event name. `8389dc4` shipped
 *      `pre-tool-use` and `post-tool-use` — lowercase and hyphenated — and the
 *      kit's Layer 6 was dead from the day it shipped. Nothing noticed, because
 *      an unknown event name registers nothing and says nothing.
 *   3. Every hook entry has a non-empty `hooks` array, a `matcher` that Claude
 *      Code can evaluate, and no key beyond those two. Both entries in the kit
 *      once put `command` straight on the matcher object, so neither hook was
 *      ever registered. Observed under Claude Code 2.1.278: a malformed
 *      `PreToolUse` entry made Claude Code reject the whole settings file, so
 *      the `permissions` block beside it was inert too. That is one version's
 *      behaviour, recorded with its version rather than asserted as a law —
 *      this check is worth keeping either way, since the entry simply does not
 *      register in that shape.
 *   4. Every element of a `hooks` array is a hook handler object, and a
 *      `"type": "command"` handler has a non-empty `command`.
 *   5. Every script path a command names under the settings file's own
 *      `.claude/` directory exists on disk and is a file. A hook command that
 *      points at a moved or renamed file does NOT fail quietly: python3 cannot
 *      open the file and CPython exits 2, and on `PreToolUse` exit 2 means
 *      *block*. A stale path there refuses every matching tool call in the
 *      session. (An earlier version of this comment said "fails silently at
 *      run time". That was wrong, and it was the wrong way round.)
 *   6. `templates/.claude/settings.json` specifically registers at least one
 *      `PreToolUse` and one `PostToolUse` hook. Checks 2-5 all pass on a file
 *      whose `hooks` block has been deleted outright, which is the same dead
 *      Layer 6 arrived at by a different route.
 *   7. At least one settings file was found. A walk that matches nothing
 *      reports the same "all checks passed" as a walk that matches everything.
 *   8. Every `permissions` entry in the kit matches the commands it is meant to
 *      match, and none of them matches a `git push`. The allow list was only
 *      ever swept negatively; a typo like `Bash(git statu:*)` passes checks 1-7
 *      and surfaces months later as an unexplained prompt that someone "fixes"
 *      by widening back to `Bash(git:*)`. The rule matcher this check needs is
 *      a reimplementation of someone else's, so it is first self-tested against
 *      the worked examples on the Claude Code permissions page (see
 *      RULE_SYNTAX_FIXTURES) — a wrong matcher would otherwise vouch for the
 *      list as confidently as a right one.
 *   9. The kit's two hook commands are RUN, and observed to fail open when
 *      mis-wired and to still block when wired correctly. Checks 1-8 are all
 *      textual, and the defect that motivated this one is not: a command of
 *      `python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/...` is perfectly
 *      well-formed, names a file that exists, and still refuses every Write and
 *      Edit in the session the moment CLAUDE_PROJECT_DIR is unset, because
 *      python3 exits 2 on a file it cannot open and PreToolUse reads 2 as
 *      "block". Nothing short of running it catches that, so this check runs it.
 *
 * Deliberately NOT a validation against the published Claude Code settings
 * schema (https://json.schemastore.org/claude-code-settings.json). That schema
 * would catch the original defect — it was used to confirm it — but it is
 * community-maintained, sets `additionalProperties: false` throughout, and lags
 * Claude Code releases, so a newly valid setting would fail CI.
 *
 * That argument does not make these checks immune to the same failure, and it
 * should not be read as claiming otherwise. `MATCHER_KEYS`, `HOOK_TYPES` and
 * `HOOK_EVENTS` are closed sets over the same upstream, transcribed from the
 * hooks reference on 2026-09-22 (Claude Code 2.1.278). When Claude Code adds an
 * event, a handler type, or a key on a matcher group, this file will reject a
 * valid settings file until someone updates it. The tradeoff is accepted for a
 * smaller surface — three short lists in one file, each traceable to a table in
 * the docs — rather than a whole schema tracking every key in the product. If
 * this check ever cries wolf, widen the list; do not switch it off.
 *
 * Usage:  node scripts/check-template-kit.mjs [--verbose]
 * Exits non-zero if any check fails. No dependencies beyond Node itself.
 */

import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join, dirname, resolve, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const VERBOSE = process.argv.includes('--verbose');

/** Directory names skipped wherever they appear in the tree. */
const SKIP_ANYWHERE = new Set([
  '.git',
  'node_modules',
  // Transient checkouts a GitHub action or a local review script leaves behind.
  // A scratch copy of the repository is not the repository.
  '.claude-pr',
]);

/** The only keys a hook matcher group may carry. */
const MATCHER_KEYS = new Set(['matcher', 'hooks']);

/**
 * Hook handler types, from the "Common fields" table of the hooks reference.
 * Only `command` handlers carry a script path for check 5.
 */
const HOOK_TYPES = new Set(['command', 'http', 'mcp_tool', 'prompt', 'agent']);

/**
 * Every Claude Code hook event, from the "Hook events" section of
 * https://code.claude.com/docs/en/hooks (retrieved 2026-09-22, v2.1.278).
 *
 * This is the check that would have caught `8389dc4`. Without it,
 * `"PreToolUsee"`, `"pre-tool-use"` and `"preToolUse"` all pass every other
 * assertion in this file.
 */
const HOOK_EVENTS = new Set([
  'SessionStart', 'Setup', 'InstructionsLoaded', 'UserPromptSubmit',
  'UserPromptExpansion', 'MessageDisplay', 'PreToolUse', 'PermissionRequest',
  'PostToolUse', 'PostToolUseFailure', 'PostToolBatch', 'PermissionDenied',
  'Notification', 'SubagentStart', 'SubagentStop', 'TaskCreated',
  'TaskCompleted', 'Stop', 'StopFailure', 'TeammateIdle', 'ConfigChange',
  'CwdChanged', 'DirectoryAdded', 'FileChanged', 'WorktreeCreate',
  'WorktreeRemove', 'PreCompact', 'PostCompact', 'PreModelSwitch',
  'PostModelSwitch', 'SessionEnd', 'Elicitation', 'ElicitationResult',
]);

/** The kit itself, which checks 6 and 8 hold to a higher standard than the rest. */
const KIT_SETTINGS = join(REPO_ROOT, 'templates', '.claude', 'settings.json');

const failures = [];
const fail = (file, line, check, message) =>
  failures.push({ file: relative(REPO_ROOT, file), line, check, message });

/** Every `.claude/settings.json` in the tree. */
function settingsFiles(dir = REPO_ROOT) {
  const found = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (SKIP_ANYWHERE.has(entry.name)) continue;
      found.push(...settingsFiles(full));
      // `join` emits a platform separator, so comparing against a literal '/'
      // silently matches nothing on Windows and the whole walk returns empty.
    } else if (entry.name === 'settings.json' && dir.endsWith(`${sep}.claude`)) {
      found.push(full);
    }
  }
  return found;
}

/**
 * The 1-based line a string first appears on, or null.
 *
 * JSON.parse discards position, so failures are located by looking the
 * offending text back up in the source. Good enough to jump to, and it costs
 * nothing when it misses.
 */
function lineOf(source, needle) {
  if (typeof needle !== 'string' || needle === '') return null;
  const index = source.indexOf(JSON.stringify(needle).slice(1, -1));
  if (index === -1) return null;
  return source.slice(0, index).split('\n').length;
}

// ---------------------------------------------------------------------------
// Check 3 — matcher values
// ---------------------------------------------------------------------------

/** Characters that keep a matcher on the exact-string path, per the docs. */
const EXACT_MATCH_ONLY = /^[A-Za-z0-9_\-, |]+$/;

/**
 * Why a matcher value is unusable, or null if it is fine.
 *
 * Per https://code.claude.com/docs/en/hooks#matcher-patterns: `"*"`, `""` and
 * an omitted matcher all mean "match all"; a value of only letters, digits,
 * `_`, `-`, spaces, `,` and `|` is compared as exact strings; anything else is
 * a JavaScript regular expression. So a non-string is never valid, and a value
 * on the regex path that does not compile silently matches nothing.
 */
function matcherProblem(matcher) {
  if (matcher === undefined) return null;
  if (typeof matcher !== 'string') {
    return `\`matcher\` must be a string, not ${Array.isArray(matcher) ? 'an array' : typeof matcher}`;
  }
  if (matcher === '*' || matcher === '' || EXACT_MATCH_ONLY.test(matcher)) return null;
  try {
    new RegExp(matcher);
  } catch (error) {
    return `\`matcher\` ${JSON.stringify(matcher)} is not a valid regular expression ` +
      `(${error.message}), so the entry matches nothing`;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Check 5 — script paths named in a hook command
// ---------------------------------------------------------------------------

/** Characters that end a shell word for the purposes of finding a path token. */
const WORD_BREAK = new Set([' ', '\t', '\n', '"', "'", '`', ';', '|', '&', '(', ')', '=', '<', '>', ',']);

/**
 * Prefixes that mean "the `.claude/` beside this settings file".
 *
 * Anything else — `~/.claude/`, `$HOME/.claude/`, `$CLAUDE_CONFIG_DIR/...`,
 * `${CLAUDE_PLUGIN_ROOT}/.claude/`, an absolute path — names a directory this
 * check has no business resolving against `dirname(file)`. A shared hook in the
 * user's own `~/.claude/hooks/` is a legitimate thing to reference, and
 * reporting it missing would block the repository over a file that is not the
 * repository's to hold.
 */
const LOCAL_PREFIXES = [
  '', './', '$CLAUDE_PROJECT_DIR/', '${CLAUDE_PROJECT_DIR}/',
];
const LOCAL_PREFIX_RE = /^\$\{CLAUDE_PROJECT_DIR(:?[-=+?][^}]*)?\}\/$/;

function isProjectLocal(prefix) {
  const bare = prefix.replace(/["']/g, '');
  return LOCAL_PREFIXES.includes(bare) || LOCAL_PREFIX_RE.test(bare);
}

/** True if a path token cannot be resolved without running a shell. */
const hasShellExpansion = (text) => /[$`*?~\[\]{}]/.test(text);

let pathsSkipped = 0;

/**
 * Check 5. Finds each `.claude/` in a command, recovers the whole shell word
 * around it, and only resolves the ones that name the local `.claude/`.
 */
function checkCommandPaths(file, source, command, where, isKit) {
  const claudeDir = dirname(file);
  const marker = '.claude/';
  // Quotes are stripped before scanning. `python3 "$CLAUDE_PROJECT_DIR"/.claude/x`
  // is the form the hooks reference recommends for shell form, and treating the
  // closing quote as a word break would recover a prefix of just `/` and send a
  // perfectly good project-local path down the "not ours" branch.
  const text = command.replace(/["']/g, '');

  // A path this check cannot resolve is tolerable in an arbitrary settings
  // file and not in the kit, which is the artifact this whole script exists to
  // keep working. Skipping there would restore exactly the silent pass the
  // path check was added to remove.
  const unresolvable = (why) => {
    pathsSkipped += 1;
    if (isKit) {
      fail(file, lineOf(source, command), 'hook-path',
        `${where} command names a path this check cannot resolve (${why}); the kit's ` +
        'own hook paths must be literal, or check 5 vouches for nothing');
    }
  };

  for (let at = text.indexOf(marker); at !== -1; at = text.indexOf(marker, at + 1)) {
    let start = at;
    while (start > 0 && !WORD_BREAK.has(text[start - 1])) start -= 1;
    let end = at + marker.length;
    while (end < text.length && !WORD_BREAK.has(text[end])) end += 1;

    const prefix = text.slice(start, at);
    const tail = text.slice(at + marker.length, end);

    if (!isProjectLocal(prefix)) {
      // Not this repository's `.claude/`; nothing here can verify it. A shared
      // hook under the user's own `~/.claude/` is legitimate, and resolving it
      // against `dirname(file)` would report a missing file that isn't.
      unresolvable(`\`${prefix}\` is not the project's own .claude/`);
      continue;
    }
    if (tail === '' || hasShellExpansion(tail)) {
      // `.claude/hooks/$TOOL/run.py` cannot be resolved statically. The old
      // check captured `hooks/` out of it and passed, because `existsSync`
      // says true for a directory — a vacuous pass reading as a real one.
      unresolvable('it contains a shell expansion');
      continue;
    }

    const target = join(claudeDir, tail);
    const shown = relative(REPO_ROOT, target);
    if (!existsSync(target)) {
      fail(file, lineOf(source, command), 'hook-path',
        `${where} command names ${shown}, which does not exist — on PreToolUse ` +
        'the interpreter exits 2 over that, which blocks the tool call');
    } else if (!statSync(target).isFile()) {
      fail(file, lineOf(source, command), 'hook-path',
        `${where} command names ${shown}, which is a directory, not a script`);
    }
  }
}

// ---------------------------------------------------------------------------
// Check 8 — permission rule matching
// ---------------------------------------------------------------------------

const escapeRe = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/**
 * The forms a `Bash(...)` specifier matches, as regular expressions.
 *
 * Transcribed from https://code.claude.com/docs/en/permissions#wildcard-patterns
 * (retrieved 2026-09-22):
 *
 *   - `*` stands in for any text, including spaces.
 *   - A trailing `*` with a space before it also matches the bare command, but
 *     only when it is the rule's only wildcard.
 *   - The space before a trailing `*` is part of the rule, so `Bash(ls*)` and
 *     `Bash(ls *)` differ.
 *   - "The `:*` suffix is an equivalent way to write a trailing wildcard, so
 *     `Bash(ls:*)` matches the same commands as `Bash(ls *)`." Recognized only
 *     at the end of a pattern; elsewhere the colon is a literal.
 *
 * What this deliberately does NOT model: Claude Code splits compound commands
 * and strips process wrappers *before* a rule is matched, so what a rule is
 * tested against is one simple command. This function takes that simple command
 * as given. Feeding it `a && b` would therefore misreport — not because the
 * rules behave differently, but because the splitting has not happened yet. The
 * fixtures and sweeps below all use single commands, which is the level Claude
 * Code matches at.
 */
function bashRuleForms(specifier) {
  const pattern = specifier.endsWith(':*') ? `${specifier.slice(0, -2)} *` : specifier;
  const parts = pattern.split('*');
  const forms = [new RegExp(`^${parts.map(escapeRe).join('.*')}$`)];
  if (parts.length === 2 && pattern.endsWith(' *')) {
    forms.push(new RegExp(`^${escapeRe(pattern.slice(0, -2))}$`));
  }
  return forms;
}

/** True if `command` matches the Bash permission rule `entry`, e.g. `Bash(git log:*)`. */
function bashRuleMatches(entry, command) {
  const specifier = /^Bash\((.*)\)$/s.exec(entry);
  if (!specifier) return entry === 'Bash';
  return bashRuleForms(specifier[1]).some((form) => form.test(command));
}

/**
 * Self-test rows, taken verbatim from the worked table on the permissions page.
 * `bashRuleMatches` is a reimplementation of Claude Code's matcher, and a wrong
 * reimplementation would vouch for a broken allow list just as confidently as a
 * right one. These rows make the matcher earn the vouching first.
 */
const RULE_SYNTAX_FIXTURES = [
  ['Bash(npm run build)', ['npm run build'], ['npm run build --watch']],
  ['Bash(npm run *)', ['npm run build', 'npm run test --watch', 'npm run'], ['npm install']],
  ['Bash(git log * main)',
    ['git log --oneline main', 'git log -5 main', 'git log --output=<file> main'],
    ['git log main', 'git push origin main']],
  ['Bash(git * main)',
    ['git merge main', 'git push origin main', 'git -c core.fsmonitor=<script> diff main'],
    ['git log']],
  ['Bash(* --version)', ['node --version', "bash -c 'echo hi' --version"], ['node -v']],
  ['Bash(ls *)', ['ls -la', 'ls'], ['lsof']],
  ['Bash(ls*)', ['ls -la', 'lsof'], []],
  ['Bash(* --help *)', ['npm --help x'], ['npm --help']],
  // "The `:*` suffix is an equivalent way to write a trailing wildcard."
  ['Bash(ls:*)', ['ls -la', 'ls'], ['lsof']],
  // "In a pattern like `Bash(git:* push)`, the colon is treated as a literal
  // character and won't match git commands."
  ['Bash(git:* push)', [], ['git push', 'git remote push']],
];

/**
 * Commands every entry in the kit's allow list is meant to cover: one per
 * entry, each of which must match exactly one entry. "Exactly one" is what
 * catches both a typo (zero matches) and a new entry that silently subsumes an
 * older, narrower one (two matches).
 */
const ALLOW_POSITIVE = [
  'make test',
  'uv sync',
  'git status --short',
  'git diff --cached',
  'git log --oneline -5',
  'git show HEAD',
  'git rev-parse --show-toplevel',
  'git ls-files',
  'git blame README.md',
  'git describe --tags',
  'git grep -n TODO',
  'git worktree list',
  'git remote',
  'git remote -v',
  'git add -A',
  'git commit -m x',
  'git branch --all',
  'git switch -c feature',
  'git checkout -- README.md',
  'git stash pop',
  'git fetch origin',
  'git pull --ff-only',
  'git restore --staged README.md',
  'ruff check .',
  'mypy src',
  'pytest -q',
];

/**
 * Commands no allow entry may match. `push` is absent from the list by
 * decision, and the `worktree` and `remote` entries are scoped to their read
 * forms, so the mutating subcommands beside them must still reach a human.
 *
 * The `git remote -v <subcommand>` rows are not padding. `-v` in `git remote`
 * goes BETWEEN `remote` and the subcommand — "NOTE: This must be placed
 * between `remote` and subcommand", per git's own option documentation — so
 * `Bash(git remote -v:*)`, the entry that was added to avoid the `Bash(git:*)`
 * hole, auto-approved every config-mutating `remote` subcommand through
 * exactly that hole. All four forms below were run against git 2.43.0 and all
 * four succeeded. The bare forms above them were already here and passed,
 * which is how the sweep vouched for a list that did not hold: a negative
 * sweep only excludes the spellings someone thought to write down.
 */
const ALLOW_NEGATIVE = [
  'git push',
  'git push -f',
  'git push --force origin main',
  'git push origin +main',
  'git worktree remove ../wt',
  'git worktree add ../wt',
  'git remote add upstream git@github.com:o/r.git',
  'git remote set-url origin git@github.com:o/r.git',
  'git remote remove upstream',
  'git remote -v add upstream git@github.com:o/r.git',
  'git remote -v set-url origin git@github.com:o/r.git',
  'git remote -v remove upstream',
  'git remote -v update --prune',
];

/** Commands each deny entry is meant to cover. */
const DENY_POSITIVE = [
  ['Bash(rm -rf:*)', 'rm -rf build'],
  ['Bash(git push --force:*)', 'git push --force origin main'],
];

function checkRuleSyntaxFixtures() {
  for (const [entry, shouldMatch, shouldNotMatch] of RULE_SYNTAX_FIXTURES) {
    for (const command of shouldMatch) {
      if (!bashRuleMatches(entry, command)) {
        fail(KIT_SETTINGS, null, 'rule-syntax',
          `the rule matcher in this script says ${entry} does not match \`${command}\`, ` +
          'but the Claude Code permissions page says it does — the matcher is wrong, ' +
          'so check 8 cannot be trusted');
      }
    }
    for (const command of shouldNotMatch) {
      if (bashRuleMatches(entry, command)) {
        fail(KIT_SETTINGS, null, 'rule-syntax',
          `the rule matcher in this script says ${entry} matches \`${command}\`, ` +
          'but the Claude Code permissions page says it does not — the matcher is ' +
          'wrong, so check 8 cannot be trusted');
      }
    }
  }
}

function checkKitPermissions(file, source, settings) {
  const allow = settings?.permissions?.allow;
  const deny = settings?.permissions?.deny;
  if (!Array.isArray(allow) || allow.length === 0) {
    fail(file, lineOf(source, 'allow'), 'permissions',
      'the kit must carry a non-empty `permissions.allow` list');
    return;
  }
  if (!Array.isArray(deny) || deny.length === 0) {
    fail(file, lineOf(source, 'deny'), 'permissions',
      'the kit must carry a non-empty `permissions.deny` list');
    return;
  }

  const matchedBy = new Set();
  for (const command of ALLOW_POSITIVE) {
    const hits = allow.filter((entry) => bashRuleMatches(entry, command));
    if (hits.length === 0) {
      fail(file, lineOf(source, 'allow'), 'permissions',
        `no allow entry matches \`${command}\`, which one of them is meant to cover — ` +
        'check that entry for a typo before widening anything');
    } else if (hits.length > 1) {
      fail(file, lineOf(source, hits[0]), 'permissions',
        `\`${command}\` matches ${hits.length} allow entries (${hits.join(', ')}); ` +
        'one of them is redundant or broader than intended');
    } else {
      matchedBy.add(hits[0]);
    }
  }
  for (const entry of allow) {
    if (!matchedBy.has(entry)) {
      fail(file, lineOf(source, entry), 'permissions',
        `allow entry ${entry} is not covered by ALLOW_POSITIVE in ` +
        'scripts/check-template-kit.mjs — add the command it is meant to permit, ' +
        'so a typo in it cannot go unnoticed');
    }
  }

  for (const command of ALLOW_NEGATIVE) {
    const hits = allow.filter((entry) => bashRuleMatches(entry, command));
    if (hits.length > 0) {
      fail(file, lineOf(source, hits[0]), 'permissions',
        `\`${command}\` is auto-approved by ${hits.join(', ')}; it must reach a human`);
    }
  }

  for (const [entry, command] of DENY_POSITIVE) {
    if (!deny.includes(entry)) {
      fail(file, lineOf(source, 'deny'), 'permissions',
        `deny entry ${entry} is missing`);
    } else if (!bashRuleMatches(entry, command)) {
      fail(file, lineOf(source, entry), 'permissions',
        `deny entry ${entry} does not match \`${command}\`, the command it exists for`);
    }
  }
}

// ---------------------------------------------------------------------------

/**
 * Check 9 — run the kit's hook commands and observe what they do.
 *
 * Three observations per command, the first two of which are the ones that
 * matter: a mis-wired hook must cost you the check, never the session.
 *
 *   A. CLAUDE_PROJECT_DIR unset  -> exit code must not be 2
 *   B. CLAUDE_PROJECT_DIR empty  -> exit code must not be 2
 *   C. wired correctly           -> some PreToolUse command still exits 2 on a
 *                                   payload the kit is documented to refuse,
 *                                   and every one of them exits 0 on one it is
 *                                   not
 *
 * Without C this check would pass just as happily on a hook that exits 0 on
 * everything, which is indistinguishable from no hook at all — the state this
 * kit was actually in.
 *
 * EVERY command under both events is run, not the first of each. Check 5 walks
 * every command in the file and this one used to walk one per event; the
 * fail-open property has to hold for all of them, and a second handler added
 * beside an existing one is exactly where a mis-wired command would sit
 * unobserved.
 *
 * An exit code this check could not observe is a FAILURE, not a pass. On a
 * spawn error or the 15s timeout `spawnSync` reports `status` as null, and the
 * old `if (status === 2)` read that as "did not exit 2" — so a command that
 * never ran at all cleared the two assertions that are the entire reason this
 * check exists.
 *
 * SECURITY — read before moving this. This function executes command strings
 * out of a file in the checkout, by design: nothing short of running them
 * catches the defect above. That is safe only where it is invoked from.
 * `.github/workflows/docs.yml` runs on `pull_request`, which withholds secrets
 * and gives a fork a read-only token, and it already runs PR-authored
 * `scripts/check-template-kit.mjs` and `npm ci` against a PR-authored manifest,
 * so this grants no capability that workflow did not already grant. It must
 * never be invoked from a workflow holding secrets or a write token —
 * `pull_request_target`, a scheduled job, or anything reusing the permissions
 * in `.github/workflows/claude.yml`. If this check moves, that constraint moves
 * with it.
 */
function runKitHooks(file, source, settings) {
  if (process.platform === 'win32') return;  // the kit's commands are POSIX sh
  if (spawnSync('sh', ['-c', 'exit 7']).status !== 7) return;  // no usable sh

  const payload = (content) => JSON.stringify({
    hook_event_name: 'PreToolUse', tool_name: 'Write',
    tool_input: { file_path: 'example.py', content },
  });

  // stdin is always supplied: left open, a correctly wired hook would block
  // waiting for the payload Claude Code normally writes to it.
  const run = (command, projectDir, input) => {
    const env = { ...process.env };
    if (projectDir === undefined) delete env.CLAUDE_PROJECT_DIR;
    else env.CLAUDE_PROJECT_DIR = projectDir;
    return spawnSync('sh', ['-c', command], {
      cwd: REPO_ROOT, env, input, encoding: 'utf8', timeout: 15000,
    });
  };

  /**
   * The exit code of one run, or null once the reason it could not be observed
   * has been recorded as a failure. Every assertion below reads the return
   * value, so "the command never ran" can never be mistaken for "the command
   * behaved".
   */
  const exitCode = (result, line, what) => {
    if (typeof result.status === 'number') return result.status;
    const why = result.error
      ? `it could not be started (${result.error.message})`
      : result.signal
        ? `it was killed by ${result.signal}, which is the 15s timeout`
        : 'the process reported no exit code';
    fail(file, line, 'hook-runs',
      `${what} produced no observable exit code: ${why}. An unobserved run is a ` +
      'failed check, not a passing one — running these commands is the only ' +
      'thing this check does');
    return null;
  };

  const kitRoot = join(REPO_ROOT, 'templates');

  const commands = [];
  for (const event of ['PreToolUse', 'PostToolUse']) {
    const matchers = settings?.hooks?.[event];
    if (!Array.isArray(matchers)) continue;
    matchers.forEach((matcher, m) => {
      const handlers = matcher?.hooks;
      if (!Array.isArray(handlers)) return;
      handlers.forEach((hook, h) => {
        if (hook === null || typeof hook !== 'object') return;
        if (hook.type !== 'command') return;
        if (typeof hook.command !== 'string' || hook.command.trim() === '') return;
        commands.push({
          event, command: hook.command, where: `hooks.${event}[${m}].hooks[${h}]`,
        });
      });
    });
  }

  if (commands.length === 0) {
    // Not a skip. Check 6 counts an `http`, `prompt` or `agent` handler as a
    // registered hook, so a kit carrying only those passes check 6 while this
    // check quietly observes nothing — both green, zero behavioural coverage,
    // which is the state check 9 was added to end.
    fail(file, lineOf(source, 'hooks'), 'hook-runs',
      'the kit registers no `"type": "command"` hook under PreToolUse or ' +
      'PostToolUse, so check 9 runs nothing and vouches for nothing. Check 6 ' +
      'still passes on a non-command handler, so this must be reported rather ' +
      'than skipped: the kit ships one runnable example of each event, and the ' +
      'whole point of this check is that only running it catches a fail-closed ' +
      'command');
    return;
  }

  for (const { event, command, where } of commands) {
    const line = lineOf(source, command);
    for (const [label, value] of [['unset', undefined], ['empty', '']]) {
      const status = exitCode(run(command, value, ''), line,
        `${where}, run with CLAUDE_PROJECT_DIR ${label},`);
      if (status !== 2) continue;
      const consequence = event === 'PreToolUse'
        ? 'on PreToolUse that means *block*, so every Write and Edit in the ' +
          'session is refused with `can\'t open file` as the reason'
        : 'PostToolUse cannot block, but this puts a spurious error in front of ' +
          'Claude on every matching call — and the PreToolUse entry beside it, ' +
          'written the same way, refuses the call outright';
      fail(file, line, 'hook-runs',
        `with CLAUDE_PROJECT_DIR ${label}, the ${where} command exits 2; ` +
        `${consequence}. Guard the path: \`\${CLAUDE_PROJECT_DIR:-.}\` for the ` +
        'unset and empty cases, and `[ -f "$hook" ] || exit 0` before the ' +
        'interpreter is ever handed the path');
    }
  }

  const pre = commands.filter((entry) => entry.event === 'PreToolUse');
  if (pre.length === 0) {
    fail(file, lineOf(source, 'hooks'), 'hook-runs',
      'the kit registers no PreToolUse command, so nothing observes the ' +
      'blocking direction — and a hook that never blocks is indistinguishable ' +
      'from no hook at all');
    return;
  }

  // The shipped example refuses `time.sleep(`; templates/README.md says so. If
  // you replace the example rule, replace these two payloads with yours rather
  // than deleting the check — an example hook that blocks nothing is the defect.
  let observed = 0;
  let blocked = 0;
  for (const { command, where } of pre) {
    const line = lineOf(source, command);
    const status = exitCode(
      run(command, kitRoot, payload('import time\ntime.sleep(3)\n')), line,
      `${where}, run wired correctly on a payload the kit's example rule refuses,`);
    if (status === null) continue;
    observed += 1;
    if (status === 2) blocked += 1;
  }
  if (observed > 0 && blocked === 0) {
    fail(file, lineOf(source, pre[0].command), 'hook-runs',
      `wired correctly, none of the ${pre.length} PreToolUse command(s) exits 2 ` +
      'on a payload the kit\'s example rule is documented to refuse; one of them ' +
      'should. A hook that never blocks is indistinguishable from no hook at all');
  }

  for (const { command, where } of pre) {
    const line = lineOf(source, command);
    const status = exitCode(
      run(command, kitRoot, payload('print("hello")\n')), line,
      `${where}, run wired correctly on an ordinary write,`);
    if (status === null || status === 0) continue;
    fail(file, line, 'hook-runs',
      `wired correctly, the ${where} command exits ${status} on an ordinary ` +
      'write; it should exit 0 and let the call through');
  }
}

function checkSettings(file) {
  const source = readFileSync(file, 'utf8');
  const isKit = resolve(file) === KIT_SETTINGS;

  let settings;
  try {
    settings = JSON.parse(source);
  } catch (error) {
    fail(file, null, 'json', `not valid JSON: ${error.message}`);
    return 0;
  }

  if (isKit) {
    checkKitPermissions(file, source, settings);
    runKitHooks(file, source, settings);
  }

  const hooks = settings?.hooks;
  if (hooks === undefined) {
    // Fine for any other settings file — most have no hooks at all. Not fine
    // for the kit, which is the repository's only Layer 6 and has gone dead
    // once already.
    if (isKit) {
      fail(file, null, 'kit-hooks',
        'the kit has no `hooks` block at all, so it ships no Layer 6');
    }
    return 0;
  }
  if (hooks === null || typeof hooks !== 'object' || Array.isArray(hooks)) {
    fail(file, lineOf(source, 'hooks'), 'hooks',
      '`hooks` must be an object keyed by event name');
    return 0;
  }

  let entries = 0;
  const registered = new Map();

  for (const [event, matchers] of Object.entries(hooks)) {
    if (!HOOK_EVENTS.has(event)) {
      fail(file, lineOf(source, event), 'event',
        `\`${event}\` is not a Claude Code hook event, so nothing under it ever ` +
        `runs — did you mean one of ${[...HOOK_EVENTS].slice(0, 4).join(', ')}, …? ` +
        'The names are PascalCase; see https://code.claude.com/docs/en/hooks');
      continue;
    }
    if (!Array.isArray(matchers)) {
      fail(file, lineOf(source, event), 'hooks',
        `hooks.${event} must be an array of matcher objects`);
      continue;
    }
    if (matchers.length === 0) {
      fail(file, lineOf(source, event), 'hooks',
        `hooks.${event} is an empty array, which registers nothing — remove the ` +
        'key or give it an entry');
      continue;
    }

    matchers.forEach((matcher, position) => {
      const where = `hooks.${event}[${position}]`;
      const line = lineOf(source, event);

      if (matcher === null || typeof matcher !== 'object' || Array.isArray(matcher)) {
        fail(file, line, 'matcher', `${where} must be an object`);
        return;
      }

      for (const key of Object.keys(matcher)) {
        if (!MATCHER_KEYS.has(key)) {
          fail(file, lineOf(source, key) ?? line, 'matcher',
            `${where} carries an unexpected key \`${key}\` — a hook command belongs ` +
            'in the nested `hooks` array, not on the matcher');
        }
      }

      const problem = matcherProblem(matcher.matcher);
      if (problem) fail(file, lineOf(source, 'matcher') ?? line, 'matcher', `${where} ${problem}`);

      if (!Array.isArray(matcher.hooks)) {
        fail(file, line, 'matcher',
          `${where} has no \`hooks\` array, so the entry never registers`);
        return;
      }
      if (matcher.hooks.length === 0) {
        fail(file, line, 'matcher',
          `${where} has an empty \`hooks\` array, so the entry never registers`);
        return;
      }

      matcher.hooks.forEach((hook, hookPosition) => {
        entries += 1;
        const at = `${where}.hooks[${hookPosition}]`;
        if (hook === null || typeof hook !== 'object' || Array.isArray(hook)) {
          fail(file, line, 'hook', `${at} must be an object`);
          return;
        }
        if (!HOOK_TYPES.has(hook.type)) {
          fail(file, line, 'hook',
            `${at} has type ${JSON.stringify(hook.type)}; expected one of ` +
            `${[...HOOK_TYPES].map((t) => JSON.stringify(t)).join(', ')}`);
          return;
        }
        if (hook.type !== 'command') {
          registered.set(event, (registered.get(event) ?? 0) + 1);
          return;
        }
        if (typeof hook.command !== 'string' || hook.command.trim() === '') {
          fail(file, line, 'hook', `${at} has no non-empty \`command\``);
          return;
        }
        registered.set(event, (registered.get(event) ?? 0) + 1);
        checkCommandPaths(file, source, hook.command, where, isKit);
      });
    });
  }

  if (isKit) {
    for (const event of ['PreToolUse', 'PostToolUse']) {
      if (!registered.get(event)) {
        fail(file, lineOf(source, 'hooks'), 'kit-hooks',
          `the kit registers no working ${event} hook — the starter kit ships one ` +
          'of each as its Layer 6 example, and losing either is how it went dead before');
      }
    }
  }

  return entries;
}

checkRuleSyntaxFixtures();

const files = settingsFiles();
if (files.length === 0) {
  fail(REPO_ROOT, null, 'walk',
    'no .claude/settings.json found anywhere in the tree — a walk that matches ' +
    'nothing reports success exactly like a walk that matches everything, so ' +
    'this is a failure, not a pass');
}
if (!files.some((file) => resolve(file) === KIT_SETTINGS)) {
  fail(KIT_SETTINGS, null, 'walk',
    'templates/.claude/settings.json was not reached by the walk, so none of the ' +
    'kit-specific checks ran');
}

let hookEntries = 0;
for (const file of files) hookEntries += checkSettings(file);

if (VERBOSE || failures.length === 0) {
  console.log(
    `Checked ${files.length} .claude/settings.json file(s) and ${hookEntries} hook ` +
    `command(s); ${RULE_SYNTAX_FIXTURES.length} rule-syntax fixtures, ` +
    `${ALLOW_POSITIVE.length} allow-list positive and ${ALLOW_NEGATIVE.length} ` +
    `negative cases. ${pathsSkipped} command path(s) skipped as not statically resolvable.`);
}

if (failures.length > 0) {
  console.error(`\n${failures.length} problem(s) found:\n`);
  for (const f of failures) console.error(`  ${f.file}:${f.line ?? '-'}  [${f.check}] ${f.message}`);
  console.error('');
  process.exit(1);
}

console.log('All template kit checks passed.');
