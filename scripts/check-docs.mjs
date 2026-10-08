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
 *   7. The gitleaks version and hashes are written only in
 *      scripts/install-gitleaks.sh. (6 was retired in #31; see below.)
 *   8. A code block marked as a copy of a standard's block matches it.
 *
 * Checks 2 through 4 skip fenced code blocks, and check 2 also ignores inline
 * code spans: an example of a defect is not a defect, which is what lets the
 * documentation show what each check catches. Checks 3 and 4 read the raw line,
 * since a leading code span already displaces the marker they look for.
 *
 * Leaked absolute home-directory paths were check 6 here until #31. That rule
 * now lives in `.gitleaks.toml`, which scans every tracked file rather than
 * Markdown only, and runs in `.github/workflows/leaks.yml` on every change.
 *
 * Usage:  node scripts/check-docs.mjs [--verbose]
 * Exits non-zero if any check fails.
 */

import { execFileSync } from 'node:child_process';
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

/** Every Markdown file in the repository, minus SKIP_ANYWHERE and SKIP_PATHS. */
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
        delimiter: isDelimiter,
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

/**
 * Check 7 — the gitleaks pins live in one place.
 *
 * `scripts/install-gitleaks.sh` is the only file that writes the gitleaks
 * version and the SHA-256 of each release tarball (#70). A second copy, in a
 * workflow, a standard's install text or another script, drifts the first time
 * an upgrade misses it. So no tracked file outside the script and the history
 * directories may hold a 64-hex-digit literal or a gitleaks tarball name with a
 * version in it. No other 64-hex literal exists outside those directories, so
 * the rule needs no allowlist; a future unrelated one gets a named exemption
 * here.
 *
 * Three install forms pin a version with no hash at all, and they fail too: a
 * gitleaks release download URL, a `go install` of the gitleaks module at a
 * version, and a rev on or within three lines after a pre-commit repo line
 * naming the gitleaks repository. A version in prose is not read: what is left
 * of it is dated evidence of what was run. (This comment avoids the literal
 * forms, because this file is checked too.)
 *
 * Unlike checks 1 to 5, this reads every tracked file, not only Markdown, and
 * .github/workflows/docs.yml runs it when a script or workflow changes. A stale
 * copy of an old hash fails as well as a copy of a current one.
 *
 * The pins are read by running the script with --pins, so the check sees what
 * sh sees. A literal equal to a current pin is named by its platform. Any other
 * is reported without being printed: it could be a secret, and this log is
 * public.
 */
const PIN_SCRIPT = 'scripts/install-gitleaks.sh';
const PIN_HISTORY = ['docs/plans/', 'docs/solutions/', 'agent-transcripts/', 'archive/'];

function checkGitleaksPins() {
  const script = join(REPO_ROOT, PIN_SCRIPT);
  let pins;
  try {
    pins = execFileSync('sh', [script, '--pins'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  } catch {
    fail(script, 1, 'gitleaks-pin', '`sh install-gitleaks.sh --pins` failed, so the pins cannot be read');
    return;
  }
  const platformOf = new Map();
  for (const line of pins.split('\n')) {
    const m = /^((?:linux|darwin)_(?:x64|arm64)) ([0-9a-f]{64})$/.exec(line);
    if (m) platformOf.set(m[2], m[1]);
  }
  if (platformOf.size !== 4 || !/^version \d+\.\d+\.\d+$/m.test(pins)) {
    fail(script, 1, 'gitleaks-pin', '`--pins` did not print a version and four distinct platform hashes');
    return;
  }

  const HEX = /(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])/g;
  const TARBALL = /gitleaks_\d+\.\d+\.\d+_/;
  const DOWNLOAD = /gitleaks\/gitleaks\/releases\/download\//;
  const GO_INSTALL = /\/gitleaks\/v\d+@/;
  const HOOK_REPO = /repo:\s*\S*gitleaks\/gitleaks\b/;
  const REV = /\brev:/;
  const tracked = execFileSync('git', ['ls-files', '-z'], { cwd: REPO_ROOT, encoding: 'utf8' })
    .split('\0').filter(Boolean);
  for (const path of tracked) {
    if (path === PIN_SCRIPT || PIN_HISTORY.some(dir => path.startsWith(dir))) continue;
    const file = join(REPO_ROOT, path);
    let text;
    try { text = readFileSync(file, 'utf8'); } catch { continue; } // deleted in the working tree
    if (text.includes('\0')) continue; // binary
    const lines = text.split('\n');
    lines.forEach((line, i) => {
      for (const [hex] of line.matchAll(HEX)) {
        const platform = platformOf.get(hex.toLowerCase());
        fail(file, i + 1, 'gitleaks-pin', platform
          ? `restates the ${platform} gitleaks hash, which belongs only in ${PIN_SCRIPT}`
          : `holds a 64-hex-digit literal (not printed) that is no current gitleaks pin: a stale ` +
            `gitleaks hash belongs only in ${PIN_SCRIPT}, and an unrelated one needs an exemption in check 7`);
      }
      if (TARBALL.test(line)) {
        fail(file, i + 1, 'gitleaks-pin',
          `names a gitleaks tarball with a version in it; the version belongs only in ${PIN_SCRIPT}`);
      }
      if (DOWNLOAD.test(line) || GO_INSTALL.test(line)) {
        fail(file, i + 1, 'gitleaks-pin',
          `installs gitleaks at a version without the pinned hash; install it with ${PIN_SCRIPT}`);
      }
      if (HOOK_REPO.test(line) && lines.slice(i, i + 4).some(l => REV.test(l))) {
        fail(file, i + 1, 'gitleaks-pin',
          `pins a gitleaks pre-commit hook by rev; the leak gate's repo: local entry runs the binary ${PIN_SCRIPT} installs`);
      }
    });
  }
}

/**
 * Check 8 — a marked copy of a standard's code block matches its source.
 *
 * QUICKSTART.md repeats commands, hook installers and settings JSON that a
 * standard owns, so a reader can copy them in one place; the agent-team
 * plugin's README repeats its install commands. A copy drifts the
 * first time the standard changes and the copy doesn't. So each copy carries a
 * marker on the line before its fence, naming the source file and a string that
 * only one fenced block there contains:
 *
 *   <!-- copy-of: process/repository-standards.md | hooks)/pre-commit" -->
 *
 * The copy's info string and content, each block taken without the indentation
 * of its own fence, must equal the source block's byte for byte.
 *
 *   <!-- copy-of-line: process/repository-standards.md | leak-gate.sh history -->
 *
 * copies one line of a source block instead. The copy must be that one line,
 * without the line's trailing `# comment`: zsh, the default macOS shell, reads a
 * pasted `#` as a command by default. Everything before the comment must be
 * identical.
 *
 * A marker with no fence after it, a source that is missing, and a string that
 * matches no block, or more than one, fail too, so a renamed section cannot
 * turn the check off quietly.
 *
 * A copy without a marker would go unchecked. So in the files listed in
 * MARKED_FILES, every fenced block must carry a marker: a copy-of marker, or
 * `<!-- own -->` for text no standard holds. A new block then has to say which
 * it is, and review sees the choice.
 */
const COPY_MARKER = /^\s*<!-- copy-of(-line)?: (\S+) \| (.+?) -->\s*$/;
const OWN_MARKER = /^\s*<!-- own -->\s*$/;
const MARKED_FILES = new Set(['QUICKSTART.md', 'plugins/agent-team/README.md']);

/**
 * Every fenced block in a file: its info string, its content lines with the
 * fence's own indentation removed, and the line number of its opener. Which
 * lines are fenced comes from readMarkdown, so this agrees with checks 2 to 5.
 */
const blocksCache = new Map();

function fencedBlocks(file) {
  if (blocksCache.has(file)) return blocksCache.get(file);
  const blocks = [];
  let open = null;
  for (const { raw, number, delimiter } of readMarkdown(file).lines) {
    const indent = raw.length - raw.trimStart().length;
    if (delimiter && open === null) {
      open = { info: FENCE_DELIMITER.exec(raw.trim())[2].trim(), indent, line: number, content: [] };
      blocks.push(open);
    } else if (delimiter) {
      open = null;
    } else if (open !== null) {
      open.content.push(raw.slice(Math.min(open.indent, indent)));
    }
  }
  blocksCache.set(file, blocks);
  return blocks;
}

function checkMarkedCopies(files) {
  let copies = 0;
  for (const file of files) {
    const { lines } = readMarkdown(file);
    if (MARKED_FILES.has(relative(REPO_ROOT, file))) {
      for (const block of fencedBlocks(file)) {
        const before = lines[block.line - 2]?.raw ?? '';
        if (!COPY_MARKER.test(before) && !OWN_MARKER.test(before)) {
          fail(file, block.line, 'copy',
            'code block has no marker: put <!-- copy-of: <file> | <string> --> or <!-- own --> on the line before it');
        }
      }
    }
    lines.forEach(({ raw, fenced, number }) => {
      if (fenced) return;
      const m = COPY_MARKER.exec(raw);
      if (!m) return;
      const [, lineMode, sourcePath, needle] = m;
      const copy = fencedBlocks(file).find(b => b.line === number + 1);
      if (!copy) {
        fail(file, number, 'copy', 'copy-of marker is not on the line before a code fence');
        return;
      }
      const source = join(REPO_ROOT, sourcePath);
      if (!existsSync(source)) {
        fail(file, number, 'copy', `copy-of names ${sourcePath}, which does not exist`);
        return;
      }
      const found = fencedBlocks(source).filter(b => b.content.some(l => l.includes(needle)));
      if (found.length !== 1) {
        fail(file, number, 'copy',
          `\`${needle}\` is in ${found.length} code blocks of ${sourcePath}; it must name exactly one`);
        return;
      }
      const [src] = found;
      copies++;
      if (lineMode) {
        const srcLine = src.content.find(l => l.includes(needle)).replace(/\s+#.*$/, '');
        if (copy.content.length !== 1 || copy.content[0] !== srcLine) {
          fail(file, copy.line, 'copy',
            `differs from its source line at ${sourcePath}:${src.line}; copy that line without its comment`);
        }
      } else if (copy.info !== src.info || copy.content.join('\n') !== src.content.join('\n')) {
        fail(file, copy.line, 'copy',
          `differs from its source block at ${sourcePath}:${src.line}; copy the block again`);
      }
    });
  }
  return copies;
}

const files = await markdownFiles();
const diagrams = await checkMermaid(files);
const links = checkLinks(files);
checkAccidentalBlockquotes(files);
checkUnmarkedLists(files);
checkFencesClosed(files);
checkGitleaksPins();
const copies = checkMarkedCopies(files);

if (VERBOSE || failures.length === 0) {
  console.log(
    `Checked ${files.length} Markdown files: ${diagrams} Mermaid diagram(s) and ` +
    `${links.checked} relative link(s), ${links.anchors} of them carrying a verified anchor, ` +
    `and ${copies} marked copy block(s).`);
}

if (failures.length > 0) {
  console.error(`\n${failures.length} problem(s) found:\n`);
  for (const f of failures) console.error(`  ${f.file}:${f.line}  [${f.check}] ${f.message}`);
  console.error('');
  process.exit(1);
}

console.log('All documentation checks passed.');
