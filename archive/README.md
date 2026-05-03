# Archive

Documents preserved here for historical context. Their implementation strategy was superseded; the analytical content remains as the framework that informed subsequent decisions.

## Agent-Native Analysis (path-not-taken)

Three documents proposed building agent-native abstractions in this repository — a thin agent-native layer with workflows, learnings directories, JSON indices, parity matrices, and so on.

- **[`adoption-roadmap.md`](./adoption-roadmap.md)** (2026-01-24) — phased adoption plan for agent-native principles
- **[`agent-native-improvements.md`](./agent-native-improvements.md)** (2026-01-22) — full enumeration of 10 agent-native improvements
- **[`top-3-enhancements.md`](./top-3-enhancements.md)** (2026-01-24) — three highest-impact items distilled from the above

These were superseded by [ADR-0001: Six-Layer AI Architecture](../docs/engineering/adr/0001-six-layer-ai-architecture.md). Rather than build agent-native abstractions in-house, the repository adopted the [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) plugin as the canonical realization of Layers 2 (Workflow Skills), 3 (Persona Agents), 4 (References), and 5 (Compound / Learnings). The four-layer model these documents proposed evolved to a six-layer model that better accommodates a developed LLM-engineering system; see the ADR for the architectural reasoning.

The analysis in these documents remains valid as the evaluative framework. If the canonical-realization decision is ever revisited, this analysis is the lens.

## How archive works

The `archive/` directory exists at the top level of the repository — outside `ai/` and `templates/` — so:

- Recursive globs targeting `ai/**/*.md` or `templates/**/*.md` (which AI tools, RAG systems, and template-copying workflows often use) do not pick up archived content.
- Adopters who copy `ai/` or `templates/` subtrees into a new project don't inherit superseded plans with broken relative ADR links.

Future archived content can land here following the same pattern: relocate the file to `archive/`, add a banner pointing at the superseding decision, list it in this README.
