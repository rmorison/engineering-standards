# /plan — Break work into estimated, sequenced tasks

Create a project plan with task breakdown, estimates, and sequencing.

## Instructions

1. Fetch the project planning standards for reference:

<web_fetch>
https://raw.githubusercontent.com/rmorison/engineering-standards/main/process/project-planning-standards.md
</web_fetch>

2. Identify the scope of work. Ask the user for:
   - The spec or feature description to plan against
   - Any known constraints (timeline, dependencies, team size)
   - Whether this plan feeds into GitHub issues or is for discussion

3. Break the work down into tasks following the planning standards:
   - Each task should be independently deliverable
   - Target 1–5 story points per task (split anything larger)
   - Identify dependencies between tasks
   - Flag risks and unknowns

4. Estimate each task using the Fibonacci scale:
   - 1 point: trivial (~half day)
   - 2 points: straightforward (~1 day, baseline)
   - 3 points: moderate complexity (~1.5 days)
   - 5 points: significant (~2–3 days)
   - 8 points: complex (~4 days, consider splitting)
   - 13 points: too large — must be split

5. Sequence the tasks:
   - Identify the critical path
   - Group parallelizable work
   - Note external dependencies or blockers

6. Present the plan as a table with: task, estimate, dependencies, and notes.
   Wait for confirmation before creating issues.

## Notes

- Plans are living documents — expect iteration
- Points measure complexity, not hours
- If total exceeds 40 points, suggest phasing the work into milestones
