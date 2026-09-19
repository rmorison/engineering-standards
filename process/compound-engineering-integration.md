# Compound Engineering Integration

*Operational reference for adopting compound-engineering as the canonical realization of Layers 2–5 of the [six-layer AI architecture](../ai/claude-code/README.md).*

**Architectural decision:** [ADR-0001](../docs/engineering/adr/0001-six-layer-ai-architecture.md).
**Audience:** projects using compound-engineering (CE) — most concretely the `rmorison` projects, but the integration is intended to be readable and usable by any adopter.
**Status:** active.
**Verified against:** CE v3.27.0 (2026-09-19).

---

## Scope

This document describes how compound-engineering ([CE](https://github.com/EveryInc/compound-engineering-plugin), v3.x) realizes the six-layer AI architecture in the engineering-standards repository, and resolves the operational details that surface when CE coexists with these standards: artifact path conventions, issue-tracking ceremony scaling, branch-naming reconciliation, AI-review discipline, and ticket-tracking modes.

For the architecture itself, see [`ai/claude-code/README.md`](../ai/claude-code/README.md). This doc is the operational complement.

**Precedence rule with provenance clause.** When a CE skill produces an artifact, CE paths and conventions win. Standards paths and conventions own human-authored artifacts and ADRs. Ownership is decided in two steps:

- **The path decides, by default.** The [artifact location mapping](#2-artifact-location-mapping) in § 2 maps every path this integration names to its owner: `docs/plans/` is CE's, `docs/engineering/designs/` is the standards'. A file's location answers the question without recovering who wrote it first — which nothing in the repository records, since CE writes and hand edits appear in git as the same author.
- **Explicit reclassification** via a one-line `provenance:` frontmatter note (`provenance: hand-authored` or `provenance: ce-plan`) overrides the path. Use it only when a file genuinely crosses a boundary — a hand-authored document living in a CE path, or a CE artifact since adopted as hand-maintained. Ordinary files carry no annotation, so the note's presence is itself the signal that something non-obvious happened.

---

## 1. How CE realizes the six layers

| # | Layer | Principle | What CE provides |
|---|-------|-----------|------------------|
| 1 | Rules | Persistence | *Not provided.* The standards repo's [`ai/claude-code/rules/*.md`](../ai/claude-code/rules/) retains ownership. Rule files carry one-line CE-aware pointers, not multi-mode policy. |
| 2 | Workflow Skills | Composability | 36 skills covering discovery, planning, execution, review, debugging, and compounding. Pipeline shape: `ce-brainstorm → ce-plan → ce-work → ce-doc-review → ce-code-review → ce-compound`. The `lfg` skill routes a request to the skills whose job it is and carries a code change through to an open PR. |
| 3 | Persona Agents | Perspective | 27 specialized review personas, held as reference files inside `ce-code-review` (16), `ce-doc-review` (8), and `ce-simplify-code` (3). Each review skill activates a subset per document or diff rather than dispatching all of them: in `ce-doc-review` only coherence and feasibility run every time, the rest on matching signals. The roster lives in CE's internals and carries no stability contract — the durable interface is the skill invocation, not the persona names. |
| 4 | References | Progressivity | Each skill ships a `references/*.md` subtree loaded progressively as workflow depth grows. The pattern keeps Layer 2 skills lean at the entry point. |
| 5 | Compound / Learnings | Compounding | `ce-compound` captures learnings from completed work into `docs/solutions/`. `ce-compound-refresh` audits and consolidates. The compound output is itself a Layer 5 artifact. |
| 6 | Hooks | Determinism | *Not provided.* The standards repo's [`templates/.claude/hooks/`](../templates/.claude/hooks/) retains ownership. CE-mode invariants (e.g., warn if `/plan` is invoked instead of `/ce-plan`) can be added as hooks in follow-up work. |

For the canonical layer descriptions (vendor-neutral), see [`ai/claude-code/README.md`](../ai/claude-code/README.md). This table is the operational mapping.

---

## 2. Artifact location mapping

CE-using projects produce artifacts at paths the standards' `docs/` taxonomy does not name. The precedence rule (above) governs ownership; this table documents which paths are produced by which CE skill.

**The `docs/` prefixes below are CE's default artifact root.** CE resolves that root from `docs_root` in `<repo-root>/.compound-engineering/config.yaml`; an adopter who sets it should read every `docs/` path in this document as `<docs_root>/`. An invalid value stops CE from writing artifacts rather than silently falling back to `docs/`. This repository declares no config file, so the default applies here.

| Path | Owner | Producer / notes |
|------|-------|------------------|
| `docs/ideation/` | CE | `ce-ideate` output |
| `docs/plans/` | CE | Every unified plan artifact, whichever skill wrote it. `ce-plan` output — implementation-ready, carrying Implementation Units and acceptance criteria. Subsumes the standards' `docs/planning/` for CE-using projects. |
| `docs/plans/YYYY-MM-DD-HHMM-<type>-<topic>-plan.md` | CE | `ce-brainstorm` output as of CE 3.x, in the same directory — a requirements-only unified plan (`artifact_contract: ce-unified-plan/v1`, `product_contract_source: ce-brainstorm`) carrying a Product Contract but no Implementation Units. **Serves as the Phase 0 / discovery artifact** for [`process/feature-development-workflow.md`](./feature-development-workflow.md); Phase 1 (Product Concept) is seeded from it. |
| `docs/brainstorms/` | CE (legacy) | Historical `*-requirements.{md,html}` files. `ce-plan` still accepts them as input; `ce-brainstorm` no longer writes here. |
| `docs/solutions/` | CE | Layer 5 artifacts produced by `ce-compound` and `ce-compound-refresh`. No standards analog yet. |
| `docs/engineering/adr/` | shared | Human-authored ADRs. Path identical in standards-mode and CE-mode. |
| `docs/engineering/designs/` | standards | Human-authored technical design documents. |
| `docs/product/` | standards | Human-authored product concepts and feature specs. |

**When in doubt:** the path in this table is the answer. A `provenance:` frontmatter note overrides it for the rare file that belongs to the other side of the boundary; absent that note, the path governs regardless of who last edited the file.

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

Reactive issue creation only. The implementation-ready plan file — the one carrying `## Implementation Units`, not a requirements-only brainstorm artifact sharing the same directory — is the granular unit tracker via U-IDs; pre-allocating per-U sub-issues duplicates state and drifts from the plan. Apply when:

- Sole contributor working with CE
- Plan U-IDs adequately track granular progress
- Issues created reactively for: `lfg` residuals, post-ship bugs, plan Open Question activations, scope expansions

The standards' [`process/issue-tracking.md`](./issue-tracking.md) already carries solo carve-outs under **Epic Size Guidelines** ("Fewer than 3 issues: probably doesn't need an epic, just use labels"; "<1 month: might not need epic structure"). Solo + AI mode is the natural extension of those carve-outs.

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

**Prerequisite.** CE derives branch names from the work description and has no path that reads an issue number — `ce-worktree` picks a name like `feat/login`, and `ce-work` creates one from the plan whenever the session starts on the default branch. So the issue-numbered half of the rule applies only if you create and check out `{issue-number}-{slugified-title}` *before* invoking `ce-work` or `lfg`. Otherwise you get topic-style naming regardless of whether an issue exists.

[`process/git-branching-strategy.md`](./git-branching-strategy.md) carries this carve-out in its anti-pattern section.

---

## 5. Solo-scale adaptations and AI-review discipline

### Solo-scale adaptations

What shifts at solo + AI scale, with citations to existing standards:

- **Estimation.** [`process/project-planning-standards.md`](./project-planning-standards.md) already permits solo estimation under **Team Estimation**. For CE-using solo work, point estimates in CE plan files (`docs/plans/...`) serve as the self-calibration mechanism; planning poker is N/A.
- **Code review.** Standards assume a human reviewer. Solo + AI work substitutes the AI-review discipline below.
- **Milestones.** Earn their keep at >3-month horizons. Solo + AI work over shorter horizons typically uses plans (Layer 2 outputs) and reactive issues.
- **Epic structure.** Earns its keep at 5+ implementation issues per feature. This *replaces* the standards' epic minimum rather than extending it: [`process/issue-tracking.md`](./issue-tracking.md) sets the minimum at 3–5 sub-issues and exempts only fewer than 3. For the 3–4 band in between, solo + AI mode uses labels plus plan U-IDs — the standards' own answer for small groupings — rather than an epic.

### AI-review discipline (not enforced merge gate)

For solo + AI work, the human-reviewer slot in branch protection is replaced by an **AI-review discipline**. This is **process discipline, not a merge gate enforced by repo configuration**. There is no CI check, branch-protection automation, or PR template that enforces "no unresolved P0/P1 findings" — claiming otherwise would be aspirational documentation.

**The discipline names:**

1. **`ce-code-review`** on the diff before merge. Dispatches Layer 3 persona reviewers (security, reliability, performance, language-specific style, etc.) per the conditional triggers in the skill. Surfaces P0/P1 findings.
2. **`ce-doc-review`** on the plan or spec when applicable. Dispatches Layer 3 persona reviewers (coherence, feasibility, scope-guardian, adversarial, product-lens, etc.). Surfaces P0/P1 findings.
3. **Self-review against plan acceptance criteria.** The implementer verifies the unit's `Verification` field is satisfied before merge.
4. **A disposition record in the PR body.** State that `ce-code-review` ran (and `ce-doc-review` where applicable), then one line per P0/P1 finding saying what happened to it: fixed, deferred to an issue, or not accepted and why. A review that surfaced nothing says so in one line. This is the record the branch-protection approval would otherwise have left — it is documentation, not a gate, and nothing blocks the merge on it.

**Failure modes the discipline does not catch:**

- **Cross-PR scope drift.** AI reviewers see one diff at a time; missing requirements that span PRs are not flagged.
- **Self-grading loops.** In solo mode the implementer decides what "unresolved" means. A P1 finding the implementer disagrees with becomes "addressed" by judgment.
- **Product-positioning regressions.** AI reviewers tuned for code patterns miss strategic intent.
- **Same-intent author/reviewer.** No second pair of eyes with independent stakes.

**Where the discipline is not sufficient on its own.** Scale is not the only axis that matters; risk is the other. [`process/technical-work-workflow.md`](./technical-work-workflow.md) reserves its critical (P0) tier for security breaches, data loss, and authentication bypass. For changes in those classes — security fixes, data-loss-capable migrations, and auth or permission changes — the discipline above is a floor, not a substitute, and three additions apply:

- **A second review pass in a separate session**, so the reviewing context is not the one that wrote the change. The self-grading failure mode above is strongest exactly where the stakes are highest.
- **No same-session merge.** Let the change sit until a later session before merging, so the disposition decisions get read by someone who is no longer mid-implementation.
- **An explicit note in the PR body** recording that the change is in a critical class and was merged without human approval, so the choice is visible in history rather than implied by its absence.

Where a human reviewer is available, these classes take human approval and the additions above do not substitute for it. Adopters who follow the discipline understand they are trading the remaining failure modes for the speed of solo work. When a human reviewer onboards, the standards' "Require at least 1 approval" rule re-engages and AI review becomes complementary.

[`process/git-branching-strategy.md`](./git-branching-strategy.md) carries a one-line note in its branch protection block pointing at this discipline.

---

## 6. CE skill ↔ standards doc cross-reference

The table below maps the CE pipeline and git-adjacent skills (Layer 2) that the standards docs govern — not all 36 CE ships. Behavior is described alongside each skill name so the mapping survives a rename.

| CE skill | Behavior | Standards doc(s) it operates within |
|----------|----------|------------------------------------|
| `ce-ideate` | Open-ended ideation; produces `docs/ideation/` artifacts | Pre-Phase 1 of [`process/feature-development-workflow.md`](./feature-development-workflow.md) |
| `ce-brainstorm` | Structured requirements gathering; produces a requirements-only unified plan at `docs/plans/YYYY-MM-DD-HHMM-<type>-<topic>-plan.md`. Legacy `docs/brainstorms/*-requirements.md` files remain valid input to `ce-plan` but are no longer written | **Phase 0** of [`process/feature-development-workflow.md`](./feature-development-workflow.md); Phase 1 is seeded from the brainstorm output |
| `ce-plan` | Produces implementation plans at `docs/plans/...` with U-IDs and acceptance criteria | Phases 3–4 of [`process/feature-development-workflow.md`](./feature-development-workflow.md); subsumes `docs/planning/` for CE-using projects |
| `ce-work` | Executes a plan; manages task state and incremental commits | Phase 5 of [`process/feature-development-workflow.md`](./feature-development-workflow.md) |
| `ce-doc-review` | Dispatches Layer 3 persona reviewers against a plan or requirements doc; produces P0–P3 findings | Phase 4 review surface (plans, designs, ADRs) |
| `ce-code-review` | Dispatches Layer 3 persona reviewers against a code diff; produces P0–P3 findings | Phase 5 review surface (code review, the AI-review discipline above) |
| `ce-debug` | Systematic root-cause investigation; produces a debug record | Bug-fix work in [`process/technical-work-workflow.md`](./technical-work-workflow.md) |
| `ce-compound` | Captures learnings from completed work into `docs/solutions/` (Layer 5 output) | Phase 6 (validation/iteration) of [`process/feature-development-workflow.md`](./feature-development-workflow.md), or post-incident |
| `ce-compound-refresh` | Audits and consolidates `docs/solutions/`; supersedes outdated learnings | Maintenance of Layer 5 artifacts |
| `ce-commit` / `ce-commit-push-pr` | Creates commits and opens PRs | Commit-message and PR conventions in [`process/git-branching-strategy.md`](./git-branching-strategy.md) |
| `ce-worktree` | Creates isolated worktrees and branches | Branch naming per § 4 above — supply the name when an issue exists |
| `ce-resolve-pr-feedback` / `ce-babysit-pr` | Resolves review feedback and drives a PR to merge-ready | PR review and merge gates in [`process/git-branching-strategy.md`](./git-branching-strategy.md) |
| `lfg` | Routes a request to the CE skill whose job it is rather than running a fixed chain. On a code change: plans, implements, simplifies, runs `ce-code-review` and applies eligible findings, then pushes a branch, opens a PR and watches CI — leaving only the merge. `ce-brainstorm` runs only when a human is present; `ce-compound` only when the run produced durable reasoning | The full feature workflow, executed without per-step confirmation, through to an open PR |

**Version drift.** Renaming is not the drift vector to plan for. Between CE 3.1.0 (which this doc was first written against) and 3.27.0, no skill was renamed — but the skill count grew, the persona roster moved and grew, `ce-brainstorm`'s output path changed, and `lfg` gained a shipping tail. Behavior and output paths are what move, and they move § 1, § 2 and § 6 together rather than one row at a time. Re-verify all three tables against the installed CE on each minor upgrade, and update the **Verified against** line in the header when you do.

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
