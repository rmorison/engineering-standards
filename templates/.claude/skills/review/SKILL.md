# /review — Review code against engineering standards

Review code changes against the project's engineering standards.

## Instructions

1. Fetch the feature development workflow and code standards for reference:

<web_fetch>
https://raw.githubusercontent.com/rmorison/engineering-standards/main/process/feature-development-workflow.md
</web_fetch>

<web_fetch>
https://raw.githubusercontent.com/rmorison/engineering-standards/main/code/python-standards.md
</web_fetch>

2. Identify what to review:
   - If the user specifies files or a PR, review those
   - If no target is specified, review staged or uncommitted changes (`git diff` and `git diff --cached`)
   - Read the relevant spec or issue for context on what the changes should accomplish

3. Review against these categories:

   **Spec compliance**
   - Do the changes implement what the spec describes?
   - Are acceptance criteria addressed?
   - Is anything missing or out of scope?

   **Code quality**
   - No dead code or commented-out code
   - Single responsibility per module/function
   - No unnecessary complexity or premature abstractions
   - Error handling at system boundaries, not everywhere

   **Git hygiene**
   - Commits follow conventional format: `type(scope): description`
   - Changes are focused — one concern per commit
   - No unrelated changes mixed in

   **Testing**
   - Are changed behaviors covered by tests?
   - Do existing tests still pass?
   - Are edge cases from the spec addressed?

   **Documentation**
   - Are specs updated if behavior changed?
   - Are ADRs written for significant decisions?

4. Present findings organized by category. For each issue:
   - State what the standard says
   - Show the specific code or commit that deviates
   - Suggest a fix

5. Summarize: overall assessment (approve, request changes, or needs discussion)
   and a prioritized list of action items.

## Notes

- Focus on substantive issues, not style nitpicks
- If the project has language-specific standards (e.g., Python), apply those too
- Flag security concerns (OWASP top 10) if spotted
