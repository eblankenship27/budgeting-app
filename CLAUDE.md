# CLAUDE.md

This file gives Claude Code the context it needs to help build this project effectively. Read this first before making changes.

## Project Overview

A personal **budgeting app** being built as a learning project to practice Python, FastAPI, AWS Lambda, and modern full-stack patterns ahead of an upcoming internship. The app will eventually have a web frontend and a mobile app, with bank connectivity via Plaid.

**The point is not just to ship — it's to learn the AWS serverless stack, modern Python patterns, and full-stack TypeScript/React deeply.** Optimize explanations and choices for educational value, not just speed.

## How to Teach Me

Work is organized as numbered lessons (Lesson 8) made of lettered steps (8a, 8b, ...). I type the code myself.

1. **Teach before code.** Every lesson, and every step within it, starts with an explanation before any code:
   - the concept and the problem it solves,
   - how it works under the hood (what AWS, CDK, or the library actually does),
   - why this approach was chosen over the alternatives,
   - what to watch for: costs, security implications, common mistakes.

   Only then give the code, and explain any line that isn't obvious.
2. **Ask me when unsure.** If a requirement, a design choice, or my intent is ambiguous, ask before proceeding. Don't guess. The same goes for anything not verified: say so explicitly rather than presenting it as fact.
3. **Check my work.** After I finish a step, review what I wrote and run the tests or synth before moving on.

## Tech Stack

### Backend

- **Python 3.12+** with `uv` for package management
- **FastAPI** as the web framework (chosen over Flask for async, OpenAPI auto-gen, Pydantic integration)
- **SQLAlchemy 2.x** ORM with type-annotated `Mapped[...]` / `mapped_column(...)` style
- **Alembic** for migrations
- **Pydantic v2** + **pydantic-settings** for schemas and config
- **psycopg[binary]** (psycopg3) as the Postgres driver
- **Mangum** as the ASGI-to-Lambda adapter for production deployment
- **pytest** + **httpx** for testing, **ruff** for lint/format, **mypy** for type checking

### Database

- **PostgreSQL 16** (local: Docker Compose, prod: Aurora Serverless v2)
- Lambda connects **directly to the Aurora cluster** with `pool_size=1, max_overflow=0`. Concurrency is capped by the account's Lambda limit of 10 (reserved concurrency once that's raised). **RDS Proxy** was deployed once in step 16 to learn it, then torn down. It has an ~$87/month floor on Serverless v2 and blocks auto-pause (DECISION 018). Its code lives on the unmerged branch `lesson-8-rds-proxy`.

### Infrastructure

- **AWS CDK (Python)** — Infrastructure-as-Code
- **AWS Lambda** + **API Gateway** for the backend
- **AWS Cognito** for authentication (JWTs validated at API Gateway)
- **EventBridge** + **SQS** for scheduled jobs and async work (later phases)

### Web frontend (later)

- **Next.js (App Router)** + **TypeScript** + **Tailwind**
- **TanStack Query** for server state
- Deployed to **Vercel**

### Mobile (later)

- **Expo** + **React Native** + **TypeScript**

### Shared

- **pnpm workspaces** monorepo
- `packages/shared` holds TypeScript types (generated from FastAPI's OpenAPI spec), Zod schemas, and API client code
- Both web and mobile import from `packages/shared`

### Optional / Future

- **Plaid** for bank connectivity (sandbox first)
- **pandas** in an analytics service layer for spending summaries, rolling averages, CSV imports — NOT for basic CRUD
- **polars** is worth knowing about as a modern alternative, but pandas is the choice here for internship-prep reasons

## Repository Structure

``` text
budgeting-app/
├── apps/
│   ├── api/                 # FastAPI backend (Python, uv-managed)
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   ├── models/      # SQLAlchemy ORM
│   │   │   ├── schemas/     # Pydantic schemas
│   │   │   ├── routers/     # FastAPI route handlers
│   │   │   ├── services/    # Business logic (pandas lives here)
│   │   │   └── deps/        # FastAPI dependencies (auth, etc.)
│   │   ├── alembic/         # Migrations
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   ├── alembic.ini
│   │   ├── .env             # gitignored
│   │   └── .env.example
│   ├── web/                 # Next.js (later)
│   └── mobile/              # Expo (later)
├── packages/
│   └── shared/              # Shared TS types, Zod schemas, API client
├── infra/
│   └── cdk/                 # AWS CDK stacks (Python)
│       └── stacks/
│           ├── api_stack.py
│           ├── db_stack.py
│           └── auth_stack.py
├── docker-compose.yml       # Local Postgres
├── package.json             # Root workspace config
├── pnpm-workspace.yaml
├── .gitattributes           # Line ending normalization (LF in repo)
├── .gitignore
└── CLAUDE.md                # This file
```

## Architectural Principles

1. **Schemas ≠ Models.** SQLAlchemy models describe the database; Pydantic schemas describe the API surface. They overlap but evolve separately. Three Pydantic schemas per entity: `Create`, `Update`, `Read`.

2. **Every table has a `user_id` FK.** Multi-tenant isolation must be enforced at the query layer. Forgetting this is the #1 security bug — a `get_current_user` dependency in phase 4 will enforce it.

3. **Money is `Numeric(12, 2)` / `Decimal`, never `Float`.** Non-negotiable. IEEE 754 has no place near user money.

4. **UUIDs as primary keys, not auto-increment integers.** Postgres native UUID type with `as_uuid=True`.

5. **Foreign keys use `ON DELETE CASCADE` for owned data, `ON DELETE SET NULL` for soft references** (e.g., `category_id` on a transaction).

6. **`server_default=func.now()` for timestamps**, not Python-side defaults. The DB is the source of truth for time.

7. **FastAPI code stays infrastructure-agnostic.** `Mangum` is the only Lambda glue. The same code runs under `uvicorn` locally and inside Lambda in prod. CDK lives in a separate folder so deployment targets can change without touching app code.

8. **Auth at the edge.** API Gateway validates Cognito JWTs before invoking Lambda. The FastAPI app trusts the JWT claims and only re-validates structure, not signature.

9. **Pandas is for analytics, not CRUD.** Use SQLAlchemy for CRUD. Reach for pandas in a service layer when doing rolling averages, time-series resampling, CSV ETL, or anomaly detection. Always filter at SQL first; never `SELECT *` into a DataFrame.

10. **Cap everything.** Every string `max_length`, every numeric `max_digits`, every paginated endpoint hard-caps `limit` (e.g., 200). Defensive by default.

## Conventions

- **Sentence case** in user-facing strings.
- **`str | None` over `Optional[str]`** (Python 3.10+ syntax).
- **`from __future__ import annotations` not used** — we're on 3.12+ so PEP 604 union syntax just works.
- **Imports sorted by ruff** (`I` rule enabled).
- **Type hints on every function**, including return types — mypy is enabled.
- **Pydantic `model_config = ConfigDict(from_attributes=True)`** on read schemas so they can be built from ORM objects via `Schema.model_validate(orm_obj)`.
- **Never put `user_id` in request bodies.** It comes from auth, never from the client.
- **Never expose `password_hash`, `cognito_sub`, or other internal columns in response schemas.**
- **Tests under `apps/api/tests/`** mirror the `app/` package structure.
- **Migrations are reviewed before applying.** Always open the autogenerated file and verify it before `alembic upgrade head`.

## Environment

- **Developer OS:** Windows 11, PowerShell. (WSL2 may be added later for Lambda packaging work.)
- **Python:** 3.12.x installed via winget; `uv` for venv/dep management.
- **Node:** LTS via nvm-windows. `.nvmrc` pinned at the repo root.
- **Docker Desktop** for local Postgres.
- **AWS region:** us-east-2 (Ohio — close to Boston, fewer outages than us-east-1).
- **AWS account:** `001945408785`.
- **Budget alert:** created in the Billing console as account root, notification-only (no budget actions — see `PROGRESS.md` step 3 for why). Billing is account-level: IAM users get no access to it until the root user enables "IAM user and role access to billing information", so budget work can't be done from the CLI with these credentials.

### AWS access model

Deliberately **assume-role only**. The long-lived access key holds almost no power; roles hold the permissions.

| Identity | Permissions | Used for |
| --- | --- | --- |
| `budget-app-dev` (IAM user) | one inline policy, `AssumeBudgetingDeployRole`: `sts:AssumeRole` on `budgeting-app-deploy` only | holding the static access key in `~/.aws/credentials`; nothing else |
| `budgeting-app-deploy` (role) | customer-managed `CdkDeployAssumeRoles`: `sts:AssumeRole` on the four `cdk-hnb659fds-*` bootstrap roles + `ssm:GetParameter` on `/cdk-bootstrap/hnb659fds/version` | every `cdk deploy` / `cdk diff` |
| `budgeting-app-viewer` (role) | AWS-managed `ViewOnlyAccess` (lists and describes resources; can't read data such as secret values). Trust policy names `budget-app-dev` directly. | observing deployed resources: `--profile budgeting-view` |
| `cdk-hnb659fds-cfn-exec-role-...` | `AdministratorAccess` (bootstrap default) | assumed by **CloudFormation**, never by you — this is what actually creates resources |

The CLI profile in `~/.aws/config` does the exchange automatically:

```ini
[profile budgeting-deploy]
role_arn = arn:aws:iam::001945408785:role/budgeting-app-deploy
source_profile = default
region = us-east-2

[profile budgeting-view]
role_arn = arn:aws:iam::001945408785:role/budgeting-app-viewer
source_profile = default
region = us-east-2
```

Verify with `aws sts get-caller-identity --profile budgeting-deploy` — the ARN must come back as `assumed-role/budgeting-app-deploy/...`, not `user/budget-app-dev`.

**Why this shape:** a leaked access key can only open an hour-long session on one named role, visible in CloudTrail and revocable by editing one trust policy (no key rotation). Don't add permissions to `budget-app-dev` — add them to a role. Not even `iam:Get*` on itself; that's how users quietly accumulate ambient power.

**Don't add `AdministratorAccess` back to `budgeting-app-deploy`.** Two consequences to plan around instead:

1. **`cdk bootstrap` will fail** under the narrowed policy — it creates IAM roles, an S3 bucket, an ECR repo and SSM parameters. This matters when a CDK upgrade demands a newer bootstrap version (currently at **32**).
2. **No IAM visibility.** Inspecting or changing IAM now requires the root console.

Both are solved by a second assumable role — **not yet created** — e.g. `budgeting-app-admin` with `AdministratorAccess`, the same trust policy pointing at `budget-app-dev`, that ARN added to the user's inline policy, and its own CLI profile. Root then goes back to being reserved for genuinely account-level work (billing, support plans, closing the account). An MFA condition on *that* role's trust policy is where MFA is worth the friction.

**Verify a permission change by confirming what it forbids,** not just what it allows: after narrowing, `aws iam list-roles --profile budgeting-deploy` must return `AccessDenied` while the `sts:AssumeRole` calls still succeed. Same reasoning as the cross-tenant 404 tests.

## Windows Gotchas

### Line endings

The repo uses a `.gitattributes` file that normalizes all text files to LF in the repo, with `.ps1`/`.bat`/`.cmd` files explicitly CRLF. Don't disable this. After any `.gitattributes` change, run `git add --renormalize .`.

### Git Bash mangles AWS paths and ARNs

Git Bash (MSYS) rewrites any argument that looks like a Unix absolute path into a Windows path before the program sees it. `aws ssm get-parameter --name /cdk-bootstrap/hnb659fds/version` silently became `C:/Program Files/Git/cdk-bootstrap/...` and returned `ParameterNotFound` — a wrong answer, not an error, which looks exactly like a broken bootstrap.

Run AWS commands from **PowerShell**, or prefix with `MSYS_NO_PATHCONV=1`, or double the leading slash (`//cdk-bootstrap/...`). Expect this with SSM parameter paths and IAM ARNs.

## Project Phases & Status

See `PROGRESS.md` for the detailed checklist with completion status. Summary:

- **Phase 1: Foundations** — monorepo, dev tools, FastAPI hello-world, local Postgres ✅
- **Phase 2: Data Model & Core API** — SQLAlchemy models + Alembic ✅ / Pydantic schemas ✅ / CRUD routers ✅ / seed script ✅ / tests ✅ **(Phase 2 complete)**
- **Phase 3: AWS Infrastructure** — CDK, Lambda, Aurora, migrations, RDS Proxy (deploy-once learning exercise, DECISION 018) ✅ **(Phase 3 complete)**
- **Phase 4: Authentication** — Cognito, scoped queries
- **Phase 5: Web Frontend** — Next.js, auth, dashboard, analytics endpoints (where pandas enters)
- **Phase 6: Bank Connectivity** — Plaid sandbox, transaction sync
- **Phase 7: Mobile** — Expo, shared API client
- **Phase 8: Polish** — observability, CI/CD, README

## What's Next

**Phase 2 is complete.** Models + migrations, Pydantic schemas, CRUD routers for all four entities, the `Faker` seed script, and the pytest suite are all done. 37 tests pass; `ruff check`, `ruff format --check`, and `mypy app` are clean.

**Phase 3 has started.** The budget alert (step 3) is in place, the assume-role access model is set up and narrowed (see Environment above), and `cdk bootstrap` has run against `aws://001945408785/us-east-2` — bootstrap stack `CDKToolkit` is `CREATE_COMPLETE` at version 32.

**Step 12 is done and Step 13 is nearly done.** `infra/cdk/` holds a CDK app with two stacks. `ApiStack` is described below. `DbStack` (`BudgetingDbDev`) is a VPC with no NAT gateway and two isolated subnets, plus an Aurora Serverless v2 cluster on Postgres 16.13. It has been deployed, checked against the real account, and destroyed. Five template assertions in `infra/cdk/tests/unit/test_db_stack.py` pin its cost and security settings (DECISION 019). The account was upgraded from the AWS Free plan to the Paid plan, because Free-plan accounts can't create a regular Aurora cluster.

**Step 14 is done, and `ApiStack` is deployed and working.** FastAPI runs as a Lambda container image (`apps/api/Dockerfile`), behind an API Gateway HTTP API, in the isolated subnets. `/health` and `/docs` worked end to end, and both stacks were destroyed afterwards.

**Steps 13, 15 and 17 are done: the Lambda talks to Aurora.** It connects as `budgeting_app` with IAM auth tokens (no stored password). `DbStack` creates that user through a Data API custom resource, and a migration Lambda run by a CDK `Trigger` applies Alembic before the API Lambda updates (DECISION 020). `/accounts/` worked end to end through API Gateway; both stacks were destroyed. Cold init is ~2.2 s, but the first request after idle takes ~22 s while Aurora resumes from 0 ACU, close to API Gateway's 30 s cap.

**Step 16 is done, so Phase 3 is complete.** RDS Proxy was deployed once from the unmerged `lesson-8-rds-proxy` branch, load-tested, and destroyed. Lambda's concurrency limit of 10 throttled most of a 200-request burst before any request reached the database, and the proxy never needed to multiplex (DECISION 018 outcome). An optional follow-up on that branch: force multiplexing with `max_connections_percent=1`.

The next step is **Phase 4: Cognito authentication** (PROGRESS step 18 onward).

Cleanup habit: CDK's helper Lambdas (`CustomVpcRestrictDefaultSG` in `DbStack`, the Trigger provider in `ApiStack`) each leave a `/aws/lambda/...` log group behind on every deploy, with retention set to never expire. Lambda creates the group itself, outside CloudFormation, so `cdk destroy` can't remove it. Delete them in the root console now and then. Bootstrap ECR images also accumulate, at about 240 MB per rebuild.

Cost habits: `cdk destroy` whenever you're not actively working. The budget alert only tells you after money is spent; destroying the stack is what actually stops it. On the Paid plan nothing caps spending once credits run out.

### CDK workflow notes (for future sessions)

- Run every `cdk` command from `infra/cdk` with **its own venv active** (`.venv\Scripts\Activate.ps1`). It's pip-managed, not uv, so `uv run` doesn't apply there. Tests: `python -m pytest`, never bare `pytest`.
- A fresh venv needs **both** files: `python -m pip install -r requirements.txt -r requirements-dev.txt`.
- **The CDK CLI must be at least as new as `aws-cdk-lib`.** If `cdk` reports a "cloud assembly schema version mismatch", run `npm install -g aws-cdk`.
- **Venvs can't be moved.** If the repo folder moves, delete `.venv` and recreate it.
- **AWS retires Aurora minor versions.** Synth and unit tests can't catch a retired version; only a deploy does. Pick a version from `aws rds describe-db-engine-versions --engine aurora-postgresql --profile budgeting-view`.
- Deploy and destroy with `--profile budgeting-deploy`. Inspect with `--profile budgeting-view`. The view role can't list or read secrets.
- **Check synth with `cdk synth`, not `python app.py`.** Only the CLI applies the feature flags in `cdk.json`. One of them, `validateAgainstDefaultRules`, turns template-validation warnings into synth errors; others change generated names. Suppress a false positive on one construct with `cdk.Validations.of(construct).acknowledge(cdk.Acknowledgment(id=..., reason=...))`.
- **A 503 from the HTTP API under load usually means Lambda throttling** (account concurrency limit 10), not an app error. Check the function's `Throttles` metric.

### Testing notes (for future sessions)

- Tests need Docker running and a `budgeting_test` database alongside `budgeting_dev` in the same container. The schema is created and dropped per run, so that DB is empty between runs — that's expected, not a bug.
- `tests/conftest.py` isolates each test by rolling back an outer transaction. Routers call `commit()` freely because the session is bound with `join_transaction_mode="create_savepoint"`.
- Run from `apps/api`, not the repo root — `Settings` resolves `.env` relative to the current working directory.
- Assert on the `loc` of a 422 error, never on `msg`; message wording is a Pydantic version detail.
- Cross-tenant attempts must return **404, not 403**. A 403 would confirm the row exists and leak another tenant's data. `tests/test_crud.py` pins this.

### Open decision

Write schemas inherit Pydantic's default `extra="ignore"`, so a misspelled field in a request body is silently dropped rather than rejected (a typo'd `initial_balance` posts an account with a zero balance and returns 201). `PaginationParams` already sets `extra="forbid"`. Decide whether `APISchema` should do the same — it would turn client typos into 422s, at the cost of rejecting forward-compatible clients that send unknown fields.

See `docs/NEXT.md` for the detailed router/seed working notes and `docs/REVIEW.md` for the self-review checklist.

## Key Files to Read First

When picking this project back up, read in this order:

1. `CLAUDE.md` (this file) — context and conventions
2. `PROGRESS.md` — detailed phase checklist
3. `apps/api/app/db.py` — DB setup and base
4. `apps/api/app/models/__init__.py` — see all models at a glance
5. `apps/api/app/schemas/__init__.py` — see all schemas at a glance
6. `apps/api/alembic/versions/` — schema history
7. `docker-compose.yml` — local DB setup

## Things to Avoid

- **Don't** use `Float` for money columns or amounts. Ever.
- **Don't** put `import pandas` in `main.py` — Lambda cold start cost. Import only inside service modules that use it.
- **Don't** trust client-supplied `user_id`. Pull it from the auth dependency.
- **Don't** skip `pool_pre_ping=True` on the SQLAlchemy engine — Lambda + RDS without it gives flaky connection errors.
- **Don't** put business logic in routers. Routers parse input, call services, return output.
- **Don't** add fields to the SQLAlchemy model without a corresponding Alembic migration. Schema drift between code and DB is a recurring source of "works on my machine" pain.
- **Don't** call SQLAlchemy 1.x style `query()` syntax — use 2.0 style `select()` everywhere.
- **Don't** use `autocommit` in `sessionmaker` — it was removed in SQLAlchemy 2.0. `autoflush=False` is still valid.

## Useful Reference Commands

```powershell
# Start local DB
docker compose up -d

# Run API locally
cd apps\api
uv run uvicorn app.main:app --reload

# New migration
uv run alembic revision --autogenerate -m "describe change"

# Apply migrations
uv run alembic upgrade head

# Rollback last migration
uv run alembic downgrade -1

# Lint & format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy app

# Run tests
uv run pytest

# Generate TS types from OpenAPI (once openapi-typescript is set up in packages/shared)
# pnpm --filter shared generate:types
```
