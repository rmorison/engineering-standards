#!/usr/bin/env node
/**
 * Documentation checks for this repository.
 *
 * Catches defects that ship silently: a Markdown file renders "fine" locally,
 * and the damage is only visible on GitHub, or not visible at all. Each check
 * here exists because the defect it looks for reached the default branch.
 *
 *   1. Mermaid diagrams parse.
 *   2. Relative links resolve to a file on disk.
 *   3. No list item opens a blockquote by accident.
 *   4. No run of marker-prefixed lines collapses into one paragraph.
 *
 * Usage:  node scripts/check-docs.mjs [--verbose]
 * Exits non-zero if any check fails.
 */

import { readFileSync, existsSync, statSync } from 'node:fs';
import { readdir } from 'node:fs/promises';
import { join, dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const VERBOSE = process.argv.includes('--verbose');

/** Directory names skipped wherever they appear in the tree. */
const SKIP_ANYWHERE = new Set(['.git', 'node_modules']);

/**
 * Specific directories skipped, as repo-relative paths.
 *
 * `archive/` and `docs/plans/` hold point-in-time artifacts. Plans in
 * particular quote text destined for other files, so their paths are relative
 * to a destination the checker cannot know — checking them reports links that
 * are correct where the text will land.
 *
 * These are paths rather than names deliberately: matching on the name alone
 * would also skip a future `process/plans/` or a `scripts/` directory inside a
 * template, silently and with nothing in the output saying so.
 */
const SKIP_PATHS = new Set(['archive', 'docs/plans', 'scripts']);

const failures = [];
const fail = (file, line, check, message) =>
  failures.push({ file: relative(REPO_ROOT, file), line, check, message });

/** Every Markdown file in the repository, minus SKIP_DIRS. */
async function markdownFiles(dir = REPO_ROOT) {
  const found = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (SKIP_ANYWHERE.has(entry.name)) continue;
      const rel = relative(REPO_ROOT, join(dir, entry.name));
      if (SKIP_PATHS.has(rel)) continue;
      found.push(...(await markdownFiles(join(dir, entry.name))));
    } else if (entry.name.endsWith('.md')) {
      found.push(join(dir, entry.name));
    }
  }
  return found;
}

/**
 * Check 1 — Mermaid diagrams parse.
 *
 * Uses mermaid's `parse()` rather than a full render. The two disagree: the
 * render path accepts constructs that GitHub's parser rejects, so a diagram can
 * render locally and still show an error box on GitHub. `parse()` reproduces
 * GitHub's behavior, and needs no browser.
 */
async function checkMermaid(files) {
  const blocks = [];
  for (const file of files) {
    const lines = readFileSync(file, 'utf8').split('\n');
    let start = null;
    lines.forEach((line, i) => {
      if (start === null && line.trim() === '```mermaid') start = i;
      else if (start !== null && line.trim() === '```') {
        blocks.push({ file, line: start + 2, source: lines.slice(start + 1, i).join('\n') });
        start = null;
      }
    });
  }
  if (blocks.length === 0) return 0;

  // mermaid needs a DOM even to parse.
  const { JSDOM } = await import('jsdom');
  const dom = new JSDOM('<!DOCTYPE html><body></body>', { pretendToBeVisual: true });
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  const mermaid = (await import('mermaid')).default;
  mermaid.initialize({ startOnLoad: false });

  for (const block of blocks) {
    try {
      await mermaid.parse(block.source);
    } catch (error) {
      const detail = String(error.message).split('\n')[0].trim();
      fail(block.file, block.line, 'mermaid', `diagram does not parse — ${detail}`);
    }
  }
  return blocks.length;
}

/**
 * Check 2 — relative links resolve.
 *
 * Only relative targets are checked; external URLs are not fetched. A link to a
 * directory is fine, as is a fragment on an existing file.
 */
function checkLinks(files) {
  let checked = 0;
  for (const file of files) {
    const lines = readFileSync(file, 'utf8').split('\n');
    lines.forEach((line, i) => {
      for (const match of line.matchAll(/\]\((?!https?:|mailto:|#)([^)\s]+)\)/g)) {
        const target = match[1].split('#')[0];
        if (!target) continue; // pure fragment, same file
        checked++;
        const resolved = resolve(dirname(file), target);
        if (!existsSync(resolved)) {
          fail(file, i + 1, 'link', `relative link does not resolve: ${target}`);
        }
      }
    });
  }
  return checked;
}

/**
 * Check 3 — no accidental blockquote inside a list item.
 *
 * `- >3 months: split` is a list item containing a blockquote, not a bullet
 * reading "greater than three months". The `>` is swallowed and the line
 * renders indented in a quote block. Wrap the comparison in backticks.
 */
function checkAccidentalBlockquotes(files) {
  for (const file of files) {
    readFileSync(file, 'utf8').split('\n').forEach((line, i) => {
      if (/^\s*[-*+]\s*>/.test(line)) {
        fail(file, i + 1, 'blockquote', 'list item starts with ">", which opens a blockquote — use a code span');
      }
    });
  }
}

/**
 * Check 4 — marker-prefixed lines that do not form a list.
 *
 * Consecutive lines beginning with a status marker and no list marker are
 * joined into one run-on paragraph, because a newline alone does not break a
 * Markdown paragraph. Two or more in a row is always a list that lost its
 * markers.
 */
function checkUnmarkedLists(files) {
  const MARKER = /^[✅❌⚠️✓✗\u{1F534}\u{1F7E1}\u{1F7E2}]+\s+\S/u;
  for (const file of files) {
    const lines = readFileSync(file, 'utf8').split('\n');
    let run = [];
    const flush = () => {
      if (run.length >= 2) {
        fail(file, run[0], 'unmarked-list',
          `${run.length} consecutive marker lines with no list marker render as one paragraph`);
      }
      run = [];
    };
    let inFence = false;
    lines.forEach((line, i) => {
      if (line.trim().startsWith('```')) { inFence = !inFence; flush(); return; }
      if (!inFence && MARKER.test(line)) run.push(i + 1);
      else flush();
    });
    flush();
  }
}

const files = await markdownFiles();
const diagrams = await checkMermaid(files);
const links = checkLinks(files);
checkAccidentalBlockquotes(files);
checkUnmarkedLists(files);

if (VERBOSE || failures.length === 0) {
  console.log(`Checked ${files.length} Markdown files: ${diagrams} Mermaid diagram(s), ${links} relative link(s).`);
}

if (failures.length > 0) {
  console.error(`\n${failures.length} problem(s) found:\n`);
  for (const f of failures) console.error(`  ${f.file}:${f.line}  [${f.check}] ${f.message}`);
  console.error('');
  process.exit(1);
}

console.log('All documentation checks passed.');
