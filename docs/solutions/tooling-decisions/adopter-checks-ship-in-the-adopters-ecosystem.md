---
title: A check an adopting project runs ships in that project's ecosystem
date: 2026-09-27
category: tooling-decisions
module: adopter-checks
problem_type: tooling_decision
component: tooling
severity: medium
resolution_type: code_fix
applies_when:
  - A standard asks an adopting project to run a script or check
  - Choosing the language for a new check under scripts/
  - Adding a standard for a new language, such as Go, that needs a check an existing standard already ships
  - Proposing to port this repository's own Node checks to another language
related_components:
  - development_workflow
  - documentation
tags: [adopters, ecosystem, node, python, secret-refs, ci, scripts, decision-record]
---

# A check an adopting project runs ships in that project's ecosystem

## Context

The Secrets rule in `code/python-standards.md` asks a project that commits `secret-refs.env` to check it with a script from this repository. Until #29 that script was `scripts/check-secret-refs.mjs` (deleted by PR #55; `git show 64163ec:scripts/check-secret-refs.mjs` shows its last version, on `main` just before #55), which is Node. A Python project adopting the standard would have had to install Node to run one check. The script was written in Node because this repository's other checks were Node (`scripts/package.json`), not because the check needed anything Node offered: it imported only Node's built-in `fs`, `path` and `url`.

The repository owner rejected that during #29: "I don't want to presume pull Node into a Python or Go project, not a typical combination, even if it's for CI checks or other utilities. Most engineers will try to stay in one, or at most 2, ecosystems (unless it's a monorepo)." #29 gained an item 5 recording the principle, and PR #55 replaced the Node script with `scripts/check_secret_refs.py`, which uses only Python's standard library and runs on Python 3.10 or later.

## Guidance

**Split scripts by who runs them.**

| Who runs it | Language rule | Examples |
|---|---|---|
| An adopting project, on its own files | The project's ecosystem: its language's standard library, a dev dependency from its own package manager, or one static binary that needs no runtime, pinned and checksum-verified | `scripts/check_secret_refs.py`; detect-secrets (a Python dev dependency); gitleaks (one Go binary) |
| Only this repository, on its own content | Whatever fits the job | `scripts/check-docs.mjs`, `scripts/check-template-kit.mjs` |

1. **An adopter-facing check is written in the adopter's language, or is a static binary.** A Python project should not need a second runtime to follow the Python standard. A binary is fetched the way the Python standard fetches gitleaks: at a pinned version, with the release checksum verified (`code/python-standards.md:825-834`), never piped from `curl` into a shell. In an adopter with more than one ecosystem, such as the web application standard's Turborepo with a Next.js frontend and a Python backend (`code/web-application-standards.md:7`), a check ships in the ecosystem of the part it checks. `secret-refs.env` belongs to the Python backend (`code/web-application-standards.md:71`), so the web application standard needs no Node port of the check. The Python standard states this in Core Tools (`code/python-standards.md:50`) and the `code/` index repeats it (`code/README.md:19`). Both lines speak only for Python. This doc records the rule for every standard.
2. **This repository's own checks are exempt, and should stay in Node until there is a reason to move them.** Nobody inherits them. `check-docs.mjs` has a reason to be Node beyond habit: it runs mermaid's own `parse()` (`scripts/check-docs.mjs:240`), so a diagram fails here the way it would fail when GitHub renders it, and it checks anchors with `github-slugger` (`scripts/check-docs.mjs:198`), the library GitHub's own Markdown pipeline uses. Porting it would lose both. Porting either script "for consistency" with the Python port misreads this decision.
3. **The standard owns the rule; a script is one implementation of it.** The reference-file rules are written out as a list in the Secrets section. The script enforces that list, and the standard's own examples are checked against it in this repository's CI (`python scripts/check_secret_refs.py --standard`). If a second language ever needs the same check, write that language's version against the same rules. The fixtures are tables inside the script today (`LINE_FIXTURES`, `FILE_FIXTURES`, `LEAK_FIXTURES` and others in `scripts/check_secret_refs.py`). When a second version exists, move them into a language-neutral data file that every version must pass, so that drift between versions fails a test rather than going unnoticed.
4. **Keep one implementation while one ecosystem uses the rule.** Only the Python standard defines `secret-refs.env` today, and `code/web-application-standards.md` defers to it for the backend. There is no Go standard, so there is no Go port. Add one when a Go standard adopts the rule, not before.
5. **Porting a check changes its behaviour unless the port is proven equal.** Regex classes and string trimming differ between languages. [a-check-must-read-a-file-the-way-its-consumer-does](../best-practices/a-check-must-read-a-file-the-way-its-consumer-does.md) records how the Python port matched the Node original and how that was proven.

## Why This Matters

A standard that needs a second runtime is one that teams skip. Most teams work in one ecosystem, or two outside a monorepo. A Python team told to install Node for one check is likely to leave the check out, and that check guards the promise that `secret-refs.env` holds no secret. The rule cost this repository one port. The Node script was 509 lines. The Python version is 766, including fixtures that pin down where Python's regex classes differ from JavaScript's.

The exemption matters just as much. Without it, the rule reads as "no Node in this repository", and someone ports `check-docs.mjs` to Python, loses mermaid's parser, and trades a check that matches GitHub's renderer for one that does not.

## When to Apply

- Writing a new script that a standard tells adopting projects to copy or run
- Adding a standard for a new language and deciding how its projects run an existing check
- Reviewing a pull request that makes a standard depend on a runtime the adopting project would not otherwise have
- Asked to move `check-docs.mjs` or `check-template-kit.mjs` out of Node. Check first whether a standard now asks adopters to run them. As of this writing, none does

## Examples

**Before #29.** The Python standard's Secrets section named `scripts/check-secret-refs.mjs` as the check for these rules, and this repository's CI ran it with `node scripts/check-secret-refs.mjs --standard`. A Python project that ran the check on its own files needed Node to do it.

**After #29.** The project copies `scripts/check_secret_refs.py` and runs it through the interpreter it already manages (`code/python-standards.md:258`, in the `security` recipe):

```make
@if [ -f secret-refs.env ]; then uv run python scripts/check_secret_refs.py secret-refs.env --config example.env; fi
```

This repository's CI runs the same file on Python 3.10, the oldest version it supports, so a construct that needs a newer Python fails here, not in an adopting project (`.github/workflows/docs.yml`, job `check-secret-refs`). The Node checks run in their own jobs, unchanged.

**Tools already follow the rule.** The Python standard's secret scanners were already in-ecosystem: detect-secrets installs as a Python dev dependency, and gitleaks, the sanctioned alternative, is a single Go binary with no runtime. The Node script was the only exception.

## Related

- #29, item 5: the ticket statement of this principle
- PR #55: the port and the wiring into `make security`
- [a-check-must-read-a-file-the-way-its-consumer-does](../best-practices/a-check-must-read-a-file-the-way-its-consumer-does.md): what a port must preserve
