#!/usr/bin/env node
/**
 * Structural checks for every `.claude/settings.json` in this repository.
 *
 * The starter kit in `templates/.claude/` is copied into adopters' projects,
 * so a defect in it ships to every one of them. Each check here exists because
 * the defect it looks for reached the default branch:
 *
 *   1. The file parses as JSON.
 *   2. Every hook entry has a `hooks` array and no key beyond `matcher` and
 *      `hooks`. Both entries in the kit put `command` straight on the matcher
 *      object, so neither hook was ever registered. Worse, the malformed entry
 *      was a `PreToolUse` one, and Claude Code discards the whole settings
 *      file over that — the `permissions` block beside it was inert too.
 *   3. Every element of a `hooks` array is `{"type": "command", "command": …}`
 *      with a non-empty command. This is the shape the corrected entries use;
 *      the check is what keeps the next hand-edit inside it.
 *   4. Every script path a command names under the settings file's own
 *      `.claude/` directory exists on disk. A hook command that points at a
 *      moved or renamed file fails silently at run time.
 *
 * Deliberately NOT a validation against the published Claude Code settings
 * schema (https://json.schemastore.org/claude-code-settings.json). That schema
 * would catch this defect — it was used to confirm it — but it is
 * community-maintained, sets `additionalProperties: false` throughout, and
 * lags Claude Code releases, so a newly valid setting would fail CI. A check
 * that cries wolf is a check people learn to ignore. These four assertions
 * cover the invariants that actually broke and have no upstream to drift from.
 *
 * Usage:  node scripts/check-template-kit.mjs [--verbose]
 * Exits non-zero if any check fails. No dependencies beyond Node itself.
 */

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join, dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const VERBOSE = process.argv.includes('--verbose');

/** Directory names skipped wherever they appear in the tree. */
const SKIP_ANYWHERE = new Set(['.git', 'node_modules']);

/** The only keys a hook matcher object may carry. */
const MATCHER_KEYS = new Set(['matcher', 'hooks']);

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
    } else if (entry.name === 'settings.json' && dir.endsWith('/.claude')) {
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

/** Check 4 — script paths named in a hook command, relative to its own `.claude/`. */
function checkCommandPaths(file, source, command, event, position) {
  const claudeDir = dirname(file);
  for (const match of command.matchAll(/\.claude\/([\w./-]+)/g)) {
    const target = join(claudeDir, match[1]);
    if (!existsSync(target)) {
      fail(file, lineOf(source, command), 'hook-path',
        `${event}[${position}] command names ${relative(REPO_ROOT, target)}, which does not exist`);
    }
  }
}

function checkSettings(file) {
  const source = readFileSync(file, 'utf8');

  let settings;
  try {
    settings = JSON.parse(source);
  } catch (error) {
    fail(file, null, 'json', `not valid JSON: ${error.message}`);
    return 0;
  }

  const hooks = settings?.hooks;
  // A settings file with no hooks at all is fine — most of them have none.
  if (hooks === undefined) return 0;
  if (hooks === null || typeof hooks !== 'object' || Array.isArray(hooks)) {
    fail(file, lineOf(source, 'hooks'), 'hooks',
      '`hooks` must be an object keyed by event name');
    return 0;
  }

  let entries = 0;
  for (const [event, matchers] of Object.entries(hooks)) {
    if (!Array.isArray(matchers)) {
      fail(file, lineOf(source, event), 'hooks',
        `hooks.${event} must be an array of matcher objects`);
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

      if (!Array.isArray(matcher.hooks)) {
        fail(file, line, 'matcher',
          `${where} has no \`hooks\` array, so the entry never registers`);
        return;
      }

      matcher.hooks.forEach((hook, hookPosition) => {
        entries += 1;
        const at = `${where}.hooks[${hookPosition}]`;
        if (hook === null || typeof hook !== 'object' || Array.isArray(hook)) {
          fail(file, line, 'hook', `${at} must be an object`);
          return;
        }
        if (hook.type !== 'command') {
          fail(file, line, 'hook',
            `${at} has type ${JSON.stringify(hook.type)}; expected "command"`);
        }
        if (typeof hook.command !== 'string' || hook.command.trim() === '') {
          fail(file, line, 'hook', `${at} has no non-empty \`command\``);
          return;
        }
        checkCommandPaths(file, source, hook.command, `hooks.${event}`, position);
      });
    });
  }
  return entries;
}

const files = settingsFiles();
let hookEntries = 0;
for (const file of files) hookEntries += checkSettings(file);

if (VERBOSE || failures.length === 0) {
  console.log(
    `Checked ${files.length} .claude/settings.json file(s) and ${hookEntries} hook command(s).`);
}

if (failures.length > 0) {
  console.error(`\n${failures.length} problem(s) found:\n`);
  for (const f of failures) console.error(`  ${f.file}:${f.line ?? '-'}  [${f.check}] ${f.message}`);
  console.error('');
  process.exit(1);
}

console.log('All template kit checks passed.');
