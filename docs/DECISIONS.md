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

**Connection pooling concern:** Lambda + RDS without RDS Proxy causes connection exhaustion. ~~RDS Proxy is mandatory in prod (Phase 3, step 16).~~ Superseded by DECISION 018: the proxy is deployed once for learning, then removed.

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

---

## 018 — RDS Proxy: deploy once to learn it, then remove it

**Decision:** Step 16 deploys RDS Proxy in front of Aurora a single time. The goal is to learn the setup: the proxy construct, its Secrets Manager or IAM auth, pointing the Lambda's `DATABASE_URL` at the proxy endpoint, and checking connections in CloudWatch. After that session the proxy is removed from the stack and redeployed without it. The steady-state dev stack has no proxy.

**Why:**

- **Cost floor.** For Aurora Serverless v2, RDS Proxy bills per ACU-hour of the database with an **8-ACU minimum**, about $0.015/ACU-hour in the US. That works out to roughly **$87/month** even when the database is scaled to 0 ACU. The proxy has no pause, so it would be most of the bill for a learning project.
- **Auto-pause.** The proxy holds a connection open to the cluster, so Aurora **won't auto-pause** while a proxy is attached (confirmed in the Aurora auto-pause docs). It sits at 0.5 ACU or more instead.
- **The problem doesn't exist at this scale.** Connection exhaustion needs many concurrent Lambda environments. Two settings bound total connections without a proxy:
  - `pool_size=1, max_overflow=0` on the engine under Lambda (each environment serves one request at a time).
  - **Reserved concurrency** on the Lambda (e.g. 10), which caps environments and therefore connections. *Update:* this account's total Lambda concurrency limit is **10**, and AWS won't let you reserve all of it. So `reserved_concurrent_executions` is commented out in `api_stack.py`, and the account limit itself is the cap. If the limit is ever raised (via Service Quotas), turn reserved concurrency back on before relying on the higher limit.
- **The learning still happens.** The proxy is billed per second with a 10-minute minimum, so one deploy-and-destroy session costs cents.

**How to apply:**

- The proxy code lives on the unmerged branch `lesson-8-rds-proxy`, never on `main`. Redeploying it means switching to that branch and running `cdk deploy --all`.
- After the session, confirm it's gone with `aws rds describe-db-proxies`. That command must return an empty list. Run it with a profile that has `rds:Describe*`. `budgeting-deploy` doesn't: it can only assume the CDK bootstrap roles, so the command returns `AccessDenied`. The budget alert would only catch a forgotten proxy weeks later.
- The default Lambda wiring connects **directly to the Aurora cluster endpoint**. `ApiStack` must not require a proxy to exist.

**Revisit when:** real traffic arrives, Lambda concurrency needs to go well above the reserved cap, or this becomes a production deployment rather than a learning account.

**Alternative considered:** keeping the proxy permanently, which matches the original DECISION 003 note. Rejected on cost: roughly $87/month for protection against a load this project doesn't have.

**Outcome (2026-11-24):** deployed once with end-to-end IAM auth, load-tested, and destroyed. The measurements back the decision. Under a 200-request burst, Lambda's concurrency limit of 10 throttled 152 requests (503s) before any of them reached the database. The proxy never multiplexed: client and database connections both peaked at 7. At this scale the proxy adds cost and blocks auto-pause, and the actual limit is somewhere it can't help. Details are in PROGRESS step 16.

---

## 019 — Dev `DbStack`: isolated VPC, Aurora that can pause to zero, IAM auth

**Decision:** The dev database stack (`infra/cdk/stacks/db_stack.py`) is configured for minimum idle cost:

- A **VPC with `nat_gateways=0`** and two `PRIVATE_ISOLATED` subnets (`/24`). There is no internet route in or out.
- **Aurora Serverless v2 with `min_capacity=0`, `max_capacity=1`**. At 0 the instance pauses after 300 s idle (requires Postgres 16.3+). This replaces the earlier plan of a 0.5 ACU minimum.
- **`iam_authentication=True`**, so the Lambda will connect with a token signed by its own role. The master password is generated into Secrets Manager and is used only to create the IAM-auth user.
- **`storage_encrypted=True`.** CDK's default is `False` unless you pass a KMS key.
- **`RemovalPolicy.DESTROY`**, so `cdk destroy` leaves no final snapshot behind. **Dev only; never in prod.**

Each of these is pinned by a test in `infra/cdk/tests/unit/test_db_stack.py`.

**Why:**

- **NAT gateways cost about $32/month each, per AZ, even when idle.** CDK's default VPC creates one per AZ.
- **A 0.5 ACU floor costs about $43/month if it runs 24/7. Pausing at 0 costs $0 for compute while idle.** The tradeoff is roughly a 15 s resume on the first query after a pause, which is acceptable for dev.
- **The isolated subnets have no route to Secrets Manager**, so IAM auth is what makes them workable: the Lambda signs its token locally and never needs to fetch a password over the network. Without IAM auth, you'd need a NAT gateway or a Secrets Manager VPC endpoint (about $7/month per AZ).
- **A max of 1 ACU is the cost ceiling.** A runaway query can't scale the bill.

**Account plan:** AWS Free-plan accounts can only create Aurora with "express configuration". That mode has no VPC, a public endpoint, and no CloudFormation support. The account was upgraded to the Paid plan instead, to keep the standard VPC-based architecture (and Step 16's RDS Proxy, which needs a VPC). As a result, nothing caps spending once credits run out. The budget alert and `cdk destroy` are now the cost controls.

**Alternatives considered:**

- **`db.t4g.micro` provisioned RDS:** cheap, but it doesn't pause, and the project targets Aurora.
- **Aurora express configuration on the Free plan:** rejected for losing the VPC and needing hand-written custom resources.
- **Password auth plus a Secrets Manager VPC endpoint:** rejected because it adds about $7/month per AZ for no learning gain over IAM auth.

---

## 020 — Database bootstrap and migrations run inside CloudFormation

**Decision:** Two jobs run automatically during `cdk deploy`:

1. **Creating the app user, in `DbStack`.** The cluster has the Data API enabled (`enable_data_api=True`). A CDK `AwsCustomResource` calls `rds-data:ExecuteStatement` once, when the cluster is created. Using the master secret, it creates `budgeting_app`, grants it `rds_iam`, and grants `USAGE, CREATE ON SCHEMA public`. The SQL is idempotent (`IF NOT EXISTS`).
2. **Running migrations, in `ApiStack`.** A second Lambda built from the same image (`cmd=["app.migrate.handler"]`) runs `alembic upgrade head` as `budgeting_app` over IAM auth. CDK's `triggers.Trigger` invokes it on every deploy where the function changed. It runs **before** the API Lambda is updated (`execute_before`), so new code never runs against an old schema.

This settles Step 17's open question ("separate Lambda vs. CI step").

**Verified 2026-11-17:** deployed, both jobs ran, and `/accounts/` returned an empty page through API Gateway. Destroy leaves one orphan log group (the Trigger provider's `/aws/lambda/BudgetingApiDev-AWSCDKTriggerCustomResourceProvider...`), the same as the `CustomVpcRestrictDefaultSG` one.

**Why:**

- **Only CloudFormation can do this.** The database is in isolated subnets, so a laptop or CI can't reach it. The Lambda has no route to Secrets Manager, so it can't read the master password. The deploy role can't run SQL or invoke Lambdas. CloudFormation can be given exactly the permissions and network position each job needs.
- **The Data API is HTTPS, not a database connection,** so user creation needs no network path into the VPC. The master password never leaves AWS.
- **The migration Lambda reuses the API image.** The image is built and pushed once, and both Lambdas carry the same code and IAM-auth path (7a's `env.py` change).
- **A failed migration rolls back cleanly.** Postgres has transactional DDL and `env.py` runs inside one transaction, so a failed `upgrade` leaves the schema unchanged. The Trigger fails and `ApiStack` rolls back.

**Rules this creates:**

- **Migrations must be expand-only within a deploy.** A resource failing *after* a successful migration rolls back CloudFormation but not the database. Removing or renaming a column takes two deploys.
- **`budgeting_app` owns the tables**, so the API could run DDL. Splitting it into a migrator (owner) and an app user (DML only) is a later hardening step (Phase 8).
- **The Data API is an extra, IAM-gated way into the database.** Only the bootstrap custom resource holds `rds-data:ExecuteStatement` and read access to the master secret.

**Alternatives considered:**

- **A Secrets Manager VPC endpoint:** about $0.02/hour while deployed, and more networking to manage.
- **The master password in a Lambda env var:** readable by anyone who can view the function's configuration.
- **Alembic from CI:** CI can't reach isolated subnets without a bastion host.
- **`aws lambda invoke` by hand:** the deploy role can't invoke, and it's a step that's easy to forget.
