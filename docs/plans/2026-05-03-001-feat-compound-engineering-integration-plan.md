---
title: "feat: Integrate compound-engineering practices with the standards repo"
type: feat
status: abandoned
date: 2026-05-03
deepened: 2026-05-03
abandoned: 2026-05-03
origin: https://github.com/rmorison/engineering-standards/issues/22
---

> **Status: abandoned.** This plan iterated three rounds of multi-persona doc-review under shifting architectural framings:
> 1. **Round 1**: "supersede the 4-layer with CE" — surfaced books-ops privacy, AI-review-as-gate overclaim, vendor coupling concerns.
> 2. **Round 2**: "CE as specialization of Layers 2 and 3" — surfaced that CE doesn't fit the 4-layer cleanly (personas aren't standalone agents; depth gap is 10x; Layer 1 inlining violates compact-pointer purpose).
> 3. **Round 3**: "morph the 4-layer to fit CE" — at this point the work had grown beyond CE integration into **architectural redesign with publishable framing**. The plan was no longer right-sized for what's actually being built.
>
> **Superseded by**: a fresh plan around the **6-layer AI architecture** (Rules / Workflow Skills / Persona Agents / References / Compound / Hooks) with CE as the canonical realization. The new plan frames the architecture as the abstraction and CE as one (highly developed) realization — supports the user's potential technical article *"Abstracting the Every Compound Engineering Model for LLM Based Engineering"* and the repo's encompassing-standard direction.
>
> Preserved here as iteration history: the operational findings (path mappings, branch-naming reconciliation, AI-review-as-discipline framing, books-ops privacy resolution by inlining, archive-prior-proposals-to-top-level) remain valid input to the new plan; the architectural framing was wrong, the operational details were right.

# feat: Integrate compound-engineering practices with the standards repo (abandoned)

## Overview

Make the relationship between this repo's engineering standards and the compound-engineering (CE) plugin explicit by **framing CE as a specialization of Layers 2 (Skills) and 3 (Agents)** of the 4-layer AI architecture this repo already ships (PRs #16/#19/#21). The 4-layer model is the abstraction: it defines four context-cost slots (Rules / Skills / Agents / Hooks) for AI tooling. CE is a deep, vendor-coupled implementation of two of those slots that you load when you install the plugin. The vendor-neutral `templates/.claude/skills/{spec,plan,review}/` and `templates/.claude/agents/` remain in place as the Layer 2/3 baseline for projects that don't run CE.

This framing — **abstraction (the 4-layer model) + specialization (CE as the deep implementation of Layers 2 and 3 when present)** — is load-bearing for the integration. The top-level docs (`README.md`, `ai/CLAUDE.md`, `ai/claude-code/README.md`) explicitly stress this layering so new adopters understand the architecture before any specific workflow.

The plan delivers: an ADR establishing the layering, a process doc that inlines its own load-bearing content (so a public reader can apply it without 404'ing on a private books-ops link), inline-replace fixes for conflicting *content* in `ai/CLAUDE.md` and `ai/claude-code/rules/` (the always-loaded Layer 1 files), archival of three prior agent-native proposals to top-level `archive/`, a CE-as-specialization subsection added to README and `ai/claude-code/README.md`, a CE-aware section in `templates/CLAUDE.md`, and cross-references in the five existing process docs. Solo / AI-driven workflows become a first-class scale alongside the team-scale assumptions that pervade the current standards.

**Critically, the lightweight skills (`/spec`, `/plan`, `/review`) and agents (`code-reviewer`, `spec-writer`) are NOT archived** — they are the vendor-neutral baseline of Layers 2 and 3. CE specializes those layers when installed; both remain available, with CE-using projects defaulting to the deeper CE skills.

The key precedence rule the integration doc enforces: **when a CE skill produces an artifact, CE paths and conventions win; standards paths and conventions still own human-authored artifacts and ADRs.** Provenance edge cases (co-authored docs, human-bootstrapped artifacts later run through a CE skill, CE outputs later edited by hand) are resolved by a "first-skill-touched-the-file" rule, with an escape hatch for explicit reclassification — see Key Technical Decisions.

A second, deliberately humbler framing: the AI-review process described here is **review discipline, not an enforced merge gate**. The repo has no CI check or branch-protection automation that can enforce "no unresolved P0/P1 findings." Adopters get value by following the discipline; they don't get a wall.

---

## Problem Frame

Both systems ship in the same repos today (e.g., `books-ops`) with no documented relationship:

- Standards prescribe `docs/product/`, `docs/engineering/designs/`, `docs/engineering/adr/`, `docs/planning/`. CE writes to `docs/ideation/`, `docs/brainstorms/`, `docs/plans/`, `docs/solutions/`. Direct path conflict at `docs/plans/` vs `docs/planning/`. No standards analog for `docs/solutions/`.
- Standards' three-tier issue hierarchy (Milestone → Epic → Implementation) is right for 3-5-person teams. CE plan files use U-IDs as the unit tracker; pre-allocating sub-issues per U duplicates state and drifts from the plan. Standards already have implicit solo carve-outs (`process/issue-tracking.md`'s "<3 issues: just use labels" / "<1 month: might not need epic structure") but they aren't surfaced.
- Standards' branch naming (`{issue-number}-{slugified-title}`) directly contradicts CE's `lfg` / `ce-work` autonomous flows that produce `feat/...` / `fix/...` branches without a parent issue. `process/git-branching-strategy.md`'s "❌ Branches Without Issues" anti-pattern needs a reframe, not just a pointer.
- Branch protection in standards assumes "Require at least 1 approval." For solo CE work, the human reviewer slot is replaced by `ce-code-review` + `ce-doc-review` + PR self-review — but the criteria for "review passed" are undefined, and the substitution itself has unexamined failure modes (scope drift across PRs that AI reviewers don't see, self-grading loops, no second-pair-of-eyes with independent stakes).
- `ai/CLAUDE.md` is the highest-leverage AI-facing artifact (agents read it every turn) and currently hardcodes the standards paths *and* the unqualified `{issue-number}-{slugified-title}` branch-naming rule that directly contradicts CE's `lfg` / `ce-work` flows. Side-by-side overrides leave conflicting top-of-file content; agents reading top-down hit standards rules before reaching the CE section. The fix needs to be inline replacement of conflicting rules, not addition.
- Three untracked `ai/` proposals (`adoption-roadmap.md`, `agent-native-improvements.md`, `top-3-enhancements.md`) document a path-not-taken: building agent-native abstractions ourselves rather than adopting CE directly. They need clear supersession **and** physical relocation outside the agent-context tree (top-level `archive/`, not `ai/archive/`) so recursive agent globs and template-copying adopters don't ingest them.
- **Newly merged into `main` (PRs #16, #19, #21) and discovered after initial planning**: a 4-layer AI architecture (Rules + Skills + Agents + Hooks) that — once correctly understood — does NOT compete with CE; it provides the taxonomy CE specializes. The 4-layer model defines four context-cost slots; CE is a deep implementation of two of them (Skills and Agents) that loads when the plugin is installed. The genuine integration tasks remaining are: (a) Layer 1 *content* conflicts — `ai/claude-code/rules/engineering-standards.md` hardcodes the standards-only `docs/` tree and unqualified branch-naming, and `ai/claude-code/rules/sdlc-workflow.md`'s "wait for explicit confirmation before proceeding" contradicts CE's `lfg` autonomous flow; the layer itself is correct, the content needs CE-aware updates; (b) Layer 2/3 default selection — adopters need to know which deep implementation fills Layers 2 and 3 (CE if installed, vendor-neutral templates otherwise); (c) discoverability — the README's "AI / Claude Code Integration" section currently describes the 4-layer model without naming CE as the specialization, so CE adopters don't see the relationship; (d) cross-references in the five existing process docs.

The `books-ops` project ([private CLAUDE.md](https://github.com/rmorison/books-ops/blob/main/CLAUDE.md), inaccessible to non-rmorison readers) absorbed all five gaps locally during real use of the ideation → brainstorm → plan → ce-doc-review → lfg pipeline. Its absorbed wording is battle-tested. **Because `engineering-standards` is a public, copyable template repo, the integration doc inlines the load-bearing content (Documentation Paths table, Review Discipline paragraph, Ticket Policy block) directly rather than pointing readers at a 404.** books-ops is named as a real-world deployment example, not as a canonical reference.

---

## Requirements Trace

- R1. Document the decision to integrate CE with the standards, with rationale and pointers (issue #22 acceptance criterion: ADR).
- R2. Produce an integration process doc with five sections: artifact location mapping, issue-tracking modes, branch-naming reconciliation, solo-scale adaptations, CE skill ↔ standards doc cross-reference (issue #22 acceptance criterion).
- R3. Add minimal cross-references to the five named existing process docs (issue #22 acceptance criterion).
- R4. Reference at least one downstream project (`books-ops`) as the integration's working example (issue #22 acceptance criterion).
- R5. Add no weakening of team-scale standards; the solo-mode track adds, never replaces (issue #22 acceptance criterion).
- R6. Add `docs/solutions/` to the path mapping as a CE-owned path with no standards analog (Claude review gap #1; books-ops absorbed).
- R7. Define the AI-review **discipline** (not enforced gate) — what `ce-code-review` + `ce-doc-review` checks, what failure modes the substitution invites, and explicitly state that the discipline is process-level, not enforced by repo configuration (Claude review gap #2; books-ops left undefined; doc-review surfaced enforcement and failure-mode gaps).
- R8. Update `ai/CLAUDE.md` to **inline-replace the conflicting Quick Reference content** (workflow paths, branch-naming rule) for CE-mode and add the precedence section. Side-by-side override is rejected because it leaves contradictory standards-path content above the override (Claude review gap #3; books-ops absorbed locally; doc-review identified that side-by-side fails for agents reading top-down).
- R9. Declare `docs/brainstorms/` (the `ce-brainstorm` output) as the Phase 0 / discovery artifact for `process/feature-development-workflow.md`, with Phase 1 seeded from it. Closes the overlap with issue #12 (Claude review gap #4; books-ops absorbed).
- R10. Reframe `process/git-branching-strategy.md`'s "❌ Branches Without Issues" anti-pattern to allow topic-style naming for `lfg` / `ce-work` flows without a parent issue (Claude review gap #5; books-ops absorbed).
- R11. Supersede the three prior `ai/` proposal docs by relocating them to top-level `archive/` (outside the agent-context `ai/` tree) and adding banners pointing at the new ADR. User selected archive-with-banner; doc-review surfaced that placing them under `ai/archive/` keeps them in agent-recursive globs and in the copyable template tree, which defeats the goal — so the location moves to top-level `archive/`.

- R12. Defend the choice to couple the engineering standards to one specific AI-workflow plugin (CE/EveryInc) rather than describe vendor-neutral patterns. The ADR carries a "Why this plugin specifically" subsection that names the alternative considered (vendor-neutral patterns + CE as one realization), explains why direct adoption beats neutrality for the rmorison use case, and states the upgrade discipline relative to CE's release cadence (doc-review product-lens finding).

- R13. Specify the precedence rule's behavior on edge-case provenance: co-authored documents, human-bootstrapped artifacts later run through a CE skill, CE outputs later edited by hand. Resolution: "first-skill-touched-the-file" rule with an explicit reclassification escape hatch (doc-review adversarial finding).

- R14. Update the *content* of the Layer 1 always-loaded rules — `ai/claude-code/rules/engineering-standards.md` (hardcoded `docs/` tree, unqualified branch-naming) and `ai/claude-code/rules/sdlc-workflow.md` ("wait for confirmation before implementing" contradicts `lfg`) — to be CE-aware. The layer itself is correct; the content currently presupposes Layer-2-as-templates-only. Same two-mode pattern as `ai/CLAUDE.md` (R8): describe the standards-mode rule and the CE-mode addendum.

- R15. **Establish the layering explicitly across top-level AI docs.** The 4-layer model is the abstraction; CE is the specialization of Layers 2 (Skills) and 3 (Agents) that loads when the plugin is installed. This is stated in: the ADR (U1), `ai/claude-code/README.md` (U3 — currently describes the 4-layer architecture; expand to name CE as the specialization for Layers 2 and 3), `ai/CLAUDE.md` (U3), and the README's "AI / Claude Code Integration" section (U7). Top-level docs are the new-adopter onboarding surface; the layering must be visible there.

- R16. Add a CE-as-specialization subsection to the README's "AI / Claude Code Integration" section (lines 96–117). **Do NOT replace the 4-layer description** — it remains accurate for projects that don't run CE. Add a subsection naming CE as the deep implementation of Layers 2 and 3 when installed, with pointers to the ADR (U1) and integration doc (U2). Update Layer 2 and Layer 3 rows of the existing Layer table to note "(or CE skills/agents when CE is installed)".

---

## Scope Boundaries

- Forking compound-engineering or maintaining its skill content here.
- Tracking compound-engineering's version updates inside the standards (the integration doc describes CE-skill behavior and artifact shape, not specific skill names where possible — reduces maintenance churn per issue #22 technical notes).
- Wholesale rewrite of existing standards docs.
- Building automated tooling that enforces CE-mode vs standards-mode (no `.project-status.json`, no validation scripts, no JSON standards index — those were the path-not-taken in the now-archived `ai/` proposals).
- Defining a deep AI-review scoring rubric beyond the merge-gate criteria (R7). Rubric refinement can be a follow-up if real use surfaces ambiguity.

### Deferred to Follow-Up Work

- Rewrite of `code/python-standards.md`, `code/database-standards.md`, `code/web-application-standards.md` to add CE-skill cross-references — these are language/stack standards, not process; they don't need the same touch-up. Surface in a follow-up issue only if real use shows a gap.
- Hooks that enforce CE-mode invariants (e.g., a hook that warns if `/plan` is invoked instead of `/ce-plan` in a CE project). Not required for #22; the 4-layer's existing example hooks remain in place and could host this in a follow-up if adopters report confusion.
- Project-specific wrapper skills (e.g., a `templates/.claude/skills/ce-plan-wrapper/` that pre-fills repo conventions before invoking `/ce-plan`). Adds vendor coupling at the template level; defer until concrete need.

---

## Context & Research

### Relevant Code and Patterns

- [`books-ops/CLAUDE.md`](https://github.com/rmorison/books-ops/blob/main/CLAUDE.md) — the canonical working example. Sections to lift: Documentation Paths table (lines 75–89), Review Gate paragraph (lines 48–49), Ticket Policy (lines 59–73), branch-naming carve-out (line 73). Adapt wording from books-ops-specific to integration-doc-generic.
- `ai/CLAUDE.md` lines 22–66 — Quick Reference / Documentation Structure block that hardcodes the standards paths. The new "When using compound-engineering" section overrides this block.
- `process/feature-development-workflow.md` lines 40–70 — Phase 1 (Product Concept) block (heading through the Example) is the seam where Phase 0 (CE brainstorm) attaches. The cross-ref note goes near the top of this Phase block.
- `process/issue-tracking.md` lines 359–373 — already-existing solo carve-outs ("<3 issues: just use labels", "<1 month: might not need epic structure"). The integration doc cites these as the foundation for solo mode rather than inventing new ones.
- `process/git-branching-strategy.md` lines 287–291 — the "❌ Branches Without Issues" anti-pattern that requires reframe (R10). Lines 322–331 — branch protection block where R7 merge-gate criteria attach.
- `process/project-planning-standards.md` lines 79–86 — already has solo carve-out ("Individual contributors can estimate solo...") that the integration doc cites for R5 compliance.
- `process/documentation-standards.md` lines 36–46 — `docs/planning/` is described as optional; the integration doc declares CE's `docs/plans/` as the CE-mode replacement.

### Institutional Learnings

- The three archived `ai/` proposals (`adoption-roadmap.md`, `agent-native-improvements.md`, `top-3-enhancements.md`) document the path-not-taken: building our own agent-native abstractions (workflows, learnings dirs, JSON indices, parity matrix). The decision to adopt CE directly supersedes these. Their analysis of agent-native principles remains valid — what changed is the implementation strategy. The archive banners (U4) preserve this context.
- The `books-ops` integration was forced through the full pipeline (ideation → brainstorm → plan → ce-doc-review → lfg) and surfaced all five Claude-reviewer gaps in real use. Treating books-ops' absorbed wording as the source of truth is faster and lower-risk than re-deriving from first principles.

### External References

- [Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin) — version 3.1.0 currently. The integration doc describes skill behavior and artifact shape, not exact names where possible (per issue #22 technical notes), to reduce churn.
- [Every.to Agent-Native Guide](https://every.to/guides/agent-native) — the conceptual foundation; the archived `ai/` proposals analyzed it. The integration doc points to it as background reading, not as a competing framework.

---

## Key Technical Decisions

- **CE precedence rule with provenance clause** (R13): when a CE skill produces an artifact, CE paths and conventions win; standards paths and conventions own human-authored artifacts and ADRs. Edge cases: (a) **first-skill-touched-the-file wins** — if `ce-plan` produced `docs/plans/foo.md`, subsequent human edits don't reclassify it as hand-authored; (b) **human-bootstrapped artifacts later run through a CE skill** become CE-mode at the skill's first touch; (c) **explicit reclassification** is allowed via a one-line frontmatter note (`provenance: hand-authored` or `provenance: ce-plan`) when the default rule produces the wrong answer. Rationale: forces a clean disambiguation that an agent can apply without re-deriving per project; the escape hatch handles the inevitable cases where heuristics fail.
- **ADR location**: `docs/engineering/adr/0001-compound-engineering-integration.md`, not `process/adr/` as the issue body proposed. Aligns with what `ai/CLAUDE.md` and `process/documentation-standards.md` already reference. Creating `docs/engineering/adr/` is correct rather than papering over a pre-existing inconsistency. **Note** (doc-review finding): `process/documentation-standards.md` line 125 says "each `docs/` subdirectory should have a `README.md`." U1 also creates `docs/README.md` and `docs/engineering/README.md` to honor this — minimal stubs pointing into the actual content.
- **`ai/CLAUDE.md` strategy — two-mode framing inline, anchored in the layering** (R8): the existing Quick Reference (Documentation Structure, Feature Development Workflow, branch-naming rule) is reframed as two-mode blocks. Each block names the vendor-neutral baseline (the existing rule, what loads when CE is not installed) and the CE-mode addendum (what changes when the CE plugin is in use). Both modes remain visible. Polarity rationale: the layering itself defines the default — Layer 2/3 baselines are the templates' vendor-neutral skills/agents; CE specializes those layers when installed. Agents read whichever applies to their environment without ambiguity.
- **Disposition of prior `ai/` proposals — top-level `archive/`** (R11): relocate three untracked `ai/*.md` files (`adoption-roadmap.md`, `agent-native-improvements.md`, `top-3-enhancements.md`) to top-level `archive/`. These three documents are the genuine path-not-taken: they proposed building agent-native abstractions ourselves rather than adopting an existing toolkit. The 4-layer model that shipped via PRs #16/#19/#21 is **not** archived — it is the abstraction CE specializes. Top-level `archive/` (rather than `ai/archive/`) keeps the relocated files out of agent-recursive globs and out of the copyable `ai/` subtree.
- **AI-review discipline (not enforced gate)** (R7): the integration doc names this as **review discipline** that adopters voluntarily follow, not a merge gate enforced by repo configuration. There is no CI check, branch-protection automation, or PR template that enforces "no unresolved P0/P1 findings" — claiming otherwise would be aspirational documentation. The discipline names: (a) `ce-code-review` on the diff; (b) `ce-doc-review` on the plan or spec when applicable; (c) self-review against plan acceptance criteria. **Under the layering, the CE persona reviewers ARE Layer 3** — `ce-code-review` and `ce-doc-review` are the deep specialization of Layer 3 that fires when CE is in use. The integration doc also names the failure modes the discipline does not catch: cross-PR scope drift (AI reviewers see a single diff), self-grading loops (the implementer decides what "unresolved" means in solo mode), product-positioning regressions (AI reviewers tuned for code patterns miss strategic intent). When a human reviewer onboards, the standards' "Require at least 1 approval" rule re-engages and AI review becomes complementary.
- **Vendor coupling reframed under specialization** (R12): the ADR's defense of CE adoption is now framed as "CE is a deep, vendor-coupled specialization of Layers 2 and 3 that you load when you install the plugin." The vendor-neutral baseline (`templates/.claude/skills/`, `templates/.claude/agents/`) remains in place as the default for projects that don't run CE. This is materially different from "we picked CE over vendor-neutrality" — vendor-neutrality is preserved by the layering itself; vendor coupling lives in the specialization layer where adopters opt in by installing the plugin. **Upgrade discipline**: pin to CE 3.x; re-evaluate at CE 4.x major version. The integration doc describes skill behavior alongside skill names so name churn within 3.x is a one-row table edit.
- **Phase 0 declaration**: `docs/brainstorms/` IS the Phase 0 / discovery artifact for the feature workflow **when CE is in use**. Phase 1 (Product Concept) is seeded from the brainstorm requirements doc. **Issue #12 framing** (revised after doc-review): #12 is "partially addressed" by R9, not "closed." Non-CE adopters still see Phase 1 starting cold; if #12's acceptance language requires Phase 0 for non-CE adopters too, that's a separate follow-up. Verify #12's actual acceptance criteria before closing.
- **CE-skill name handling**: the integration doc uses skill names (`ce-brainstorm`, `ce-plan`, `ce-work`, `ce-code-review`, `ce-doc-review`, `lfg`) for the skill-↔-standards cross-reference table, but describes the behavior alongside each name. The names are stable in CE 3.x; if they change, only the table needs updating.
- **Single PR scope** (revised after specialization-framing pass): the integration PR is ~400–500 lines / ~10–12 files after dropping R15 (the 4-layer skills and agents are not archived) and reducing R16 from rewrite to additive. This is close to `process/git-branching-strategy.md`'s 200-400-line target. The artifacts still cross-reference each other (ADR ↔ integration doc ↔ `ai/CLAUDE.md` ↔ `ai/claude-code/rules/` ↔ README), so single-PR scope stays the right call. If review surfaces clear seams (e.g., U1+U2 first, U3-U8 follow), the PR can be split — units are dependency-ordered.

- **Layer architecture as the load-bearing framing** (new — supersedes the prior "supersede vs coexist" decision): the relationship between the 4-layer model and CE is not "CE replaces the 4-layer." It is "**the 4-layer is the abstraction; CE is the deep specialization of Layers 2 and 3 that loads when the plugin is installed.**" The 4-layer's vendor-neutral skills (`templates/.claude/skills/{spec,plan,review}/`) and agents (`templates/.claude/agents/`) remain in place as the Layer 2/3 baseline. CE skills (`/ce-brainstorm`, `/ce-plan`, `/ce-work`, `/ce-code-review`, `/ce-doc-review`, `lfg`, etc.) and CE persona reviewers fill the same layers more deeply for projects that have CE installed. **The 4-layer principle — "Context is expensive — only load what's needed, when it's needed" — is exactly CE's design philosophy; CE embodies the principle more deeply than the 4-layer's own thin skills did.** This framing is load-bearing: it preserves vendor-neutrality (the layering itself), makes CE adoption purely additive (no architecture is being superseded), and dramatically reduces PR scope. New-adopter onboarding docs (`README.md`, `ai/CLAUDE.md`, `ai/claude-code/README.md`) explicitly state this layering — the user-stated requirement is "make sure top-level docs stress this" because the layering is what facilitates architecture and understanding for adopters who land on the repo cold.

---

## Open Questions

### Resolved During Planning

- ADR location → `docs/engineering/adr/` (user answer; aligns with documentation-standards.md).
- Disposition of prior `ai/` proposals → top-level `archive/` (revised from initial `ai/archive/` answer; doc-review surfaced that placement under `ai/` keeps them in agent-recursive globs and template trees).
- `ai/CLAUDE.md` strategy → inline section (user answer).

### Deferred to Implementation

- Exact wording of the "Implementation strategy superseded by ADR-0001" banner — finalize in U4 against the ADR's actual frontmatter title.
- Whether `process/documentation-standards.md` needs an Optional Directory entry for `docs/brainstorms/` / `docs/ideation/` / `docs/plans/` / `docs/solutions/`, or whether the integration doc's path mapping is enough. Default to a single cross-ref; revisit only if the standards' Optional Directories list (lines 28–47) feels misleading without it.
- Whether `archive/README.md` is needed (default: skip, since the three superseded banners + the U7 README mention are sufficient discovery). Revisit if a reader genuinely benefits from the directory-level explainer.

### From 2026-05-03 doc-review (deferred)

- **Issue #12 closure framing**: R9 adds a CE-conditional Phase 0 cross-ref to `process/feature-development-workflow.md`, not a Phase 0 spec for non-CE adopters. Verify #12's actual acceptance language before closing — if it requires Phase 0 for all adopters, this plan only partially addresses it and #12 stays open.
- **Solo + AI as first-class scale: audience-segmentation cost** — every standards doc now requires routing logic ("which mode am I in?") before the rule applies. The product-lens reviewer flagged this as an unexamined cumulative readability tax. Lighter alternative: keep team-mode as the spine, put CE/solo content in a single annex doc, minimize cross-refs from standards docs back into it. Worth re-evaluating after the integration ships and adopters have read the new structure.
- **U7 (README update) scope**: scope-guardian and adversarial reviewers flagged this as not in issue #22's acceptance criteria and possibly speculative. Default: keep U7 (small, surfaces integration from front door, justifies its own ≤4 lines). Drop only if it creates real tension with discovery via `ai/CLAUDE.md` Quick Links.
- **`ce-compound`, `ce-compound-refresh`, `ce-debug` table entries**: U2's skill cross-reference table should explicitly state that these are meta-skills with no artifact-path output (verified via `ls ~/.claude/plugins/.../compound-engineering/3.1.0/skills/`). Avoid the table reading as half-filled.
- **Standards-side conflict resolution**: the precedence rule says "CE wins when CE produces the artifact" — but what about the inverse? If CE produces an artifact whose conventions conflict with a standards principle (e.g., a future CE skill that emits a non-Fibonacci estimation field), is the rule still "CE wins"? Adversarial reviewer flagged this as asymmetric. Likely answer: the rule is path/format precedence, not principle precedence — standards principles still apply within CE-produced artifacts. Capture in the integration doc only if real use surfaces a conflict.
- **Recursive-glob safety for `ai/`**: U4 moves archives to top-level `archive/`. Worth checking whether any other files in `ai/` (e.g., the original `ai/CLAUDE.md`) get loaded as policy by tools beyond Claude Code. Out of scope for this plan; flag if discovered during U3 implementation.

---

## Implementation Units

- U1. **ADR — Adopt compound-engineering as the AI workflow standard**

**Goal:** Capture the decision to integrate CE with the engineering standards by **framing CE as a deep specialization of Layers 2 and 3** of the 4-layer AI architecture this repo already ships. State the layering explicitly so future readers see the architectural relationship without re-deriving it. Defend the choice to load CE as the Layer 2/3 specialization for rmorison projects (rather than building the depth ourselves), and point to U2 for operational details.

**Requirements:** R1, R5, R12, R15

**Dependencies:** None.

**Files:**
- Create: `docs/README.md` (one-paragraph stub: "this directory holds documentation per `process/documentation-standards.md`; current contents: `engineering/adr/`, `plans/`")
- Create: `docs/engineering/README.md` (one-paragraph stub pointing into `adr/` with a note that `designs/` would live here too when written)
- Create: `docs/engineering/adr/0001-compound-engineering-integration.md`

**Approach:**
- Create the directory tree (`docs/`, `docs/engineering/`, `docs/engineering/adr/`). `docs/plans/` already exists (this plan lives there).
- Create the two README stubs to honor `process/documentation-standards.md` line 125.
- Use the lightweight ADR format described in `process/documentation-standards.md` (Decision / Context / Consequences / References). Keep it ≤2 pages.
- **Decision**: adopt compound-engineering (CE) v3.1.0+ as the deep specialization of Layers 2 (Skills) and 3 (Agents) of this repo's 4-layer AI architecture. State the layering explicitly: the 4-layer model is the abstraction; CE fills Layers 2 and 3 with deep, vendor-coupled implementations when the plugin is installed. The vendor-neutral baseline (`templates/.claude/skills/`, `templates/.claude/agents/`) remains the default for projects without CE. Layer 1 (Rules) and Layer 4 (Hooks) are unchanged; their content is updated to be CE-aware where it conflicts (R14).
- **Context**: PRs #16/#19/#21 (~5 weeks ago) shipped the 4-layer model. CE is in active use across `rmorison` projects (most concretely `books-ops`). The relationship between the two has been re-derived per project. This ADR establishes the architectural layering that resolves the re-derivation tax.
- **The layering — Why this framing (R15)**: subsection establishing the 4-layer abstraction + CE specialization explicitly. Layer 1 (Rules) holds always-loaded session context; Layer 2 (Skills) is on-demand workflows; Layer 3 (Agents) is specialized subagents; Layer 4 (Hooks) is deterministic shell-level enforcement. CE provides Layer 2 and Layer 3 implementations that are deeper than the templates' vendor-neutral defaults (~30 skills vs 3, ~20 persona reviewers vs 2). CE doesn't ship Layer 1 or Layer 4 content; those continue to come from this repo. The 4-layer principle ("context is expensive — only load what's needed, when it's needed") is exactly CE's design philosophy; CE embodies it more deeply than the 4-layer's own thin skills did.
- **Why CE rather than building the depth ourselves (R12)**: subsection defending the choice to install CE as the Layer 2/3 specialization rather than expanding the vendor-neutral skills toward CE-level depth. Alternative considered: build deeper Layer 2 and Layer 3 implementations in `templates/.claude/skills/` and `templates/.claude/agents/`, vendor-neutral. Rejected because (a) CE already provides this depth and is actively maintained, (b) duplicating it would be a maintenance liability against an evolving target, (c) the layering preserves vendor-neutrality at the 4-layer's own depth — adopters who don't run CE retain a working baseline. **Upgrade discipline**: pin to CE 3.x; re-evaluate at 4.x.
- **Consequences**: list what changes (Layer 2/3 default-when-CE-installed, solo-mode is first-class, AI-review **discipline** — not enforced gate, precedence rule with provenance clause for artifact paths), what stays unchanged (ADR location, semver, conventional commits, PR-based merges, code quality principles, the 4-layer model itself, the vendor-neutral templates), and explicitly note the maintenance liability the vendor coupling creates at the specialization layer.
- **References**: issue #22, the integration doc (U2), PRs #16/#19/#21 (the 4-layer model — referenced as foundational, not superseded), the three archived `ai/*.md` proposals (superseded — they proposed building agent-native abstractions ourselves rather than using the 4-layer + CE specialization framing), and books-ops as a real-world deployment example (qualified: "private repo, named for context not as a reference").
- Number 0001 since no ADRs exist yet in this repo.

**Patterns to follow:**
- ADR shape from `process/documentation-standards.md` lines 83–92.

**Test scenarios:**
- Test expectation: none — documentation change. Verification is structural review per the next field.

**Verification:**
- ADR exists at `docs/engineering/adr/0001-compound-engineering-integration.md`.
- `docs/README.md` and `docs/engineering/README.md` exist as minimal stubs.
- Sections present: Decision / Context / The layering — Why this framing / Why CE rather than building the depth ourselves / Consequences / References.
- The layering subsection explicitly names the 4-layer model (with all four layers) and identifies CE as the deep specialization of Layers 2 and 3.
- Precedence rule with provenance clause stated unambiguously for artifact paths.
- Consequences explicitly distinguish "review discipline" from "enforced merge gate."
- The 4-layer's principle ("context is expensive — only load what's needed") is restated and credited as CE's design philosophy too.
- Pointer to `process/compound-engineering-integration.md` (U2) is present.
- References include issue #22, PRs #16/#19/#21 (foundational, not superseded), the three archived prior proposals, and books-ops qualified as real-world deployment, not canonical reference.

---

- U2. **Process doc — compound-engineering integration (self-contained, not pointer-only)**

**Goal:** Operational reference that resolves the path conflicts, ceremony scaling, branch-naming reconciliation, and AI-review discipline. **The doc is self-contained**: it inlines the load-bearing tables and paragraphs (Documentation Paths, Review Discipline, Ticket Policy) directly so a public reader without rmorison access can apply it without 404ing on books-ops links.

**Requirements:** R2, R4, R5, R6, R7, R12, R13

**Dependencies:** U1 (the doc references the ADR by number).

**Files:**
- Create: `process/compound-engineering-integration.md`

**Approach:**
- Header section: scope statement, audience ("projects using compound-engineering — most concretely the `rmorison` projects, but the integration is intended to be readable and usable by any adopter"), and the precedence rule with provenance clause (R13).
- Five sections per issue #22:
  1. **Artifact location mapping** — full table including `docs/solutions/` row (R6). Inline the table content directly into the integration doc (do not point at books-ops). State the precedence rule and the provenance clause (first-skill-touched-the-file; explicit `provenance:` frontmatter override). Sample row format mirrors books-ops' battle-tested table:

     | Path | Owner | Producer |
     | --- | --- | --- |
     | `docs/ideation/` | CE | `ce-ideate` |
     | `docs/brainstorms/` | CE | `ce-brainstorm` — also serves as Phase 0 / discovery artifact for `process/feature-development-workflow.md`; Phase 1 is seeded from the brainstorm |
     | `docs/plans/` | CE | `ce-plan` (subsumes `docs/planning/` from the standards) |
     | `docs/solutions/` | CE | `ce-compound`, `ce-compound-refresh` (no standards analog) |
     | `docs/engineering/adr/` | shared | human-authored ADRs (path identical in both models) |
     | `docs/engineering/designs/` | standards | human-authored design docs |
     | `docs/product/` | standards | human-authored product concepts and feature specs |

  2. **Issue-tracking modes** — three modes: team-scale (full three-tier hierarchy from `process/issue-tracking.md`), solo + AI (reactive issue creation, plan U-IDs as unit tracker), hybrid (solo today, team tomorrow — adopt lean now, add epics/milestones when a second contributor arrives). Cite the existing solo carve-outs in `process/issue-tracking.md` lines 359–373 ("<3 issues: just use labels", "<1 month: might not need epic structure") as the foundation rather than inventing new ones. Inline a minimal Ticket Policy block (umbrella epic per multi-phase plan, sub-issues reactive, U-aligned branch naming) so adopters do not need to read books-ops to see the pattern.

  3. **Branch-naming reconciliation** — issue-numbered when an issue exists, topic-style (`feat/...`, `fix/...`) when produced by `lfg` / `ce-work` without a parent issue. Standards' rule applies once an issue is opened. State that this works in concert with U5's anti-pattern reframe.

  4. **Solo-scale adaptations + AI-review discipline** — what shifts at solo scale: no planning poker (point estimates become self-calibration; cite `process/project-planning-standards.md` line 86), no human code-review assignment (replaced by AI-review **discipline**, definition follows), milestones earn their keep at >3-month horizons, epic structure earns its keep at 5+ implementation issues per feature.
     - **AI-review discipline (R7, revised)**: a sub-block stating clearly: **this is review discipline, not an enforced merge gate.** No CI check, no branch-protection automation, no PR template enforces it — claiming otherwise would be aspirational documentation. The discipline names: (a) `ce-code-review` on the diff before merge; (b) `ce-doc-review` on the plan or spec when applicable; (c) self-review against plan acceptance criteria.
     - **Failure modes the discipline does not catch** (named explicitly so adopters can compensate): cross-PR scope drift (AI reviewers see one diff at a time and rarely flag missing requirements that span PRs); self-grading loops (in solo mode the implementer decides what "unresolved" means); product-positioning regressions (AI reviewers tuned for code patterns miss strategic intent); same-intent author-and-reviewer collapse (no second pair of eyes with independent stakes).
     - When a human reviewer onboards, the standards' "Require at least 1 approval" rule re-engages and AI-review becomes complementary.

  5. **Compound-engineering skill ↔ standards doc cross-reference** — table mapping CE skills (`ce-brainstorm`, `ce-plan`, `ce-work`, `ce-code-review`, `ce-doc-review`, `lfg`, `ce-compound`, `ce-compound-refresh`, `ce-debug`) to the standards docs they operate within. **Each row describes behavior alongside the skill name** (e.g., "the skill that produces a brainstorm requirements doc — currently `ce-brainstorm` — seeds Phase 1 of `process/feature-development-workflow.md`"). For meta-skills with no artifact output (e.g., `ce-compound-refresh`, `ce-debug`), the row says so explicitly so the table does not read as half-filled. Note the upgrade discipline: pin to CE 3.x; re-evaluate at 4.x major version.
- Footer: **"Real-world deployment example"** subsection (renamed from "Working example") naming `books-ops` with one paragraph qualifying it as a private rmorison deployment, not as a doc reference. No line-range citations.
- Use repo-relative paths everywhere. Do not point at the books-ops repo for content the integration doc itself should carry.

**Patterns to follow:**
- `process/issue-tracking.md` voice and structure for the issue-tracking modes section.
- `process/git-branching-strategy.md` voice for the branch-naming reconciliation section.

**Test scenarios:**
- Test expectation: none — documentation change. Verification is structural review per the next field.

**Verification:**
- All five sections present.
- `docs/solutions/` row in the mapping table; precedence rule + provenance clause stated explicitly.
- Documentation Paths table is inlined (not linked to books-ops).
- AI-review discipline section names: (a) what's checked, (b) the four failure modes, (c) explicit "discipline, not enforced gate" framing.
- Ticket Policy block inlined so adopters can apply without external reference.
- `books-ops` named only as real-world deployment, never as canonical reference.
- A reader without rmorison repo access can apply the integration doc end-to-end.
- No team-scale standards weakened — re-reading every cross-reference shows additive language ("when in solo CE mode...") rather than subtractive ("the standard no longer applies").
- Skill name changes within CE 3.x wouldn't break the doc (behaviors described alongside names).

---

- U3. **Update `ai/CLAUDE.md` AND `ai/claude-code/rules/` — inline-replace conflicting rules, add CE precedence**

**Goal:** The highest-leverage change. Agents read these files every turn. Inline-replace the conflicting content (workflow paths, branch-naming rule, "wait for confirmation before implementing") so an agent reading top-down does not execute a standards rule that contradicts CE before reaching any override. Side-by-side was rejected because the existing files contain both workflow paths *and* the unqualified branch-naming rule, which directly contradict CE behavior.

**Requirements:** R8, R9, R14

**Dependencies:** U1, U2 (sections point at both).

**Files:**
- Modify: `ai/CLAUDE.md`
- Modify: `ai/claude-code/rules/engineering-standards.md` (always-loaded; conflicts on `docs/` tree at lines 27–37 and branch-naming rule at line 44)
- Modify: `ai/claude-code/rules/sdlc-workflow.md` (always-loaded; "Plan Before Implementing... Wait for explicit confirmation" at lines 13–18 contradicts `lfg`)
- Modify: `ai/claude-code/README.md` (describes the 4-layer model; needs supersession note pointing at the ADR + integration doc)

**Approach:**

For **`ai/CLAUDE.md`**:
- **Replace** the existing Documentation Structure block (lines ~54–66) with a two-mode block: "Standards mode (default):" followed by the existing tree, "When using compound-engineering:" followed by the CE path-ownership table inlined from U2. Both modes remain visible — the change is structural reframing, not deletion.
- **Replace** the unqualified branch-naming line (`ai/CLAUDE.md` line 41: `**Branch naming**: {issue-number}-{slugified-title}`) with a two-mode version: "Standards mode: `{issue-number}-{slugified-title}`. When using compound-engineering: also accepts topic-style `feat/...` / `fix/...` for `lfg` / `ce-work` flows without a parent issue. See `process/compound-engineering-integration.md`."
- **Replace** the Feature Development Workflow numbered list (lines ~24–29) with a two-mode version: standards-mode list (unchanged) and CE-mode list (Phase 0 = `docs/brainstorms/`, Phase 1 seeded from brainstorm, Phase 3-4 outputs at CE-mode paths). This addresses R9 directly in the highest-leverage file.
- **Insert** a new "When using compound-engineering" section after the existing Quick Reference block containing: (a) one-line precedence statement with provenance clause summary; (b) pointer to the ADR (U1) and integration doc (U2); (c) one-paragraph framing of AI-review as discipline (not gate); (d) link to the integration doc for the full path-ownership table.
- Update the Quick Links section at the bottom to include the new ADR and integration doc.
- Do NOT cite `books-ops/CLAUDE.md` from `ai/CLAUDE.md` — the integration doc is the authoritative reference for CE-mode behavior.

For **`ai/claude-code/rules/engineering-standards.md`** (always-loaded):
- **Replace** the hardcoded `docs/` tree block (lines 27–37) with a two-mode version mirroring the `ai/CLAUDE.md` treatment: "Standards mode" tree (unchanged), "When using compound-engineering" tree (CE paths). Pointer to integration doc.
- **Replace** the unqualified Branching line (line 44: `**Branch names**: {issue-number}-{slugified-title}`) with the same two-mode version as `ai/CLAUDE.md`.
- **Add** a "When using compound-engineering" subsection at the end pointing at the ADR (U1) and integration doc (U2). One paragraph plus links.

For **`ai/claude-code/rules/sdlc-workflow.md`** (always-loaded):
- **Replace** the "Plan Before Implementing" section (lines 13–18) with a two-mode version: "Standards mode: author a plan and present it before writing any code. Wait for explicit confirmation before proceeding." / "When using compound-engineering: `/ce-plan` produces the plan; `/ce-work` executes it iteratively. The `lfg` autonomous flow runs without per-step confirmation by design — the plan and CE-doc-review steps capture intent up-front instead of via inline approval. Use `lfg` only when you have a complete plan; otherwise default to `/ce-plan` → `/ce-work` with explicit handoff."
- Other sections (Read Before Changing, Validate After Each Change, Flag Uncertainty, Scope Discipline) are CE-compatible and need no change. Add a one-line top pointer at the file's intro: "When working with compound-engineering, see also `process/compound-engineering-integration.md`."

For **`ai/claude-code/README.md`** (4-layer model description) — this is the **load-bearing architecture doc** for new adopters; expand it to explicitly state CE as the Layer 2/3 specialization:
- **Update the intro** to state the layering plainly: "This directory defines the AI artifacts layer. Four layers organize AI tooling by context cost. CE specializes Layers 2 and 3 with deep implementations when the plugin is installed; the layers themselves are the abstraction."
- **Update the Layer 2 (Skills) row**: keep the existing description of `templates/.claude/skills/{spec,plan,review}/` as the vendor-neutral default; **add** a sentence: "When [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) is installed, CE skills (`/ce-brainstorm`, `/ce-plan`, `/ce-work`, `/ce-doc-review`, `/ce-code-review`, `lfg`, etc.) are the deep specialization of this layer. CE-using projects default to those skills; non-CE projects use the templates' skills. See `process/compound-engineering-integration.md`."
- **Update the Layer 3 (Agents) row**: keep the existing description of the templates' agents as the vendor-neutral default; **add** a sentence: "When CE is installed, CE persona reviewers (~20 specialized agents covering coherence, feasibility, adversarial, security, performance, etc.) are the deep specialization of this layer."
- Layers 1 (Rules) and 4 (Hooks) descriptions unchanged structurally; Layer 1 row gets a one-line note that `ai/claude-code/rules/` content is CE-aware (see U3 changes to those rule files).
- **Add** a "When you adopt CE" subsection at the end with: install pointer, link to the ADR (U1) and integration doc (U2), and a one-paragraph framing reiterating the layering (CE is the deep specialization; the 4-layer architecture itself is unchanged).
- The file remains the load-bearing description of the AI architecture; it gains depth, does not get superseded.

**Patterns to follow:**
- Existing `ai/CLAUDE.md` voice — terse, table-heavy, links-out-to-detail.

**Test scenarios:**
- Test expectation: none — documentation change. Verification is structural review per the next field.

**Verification:**
- `ai/CLAUDE.md`: Documentation Structure block has explicit baseline / "When using compound-engineering" sub-blocks; branch-naming line carries both rules; Feature Development Workflow numbered list reflects both modes; Phase 0 = `docs/brainstorms/` declared (R9); precedence rule + provenance clause summary present; AI-review described as discipline, not enforced gate; Quick Links updated.
- `ai/claude-code/rules/engineering-standards.md`: `docs/` tree two-mode; branch-naming line two-mode; CE-mode subsection at end pointing at ADR + integration doc.
- `ai/claude-code/rules/sdlc-workflow.md`: Plan-Before-Implementing section two-mode (CE-mode covers `lfg` autonomous flow); top pointer to integration doc.
- `ai/claude-code/README.md`: intro states the layering explicitly (4-layer abstraction + CE as Layer 2/3 specialization); Layer 2 and Layer 3 rows describe both vendor-neutral defaults and CE specializations; "When you adopt CE" subsection present at end. The file is **enriched, not deprecated**.
- An agent reading any of these files top-down sees the layering before any specific workflow rule; both vendor-neutral and CE-mode rules remain visible and unambiguously labeled.
- All four files explicitly stress the layering in their intros or top-level structure (per the user-stated requirement that top-level docs make this load-bearing).

---

- U4. **Archive 3 prior `ai/` proposals**

**Goal:** Decisive break from the genuine path-not-taken (build agent-native abstractions ourselves rather than use the 4-layer + CE specialization framing) by relocating three untracked proposal docs to top-level `archive/` with banners pointing at the new ADR. **The 4-layer model that shipped via PRs #16/#19/#21 is NOT archived** — it is the abstraction CE specializes; archiving it would defeat the layering this plan is built on.

**Requirements:** R11

**Dependencies:** U1 (banner references the ADR number).

**Files:**
- Move: `ai/adoption-roadmap.md` → `archive/adoption-roadmap.md`
- Move: `ai/agent-native-improvements.md` → `archive/agent-native-improvements.md`
- Move: `ai/top-3-enhancements.md` → `archive/top-3-enhancements.md`
- Create: `archive/README.md` (short explainer)

**Kept in place** (NOT archived; they are the vendor-neutral baselines of Layers 2 and 3 of the 4-layer architecture):
- `templates/.claude/skills/{spec,plan,review}/SKILL.md`
- `templates/.claude/agents/{code-reviewer,spec-writer}.md`
- `templates/.claude/hooks/` and `templates/.claude/settings.json` (orthogonal Layer 4 / configuration)
- `templates/CLAUDE.md` (project template — gets CE-aware additions in U8)
- `ai/claude-code/README.md` and `ai/claude-code/rules/*.md` (Layer 1 description and content — get CE-aware updates in U3, not archived)

**Approach:**

The three files are currently untracked (per `git status`), so `git mv` would fail with "not under version control." Use: `mkdir -p archive && mv ai/<file>.md archive/<file>.md`, then `git add archive/`. The archival commit is these files' first appearance in history.

Why top-level `archive/` and not `ai/archive/`: agents that recursively load `ai/**/*.md` would still ingest the docs; adopters who pull the `ai/` subtree wholesale into a new project would inherit them. Top-level `archive/` removes both failure modes.

Banner for each archived file (relative path `../docs/engineering/adr/...` — files are 1 level deep under archive/):
```
> **Implementation strategy superseded by [ADR-0001: Compound Engineering Integration](../docs/engineering/adr/0001-compound-engineering-integration.md).**
>
> This document analyzed agent-native principles and proposed building these abstractions in this repo. We instead adopted the 4-layer AI architecture (PRs #16/#19/#21) plus [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) as the deep specialization of Layers 2 and 3. Kept here as the evaluative framework that informed the layering decision — the analysis remains the lens for re-evaluating the architecture if circumstances change. See `process/compound-engineering-integration.md` for the current operational doc.
```

`archive/README.md`: short explainer (one section) describing the three archived docs as the agent-native-analysis path-not-taken, naming the layering chosen instead. Briefly lists the three files with one-line summaries.

**Patterns to follow:**
- None specific. Banner format mirrors how superseded ADRs are typically marked.

**Test scenarios:**
- Test expectation: none — file moves and banner additions. Verification is structural per the next field.

**Verification:**
- All three `ai/*.md` proposals exist at `archive/<name>.md`, with banners and working ADR links.
- `ls ai/` shows the three files are gone; `ls archive/` shows them present.
- Recursive globs against `ai/**/*.md` no longer return the archived content.
- `archive/README.md` exists with the short explainer.
- **NOT archived (verified still in place)**: `templates/.claude/skills/{spec,plan,review}/`, `templates/.claude/agents/{code-reviewer,spec-writer}.md`, `templates/.claude/hooks/`, `templates/.claude/settings.json`, `templates/CLAUDE.md`, `ai/claude-code/README.md`, `ai/claude-code/rules/*.md`. These are the vendor-neutral baseline and Layer 1 content; they receive CE-aware updates in U3 and U8 but stay in place.

---

- U5. **Update `process/git-branching-strategy.md` — anti-pattern reframe + cross-ref**

**Goal:** Address Claude review gap #5 (R10): the "❌ Branches Without Issues" anti-pattern is a direct contradiction of `lfg` and `ce-work` flows. Reframe to add a CE carve-out, then add the standard "When using compound-engineering" pointer.

**Requirements:** R3, R10

**Dependencies:** U2 (cross-ref points at integration doc).

**Files:**
- Modify: `process/git-branching-strategy.md`

**Approach:**
- Edit the "❌ Branches Without Issues" anti-pattern (lines 287–291) to add a one-line carve-out: *"Exception: `lfg` and `ce-work` autonomous flows may produce topic-style branches (`feat/...`, `fix/...`) without a parent issue. File an issue retroactively only if review surfaces something worth tracking. See `process/compound-engineering-integration.md`."*
- Add a "When using compound-engineering" pointer paragraph near the top of the file (after the Overview section): one-line note with link to integration doc.
- **Required (R7 cross-ref)**: tweak the Branch Protection block (lines 322–331) to add a one-line note that the "Require at least 1 approval" rule has a CE-mode complement (the AI-review **discipline** defined in `process/compound-engineering-integration.md`). Frame as discipline, not enforced gate; preserve the existing rule. This row delivers the R7 forward-pointer; previously this was marked optional.
- Do not rewrite the GitHub Flow guidance — it stands.

**Patterns to follow:**
- Existing voice / formatting in the file.

**Test scenarios:**
- Test expectation: none — documentation change. Verification per the next field.

**Verification:**
- Anti-pattern carve-out present and points at the integration doc.
- Cross-ref pointer present near the top.
- Branch protection block carries the R7 cross-ref note (required) — preserves the team-scale rule and adds the CE complement, framed as discipline not enforced gate, never weakening.

---

- U6. **Cross-references in remaining four standards docs**

**Goal:** Add the minimal "When using compound-engineering" pointers required by issue #22's acceptance criterion, plus the targeted update for review gap #4 (Phase 0 = brainstorm in feature workflow). R7 is delivered by U2 + U5 promotion; no longer attributed to U6.

**Requirements:** R3, R5, R9

**Dependencies:** U2.

**Files:**
- Modify: `process/feature-development-workflow.md`
- Modify: `process/issue-tracking.md`
- Modify: `process/project-planning-standards.md`
- Modify: `process/documentation-standards.md`

**Approach:**
- **`process/feature-development-workflow.md`** — add a "When using compound-engineering" note in or just before Phase 1 (lines 40–46) declaring that `docs/brainstorms/<topic>-requirements.md` (the `ce-brainstorm` output) IS the Phase 0 / discovery artifact and that Phase 1 (Product Concept) is seeded from it (R9). Pointer to integration doc.
- **`process/issue-tracking.md`** — add a "When using compound-engineering" cross-ref near the Three-Tier Hierarchy section (around line 19) pointing at the integration doc's solo-mode subsection. Cite the existing carve-outs at lines 359–373 as the foundation. No structural change.
- **`process/project-planning-standards.md`** — add a "When using compound-engineering" cross-ref near the Team Estimation section (lines 79–86) noting that for solo CE work, point estimates in CE plan files serve as self-calibration; planning poker is N/A. Pointer to integration doc.
- **`process/documentation-standards.md`** — add a "When using compound-engineering" cross-ref in or near the Directory Structure section (lines 9–47) noting that CE-skill outputs live at `docs/brainstorms/`, `docs/ideation/`, `docs/plans/`, `docs/solutions/` per the integration doc's path mapping. No structural change.
- Each cross-ref is 1–3 lines, additive, points at `process/compound-engineering-integration.md`. No team-scale standards weakened.

**Patterns to follow:**
- Existing voice in each file. Match the existing cross-ref style (e.g., the way `process/feature-development-workflow.md` already cross-refs `process/project-planning-standards.md`).

**Test scenarios:**
- Test expectation: none — documentation changes. Verification per the next field.

**Verification:**
- All four files have a CE cross-ref.
- Phase 0 = brainstorm note exists in feature-development-workflow.md (R9).
- Solo-mode pointer in issue-tracking.md cites existing carve-outs (R5: not weakening).
- Planning poker N/A note in project-planning-standards.md cites the existing line 86 carve-out (R5: not weakening).
- Documentation paths note in documentation-standards.md.

---

- U7. **Add CE-as-specialization subsection to README + Process Standards entry**

**Goal:** Make the integration discoverable from the README without disturbing the existing 4-layer description (which remains accurate). The 4-layer is the abstraction; CE is the specialization. The README's existing AI Integration section already describes the abstraction correctly; we add the specialization subsection alongside it. **This is critical for new-adopter onboarding** — the README is the front door; the layering must be visible there.

**Requirements:** R3, R5, R16

**Dependencies:** U1, U2.

**Files:**
- Modify: `README.md`

**Approach:**
- In the existing "AI / Claude Code Integration" section (lines 96–117): **add** a brief "When the compound-engineering plugin is installed" subsection right after the existing 4-layer list. The subsection states (in 1–2 paragraphs):
  - "CE specializes Layers 2 (Skills) and 3 (Agents) of the architecture above. When CE is installed, its skills (`/ce-brainstorm`, `/ce-plan`, `/ce-work`, `/ce-code-review`, `/ce-doc-review`, `lfg`, etc.) and persona reviewers replace the templates' vendor-neutral defaults for those layers. Layers 1 (Rules) and 4 (Hooks) are unchanged."
  - "See [ADR-0001](docs/engineering/adr/0001-compound-engineering-integration.md) for the architectural decision and [`process/compound-engineering-integration.md`](process/compound-engineering-integration.md) for adoption details."
- In the existing 4-layer table: **add** to the Layer 2 row a parenthetical "(or CE skills when CE is installed)"; same for Layer 3 with "(or CE persona reviewers)". Layers 1 and 4 unchanged.
- **Add** a Process Standards entry for `process/compound-engineering-integration.md` between the existing Issue Tracking section and the AI / Claude Code Integration section. One paragraph, ≤4 lines.
- **Add** one line under "Applying These Standards" noting that projects using the compound-engineering plugin should consult the integration doc for path mapping and review discipline.
- Do not restructure other sections; do not rewrite the 4-layer description.

**Patterns to follow:**
- Existing README voice. The 4-layer description's "Key principle" framing stays — it applies to CE too.

**Test scenarios:**
- Test expectation: none — documentation change. Verification per the next field.

**Verification:**
- README's "AI / Claude Code Integration" section retains the existing 4-layer description verbatim.
- Layer 2 and Layer 3 rows of the layer table carry parenthetical CE-specialization notes.
- A new "When the compound-engineering plugin is installed" subsection follows the layer description.
- README has a Process Standards entry for the integration doc.
- "Applying These Standards" section includes a CE pointer.
- A reader landing on the README first sees the 4-layer abstraction, then the CE specialization — the architecture is visible before any specific workflow.
- The README explicitly stresses the layering (per the user-stated requirement: "make sure top-level docs stress this").

---

- U8. **Add CE-aware section to `templates/CLAUDE.md`**

**Goal:** Templates ship as a starter kit. Adopters who copy `templates/CLAUDE.md` into a CE-using project should see CE-mode guidance reflecting the layering — without disrupting the template for non-CE adopters.

**Requirements:** R15

**Dependencies:** U2 (the new section references the integration doc).

**Files:**
- Modify: `templates/CLAUDE.md`

**Approach:**
- Edit the "Plan Before Implement" section (lines 14–17) to add a one-line CE-aware note: "When the compound-engineering plugin is installed, `/ce-plan` produces the plan and `/ce-work` executes it; `lfg` runs autonomously without per-step confirmation. See `process/compound-engineering-integration.md` for the full pattern."
- Edit "Standards References" (lines 19–22) to add a line: "- Compound-engineering integration (when CE is installed): process/compound-engineering-integration.md"
- Add a brief "AI Architecture" section after "Standards References" with one paragraph explaining the layering: "This template assumes the 4-layer AI architecture defined in `ai/claude-code/README.md`. Layers 1 (Rules) and 4 (Hooks) are filled by the standards repo's `ai/claude-code/rules/` and `templates/.claude/hooks/`. Layers 2 (Skills) and 3 (Agents) are filled by `templates/.claude/skills/` and `templates/.claude/agents/` by default; when [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) is installed, CE skills and persona reviewers specialize those layers."
- Do not restructure other sections (Module Boundaries, Validation, Project Identity).
- `templates/.claude/settings.json` is not modified — its `permissions.allow` list is reasonable and CE-compatible as-is.

**Patterns to follow:**
- Existing `templates/CLAUDE.md` voice — minimal, placeholder-driven.

**Test scenarios:**
- Test expectation: none — documentation change. Verification per the next field.

**Verification:**
- `templates/CLAUDE.md`: Plan-Before-Implement carries CE-aware note; Standards References lists the integration doc; new "AI Architecture" section explains the layering.
- An adopter who copies the template to either a CE-using or non-CE project gets correct guidance — the layering tells them what to expect either way.

---

## System-Wide Impact

- **Interaction graph:** AI agents reading `ai/CLAUDE.md` (U3) get the precedence rule first, then follow pointers to the ADR (U1) and integration doc (U2). The integration doc is the load-bearing operational reference; the cross-refs in the five process docs (U5, U6) are signposts back to it. The README update (U7) is the human-discovery entry point.
- **Error propagation:** If the integration doc drifts out of sync with CE behavior (e.g., a skill name change), the failure mode is "agent reads the doc, can't find the named skill, falls back to behavior description." The doc's structure (behavior described alongside name in the cross-reference table) bounds the blast radius.
- **State lifecycle risks:** None — this is a documentation change with no runtime state.
- **API surface parity:** N/A — no APIs.
- **Integration coverage:** The acceptance criterion that "no team-scale standards are weakened" requires re-reading every cross-ref in U5/U6 to verify additive (not subtractive) language. Catch this in Verification on each unit, then again in the final review (Phase 5.1).
- **Unchanged invariants:** ADR location (`docs/engineering/adr/`), Fibonacci estimation scale, conventional commits, `main` always deployable, PR-based merges, GitHub Flow, semver, code quality principles, documentation formats. The integration doc and ADR confirm these explicitly.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| The integration doc tries to be both prescriptive (override standards) and descriptive (document books-ops) and reads confusingly. | Clear section structure: prescriptive material in the five named sections; books-ops mentioned only in a "Real-world deployment example" footer with no line-range citations. Load-bearing tables and paragraphs are inlined, not pointed at. Re-read for tone in Phase 5.1. |
| `ai/CLAUDE.md` rewrite breaks non-CE adopters who copy this template. | Inline replacement uses explicit "Standards mode (default):" / "When using compound-engineering:" sub-blocks; both modes remain visible. A non-CE adopter's reading is unchanged in semantics — only the structure is reframed. |
| CE skill names change in a future plugin version, breaking the cross-reference table in U2. | Describe behavior alongside skill names ("the skill that produces a brainstorm requirements doc — currently `ce-brainstorm`"). Localizes the rot. Upgrade discipline pinned at CE 3.x with re-evaluation at 4.x major version (R12). |
| AI-review discipline (R7) is misread as an enforced gate, leading to false confidence. | The integration doc explicitly frames the discipline as "process discipline, not enforced by repo configuration." Failure modes named explicitly (cross-PR scope drift, self-grading loops, product-positioning regressions, same-intent author/reviewer). Adopters know what they're trading. |
| Single-PR scope (~400–500 lines / ~10–12 files) is close to `process/git-branching-strategy.md`'s 200-400-line target after specialization-framing pass. | The standard has no formal PR-size deviation clause. The artifacts cross-reference each other (ADR ↔ integration doc ↔ `ai/CLAUDE.md` ↔ `ai/claude-code/rules/` ↔ README), so single-PR scope is the right call at this size. Split is still possible if review surfaces seams. |
| Layer-architecture framing is novel to this repo and may not land if not stressed in top-level docs. | U1 (ADR), U3 (`ai/claude-code/README.md`, `ai/CLAUDE.md`), U7 (README), U8 (`templates/CLAUDE.md`) all explicitly state the layering. The framing is repeated across the doc surface so a reader who lands anywhere sees it. |
| Vendor coupling to CE/EveryInc creates a maintenance liability against a roadmap the repo doesn't control. | ADR carries a "Why this plugin specifically" subsection (R12) defending the choice and stating the upgrade discipline. The standards repo's audience is small enough to make pinning lower-cost than maintaining vendor-neutral abstractions. Re-evaluation point: CE 4.x major version. |
| Precedence rule edge cases (co-authored docs, human-edited CE artifacts) leave provenance ambiguous in practice. | Provenance clause (R13) defines first-skill-touched-the-file as the default with explicit `provenance:` frontmatter override as the escape hatch. Stated in both the ADR and the integration doc. |
| books-ops working example is private; non-rmorison readers cannot verify referenced content. | Resolved by inlining all load-bearing content (Documentation Paths table, Review Discipline, Ticket Policy) directly into the integration doc. books-ops named only as "real-world deployment example" with no line-range citations. The integration doc is now self-contained for any public reader. |
| Three `ai/*.md` archived files are currently untracked; the archival commit looks unusual in history. | U4 approach explicitly addresses this: archival commit is the files' first appearance in history; no `git mv` for that batch (would fail on untracked files); banner makes the supersession explicit. The skill/agent batch IS tracked and uses `git mv` to preserve history. |
| Re-deriving "what fills Layer 2 / 3" per project remains a per-adopter decision. | The ADR + integration doc document the layering once; adopters copy `templates/CLAUDE.md` (with the AI Architecture section from U8) which carries the framing forward into their project. Books-ops becomes the working reference for "CE installed → CE specializes Layers 2/3." |

---

## Documentation / Operational Notes

- After merge: notify books-ops to refresh its CLAUDE.md to point at the now-published integration doc instead of the in-flight #22 reference. Books-ops' `CLAUDE.md` already says "see engineering-standards#22 for the in-flight upstream proposal" in two places; those become "see `process/compound-engineering-integration.md`." books-ops can also drop its locally-absorbed Documentation Paths table since the integration doc now carries it canonically.
- No CI changes, no migrations, no runtime impact. Pure documentation and three file relocations.
- Issue #12 (Add Phase 0 to feature workflow): R9 partially addresses it for CE-mode adopters by declaring `docs/brainstorms/` as the Phase 0 artifact. Before closing #12, verify whether its acceptance language requires Phase 0 for non-CE adopters too — if so, leave it open and capture the gap as a follow-up.
- Issues #16, #19, #21 (the 4-layer architecture): not closed by this PR. The ADR builds on their architecture (4-layer model is the abstraction; CE specializes Layers 2/3) — those issues remain valid completed work. No supersession comment needed; the relationship is described in the ADR and the integration doc.
- PR description: name the 4-layer-as-abstraction + CE-as-specialization framing prominently. The framing is the central architectural contribution of this PR; surfacing it in the description helps reviewers understand the structural choice before they evaluate individual file diffs.

---

## Sources & References

- **Origin issue:** [rmorison/engineering-standards#22](https://github.com/rmorison/engineering-standards/issues/22)
- **Real-world deployment example:** `books-ops` (private rmorison repo) — informed the integration doc's wording during real use of the brainstorm → plan → ce-doc-review → lfg pipeline. Not a doc reference; the integration doc inlines its own load-bearing content so public readers do not need books-ops access.
- **Related issue:** [rmorison/engineering-standards#12](https://github.com/rmorison/engineering-standards/issues/12) (Phase 0 — partially addressed by R9 for CE-mode adopters; verify acceptance language before closing)
- **Built on:** [rmorison/engineering-standards#16](https://github.com/rmorison/engineering-standards/issues/16) (4-layer AI architecture), [#19](https://github.com/rmorison/engineering-standards/issues/19) (README documentation of #16), [#21](https://github.com/rmorison/engineering-standards/issues/21) (PascalCase hook fix). The 4-layer model is the abstraction this plan extends with CE as the deep specialization of Layers 2 and 3.
- **CE plugin:** https://github.com/EveryInc/compound-engineering-plugin (v3.1.0; upgrade discipline pinned at 3.x with re-evaluation at 4.x)
- **Agent-native foundation:** https://every.to/guides/agent-native (the framework that informed the now-archived prior proposals; retained as the evaluative lens for re-evaluating CE adoption)
- **Archived prior `ai/` proposals:** `archive/adoption-roadmap.md`, `archive/agent-native-improvements.md`, `archive/top-3-enhancements.md` (after U4 — top-level `archive/`)
- **Affected files:** `process/feature-development-workflow.md`, `process/issue-tracking.md`, `process/project-planning-standards.md`, `process/documentation-standards.md`, `process/git-branching-strategy.md`, `ai/CLAUDE.md`, `ai/claude-code/rules/engineering-standards.md`, `ai/claude-code/rules/sdlc-workflow.md`, `ai/claude-code/README.md`, `templates/CLAUDE.md`, `README.md`
- **Doc-review provenance:** plan revised 2026-05-03 after two rounds of multi-persona review (coherence, feasibility, product-lens, scope-guardian, adversarial). Round 1 fixes: books-ops privacy resolved by inlining, AI-review reframed as discipline not gate, vendor coupling defended in ADR, precedence-rule provenance clause added, archives moved to top-level `archive/`. Round 2 surfaced the layer-architecture framing: the 4-layer model (PRs #16/#19/#21) and CE are at different levels of abstraction — 4-layer is the taxonomy of context-cost slots; CE is the deep specialization of Layers 2 and 3. Plan revised around this framing: dropped R15 (lightweight skill/agent archival) entirely, simplified R16 (additive README, not rewrite), reframed Key Technical Decisions, U1, U3, U4, U7, U8 around layering. Remaining round-2 findings (issue supersession comments, templates/README.md staleness, provenance frontmatter brittleness, archive directory naming) captured in Open Questions / From 2026-05-03 doc-review (deferred) where applicable; many became moot once R15 was dropped.
