# Database Standards

*PostgreSQL conventions and practices for application database design*

## Overview

This document defines standards for database design, schema management, data access, and migrations in application projects. These standards prioritize:

- **Data integrity** - The database enforces business rules through constraints and types
- **Explicit SQL** - Direct SQL over ORM abstractions for clarity and control
- **Domain boundaries** - Schemas as organizational units with clear dependency direction
- **Safe evolution** - Versioned, reversible migrations with predictable tooling

**Core principle**: The database is the source of truth for data integrity. Use SQL directly, let PostgreSQL do what it does best, and keep your application code focused on business logic.

## Philosophy

### Direct SQL Over ORM

ORMs add abstraction at the cost of control. When the database is central to your application:
- **SQL is the interface** - Write queries you can reason about, optimize, and debug
- **Pydantic for validation** - Application-layer models handle serialization and input validation
- **No hidden queries** - Every database interaction is explicit and visible

### Database as Authority

The database enforces data integrity, not the application:
- Constraints (`NOT NULL`, `CHECK`, `UNIQUE`, foreign keys) live in the schema
- Default values and timestamps are database-managed
- The application validates input; the database guarantees consistency

### Schemas as Domain Boundaries

Use PostgreSQL schemas to organize related tables into domains. Schema dependencies form a directed acyclic graph (DAG)—no circular references. This keeps domains decoupled and migration order predictable.

---

## PostgreSQL as Standard Engine

### Why PostgreSQL

PostgreSQL is the default database engine for all application projects:
- Mature, well-documented, open source
- Rich type system (JSONB, arrays, UUIDs, TIMESTAMPTZ)
- Schema support for domain separation
- Strong extension ecosystem
- Excellent tooling and driver support (psycopg 3)

### Required Extensions

Enable these extensions in your database setup as needed:

```sql
-- Trigram similarity for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Cryptographic functions (if needed)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

**Note on UUID v7**: PostgreSQL 18+ provides native `uuidv7()` — no extension required. For PostgreSQL 17 and earlier, use the [pg_uuidv7](https://github.com/fboulnois/pg_uuidv7) extension or generate UUID v7 values in the application layer (see [Primary Keys and References](#primary-keys-and-references)).

### Version Guidance

**Target PostgreSQL 18+** for new projects. PostgreSQL 18 is available on all major cloud providers (AWS RDS, Google Cloud SQL, Azure Database for PostgreSQL) as of late 2025. Key advantages of 18+ include native `uuidv7()` support and I/O subsystem improvements.

Support the latest two major versions (17, 18) for production deployments. If constrained to PostgreSQL 17, see the UUID v7 fallback guidance in [Primary Keys and References](#primary-keys-and-references).

---

## Schema Design

### Per-Domain Schemas

Organize tables into schemas by business domain:

```sql
-- Shared utilities (trigger functions, common types)
-- public schema is used for cross-domain shared objects
CREATE SCHEMA IF NOT EXISTS public;

-- Domain-specific schemas
CREATE SCHEMA IF NOT EXISTS inventory;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS auth;
```

### DAG Dependency Rule

Schema dependencies must form a directed acyclic graph. A schema may reference tables in schemas it depends on, but never the reverse.

```
public (shared utilities)
  ├── auth (depends on public)
  ├── inventory (depends on public, auth)
  └── billing (depends on public, auth, inventory)
```

**Foreign key direction enforces dependency direction**: If `billing.invoices` has a foreign key to `inventory.products`, then `billing` depends on `inventory`. The reverse FK must never exist.

**Validating no cycles**: Review your schema dependency graph during design. For automated validation, query `information_schema.table_constraints` to extract FK relationships and verify the graph is acyclic:

```sql
-- List all cross-schema foreign key dependencies
SELECT
    tc.table_schema AS source_schema,
    tc.table_name AS source_table,
    ccu.table_schema AS target_schema,
    ccu.table_name AS target_table
FROM information_schema.table_constraints tc
JOIN information_schema.constraint_column_usage ccu
    ON tc.constraint_name = ccu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema != ccu.table_schema
ORDER BY source_schema, target_schema;
```

### Public Schema for Shared Utilities

The `public` schema holds objects used across domains:
- Trigger functions (e.g., `set_updated_at()`)
- Shared enum types or lookup tables
- Extension-provided functions

Domain schemas depend on `public`, but `public` never depends on domain schemas.

---

## Naming Conventions

### Tables

- **Plural nouns**: `users`, `invoices`, `line_items`
- **snake_case**: `order_items`, not `OrderItems` or `orderItems`
- **Schema-qualified in queries**: `inventory.products`, `billing.invoices`

### Columns

- **snake_case**: `created_at`, `user_id`, `email_address`
- **Foreign key columns**: `<singular_referenced_table>_id` (e.g., `user_id`, `product_id`)
- **Boolean columns**: Use positive names (`is_active`, `has_verified_email`)

### Views and Materialized Views

Prefix views to distinguish them from tables — this matters for performance reasoning (views may hide complex joins) and data freshness (materialized views are stale between refreshes).

- **Views**: `v_` prefix — `v_active_users`, `v_invoice_totals`
- **Materialized views**: `mv_` prefix — `mv_monthly_revenue`, `mv_product_search`
- **snake_case**, schema-qualified: `billing.v_overdue_invoices`, `inventory.mv_product_catalog`
- **Indexes on materialized views**: Use the standard `idx_` prefix — `idx_mv_product_search_name`

### Constraints and Indexes

Use prefixed naming for all constraints and indexes:

| Type | Prefix | Pattern | Example |
|------|--------|---------|---------|
| Primary key | `pk_` | `pk_<table>` | `pk_users` |
| Foreign key | `fk_` | `fk_<table>_<column>` | `fk_orders_user_id` |
| Unique | `uq_` | `uq_<table>_<columns>` | `uq_users_email` |
| Index | `idx_` | `idx_<table>_<columns>` | `idx_orders_created_at` |
| Check | `ck_` | `ck_<table>_<description>` | `ck_orders_total_positive` |
| View | `v_` | `v_<description>` | `v_active_users` |
| Materialized view | `mv_` | `mv_<description>` | `mv_monthly_revenue` |

**Multi-column constraints**: Join column names with underscores: `uq_orders_user_id_product_id`

---

## Standard Columns

Every table includes these columns:

### id — UUID v7 Primary Key

```sql
id UUID NOT NULL DEFAULT uuidv7()
```

The database generates time-ordered UUID v7 values via PostgreSQL 18's native `uuidv7()` function. Application code should **not** supply `id` values on insert — let the database default handle it (see [Column-Level Privileges](#column-level-privileges-for-system-columns) for enforcement).

### created_at — Immutable Creation Timestamp

```sql
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

Set once at row creation. Never updated.

### updated_at — Auto-Updated Modification Timestamp

```sql
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

Automatically updated via a database trigger.

### Trigger Function for updated_at

Define once in the `public` schema:

```sql
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

Apply to each table:

```sql
CREATE TRIGGER trg_users_set_updated_at
    BEFORE UPDATE ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();
```

**Trigger naming**: `trg_<table>_set_updated_at`

### Complete Table Example

```sql
CREATE TABLE inventory.products (
    id UUID NOT NULL DEFAULT uuidv7(),
    name TEXT NOT NULL,
    sku TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_products PRIMARY KEY (id),
    CONSTRAINT uq_products_sku UNIQUE (sku),
    CONSTRAINT ck_products_price_positive CHECK (price_cents > 0)
);

CREATE INDEX idx_products_sku ON inventory.products (sku);

CREATE TRIGGER trg_products_set_updated_at
    BEFORE UPDATE ON inventory.products
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();
```

---

## Primary Keys and References

### UUID v7 Rationale

UUID v7 is the standard primary key type:
- **Time-ordered**: Sortable by creation time, good B-tree index locality
- **Globally unique**: Safe for distributed systems and cross-service references
- **No sequence contention**: No locking on sequence objects under concurrent inserts
- **Opaque**: Does not leak row counts or insertion order to external consumers

### UUID v7 Generation Strategy

**Standard (PostgreSQL 18+)**: Use the native `uuidv7()` function as the column default. This makes the database the single source of truth for ID generation — consistent regardless of client language, and impossible to forget. No extension required.

```sql
id UUID NOT NULL DEFAULT uuidv7()
```

Combined with [column-level privileges](#column-level-privileges-for-system-columns), application roles cannot supply their own `id` values, ensuring all primary keys are database-generated and time-ordered.

**Fallback (PostgreSQL 17 and earlier)**: If you cannot use PostgreSQL 18+, you have two options:

1. **pg_uuidv7 extension**: Provides `uuid_generate_v7()`. Available on some managed providers (e.g., Neon) but not on AWS RDS, Google Cloud SQL, or Azure.
2. **Application-side generation**: Generate UUID v7 in the application layer (e.g., Python's `uuid_utils` or `uuid7` package) and supply it on insert. Use `gen_random_uuid()` (UUID v4, built-in) as the column default for safety:

```sql
-- Fallback only — when on PostgreSQL 17 or earlier
id UUID NOT NULL DEFAULT gen_random_uuid()
```

### Foreign Key Conventions

- **Always name foreign keys**: `CONSTRAINT fk_<table>_<column> FOREIGN KEY ...`
- **Reference the primary key**: FKs reference `id` columns
- **Schema-qualify references**: `REFERENCES auth.users (id)`

```sql
CREATE TABLE billing.invoices (
    id UUID NOT NULL DEFAULT uuidv7(),
    user_id UUID NOT NULL,
    -- ...
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_invoices PRIMARY KEY (id),
    CONSTRAINT fk_invoices_user_id FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE RESTRICT
);
```

### Cascade Policies

Choose cascade behavior deliberately:

| Policy | When to Use |
|--------|-------------|
| `ON DELETE RESTRICT` | **Default**. Prevent deleting referenced rows. |
| `ON DELETE CASCADE` | Child rows are meaningless without the parent (e.g., order line items). |
| `ON DELETE SET NULL` | The reference is optional and can be cleared. |

**Prefer `RESTRICT`** unless there's a clear reason for cascading. Cascading deletes are convenient but dangerous—they hide the scope of destructive operations.

---

## Data Access Pattern

### Direct SQL with psycopg 3

Use psycopg 3 (the modern PostgreSQL driver for Python) for all database interactions:

```python
import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class Product(BaseModel):
    id: UUID
    name: str
    sku: str
    price_cents: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


async def get_product(conn: psycopg.AsyncConnection, product_id: UUID) -> Product | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM inventory.products WHERE id = %s",
            (product_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return Product.model_validate(row)


async def create_product(conn: psycopg.AsyncConnection, product: Product) -> Product:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            INSERT INTO inventory.products (name, sku, price_cents, is_active)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (product.name, product.sku, product.price_cents, product.is_active),
        )
        row = await cur.fetchone()
        return Product.model_validate(row)


async def list_active_products(conn: psycopg.AsyncConnection) -> list[Product]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM inventory.products WHERE is_active = true ORDER BY name"
        )
        rows = await cur.fetchall()
        return [Product.model_validate(row) for row in rows]
```

### Parameterized Queries Only

**Always** use parameterized queries. Never interpolate values into SQL strings:

```python
# Correct — parameterized
await conn.execute("SELECT * FROM users WHERE email = %s", (email,))

# NEVER — string interpolation (SQL injection vulnerability)
await conn.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

---

## Connection Management

### psycopg 3 Connection Pooling

Use psycopg's built-in connection pool:

```python
from psycopg_pool import AsyncConnectionPool

pool = AsyncConnectionPool(
    conninfo="postgresql://user:password@localhost:5432/mydb",
    min_size=2,
    max_size=10,
    open=False,
)

# Application startup
await pool.open()

# Application shutdown
await pool.close()

# Usage
async with pool.connection() as conn:
    await conn.execute("SELECT ...")
```

### Pool Sizing Guidance

- **min_size**: 2–5 connections for low-traffic applications
- **max_size**: Start with `(2 * CPU cores) + 1` as a baseline, adjust based on workload
- **Total connections**: Ensure `max_size * number_of_instances` does not exceed PostgreSQL's `max_connections`

### Connection Lifecycle

- Acquire connections from the pool, not by creating new ones
- Use `async with pool.connection()` to ensure connections are returned to the pool
- Let the pool handle connection health checks and reconnection
- Configure `max_idle` and `max_lifetime` to prevent stale connections

---

## Migrations

### golang-migrate as Standard Tool

Use [golang-migrate](https://github.com/golang-migrate/migrate) for all database migrations:
- Language-agnostic — works with any application stack
- No ORM coupling (unlike Alembic, which assumes SQLAlchemy)
- Clean up/down migration pairs in plain SQL
- Good multi-schema support
- Simple CLI and Docker integration

### Per-Schema Migration Directories

Organize migrations by schema:

```
db/
├── migrations/
│   ├── public/
│   │   ├── 000001_create_set_updated_at_function.up.sql
│   │   └── 000001_create_set_updated_at_function.down.sql
│   ├── auth/
│   │   ├── 000001_create_users_table.up.sql
│   │   ├── 000001_create_users_table.down.sql
│   │   ├── 000002_add_user_roles.up.sql
│   │   └── 000002_add_user_roles.down.sql
│   ├── inventory/
│   │   ├── 000001_create_products_table.up.sql
│   │   └── 000001_create_products_table.down.sql
│   └── billing/
│       ├── 000001_create_invoices_table.up.sql
│       └── 000001_create_invoices_table.down.sql
└── Makefile
```

### Migration File Naming

```
<sequence>_<description>.up.sql
<sequence>_<description>.down.sql
```

- **Sequence**: Zero-padded six-digit number (`000001`, `000002`)
- **Description**: snake_case summary of the change
- **Always create both up and down**: Every migration must be reversible

### Running Migrations

```bash
# Apply all pending migrations for a schema
migrate -path db/migrations/auth -database "$DATABASE_URL" up

# Roll back the last migration
migrate -path db/migrations/auth -database "$DATABASE_URL" down 1

# Go to a specific version
migrate -path db/migrations/auth -database "$DATABASE_URL" goto 3
```

**Migration tracking**: Each per-schema directory gets its own `schema_migrations` table in the database. golang-migrate creates this automatically on first run.

### Migration Execution Order

Run migrations in dependency order matching the schema DAG. Encode the order in a Makefile target:

```makefile
.PHONY: migrate-up
migrate-up:  ## Run all migrations in schema dependency order
	migrate -path db/migrations/public -database "$(DATABASE_URL)" up
	migrate -path db/migrations/auth -database "$(DATABASE_URL)" up
	migrate -path db/migrations/inventory -database "$(DATABASE_URL)" up
	migrate -path db/migrations/billing -database "$(DATABASE_URL)" up

.PHONY: migrate-down
migrate-down:  ## Roll back the last migration for each schema (reverse order)
	migrate -path db/migrations/billing -database "$(DATABASE_URL)" down 1
	migrate -path db/migrations/inventory -database "$(DATABASE_URL)" down 1
	migrate -path db/migrations/auth -database "$(DATABASE_URL)" down 1
	migrate -path db/migrations/public -database "$(DATABASE_URL)" down 1
```

### Idempotent Migrations

Write migrations that are safe to re-run after a partial failure (e.g., a migration that crashed mid-execution). Use `IF NOT EXISTS` and `IF EXISTS` guards so re-running the same migration doesn't error on already-applied statements:

```sql
-- Up migration: 000001_create_products_table.up.sql
CREATE SCHEMA IF NOT EXISTS inventory;

CREATE TABLE IF NOT EXISTS inventory.products (
    id UUID NOT NULL DEFAULT uuidv7(),
    name TEXT NOT NULL,
    sku TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Use IF NOT EXISTS for indexes and constraints added separately
CREATE INDEX IF NOT EXISTS idx_products_sku ON inventory.products (sku);
```

```sql
-- Down migration: 000001_create_products_table.down.sql
DROP TABLE IF EXISTS inventory.products;

-- Only drop schema if this was the only table
-- DROP SCHEMA IF EXISTS inventory;
```

---

## Security

### Parameterized Queries — Mandatory

This is non-negotiable. Every query that includes external input must use parameterized queries:

```python
# Always
await conn.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# Never
await conn.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

This applies to all contexts: application code, scripts, migration seed data, and ad-hoc tooling.

### Database Roles and Access

#### Role Naming Convention

Roles follow the pattern `{application}_{environment}_{level}`:

| Role | Purpose |
|------|---------|
| `main` | The literal superuser role name. Use `main` in Docker Compose (`POSTGRES_USER`), IaC provisioning, and managed service setup (e.g., the admin username when creating an AWS RDS instance). Owns databases and runs DDL. |
| `{app}_{env}_all` | All privileges that can be assigned on the database and its schemas. Runs migrations and manages schema objects. On cloud providers, this is the most-privileged role you can create (some provider-level privileges are reserved). |
| `{app}_{env}_write` | CRUD access (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) on application tables. The standard role for API services and application connections. No DDL privileges. |
| `{app}_{env}_read` | Read-only access (`SELECT` only). For reporting, debugging, dashboards, and analytics connections. |

**Examples**: `myapp_prod_all`, `myapp_prod_write`, `myapp_prod_read`, `myapp_dev_write`

#### Role Setup

```sql
-- Create roles (passwords come from secrets manager, not from migration files)
CREATE ROLE myapp_prod_all LOGIN;
CREATE ROLE myapp_prod_write LOGIN;
CREATE ROLE myapp_prod_read LOGIN;

-- _all: full privileges on all schemas (used for migrations and DDL)
GRANT ALL PRIVILEGES ON SCHEMA public, auth, inventory, billing TO myapp_prod_all;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public, auth, inventory, billing TO myapp_prod_all;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public, auth, inventory, billing TO myapp_prod_all;
ALTER DEFAULT PRIVILEGES IN SCHEMA public, auth, inventory, billing
    GRANT ALL PRIVILEGES ON TABLES TO myapp_prod_all;
ALTER DEFAULT PRIVILEGES IN SCHEMA public, auth, inventory, billing
    GRANT ALL PRIVILEGES ON SEQUENCES TO myapp_prod_all;

-- _read: SELECT only
GRANT USAGE ON SCHEMA auth, inventory, billing TO myapp_prod_read;
GRANT SELECT ON ALL TABLES IN SCHEMA auth, inventory, billing TO myapp_prod_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA auth, inventory, billing
    GRANT SELECT ON TABLES TO myapp_prod_read;

-- _write: CRUD on business columns (see column-level privileges below)
GRANT USAGE ON SCHEMA auth, inventory, billing TO myapp_prod_write;
```

#### Column-Level Privileges for System Columns

The `_write` role should not be able to supply values for database-managed columns (`id`, `created_at`, `updated_at`). PostgreSQL's column-level privileges enforce this.

Instead of granting table-level INSERT/UPDATE (which allows writing to all columns), grant on specific business columns only:

```sql
-- Grant SELECT at the table level (reads all columns)
GRANT SELECT ON inventory.products TO myapp_prod_write;

-- Grant INSERT only on business columns — id, created_at, updated_at
-- are omitted, so the database defaults fill them in
GRANT INSERT (name, sku, price_cents, is_active)
    ON inventory.products TO myapp_prod_write;

-- Grant UPDATE only on mutable business columns — id and created_at
-- are never updated, updated_at is handled by the trigger
GRANT UPDATE (name, sku, price_cents, is_active)
    ON inventory.products TO myapp_prod_write;

-- Grant DELETE at the table level
GRANT DELETE ON inventory.products TO myapp_prod_write;
```

**How this works**: When the `_write` role inserts a row without specifying `id`, `created_at`, or `updated_at`, PostgreSQL applies the column defaults (`uuidv7()`, `NOW()`, `NOW()`). If the role attempts to supply those columns, the query fails with a privilege error.

**Trade-off**: Column-level grants must enumerate business columns per table, which is more verbose than table-level grants. This is additional work in migrations but provides strong guarantees that system columns are database-managed. Apply this pattern to tables where the guarantee matters (most application tables); for internal/utility tables the overhead may not be warranted.

#### Applying Grants in Migrations

Role grants belong in migrations, run by the `_all` role:

```sql
-- In 000002_grant_products_access.up.sql
GRANT SELECT ON inventory.products TO myapp_prod_write;
GRANT INSERT (name, sku, price_cents, is_active) ON inventory.products TO myapp_prod_write;
GRANT UPDATE (name, sku, price_cents, is_active) ON inventory.products TO myapp_prod_write;
GRANT DELETE ON inventory.products TO myapp_prod_write;

GRANT SELECT ON inventory.products TO myapp_prod_read;
```

```sql
-- In 000002_grant_products_access.down.sql
REVOKE ALL ON inventory.products FROM myapp_prod_write;
REVOKE ALL ON inventory.products FROM myapp_prod_read;
```

#### Cloud Provider Considerations

- **AWS RDS**: Specify `main` as the admin username when creating the RDS instance. Note that `main` on RDS is not a true PostgreSQL superuser — some provider-level privileges are reserved by AWS. The `_all` role can hold all privileges RDS allows you to assign.
- **Other managed providers**: Similarly, configure `main` as the admin username at provisioning time. The `_all` role represents the maximum assignable privilege level, not necessarily PostgreSQL superuser.

### Credential Management

- **Environment variables**: `DATABASE_URL` or individual `PGHOST`, `PGUSER`, `PGPASSWORD` vars
- **Secrets managers**: AWS Secrets Manager, HashiCorp Vault, etc. for production
- **Never in code**: No credentials in source code, configuration files, or migration scripts
- **Never in migrations**: Migrations should not contain passwords, API keys, or seed data with real credentials

Follow the credential management patterns defined in [Python Project Standards](./python-standards.md#configuration-management).

---

## Configuration

### DATABASE_URL Pattern

Use a standard connection URL:

```
postgresql://user:password@host:port/database?sslmode=require
```

Set via environment variable:

```bash
# .env (local development — SSL not needed for localhost/Docker)
DATABASE_URL=postgresql://main:localpass@localhost:5432/myapp_dev

# Production — always require SSL
# DATABASE_URL=postgresql://myapp:password@prod-db.rds.amazonaws.com:5432/myapp?sslmode=require
```

### Docker Compose for Local Development

```yaml
services:
  db:
    image: postgres:18
    environment:
      POSTGRES_DB: myapp_dev
      POSTGRES_USER: main
      POSTGRES_PASSWORD: localpass
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

**Local development setup**:
1. `docker compose up -d` to start PostgreSQL
2. Run migrations in schema dependency order
3. Application connects via `DATABASE_URL`

---

## Anti-Patterns

### ❌ ORM Usage

**Problem**: ORMs hide query behavior, generate unpredictable SQL, and make performance issues hard to diagnose.

**Solution**: Write SQL directly with psycopg 3. Use Pydantic models for data validation and serialization.

### ❌ String Interpolation in Queries

**Problem**: SQL injection vulnerability—the most common and dangerous database security flaw.

**Solution**: Always use parameterized queries (`%s` placeholders with psycopg).

### ❌ Shared Mutable Schemas

**Problem**: Multiple domains writing to the same schema creates coupling and makes migrations unpredictable.

**Solution**: Assign each domain its own schema. Share only read-only utilities in `public`.

### ❌ Circular Schema Dependencies

**Problem**: Circular foreign keys between schemas make migration order impossible and indicate tangled domain boundaries.

**Solution**: Redesign domain boundaries. If two schemas depend on each other, they are likely one domain or need a shared parent schema.

### ❌ Migrations Without Down Scripts

**Problem**: Cannot roll back failed deployments. Leaves the database in an unknown state during incidents.

**Solution**: Every up migration has a corresponding down migration. Test both directions.

### ❌ Auto-Incrementing Integer Primary Keys

**Problem**: Leak row counts, create sequence contention under load, and are not globally unique across services.

**Solution**: Use UUID v7 for all primary keys.

### ❌ Missing Constraint Names

**Problem**: Auto-generated constraint names are unpredictable and hard to reference in migrations or error handling.

**Solution**: Explicitly name all constraints using the standard prefixes (`pk_`, `fk_`, `uq_`, `ck_`).

### ❌ Credentials in Code or Migrations

**Problem**: Secrets in source control are a security incident waiting to happen.

**Solution**: Use environment variables and secrets managers. Never put credentials in migration files or application code.

---

## References

### Tools
- [PostgreSQL](https://www.postgresql.org/) - Database engine
- [psycopg 3](https://www.psycopg.org/psycopg3/) - Python PostgreSQL driver
- [golang-migrate](https://github.com/golang-migrate/migrate) - Database migration tool
- [Pydantic](https://docs.pydantic.dev/) - Data validation and serialization

### Standards and Guides
- [PostgreSQL Naming Conventions](https://www.postgresql.org/docs/current/sql-syntax-lexical.html#SQL-SYNTAX-IDENTIFIERS) - Identifier rules
- [UUID v7 (RFC 9562)](https://www.rfc-editor.org/rfc/rfc9562) - Time-ordered UUID specification

### Related Documentation
- [Python Project Standards](./python-standards.md) - Application tooling and configuration management
- [Documentation Standards](../process/documentation-standards.md) - Documentation practices
- [Feature Development Workflow](../process/feature-development-workflow.md) - Development process

---

## Status

**Draft** - This standard is in active development and subject to revision based on practical experience.
