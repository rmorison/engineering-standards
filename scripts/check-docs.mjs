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
 * Checks 2 through 4 skip fenced code blocks, and check 2 also ignores inline
 * code spans: an example of a defect is not a defect, which is what lets the
 * documentation show what each check catches. Checks 3 and 4 read the raw line,
 * since a leading code span already displaces the marker they look for.
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

/** A fenced-code delimiter: three or more backticks or tildes, plus its info string. */
const FENCE_DELIMITER = /^(`{3,}|~{3,})(.*)$/;

const fileCache = new Map();

/** Files whose headings were consulted to verify an anchor. */
const anchorTargets = new Set();

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
 *
 * Delimiters follow CommonMark rather than "the line starts with three
 * backticks". Three rules earn their place, each because the loose version was
 * wrong about a file in this repository:
 *
 *   - An opening backtick fence's info string may not contain a backtick. This
 *     is what keeps ```` ``` ```` — how prose here quotes a fence — from
 *     reading as an opener. A document about a fence checker is exactly where
 *     that escape appears.
 *   - A closer matches the opener's marker and is at least as long, so a three
 *     backtick line inside a four backtick fence stays content.
 *   - A closer carries no info string, so an opener can never be mistaken for
 *     one. That is what stops a missing closer from inverting every later
 *     region of the file.
 *
 * Returns the lines, the line number of a fence that is never closed, and any
 * line where a fence is opened inside a fence of the same length. Check 5
 * reports both: each one silently redraws where the examples in a file are.
 */
function readMarkdown(file) {
  const cached = fileCache.get(file);
  if (cached) return cached;

  let open = null; // { marker, length, line } while a fence is open
  const nested = [];
  const lines = readFileSync(file, 'utf8')
    .split('\n')
    .map((raw, i) => {
      const match = FENCE_DELIMITER.exec(raw.trim());
      let isDelimiter = false;

      if (match) {
        const [marker, length, info] = [match[1][0], match[1].length, match[2].trim()];
        if (open === null) {
          if (marker !== '`' || !info.includes('`')) {
            open = { marker, length, line: i + 1 };
            isDelimiter = true;
          }
        } else if (marker === open.marker && length >= open.length && info === '') {
          open = null;
          isDelimiter = true;
        } else if (marker === open.marker && length >= open.length) {
          // An opener inside a block it cannot nest in. The author meant to
          // show a fence; the renderer will end the outer block at the next
          // bare delimiter instead, spilling the rest of the example into the
          // document as live Markdown.
          nested.push(i + 1);
        }
      }

      return {
        number: i + 1,
        raw,
        masked: raw.replace(CODE_SPAN, (span) => 'x'.repeat(span.length)),
        // A delimiter belongs to its own block, so an info string like
        // ```mermaid is not prose either.
        fenced: open !== null || isDelimiter,
      };
    });

  const result = { lines, unterminatedFence: open === null ? null : open.line, nested };
  fileCache.set(file, result);
  return result;
}

const ATX_HEADING = /^#{1,6}\s+(.+)$/;

/** Inline link and image syntax, reduced to the text GitHub renders. */
const INLINE_LINK = /!?\[([^\]]*)\]\([^)]*\)/g;
const REFERENCE_LINK = /!?\[([^\]]*)\]\[[^\]]*\]/g;

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
 *
 * Link syntax is reduced to its text first, because GitHub slugs what it
 * renders. `### [Database Standards](./database-standards.md)` is anchored at
 * `#database-standards`; the slugger only deletes characters and never removes
 * a substring, so feeding it the source yields
 * `database-standardsdatabase-standardsmd` — a live anchor reported dead, which
 * is the outcome choosing a real slugger was meant to avoid. Backticks, `**`
 * and `_` need no such treatment: the slugger deletes them without residue.
 */
function headingSlugs(file) {
  const cached = slugCache.get(file);
  if (cached) return cached;

  const slugger = new GithubSlugger();
  const slugs = new Set();
  for (const line of readMarkdown(file).lines) {
    if (line.fenced) continue;
    const heading = ATX_HEADING.exec(line.raw);
    if (!heading) continue;
    const text = heading[1].trim().replace(INLINE_LINK, '$1').replace(REFERENCE_LINK, '$1');
    slugs.add(slugger.slug(text));
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
    for (const line of readMarkdown(file).lines) {
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
        anchorTargets.add(resolved);
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
    for (const line of readMarkdown(file).lines) {
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
    for (const line of readMarkdown(file).lines) {
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
 *
 * The second case is a fence opened inside a fence of the same length, which is
 * how a quoted template breaks: fences do not nest, so the renderer ends the
 * outer block early and the rest of the template lands in the document as live
 * Markdown. `code/python-standards.md` shipped that way, leaking four headings
 * out of a README template. The fix is a longer outer fence.
 *
 * Runs over the anchor targets as well as the checked files. A file in
 * `archive/` or `docs/plans/` is skipped as a link *source*, but its headings
 * are still read to verify anchors pointing into it, so a broken fence there
 * would hide the very headings being looked for.
 */
function checkFencesClosed(files) {
  for (const file of new Set([...files, ...anchorTargets])) {
    const { unterminatedFence, nested } = readMarkdown(file);
    if (unterminatedFence !== null) {
      fail(file, unterminatedFence, 'fence',
        'code fence is never closed — the rest of the file is skipped by the other checks');
    }
    for (const line of nested) {
      fail(file, line, 'fence',
        'fence opened inside a fence of the same length — the outer one ends early; make it longer');
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
    `Checked ${files.length} Markdown files: ${diagrams} Mermaid diagram(s) and ` +
    `${links.checked} relative link(s), ${links.anchors} of them carrying a verified anchor.`);
}

if (failures.length > 0) {
  console.error(`\n${failures.length} problem(s) found:\n`);
  for (const f of failures) console.error(`  ${f.file}:${f.line}  [${f.check}] ${f.message}`);
  console.error('');
  process.exit(1);
}

console.log('All documentation checks passed.');
