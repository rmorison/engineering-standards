# SDLC Workflow

Behavioral guardrails for Claude Code sessions. Follow these in every task.

## Read Before Changing

- Read the relevant spec, issue, or requirements before touching code
- Read the existing code and understand its structure before modifying it
- Check for related tests, configs, or documentation that may need updating
- If there is no spec and the change is non-trivial, ask for one

## Plan Before Implementing

- Author a plan and present it before writing any code
- Wait for explicit confirmation before proceeding with implementation
- If the plan changes during implementation, pause and re-confirm
- Break large changes into steps; confirm each step's approach

## Validate After Each Change

- After each meaningful change: run tests, run lint, confirm behavior
- Do not batch multiple unverified changes — validate incrementally
- Check that the change matches what the spec or issue describes
- If tests don't exist for the changed behavior, note it and suggest adding them

## Flag Uncertainty

- If requirements are ambiguous, ask — don't guess
- If multiple valid approaches exist, present options with tradeoffs
- If a change has broader implications than expected, raise it before proceeding
- Prefer explicit confirmation over assumptions

## Scope Discipline

- Do only what was asked — no unrequested refactoring or improvements
- Don't add error handling, comments, or type annotations to unchanged code
- If you notice something worth fixing outside the current scope, mention it
  separately rather than including it in the current change
- Match the complexity of the solution to the complexity of the problem
