# DECISIONS.md

Architecture decisions and their reasoning. New decisions append as new entries with date and context.

---

## 001 — FastAPI over Flask

**Decision:** Use FastAPI for the backend.

**Why:**

- Native async support
- Auto-generated OpenAPI spec → drives TypeScript type generation for `packages/shared`
- Pydantic-first validation
- The modern Python web framework that internships will expect familiarity with
- Familiar feel coming from Flask, with significant DX upgrades

**Alternatives considered:** Flask (familiar but dated), Django (overkill for a JSON API).

---

## 002 — Lambda packaging via Mangum

**Decision:** Wrap the FastAPI ASGI app with Mangum for AWS Lambda. Same codebase runs under `uvicorn` locally and inside Lambda in prod.

**Why:**

- Lambda's execution model isn't a long-running server — Uvicorn can't run inside it as a server
- Mangum adapts API Gateway events to ASGI calls per-invocation
- Lets us keep one FastAPI app, two "drivers"

**Alternative considered:** AWS Lambda Web Adapter (runs Uvicorn inside Lambda via a sidecar extension). Cleaner code (no Mangum), but more setup, slightly worse cold starts. May revisit if cold starts matter more than simplicity.

---

## 003 — PostgreSQL on Aurora Serverless v2

**Decision:** Postgres for the database; Aurora Serverless v2 in prod, Docker Compose locally.

**Why:**

- Budgeting data is highly relational (accounts → transactions → categories → budgets)
- Aurora Serverless v2 scales down for cheap dev usage
- Postgres-flavored SQL is industry standard

**Alternative considered:** DynamoDB. Rejected — fighting NoSQL for relational data is painful, and Postgres' window functions and aggregations are exactly what budgeting analytics need.

**Connection pooling concern:** Lambda + RDS without RDS Proxy causes connection exhaustion. RDS Proxy is mandatory in prod (Phase 3, step 16).

---

## 004 — Cognito for authentication

**Decision:** AWS Cognito User Pool. JWTs validated by API Gateway before reaching Lambda.

**Why:**

- Integrates natively with API Gateway (no auth middleware needed in FastAPI)
- Works for both web and mobile (one identity provider)
- Keeps the stack inside AWS (educational goal: learn AWS)

**Alternatives considered:** Auth0, Clerk. Nicer DX, but defeats the "learn AWS" purpose.

---

## 005 — Monorepo with pnpm workspaces

**Decision:** Single repo with `apps/{api,web,mobile}`, `packages/shared`, `infra/cdk`.

**Why:**

- TypeScript types generated from the backend's OpenAPI spec live in `packages/shared` and are imported by both web and mobile → backend and frontend stay in sync automatically
- Single git history, single PR for a change spanning backend + frontend
- pnpm handles JS workspaces; Python projects (`api`, `cdk`) live alongside but manage their own venvs

**Why not Turborepo:** Adds complexity that pays off at much larger scale. Plain pnpm workspaces are enough.

---

## 006 — UUIDs as primary keys

**Decision:** UUID PKs everywhere, Postgres native type with `as_uuid=True`.

**Why:**

- Safe to expose in URLs without leaking row counts
- No conflicts if data ever needs to be merged across environments
- Generated client-side or server-side equally well
- Negligible performance cost at this scale

**Alternative considered:** Auto-increment integers. Faster, smaller, but worse for distributed scenarios.

---

## 007 — Money as `Numeric(12, 2)` and `Decimal`

**Decision:** Decimal types end-to-end. `Numeric(12, 2)` in Postgres, `Decimal` in Python, `Decimal` with `max_digits=12 decimal_places=2` in Pydantic.

**Why:** IEEE 754 floats can't represent `0.1 + 0.2` exactly. This is non-negotiable in financial software.

---

## 008 — `Date` not `Timestamp` for `transactions.occurred_on`

**Decision:** Store transaction date at day granularity, not as a timestamp.

**Why:**

- Banks report at day granularity
- Cross-institution timezone behavior is inconsistent
- Easier to reason about ("on Tuesday" doesn't depend on TZ)

The audit `created_at` is a separate, timestamped column.

---

## 009 — Three-schema pattern (`Create` / `Update` / `Read`)

**Decision:** Three Pydantic schemas per entity, with an optional shared `Base`.

**Why:**

- `Create` and `Update` have different shapes (PATCH semantics want everything optional)
- `Read` includes server-set fields (`id`, `created_at`) that don't belong in requests
- Letting clients set internal fields (`user_id`, `id`) is a security risk
- Clean OpenAPI output → clean generated TypeScript types

---

## 010 — Signed amounts on transactions

**Decision:** `transactions.amount` is a signed `Decimal`. Negative = outflow, positive = inflow.

**Why:** A separate `direction` column requires every aggregation query to multiply by `CASE WHEN direction='out' THEN -1 ELSE 1 END`. Signed decimals just sum correctly. Display layer can `abs()` and label.

---

## 011 — Pandas only in service layer

**Decision:** Use SQLAlchemy for CRUD. Use pandas only inside `app/services/analytics.py` and similar modules. Never import pandas in routers or models.

**Why:**

- Pandas adds ~500ms to Lambda cold starts — only pay the cost where it pays back
- Pandas DataFrames don't belong in API contracts — convert to dicts/Pydantic at the boundary
- "Memory explosion on 10M rows" is the #1 production pandas mistake — service-layer discipline keeps `WHERE` clauses at the SQL layer first
- The right tool for rolling averages, time-series, CSV ETL, and anomaly detection
- Internship-relevant skill to practice

**Alternative considered:** polars. Faster and cleaner API, but pandas is what internships test. Worth knowing polars exists.

---

## 012 — SQLAlchemy 2.0 style throughout

**Decision:** Use 2.x style (`Mapped[...]`, `mapped_column(...)`, `select(...)`, etc.) and `DeclarativeBase` as a class. Never `declarative_base()`-as-function.

**Why:**

- 2.0 is the current SQLAlchemy
- Type hints integrate with `mypy`
- The 1.x `Query` API is deprecated

**Gotcha:** `sessionmaker(autocommit=False)` is invalid in 2.0 — the parameter was removed. `autoflush=False` is still valid.

---

## 013 — Hatchling configuration

**Decision:** `apps/api/pyproject.toml` declares `[tool.hatch.build.targets.wheel] packages = ["app"]` because the package name (`budgeting-api`) doesn't match the import name (`app`).

**Alternative considered:** Set `[tool.uv] package = false` and drop the build backend entirely. Works, but a buildable package is cleaner for Lambda container packaging in Phase 3.

---

## 014 — Line endings normalized to LF in repo

**Decision:** `.gitattributes` forces LF for all text files in the repo, with explicit CRLF only for `.ps1` / `.bat` / `.cmd`.

**Why:**

- Cross-platform project: dev on Windows, run on Linux Lambdas
- CRLF in `.sh`, Dockerfiles, or `.env` files breaks Linux tools subtly
- Single source of truth that overrides per-machine `core.autocrlf` settings

---

## 015 — Pagination via `Annotated[PaginationParams, Query()]` query model

**Decision:** List endpoints paginate with a Pydantic **query model** — `PaginationParams(BaseModel)` holding `limit`/`offset` as `Field(...)` — consumed in routers as `pagination: Annotated[PaginationParams, Query()]` (FastAPI 0.115+). Lives in `app/schemas/common.py` next to `Page[T]`.

**Why:**

- Declaratively expresses "these are query params" on the model, with validation bounds (`ge`/`le`, `MAX_LIMIT = 200`) co-located on the fields
- `Field` is the correct tool here (model attribute validation), unlike the `Depends(plain class)` pattern which uses `Query()` defaults in `__init__`
- Reusable across every list endpoint without repeating `Query()` declarations

**Alternative considered:** `Depends(PaginationParams)` with a plain (non-Pydantic) class and `Query()` defaults in `__init__`. The older canonical pattern; works fine but doesn't express intent as cleanly and isn't a real Pydantic model. Chosen against in favor of the modern query-model approach.

**Gotcha:** Type the router param as `Annotated[PaginationParams, Query()]` directly — do **not** wrap it in `Depends`.

---

## 016 — Generated Alembic migrations excluded from ruff

**Decision:** `apps/api/pyproject.toml` sets `[tool.ruff] extend-exclude = ["alembic/versions"]`, so autogenerated migration files are not linted or formatted. Hand-written Alembic files (`env.py`, `alembic.ini`) remain linted.

**Why:**

- Migration files are machine-generated boilerplate, not hand-maintained code — Alembic's `--autogenerate` output uses single-line `op.create_table`/`create_index` calls (tripping `E501`) and old-style typing imports (`Union`, `typing.Sequence` → `UP007`/`UP035`)
- Holding generated files to the project style means re-cleaning them by hand after *every* `alembic revision`, which is toil and easy to forget
- Excluding the directory handles the whole category once, rather than chasing individual rule violations per migration

**Alternative considered:** Hand-clean each migration to pass ruff (the prior approach — the first migration had been manually re-wrapped). Rejected as unsustainable across many future migrations.

**Note:** This only excludes `alembic/versions/`. Migrations are still **reviewed before applying** (CLAUDE rule) — exclusion from the linter is not exclusion from human review.

---

## 017 — CRUD routers explicit, with a single shared ownership-scoped lookup helper

**Decision:** Write the four CRUD routers (accounts, categories, transactions, budgets) explicitly — each spelling out its own list/get/create/patch/delete handlers — rather than generating them from a shared base class or factory. Factor out exactly **one** piece of shared logic: "fetch a row by `id` **and** `user_id`, or raise 404." All other per-router code stays inline and visible.

**Why:**

- **Educational goal first.** Writing the FastAPI mechanics (routing, `Depends`, response models, status codes, pagination) four times cements them. A `CRUDRouter`-style abstraction hides exactly the mechanics this project exists to learn.
- **The ownership lookup is the one place duplication is a security liability, not just verbosity.** Forgetting the `user_id` filter is the "#1 security bug" (CLAUDE principle 2). Centralizing that single lookup means the dangerous filter is written and reviewed once, not copy-pasted into four routers where one could silently drift.
- **Explicit routers diverge cleanly.** Transactions need filters and FK-ownership checks accounts don't. Explicit handlers absorb those differences without fighting an abstraction; a generic factory would leak the moment one resource needs something special.

**Critical correctness note:** the helper filters by `id` AND `user_id` *in the same query* and raises 404 on no match. It does **not** fetch by `id` and then compare `row.user_id` in Python — that pulls another tenant's row into memory and invites a 403 that leaks the row's existence. Same query, both conditions, 404 on miss (never 403 — don't reveal that the row exists for another user).

**Typed ownership via a `UserOwned` mixin.** The helper is generic — `def get_owned_or_404[ModelT: UserOwned](...) -> ModelT` — so the return type tracks the concrete model passed in (pass `Account`, get an `Account` back). For that generic's bound to mean anything, the type it's bound to must actually declare the columns the helper filters on. So the four owned models inherit a `UserOwned` mixin (in `app/db.py`, alongside `Base`) that declares the shared `id` (UUID PK, `default=uuid.uuid4`) and `user_id` (FK → `users.id`, `ON DELETE CASCADE`) columns. mypy then knows every `ModelT` has `.id` and `.user_id` to filter on. `User` does **not** inherit the mixin — it has no `user_id`. Because the relocated columns are identical to the per-model declarations they replace, this needs **no migration** (verify with an autogenerate that yields an empty diff). Bonus: CLAUDE principle 2 ("every owned table has a `user_id`") becomes structurally enforced — an owned model can't be declared without it.

**Alternatives considered:**

- **Fully explicit (no shared helper).** Cleanest to read, but copies the security-critical `user_id` filter into four places — rejected for that reason alone.
- **Generic CRUD base class / router factory.** Least code, but hides the mechanics being learned and leaks under per-resource special cases (transaction filters). Deferred; revisit only if the routers prove genuinely uniform at scale.
