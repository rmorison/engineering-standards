# Database Standards Agent Transcript

*A conversation log documenting the creation of database standards for PostgreSQL*

---

## Initial Request: Database Standards for a New Project

**User:** I'm starting a new application project that will use PostgreSQL. I need a database standards document to complement the existing Python project standards. I want guidance on schemas, table/column naming, migrations, and access patterns. PostgreSQL is the core database engine.

**AI Agent:** I'll work through the key decisions with you and then produce a standards document following the format established by `python-standards.md`. Let me start by asking about some of the design choices.

---

## Deciding on Schemas and Domain Boundaries

**AI Agent:** How do you want to organize tables within PostgreSQL? One big schema, or per-domain schemas?

**User:** Per-domain schemas. Dependencies between schemas should form a DAG — no circular references.

**AI Agent:** That's a clean approach. Foreign key direction would enforce the dependency direction: if `billing.invoices` references `inventory.products`, then `billing` depends on `inventory`, and the reverse FK must never exist. The `public` schema can hold shared utilities like trigger functions so domain schemas all depend on `public` but `public` never depends on them.

**User:** Yes, that's the model.

---

## Naming Conventions

**AI Agent:** For naming, I'd suggest snake_case throughout, plural table names, and explicit prefixed constraint names.

**User:** Agreed. snake_case, plural table names.

**AI Agent:** For constraints and indexes, I'll use prefixed naming: `pk_` for primary keys, `fk_` for foreign keys, `uq_` for unique, `idx_` for indexes, `ck_` for check constraints. Auto-generated names are unpredictable and hard to reference in migrations or error handling.

---

## Migrations: golang-migrate Over Alembic

**User:** For migrations, I want golang-migrate, not Alembic. Alembic couples you to SQLAlchemy's ORM, and it handles multi-schema migrations poorly. golang-migrate gives you plain SQL files, it's language-agnostic, and it's simpler.

**AI Agent:** Makes sense — that also aligns with the "no ORM" philosophy. I'll structure migrations as per-schema directories with up/down pairs, run in DAG dependency order.

---

## Data Access: Direct SQL, No ORM

**User:** No SQLAlchemy ORM. Direct SQL with psycopg 3 and Pydantic models for validation.

**AI Agent:** So the pattern is: psycopg 3 for database interaction, parameterized queries only, and Pydantic models at the boundary for validation and serialization. Every database interaction is explicit — no hidden queries.

**User:** Exactly. Transparent access, easy to optimize and debug.

---

## Standard Columns and UUID v7

**AI Agent:** I'd recommend three standard columns on every table: `id` (UUID primary key), `created_at` (immutable timestamp), and `updated_at` (auto-updated via trigger). UUID v7 gives you time-ordering for better B-tree index locality while keeping IDs globally unique and opaque.

**User:** UUID v7 is the right choice. For the `updated_at` trigger, define it once in `public` and apply per-table.

**AI Agent:** I'll write the trigger function as `public.set_updated_at()`, with per-table triggers named `trg_<table>_set_updated_at`.

---

## Document Creation

**AI Agent:** I'll create `code/database-standards.md` following the established pattern: title with italicized subtitle, overview with core principle, philosophy section, content sections, anti-patterns with `❌` markers, references, and Draft status. I'll also update `code/README.md` with a summary entry and the top-level `README.md` to link to the new standard.

*[Document created with all agreed decisions, READMEs updated]*

---

## Post-Creation: Two Additions to Consider

**User:** Two things we can consider adding. First, database user name/access standards — I've found `_all`, `_write`, `_read` roles useful, along with `main` as the root user conforming to a superuser locally or the provided root user for AWS RDS. `_all` is all privs we can assign, `_write` is a typical API service role with CRUD access, `_read` is read only. The prefix to these suffixes can be something like `{application}_{env}`.

Second, UUID v7 — what are the pros and cons of computing that in a database function and applying it as default, vs relying on the application?

**AI Agent:** On the role naming — that's a solid pattern. `main` as root, then `{app}_{env}_all` for migrations/DDL, `{app}_{env}_write` for application services, `{app}_{env}_read` for reporting. It maps cleanly to real deployments and handles the cloud reality where root isn't truly a superuser.

On UUID v7 generation, there are real trade-offs:

**Database function (default on column):**
- Consistent regardless of client language, can't forget to set it, single source of truth
- Requires `pg_uuidv7` extension, adds a PostgreSQL dependency

**Application layer:**
- No extension needed, works anywhere, application can use the ID before insert
- Every client must remember to generate it, different services could produce different implementations

The current document hand-waves this — it says "generate in app, database default is a v4 fallback." Worth being more explicit.

**User:** We had success in an unrelated project with the `pg_uuidv7` extension, worked fine in AWS RDS. Let's make that the standard and note that if the extension is not available, fall back to application-side inclusion. With that in mind, is there a construct that prevents a database role from trying to insert or update that column, where we have a database default filling it?

**AI Agent:** Yes — PostgreSQL column-level privileges. If you grant INSERT only on specific business columns (omitting `id`, `created_at`, `updated_at`), the role can't supply those values and the DEFAULTs fill them in. Same for UPDATE. It's verbose — you have to enumerate columns per table — but it's the correct mechanism and pairs naturally with the role hierarchy.

**User:** Add the role standards. For UUID v7, make `pg_uuidv7` the standard.

---

## Implementing the Role and UUID Changes

**AI Agent:** I made the following changes:

**UUID v7 — `pg_uuidv7` as standard:**
- Added `pg_uuidv7` to required extensions
- Changed all `gen_random_uuid()` defaults to `uuid_generate_v7()` across all examples
- New "UUID v7 Generation Strategy" section explaining standard (database-side) vs fallback (application-side)
- Updated the INSERT example to omit `id` — the database handles it
- Added to references

**Database Roles and Access** (replaced the generic three-bullet section):
- `main` as root/superuser (local or cloud-provided admin)
- `{app}_{env}_all` — full assignable privileges, runs migrations
- `{app}_{env}_write` — CRUD for API services, no DDL
- `{app}_{env}_read` — SELECT only, for reporting/debugging
- Column-level privileges section with examples
- Migration examples for GRANT/REVOKE in up/down pairs
- Cloud provider considerations (AWS RDS limitations)

---

## Adding View and Materialized View Naming

**User:** One more standard to consider: naming standards for views and materialized views. Recommendations?

**AI Agent:** Given the document already uses explicit prefixes for constraints and triggers, the natural extension is `v_` for views and `mv_` for materialized views. The prefix matters here because someone reading a query needs to know if they're hitting a view (possible complex join, performance implications) vs a materialized view (stale data between refreshes, storage, needs explicit `REFRESH`). For indexes on materialized views, the existing `idx_` convention works: `idx_mv_product_search_name`.

**User:** Yes, add it.

*[Added "Views and Materialized Views" subsection to Naming Conventions, added `v_` and `mv_` to the prefix summary table]*

---

## Key Decisions Summary

1. **Database engine:** PostgreSQL (standard for all projects)
2. **Schema architecture:** Per-domain schemas with DAG dependency rule
3. **Naming:** snake_case, plural tables, prefixed constraints, `v_`/`mv_` for views
4. **Primary keys:** UUID v7 via `pg_uuidv7` extension (database-generated)
5. **Timestamps:** Database-managed `created_at`/`updated_at` with trigger
6. **Data access:** Direct SQL + psycopg 3 + Pydantic (no ORM)
7. **Migrations:** golang-migrate with per-schema directories (not Alembic)
8. **Roles:** `main` / `{app}_{env}_all` / `_write` / `_read` hierarchy
9. **Column protection:** Column-level privileges prevent application roles from writing system columns
10. **Security:** Parameterized queries mandatory, least-privilege roles, credentials via environment variables

---

## Evolution of Thinking

**UUID v7 generation** went through three stages: initially application-side generation with a v4 database fallback, then shifted to database-side generation via `pg_uuidv7` after the user confirmed AWS RDS support from another project, then strengthened further with column-level privileges that prevent application roles from overriding the database-generated values.

**Database roles** started as a generic three-role model with placeholder names like `app_user`. The user brought practical experience with the `{app}_{env}_{level}` pattern and the `main` / `_all` / `_write` / `_read` hierarchy, which maps directly to real deployment scenarios and handles the cloud provider reality where root isn't a true superuser.

**Key insight:** Making the database the single source of truth for ID generation and enforcing it via column-level privileges creates a stronger guarantee than relying on application discipline. The `pg_uuidv7` extension + column-level grants pattern ensures consistency regardless of which client or tool accesses the database.

---

## Addendum: Tools and Technology

**Tool:** Claude Code (Anthropic's official CLI for Claude)

**Model:** Claude Opus 4.6

**Date:** February 2026

The AI agent assisted with document creation, researching PostgreSQL mechanisms (column-level privileges, extension availability), drafting content, and iterating based on the user's practical experience with database role patterns and UUID v7 in production environments.

---

*This transcript documents the conversation that created the database standards. It captures the reasoning behind decisions and the evolution of thinking as the standard took shape.*
