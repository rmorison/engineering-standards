# AI Artifacts Layer

This directory defines **how Claude Code operates** to produce code that meets
the engineering standards defined in this repository. The standards in `process/`
and `code/` define *what* good code looks like; the artifacts here ensure Claude
Code actively follows those standards rather than passively referencing them.

## Layer Model

The AI artifacts are organized in four layers, ordered by context cost:

### Layer 1 — Rules (always loaded)

**Location:** `ai/claude-code/rules/`

Compact markdown files auto-loaded at session start. They act as **pointers**
to the full standards — short enough to stay in context permanently without
bloating the window. Each file stays under 150 lines.

| File | Purpose |
|------|---------|
| `engineering-standards.md` | References to feature workflow, documentation, git, and code quality principles |
| `sdlc-workflow.md` | Behavioral guardrails: read before changing, plan before implementing, validate after each change |

### Layer 2 — Skills (on demand)

**Location:** `templates/.claude/skills/`

Skills load full standards content **only when invoked**, keeping the main
context clean the rest of the time. They reference standards docs via GitHub
raw URLs so they work in any project without submodules.

| Skill | Invocation | Loads | Purpose |
|-------|-----------|-------|---------|
| spec | `/spec` | documentation-standards.md | Draft a spec in the correct format |
| plan | `/plan` | project-planning-standards.md | Break work into estimated, sequenced tasks |
| review | `/review` | feature-development-workflow.md + code standards | Review code against standards |

### Layer 3 — Agents (specialized subagents)

**Location:** `templates/.claude/agents/`

Subagents handle focused tasks with their own context and tool access.

| Agent | Type | Purpose |
|-------|------|---------|
| `code-reviewer.md` | Explore (read-only) | Standards-aware code review — checks separation of concerns, module boundaries |
| `spec-writer.md` | General-purpose | Interviews user about a feature, produces a spec in the correct format |

### Layer 4 — Hooks (deterministic, zero context cost)

**Location:** `templates/.claude/hooks/`

Shell or Python scripts that run automatically on tool-use events. They enforce
non-negotiable rules without consuming context window. Written in Python via
`uv run` for portability; Bash only for single-line operations.

The template provides example hooks showing the pattern — projects replace the
example logic with their own rules.

## How to Use

### For this repository

The `ai/claude-code/rules/` files are loaded automatically when working in this
repo. They point Claude Code at the standards docs in `process/` and `code/`.

### For new projects

Copy `templates/.claude/` into your project root as `.claude/` and customize:

1. Edit `settings.json` to match your project's toolchain
2. Keep the skills as-is (they reference standards via URL)
3. Customize agent definitions for your project's architecture
4. Replace example hooks with your project-specific rules
5. Copy `templates/CLAUDE.md` to your project root and fill in the
   project-specific sections

## Design Principles

- **Context is expensive** — only load what's needed, when it's needed
- **Standards are enforced, not just referenced** — skills and hooks make
  standards actionable
- **Templates over copies** — skills point to canonical standards via URL;
  no content duplication to keep in sync
- **Projects customize, templates provide structure** — the template layer
  gives a starting point; each project extends it
