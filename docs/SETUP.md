# SETUP.md

Local environment setup. Targets **Windows 11 + PowerShell**. Adapt commands for macOS/Linux as needed.

## Prerequisites (one-time install)

```powershell
# Python 3.12
winget install Python.Python.3.12

# uv (Python package/venv manager — replaces pip + venv)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# or: winget install astral-sh.uv

# Node LTS via nvm-windows (requires admin shell for nvm install/use)
winget install CoreyButler.NVMforWindows
# then in an admin PowerShell:
nvm install lts
nvm use lts

# pnpm
Invoke-WebRequest https://get.pnpm.io/install.ps1 -UseBasicParsing | Invoke-Expression

# AWS CLI
winget install Amazon.AWSCLI

# Docker Desktop (for local Postgres)
winget install Docker.DockerDesktop
```

Close and reopen PowerShell after these installs so PATH refreshes.

## Windows quality-of-life

- **Use Windows Terminal** (Microsoft Store), not legacy `cmd.exe`.
- **Loosen execution policy** for installer scripts:

  ``` powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

- **Enable long paths** (Node/Python deep nesting hits the 260-char limit):

  ```powershell
  # Admin PowerShell, then reboot
  New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
    -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
  ```

- **Disable Microsoft Store Python aliases** if `python` opens the Store: Settings → Apps → Advanced app settings → App execution aliases → turn off `python.exe` and `python3.exe`.
- **Don't keep the project in OneDrive/Dropbox.** Reparse points confuse `uv`. Use `C:\dev\` or similar.

## AWS

1. Create an IAM user `budgeting-app-dev` with `AdministratorAccess` (tighten later).
2. Create an access key → "Command Line Interface (CLI)" use case.
3. `aws configure`:
   - Region: `us-east-2`
   - Output format: `json`
4. Verify: `aws sts get-caller-identity` should return account info.
5. **Set a billing budget** in AWS Console → Billing → Budgets: $10–20/month, alerts at 50/80/100%. Do this before any deploys.

## Repository setup

```powershell
cd C:\dev
git clone <repo-url> budgeting-app
cd budgeting-app

# Install JS workspace deps (web, mobile, shared)
pnpm install

# Set up the Python API
cd apps\api
uv sync

# Start local Postgres
cd ..\..
docker compose up -d
docker compose ps   # should show "Up (healthy)"

# Run the API
cd apps\api
uv run uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/docs> to see the interactive Swagger UI.

## Daily dev loop

```powershell
# Start the DB if it's not running
docker compose up -d

# In one terminal: run the API
cd apps\api
uv run uvicorn app.main:app --reload

# In another terminal: run web (later phases)
cd apps\web
pnpm dev
```

## When you change models

```powershell
cd apps\api

# Generate a migration
uv run alembic revision --autogenerate -m "describe what changed"

# READ the generated file in apps\api\alembic\versions\ — autogenerate is good but not perfect

# Apply it
uv run alembic upgrade head

# Roll back one step if needed
uv run alembic downgrade -1
```

## Connecting to local Postgres with a GUI

Pick one:

- **TablePlus** — nicer UI, two-connection free tier. `winget install TablePlus.TablePlus`
- **DBeaver** — heavyweight, supports every DB. `winget install dbeaver.dbeaver`

Connection details:

- Host: `localhost`
- Port: `5432`
- User: `budgeting`
- Password: `budgeting`
- Database: `budgeting_dev`

## Troubleshooting

**`uv` shows `tool.uv.dev-dependencies` deprecation warning:** Move dev deps to `[dependency-groups] dev = [...]` instead. Delete the `[tool.uv]` block if it's empty.

**`uv trampoline failed to canonicalize script path`:** The `.venv` is broken. From `apps\api`:

```powershell
Remove-Item -Recurse -Force .venv
Remove-Item -Force uv.lock
uv sync
```

**`hatchling.build.build_editable failed`:** `pyproject.toml` is missing `[tool.hatch.build.targets.wheel] packages = ["app"]`. See `apps/api/pyproject.toml`.

**`psycopg2 vs psycopg` errors:** SQLAlchemy 2.x with psycopg3 wants `postgresql+psycopg://` in `DATABASE_URL`, not `postgresql://` or `postgresql+psycopg2://`.

**`/health/db` returns 500 "connection refused":** Docker isn't running. `docker compose up -d`.

**`/health/db` returns 500 "password authentication failed":** `.env` `DATABASE_URL` doesn't match `docker-compose.yml`. Correct value: `postgresql+psycopg://budgeting:budgeting@localhost:5432/budgeting_dev`.

**Git: "LF will be replaced by CRLF" warning:** Add `.gitattributes` (already in repo). After changes, `git add --renormalize . && git commit -m "Normalize line endings"`.

**PowerShell square bracket issue:** `uv add uvicorn[standard]` may fail because PowerShell treats `[...]` specially. Quote it: `uv add "uvicorn[standard]"`.

**nvm-windows doesn't auto-read `.nvmrc`:** Known limitation. `nvm use <version>` manually if needed.

## Stack version pins (current as of project start)

These are the versions known to work together. Update one at a time, run tests after each.

- Python: 3.12.x
- Node: 22.x LTS
- PostgreSQL: 16
- FastAPI: latest (1.x+)
- SQLAlchemy: 2.x (NOT 1.4 — APIs are different)
- Pydantic: 2.x (NOT 1.x)
- Alembic: latest
- psycopg: 3.x via `psycopg[binary]`
- Next.js: latest with App Router (NOT pages router)
- Expo SDK: latest
