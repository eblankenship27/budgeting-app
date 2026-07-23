# REVIEW.md — Self-review checklist for the CRUD routers

Run this against each router you write offline, so you can catch the common mistakes without a
live review. Work top to bottom. Anything you can't tick is a bug to fix. Pairs with `docs/NEXT.md`.

> **How to use:** copy the per-router checklist below for each of categories / transactions /
> budgets. Then run the "whole-app" checks once at the end.

---

## Tooling gate (run first — these catch a lot for free)

```powershell
cd apps\api
uv run ruff check --fix .      # import order, unused imports, lint
uv run ruff format .           # whitespace, blank lines
uv run mypy app                # type errors — the generic helper + response models
```

- [ ] `ruff check` is clean (no remaining errors after `--fix`).
- [ ] `mypy app` reports **no** errors. (If `get_for_user` complains about `.id`/`.user_id`,
      the `UserOwned` bound is wrong.)
- [ ] App imports without crashing: `uv run python -c "import app.main"` exits 0.
      (Catches the `status_code` positional-arg and 204-body assertions at import time.)

---

## Per-router checklist (repeat for categories, transactions, budgets)

### Structure & wiring
- [ ] `router = APIRouter(prefix="/<plural>", tags=["<plural>"])`.
- [ ] All five handlers are plain **`def`**, NOT `async def`.
- [ ] Every handler takes `db: Session = Depends(get_db)` and
      `user_id: uuid.UUID = Depends(get_current_user_id)`.

### POST `/`
- [ ] `status_code=status.HTTP_201_CREATED` (keyword, not positional).
- [ ] `response_model=<X>Read`.
- [ ] `user_id` is stamped from the dependency — **NOT** read from the request body.
- [ ] Any field-name mismatch between the Create schema and the model is mapped explicitly
      (don't blindly `**model_dump()` if names differ).
- [ ] **Every owned FK in the body is validated with `get_for_user` before constructing the row**
      (required FK → always; optional FK → only `if value is not None`). ⭐ security-critical
- [ ] `db.add` → `db.commit` → `db.refresh` → return the ORM object.

### GET `/` (list)
- [ ] `response_model=Page[<X>Read]`.
- [ ] `pagination: Annotated[PaginationParams, Query()]` (NOT wrapped in `Depends`).
- [ ] Uses `select(...)`, NOT `db.query(...)`.
- [ ] Rows are actually executed: `db.execute(...).scalars().all()`.
- [ ] Count is a separate `select(func.count()).select_from(<Model>).where(user_id==...)`
      resolved with `.scalar_one()` — **parentheses present**, returns an `int`.
- [ ] Both queries filter `Model.user_id == user_id`.
- [ ] A **deterministic** `.order_by(...)` is present.
- [ ] Returns `Page(items=..., total=<int>, limit=..., offset=...)`.

### GET `/{id}`
- [ ] `response_model=<X>Read`.
- [ ] Body is just `return get_for_user(db, <Model>, <id>, user_id)`.

### PATCH `/{id}`
- [ ] `response_model=<X>Read`.
- [ ] Fetches via `get_for_user` first (so a cross-tenant id 404s before any mutation).
- [ ] `for name, value in payload.model_dump(exclude_unset=True).items():` — **`.items()`** present.
- [ ] Applies with `setattr(obj, name, value)`.
- [ ] **If a PATCH body can change an owned FK, that new FK is re-validated with `get_for_user`.** ⭐
- [ ] `db.commit` → `db.refresh` → return.

### DELETE `/{id}`
- [ ] `status_code=status.HTTP_204_NO_CONTENT`.
- [ ] **No** `response_model` and **no** return-type annotation that implies a body.
- [ ] Fetches via `get_for_user`, then `db.delete(obj)` → `db.commit()` → `return` (nothing).

---

## Manual behavior tests (with the app running on `http://127.0.0.1:8000`)

Use Swagger at `/docs` (shows schemas + enum values) or `Invoke-RestMethod`. Remember the
**trailing slash** on collection routes (`/categories/`).

For each router:
- [ ] **Create** returns 201 and a body.
- [ ] **The response body does NOT contain `user_id`** (proves `response_model` is doing its job). ⭐
- [ ] **List** returns a `Page` with a correct integer `total` and your created item(s).
- [ ] **Get one** with the real id returns it; a random UUID returns **404**.
- [ ] **Patch** changes only the fields you sent; omitted fields are unchanged.
- [ ] **Delete** returns 204 with an empty body; a follow-up GET of that id returns 404.

### Owned-FK checks (the cross-tenant bug surface) ⭐
- [ ] Transactions: creating with an `account_id` that doesn't exist / isn't yours → **404**,
      not a 500 or a silent success.
- [ ] Transactions: `category_id` omitted → succeeds (it's optional).
- [ ] Budgets: bad/foreign `category_id` → **404**.
- [ ] Categories: `parent_id` pointing at a foreign/nonexistent category → **404**.

### Cascade sanity (optional but informative)
- [ ] Deleting an account deletes its transactions (cascade).
- [ ] Deleting a category sets dependent `transactions.category_id` to NULL (SET NULL),
      but cascades to its budgets (CASCADE). (Match against the model `ondelete=` settings.)

---

## Schema / DB drift
- [ ] You did **not** change any model field. (If you did, you owe an Alembic migration —
      `uv run alembic revision --autogenerate -m "..."`, review it, then `upgrade head`.)
- [ ] No new migration was generated unintentionally (routers shouldn't change the schema).

---

## Final gate before calling a router "done"
- [ ] ruff clean, mypy clean, app imports.
- [ ] All five endpoints manually exercised.
- [ ] `user_id` never appears in a response body.
- [ ] Every cross-tenant / foreign-FK attempt returns 404 (never 403, never 500, never success).

If all four boxes tick for all three routers, you've matched the accounts template correctly and
are ready to wire `main.py` and move on to the seed script + tests.
