# Compound Engineering Integration

*Operational reference for adopting compound-engineering as the canonical realization of Layers 2–5 of the [six-layer AI architecture](../ai/claude-code/README.md).*

**Architectural decision:** [ADR-0001](../docs/engineering/adr/0001-six-layer-ai-architecture.md).
**Audience:** projects using compound-engineering (CE) — most concretely the `rmorison` projects, but the integration is intended to be readable and usable by any adopter.
**Status:** active.

---

## Scope

This document describes how compound-engineering ([CE](https://github.com/EveryInc/compound-engineering-plugin), v3.x) realizes the six-layer AI architecture in the engineering-standards repository, and resolves the operational details that surface when CE coexists with these standards: artifact path conventions, issue-tracking ceremony scaling, branch-naming reconciliation, AI-review discipline, and ticket-tracking modes.

For the architecture itself, see [`ai/claude-code/README.md`](../ai/claude-code/README.md). This doc is the operational complement.

**Precedence rule with provenance clause.** When a CE skill produces an artifact, CE paths and conventions win. Standards paths and conventions own human-authored artifacts and ADRs. Edge cases:

- **First-skill-touched-the-file wins** by default. If `ce-plan` produced `docs/plans/foo.md`, subsequent human edits do not reclassify it as hand-authored.
- **Explicit reclassification** via a one-line `provenance:` frontmatter note (`provenance: hand-authored` or `provenance: ce-plan`) when the default rule produces the wrong answer.

---

## 1. How CE realizes the six layers

| # | Layer | Principle | What CE provides |
|---|-------|-----------|------------------|
| 1 | Rules | Persistence | *Not provided.* The standards repo's [`ai/claude-code/rules/*.md`](../ai/claude-code/rules/) retains ownership. Rule files carry one-line CE-aware pointers, not multi-mode policy. |
| 2 | Workflow Skills | Composability | ~30 skills covering discovery, planning, execution, review, debugging, and compounding. Pipeline shape: `ce-brainstorm → ce-plan → ce-work → ce-doc-review → ce-code-review → ce-compound`. The `lfg` skill runs the pipeline autonomously. |
| 3 | Persona Agents | Perspective | ~20 specialized review personas dispatched in parallel by `ce-doc-review` and `ce-code-review` skills. Persona names are stable in CE 3.x. |
| 4 | References | Progressivity | Each skill ships a `references/*.md` subtree loaded progressively as workflow depth grows. The pattern keeps Layer 2 skills lean at the entry point. |
| 5 | Compound / Learnings | Compounding | `ce-compound` captures learnings from completed work into `docs/solutions/`. `ce-compound-refresh` audits and consolidates. The compound output is itself a Layer 5 artifact. |
| 6 | Hooks | Determinism | *Not provided.* The standards repo's [`templates/.claude/hooks/`](../templates/.claude/hooks/) retains ownership. CE-mode invariants (e.g., warn if `/plan` is invoked instead of `/ce-plan`) can be added as hooks in follow-up work. |

For the canonical layer descriptions (vendor-neutral), see [`ai/claude-code/README.md`](../ai/claude-code/README.md). This table is the operational mapping.

---

## 2. Artifact location mapping

CE-using projects produce artifacts at paths the standards' `docs/` taxonomy does not name. The precedence rule (above) governs ownership; this table documents which paths are produced by which CE skill.

| Path | Owner | Producer / notes |
|------|-------|------------------|
| `docs/ideation/` | CE | `ce-ideate` output |
| `docs/brainstorms/` | CE | `ce-brainstorm` output. **Also serves as the Phase 0 / discovery artifact** for [`process/feature-development-workflow.md`](./feature-development-workflow.md); Phase 1 (Product Concept) is seeded from the brainstorm requirements doc. |
| `docs/plans/` | CE | `ce-plan` output. Subsumes the standards' `docs/planning/` for CE-using projects. |
| `docs/solutions/` | CE | Layer 5 artifacts produced by `ce-compound` and `ce-compound-refresh`. No standards analog yet. |
| `docs/engineering/adr/` | shared | Human-authored ADRs. Path identical in standards-mode and CE-mode. |
| `docs/engineering/designs/` | standards | Human-authored technical design documents. |
| `docs/product/` | standards | Human-authored product concepts and feature specs. |

**When in doubt:** if a CE skill produced the file, CE owns it. If a human authored it, standards conventions apply. The `provenance:` frontmatter override is available when the default heuristic produces the wrong answer.

---

## 3. Issue-tracking modes

[`process/issue-tracking.md`](./issue-tracking.md) describes a three-tier hierarchy (Milestone → Epic → Implementation Issue) sized for 3–5-person teams managing multi-month initiatives. CE-using projects often work at smaller scales where the full ceremony exceeds value.

Three modes apply:

### Team-scale (default)

Full three-tier hierarchy per [`process/issue-tracking.md`](./issue-tracking.md). Apply when:

- Multiple contributors coordinating on a multi-month initiative
- Stakeholder review cadence requires explicit milestone tracking
- Cross-team dependencies require visible epic structure

### Solo + AI

Reactive issue creation only. The plan file (`docs/plans/...`) is the granular unit tracker via U-IDs; pre-allocating per-U sub-issues duplicates state and drifts from the plan. Apply when:

- Sole contributor working with CE
- Plan U-IDs adequately track granular progress
- Issues created reactively for: `lfg` residuals, post-ship bugs, plan Open Question activations, scope expansions

The standards' [`process/issue-tracking.md`](./issue-tracking.md) already carries solo carve-outs at lines 359–373 ("<3 issues: probably doesn't need an epic, just use labels"; "<1 month: might not need epic structure"). Solo + AI mode is the natural extension of those carve-outs.

### Hybrid (solo today, team tomorrow)

Adopt solo + AI mode now; introduce epics and milestones when a second contributor arrives or a multi-month initiative emerges. The transition is incremental: existing plan U-IDs become epic sub-issues; new work follows team-scale ceremony.

### Ticket policy at solo + AI scale

A minimal pattern that has worked in real use:

- **One umbrella epic per multi-phase plan** (label: `epic`). The epic links to the plan; the plan is the granular tracker via U-IDs. Do not pre-allocate per-U sub-issues.
- **Sub-issues are reactive**, filed when needed: `bug`, `from-review` (review residuals), `from-deferred-q` (Open Question activations), `tech-debt`, `enhancement`. Add `blocked` when waiting on a dependency.
- **Branch naming** follows § 4 below.
- **Skip:** milestones, point/size labels, theme labels. Use the plan, not GitHub metadata, to express phase + scope.

---

## 4. Branch-naming reconciliation

[`process/git-branching-strategy.md`](./git-branching-strategy.md) prescribes `{issue-number}-{slugified-title}` and lists "❌ Branches Without Issues" as an anti-pattern. CE's `lfg` and `ce-work` autonomous flows can produce substantial work without a pre-existing issue.

**Rule.** When an issue exists, use the standards' `{issue-number}-{slugified-title}` format. When `lfg` or `ce-work` produces a branch without a parent issue, topic-style naming (`feat/...`, `fix/...`, `refactor/...`) is acceptable. File an issue retroactively only if review surfaces something worth tracking.

[`process/git-branching-strategy.md`](./git-branching-strategy.md) carries this carve-out in its anti-pattern section.

---

## 5. Solo-scale adaptations and AI-review discipline

### Solo-scale adaptations

What shifts at solo + AI scale, with citations to existing standards:

- **Estimation.** [`process/project-planning-standards.md`](./project-planning-standards.md) line 86 already permits solo estimation. For CE-using solo work, point estimates in CE plan files (`docs/plans/...`) serve as the self-calibration mechanism; planning poker is N/A.
- **Code review.** Standards assume a human reviewer. Solo + AI work substitutes the AI-review discipline below.
- **Milestones.** Earn their keep at >3-month horizons. Solo + AI work over shorter horizons typically uses plans (Layer 2 outputs) and reactive issues.
- **Epic structure.** Earns its keep at 5+ implementation issues per feature. Below that, plan U-IDs are the unit tracker.

### AI-review discipline (not enforced merge gate)

For solo + AI work, the human-reviewer slot in branch protection is replaced by an **AI-review discipline**. This is **process discipline, not a merge gate enforced by repo configuration**. There is no CI check, branch-protection automation, or PR template that enforces "no unresolved P0/P1 findings" — claiming otherwise would be aspirational documentation.

**The discipline names:**

1. **`ce-code-review`** on the diff before merge. Dispatches Layer 3 persona reviewers (security, reliability, performance, language-specific style, etc.) per the conditional triggers in the skill. Surfaces P0/P1 findings.
2. **`ce-doc-review`** on the plan or spec when applicable. Dispatches Layer 3 persona reviewers (coherence, feasibility, scope-guardian, adversarial, product-lens, etc.). Surfaces P0/P1 findings.
3. **Self-review against plan acceptance criteria.** The implementer verifies the unit's `Verification` field is satisfied before merge.

**Failure modes the discipline does not catch:**

- **Cross-PR scope drift.** AI reviewers see one diff at a time; missing requirements that span PRs are not flagged.
- **Self-grading loops.** In solo mode the implementer decides what "unresolved" means. A P1 finding the implementer disagrees with becomes "addressed" by judgment.
- **Product-positioning regressions.** AI reviewers tuned for code patterns miss strategic intent.
- **Same-intent author/reviewer.** No second pair of eyes with independent stakes.

Adopters who follow the discipline understand they are trading these failure modes for the speed of solo work. When a human reviewer onboards, the standards' "Require at least 1 approval" rule re-engages and AI review becomes complementary.

[`process/git-branching-strategy.md`](./git-branching-strategy.md) carries a one-line note in its branch protection block pointing at this discipline.

---

## 6. CE skill ↔ standards doc cross-reference

The table below maps each CE skill (Layer 2) to the standards doc(s) it operates within. Behavior is described alongside the skill name so that skill renaming within CE 3.x is a one-row table edit.

| CE skill | Behavior | Standards doc(s) it operates within |
|----------|----------|------------------------------------|
| `ce-ideate` | Open-ended ideation; produces `docs/ideation/` artifacts | Pre-Phase 1 of [`process/feature-development-workflow.md`](./feature-development-workflow.md) |
| `ce-brainstorm` | Structured requirements gathering; produces `docs/brainstorms/<topic>-requirements.md` | **Phase 0** of [`process/feature-development-workflow.md`](./feature-development-workflow.md); Phase 1 is seeded from the brainstorm output |
| `ce-plan` | Produces implementation plans at `docs/plans/...` with U-IDs and acceptance criteria | Phases 3–4 of [`process/feature-development-workflow.md`](./feature-development-workflow.md); subsumes `docs/planning/` for CE-using projects |
| `ce-work` | Executes a plan; manages task state and incremental commits | Phase 5 of [`process/feature-development-workflow.md`](./feature-development-workflow.md) |
| `ce-doc-review` | Dispatches Layer 3 persona reviewers against a plan or requirements doc; produces P0–P3 findings | Phase 4 review surface (plans, designs, ADRs) |
| `ce-code-review` | Dispatches Layer 3 persona reviewers against a code diff; produces P0–P3 findings | Phase 5 review surface (code review, the AI-review discipline above) |
| `ce-debug` | Systematic root-cause investigation; produces a debug record | Bug-fix work in [`process/technical-work-workflow.md`](./technical-work-workflow.md) |
| `ce-compound` | Captures learnings from completed work into `docs/solutions/` (Layer 5 output) | Phase 6 (validation/iteration) of [`process/feature-development-workflow.md`](./feature-development-workflow.md), or post-incident |
| `ce-compound-refresh` | Audits and consolidates `docs/solutions/`; supersedes outdated learnings | Maintenance of Layer 5 artifacts |
| `lfg` | Runs the brainstorm → plan → work → review → compound pipeline autonomously | The full feature workflow, executed without per-step confirmation |

**Skill renaming.** CE skill names are stable in 3.x; if a skill renames, only this table changes. Behavior descriptions are the durable anchor.

---

## Real-world deployment example

This integration doc was informed by `books-ops`, a private `rmorison` repository that ran the full `ce-brainstorm → ce-plan → ce-doc-review → lfg` pipeline against a real workload. The wording of the layer-realization mapping, the Ticket Policy block, and the AI-review discipline framing reflects iteration through that deployment. `books-ops` is named here as deployment context, not as a documentation reference; everything load-bearing in this doc is inlined directly so a public reader without `rmorison` access can apply it end-to-end.

---

## See also

- [`ai/claude-code/README.md`](../ai/claude-code/README.md) — canonical six-layer architecture description
- [ADR-0001](../docs/engineering/adr/0001-six-layer-ai-architecture.md) — the architectural decision
- [`process/feature-development-workflow.md`](./feature-development-workflow.md) — feature workflow these CE skills operate within
- [`process/issue-tracking.md`](./issue-tracking.md) — team-scale issue ceremony (compared with the solo + AI mode above)
- [`process/git-branching-strategy.md`](./git-branching-strategy.md) — branch-naming and review-gate context
- [Compound-engineering plugin](https://github.com/EveryInc/compound-engineering-plugin) — the canonical Layer 2/3/4/5 realization
