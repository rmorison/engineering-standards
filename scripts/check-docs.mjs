#!/usr/bin/env node
/**
 * Documentation checks for this repository.
 *
 * Catches defects that ship silently: a Markdown file renders "fine" locally,
 * and the damage is only visible on GitHub, or not visible at all. Each check
 * here exists because the defect it looks for reached the default branch.
 *
 *   1. Mermaid diagrams parse.
 *   2. Relative links resolve, and their anchors name a real heading.
 *   3. No list item opens a blockquote by accident.
 *   4. No run of marker-prefixed lines collapses into one paragraph.
 *   5. Every code fence is closed.
 *
 * Checks 2 through 4 read prose only: fenced code blocks and inline code spans
 * are examples, and an example of a defect is not a defect. That is what lets
 * the documentation show what each check catches.
 *
 * Usage:  node scripts/check-docs.mjs [--verbose]
 * Exits non-zero if any check fails.
 */

import { readFileSync, existsSync, statSync } from 'node:fs';
import { readdir } from 'node:fs/promises';
import { join, dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import GithubSlugger from 'github-slugger';

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
 *
 * Skipping applies to a file as a link *source*. A checked file may still link
 * into one of these directories, and the target's headings are read to verify
 * the anchor.
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

/** An inline code span, backticks included. */
const CODE_SPAN = /`[^`\n]*`/g;

const lineCache = new Map();

/**
 * A Markdown file as records, one per line, each carrying where the line sits.
 *
 * Fence tracking lives here and only here. Every check that needs to tell prose
 * from an example reads `fenced` rather than keeping its own `inFence` flag —
 * checks 2 and 3 once lacked one, so the repository could not document a broken
 * link without contorting the example so it was not literal Markdown.
 *
 * Each record carries both forms of the line because the checks need different
 * ones:
 *
 *   `raw`    — the line as written.
 *   `masked` — the line with every inline code span replaced by filler of the
 *              same length. A link inside a code span renders as text, not a
 *              link, so check 2 reads this form.
 *
 * The filler is same-length rather than empty on purpose. Deleting a span would
 * shift what follows it toward the start of the line, and check 3 anchors on the
 * start of the line: "- `foo` > bar" would collapse to "-  > bar" and report a
 * blockquote that is not there. Check 3 reads `raw` for the same reason, since
 * wrapping the comparison in backticks is the fix it prescribes.
 */
function markdownLines(file) {
  const cached = lineCache.get(file);
  if (cached) return cached;

  let inFence = false;
  const lines = readFileSync(file, 'utf8')
    .split('\n')
    .map((raw, i) => {
      const isDelimiter = raw.trim().startsWith('```');
      if (isDelimiter) inFence = !inFence;
      return {
        number: i + 1,
        raw,
        masked: raw.replace(CODE_SPAN, (span) => 'x'.repeat(span.length)),
        // A delimiter belongs to its own block, so an info string like
        // ```mermaid is not prose either.
        fenced: inFence || isDelimiter,
      };
    });

  lineCache.set(file, lines);
  return lines;
}

const ATX_HEADING = /^#{1,6}\s+(.+)$/;
const slugCache = new Map();

/**
 * The anchor slugs GitHub generates for a file's headings.
 *
 * Uses `github-slugger`, the library GitHub's own Markdown pipeline uses, rather
 * than a local approximation. This repository's headings include emoji, code
 * spans, slashes, brackets and duplicates, and an anchor check that reports
 * failures for live anchors is worse than no anchor check at all — it teaches
 * people to ignore the output.
 *
 * Headings inside fenced blocks are skipped, because GitHub gives them no
 * anchors. That is not an edge case here: most `#` lines in this repository are
 * shell comments in examples, and `process/issue-tracking.md` carries three
 * `## Acceptance Criteria` headings inside fenced issue templates. Collecting
 * them would also shift the `-1`, `-2` suffixes the slugger appends to real
 * duplicates.
 */
function headingSlugs(file) {
  const cached = slugCache.get(file);
  if (cached) return cached;

  const slugger = new GithubSlugger();
  const slugs = new Set();
  for (const line of markdownLines(file)) {
    if (line.fenced) continue;
    const heading = ATX_HEADING.exec(line.raw);
    if (heading) slugs.add(slugger.slug(heading[1].trim()));
  }

  slugCache.set(file, slugs);
  return slugs;
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

/** A relative Markdown link target, anchor included. */
const RELATIVE_LINK = /\]\((?!https?:|mailto:)([^)\s]+)\)/g;

/** Split `./file.md#anchor` into its path and its fragment. Either may be empty. */
function splitAnchor(href) {
  const hash = href.indexOf('#');
  return hash === -1 ? [href, ''] : [href.slice(0, hash), href.slice(hash + 1)];
}

/**
 * Check 2 — relative links resolve, and their anchors name a real heading.
 *
 * Only relative targets are checked; external URLs are not fetched. A link to a
 * directory is fine. Anchors are verified against the target file's headings,
 * same-file (`#section`) and cross-file (`./other.md#section`) alike — this
 * repository routes most rules through "one document owns it, the others link
 * to it", so a renamed heading breaks links in files that did not change.
 *
 * A fragment is only checkable when it lands on a Markdown file; on a directory
 * or another file type it is skipped rather than guessed at.
 */
function checkLinks(files) {
  let checked = 0;
  let anchors = 0;
  for (const file of files) {
    for (const line of markdownLines(file)) {
      if (line.fenced) continue;
      for (const match of line.masked.matchAll(RELATIVE_LINK)) {
        const [target, fragment] = splitAnchor(match[1]);
        checked++;

        const resolved = target ? resolve(dirname(file), target) : file;
        if (target && !existsSync(resolved)) {
          fail(file, line.number, 'link', `relative link does not resolve: ${target}`);
          continue;
        }

        if (!fragment) continue;
        if (!resolved.endsWith('.md') || !statSync(resolved).isFile()) continue;
        anchors++;
        if (!headingSlugs(resolved).has(fragment)) {
          fail(file, line.number, 'anchor',
            `no heading generates this anchor: ${target}#${fragment}`);
        }
      }
    }
  }
  return { checked, anchors };
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
    for (const line of markdownLines(file)) {
      if (line.fenced) continue;
      if (/^\s*[-*+]\s*>/.test(line.raw)) {
        fail(file, line.number, 'blockquote',
          'list item starts with ">", which opens a blockquote — use a code span');
      }
    }
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
    let run = [];
    const flush = () => {
      if (run.length >= 2) {
        fail(file, run[0], 'unmarked-list',
          `${run.length} consecutive marker lines with no list marker render as one paragraph`);
      }
      run = [];
    };
    for (const line of markdownLines(file)) {
      if (!line.fenced && MARKER.test(line.raw)) run.push(line.number);
      else flush();
    }
    flush();
  }
}

/**
 * Check 5 — every code fence is closed.
 *
 * Checks 2 through 4 skip fenced lines, which means an unterminated fence makes
 * the remainder of the file look like one long example and those checks quietly
 * stop reporting on it. A silent skip is the defect this repository has already
 * shipped once, from a directory skip list that matched more than it claimed.
 * Counting delimiters is enough: they toggle, so an odd count cannot close.
 */
function checkFencesClosed(files) {
  for (const file of files) {
    const delimiters = markdownLines(file).filter((line) => line.raw.trim().startsWith('```'));
    if (delimiters.length % 2 !== 0) {
      fail(file, delimiters[delimiters.length - 1].number, 'fence',
        'unterminated code fence — the rest of the file is skipped by the other checks');
    }
  }
}

const files = await markdownFiles();
const diagrams = await checkMermaid(files);
const links = checkLinks(files);
checkAccidentalBlockquotes(files);
checkUnmarkedLists(files);
checkFencesClosed(files);

if (VERBOSE || failures.length === 0) {
  console.log(
    `Checked ${files.length} Markdown files: ${diagrams} Mermaid diagram(s), ` +
    `${links.checked} relative link(s), ${links.anchors} anchor(s).`);
}

if (failures.length > 0) {
  console.error(`\n${failures.length} problem(s) found:\n`);
  for (const f of failures) console.error(`  ${f.file}:${f.line}  [${f.check}] ${f.message}`);
  console.error('');
  process.exit(1);
}

console.log('All documentation checks passed.');
