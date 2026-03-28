# Web Application Standards

*Full-stack web application standards for Next.js + FastAPI projects*

## Overview

This document defines standards for full-stack web applications using a Next.js frontend and FastAPI backend in a Turborepo monorepo. These standards prioritize:

- **Type safety across the stack** - TypeScript frontend, Pydantic backend, auto-generated API client
- **Developer experience** - Fast builds, hot reload, consistent tooling, one repo
- **Testing at every layer** - Vitest for components, Playwright for e2e, pytest for backend
- **Clear boundaries** - Frontend and backend are separate applications connected by an OpenAPI contract

**Core principle**: The OpenAPI schema is the contract between frontend and backend. Auto-generate the TypeScript client from FastAPI's schema so the two sides stay in sync without manual effort.

## Philosophy

### Monorepo, Separate Concerns

Frontend and backend live in one repository but remain independent applications:
- The Next.js app is a TypeScript project managed by npm
- The FastAPI service is a Python project managed by uv
- The OpenAPI schema is the only coupling between them
- Turborepo orchestrates the TypeScript side; Make orchestrates the Python side

### Server-First Rendering

Next.js App Router defaults to Server Components. Embrace this:
- Fetch data on the server when possible — less client JavaScript, faster initial paint
- Use Client Components (`"use client"`) only when you need interactivity (event handlers, hooks, browser APIs)
- Server Components can call your FastAPI backend server-to-server, skipping CORS and reducing latency

### Convention Over Configuration

Lean on framework defaults:
- Next.js App Router file-based routing
- Tailwind CSS utility classes over custom CSS
- shadcn/ui components over building from scratch
- FastAPI's automatic OpenAPI schema generation

---

## Tool Stack

### Frontend

| Tool | Purpose | Rationale |
|------|---------|-----------|
| **Next.js** (App Router) | React framework | SSR, file-based routing, Server Components, API routes |
| **TypeScript** | Language | Type safety, IDE support, catches errors at compile time |
| **npm** | Package manager | Default for Node.js, broad ecosystem support |
| **Tailwind CSS** | Styling | Utility-first CSS, consistent design system, no context switching |
| **shadcn/ui** | Component library | Accessible, composable components built on Tailwind + Radix UI |
| **TanStack Query** | Server state management | Caching, refetching, loading/error states for API data |
| **Auth.js** | Authentication | JWT sessions, provider support, App Router integration |
| **Vitest** | Unit/component testing | Fast, native TypeScript, Jest-compatible API |
| **@testing-library/react** | Component test utilities | Accessible queries, user-centric testing |
| **@testing-library/user-event** | Interaction simulation | Realistic browser event simulation |
| **Playwright** | E2E testing | Cross-browser headless testing, reliable selectors |
| **ESLint** | Linting | Code quality and consistency |
| **Prettier** | Formatting | Consistent code formatting |
| **lint-staged** + **Husky** | Pre-commit hooks | Run linting and formatting on staged files before commit |
| **npm audit** | Dependency scanning | Detect known vulnerabilities in npm packages |

**Note on pre-commit hooks in the monorepo**: Husky runs at the repo root for JavaScript (lint-staged, Prettier, ESLint). Python pre-commit hooks (`detect-secrets`, `pip-audit`, linting) run via `pre-commit` in `services/backend/` per [Python Project Standards](./python-standards.md). Both coexist — Husky's `.husky/pre-commit` can call `pre-commit run --config services/backend/.pre-commit-config.yaml` for Python files.

### Backend

Backend tooling follows [Python Project Standards](./python-standards.md) and [Database Standards](./database-standards.md). Key tools specific to the web application context:

| Tool | Purpose | Rationale |
|------|---------|-----------|
| **FastAPI** | Web framework | Async, automatic OpenAPI schema, Pydantic integration |
| **Pydantic** | Validation/serialization | Request/response models, settings management |
| **psycopg 3** | Database driver | Async PostgreSQL access, connection pooling |
| **uvicorn** | ASGI server | Production-grade async server for FastAPI |
| **pytest-asyncio** | Async test support | Run async test functions with pytest |

### Build System

| Tool | Purpose | Rationale |
|------|---------|-----------|
| **Turborepo** | Monorepo build orchestration | Task caching, dependency-aware builds, parallel execution |
| **Make** | Python-side task runner | Consistent with Python standards, simple and universal |

---

## Monorepo Structure

### Directory Layout

```
project-root/
├── package.json                # npm workspace root
├── turbo.json                  # Turborepo pipeline config
├── Makefile                    # Top-level commands (start all, migrate, generate client)
├── example.env                # Environment variable template
├── .nvmrc                      # Pin Node.js version (e.g., "22")
├── apps/
│   └── web/                    # Next.js application
│       ├── package.json
│       ├── next.config.ts
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       ├── src/
│       │   ├── app/            # App Router pages and layouts
│       │   ├── components/     # App-specific components
│       │   └── lib/            # App-specific utilities
│       └── tests/
│           ├── unit/           # Vitest component/unit tests
│           └── e2e/            # Playwright tests
├── packages/
│   ├── ui/                     # Shared UI components (shadcn/ui)
│   │   ├── package.json
│   │   └── src/
│   │       └── components/     # shadcn/ui components
│   ├── api-client/             # Auto-generated OpenAPI TypeScript client
│   │   ├── package.json
│   │   └── src/                # Generated code — do not edit manually
│   └── shared/                 # Shared TypeScript types and utilities
│       ├── package.json
│       └── src/
└── services/
    └── backend/                # FastAPI application
        ├── pyproject.toml
        ├── Makefile
        ├── src/
        │   └── app/            # Replace "app" with your project name
        │       ├── main.py     # FastAPI app entry point
        │       ├── routers/    # Route handlers
        │       ├── models/     # Pydantic models
        │       ├── queries/    # SQL query functions
        │       └── auth/       # Auth logic (JWT, password hashing)
        ├── tests/
        └── db/
            └── migrations/     # golang-migrate SQL files
```

### Workspace Configuration

Root `package.json`:

```json
{
  "private": true,
  "workspaces": [
    "apps/*",
    "packages/*"
  ],
  "devDependencies": {
    "turbo": "^2"
  }
}
```

### Turborepo Pipeline

`turbo.json`:

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "dist/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "lint": {
      "dependsOn": ["^build"]
    },
    "test": {
      "dependsOn": ["^build"]
    },
    "generate": {
      "cache": false
    }
  }
}
```

**Key concepts**:
- `"dependsOn": ["^build"]` — build dependencies (packages) before the app that uses them
- `"outputs"` — what Turborepo caches; subsequent runs skip work if inputs haven't changed
- `"persistent": true` — for long-running dev servers that don't exit

---

## Frontend Standards

### Next.js App Router

#### File-Based Routing

```
app/
├── layout.tsx              # Root layout (html, body, providers)
├── page.tsx                # Home page
├── (auth)/                 # Route group — no URL segment
│   ├── login/
│   │   └── page.tsx
│   └── register/
│       └── page.tsx
├── dashboard/
│   ├── layout.tsx          # Dashboard layout (sidebar, nav)
│   ├── page.tsx            # /dashboard
│   └── settings/
│       └── page.tsx        # /dashboard/settings
└── api/                    # API routes (for Auth.js, webhooks)
    └── auth/
        └── [...nextauth]/
            └── route.ts
```

#### Server vs Client Components

**Default to Server Components.** Only add `"use client"` when the component needs:
- Event handlers (`onClick`, `onChange`, `onSubmit`)
- React hooks (`useState`, `useEffect`, `useContext`)
- Browser-only APIs (`window`, `localStorage`, `IntersectionObserver`)
- TanStack Query hooks (`useQuery`, `useMutation`)

```typescript
// Server Component (default) — runs on the server, no JS shipped to client
export default async function ProductsPage() {
  const products = await fetchProducts()  // server-side fetch
  return <ProductList products={products} />
}
```

```typescript
// Client Component — interactive, runs in browser
"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@project/api-client"

export function ProductSearch() {
  const [query, setQuery] = useState("")
  const { data, isLoading } = useQuery({
    queryKey: ["products", "search", query],
    queryFn: () => apiClient.searchProducts({ query }),
    enabled: query.length > 2,
  })
  // ...
}
```

### TypeScript Configuration

`tsconfig.json` in `apps/web/`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "ES2022"],
    "module": "esnext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "jsx": "preserve",
    "incremental": true,
    "paths": {
      "@/*": ["./src/*"],
      "@project/ui": ["../../packages/ui/src"],
      "@project/api-client": ["../../packages/api-client/src"],
      "@project/shared": ["../../packages/shared/src"]
    }
  }
}
```

**Key strictness settings**:
- `"strict": true` — enables all strict type checks
- `"noUncheckedIndexedAccess": true` — array/object index access returns `T | undefined`, catching common runtime errors

### Styling with Tailwind CSS

#### Configuration

Tailwind config in `apps/web/tailwind.config.ts`:

```typescript
import type { Config } from "tailwindcss"
import tailwindcssAnimate from "tailwindcss-animate"

const config: Config = {
  darkMode: "class",
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",  // shared UI package
  ],
  theme: {
    extend: {
      // Project-specific design tokens
      colors: {
        brand: {
          50: "var(--brand-50)",
          // ...
          900: "var(--brand-900)",
        },
      },
    },
  },
  plugins: [tailwindcssAnimate],  // required by shadcn/ui
}

export default config
```

#### Conventions

- **Utility classes in JSX** — use Tailwind classes directly on elements
- **`cn()` helper for conditional classes** — shadcn/ui provides this via `clsx` + `tailwind-merge`
- **CSS variables for design tokens** — define brand colors, spacing scales as CSS variables so Tailwind and shadcn/ui themes stay in sync
- **No custom CSS files** unless Tailwind utilities genuinely can't express the style (rare)

### shadcn/ui Components

shadcn/ui is not installed as an npm package — it's a collection of components you copy into your project and own:

```bash
# Add a component to the shared UI package
npx shadcn@latest add button -c packages/ui
```

Components live in `packages/ui/src/components/` and are imported across the monorepo:

```typescript
import { Button } from "@project/ui/components/button"
import { Dialog, DialogContent, DialogTrigger } from "@project/ui/components/dialog"
```

**Conventions**:
- Keep shadcn/ui components in `packages/ui/` so they're shared across apps
- Customize via the theming system (CSS variables), not by editing component internals
- When you need to extend a component, wrap it — don't fork the shadcn source

---

## API Integration

### OpenAPI Client Generation

FastAPI automatically generates an OpenAPI schema at `/openapi.json`. Auto-generate a TypeScript client from it so frontend types always match backend models.

#### Generation Script

In root `Makefile`:

```makefile
.PHONY: generate-api-client
generate-api-client:  ## Generate TypeScript client from FastAPI OpenAPI schema
	cd services/backend && uv run python -c \
		"from app.main import app; import json; print(json.dumps(app.openapi()))" \
		> ../../packages/api-client/openapi.json
	cd packages/api-client && npx @hey-api/openapi-ts \
		-i openapi.json \
		-o src \
		-c @hey-api/client-fetch
```

**How this works**:
1. Extract the OpenAPI schema from FastAPI without running the server
2. Generate TypeScript types and a fetch-based client from the schema
3. The generated `packages/api-client/src/` contains typed request/response models and service methods

#### Using the Generated Client

```typescript
import { ProductsService } from "@project/api-client"

// Fully typed — parameter and return types match FastAPI's Pydantic models
const products = await ProductsService.listProducts({ isActive: true })
const product = await ProductsService.createProduct({
  requestBody: { name: "Widget", sku: "WDG-001", priceCents: 1999 },
})
```

#### Keeping the Client in Sync

- Run `make generate-api-client` after changing FastAPI routes or Pydantic models
- Add the generation step to CI — fail the build if generated code is out of date:

```yaml
# In GitHub Actions
- name: Check API client is up to date
  run: |
    make generate-api-client
    git diff --exit-code packages/api-client/src/
```

### TanStack Query Integration

Wrap the generated client with TanStack Query for caching and state management:

```typescript
// lib/queries/products.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ProductsService } from "@project/api-client"

export function useProducts(isActive?: boolean) {
  return useQuery({
    queryKey: ["products", { isActive }],
    queryFn: () => ProductsService.listProducts({ isActive }),
  })
}

export function useCreateProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ProductsService.createProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
    },
  })
}
```

**Conventions**:
- One file per API domain (`products.ts`, `users.ts`, `invoices.ts`)
- Export custom hooks, not raw query configs
- Query keys follow the pattern `[domain, params]`
- Mutations invalidate related queries on success

### Server-Side Data Fetching

For initial page loads, fetch data in Server Components directly — no TanStack Query needed:

```typescript
// app/products/page.tsx (Server Component)
import { ProductsService } from "@project/api-client"

export default async function ProductsPage() {
  const products = await ProductsService.listProducts({ isActive: true })
  return <ProductList products={products} />
}
```

Server Components call FastAPI server-to-server using `BACKEND_URL` (not the public `NEXT_PUBLIC_API_URL`), skipping CORS. Configure the client's base URL for server-side usage in your `lib/api-config.ts`.

Use TanStack Query in Client Components for interactive features (search, pagination, mutations, optimistic updates).

---

## Authentication

### Architecture

Authentication uses Auth.js (formerly NextAuth.js) on the frontend with JWT tokens issued by FastAPI:

```
Browser → Auth.js (Next.js) → /auth/login (FastAPI) → JWT
                             → /auth/refresh (FastAPI) → New JWT
```

### FastAPI Auth Endpoints

```python
# services/backend/src/app/routers/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    # Verify credentials against database
    # Return JWT access + refresh tokens
    ...


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest):
    # Validate refresh token, issue new access token
    ...
```

### Auth.js Configuration

```typescript
// lib/auth.ts
import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        const res = await fetch(`${process.env.BACKEND_URL}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(credentials),
        })
        if (!res.ok) return null
        const tokens = await res.json()
        return { id: tokens.user_id, ...tokens }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.access_token
        token.refreshToken = user.refresh_token
      }
      return token
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string
      return session
    },
  },
  session: { strategy: "jwt" },
})
```

```typescript
// app/api/auth/[...nextauth]/route.ts
import { handlers } from "@/lib/auth"

export const { GET, POST } = handlers
```

### Token Refresh

The `jwt` callback runs on every request. Check token expiry and refresh proactively:

```typescript
// In the jwt callback (lib/auth.ts)
async jwt({ token, user }) {
  if (user) {
    token.accessToken = user.access_token
    token.refreshToken = user.refresh_token
    token.expiresAt = Date.now() + user.expires_in * 1000
  }

  // Return existing token if not expired (with 60s buffer)
  if (Date.now() < (token.expiresAt as number) - 60_000) {
    return token
  }

  // Refresh the access token
  const res = await fetch(`${process.env.BACKEND_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: token.refreshToken }),
  })
  if (!res.ok) {
    // Refresh failed — force re-login
    return { ...token, error: "RefreshTokenError" }
  }
  const refreshed = await res.json()
  token.accessToken = refreshed.access_token
  token.refreshToken = refreshed.refresh_token
  token.expiresAt = Date.now() + refreshed.expires_in * 1000
  return token
},
```

Handle `RefreshTokenError` in your session callback or middleware to redirect to the login page. See the [Auth.js JWT rotation docs](https://authjs.dev/guides/refresh-token-rotation) for additional patterns.

### Passing Tokens to API Calls

Configure the generated API client to include the JWT token:

```typescript
// lib/api-config.ts
import { createClient } from "@hey-api/client-fetch"
import { auth } from "@/lib/auth"

export const apiClient = createClient({
  baseUrl: process.env.NEXT_PUBLIC_API_URL!,
})

apiClient.interceptors.request.use(async (request) => {
  const session = await auth()
  if (session?.accessToken) {
    request.headers.set("Authorization", `Bearer ${session.accessToken}`)
  }
  return request
})
```

---

## State Management

### Decision Framework

| State type | Tool | Examples |
|-----------|------|---------|
| Server data (API responses) | **TanStack Query** | Product lists, user profiles, dashboard data |
| URL state (shareable, bookmarkable) | **`useSearchParams`** or **nuqs** | Search queries, filters, pagination, sort order |
| Client UI state (local) | **React state** (`useState`) | Form inputs, toggle visibility, accordion state |
| Client UI state (shared) | **Zustand** | Shopping cart, multi-step wizard, notification queue |
| Global low-frequency state | **React Context** | Theme, locale, auth session |

### When to Add Zustand

Don't add Zustand preemptively. Use it when you have client-side state that:
- Is needed by multiple unrelated components
- Cannot be derived from server state (TanStack Query)
- Changes frequently enough that React Context would cause excessive re-renders

```typescript
// stores/cart.ts — only create when you actually need it
import { create } from "zustand"
import { persist } from "zustand/middleware"

interface CartStore {
  items: CartItem[]
  addItem: (item: CartItem) => void
  removeItem: (id: string) => void
  clear: () => void
}

export const useCartStore = create<CartStore>()(
  persist(
    (set) => ({
      items: [],
      addItem: (item) =>
        set((state) => ({ items: [...state.items, item] })),
      removeItem: (id) =>
        set((state) => ({ items: state.items.filter((i) => i.id !== id) })),
      clear: () => set({ items: [] }),
    }),
    { name: "cart-storage" },  // persists to localStorage
  ),
)
```

---

## Testing

### Testing Strategy

| Layer | Tool | What to test | Speed |
|-------|------|-------------|-------|
| Components/units | **Vitest** + Testing Library | Rendering, interactions, hooks, utilities | Fast (seconds) |
| API endpoints | **pytest** + httpx | Request/response, validation, auth, error cases | Fast (seconds) |
| End-to-end | **Playwright** | Full user flows across frontend and backend | Slow (minutes) |

### Vitest Configuration

`apps/web/vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config"
import react from "@vitejs/plugin-react"
import path from "path"

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      thresholds: { statements: 80, branches: 80, functions: 80, lines: 80 },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
```

#### Component Test Example

```typescript
// tests/unit/product-card.test.tsx
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ProductCard } from "@/components/product-card"

describe("ProductCard", () => {
  it("displays product name and price", () => {
    render(<ProductCard name="Widget" priceCents={1999} />)
    expect(screen.getByText("Widget")).toBeInTheDocument()
    expect(screen.getByText("$19.99")).toBeInTheDocument()
  })

  it("calls onAddToCart when button is clicked", async () => {
    const onAdd = vi.fn()
    render(<ProductCard name="Widget" priceCents={1999} onAddToCart={onAdd} />)
    await userEvent.click(screen.getByRole("button", { name: /add to cart/i }))
    expect(onAdd).toHaveBeenCalledOnce()
  })
})
```

### Playwright Configuration

`apps/web/playwright.config.ts`:

```typescript
import { defineConfig, devices } from "@playwright/test"

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
  ],
  webServer: [
    {
      command: "cd ../../services/backend && make dev",
      url: "http://localhost:8000/docs",
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
    },
  ],
})
```

#### E2E Test Example

```typescript
// tests/e2e/login.spec.ts
import { test, expect } from "@playwright/test"

test("user can log in and see dashboard", async ({ page }) => {
  await page.goto("/login")
  await page.getByLabel("Email").fill("user@example.com")
  await page.getByLabel("Password").fill("password123")
  await page.getByRole("button", { name: /sign in/i }).click()

  await expect(page).toHaveURL("/dashboard")
  await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible()
})
```

### Backend Testing

Follow [Python Project Standards](./python-standards.md) for pytest configuration. FastAPI-specific patterns:

```python
# tests/test_products.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient):
    response = await client.get("/products")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### Coverage Targets

| Layer | Target |
|-------|--------|
| Frontend components (Vitest) | 80%+ |
| Backend API (pytest) | 80%+ |
| E2E (Playwright) | Cover all critical user flows |

---

## Development Workflow

### Local Development Setup

```bash
# 1. Clone and install
git clone <repo-url> && cd <project>
npm install                          # Install JS dependencies (all workspaces)
cd services/backend && make setup    # Install Python dependencies

# 2. Start infrastructure
docker compose up -d                 # PostgreSQL

# 3. Run migrations
make migrate-up                      # Apply all database migrations

# 4. Generate API client
make generate-api-client             # Generate TypeScript client from FastAPI schema

# 5. Start development servers
turbo dev                            # Next.js dev server (with hot reload)
cd services/backend && make dev      # FastAPI dev server (uvicorn --reload)
```

### Environment Variables

`example.env` at the project root:

```bash
# Backend
DATABASE_URL=postgresql://main:localpass@localhost:5432/myapp_dev
SECRET_KEY=local-dev-secret-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=["http://localhost:3000"]

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=local-dev-secret-change-in-production

# Backend internal URL (server-to-server, used by Next.js SSR)
BACKEND_URL=http://localhost:8000
```

**Note**: `NEXT_PUBLIC_*` variables are exposed to the browser. All other variables are server-only. Never put secrets in `NEXT_PUBLIC_*` variables.

### CORS Configuration

FastAPI middleware for local development and production:

```python
# services/backend/src/app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.open()
    yield
    await pool.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # ["http://localhost:3000"] in dev
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

The `lifespan` handler manages the psycopg `AsyncConnectionPool` — see [Database Standards](./database-standards.md) for pool configuration details.

---

## CI/CD

### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "npm"
      - run: npm ci
      - run: npx turbo lint
      - run: npx turbo test
      - run: npx turbo build

  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: main
          POSTGRES_PASSWORD: testpass
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - working-directory: services/backend
        env:
          DATABASE_URL: postgresql://main:testpass@localhost:5432/test_db
        run: |
          make setup
          make lint
          make test

  api-client-check:
    runs-on: ubuntu-latest
    needs: [backend]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "npm"
      - uses: astral-sh/setup-uv@v4
      - run: npm ci
      - name: Install backend Python dependencies
        run: cd services/backend && uv sync
      - run: make generate-api-client
      - name: Verify API client is up to date
        run: git diff --exit-code packages/api-client/src/

  e2e:
    runs-on: ubuntu-latest
    needs: [frontend, backend]
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: main
          POSTGRES_PASSWORD: testpass
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "npm"
      - uses: astral-sh/setup-uv@v4
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - run: npx turbo build
      - working-directory: services/backend
        env:
          DATABASE_URL: postgresql://main:testpass@localhost:5432/test_db
        run: |
          make setup
          make migrate-up
      - name: Run Playwright tests
        env:
          DATABASE_URL: postgresql://main:testpass@localhost:5432/test_db
        run: npx playwright test --project=chromium
```

---

## Docker

### Frontend Dockerfile

```dockerfile
# apps/web/Dockerfile
FROM node:22-slim AS base

FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/
COPY packages/ui/package.json ./packages/ui/
COPY packages/api-client/package.json ./packages/api-client/
COPY packages/shared/package.json ./packages/shared/
RUN npm ci

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npx turbo build --filter=web

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public
USER nextjs
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
```

### Docker Compose (Full Stack)

```yaml
# docker-compose.yml
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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U main -d myapp_dev"]
      interval: 5s
      timeout: 3s
      retries: 5

  backend:
    build:
      context: ./services/backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://main:localpass@db:5432/myapp_dev
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
      interval: 5s
      timeout: 3s
      retries: 5

  web:
    build:
      context: .
      dockerfile: apps/web/Dockerfile
    ports:
      - "3000:3000"
    environment:
      BACKEND_URL: http://backend:8000
      # Note: NEXT_PUBLIC_* vars are baked in at build time, not read at runtime.
      # Pass them as build args in the Dockerfile instead.
    depends_on:
      backend:
        condition: service_healthy

volumes:
  pgdata:
```

---

## Anti-Patterns

### Frontend

**CSS-in-JS libraries** — Use Tailwind utility classes. CSS-in-JS adds runtime cost and conflicts with Server Components.

**Barrel exports (`index.ts` re-exports)** — These defeat tree-shaking and slow down builds. Import directly from the source file.

**`useEffect` for data fetching** — Use TanStack Query or Server Components. Raw `useEffect` + `fetch` loses caching, race condition handling, and loading states.

**Prop drilling through many layers** — If data passes through 3+ components untouched, lift it to TanStack Query (server state) or Zustand (client state).

### Integration

**Manual API types** — Never hand-write TypeScript types that mirror Pydantic models. Auto-generate the client. Manual types drift from the backend.

**Wrapping server data fetches in Client Components** — If the data doesn't need interactivity, fetch it in a Server Component. Don't add `"use client"` just to call `useEffect` + `fetch` when a Server Component can fetch the same data with zero client JavaScript.

### Backend

**Returning database rows directly** — Always serialize through Pydantic response models. This controls what's exposed and decouples the API shape from the database schema.

**Storing JWT secrets in code** — Use environment variables. See [Credential Management](./database-standards.md#credential-management).

---

## References

### Tools
- [Next.js](https://nextjs.org/) - React framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS
- [shadcn/ui](https://ui.shadcn.com/) - Component collection
- [TanStack Query](https://tanstack.com/query) - Server state management
- [Auth.js](https://authjs.dev/) - Authentication
- [Vitest](https://vitest.dev/) - Test runner
- [Playwright](https://playwright.dev/) - E2E testing
- [Turborepo](https://turbo.build/) - Monorepo build system
- [@hey-api/openapi-ts](https://heyapi.dev/) - OpenAPI client generator
- [Zustand](https://zustand-demo.pmnd.rs/) - Client state management

### Related Standards
- [Python Project Standards](./python-standards.md) - Backend tooling and conventions
- [Database Standards](./database-standards.md) - PostgreSQL schema design and data access
- [Git Branching Strategy](../process/git-branching-strategy.md) - Branch management
- [Feature Development Workflow](../process/feature-development-workflow.md) - Development process

---

## Status

**Draft** - This standard is in active development and subject to revision based on practical experience.
