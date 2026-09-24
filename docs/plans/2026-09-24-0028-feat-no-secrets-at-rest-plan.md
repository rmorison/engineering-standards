---
title: No Application Secrets at Rest in the Developer Environment - Plan
type: feat
date: 2026-09-24
deepened: 2026-09-24
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
---

# No Application Secrets at Rest in the Developer Environment - Plan

## Goal Capsule

- **Objective:** An adopter following this repository's Python standards keeps application secret values out of the working tree an AI agent operates in, and can tell exactly what each option protects against and what it does not.
- **Means:** a tiered secrets rule owned by `code/python-standards.md` Configuration Management (KTD1), with a committed reference file enforced by a decidable check (KTD4, KTD5).
- **Authority:** issue #30's acceptance criteria, then the Key Decisions below, then this plan, then implementer judgment. Where #30's wording and this plan differ, the plan records why (KTD11).
- **Stop conditions:** stop and report rather than improvise if any CLI syntax the standard would state cannot be verified against a primary source, if the check cannot be made to fail on a planted literal, or if a change would contradict #29 or #31.
- **Execution profile:** Markdown standards edits plus one dependency-free Node script and a CI job. No product code, no network calls at run time.
- **Finishing:** `ce-work` implements; the calling `lfg` run reviews, commits, opens a PR and watches CI. Merging stays with the user.

---

## Product Contract

### Summary

Replace the single "gitignored `.env`" secrets pattern with a three-tier rule for application secrets, whose recommended tier resolves them from a secret manager at process start, so no secret value sits in the working tree and the runner writes none to disk. A committed reference file holds secret-manager references instead of values, and a check fails on any line of it that is not a reference. Every statement the standard makes about a CLI carries its source and version or says it is unverified, and the standard says plainly that this makes retrieval explicit rather than preventing it.

### Problem Frame

`code/python-standards.md` prescribes one pattern: secret values in an in-tree `.env`, kept out of git by `.gitignore`. That manages accidental commit. It does nothing about a process with filesystem access reading the file, and in an agent-operated repository that is the ordinary case: an agent that runs `cat .env`, greps for configuration or summarises a directory reads the secrets, and they can then land in a transcript, a log or an issue body. This repository ships a Claude Code starter kit whose `templates/.claude/settings.json` pre-approves `Bash(uv:*)` and `Bash(make:*)`, so its own adopters are squarely exposed.

Issue #30's first proposal, an out-of-tree file at mode `0600`, does not survive its own threat model: an agent runs as the developer and reads a file the developer owns as easily as an in-tree one. Research for this plan found a second gap. Stated as one headline, "never at rest" contradicts the fallback tiers and the local Docker stack, both of which put values on disk. So the invariant has to be stated per tier.

### Key Decisions

- **Fold the "no local secrets" philosophy into #30 rather than a separate issue or document.** (session-settled: user-approved — chosen over a separate issue or doc for the philosophy: two artifacts would argue one principle to different conclusions.) Governs R1.
- **State the requirement tool-neutrally, with 1Password `op` as the named default and doppler, sops and HashiCorp Vault sanctioned.** (session-settled: user-approved — chosen over `op`-specific guidance: the repo is vendor-neutral elsewhere, and #29 settles the same requirement-plus-named-default shape for secret scanning.) Governs R4, R17.
- **An out-of-tree `0600` file is the fallback tier, not the recommendation.** (session-settled: user-approved — chosen over recommending it, as #30 first did: an agent with a shell reads a `0600` file the developer owns as easily as an in-tree `.env`.) Governs R3, R27.
- **No new top-level document and no splitting of existing files.** (session-settled: user-directed — chosen over a new secrets document or a folder of topic files: this repo's recurring failure mode is drift across surfaces, not file length.) Governs R1.

### Requirements

**The rule**

- R1. `code/python-standards.md` Configuration Management owns the secrets rule, and every other document that mentions secrets links to it rather than restating it.
- R2. A secret is a credential granting access to something that exists outside the developer's machine; a throwaway credential for a local-only service, such as a Docker Postgres on localhost, is configuration.
- R3. The rule names three tiers and what each protects against: tier 1, a secret manager resolves references at process start and the runner writes no secret to disk; tier 2, a file outside the working tree at mode `0600`; tier 3, an in-tree gitignored `.env`, which protects against accidental commit only.
- R4. The requirement is stated tool-neutrally, with `op` as the named default and doppler, sops and HashiCorp Vault sanctioned.
- R5. A runner resolves every reference, fails closed if any reference does not resolve, and injects values into the environment of the one command it launches; nothing sources a reference file into a shell.
- R6. Every CLI syntax the standard states is verified against a primary source and cited with its package and version, and anything unverified is labelled as such with the date.
- R7. The standard states the limit: an agent running commands as the developer can call the manager's CLI and read the environment it resolves into, including through commands the starter kit pre-approves, so tier 1 turns retrieval into an explicit call rather than a file read and does not prevent it.
- R8. The standard states that `.gitignore` is a git convention, not an access-control boundary.
- R23. The rule covers application secrets supplied as environment variables; developer-tool credential stores such as cloud CLI profiles, `gh`, package-registry tokens and SSH keys stay at rest and are named as out of scope.
- R26. Tier 1's claim is bounded: whatever the launched process prints, logs or hands to a container can still reach disk, and a resolved value is readable by the same user for the life of the process.
- R27. A tier 2 file is not named `.env`, sits in no ancestor directory of any working tree, and is not under version control, a dotfiles repository or a synced folder, because `load_dotenv()` without a path searches upward for `.env`.
- R28. Tier 3 applies only where no agent has access to the working tree, where an agent includes IDE assistants and any tool that reads workspace contents for a model; if unsure, the condition is not met. Tier 3 is a choice made per repository, by committing no `secret-refs.env`; tiers 1 and 2 are per-developer choices inside a repository that commits one.
- R29. The command a runner launches is the application or an integration-test target, never an agent, an editor, a terminal multiplexer, a general-purpose `make` target, or a shell-integration tool such as direnv.
- R30. Under tier 1 an agent can reach every item the developer's manager identity can read, which can exceed what a tier 3 `.env` exposed, so a manager CLI is never added to an agent's allow list, and no Makefile target or script an agent's allow list reaches invokes the runner or the manager CLI. The starter kit pre-approves `Bash(make:*)`, so such a target amounts to allow-listing the manager.

**The reference file**

- R9. A committed `secret-refs.env` holds secret keys only, each value a single secret reference; non-secret configuration stays in `example.env`, and the two files share no key.
- R10. A reference file contains only full-line comments, blank lines, and `KEY=reference` lines with no quotes, `export` prefix, `$`, inline comment, whitespace in the value, or repeated key.
- R11. A secret embedded in a larger value, such as a password inside `DATABASE_URL`, is stored whole as one manager field and referenced as one value.
- R24. A reference file holds no key with a browser-exposed prefix (`NEXT_PUBLIC_`, `VITE_`, `REACT_APP_`, `PUBLIC_`), since a build tool inlines such values into client bundles.
- R25. A reference file is a security-sensitive path that needs required review, because repointing a key can send one service's secret to another.

**The developer flow**

- R12. Configuration resolves secrets when they are used rather than at import, so `make setup` and unit tests run without a secret-manager session, and a value that is still an unresolved reference is rejected.
- R31. Where a `secret-refs.env` exists, the configuration example refuses to start when `.env` defines a key that `secret-refs.env` holds, and its errors name keys, never values.
- R13. CI never reads `secret-refs.env`: secrets CI needs come from the CI platform's secret store under the same names, throwaway service credentials stay literal configuration, and a test needing a third-party secret skips when it is absent only on runs where the platform withholds secrets, such as a fork's pull request; on any other run an absent secret fails the test.
- R32. A CI secret is exposed to the one step that needs it, never to a job that runs an agent or runs PR-authored code under `pull_request_target`, and a test skipped on a fork's pull request is expected rather than a reason to change the trigger. A secret available to a same-repository `pull_request` run can be read by anyone who can push a branch, agents included, so CI secrets are limited to development and test credentials, as in R15.
- R14. A developer moving to tier 1 from tier 2 or 3 rotates every secret that sat in a file an agent could read.
- R15. References point at a shared team vault holding development and test credentials only, and onboarding includes access to it. What an agent can reach is set by the identity signed in to the manager, not by where references point, so the standard says the developer's personal vault and any vault that identity can read are within reach, and that staging and production access is held by an identity other than the one signed in during daily development.
- R16. The existing `.env` guidance is retained and rescoped, not deleted: under tiers 1 and 2 `.env` is a configuration file, and only under tier 3 does it hold secrets.

**The check**

- R17. `scripts/check-secret-refs.mjs` fails on any reference-file line that is not a comment, a blank line, or `KEY=reference` with a reference from its grammar allowlist; on empty or missing input; and on any key a reference file shares with the configuration files it must be given.
- R18. The check proves its line classifier against built-in fixtures, including every must-fail case, before it reports on any file.
- R19. The check holds the standard's own example: the `secret-refs.env` and `example.env` example blocks in `code/python-standards.md` must pass and share no key, and the check fails if either block is missing or appears more than once.
- R20. CI runs the check in its own dependency-free job, triggered by changes to the script as well as to Markdown.
- R21. `process/documentation-standards.md` Automated Checks lists the check, how to run it locally, and that a pass means only that the named files are well-formed.

**Consistency**

- R22. `code/web-application-standards.md` Environment Variables links to the owner for the secrets rule and keeps only the variables specific to the web stack.

### Scope Boundaries

- Production secret handling (ECS task definitions, the Kubernetes Secrets Store CSI driver, External Secrets Operator) is unchanged. The rule governs the developer environment.
- The check decides the shape of the files it is named, and nothing more. It does not decide that a reference resolves, that no secret sits in another file, that a key in the reference file really is a secret, or that a reference-shaped value is not a literal: a secret pasted in as a segment, `op://dev/stripe/<pasted key>`, passes. `detect-secrets` stays the guard against literals elsewhere.
- Developer-tool credential stores (cloud CLI profiles, `gh`, package-registry tokens, SSH keys) are out of scope and stay at rest (R23).
- No change to `templates/.claude/settings.json`. Its own README (`templates/README.md`) says a textual deny rule "isn't a security boundary around the program", and `check-template-kit.mjs` cannot evaluate a non-`Bash` deny rule, so a `Read(.env)` rule would be unverified and would not satisfy tier 3's condition.

#### Deferred to Follow-Up Work

- A shipped loader that resolves references into a child process. See KTD3 for why it is not in this change.
- Distributing the check to adopters as a pinned pre-commit hook (`.pre-commit-hooks.yaml`), and discovering reference files automatically instead of taking them as arguments.
- Rejecting personal vault names (`Private`, `Personal`, `Employee`) in references, which pass the check but resolve only for their author.
- A `PreToolUse` hook in the starter kit that intercepts calls to a secret-manager CLI.
- The starter kit's `Bash(uv:*)` pre-approves arbitrary commands through `uv run`. Verified with `check-template-kit.mjs`'s own matcher after it passed its 30 documented fixtures: `uv run op read <reference>`, `uv run cat <any file>` and `uv run env` are all pre-approved, while a bare `op read` needs a prompt. It is the same shape as the `git remote -v:*` hole #44 fixed. It needs its own issue, and the claim R7 makes about it should then be held by `check-template-kit.mjs` rather than asserted.
- Short-lived or SSO-backed credentials for developer tooling, which would extend R23's out-of-scope stores into the rule.
- Failing when a tracked `*.env` file is named neither as a reference file nor as a configuration file.
- Binding the local Docker stack's published ports to `127.0.0.1` in `code/web-application-standards.md` and `code/database-standards.md`, which strengthens R2's "local-only" premise.
- `templates/CLAUDE.md` names the template `.env.example` while every file in `code/` uses `example.env`.
- Pre-existing production inconsistencies in `code/python-standards.md`: the CSI example mounts secrets as files at `/mnt/secrets` against the "not file paths" rule, and the Docker example passes production secrets on a `docker run -e` command line.
- Secret-scanning tool neutrality (#29) and the publication leak gate (#31). The check's grammar table is data (KTD6) so #31 can reuse the scanner with its own rule set.

### Sources

- Issue #30, rewritten 2026-09-23, and its acceptance criteria. Related: #29, #31, #35.
- `@1password/sdk@0.5.0`, published by `npm@1password.com`: secret reference syntax `op://<vault-name>/<item-name>[/<section-name>]/<field-name>`.
- `@1password/op-js@0.1.13`, same publisher: invokes `op read <reference>` and `op inject` with `--out-file`, `--file-mode` and `--force`. It does not wrap `op run`, and neither package attests query parameters in references.
- `python-dotenv` 1.2.3, `dotenv/main.py`: `load_dotenv(..., override: bool = False, interpolate: bool = True, ...)`, and an already-set environment variable is skipped unless `override` is true.
- `scripts/check-template-kit.mjs`: `RULE_SYNTAX_FIXTURES` self-tests a reimplemented matcher before it vouches for anything; check 7 fails on an empty walk. PR #44 (merged) recorded behaviour "with its version rather than asserted as a law".
- `docs/solutions/best-practices/prove-a-check-fails-before-trusting-it-passes.md` and `docs/solutions/best-practices/a-corrected-claim-is-not-a-verified-claim.md`.

---

## Planning Contract

### Key Technical Decisions

- KTD1. **The rule lives in a new `### Secrets` subsection placed first in `## Configuration Management`, and `### Environment Variables Strategy` is rescoped to configuration.** The `## Configuration Management` heading text stays unchanged, since `code/database-standards.md` links to `#configuration-management` and that is the only inbound anchor into the file. (session-settled: user-directed — chosen over a new secrets document or split files: this repo's recurring failure mode is drift across surfaces, not length.) Governs R1.
- KTD2. **The invariant is stated per tier, not as one headline.** "Never stored at rest" is true of tier 1 outside container tooling and false of tiers 2 and 3, so a single headline would contradict the section's own fallbacks. Stating it per tier also lets R7's limit say precisely what tier 1 buys.
- KTD3. **No loader ships; the standard specifies the runner's contract instead.** Every verified route for putting values into an environment either writes a file, as `op inject --out-file` does, or depends on unverified output details: whether `op read` appends a trailing newline, which matters for PEM keys, and whether `op inject` substitutes a bare reference or only a braced one. Secrets-handling code built on those guesses is worse than none. The standard names `op run` as 1Password's usual runner and says its flags were not verifiable when written, on 2026-09-24. Rejected: a loader built on `op read`.
- KTD4. **The reference file holds secrets only and shares no key with `example.env`, and the application enforces the same disjointness against `.env` at start.** A secrets-only file is what makes "every value is a reference" decidable; a mixed file would need a classifier to say which keys are secrets, which is a heuristic. The check can only compare committed files, and `.env` is gitignored, so it never reaches the check: a real value typed into `.env` under a secret's name would otherwise be used silently whenever the runner is not. Hence R31's start-up refusal, which reads the keys with `dotenv_values` (python-dotenv 1.2.3). Rejected: one mixed file with a key classifier.
- KTD5. **The check accepts a strict subset of dotenv and fails closed.** It classifies every non-blank line and fails any line it does not recognise, so it cannot pass a file because of a line it skipped. Quotes, `export`, `$`, inline comments and whitespace in values are rejected because dotenv parsers disagree about them. A parser that accepted any of them could let a literal through that a runner would read differently, for example a multi-line quoted value. Line endings and a byte-order mark are normalised, because failing on them would be failing for the wrong reason. Rejected: reusing a dotenv parser.
- KTD6. **The grammar allowlist is data, shipped with `op://` only, and each entry records its source and version.** `op://` is transcribed from `@1password/sdk@0.5.0` as exactly three or four non-empty segments, and a segment admits only `A-Z`, `a-z`, `0-9`, `.`, `_` and `-`. Listing what a segment may contain, rather than what it may not, keeps out shell metacharacters (`;`, backticks, `|`, `&`, quotes, `\`, `(`), control characters and non-ASCII, any of which would turn a committed file into something dangerous to source. A vault or item name outside that set is renamed. The manager's item IDs are an alternative, but their syntax was not verified, so the standard does not state it. Doppler, sops and Vault entries are not shipped because their formats were not verified, and sops encrypts values rather than referencing them. Adopters add an entry with its own source. This keeps the requirement tool-neutral while the shipped default stays verified. (session-settled: user-approved — chosen over `op`-specific guidance: the requirement is tool-neutral; only the shipped default is `op`.) Rejected: accepting any `scheme://` value, which admits `https://user:pass@host`. Governs R4, R17.
- KTD7. **The check proves itself in-script and holds the standard's example blocks.** Fixtures live in the script, as `RULE_SYNTAX_FIXTURES` does, and run before any verdict. The example blocks are found by their first-line marker comment (`# secret-refs.env`, `# example.env`) rather than by a general fence parser, which would copy `readMarkdown()` into a third place. Rejected: a fixture directory. That would be one more path to wire into CI, and `.gitignore` already ignores `env/` and `ENV/`.
- KTD8. **The check runs in its own CI job with no install step,** mirroring `check-template-kit`, so a failure is attributable and the `check-docs` job keeps its name for branch protection. The job runs a PR-authored script, so it carries the same warning comment as `check-template-kit`: never `pull_request_target`, never secrets, never a write token.
- KTD9. **A secret grants access to something outside the developer's machine.** That leaves the existing local Docker examples (`localpass`, `local-dev-secret-change-in-production`) valid as configuration, and it classifies test-mode third-party keys, such as a Stripe test key, as secrets despite their names. Rejected: treating every credential-shaped value as a secret, which would force rewriting local examples whose values grant access to nothing.
- KTD10. **The configuration example resolves secrets at the call site, and unit tests set fakes.** Resolving at import would make every test importing configuration need a manager session, including those run by `make setup`, by CI and by agents. `get_secret` also rejects a value that still looks like a reference, which is what reaches the app if someone loads `secret-refs.env` as plain dotenv. An explicit `validate_config()`, called from the application entrypoint and never at import, keeps the file's "validate on startup" practice: it checks that every key `secret-refs.env` names is set and is not an unresolved reference, and performs R31's refusal. Unit tests never call the entrypoint. Rejected: keeping placeholder secret keys in `example.env`, which invites real values into `.env` and breaks KTD4.
- KTD11. **`code/web-application-standards.md` keeps its own variable list and links to the owner for the rule.** #30's acceptance criterion asks it to link "rather than restating an `example.env` inline", but that block also holds web-stack variables the Python standard does not cover, such as `NEXT_PUBLIC_API_URL` and `NEXTAUTH_URL`. Its secret-shaped values are local-only configuration under KTD9. So the plan keeps the variables and removes only the restated rule. Rejected: deleting the block, which loses facts nothing else states.
- KTD12. **The check rejects browser-exposed key prefixes in a reference file** (R24). A secret under `NEXT_PUBLIC_` resolved at build time ends up in a client bundle. The web standard already forbids that in prose; a prefix list is decidable, so the check enforces it. Rejected: leaving it to the web standard's prose.
- KTD13. **The standard shows `op read` only with a warning, and states no other `op` form.** `op read` prints the value, so run by an agent it enters the session transcript. A resolve-without-printing form, and `op run`'s output masking, would both be convenient to cite, but neither was verified, so the standard neither names them nor relies on masking.

### High-Level Technical Design

Where a secret value lives, by tier:

```mermaid
flowchart TB
  V[(Team vault in the secret manager)]
  R[secret-refs.env, committed, references only]
  E[example.env, committed, configuration only]
  D[.env, gitignored, copy of example.env]
  S[File outside the working tree, mode 0600]
  P[One launched process environment]
  R -->|tier 1: runner resolves each reference at start| V
  V -->|values, for this process only| P
  S -->|tier 2: loaded at start| P
  E -->|copied by make setup| D
  D -->|load_dotenv, override=False| P
```

Under tier 3 the secret values sit in `.env` itself. The standard confines that tier to repositories with no agent access to the tree.

The reference-file grammar the check enforces, as directional guidance rather than the implementation:

```text
file       := line*
line       := blank | comment | entry
blank      := whitespace only
comment    := "#" at column 1, then anything
entry      := KEY "=" reference              (no surrounding whitespace)
KEY        := [A-Z_][A-Z0-9_]*               (unique within the file,
                                              no browser-exposed prefix)
reference  := one grammar from the allowlist, matching the whole value
op         := "op://" seg "/" seg ["/" seg] "/" seg
seg        := one or more of  A-Z a-z 0-9 . _ -
```

Line endings and a leading byte-order mark are normalised before classification. Everything else that is not `blank`, `comment` or `entry` classifies as `malformed` and fails.

| Line | Class | Verdict |
|---|---|---|
| `STRIPE_API_KEY=op://dev/stripe/credential` | entry, reference | pass |
| `# rotated 2026-09` or an empty line | comment or blank | ignored |
| `STRIPE_API_KEY=not-a-reference` | entry, literal | fail |
| `STRIPE_API_KEY="op://dev/stripe/credential"` | entry, literal | fail: quotes |
| `export STRIPE_API_KEY=op://dev/stripe/credential` | malformed | fail |
| `STRIPE_API_KEY=op://dev/stripe/a;id` | entry, malformed reference | fail: `;` is outside the segment set |
| `NEXT_PUBLIC_STRIPE_KEY=op://dev/stripe/credential` | entry, browser-exposed key | fail |
| `STRIPE_API_KEY: op://dev/stripe/credential` | malformed | fail |

### Assumptions

- The reference file is named `secret-refs.env`. No common auto-loader reads it: python-dotenv, pydantic `env_file` and Docker Compose all default to `.env`.
- Tier 3 is retained, as #30 requires, and scoped to repositories where no agent has access to the working tree. That excludes adopters of this repository's AI starter kit, and the standard says so.
- A `DATABASE_URL` pointing at a shared or cloud database is stored whole as one manager field (R11). Split credentials assembled in code are the alternative, and the standard does not prescribe them.
- The check is a Node script like its two siblings. Adopters copy it until distribution is settled, which is deferred.
- Keys in a reference file follow the uppercase naming convention already in the standard. The check enforces it.

### Sequencing

U1 writes the rule the other units depend on. U2 and U3 bring the rest of `code/python-standards.md` into line with it. U4 builds the check against the example blocks U2 writes. U5 wires the check into CI and the documentation. U6 is independent of U4 and U5.

### System-Wide Impact

- **Adopters' developer environments.** Under tier 1, an agent's reach moves from reading one file in the tree to whatever the developer's manager identity can read (R30). What bounds it is the signed-in identity, which R15 keeps away from staging and production.
- **The agent access boundary.** Unchanged by this plan, and described by it. Three things now bear on it: what a runner may launch (R29), what an agent's allow list contains (R30, and the deferred `uv:*` finding), and where transcripts land (R26).
- **Adopters' CI.** Where CI secrets are scoped, and which trigger runs PR-authored code (R32).
- **This repository's CI.** A new job runs a PR-authored script under `pull_request` with `contents: read` (KTD8).
- **The documents.** `code/python-standards.md` owns the rule; `code/web-application-standards.md` links to it (U6); `process/documentation-standards.md` lists the check (U5). `ai/CLAUDE.md` describes a committed `agent-transcripts/` convention; R26 names transcripts as a place secrets reach disk, but this plan does not change that convention.

### Risks & Dependencies

| Risk | Mitigation |
|---|---|
| A shell metacharacter in a committed reference file runs when someone sources it | Segment character allowlist (KTD6); fixtures for each metacharacter (U4); nothing sources a reference file (R5) |
| Tier 1 reaches more than a tier 3 `.env` did | Reach stated (R30); staging and production held by a separate identity (R15); no manager CLI on an allow list (R30) |
| A runner launches an agent, an editor, a `make` catch-all or direnv, handing every descendant the secrets | Exclusions named (R29) |
| An adopter reads a green check, or the title, as "my environment is clean" | Scope stated (R23); what a pass means stated (R21); known limits in Scope Boundaries |
| A secret reaches disk through printed output, logs, transcripts or containers | Tier 1's claim bounded (R26); `op read` shown only with its warning (KTD13) |
| A real value typed into `.env` is used silently | Start-up refusal on overlapping keys (R31, KTD4) |
| A tier 2 file is auto-loaded, committed or synced | Placement rules (R27); explicit `load_dotenv` path in the example (U2) |
| A repointed reference sends one service's secret to another | Required review for reference files (R25). A green check on a PR that edits the check or the example blocks is not evidence: the reviewer reads the diff |
| CI exposes secrets to agent jobs or PR-authored code | Step-level scoping; no `pull_request_target` (R32) |
| A must-fail fixture trips GitHub push protection | Obviously fake literals in no provider's format (U4) |
| **Dependency:** facts about 1Password's CLI and python-dotenv | Each fact the standard states is verified and cited (R6); `op run`'s flags, item-ID syntax and any resolve-without-printing form stay unstated |

---

## Implementation Units

### U1. Write the owner section

**Goal:** Add the `### Secrets` subsection that owns the rule, and rescope `### Environment Variables Strategy` to configuration.

**Requirements:** R1–R8, R11, R13–R15, R23, R25–R30, R32

**Dependencies:** none

**Files:**
- `code/python-standards.md`

**Approach:**
1. Insert `### Secrets` as the first subsection of `## Configuration Management` (KTD1). Leave the `##` heading text unchanged.
2. Lead with the requirement (R4), its scope to application secrets (R23), and the definition of a secret (R2, KTD9).
3. Present the three tiers per KTD2 (R3), each with what it protects against and what it gives up, with tier 1's bound (R26), tier 2's placement rules (R27) and tier 3's condition (R28). Say that tier 3's condition excludes adopters of the AI starter kit, and that tier 3 is chosen per repository by committing no `secret-refs.env` (R28).
4. State the runner contract (R5) and what it may launch (R29). Name `op run` as 1Password's usual runner with its flags explicitly unverified, and say not to rely on its output masking (KTD3, KTD13).
5. Show the verified surface only, cited per R6: the reference grammar, and `op read <reference>` for resolving one value by hand, with its warning that the value is printed and so enters any agent transcript (KTD13).
6. State the limit (R7) and the reach (R30). Name the starter kit's `Bash(uv:*)`: `uv run op read` is pre-approved where a bare `op read` prompts. Do not claim retrieval is audited: whether the manager logs CLI access depends on the manager and plan, and was not verified. Say that reach is set by the signed-in identity (R15), that a Makefile target invoking the runner is reachable through `Bash(make:*)` (R30), and that the explicit call R7 describes assumes interactive sign-in: a manager token exported in the shell reaches every command an agent spawns and is itself at rest.
7. State R8, R11, R13, R14, R15, R25 and R32 briefly, one or two sentences each. R25 recommends CODEOWNERS or required review for reference files.
8. Recommend `secret-refs.env text eol=lf` in `.gitattributes`.
9. Rescope `### Environment Variables Strategy`: its Pattern bullets become configuration bullets and link to `### Secrets` for secrets.

**Patterns to follow:** check-template-kit's habit of recording behaviour "with its version rather than asserted as a law"; the corrected-claim learning's "quote or drop".

**Test scenarios:**
- Every CLI command or syntax in the new section appears in the Sources list with a package and version, or carries an explicit "not verified" label and date.
- The section contains no sentence asserting that retrieval is logged or audited.
- Reading only `### Secrets`, a reader can state what each tier does not protect against.
- No sentence says or implies that a secret never reaches disk without R26's qualification.
- The section names every R29 exclusion, including direnv, and states R30's reach, including the Makefile-target route and that the signed-in identity sets it.
- The section's claim about `Bash(uv:*)` is re-verified with `check-template-kit.mjs`'s matcher, after that matcher passes its own fixtures, and the result is recorded in the PR. The claim was verified at planning time and would otherwise be asserted.
- The section never names a `.env`-reading tool's behaviour that is not in the Sources list, in particular `load_dotenv`'s upward search.
- `node scripts/check-docs.mjs` passes, and the `#configuration-management` anchor from `code/database-standards.md` still resolves.

**Verification:** The section states the rule once. No other subsection of the file restates a tier. The one inbound anchor still resolves.

### U2. Bring the rest of Configuration Management into line

**Goal:** Make every later subsection of `## Configuration Management` consistent with U1, so no sentence in the section still implies secret values live in `.env`.

**Requirements:** R9, R10, R12, R16, R28, R31

**Dependencies:** U1

**Files:**
- `code/python-standards.md`

**Approach:**
1. Naming Conventions: say the "Secrets" block lists keys that are secrets when they grant outside access (KTD9), with values coming from references rather than literals.
2. Project Structure tree: add `secret-refs.env`, committed.
3. `### example.env Template`: keep only configuration and local-only values. Add a separate `secret-refs.env` example block whose first line is the marker comment `# secret-refs.env` (KTD7), holding the third-party keys as `op://` references. Keep the existing `# example.env` first-line marker. The two blocks share no key (KTD4).
4. Makefile Integration: keep `cp example.env .env`, and replace "update with your values" with text that says `.env` holds configuration only.
5. `.gitignore Entries`: correct the "contains secrets" comment to say what the file holds under each tier (R16).
6. Loading Environment Variables: resolve secrets at the call site (KTD10); make `get_secret` reject a value that is still a reference; say that `load_dotenv` defaults to `override=False`, so a runner-injected value wins; show unit tests setting fakes. Pass `load_dotenv` an explicit path, since without one it searches upward (R27). Add `validate_config()`, called from the entrypoint (KTD10): it checks that every key `secret-refs.env` names is set and not an unresolved reference, and refuses to start when `.env` defines a key that `secret-refs.env` also holds, compared through `dotenv_values`; errors name keys, never values (R31). A missing `secret-refs.env` holds no keys, so a tier 3 repository starts normally (R28). Keep best practice 7.
7. Infrastructure Compatibility, Local Development: replace the `.env`-with-secrets block with the tier 1 pattern.
8. Multi-Environment Strategy: change the Development row and the "Development (local .env file): Actual values in .env" block to references resolved from the team's manager. That also removes the file's contradiction with its own best practice 10.
9. Best Practices: reword items 1 and 5 so neither points secrets at `.env`.

**Test scenarios:**
- The `example.env` and `secret-refs.env` blocks share no key.
- Every value in the `secret-refs.env` block is an `op://` reference with three or four segments.
- No sentence in `## Configuration Management` outside tier 3 says or implies that secret values live in `.env`. Sweep the section for `.env` and classify every hit.
- The configuration example no longer calls `get_secret` at module import.
- The configuration example shows the start-up refusal for a key present in both `.env` and `secret-refs.env`, and its error message names only keys.
- With no `secret-refs.env`, the example starts with secret keys defined in `.env`.
- `validate_config()` is called from the entrypoint, not at import, and best practice 7 still stands.

**Verification:** A sweep of the section for `.env`, `example.env` and "secret" finds only tier-consistent statements.

### U3. Rescope the remaining statements in the Python standard

**Goal:** Remove the contradicting statements outside `## Configuration Management`.

**Requirements:** R1, R13, R16

**Dependencies:** U1

**Files:**
- `code/python-standards.md`

**Approach:**
1. Standard layout tree (the first place a reader meets `.env`): add `secret-refs.env` and correct the `.env` comment.
2. `## Security` Best Practices: replace "Use `.env` files locally" with a link to `### Secrets`.
3. The general Best Practices security line: link to `### Secrets` instead of restating it.
4. Example Project Setup: its `.gitignore` omits `.env`, although `.gitignore Entries` requires it. Add it.
5. `## CI/CD with GitHub Actions`: add a one-line pointer to R13 in the owner section, if the section's shape takes one. Do not restate R13.

**Test scenarios:**
- A sweep of the whole file for `.env`, `example.env`, `secret` and `credential` finds no statement contradicting `### Secrets`. Record the classified list in the PR.
- `node scripts/check-docs.mjs` passes.

**Verification:** The corpus sweep in the Verification Contract comes back clean for this file.

### U4. Build the reference-file check

**Goal:** Ship `scripts/check-secret-refs.mjs`, which decides whether a reference file contains only references, proves its own classifier first, and holds the standard's example blocks.

**Requirements:** R10, R17, R18, R19, R24

**Dependencies:** U1, U2

**Files:**
- `scripts/check-secret-refs.mjs` (new; the self-test fixtures live inside it)

**Approach:**
1. Follow its siblings: an ESM script with a numbered header docblock; `REPO_ROOT` from `import.meta.url`; failures collected through `fail(file, line, check, message)`; `file:line  [check] message` on stderr; exit 1 on failure. Its header states that the check is preventive, since unlike its siblings no shipped defect prompted it.
2. Classify each line per the grammar in High-Level Technical Design (KTD5), after normalising line endings and a byte-order mark.
3. Hold the grammar allowlist as a data table (KTD6). Each entry carries its source and version. Ship `op` only.
4. Run the built-in fixtures before any verdict (KTD7, R18). A single misclassification fails the run.
5. Modes:
   - One mode takes reference-file paths, plus configuration-file paths for the disjointness rule.
   - The other checks the standard's own example blocks in `code/python-standards.md` (R19).
   - Invoking it with neither fails.
6. Empty or missing input fails, including a reference file with no entries. File mode requires at least one configuration file alongside the reference files, so the disjointness rule cannot be skipped by omission.
7. Reject a key with a browser-exposed prefix (R24, KTD12).

**Patterns to follow:** `scripts/check-template-kit.mjs` (`RULE_SYNTAX_FIXTURES`; check 7's empty-walk failure; its header's per-check rationale). Must-fail fixture literals are obviously fake and not in any provider's format, for example `hunter2` or `not-a-reference`, never `sk_live_` or `sk-ant-`, so that GitHub push protection does not reject the push.

**Execution note:** Build the fixtures first and watch every must-fail row fail before trusting a pass. That is habit 1 of the prove-a-check-fails learning.

**Test scenarios:**
- *Happy path:* `STRIPE_API_KEY=op://dev/stripe/credential` classifies as a reference; the four-segment `op://dev/app/api/key` passes; comments and blank lines are ignored; a valid file with CRLF endings passes; a valid file with a leading byte-order mark passes.
- *Literals:* `KEY=hunter2` fails. `KEY=` with an empty value fails.
- *Rejected syntax:* quoted `KEY="op://dev/a/b"` fails; `export KEY=op://dev/a/b` fails; `KEY=${OTHER}` and `KEY=op://${VAULT}/a/b` fail on `$`; `KEY=op://dev/a/b # note` fails on the inline comment.
- *Reference not the whole value:* `DATABASE_URL=postgres://u:op://dev/a/b@h/d` fails; `KEY=hunter2 op://dev/a/b` fails.
- *Shell metacharacters:* each of `;` `` ` `` `|` `&` `'` `"` `\` `(` `)` `<` `>` `#` `*` inside a segment fails; so does a control character and a non-ASCII character. Segments allow only `A-Z a-z 0-9 . _ -` (KTD6).
- *Browser exposure:* `NEXT_PUBLIC_STRIPE_KEY=op://dev/stripe/credential` fails.
- *Malformed references:* whitespace in a segment (`op://My Vault/a/b`) fails; too few segments (`op://dev/a`) fails; too many (`op://a/b/c/d/e`) fails; an empty segment (`op://dev//b`) fails; a query parameter (`op://dev/a/b?attribute=otp`) fails; another scheme (`https://user:pass@host`) fails.
- *Malformed lines:* a bare value with no `=` fails; YAML-style `KEY: op://dev/a/b` fails; an invalid key (`1KEY=...`, `lower=...`) fails; leading indentation fails.
- *File level:* a repeated key fails; a file with no entries fails; a missing file fails; no arguments fails; reference files with no configuration file fail; a key present in both a reference file and a named configuration file fails.
- *Known limit:* a literal shaped like a reference (`op://hunter2/hunter2/hunter2`) passes. The fixture is marked as documenting the limit Scope Boundaries names, so nobody reads the pass as a defect or a guarantee.
- *Standard's example:* the check passes on the tree after U2. It fails when the `# secret-refs.env` block is removed. It fails when a key is copied from one example block into the other. It fails when a literal is planted in the example block. It fails when a marker line appears twice.
- *Self-test integrity:* flipping one fixture's expected class makes the run fail before any file is checked.

**Verification:** Every must-fail scenario was watched to exit non-zero for the expected reason, and each planted defect was reverted. The PR records the planted defects and their failures.

### U5. Wire the check into CI and the documentation

**Goal:** Make the check run on every relevant change, and list it where the repository documents its checks.

**Requirements:** R20, R21

**Dependencies:** U4

**Files:**
- `.github/workflows/docs.yml`
- `process/documentation-standards.md`

**Approach:**
1. Add a `check-secret-refs` job with no install step (KTD8), running the standard-example mode. Keep the top-level `permissions: contents: read`. Give the job the same NEVER comment the template-kit job carries: no `pull_request_target`, no secrets, no write token.
2. Add `scripts/check-secret-refs.mjs` to both the `pull_request` and the `push` path lists. `code/python-standards.md` is already covered by `**/*.md`.
3. In `### Automated Checks`, add a row saying what the check catches, a short paragraph like the template-kit one explaining that it is not a Markdown check, and its local run command. The row says a pass means only that the named files are well-formed, not that no secret is present. Adjust the intro sentence if it still implies every check is a Markdown check.

**Test scenarios:**
- On the PR, the new job runs and passes.
- Planting a literal in the standard's `secret-refs.env` block turns the job red. Revert afterwards.
- `node scripts/check-docs.mjs` passes on the edited `process/documentation-standards.md`.

**Verification:** The job appears on the PR's checks and has been seen to fail on a planted defect.

### U6. Point the web standard at the owner

**Goal:** Stop `code/web-application-standards.md` from restating the secrets rule, while keeping its own variables (KTD11).

**Requirements:** R22, R24

**Dependencies:** U1

**Files:**
- `code/web-application-standards.md`

**Approach:**
1. In `### Environment Variables`, add a link to `python-standards.md#secrets` for how secrets are handled.
2. Keep the web-stack variables, and state that the block's credential-shaped values are local-only configuration under R2.
3. Do not add a `secret-refs.env` block here; the owner holds the example.
4. State that a browser-exposed variable is public by construction and never appears in a reference file (R24).

**Test scenarios:**
- The new `#secrets` anchor resolves under `node scripts/check-docs.mjs`.
- No sentence in the section restates a tier.

**Verification:** `check-docs` passes, and the section links to the rule rather than restating it.

---

## Verification Contract

| Gate | Command or action | Proves |
|---|---|---|
| Reference check | `node scripts/check-secret-refs.mjs` in standard-example mode | The fixtures classify correctly and the standard's examples pass and share no key |
| Planted defects | Each U4 must-fail scenario and each U5 planted literal, then reverted | The check fails when it should, not only passes when it should |
| Documentation | `npm ci --prefix scripts && node scripts/check-docs.mjs` | Links, anchors including `#secrets` and `#configuration-management`, and fences |
| Template kit | `node scripts/check-template-kit.mjs` | Unchanged, and still green |
| Permission claim | Run the kit's `bashRuleMatches` against `Bash(uv:*)` with `uv run op read op://dev/a/b` and `uv run cat .env` | The standard's statement that the kit pre-approves these holds on the merged kit |
| Corpus sweep | Search `code/`, `process/`, `ai/`, `templates/`, `docs/` and `README.md` for `.env`, `example.env`, `secret` and `credential`, and classify every hit | No live statement contradicts `### Secrets`; out-of-scope hits are the named follow-ups |
| CI | The PR's checks | All three jobs green on the final head |

---

## Definition of Done

- Every requirement R1–R32 is met, and each unit's verification holds.
- Every CLI syntax the standard states is cited with package and version, or labelled unverified with its date.
- Every must-fail fixture and planted defect was seen to fail, and the PR says which ones.
- The corpus sweep is recorded in the PR, and every remaining out-of-scope hit maps to an item under Deferred to Follow-Up Work.
- No planted defect, probe file or experimental code remains in the diff.
- CI is green on the final head.
