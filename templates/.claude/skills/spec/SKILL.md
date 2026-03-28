# /spec — Draft a specification

Draft a specification document following the engineering standards documentation format.

## Instructions

1. Fetch the documentation standards for reference:

<web_fetch>
https://raw.githubusercontent.com/rmorison/engineering-standards/main/process/documentation-standards.md
</web_fetch>

2. Ask the user what they want to spec. Gather:
   - Feature name and one-line description
   - Problem being solved and target users
   - Whether this is a product spec (`docs/product/features/`) or technical design (`docs/engineering/design/`)

3. Draft the spec following the standard structure from the documentation standards:
   - For product specs: problem statement, requirements, acceptance criteria, UI/UX considerations
   - For technical designs: context, approach, alternatives considered, risks
   - For ADRs: status, context, decision, consequences

4. Present the draft for review. Iterate based on feedback.

5. Write the final spec to the correct path using the project's directory structure.

## Notes

- Use kebab-case filenames: `feature-name.md`
- Keep specs focused — one feature per document
- Include acceptance criteria that can be validated
- Link related specs and ADRs where relevant
