# NEXT.md — Offline work plan (Phase 2 / Step 9b, continued)

A self-contained guide for finishing the CRUD routers while offline. Pairs with
`docs/REVIEW.md` (use that to self-check each file before you'd normally ping for a review).

> **Context:** Read `CLAUDE.md`, `PROGRESS.md`, and `docs/DECISIONS.md` (esp. **017**) first.
> The accounts router is the **reference template** — copy its shape for the rest.

---

## Where we are

- ✅ `UserOwned` mixin in `app/db.py` (plain class, NOT a second `DeclarativeBase`) — gives the
  four owned models a shared `id` + `user_id`, and gives the generic helper a typed bound.
- ✅ `app/crud.py` → `get_for_user[ModelT: UserOwned](db, Model, row_id, user_id) -> ModelT`
  — the single ownership-scoped "fetch or 404" chokepoint.
- ✅ `app/deps/auth.py` → `get_current_user_id` (placeholder dev user, get-or-create, returns `user.id`).
- ✅ `app/routers/accounts.py` — **complete and correct**. This is your template.
- ⏳ Remaining: **categories, transactions, budgets** routers, then wire them into `main.py`.

---

## The remaining routers

Mechanically these are **copies of accounts** — same five verbs, same pagination, same
`get_for_user` for get-one. Build them by copying `accounts.py` and changing the model,
schemas, and the FK checks below. Suggested order: **categories → transactions → budgets**
(the latter two FK into categories, so having categories working makes them testable).

### ⭐ The one concept that matters: validate **owned foreign keys**

Accounts had no FK to another user-owned resource (only `user_id`). The other three do.
**The DB's FK constraint only checks a row *exists*, not who owns it.** So if a client sends
an `account_id` / `category_id` / `parent_id` in a create or update body, nothing stops them
pointing at *another user's* row — a silent cross-tenant write.

**Reuse `get_for_user` to validate every incoming owned FK.** It's not just for the GET-by-id
route — it's your generic "does this id belong to me, else 404" check:

```python
# in transaction_create, before constructing the Transaction:
get_for_user(db, Account, body.account_id, user_id)          # required FK → always check
if body.category_id is not None:                              # optional FK → only if provided
    get_for_user(db, Category, body.category_id, user_id)
```

Same query, both conditions, 404 on miss — the DECISION 017 discipline applied to **writes**.
Do this in **both** POST and PATCH (PATCH only for FKs actually present in `exclude_unset`).

### Per-resource differences (vs. accounts)

| Router | Owned FKs to validate | Notes |
| --- | --- | --- |
| **categories** | `parent_id` (self-FK, **optional**) | Validate `parent_id` against `Category` for this user if set — can't parent under someone else's category. Check `CategoryCreate` for any field-name mapping (accounts had `initial_balance → current_balance`; categories is likely a direct construct). |
| **transactions** | `account_id` (**required**), `category_id` (**optional**) | Heaviest router. `amount` is a signed `Decimal` — no special handling, just stores. List endpoint naturally wants `order_by(transaction_date.desc())` (the `(user_id, transaction_date)` composite index supports this). Filters (date range / account / category) are a good follow-up but keep parity-with-accounts for now. |
| **budgets** | `category_id` (**required**) | Simplest of the three. Validate `category_id` always. |

---

## After the three routers

1. **Wire all four into `main.py` (Step 5).** Currently only accounts is included (and only
   temporarily, for testing). Do them together:

   ```python
   from app.routers.accounts import router as accounts_router
   from app.routers.categories import router as categories_router
   from app.routers.transactions import router as transactions_router
   from app.routers.budgets import router as budgets_router
   # ...
   app.include_router(accounts_router)
   app.include_router(categories_router)
   app.include_router(transactions_router)
   app.include_router(budgets_router)
   ```

   (Optional polish: a `routers/__init__.py` that exposes them, so `main.py` has one import line.)

2. **Seed script (Step 10)** — `Faker` to populate the local DB with a dev user + realistic
   accounts/categories/transactions/budgets. ⚠️ See offline note below: `uv add faker` needs
   network — install it **before** you lose service.

3. **Tests (Step 11)** — `pytest` + `TestClient`. Per endpoint: one happy path, one validation
   failure, one **cross-tenant attempt** (create data as user A, try to read/patch/delete it as
   user B → expect 404). The cross-tenant test is the one that proves the whole `user_id`-scoping
   design. (`pytest`/`httpx` should already be dev deps — verify before going offline.)

---

## Gotchas (everything that bit us building accounts — don't relearn these)

- **`status_code` is keyword-only.** `@router.post("/", 201)` crashes at import. Use
  `status_code=status.HTTP_201_CREATED`. Same for `204_NO_CONTENT` on DELETE.
- **204 must have NO response body.** DELETE gets `status_code=204` and **no** `response_model`
  / return annotation — otherwise `AssertionError: Status code 204 must not have a response body`.
- **`def`, not `async def`.** The DB layer is synchronous. `async def` + a blocking `db.commit()`
  stalls the event loop. Use plain `def` so FastAPI runs handlers in a threadpool.
- **SQLAlchemy 2.0 only.** No `db.query(...)` — use `select(...)`. CLAUDE rule.
- **Execute your queries.** `select(...).limit(...)` is just a statement; you need
  `db.execute(...).scalars().all()` for rows. Count = `select(func.count()).select_from(Model)
  .where(...)` resolved with `.scalar_one()` — **with the parentheses** (a bare `.scalar_one`
  is a method object, not an int, and fails `Page` validation).
- **`response_model` on every body-returning route.** Without it, FastAPI serializes the raw ORM
  object and **leaks `user_id`** (and risks lazy-loads). POST/GET-one/PATCH → `XRead`;
  list → `Page[XRead]`; DELETE → none.
- **PATCH semantics:** `payload.model_dump(exclude_unset=True).items()` → `setattr`. Iterating the
  dict without `.items()` yields keys and explodes on unpack. `exclude_unset` is what stops you
  clobbering stored fields with `None`.
- **Deterministic `order_by`** on list endpoints (`created_at` or `id`) — otherwise `limit/offset`
  paging is non-deterministic across requests.
- **Pagination param:** `pagination: Annotated[PaginationParams, Query()]` — typed directly, **not**
  wrapped in `Depends` (DECISION 015).
- **Never trust client `user_id`.** It comes from `get_current_user_id`, never the request body.
- **Trailing slash:** collection routes are at `"/"` → full path `/categories/` etc. Hitting the
  no-slash form triggers a 307 redirect.

---

## What you CAN do offline (no network needed)

Everything local works without internet, **provided dependencies are already installed**:

- Write all three routers + wire into `main.py`.
- `docker compose up -d` (image already pulled), `uv run alembic upgrade head`.
- `uv run uvicorn app.main:app --reload` and test via Swagger at `http://127.0.0.1:8000/docs`.
- `uv run ruff check --fix . ; uv run ruff format . ; uv run mypy app`.
- Write the seed script and the test suite; `uv run pytest`.
- Self-review every file against `docs/REVIEW.md`.

### ⚠️ Do these BEFORE you lose service (they need network)

- `uv add faker` (seed script dependency).
- Confirm `pytest` + `httpx` are installed: `uv run pytest --version`. If not, `uv add --dev pytest httpx`.
- Any other new dependency. `uv` can't fetch packages offline.

---

## When you're back online

Hand me the three routers (and seed/tests if you got to them). I'll review against the
accounts template, focusing on the **owned-FK validation** in each POST/PATCH — that's the
spot most likely to hide a cross-tenant bug. Then we move to Phase 2 wrap-up and Phase 3 (AWS).
