# Engineering Standards

This project follows the engineering standards defined in the
[engineering-standards](https://github.com/rmorison/engineering-standards)
repository. Read and follow these standards for all work.

## Feature Development

Follow the spec-driven workflow: **Intent → Spec → Plan → Execute → Validate**.

- Read the spec before writing code
- Break work into small, reviewable increments
- Validate each increment against the spec before moving on

Full workflow: [process/feature-development-workflow.md](../../process/feature-development-workflow.md)

## Documentation

Specs are the source of truth. Write specs before code when:
- The feature has UI/UX components
- Multiple implementation approaches exist
- Work spans multiple PRs
- Requirements need stakeholder validation

Skip specs for trivial changes, obvious implementations, or experiments.

Standard structure:
```
docs/
├── product/
│   ├── strategic-vision.md
│   ├── concepts/{feature}.md
│   └── features/{feature}.md
└── engineering/
    ├── design/{feature}.md
    └── adr/{number}-{title}.md
```

Full standard: [process/documentation-standards.md](../../process/documentation-standards.md)

## Git Conventions

- **Branching**: GitHub Flow — `main` is always deployable, all work in feature branches
- **Branch names**: `{issue-number}-{slugified-title}` (use GitHub auto-generated names)
- **Commits**: Conventional format — `type(scope): description`
- **PRs**: Small, focused, one feature/fix per branch
- **Versioning**: Semantic versioning (vMAJOR.MINOR.PATCH)

Full strategy: [process/git-branching-strategy.md](../../process/git-branching-strategy.md)

## Code Quality Principles

- No dead code — remove unused code, don't comment it out
- Root-cause fixes — diagnose before patching, no bandaids
- Single responsibility — each module does one thing well
- Don't cross module boundaries for quick fixes — raise for discussion
- Validate after every meaningful change

Language-specific standards: [code/](../../code/)
