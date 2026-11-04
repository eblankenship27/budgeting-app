# PROGRESS.md

Tracks completion of the project plan from the original chat. Update as steps are completed.

Legend: ✅ done · ⏳ in progress · ⬜ not started · ⏭ skipped/deferred

---

## Phase 1: Foundations & Local Setup

- ✅ **1.** Set up monorepo (`apps/`, `packages/`, `infra/cdk`) with `pnpm-workspace.yaml` + root `package.json` (private, workspaces). Git initialized.
- ✅ **2.** Install Python 3.12+, Node LTS (nvm-windows), AWS CLI. Configure `aws configure` with `budget-app-dev` IAM user.
- ✅ **3.** AWS budget alert created in the Billing console as the account root (the `budget-app-dev` IAM user has no billing permissions, so this could not be done from the CLI). Notification-only — no budget actions, deliberately: actions can't stop Lambda or an Aurora cluster, carry a per-day charge, and an IAM-deny action risks locking the dev user out of `cdk destroy`. The real cost control is tearing stacks down when not in use.
- ✅ **4.** FastAPI project in `apps/api` with `uv`. Hello-world `/health` endpoint running under `uvicorn app.main:app --reload`. Mangum handler defined (unused locally).
- ✅ **5.** Postgres 16 running locally via Docker Compose at `localhost:5432`. Credentials: `budgeting/budgeting/budgeting_dev`. `/health/db` endpoint confirms connection.

## Phase 2: Data Model & Core API

- ✅ **6.** Data model sketched: `User`, `Account`, `Category`, `Transaction`, `Budget` + enums. Money as `Numeric(12,2)`, dates as `Date`, UUIDs as PKs. Composite index `(user_id, occurred_on)` on transactions.
- ✅ **7.** SQLAlchemy 2.x models with `Mapped[...]` / `mapped_column(...)`. All under `apps/api/app/models/`. Cascade deletes from user.
- ✅ **8.** Alembic configured (`alembic init alembic`, `env.py` reads `DATABASE_URL` from settings, imports `app.models`). Initial migration generated and applied. `alembic_version` table present.
- ✅ **9a.** Pydantic schemas for all entities under `apps/api/app/schemas/`. Three-schema pattern (`Create`/`Update`/`Read`). `APISchema` base with `from_attributes=True`. `Page[T]` and `PaginationParams` in `common.py` (the latter as a `BaseModel` query model, consumed via `Annotated[PaginationParams, Query()]` — see DECISION 015). `email-validator` installed. Package re-exports via `schemas/__init__.py`. mypy clean (added `pydantic.mypy` plugin to fix a `BaseSettings` call-arg false positive).
- ✅ **9b.** CRUD routers under `apps/api/app/routers/` for accounts, categories, transactions, budgets. Five verbs each, `Page[T]` list endpoints, placeholder `get_current_user_id` dependency (real Cognito one comes in Phase 4). Ownership enforced via the generic `get_for_user` helper in `app/crud.py` + the `UserOwned` mixin (see DECISION 017); owned FKs (`account_id`/`category_id`/`parent_id`) validated on create/update. All four wired into `main.py` via `routers/__init__.py` re-exports.
- ✅ **10.** Seed script (`apps/api/scripts/seed.py`) using `Faker` to populate local DB with realistic test data. Writes through the ORM directly (not the HTTP API), wipes-and-reseeds the dev user (matching `DEV_USER_EMAIL`) via cascade, stamps `user_id` on every owned row, uses `Decimal` money with signed amounts (DECISION 010). Run: `uv run python scripts/seed.py`.
- ✅ **11.** pytest + `TestClient`. `tests/conftest.py` holds the shared fixtures: a session-scoped `engine` that creates/drops the schema in a separate `budgeting_test` database, a function-scoped `db_session` bound to a connection with `join_transaction_mode="create_savepoint"` (so router `commit()` calls become savepoint releases and the outer rollback still isolates each test), `user`/`other_user` plus owned-row fixtures for all four entities, and a `client` that overrides `get_db` and `get_current_user_id`. 37 tests under `tests/routers/` (happy path, validation failure, cross-tenant 404 on every id-taking verb, plus FK-ownership attempts on `account_id`/`category_id`/`parent_id` for both create and update) and `tests/test_crud.py` (parametrized unit tests for `get_for_user` across all four models). Run: `cd apps/api; uv run pytest`.

## Phase 3: AWS Infrastructure

- ✅ **12.** `cdk bootstrap` done: `aws://001945408785/us-east-2`, stack `CDKToolkit` at bootstrap version 32, run through the `budgeting-app-deploy` role. Access model narrowed to assume-role only, plus a `budgeting-app-viewer` role (`ViewOnlyAccess`) for inspecting resources (see CLAUDE.md → AWS access model). CDK app created with `cdk init app --language python` in `infra/cdk` (pip venv, `app.py`, `stacks/`).
- ⏳ **13.** **`DbStack` done** (`BudgetingDbDev`, DECISION 019): a VPC with 2 isolated subnets and no NAT gateway, and Aurora Serverless v2 on Postgres 16.13 (min 0 / max 1 ACU, auto-pause after 300 s, encrypted, IAM auth, `RemovalPolicy.DESTROY`). 5 template tests in `infra/cdk/tests/unit/test_db_stack.py`. Deployed, checked with the viewer profile, then destroyed. Problems hit along the way:
  - **Free-plan accounts can't create a regular Aurora cluster** ("you need to set WithExpressConfiguration"). The account was upgraded to the Paid plan.
  - **The engine version had been retired.** 16.6 was gone, so the cluster now uses 16.13.
  - **The CDK CLI was older than `aws-cdk-lib`** (cloud assembly schema mismatch). Fixed by upgrading the CLI.
  - **Automated backups are deleted with the cluster.** The daily `rds:` snapshot didn't survive `cdk destroy`, so `delete_automated_backups` isn't needed.

  **`ApiStack` done** (`BudgetingApiDev`): a `DockerImageFunction` (x86_64, 512 MB, 30 s timeout) in the isolated subnets, an HTTP API in front of it, an explicit `LogGroup` (7-day retention, `DESTROY`), and a `ApiUrl` output. `DATABASE_URL` points at the cluster endpoint as `budgeting_app`, with no password. 3 template tests in `test_api_stack.py`. Deployed; `/health` and `/docs` worked through API Gateway; destroyed.
  - **The account's Lambda concurrency limit is 10**, so `reserved_concurrent_executions` is commented out. The account limit caps connections for now (DECISION 018).

  **Still to do:** the security group rule letting the Lambda into the DB (Lesson 7, with Step 15).
- ✅ **14.** Lambda container image: `apps/api/Dockerfile` on `public.ecr.aws/lambda/python:3.12`, deps installed with `uv export --frozen --no-dev` + `uv pip install --target ${LAMBDA_TASK_ROOT}`, `CMD ["app.main.handler"]`. A `.dockerignore` keeps `.env` and `.venv` out. Runtime deps trimmed: `pytest`, `httpx`, `faker`, `uvicorn` moved to the dev group. Tested locally with the emulator using `apps/api/events/health.json` (`/health` → 200; `/health/db` reaches Compose Postgres via `host.docker.internal`).
- ⏳ **15.** First successful `cdk deploy`. Debug cold starts, DB connectivity, IAM. **This step teaches the most.**
  - **Cold start, still to re-measure.** The emulator's init took 812 ms. The first Lambda cold start after deploy reported `Init Duration: 10000.42 ms`. That's exactly the 10 s init limit, so init most likely timed out and was retried during the invoke, probably because the newly deployed image was still loading from ECR. Next deploy: read the `INIT_REPORT` status, force a second cold start (edit an env var), and compare. If ~10 s repeats every time, try `memory_size=1024`. Watch the total time: a timed-out init plus an Aurora resume (~15 s) gets close to API Gateway's 30 s limit.
- ⬜ **16.** **Learning exercise, then teardown (DECISION 018).** Deploy RDS Proxy once in front of the DB, point the Lambda at the proxy endpoint, and observe connections. Then remove the proxy and verify `aws rds describe-db-proxies` returns empty. This needs a read-capable profile; `budgeting-deploy` gets `AccessDenied`. It has an ~$87/month floor on Aurora Serverless v2 (8-ACU minimum). Steady state: the Lambda connects directly to the cluster with `pool_size=1, max_overflow=0` plus reserved concurrency.
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
