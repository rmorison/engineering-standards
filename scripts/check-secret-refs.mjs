#!/usr/bin/env node
/**
 * Checks that a secret reference file holds references and nothing else.
 *
 * The rule lives in code/python-standards.md (Configuration Management >
 * Secrets): a project commits `secret-refs.env`, whose every value is a
 * reference into a secret manager, never the secret itself. Unlike its two
 * sibling scripts, this check is preventive: no shipped defect prompted it. It
 * exists so that the rule's central promise, "this file holds no secret", is
 * decided by a program rather than trusted to review.
 *
 *   1. The line classifier passes its built-in fixtures before it reports on any
 *      file (LINE_FIXTURES, FILE_FIXTURES). A classifier that is wrong would
 *      otherwise pass a literal as confidently as it passes a reference.
 *   2. Every line of a reference file is a full-line comment, a blank line, or
 *      `KEY=reference`, where the reference matches one grammar in
 *      REFERENCE_GRAMMARS and is the whole value. Anything else fails: quotes,
 *      `export`, `$`, an inline comment, whitespace in a value, a YAML-style
 *      `KEY: value`. Dotenv parsers disagree about each of those, so a file
 *      that one of them reads differently from this check is not safe to pass.
 *   3. No key repeats, and no key has a browser-exposed prefix: a build tool
 *      inlines NEXT_PUBLIC_ and similar values into client bundles.
 *   4. Every named file exists, and a reference file has at least one entry. A
 *      check over nothing reports the same "passed" as a check over everything.
 *   5. No key appears in both a reference file and a configuration file, and at
 *      least one configuration file is named, so the rule cannot be skipped by
 *      leaving the configuration file out. Configuration files are read
 *      leniently, but a line this script cannot read as a key fails, because a
 *      skipped line could hide a shared key.
 *   6. With --standard, the `# secret-refs.env` and `# example.env` example
 *      blocks in code/python-standards.md each appear exactly once and pass
 *      checks 2-5, so the standard cannot show an example its own rule rejects.
 *
 * A pass means only that the named files are well-formed. It does not mean a
 * reference resolves, that no secret sits in some other file, that every key in
 * the reference file really is a secret, or that a value shaped like a
 * reference is not a pasted secret: `op://dev/stripe/<pasted key>` passes.
 *
 * Messages name the file, line and key, never the value, so a real secret in a
 * reference file does not end up in a CI log.
 *
 * Usage:  node scripts/check-secret-refs.mjs --standard
 *         node scripts/check-secret-refs.mjs <reference-file>... --config <configuration-file>...
 * Exits non-zero if any check fails. No dependencies beyond Node itself.
 */

import { readFileSync, existsSync } from 'node:fs';
import { join, dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const STANDARD = join(REPO_ROOT, 'code', 'python-standards.md');

/**
 * The reference grammars this check accepts. Each entry records where its
 * syntax was verified. Only 1Password's ships; a project using doppler, sops or
 * HashiCorp Vault adds an entry with its own source, which keeps the rule
 * tool-neutral while the shipped default stays verified.
 *
 * A segment admits only letters, digits, `.`, `_` and `-`. Listing what a
 * segment may contain, rather than what it may not, keeps out shell
 * metacharacters, control characters and non-ASCII, any of which would make a
 * committed file dangerous to source by mistake.
 */
const SEGMENT = '[A-Za-z0-9._-]+';
const REFERENCE_GRAMMARS = [
  {
    name: '1Password',
    // op://<vault-name>/<item-name>[/<section-name>]/<field-name>
    source: '@1password/sdk 0.5.0 (npm, published by 1Password), checked 2026-09-24',
    pattern: new RegExp(`^op://${SEGMENT}/${SEGMENT}(?:/${SEGMENT})?/${SEGMENT}$`),
  },
];

const KEY = /^[A-Z_][A-Z0-9_]*$/;
const BROWSER_EXPOSED_PREFIXES = ['NEXT_PUBLIC_', 'VITE_', 'REACT_APP_', 'PUBLIC_'];

/**
 * Classifies one reference-file line as blank, comment, reference, literal,
 * exposed or malformed. Only blank, comment and reference pass. `reason` says
 * why a line failed without repeating its value.
 */
function classifyLine(line) {
  if (/^[ \t]*$/.test(line)) return { kind: 'blank' };
  if (line.startsWith('#')) return { kind: 'comment' };

  const entry = /^([A-Za-z0-9_]+)=(.*)$/.exec(line);
  if (!entry) {
    return { kind: 'malformed', reason: 'is not a comment, a blank line or KEY=reference' };
  }
  const [, key, value] = entry;
  if (!KEY.test(key)) {
    return { kind: 'malformed', key, reason: 'has a key that is not UPPER_SNAKE_CASE' };
  }
  if (BROWSER_EXPOSED_PREFIXES.some((prefix) => key.startsWith(prefix))) {
    return { kind: 'exposed', key, reason: 'has a browser-exposed prefix, so a build tool would inline it into client code' };
  }
  if (REFERENCE_GRAMMARS.some((grammar) => grammar.pattern.test(value))) {
    return { kind: 'reference', key };
  }
  return { kind: 'literal', key, reason: literalReason(value) };
}

/** Why a value is not a reference, in words that do not repeat the value. */
function literalReason(value) {
  if (value === '') return 'has an empty value';
  if (/^["']/.test(value)) return 'has a quoted value';
  if (value.includes('$')) return 'has a `$` in its value';
  if (/[ \t]#/.test(value)) return 'has an inline comment';
  if (/\s/.test(value)) return 'has whitespace in its value';
  if (/^op:\/\//.test(value)) return 'has an op:// value that is not a well-formed reference';
  return 'has a value that is not a reference';
}

/** Splits file text into lines, dropping a byte-order mark and CRLF endings. */
function linesOf(text) {
  return text.replace(/^\uFEFF/, '').split(/\r?\n/);
}

/**
 * Checks a reference file's text. `report(index, check, message)` receives the
 * zero-based line index, or null for a whole-file failure. Returns the keys the
 * file defines, each mapped to its line index.
 */
function checkReferenceText(text, report) {
  const keys = new Map();
  linesOf(text).forEach((line, index) => {
    const result = classifyLine(line);
    if (['malformed', 'literal', 'exposed'].includes(result.kind)) {
      const subject = result.key ? `\`${result.key}\`` : 'this line';
      report(index, result.kind, `${subject} ${result.reason}`);
      return;
    }
    if (result.kind !== 'reference') return;
    if (keys.has(result.key)) {
      report(index, 'duplicate', `\`${result.key}\` is also defined on line ${keys.get(result.key) + 1} of this file`);
      return;
    }
    keys.set(result.key, index);
  });
  if (keys.size === 0) {
    report(null, 'empty', 'defines no references; a reference file with no entries checks nothing');
  }
  return keys;
}

/** Reads a configuration file's keys, failing on any line it cannot read. */
function configurationKeys(text, report) {
  const keys = new Map();
  linesOf(text).forEach((line, index) => {
    if (/^[ \t]*$/.test(line) || /^[ \t]*#/.test(line)) return;
    const entry = /^(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*=/.exec(line);
    if (!entry) {
      report(index, 'unreadable', 'is not a KEY=value line, so a key it holds could be missed');
      return;
    }
    if (!keys.has(entry[1])) keys.set(entry[1], index);
  });
  return keys;
}

/** Fails every key a reference file shares with a configuration file. */
function checkDisjoint(references, configurations, report) {
  for (const ref of references) {
    for (const [key, index] of ref.keys) {
      for (const config of configurations) {
        if (config.keys.has(key)) {
          report(ref, index, 'shared-key',
            `\`${key}\` is also defined in ${config.label}; secrets and configuration share no key`);
        }
      }
    }
  }
}

/**
 * Line fixtures: [line, expected kind]. Every must-fail case the plan names is
 * here, so a change that loosens the classifier fails before any file is read.
 * Literal values are obviously fake and in no provider's format, so they cannot
 * trip GitHub push protection.
 */
const LINE_FIXTURES = [
  // Happy path
  ['STRIPE_API_KEY=op://dev/stripe/credential', 'reference'],
  ['API_KEY=op://dev/app/api/key', 'reference'],
  ['KEY=op://dev.vault/my_item/field-1', 'reference'],
  ['# rotated 2026-09', 'comment'],
  ['#', 'comment'],
  ['', 'blank'],
  ['   ', 'blank'],
  // Known limit, recorded rather than hidden: a secret pasted in as segments
  // passes, because it is shaped like a reference. See the header.
  ['KEY=op://hunter2/hunter2/hunter2', 'reference'],
  // Literals
  ['KEY=hunter2', 'literal'],
  ['KEY=', 'literal'],
  ['KEY=not-a-reference', 'literal'],
  // Rejected syntax
  ['KEY="op://dev/a/b"', 'literal'],
  ["KEY='op://dev/a/b'", 'literal'],
  ['export KEY=op://dev/a/b', 'malformed'],
  ['KEY=${OTHER}', 'literal'],
  ['KEY=op://${VAULT}/a/b', 'literal'],
  ['KEY=op://dev/a/b # note', 'literal'],
  // A reference that is not the whole value
  ['DATABASE_URL=postgres://u:op://dev/a/b@h/d', 'literal'],
  ['KEY=hunter2 op://dev/a/b', 'literal'],
  // Malformed references
  ['KEY=op://My Vault/a/b', 'literal'],
  ['KEY=op://dev/a', 'literal'],
  ['KEY=op://a/b/c/d/e', 'literal'],
  ['KEY=op://dev//b', 'literal'],
  ['KEY=op://dev/a/b?attribute=otp', 'literal'],
  ['KEY=https://user:pass@host', 'literal'],
  ['KEY=OP://dev/a/b', 'literal'],
  // Shell metacharacters, a control character and non-ASCII inside a segment
  ...[';', '`', '|', '&', "'", '"', '\\', '(', ')', '<', '>', '#', '*', '\u0007', '\u00E9']
    .map((ch) => [`KEY=op://dev/stripe/a${ch}b`, 'literal']),
  // Browser exposure
  ['NEXT_PUBLIC_STRIPE_KEY=op://dev/stripe/credential', 'exposed'],
  ['VITE_API_KEY=op://dev/a/b', 'exposed'],
  ['REACT_APP_KEY=op://dev/a/b', 'exposed'],
  ['PUBLIC_KEY=op://dev/a/b', 'exposed'],
  // Malformed lines
  ['op://dev/a/b', 'malformed'],
  ['KEY: op://dev/a/b', 'malformed'],
  ['KEY = op://dev/a/b', 'malformed'],
  ['1KEY=op://dev/a/b', 'malformed'],
  ['lower=op://dev/a/b', 'malformed'],
  ['  KEY=op://dev/a/b', 'malformed'],
  ['  # an indented comment', 'malformed'],
  ['KEY-NAME=op://dev/a/b', 'malformed'],
];

/**
 * File fixtures: a reference file, the configuration files beside it, and the
 * checks expected to fail. An empty list means the fixture must pass.
 */
const FILE_FIXTURES = [
  { name: 'valid file', refs: 'A=op://dev/a/b\n# c\n\nB=op://dev/b/c\n', configs: ['C=1\n'], fails: [] },
  { name: 'CRLF endings', refs: 'A=op://dev/a/b\r\nB=op://dev/b/c\r\n', configs: ['C=1\r\n'], fails: [] },
  { name: 'byte-order mark', refs: '\uFEFFA=op://dev/a/b\n', configs: ['C=1\n'], fails: [] },
  { name: 'repeated key', refs: 'A=op://dev/a/b\nA=op://dev/a/c\n', configs: ['C=1\n'], fails: ['duplicate'] },
  { name: 'no entries', refs: '# only a comment\n\n', configs: ['C=1\n'], fails: ['empty'] },
  { name: 'empty file', refs: '', configs: ['C=1\n'], fails: ['empty'] },
  { name: 'shared key', refs: 'A=op://dev/a/b\n', configs: ['A=local\n'], fails: ['shared-key'] },
  { name: 'shared key, export form', refs: 'A=op://dev/a/b\n', configs: ['export A=local\n'], fails: ['shared-key'] },
  { name: 'unreadable configuration line', refs: 'A=op://dev/a/b\n', configs: ['not a key line\n'], fails: ['unreadable'] },
];

/** Runs the reference and configuration checks on in-memory texts. */
function checkTexts(refsText, configTexts, report) {
  const refs = { label: 'the reference file', keys: checkReferenceText(refsText, (i, c, m) => report(c, m)) };
  const configs = configTexts.map((text, n) => ({
    label: `configuration file ${n + 1}`,
    keys: configurationKeys(text, (i, c, m) => report(c, m)),
  }));
  checkDisjoint([refs], configs, (ref, i, c, m) => report(c, m));
}

/** Check 1: the classifier and file rules must pass their fixtures first. */
function selfTest() {
  const problems = [];
  for (const [line, expected] of LINE_FIXTURES) {
    const { kind } = classifyLine(line);
    if (kind !== expected) {
      problems.push(`line fixture ${JSON.stringify(line)} classified as ${kind}, expected ${expected}`);
    }
  }
  for (const fixture of FILE_FIXTURES) {
    const seen = [];
    checkTexts(fixture.refs, fixture.configs, (check) => seen.push(check));
    const got = [...new Set(seen)].sort().join(', ') || 'no failures';
    const want = [...fixture.fails].sort().join(', ') || 'no failures';
    if (got !== want) problems.push(`file fixture "${fixture.name}" produced ${got}, expected ${want}`);
  }
  return problems;
}

const failures = [];
const fail = (file, line, check, message) =>
  failures.push({ file: file ? relative(process.cwd(), file) || file : '-', line, check, message });

/** Reads a named file, recording a failure when it is missing. */
function readNamed(path) {
  if (!existsSync(path)) {
    fail(path, null, 'missing', 'does not exist');
    return null;
  }
  return readFileSync(path, 'utf8');
}

/** Checks reference files against configuration files, both given as paths. */
function checkFiles(refPaths, configPaths) {
  const refs = [];
  for (const path of refPaths) {
    const text = readNamed(path);
    if (text === null) continue;
    const keys = checkReferenceText(text, (i, check, message) => fail(path, i === null ? null : i + 1, check, message));
    refs.push({ path, keys });
  }
  const configs = [];
  for (const path of configPaths) {
    const text = readNamed(path);
    if (text === null) continue;
    const keys = configurationKeys(text, (i, check, message) => fail(path, i + 1, check, message));
    configs.push({ path, keys, label: relative(process.cwd(), path) || path });
  }
  checkDisjoint(refs, configs, (ref, i, check, message) => fail(ref.path, i + 1, check, message));
  return refs.length + configs.length;
}

/**
 * Finds the fenced blocks whose first line is exactly `marker`. Returns each
 * block's text and the Markdown line number of its first line. Only this much
 * fence handling is needed, because the marker line identifies the block.
 */
function markedBlocks(lines, marker) {
  const blocks = [];
  for (let i = 1; i < lines.length; i++) {
    const open = /^(`{3,}|~{3,})/.exec(lines[i - 1]);
    if (!open || lines[i] !== marker) continue;
    const fence = open[1];
    const closes = (line) => {
      const close = /^(`{3,}|~{3,})[ \t]*$/.exec(line);
      return close && close[1][0] === fence[0] && close[1].length >= fence.length;
    };
    const body = [];
    for (let j = i; j < lines.length && !closes(lines[j]); j++) body.push(lines[j]);
    blocks.push({ text: body.join('\n') + '\n', firstLine: i + 1 });
  }
  return blocks;
}

/** Check 6: the standard's own example blocks. */
function checkStandard() {
  const text = readNamed(STANDARD);
  if (text === null) return 0;
  const lines = linesOf(text);
  const found = {};
  for (const marker of ['# secret-refs.env', '# example.env']) {
    const blocks = markedBlocks(lines, marker);
    if (blocks.length !== 1) {
      fail(STANDARD, blocks[1]?.firstLine ?? null, 'example',
        `expected exactly one fenced block starting with \`${marker}\`, found ${blocks.length}`);
    }
    found[marker] = blocks[0];
  }
  const refsBlock = found['# secret-refs.env'];
  const configBlock = found['# example.env'];
  if (!refsBlock || !configBlock) return 0;

  const at = (block) => (i, check, message) => fail(STANDARD, i === null ? block.firstLine : block.firstLine + i, check, message);
  const refs = { keys: checkReferenceText(refsBlock.text, at(refsBlock)) };
  const configs = [{ keys: configurationKeys(configBlock.text, at(configBlock)), label: 'the `# example.env` block' }];
  checkDisjoint([refs], configs, (ref, i, check, message) => at(refsBlock)(i, check, message));
  return 2;
}

/** Parses arguments into a mode, or records a usage failure. */
function parseArgs(argv) {
  if (argv.length === 1 && argv[0] === '--standard') return { mode: 'standard' };
  const refs = [];
  const configs = [];
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--config' && i + 1 < argv.length) configs.push(resolve(argv[++i]));
    else if (argv[i].startsWith('--')) return { mode: 'usage', message: `unknown or incomplete option ${argv[i]}` };
    else refs.push(resolve(argv[i]));
  }
  if (refs.length === 0) return { mode: 'usage', message: 'no reference file named' };
  if (configs.length === 0) {
    return { mode: 'usage', message: 'no --config file named, so the shared-key rule could not run' };
  }
  return { mode: 'files', refs, configs };
}

const problems = selfTest();
if (problems.length > 0) {
  console.error(`\nThe classifier failed ${problems.length} of its own fixture(s), so no file was checked:\n`);
  for (const problem of problems) console.error(`  [self-test] ${problem}`);
  console.error('');
  process.exit(1);
}

const args = parseArgs(process.argv.slice(2));
let checked = 0;
if (args.mode === 'usage') {
  fail(null, null, 'usage',
    `${args.message}. Usage: check-secret-refs.mjs --standard | <reference-file>... --config <configuration-file>...`);
} else if (args.mode === 'standard') {
  checked = checkStandard();
} else {
  checked = checkFiles(args.refs, args.configs);
}

if (failures.length > 0) {
  console.error(`\n${failures.length} problem(s) found:\n`);
  for (const f of failures) console.error(`  ${f.file}:${f.line ?? '-'}  [${f.check}] ${f.message}`);
  console.error('');
  process.exit(1);
}

console.log(
  `Checked ${checked} file(s) or example block(s) against ${REFERENCE_GRAMMARS.length} reference ` +
  `grammar(s), after ${LINE_FIXTURES.length} line and ${FILE_FIXTURES.length} file fixtures passed.`);
console.log('All secret reference checks passed. That means the files are well-formed, not that no secret is present.');
