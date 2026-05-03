---
title: "refactor: Adopt 6-layer AI architecture with compound-engineering as canonical realization"
type: refactor
status: active
date: 2026-05-03
origin: https://github.com/rmorison/engineering-standards/issues/22
prior_plan: docs/plans/2026-05-03-001-feat-compound-engineering-integration-plan.md
---

# refactor: Adopt 6-layer AI architecture with compound-engineering as canonical realization

## Overview

This plan implements the architectural redesign described in rescoped issue #22. The repo currently ships a **4-layer AI architecture** (Rules / Skills / Agents / Hooks) introduced via PRs #16/#19/#21 (~5 weeks ago). Under that model, `ai/claude-code/rules/*.md` are Layer 1, `templates/.claude/skills/{spec,plan,review}/` are Layer 2, `templates/.claude/agents/{code-reviewer,spec-writer}.md` are Layer 3, and `templates/.claude/hooks/` are Layer 4. The 4-layer was a useful first sketch but a tactical CE-integration attempt (the abandoned prior plan, three rounds of multi-persona doc-review) revealed that CE doesn't fit it cleanly — CE has structural patterns the 4-layer doesn't name (References, Compound/Learnings) and the existing layers' definitions force category errors (CE personas aren't standalone Layer-3 agents).

This plan evolves the architecture to a **6-layer model**:

1. **Rules** — always-loaded session context (compact pointers, behavioral guardrails)
2. **Workflow Skills** — composable on-demand workflows that orchestrate multi-step processes
3. **Persona Agents** — specialized review/analysis perspectives, dispatched by skills (or directly invocable for simple cases)
4. **References** — skill-loaded progressive context that grows as workflow depth grows
5. **Compound / Learnings** — institutional knowledge accumulation that feeds forward into future work
6. **Hooks** — deterministic non-AI enforcement at zero context cost

The architecture is the **abstraction**; **compound-engineering** (CE) is named as one **canonical realization**. Layer definitions are vendor-neutral so other LLM-engineering toolkits — present or future — can fit the same slots. The vendor-neutral templates' skills/agents stay in place as Layer 2/3 baseline implementations for projects that don't run CE; CE provides deeper Layer 2/3 implementations for projects that install the plugin. Layer 5 (Compound) is new and currently realized only by CE; Layers 1, 4, and 6 are owned by the standards repo and are not vendor-coupled.

The architectural artifacts (ADR, `ai/claude-code/README.md`) are written with **publication-quality framing**: standalone, vendor-neutral architectural description suitable for the repo's role as an encompassing standard for future work and as foundation for a potential follow-on technical article (*"Abstracting the Every Compound Engineering Model for LLM Based Engineering"*).

---

## Problem Frame

The repo's identity is "lightweight standards anyone can adopt" with branches for different project types. AI-tooling guidance is part of the standards surface. The current 4-layer model has three concrete inadequacies once compared to a developed system like CE:

1. **Layer 3 collapses two distinct shapes**: the 4-layer's Layer 3 def assumes "specialized subagents directly invoked." CE's persona reviewers are skill-internal prompt templates dispatched by orchestrators (`ce-doc-review`, `ce-code-review`); they don't run standalone. The abandoned plan's attempt to call CE skills "Layer 3" was a category error the layer model invited.
2. **Layer 2 conflates lazy-and-minimal with lazy-and-deep**: the templates' skills are 30–60 lines and load standards via URL. CE skills are 800–1500 lines plus reference subtrees. Both are lazy-loaded, but the load profiles differ by orders of magnitude. Calling them the same Layer 2 paper-thinly hides a real depth tradeoff.
3. **References and Compound/Learnings are unnamed structural patterns**: CE skills ship `references/*.md` subtrees that progressively load context during execution. CE captures learnings via `ce-compound` + `docs/solutions/`. The 4-layer model has no slot for either — the patterns are real but inarticulable in the existing taxonomy.

The fix is not to "supersede" the 4-layer (the abandoned plan's first framing) or "specialize within it" (the abandoned plan's second framing). The fix is to evolve the architecture itself to absorb the patterns CE has surfaced — keeping it general enough that the abstraction stays vendor-neutral while CE serves as the canonical realization adopters point to.

The work is also positioned for **publication**: the user is considering a follow-on technical article abstracting CE's model. That requires the architecture artifacts to be readable by external readers without rmorison context.

---

## Requirements Trace

The requirements derive from the rescoped issue's acceptance criteria plus operational findings carried forward from the abandoned prior plan.

- **R1.** ADR establishes the 6-layer architecture, articulates each layer's definition, names CE as canonical realization, and frames the architecture-as-abstraction / CE-as-realization relationship.
- **R2.** `ai/claude-code/README.md` rewrites as the canonical 6-layer description with publication-quality framing — readable as standalone architectural description.
- **R3.** `ai/CLAUDE.md` reflects the 6-layer architecture (CE-aware path mappings, branch-naming carve-out, Phase 0 = brainstorm declaration where CE is in use).
- **R4.** `ai/claude-code/rules/engineering-standards.md` and `ai/claude-code/rules/sdlc-workflow.md` content is CE-aware while staying compact-pointer in shape (Layer 1's <150-line discipline preserved). Two-mode policy lives in U5 (integration doc) and U3 (`ai/CLAUDE.md`), not in Layer 1.
- **R5.** Integration process doc `process/compound-engineering-integration.md` describes CE's realization of each of the 6 layers and the operational details: artifact path mapping, issue-tracking modes, branch-naming reconciliation, AI-review **discipline** (not enforced gate), CE skill ↔ standards doc cross-reference. Self-contained — load-bearing content inlined; no public reader needs rmorison or books-ops access.
- **R6.** README's "AI / Claude Code Integration" section rewrites to reflect the 6-layer model. Adds CE as canonical realization. Keeps the "Context is expensive" principle (it transfers cleanly to the new model).
- **R7.** `templates/CLAUDE.md` updated with a brief "AI Architecture" section reflecting the 6-layer model and a CE-aware note in "Plan Before Implement."
- **R8.** Cross-references added to: `process/feature-development-workflow.md`, `process/issue-tracking.md`, `process/project-planning-standards.md`, `process/documentation-standards.md`, `process/git-branching-strategy.md`. The branching standard also gets a CE carve-out for `lfg`/`ce-work` topic-style branches and a Layer-3-discipline note in branch protection.
- **R9.** Three prior `ai/*.md` proposals (`adoption-roadmap.md`, `agent-native-improvements.md`, `top-3-enhancements.md`) relocated to top-level `archive/` with banners pointing at the new ADR. These are the genuine path-not-taken: they proposed building agent-native abstractions ourselves rather than adopting a developed toolkit.
- **R10.** No team-scale standards weakened — every cross-reference is additive ("when CE is in use..."), never subtractive.
- **R11.** All AI-architecture artifacts written with publication-quality framing — vendor-neutral layer definitions, CE as one realization, no rmorison-specific assumptions in top-level docs.
- **R12.** Layer definitions are general enough that other LLM-engineering toolkits (or hand-rolled implementations) could fit the same slots. The architecture description should answer "what would Layer 2 look like in Cursor / Aider / a hand-rolled system" without contradiction.
- **R13.** Operational findings from the abandoned prior plan carried forward where still valid:
   - Books-ops privacy resolved by inlining all load-bearing content; books-ops named only as "real-world deployment example"
   - AI-review framed as **discipline**, not an enforced merge gate; failure modes named explicitly (cross-PR scope drift, self-grading loops, product-positioning regressions, same-intent author/reviewer)
   - Provenance clause for artifact paths: first-skill-touched-the-file wins; explicit `provenance:` frontmatter override
   - `docs/brainstorms/` declared as Phase 0 / discovery artifact for the feature workflow when CE is in use (partially addresses #12)
   - Branch-naming carve-out for `lfg` / `ce-work` autonomous flows (topic-style accepted when no parent issue)
   - Solo carve-outs from existing standards (cite — not invent — the existing `process/issue-tracking.md` and `process/project-planning-standards.md` solo escape hatches)

---

## Scope Boundaries

- **The technical article itself** is a separate publishing track. This plan produces the architectural artifacts the article would draw on; the article is not in scope.
- **Forking compound-engineering** or maintaining its skill content here.
- **Tracking CE's version updates inside the standards** — the integration doc describes CE-skill behavior alongside names, so name churn within 3.x is a one-row table edit. Re-evaluate at CE 4.x.
- **Rewrites of `code/python-standards.md`, `code/database-standards.md`, `code/web-application-standards.md`** to add CE-skill cross-references. Surface in a follow-up only if real use shows a gap.
- **CE-mode enforcement hooks** (e.g., a hook that warns if `/plan` is invoked in a CE project). The 4-layer's example hooks remain in place as Layer 6 baseline; project-specific enforcement can be a follow-up.
- **Project-specific wrapper skills** (e.g., `templates/.claude/skills/ce-plan-wrapper/` that pre-fills repo conventions). Adds vendor coupling at the template level; defer until concrete need.
- **Layer 5 (Compound) tooling stubs** in templates. The integration doc and ADR describe Layer 5; if a concrete `templates/.claude/learnings/` or similar artifact is needed, that is a follow-up driven by first compound output.
- **Migration guide for hypothetical external adopters** of the prior 4-layer model. Repo has no external-adopter signals; if real adopters surface concerns post-merge, address in a follow-up.

### Deferred to Follow-Up Work

- Branch rename from `22-integrate-compound-engineering-practices-with-the-standards-repo` to a name reflecting the new title (e.g., `22-refactor-ai-architecture-6-layer-model`). Optional cosmetic; current slug is functional and a rename can happen at any point with `git branch -m`. Decision deferred to the implementer.
- Retroactive comments on issues #16 / #19 / #21 indicating the architecture has evolved (not superseded — the 4-layer principle is preserved). Cheap to add post-merge if the issue tracker becomes a discovery surface.

---

## Context & Research

### Relevant Code and Patterns

- `ai/claude-code/README.md` (88 lines) — current 4-layer description. The Layer table and "Key principle: context is expensive" framing transfer cleanly to the 6-layer; structural rewrite needed for the additional layers and refined definitions.
- `ai/claude-code/rules/engineering-standards.md` (59 lines) — Layer 1 content; hardcoded `docs/` tree (lines 27–37) and unqualified branch-naming (line 44) need CE-aware updates while staying compact-pointer in shape.
- `ai/claude-code/rules/sdlc-workflow.md` (39 lines) — "Plan Before Implementing" (lines 13–18) contradicts CE's `lfg` autonomous flow; needs a one-line addendum pointing at the integration doc, not a multi-mode rewrite.
- `ai/CLAUDE.md` (lines ~22–66) — Quick Reference Documentation Structure, Feature Development Workflow numbered list, branch-naming rule. Needs two-mode framing inline (vendor-neutral baseline + CE-mode addendum) for each block.
- `templates/CLAUDE.md` (62 lines) — project template. "Plan Before Implement" + "Standards References" sections accept CE-aware additions; new "AI Architecture" section reflects 6-layer model.
- `README.md` (lines 96–117) — current "AI / Claude Code Integration" section describes 4-layer. Rewrite to describe 6-layer with CE as canonical realization.
- `process/feature-development-workflow.md` Phase 1 (lines 40–70) — seam where Phase 0 (CE brainstorm) attaches.
- `process/issue-tracking.md` lines 359–373 — existing solo carve-outs ("<3 issues: just use labels", "<1 month: might not need epic structure"). Cite, don't invent.
- `process/project-planning-standards.md` line 86 — existing solo carve-out for individual estimation.
- `process/git-branching-strategy.md` lines 287–291 — "❌ Branches Without Issues" anti-pattern needs a `lfg`/`ce-work` carve-out. Lines 322–331 — branch protection block where AI-review discipline cross-ref attaches.
- `process/documentation-standards.md` line 125 — "each `docs/` subdirectory should have a `README.md`."
- `templates/.claude/skills/{spec,plan,review}/SKILL.md` — vendor-neutral Layer 2 baseline. **Stays in place** (not archived).
- `templates/.claude/agents/{code-reviewer,spec-writer}.md` — vendor-neutral Layer 3 baseline. **Stays in place** (not archived).
- `templates/.claude/hooks/`, `templates/.claude/settings.json` — Layer 6 baseline + config. Stay in place; no changes needed.

### CE structure (verified against `~/.claude/plugins/cache/compound-engineering-plugin/3.1.0/`)

- **Skills**: ~30 skills in `skills/ce-*/` and `skills/lfg/` — slash-commands implementing workflow orchestrators. Each skill has a `SKILL.md` plus typically a `references/` subtree.
- **Agents**: ~50 agents in `agents/ce-*-reviewer.agent.md` etc. — persona prompt templates dispatched by skills (rarely invoked standalone).
- **References**: `skills/<name>/references/*.md` — progressive context loaded during skill execution.
- **Compound**: `ce-compound`, `ce-compound-refresh`, plus `docs/solutions/` artifact pattern.
- **Layer 1 / Layer 4**: CE doesn't ship these — the standards repo's `ai/claude-code/rules/` and `templates/.claude/hooks/` retain ownership.

### Institutional Learnings

- The abandoned prior plan (`docs/plans/2026-05-03-001-feat-compound-engineering-integration-plan.md`, status: abandoned) documents three rounds of doc-review iteration. Operational findings preserved as input; architectural framing was wrong. Treat the abandoned plan's R-IDs and U-IDs as void; this plan starts fresh.
- Three rounds of multi-persona review converged on the same insight: any framing that forced CE to fit the 4-layer broke down. The 6-layer evolution is the framing the iteration arrived at.
- `docs/solutions/` doesn't exist yet in this repo — Layer 5 (Compound) is described in the architecture but doesn't yet have realized output. First compound output will populate it.

### External References

- Compound-engineering plugin: https://github.com/EveryInc/compound-engineering-plugin (v3.1.0)
- Every.to agent-native foundation: https://every.to/guides/agent-native (informed both the 4-layer design and CE itself)
- Books-ops working example: private rmorison repo at `/home/rod/Projects/github.com/rmorison/books-ops` — informed the integration doc's wording during real use of the brainstorm → plan → ce-doc-review → lfg pipeline. Not a doc reference for content; the integration doc inlines its own load-bearing material.

---

## Key Technical Decisions

- **Architecture-as-abstraction, CE-as-canonical-realization** (R1, R11, R12). The 6-layer model is described in vendor-neutral terms. CE is named as one realization adopters can install. The vendor-neutral baseline (templates' skills/agents, standards' rules/hooks) is sufficient for projects that don't run CE. Rationale: preserves the repo's "encompassing standard" identity while honestly naming CE's role; supports the publication-quality framing without coupling the architecture description to one vendor.

- **Layer 1 stays compact-pointer** (R4). The Layer 1 rule files get one-line CE-aware additions ("when CE is in use, see `process/compound-engineering-integration.md` for path/branch/workflow conventions") rather than two-mode policy inline. Multi-mode policy lives in `ai/CLAUDE.md` (R3) and the integration doc (R5). Rationale: Layer 1's <150-line discipline is the principle that makes always-loaded context affordable; inlining two-mode policy violates the principle even if numerically under 150 lines.

- **Vendor-neutral Layer 2/3 baselines stay in place** (R10, R12). `templates/.claude/skills/{spec,plan,review}/` and `templates/.claude/agents/{code-reviewer,spec-writer}.md` are not archived. They are the Layer 2 / Layer 3 implementations for projects that don't install CE. CE provides deeper Layer 2/3 implementations when present. Rationale: archiving them would couple the architecture to CE; the layering's vendor-neutrality depends on having a baseline that exists without CE.

- **Layer 5 (Compound/Learnings) is new and currently CE-only**. The architecture describes Compound as a layer with one canonical realization (CE's `ce-compound` + `docs/solutions/`). Non-CE adopters have no realized Layer 5; the layer's description names what would fill it (learning docs, retrospective notes, postmortem repository) so adopters can populate it with hand-rolled implementations if they choose. Rationale: capturing Compound as a layer is the architectural insight CE surfaced; not naming it just because non-CE realizations are thin would lose the insight.

- **AI-review as discipline, not enforced gate** (R5, R13). The integration doc names this explicitly: there is no CI check, branch-protection automation, or PR template that enforces "no unresolved P0/P1 findings." The discipline names what's checked (`ce-code-review`, `ce-doc-review`, self-review against acceptance criteria) and the failure modes the discipline does not catch (cross-PR scope drift, self-grading loops, product-positioning regressions, same-intent author/reviewer). Under the 6-layer model, CE persona reviewers are Layer 3 (skill-internal personas dispatched by `ce-doc-review` and `ce-code-review` skills); the *discipline* is a pattern of using Layer 2 skills to consume Layer 3 personas.

- **Provenance clause for artifact paths** (R5, R13). When a CE skill produces an artifact, CE paths and conventions win; standards paths and conventions own human-authored artifacts and ADRs. Edge cases: (a) **first-skill-touched-the-file wins** by default; (b) **explicit reclassification** is allowed via a one-line `provenance:` frontmatter note when the default rule produces the wrong answer. The default is unverifiable from filesystem state alone, so the frontmatter override is the load-bearing escape hatch.

- **Self-contained integration doc** (R5, R13). All load-bearing content (Documentation Paths table, Review Discipline, Ticket Policy block) is inlined directly into `process/compound-engineering-integration.md`. Books-ops is named once in a "Real-world deployment example" footer, qualified as private. No public reader needs rmorison or books-ops access to apply the integration doc end-to-end.

- **Single-PR scope** (~500–700 lines / ~12–14 files). Rationale: artifacts cross-reference each other (ADR ↔ `ai/claude-code/README.md` ↔ integration doc ↔ `ai/CLAUDE.md` ↔ rules/templates/README); splitting forces stub artifacts. Closer to standards' 200-400 target than the abandoned plan's ~900–1100. Split is available if review surfaces seams (U1+U2 first; everything else follows).

- **Publication-quality framing** (R11). Architectural artifacts (ADR in U1, `ai/claude-code/README.md` in U2) are written so a reader without rmorison context can understand the architecture standalone. Layer definitions don't reference rmorison projects. CE is named as a realization, not as the only realization. The framing supports a follow-on technical article without pre-committing to it.

---

## Open Questions

### Resolved During Planning

- 6-layer model adopted (heavy morph). The 4-layer was a useful first sketch; the 6-layer is the evolution.
- CE is canonical realization; vendor-neutral baselines stay in place. Coexistence is real; vendor-neutrality is preserved by the layering itself.
- Publication-quality framing is required. Top-level architectural docs must be readable standalone.
- Operational findings from the abandoned prior plan carry forward (R13 enumerates).
- Layer 1 stays compact-pointer; CE-mode policy lives elsewhere.
- AI-review is discipline, not enforced gate.

### Deferred to Implementation

- **Branch rename**: optional cosmetic. Current branch slug works; the implementer can rename mid-PR with `git branch -m` and `git push -u origin <new-name>` if desired. The plan does not require it.
- **Exact wording of layer definitions** in `ai/claude-code/README.md`. Publication-quality requires careful drafting; the plan specifies the structural shape but not the exact prose. Implementer drafts; ce-doc-review or self-review verifies.
- **Layer 5 stub in templates**: should `templates/.claude/learnings/` exist as a stub directory pointing at CE's `ce-compound` workflow, or wait until first compound output? Default: skip the stub (no compound output yet to organize); revisit when first `ce-compound` invocation produces a real `docs/solutions/` entry.
- **Issue #12 closure**: R13 carries forward Phase 0 = brainstorm declaration for CE-mode adopters. Verify #12's actual acceptance language before closing — if it requires Phase 0 for non-CE adopters too, leave it open and capture as follow-up.
- **Retroactive comments on PRs #16/#19/#21**: optional. The architecture has evolved, not superseded; the principle ("context is expensive") is preserved. A one-line comment on each pointing at this PR is cheap if discoverability becomes a concern post-merge.
- **Archive directory naming for the README within `archive/`**: whether `archive/README.md` is needed or whether per-file banners are sufficient. Default: include `archive/README.md` since two narratives (the path-not-taken proposals, plus future archive entries) benefit from a directory-level explainer.

---

## High-Level Technical Design

The architecture has six layers ordered by context-cost and invocation pattern. This sketch communicates the shape the artifacts will describe; it is directional guidance for review, not implementation specification.

```
┌──────────────────────────────────────────────────────────────────────┐
│  6-Layer AI Architecture                                             │
│  (abstraction; CE = canonical realization)                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Layer 1: Rules         always-loaded session context                │
│  ─────────────          (compact pointers; behavioral guardrails)    │
│  ai/claude-code/rules/*.md         (standards repo owns)             │
│                                                                      │
│  Layer 2: Workflow Skills    on-demand orchestrators                 │
│  ────────────────────────    (compose into pipelines)                │
│  templates/.claude/skills/   ←  vendor-neutral baseline              │
│  CE skills (/ce-plan etc.)   ←  canonical realization                │
│                                                                      │
│  Layer 3: Persona Agents     skill-orchestrated personas             │
│  ───────────────────────     (or directly invocable for simple)      │
│  templates/.claude/agents/   ←  vendor-neutral baseline              │
│  CE persona reviewers        ←  canonical realization                │
│                                                                      │
│  Layer 4: References         skill-loaded progressive context        │
│  ───────────────────         (loaded during skill execution)         │
│  CE skills' references/      ←  canonical realization                │
│  (no vendor-neutral baseline yet — described in architecture)        │
│                                                                      │
│  Layer 5: Compound /          institutional knowledge accumulation   │
│           Learnings           (feeds forward into future work)       │
│  ───────────────────          (closes the learning loop)             │
│  CE: docs/solutions/ +        ←  canonical realization               │
│  ce-compound, ce-compound-refresh                                    │
│  (no vendor-neutral baseline yet — described in architecture)        │
│                                                                      │
│  Layer 6: Hooks              deterministic non-AI enforcement        │
│  ──────────────              (zero context cost)                     │
│  templates/.claude/hooks/    (standards repo owns)                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

Pipelines compose Layer 2 skills:
  brainstorm ──▶ plan ──▶ work ──▶ doc-review ──▶ code-review ──▶ compound
                  │         │           │              │
                  ▼         ▼           ▼              ▼
              [Layer 4]  [Layer 4]  [Layer 3       [Layer 3
              references references  personas]      personas]
                                         │              │
                                         └──────────────┴──▶ [Layer 5]
                                                              compound
```

**Reading the model**: Layers are ordered by context-cost (Layer 1 always-loaded → Layer 6 zero-context). Each layer's slot is **independent** — a project can fill Layers 1, 4, 6 from the standards repo while filling Layers 2, 3, 5 from CE; or fill all six from CE; or fill 1, 2, 3, 6 from vendor-neutral templates with no Layer 4 or 5; etc.

**The principle each layer specializes**:
- Layer 1: persistence (load once per session, every session)
- Layer 2: composability (workflows compose into pipelines)
- Layer 3: perspective (multiple expertises analyze the same artifact)
- Layer 4: progressivity (context grows as workflow depth grows, not at invocation)
- Layer 5: compounding (institutional knowledge accumulates across work)
- Layer 6: determinism (non-AI enforcement at the shell boundary)

These six principles together capture *what makes LLM-based engineering work as practiced today*. The 4-layer captured three of them (persistence, composability, perspective) plus determinism; the 6-layer adds progressivity and compounding.

---

## Implementation Units

8 units, dependency-ordered.

- U1. **ADR — Establish the 6-layer AI architecture**

**Goal:** Capture the architectural decision: 6-layer AI model as the abstraction, CE as canonical realization, vendor-neutrality preserved by the layering itself. Defend the model with the principle-per-layer framing. Establish the publication-quality framing for downstream artifacts (U2 onward).

**Requirements:** R1, R11, R12

**Dependencies:** None.

**Files:**
- Create: `docs/README.md` (one-paragraph stub: "this directory holds documentation per `process/documentation-standards.md`; current contents: `engineering/`, `plans/`")
- Create: `docs/engineering/README.md` (one-paragraph stub pointing into `adr/` with a note that `designs/` would live here too when written)
- Create: `docs/engineering/adr/0001-six-layer-ai-architecture.md`

**Approach:**
- Create the directory tree (`docs/`, `docs/engineering/`, `docs/engineering/adr/`). `docs/plans/` already exists.
- Create the two README stubs to honor `process/documentation-standards.md` line 125.
- Use the lightweight ADR format from `process/documentation-standards.md` lines 83–92 (Decision / Context / Consequences). Sections:
  - **Decision**: adopt the 6-layer AI architecture; CE is canonical realization; vendor-neutral baselines stay in place.
  - **Context**: PRs #16/#19/#21 shipped a 4-layer model; CE adoption surfaced structural patterns the 4-layer didn't name; three rounds of doc-review on the abandoned prior plan converged on this evolution.
  - **The architecture — vendor-neutral description**: one paragraph per layer, naming the principle each specializes. Layer table: layer / principle / what fills it (vendor-neutral baseline + CE realization).
  - **Why CE specifically as canonical realization**: short subsection. CE is the most developed implementation in active use across rmorison projects; describing the architecture in CE's terms gives concrete grounding while the layer definitions stay abstract enough that other realizations fit.
  - **Consequences**: list what changes (Layer 4/5 named for the first time; Layer 1 stays pointers; vendor-neutral Layer 2/3 baselines unchanged; CE adoption is additive when present), what stays unchanged (PR-based merges, semver, conventional commits, code quality principles, the principle "context is expensive"), and the maintenance liability the architecture creates (track CE realization at major versions; revisit layer definitions when other LLM-engineering toolkits surface patterns we should absorb).
  - **References**: rescoped issue #22, the integration doc (U2), PRs #16/#19/#21 (built on, not superseded), the three to-be-archived prior proposals, books-ops as private real-world deployment example.
- Write the ADR with publication-quality framing. Reader assumption: a developer landing on the repo cold; no rmorison context. Layer definitions describe what the layer is structurally, not which CE skill fills it. The "vendor-neutral baseline + CE realization" framing makes the abstraction visible.
- Number 0001; no ADRs exist yet.

**Patterns to follow:**
- ADR shape from `process/documentation-standards.md` lines 83–92.
- Publication-quality framing: each layer description should answer "what is this layer for, structurally" before naming what fills it.

**Test scenarios:**
- Test expectation: none — documentation. Verification by structural review.

**Verification:**
- ADR exists at `docs/engineering/adr/0001-six-layer-ai-architecture.md`.
- Six layers each have a paragraph of vendor-neutral structural description.
- Each layer names its principle (persistence, composability, perspective, progressivity, compounding, determinism).
- Layer table shows vendor-neutral baseline + CE realization side-by-side.
- "Why CE specifically" subsection defends the canonical-realization choice without making CE sound mandatory.
- Consequences distinguish "review discipline" from "enforced merge gate."
- A reader without rmorison context can understand the architecture from the ADR alone.
- `docs/README.md` and `docs/engineering/README.md` exist as minimal stubs.

---

- U2. **Rewrite `ai/claude-code/README.md` as canonical 6-layer description**

**Goal:** The repo's load-bearing AI-architecture description for new adopters. Rewritten with publication-quality framing — readable as standalone document. Names the 6 layers, their principles, what fills each (vendor-neutral baseline + CE realization), and how the layers compose into pipelines.

**Requirements:** R2, R11, R12

**Dependencies:** U1 (references the ADR by number).

**Files:**
- Modify (substantial rewrite): `ai/claude-code/README.md`

**Approach:**
- **Section: Abstraction & Realization**: open with the framing — this directory describes the AI architecture; the architecture is the abstraction; CE is one canonical realization. Vendor-neutral baselines exist for some layers; non-CE adopters can use them or roll their own.
- **Section: The Six Layers**: one subsection per layer. Each subsection has:
  - Layer name and one-sentence principle (persistence / composability / perspective / progressivity / compounding / determinism)
  - Structural description (what the layer holds, when it's loaded, what its constraints are)
  - Vendor-neutral baseline (pointer to where it lives in the standards repo)
  - CE realization (link to plugin and one-paragraph description of CE's implementation)
  - Examples of other potential realizations (Cursor commands, Aider, hand-rolled — keeps the abstraction concrete without committing to those)
- **Section: How the Layers Compose**: short subsection showing the pipeline pattern (brainstorm → plan → work → doc-review → code-review → compound) and how Layer 2 skills consume Layer 3 personas via Layer 4 references and produce Layer 5 compound output. Reference the High-Level Technical Design block from this plan as the visual aid.
- **Section: How to Use**: brief; for this repo and for new projects (copy `templates/.claude/`).
- **Section: Design Principles**: keep the existing principles ("Context is expensive — only load what's needed, when it's needed", "Standards are enforced, not just referenced", "Templates over copies", "Projects customize, templates provide structure"). They transfer cleanly to the 6-layer.
- **Length target**: 100–150 lines. Compact enough to read in one sitting; rich enough to be a standalone architecture description.
- Pointer at the bottom to the ADR (U1) and integration doc (U5).
- Do NOT cite books-ops in this file.

**Patterns to follow:**
- Existing voice: concise, table-heavy, links-out-to-detail.
- Publication-quality framing: structural before specific. A reader should understand the layer's *purpose* before seeing what fills it.

**Test scenarios:**
- Test expectation: none — documentation. Verification by structural review and reader test.

**Verification:**
- File describes 6 layers, each with principle + structural description + vendor-neutral baseline + CE realization + other-realization examples.
- "How the Layers Compose" section explains pipelines.
- A reader without rmorison context can understand the architecture from this file alone.
- File length 100–150 lines.
- Pointers to ADR and integration doc present.
- No rmorison-specific assumptions or books-ops citations.

---

- U3. **Update `ai/CLAUDE.md` to reflect 6-layer architecture**

**Goal:** `ai/CLAUDE.md` is the highest-leverage AI-facing artifact (agents read it every turn). Update it so an agent operating in CE-mode or standards-only-mode gets correct guidance without ambiguity. Keep the file functional as a template for downstream projects.

**Requirements:** R3, R10, R13

**Dependencies:** U1, U2 (file points at both).

**Files:**
- Modify: `ai/CLAUDE.md`

**Approach:**
- **Add an Architecture intro** (after the existing "For AI Assistants" header): one paragraph stating that this repo follows the 6-layer AI architecture (link to `ai/claude-code/README.md`) and that this file holds Layer 1-style guidance for CE-using projects.
- **Reframe the Documentation Structure block** (lines ~54–66): two-mode block — "Standards-only mode" (existing tree) and "When CE is in use" (CE path-ownership table inlined from U5). Both visible.
- **Reframe the Feature Development Workflow numbered list** (lines ~24–29): two-mode — standards-only list unchanged; CE-mode list (Phase 0 = `docs/brainstorms/`, Phase 1 seeded from brainstorm, Phase 3-4 outputs at CE-mode paths). Phase 0 = brainstorm declaration is R13.
- **Reframe the branch-naming line** (line 41): two-mode — standards-only `{issue-number}-{slugified-title}`; when CE is in use, also accepts topic-style for `lfg`/`ce-work` flows without a parent issue. Pointer to integration doc.
- **Add a "When using compound-engineering" section** at the end of the file: one-line precedence statement with provenance clause summary; one-paragraph framing of AI-review as discipline (not gate); pointers to ADR (U1) and integration doc (U5).
- Update the Quick Links section to include the new ADR and integration doc.
- Do NOT cite books-ops.

**Patterns to follow:**
- Existing `ai/CLAUDE.md` voice — terse, tables, link-out.

**Test scenarios:**
- Test expectation: none — documentation. Verification per the next field.

**Verification:**
- Architecture intro present and points at `ai/claude-code/README.md`.
- Documentation Structure block has explicit standards-only and CE-mode sub-blocks.
- Feature Development Workflow list shows both modes; Phase 0 = brainstorm declared.
- Branch-naming line carries both rules with CE carve-out qualified explicitly.
- "When using compound-engineering" section present at end.
- Pointers to ADR and integration doc in body and Quick Links.
- An agent reading the file top-down does not encounter a contradicted rule.

---

- U4. **Update Layer 1 rule files (`ai/claude-code/rules/*.md`) — compact CE-aware additions**

**Goal:** Layer 1 files are always-loaded; their content shapes default agent behavior every turn. Add CE-aware notes that point at the integration doc when CE is in use, **without inlining two-mode policy** (preserves Layer 1's compact-pointer discipline).

**Requirements:** R4, R10, R13

**Dependencies:** U1, U5.

**Files:**
- Modify: `ai/claude-code/rules/engineering-standards.md`
- Modify: `ai/claude-code/rules/sdlc-workflow.md`

**Approach:**

For **`ai/claude-code/rules/engineering-standards.md`**:
- After the `docs/` tree block (lines 27–37), add ONE paragraph: "When compound-engineering is in use, additional artifact paths apply (`docs/brainstorms/`, `docs/plans/`, `docs/solutions/`). See `process/compound-engineering-integration.md` for the full path mapping and precedence rules."
- After the Branch-naming line (line 44), add ONE line: "When CE is in use, `lfg`/`ce-work` autonomous flows may produce topic-style branches; see `process/git-branching-strategy.md` and the integration doc."
- Do NOT replace existing rules with two-mode blocks; do NOT reframe the Quick Reference structurally. Layer 1's discipline is compact-pointer; the additions are pointers.

For **`ai/claude-code/rules/sdlc-workflow.md`**:
- After the "Plan Before Implementing" section (lines 13–18), add ONE paragraph: "When compound-engineering is in use, `/ce-plan` produces the plan and `/ce-work` executes it iteratively; the `lfg` autonomous flow runs without per-step confirmation and is appropriate when a complete plan exists. See `process/compound-engineering-integration.md` for the workflow."
- Other sections (Read Before Changing, Validate After Each Change, Flag Uncertainty, Scope Discipline) are CE-compatible; no changes.

**Verify post-edit line counts**: target both files staying at or under 80 lines (well within the 150-line discipline). Each addition should be ≤ 5 lines.

**Patterns to follow:**
- Existing terse voice. Pointer-style: state the rule, link to the elaboration.

**Test scenarios:**
- Test expectation: none — documentation. Verification per the next field.

**Verification:**
- `ai/claude-code/rules/engineering-standards.md` has CE-aware additions after `docs/` tree and after branch-naming line; total file length ≤ 80 lines.
- `ai/claude-code/rules/sdlc-workflow.md` has a CE-aware addition after Plan Before Implementing; total file length ≤ 60 lines.
- Both files retain their compact-pointer character; no inlined two-mode policy.
- Pointers to `process/compound-engineering-integration.md` work.

---

- U5. **Write integration process doc — CE realization of the 6 layers + operational details**

**Goal:** Operational reference that describes how CE realizes the 6-layer architecture and resolves the path conflicts, branch-naming reconciliation, AI-review discipline, and ticket-tracking modes. Self-contained — load-bearing content inlined.

**Requirements:** R5, R10, R11, R13

**Dependencies:** U1.

**Files:**
- Create: `process/compound-engineering-integration.md`

**Approach:**
- **Header**: scope statement, audience ("projects using compound-engineering — concretely the rmorison projects, but the integration is intended to be readable and usable by any adopter"), and the precedence rule with provenance clause (R13).
- **Section 1: How CE realizes the 6 layers**: brief table mapping layer → CE realization. Cross-reference `ai/claude-code/README.md` (U2) for the canonical layer descriptions; this section is the operational mapping.
  - Layer 1: standards repo (CE doesn't fill)
  - Layer 2: CE skills (`/ce-brainstorm`, `/ce-plan`, `/ce-work`, `/ce-doc-review`, `/ce-code-review`, `/ce-debug`, `/ce-compound`, `lfg`)
  - Layer 3: CE persona reviewers (~20 specialized agents, dispatched by Layer 2 skills)
  - Layer 4: CE skills' `references/*.md` subtrees
  - Layer 5: `docs/solutions/` + `ce-compound`/`ce-compound-refresh`
  - Layer 6: standards repo (CE doesn't fill)
- **Section 2: Artifact location mapping**: full path table including `docs/solutions/` row. Inline the table directly (do NOT point at books-ops):

  | Path | Owner | Producer |
  | --- | --- | --- |
  | `docs/ideation/` | CE | `ce-ideate` |
  | `docs/brainstorms/` | CE | `ce-brainstorm` — also Phase 0 / discovery artifact for `process/feature-development-workflow.md`; Phase 1 seeded from brainstorm |
  | `docs/plans/` | CE | `ce-plan` (subsumes `docs/planning/` from the standards) |
  | `docs/solutions/` | CE | `ce-compound`, `ce-compound-refresh` (Layer 5; no standards analog yet) |
  | `docs/engineering/adr/` | shared | human-authored ADRs (path identical in both models) |
  | `docs/engineering/designs/` | standards | human-authored design docs |
  | `docs/product/` | standards | human-authored product concepts and feature specs |

  State the precedence rule + provenance clause: when a CE skill produces an artifact, CE paths and conventions win; standards paths/conventions own human-authored artifacts; first-skill-touched-the-file is the default; explicit `provenance:` frontmatter overrides.

- **Section 3: Issue-tracking modes**: three modes — team-scale (full three-tier hierarchy from `process/issue-tracking.md`), solo + AI (reactive issue creation, plan U-IDs as unit tracker), hybrid. Cite the existing solo carve-outs in `process/issue-tracking.md` lines 359–373. Inline a minimal Ticket Policy block (umbrella epic per multi-phase plan, sub-issues reactive, U-aligned branch naming).

- **Section 4: Branch-naming reconciliation**: issue-numbered when an issue exists, topic-style for `lfg`/`ce-work` flows without a parent issue. Pointer to U7's anti-pattern reframe in `process/git-branching-strategy.md`.

- **Section 5: Solo-scale adaptations + AI-review discipline**: what shifts at solo scale (no planning poker; no human code-review assignment; milestones earn keep at >3-month horizons; epic structure earns keep at 5+ implementation issues per feature).
  - **AI-review discipline**: explicit framing — this is **review discipline**, not an enforced merge gate. No CI check, branch-protection automation, or PR template enforces it. The discipline names: (a) `ce-code-review` on the diff before merge; (b) `ce-doc-review` on the plan or spec when applicable; (c) self-review against plan acceptance criteria. **Failure modes the discipline does not catch**: cross-PR scope drift, self-grading loops, product-positioning regressions, same-intent author/reviewer. When a human reviewer onboards, the standards' "Require at least 1 approval" rule re-engages and AI review becomes complementary.

- **Section 6: CE skill ↔ standards doc cross-reference**: table mapping each CE skill (workflow + behavior description) to the standards docs it operates within. Behavior described alongside skill name to localize name-churn rot.

- **Footer: Real-world deployment example**: one paragraph naming `books-ops` as a private rmorison deployment that informed this doc's wording. No line-range citations; no references to books-ops content as canonical.

**Patterns to follow:**
- `process/issue-tracking.md` voice for the issue-tracking section.
- `process/git-branching-strategy.md` voice for the branch-naming section.

**Test scenarios:**
- Test expectation: none — documentation. Verification per the next field.

**Verification:**
- All six sections present.
- Layer-to-CE-realization mapping includes all 6 layers.
- Documentation Paths table inlined directly (not linked to books-ops).
- Precedence rule + provenance clause stated.
- AI-review discipline section names: (a) what's checked, (b) the four failure modes, (c) explicit "discipline, not enforced gate" framing.
- Ticket Policy block inlined.
- `books-ops` named only in the footer as real-world deployment.
- A reader without rmorison repo access can apply the doc end-to-end.
- No team-scale standards weakened — every cross-reference is additive.

---

- U6. **Rewrite README's "AI / Claude Code Integration" section + add Process Standards entry**

**Goal:** Front-door positioning. The README is where readers land first; it must reflect the 6-layer architecture and name CE as canonical realization without losing the lightweight-standards positioning.

**Requirements:** R6, R10, R11

**Dependencies:** U1, U2, U5.

**Files:**
- Modify: `README.md`

**Approach:**
- **Replace** the "AI / Claude Code Integration" section (lines 96–117) with a CE-aware 6-layer version:
  - One-paragraph intro: this repo defines a 6-layer AI architecture (link to `ai/claude-code/README.md`); CE is named as canonical realization for projects that adopt the plugin.
  - **Layer table** (replacing the existing 4-row table): six rows, one per layer, with: Layer name / Principle / Vendor-neutral baseline / CE realization. Brief — link out to `ai/claude-code/README.md` for full descriptions.
  - **"Key principle" line**: keep the existing "Context is expensive — only load what's needed, when it's needed." It transfers cleanly. Add: "The 6-layer model specializes this principle across context-cost slots."
- **Add** a Process Standards entry for `process/compound-engineering-integration.md` between the existing Issue Tracking section and the AI / Claude Code Integration section. One paragraph, ≤ 4 lines.
- **Add** one line under "Applying These Standards" → "For New Projects" noting that projects using CE consult the integration doc for Layer 2/3 path mapping and review discipline.
- Do not restructure other sections.

**Patterns to follow:**
- Existing README voice.

**Test scenarios:**
- Test expectation: none — documentation. Verification per the next field.

**Verification:**
- README "AI / Claude Code Integration" section reflects 6-layer model with vendor-neutral baseline + CE realization columns.
- "Key principle: context is expensive" preserved and extended.
- Process Standards entry for the integration doc present.
- "Applying These Standards" includes CE pointer.
- A reader landing on the README sees the architecture before any specific workflow rule.

---

- U7. **Update `process/git-branching-strategy.md` — anti-pattern carve-out + Layer 3 discipline cross-ref + pointer**

**Goal:** Address the genuine conflict between standards' issue-required branch naming and CE's `lfg`/`ce-work` autonomous flows. Add a Layer 3 discipline cross-ref in branch protection.

**Requirements:** R8, R10, R13

**Dependencies:** U5.

**Files:**
- Modify: `process/git-branching-strategy.md`

**Approach:**
- **Edit the "❌ Branches Without Issues" anti-pattern** (lines 287–291): add a one-line carve-out — "*Exception: `lfg` and `ce-work` autonomous flows may produce topic-style branches (`feat/...`, `fix/...`) without a parent issue. File an issue retroactively only if review surfaces something worth tracking. See `process/compound-engineering-integration.md`.*"
- **Add a "When using compound-engineering" pointer** near the top of the file (after the Overview): one-line note with link to integration doc.
- **Add a Layer 3 discipline cross-ref to the Branch Protection block** (lines 322–331): one-line note that the "Require at least 1 approval" rule has a CE-mode complement — the Layer 3 AI-review discipline (`ce-code-review` + `ce-doc-review`), defined in the integration doc. Frame as discipline, not enforced gate.
- Do not rewrite the GitHub Flow guidance.

**Patterns to follow:**
- Existing voice/formatting.

**Test scenarios:**
- Test expectation: none — documentation. Verification per the next field.

**Verification:**
- Anti-pattern carve-out present and points at the integration doc.
- Cross-ref pointer present near the top.
- Branch protection block carries the Layer 3 discipline cross-ref — preserves team-scale rule, adds CE complement, framed as discipline not enforced gate.

---

- U8. **Cross-references in remaining 4 process docs + archive 3 prior `ai/*.md` proposals**

**Goal:** Complete the cross-reference work and archive the genuine path-not-taken (the three pre-CE agent-native proposals).

**Requirements:** R8, R9, R10, R13

**Dependencies:** U1, U5.

**Files:**
- Modify: `process/feature-development-workflow.md` (Phase 0 = brainstorm note in or near Phase 1 block, lines 40–70)
- Modify: `process/issue-tracking.md` (cross-ref pointer near Three-Tier Hierarchy section, citing existing solo carve-outs at lines 359–373)
- Modify: `process/project-planning-standards.md` (cross-ref pointer near Team Estimation section, citing existing solo carve-out at line 86)
- Modify: `process/documentation-standards.md` (cross-ref note in or near Directory Structure, lines 9–47)
- Move: `ai/adoption-roadmap.md` → `archive/adoption-roadmap.md`
- Move: `ai/agent-native-improvements.md` → `archive/agent-native-improvements.md`
- Move: `ai/top-3-enhancements.md` → `archive/top-3-enhancements.md`
- Create: `archive/README.md` (short explainer for the archived proposals)

**Approach:**

Cross-references (each is 1–3 lines, additive, points at `process/compound-engineering-integration.md`):
- **`process/feature-development-workflow.md`**: in or just before Phase 1, add note that `docs/brainstorms/<topic>-requirements.md` (the `ce-brainstorm` output) IS the Phase 0 / discovery artifact when CE is in use; Phase 1 is seeded from the brainstorm.
- **`process/issue-tracking.md`**: near Three-Tier Hierarchy, add pointer with citation to existing solo carve-outs at lines 359–373.
- **`process/project-planning-standards.md`**: near Team Estimation, add pointer noting that for solo CE work, point estimates in plan files serve as self-calibration; planning poker is N/A. Cite the existing solo carve-out at line 86.
- **`process/documentation-standards.md`**: near Directory Structure, add note that CE-skill outputs live at `docs/brainstorms/`, `docs/ideation/`, `docs/plans/`, `docs/solutions/` per the integration doc's path mapping.

Archive (3 prior proposals, currently untracked per `git status`):
- `git mv` would fail on untracked files. Use: `mkdir -p archive && mv ai/<file>.md archive/<file>.md`, then `git add archive/`. The archival commit is these files' first appearance in history.
- Banner each archived file (relative path `../docs/engineering/adr/...`):
  ```
  > **Implementation strategy superseded by [ADR-0001: Six-Layer AI Architecture](../docs/engineering/adr/0001-six-layer-ai-architecture.md).**
  >
  > This document analyzed agent-native principles and proposed building these abstractions in this repo. We instead adopted the 6-layer AI architecture (this ADR) with [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) as the canonical realization of Layers 2 and 3. Kept here as the evaluative framework that informed the architecture — the analysis remains the lens for re-evaluating CE adoption if circumstances change. See `process/compound-engineering-integration.md` for the operational doc.
  ```
- `archive/README.md`: short explainer (one paragraph) describing the three archived docs as the agent-native-analysis path-not-taken; names the architecture chosen instead.

**Patterns to follow:**
- Existing voice/format in each file.
- Match existing cross-ref style.

**Test scenarios:**
- Test expectation: none — documentation. Verification per the next field.

**Verification:**
- All four named process docs have a CE cross-ref.
- Phase 0 = brainstorm note exists in `process/feature-development-workflow.md` (R13).
- Solo-mode pointer in `process/issue-tracking.md` cites existing carve-outs (R10: not weakening).
- Planning poker N/A note in `process/project-planning-standards.md` cites the existing solo carve-out.
- Three `ai/*.md` proposals exist at `archive/<name>.md`, with banners and working ADR links.
- `archive/README.md` exists.
- Recursive globs against `ai/**/*.md` no longer return the archived content.
- `templates/.claude/skills/`, `templates/.claude/agents/`, `templates/.claude/hooks/`, `templates/.claude/settings.json` UNCHANGED (vendor-neutral baselines stay in place).

---

## System-Wide Impact

- **Interaction graph:** AI agents reading `ai/CLAUDE.md` (U3) get architecture pointers. The integration doc (U5) is the load-bearing operational reference. Layer 1 rules (U4) carry pointer-only notes; multi-mode policy lives in U3 and U5. The README (U6) and `ai/claude-code/README.md` (U2) frame the architecture for human and AI readers respectively. Cross-refs in U7 and U8 are signposts back to U5.
- **Error propagation:** N/A — documentation change. The architectural framing's failure mode is "reader misinterprets the layering"; mitigation is publication-quality framing (R11) with reader-test verification.
- **State lifecycle risks:** None — no runtime state.
- **API surface parity:** N/A — no APIs.
- **Integration coverage:** "No team-scale standards weakened" (R10) requires re-reading every cross-ref in U7/U8 to verify additive language.
- **Unchanged invariants:** ADR location convention; semver; conventional commits; PR-based merges; GitHub Flow; code quality principles; documentation formats; the vendor-neutral templates' Layer 2 and Layer 3 baselines (`templates/.claude/skills/`, `templates/.claude/agents/`); the 4-layer model's principle ("context is expensive — only load what's needed, when it's needed") — preserved and extended.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| 6-layer model is novel; layer definitions may need refinement once real adopters use them. | Publication-quality framing (R11) gives the architecture a chance to be tested by external readers (the article surface). Iteration is expected post-merge; the architecture is live documentation, not a final claim. |
| Layer 4 (References) and Layer 5 (Compound) currently have only CE realizations. Vendor-neutral baselines for these layers don't exist yet. | The architecture describes what those layers ARE structurally; the lack of vendor-neutral baseline is named honestly ("no vendor-neutral baseline yet — described in architecture"). Future work could populate these layers in `templates/`. |
| Integration doc's "AI-review discipline" framing is misread as enforced gate, leading to false confidence. | Doc explicitly frames as "process discipline, not enforced by repo configuration." Failure modes named explicitly. Adopters know what they're trading. |
| Vendor coupling at Layer 2/3 (CE) creates a maintenance liability against EveryInc's roadmap. | ADR (U1) defends the canonical-realization choice and states the upgrade discipline (pin to CE 3.x; re-evaluate at 4.x). Layer 2/3 vendor-neutral baselines remain in place; CE adoption is opt-in. |
| Single-PR scope (~500–700 lines / ~12–14 files) above standards' 200-400 target. | Standards' "When to Deviate" provision covers branching-model alternatives, not PR size — so the deviation must stand on cross-reference coherence (artifacts reference each other). Split is available if review surfaces seams (U1+U2 first; everything else follows). |
| Publication-quality framing (R11) adds drafting latency. | The latency is the cost of the publication-quality bar. ce-doc-review (run after plan write) provides a reader-quality gate. Iteration cost is bounded. |
| Books-ops privacy: integration doc inlines content, but books-ops is named in the footer as real-world deployment. | Footer is one paragraph; no line-range citations; integration doc is self-contained. A non-rmorison reader hits "this is private" once and proceeds. |
| Three rounds of doc-review on the abandoned plan converged on the 6-layer; this plan should not need 3 more rounds. | Plan written tighter than the abandoned one; key architectural decisions (6-layer, vendor-neutral baselines stay, Layer 1 stays compact) decided up-front. ce-doc-review is the next quality gate; results from that pass should be substantively different than rounds 1–3 of the prior plan because the architectural framing is now sound. |

---

## Documentation / Operational Notes

- **After merge**: notify books-ops to refresh its CLAUDE.md to point at the published integration doc instead of the in-flight #22 reference. Books-ops' `CLAUDE.md` already says "see engineering-standards#22 for the in-flight upstream proposal" in two places; those become "see `process/compound-engineering-integration.md`." books-ops can also drop its locally-absorbed Documentation Paths table since the integration doc carries it canonically.
- **Issue #12** (Phase 0): R13 partially addresses for CE-mode adopters. Verify acceptance language before closing.
- **Issues #16/#19/#21**: built on, not superseded. Optional one-line comments noting the architecture has evolved (cheap to add post-merge if discoverability becomes a concern).
- **PR description**: lead with the architectural framing (6-layer abstraction + CE as canonical realization). The framing is the central contribution; surfacing it in the description helps reviewers understand the structural choice before evaluating individual file diffs. Invoke standards' "When to Deviate" only if PR size is questioned; the cross-reference coherence argument stands on its own.
- **No CI changes, no migrations, no runtime impact**. Pure documentation and three file relocations.
- **Branch rename** (deferred to implementation): if the implementer prefers the branch name to match the new title, `git branch -m 22-refactor-ai-architecture-6-layer-model` and `git push -u origin 22-refactor-ai-architecture-6-layer-model` mid-PR. Not required.

---

## Sources & References

- **Origin issue:** [rmorison/engineering-standards#22 (rescoped)](https://github.com/rmorison/engineering-standards/issues/22) — "Refactor AI architecture to a 6-layer model with compound-engineering as canonical realization"
- **Prior plan (abandoned):** [`docs/plans/2026-05-03-001-feat-compound-engineering-integration-plan.md`](2026-05-03-001-feat-compound-engineering-integration-plan.md) — three rounds of doc-review iteration; operational findings carried forward (R13)
- **Built on:** PRs [#16](https://github.com/rmorison/engineering-standards/issues/16) (4-layer AI architecture), [#19](https://github.com/rmorison/engineering-standards/issues/19) (README documentation), [#21](https://github.com/rmorison/engineering-standards/issues/21) (PascalCase hooks). The 4-layer was the foundation this evolves.
- **Related issue:** [#12](https://github.com/rmorison/engineering-standards/issues/12) (Phase 0) — partially addressed by R13 for CE-mode adopters.
- **CE plugin:** https://github.com/EveryInc/compound-engineering-plugin (v3.1.0; canonical realization of Layers 2, 3, 4, 5)
- **Agent-native foundation:** https://every.to/guides/agent-native (informed both the original 4-layer and CE itself)
- **Real-world deployment example:** `books-ops` (private rmorison repo) — informed wording during real use of the brainstorm → plan → ce-doc-review → lfg pipeline. Not a doc reference; integration doc is self-contained.
- **Memory:** `architecture_explanation_style.md`, `ce_as_engineering_baseline.md`, `repo_purpose_and_article.md` (in `~/.claude/projects/.../memory/`)
- **Affected files:** `docs/README.md` (new), `docs/engineering/README.md` (new), `docs/engineering/adr/0001-six-layer-ai-architecture.md` (new), `process/compound-engineering-integration.md` (new), `archive/README.md` (new), `ai/claude-code/README.md`, `ai/CLAUDE.md`, `ai/claude-code/rules/engineering-standards.md`, `ai/claude-code/rules/sdlc-workflow.md`, `templates/CLAUDE.md`, `README.md`, `process/feature-development-workflow.md`, `process/issue-tracking.md`, `process/project-planning-standards.md`, `process/documentation-standards.md`, `process/git-branching-strategy.md`, three archived `ai/*.md` files (moves)
