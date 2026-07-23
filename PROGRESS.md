# PROGRESS.md

Tracks completion of the project plan from the original chat. Update as steps are completed.

Legend: ✅ done · ⏳ in progress · ⬜ not started · ⏭ skipped/deferred

---

## Phase 1: Foundations & Local Setup

- ✅ **1.** Set up monorepo (`apps/`, `packages/`, `infra/cdk`) with `pnpm-workspace.yaml` + root `package.json` (private, workspaces). Git initialized.
- ✅ **2.** Install Python 3.12+, Node LTS (nvm-windows), AWS CLI. Configure `aws configure` with `budgeting-app-dev` IAM user.
- ⬜ **3.** AWS budget alert ($10–20/month, alerts at 50/80/100%). **Do this before any AWS deploy in Phase 3.**
- ✅ **4.** FastAPI project in `apps/api` with `uv`. Hello-world `/health` endpoint running under `uvicorn app.main:app --reload`. Mangum handler defined (unused locally).
- ✅ **5.** Postgres 16 running locally via Docker Compose at `localhost:5432`. Credentials: `budgeting/budgeting/budgeting_dev`. `/health/db` endpoint confirms connection.

## Phase 2: Data Model & Core API

- ✅ **6.** Data model sketched: `User`, `Account`, `Category`, `Transaction`, `Budget` + enums. Money as `Numeric(12,2)`, dates as `Date`, UUIDs as PKs. Composite index `(user_id, occurred_on)` on transactions.
- ✅ **7.** SQLAlchemy 2.x models with `Mapped[...]` / `mapped_column(...)`. All under `apps/api/app/models/`. Cascade deletes from user.
- ✅ **8.** Alembic configured (`alembic init alembic`, `env.py` reads `DATABASE_URL` from settings, imports `app.models`). Initial migration generated and applied. `alembic_version` table present.
- ✅ **9a.** Pydantic schemas for all entities under `apps/api/app/schemas/`. Three-schema pattern (`Create`/`Update`/`Read`). `APISchema` base with `from_attributes=True`. `Page[T]` and `PaginationParams` in `common.py` (the latter as a `BaseModel` query model, consumed via `Annotated[PaginationParams, Query()]` — see DECISION 015). `email-validator` installed. Package re-exports via `schemas/__init__.py`. mypy clean (added `pydantic.mypy` plugin to fix a `BaseSettings` call-arg false positive).
- ✅ **9b.** CRUD routers under `apps/api/app/routers/` for accounts, categories, transactions, budgets. Five verbs each, `Page[T]` list endpoints, placeholder `get_current_user_id` dependency (real Cognito one comes in Phase 4). Ownership enforced via the generic `get_for_user` helper in `app/crud.py` + the `UserOwned` mixin (see DECISION 017); owned FKs (`account_id`/`category_id`/`parent_id`) validated on create/update. All four wired into `main.py` via `routers/__init__.py` re-exports.
- ✅ **10.** Seed script (`apps/api/scripts/seed.py`) using `Faker` to populate local DB with realistic test data. Writes through the ORM directly (not the HTTP API), wipes-and-reseeds the dev user (matching `DEV_USER_EMAIL`) via cascade, stamps `user_id` on every owned row, uses `Decimal` money with signed amounts (DECISION 010). Run: `uv run python scripts/seed.py`.
- ⏳ **11.** pytest setup with `TestClient`. Test patterns: one happy path per endpoint, one validation failure, one cross-tenant access attempt.

## Phase 3: AWS Infrastructure

- ⬜ **12.** Set up AWS CDK with Python in `infra/cdk/`. `cdk bootstrap` for account/region.
- ⬜ **13.** CDK stack: Aurora Serverless v2 Postgres (or `db.t4g.micro` for cheaper dev) + Lambda + API Gateway + IAM.
- ⬜ **14.** Package FastAPI for Lambda. Recommended: Lambda container image (FastAPI deps are heavy). Mangum already wired into `main.py`.
- ⬜ **15.** First successful `cdk deploy`. Debug cold starts, DB connectivity, IAM. **This step teaches the most.**
- ⬜ **16.** Add RDS Proxy in front of the DB. Update Lambda env to connect through proxy.
- ⬜ **17.** Run Alembic migrations against AWS Postgres. Decide on migration strategy (separate Lambda vs. CI step).

## Phase 4: Authentication

- ⬜ **18.** Cognito User Pool in CDK stack with email signup. App client created.
- ⬜ **19.** API Gateway validates Cognito JWTs. FastAPI `get_current_user` dependency extracts claims.
- ⬜ **20.** Add `user_id` foreign key to all models (already done in Phase 2) and scope every query to current user. Security-critical.

## Phase 5: Web Frontend

- ⬜ **21.** Next.js + TS + Tailwind + App Router in `apps/web`.
- ⬜ **22.** TypeScript types in `packages/shared/` generated from FastAPI's `/openapi.json` via `openapi-typescript`. Zod schemas mirrored.
- ⬜ **23.** TanStack Query + API client wrapper that attaches Cognito JWT. `aws-amplify/auth` for Cognito client.
- ⬜ **24.** Auth flows: signup, login, logout, password reset.
- ⬜ **25.** Core screens: dashboard, transactions list with filters, categories, budget setup, budget vs. actual.
- ⬜ **25b.** Analytics endpoints in `apps/api/app/services/analytics.py` using **pandas** (monthly spending, rolling averages, budget pacing).
- ⬜ **26.** Deploy web to Vercel.

## Phase 6: Bank Connectivity (Optional)

- ⬜ **27.** Plaid developer account + sandbox credentials.
- ⬜ **28.** Plaid Link in web app for connecting sandbox bank accounts.
- ⬜ **29.** Backend: token exchange, encrypted access token storage (KMS/Secrets Manager), transaction fetch. **pandas for dedup against existing rows.**
- ⬜ **30.** Scheduled EventBridge rule → Lambda for daily sync. Plaid webhooks for real-time updates.

## Phase 7: Mobile

- ⬜ **31.** Expo project in `apps/mobile` with TypeScript. Verify via Expo Go.
- ⬜ **32.** Reuse `packages/shared`. `expo-secure-store` for token storage.
- ⬜ **33.** Mobile-specific screens using React Native primitives (don't share UI components across web/mobile).
- ⬜ **34.** Test iOS + Android.

## Phase 8: Polish & Production Readiness

- ⬜ **35.** CloudWatch alarms (Lambda errors, API Gateway 5xx, DB CPU). SNS email topic.
- ⬜ **36.** Structured logging + request-ID middleware in FastAPI. Logs to CloudWatch.
- ⬜ **37.** GitHub Actions CI: tests on PR, deploy on merge to main. AWS OIDC, not long-lived keys.
- ⬜ **38.** README with architecture, local setup, deploy instructions.

---

## Notes for Future Sessions

- The `data-analysis` and `analytics` features are NOT in CRUD routers — they go in `apps/api/app/services/analytics.py` and have their own router file. Keep the boundaries clean.
- The first AWS deploy (step 15) will likely take a full session to debug. Plan accordingly.
- The pandas/Lambda cold-start concern: only import pandas in modules that actually use it. Don't put `import pandas` at the top of `main.py`.
- WSL2 may be worth setting up before Phase 3 — Lambda container packaging is smoother on Linux.

## Known Model Bugs (found during 9a schema review) — ✅ ALL RESOLVED

These were pre-existing issues in the SQLAlchemy models from step 7, surfaced while writing the Pydantic schemas. All three are now fixed in the models (verified during the 9b router work).

1. ✅ **`transactions.category_id` mismatch.** Now `nullable=True` + `ON DELETE SET NULL` ([models/transaction.py](apps/api/app/models/transaction.py)) — deleting a category orphans its transactions rather than deleting them, matching CLAUDE principle 5 and the `TransactionCreate`/`Read` schemas.
2. ✅ **`Account.transactions` wrong `back_populates`.** Now `back_populates="account"` ([models/account.py](apps/api/app/models/account.py)) — the mapper pairs correctly with `Transaction.account`.
3. ✅ **`users.email` under-specified.** Now `String(255)` + `unique=True` ([models/user.py](apps/api/app/models/user.py)).
