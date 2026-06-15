# CODE_STYLE.md

Conventions for code in this repo. Most are enforced by `ruff` and `mypy`; this doc captures the patterns that aren't automatically checked.

## Python

### Type hints

- **Type hints on every function**, including return types.
- **`str | None` over `Optional[str]`.** Python 3.12 PEP 604 syntax.
- **`list[T]` / `dict[K, V]` over `List[T]` / `Dict[K, V]`.** No need to import from `typing`.
- **`Generator[T, None, None]` for FastAPI dependencies** that yield.

```python
# Yes
def get_account(account_id: uuid.UUID, db: Session) -> Account | None: ...

# No
from typing import Optional
def get_account(account_id, db) -> Optional[Account]: ...
```

### Imports

- **Sorted by ruff (`I` rule).** Standard library first, third-party, then local.
- **`from app.X import Y` not `import app.X`.** Explicit and avoids deep dotted access.
- **`if TYPE_CHECKING:` block** for cross-module type imports that would otherwise cause circular imports.

### SQLAlchemy

- **Always 2.0 style.** `Mapped[...]` + `mapped_column(...)`. `select(...)` for queries. Never `query()`.
- **`DeclarativeBase` as a class**, not `declarative_base()` as a function call.
- **Every model has `__tablename__` explicit**, not relying on automatic generation.
- **Foreign keys declared on the column**, not in a separate `ForeignKeyConstraint`.
- **Relationships declared with `back_populates=`** (bidirectional). Avoid `backref=` (one-way magic, harder to find).
- **`server_default=func.now()`** for timestamps, not Python-side `default=datetime.utcnow`.
- **Numeric for money:** `Mapped[Decimal] = mapped_column(Numeric(12, 2), ...)`. Never `Float`.
- **UUIDs:** `Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`.

### Pydantic

- **Schemas inherit from `APISchema`** (defined in `app/schemas/base.py`) which sets `from_attributes=True` and `str_strip_whitespace=True`.
- **Three schemas per entity:** `XxxCreate`, `XxxUpdate`, `XxxRead`. Often a shared `XxxBase`.
- **`Update` schemas have all fields `T | None = None`** for PATCH semantics.
- **`Read` schemas include `id` and `created_at`.**
- **Always cap strings and numerics:** `Field(min_length=1, max_length=100)`, `Field(max_digits=12, decimal_places=2)`.
- **Use validators for cross-field logic**, not for single-field constraints (those go on `Field`).

### FastAPI

- **Routers use `APIRouter(prefix="/...", tags=["..."])`.**
- **Path operations are typed:**

  ```python
  @router.get("/{account_id}", response_model=AccountRead)
  def get_account(account_id: uuid.UUID, db: Session = Depends(get_db)) -> Account:
      ...
  ```

- **`response_model=` is set explicitly** for response schema. FastAPI converts the returned ORM object via the schema's `from_attributes` config.
- **Dependencies use `Depends(...)`** as default values, never as decorators.
- **HTTP errors use `HTTPException(status_code=..., detail=...)`,** not raw `Response` objects.
- **Status codes:** `200` for reads, `201` for creates with body, `204` for deletes with no body, `404` for not found, `403` for unauthorized access to another user's data, `422` for validation failures (FastAPI does this automatically).

### Routers

- **Routers parse input, call services, return output.** No business logic, no DB queries directly in route handlers (other than trivial ones).
- **Services live in `app/services/`** and own their DB queries + business logic.
- **Pandas only in service layer**, never in routers.

### Naming

- **`snake_case`** for variables, functions, modules.
- **`PascalCase`** for classes.
- **`UPPER_SNAKE`** for constants and enum values defined in module scope. (Enum *members* themselves are `snake_case` for `str, Enum` because they're the wire values.)
- **Module names:** singular for model modules (`account.py`, `transaction.py`), plural for collections of utilities (`schemas/common.py`).

### Error handling

- **Use specific exceptions.** `HTTPException(404)` not `Exception("not found")`.
- **Don't swallow exceptions silently.** Always log or re-raise.
- **Database constraint violations** (`IntegrityError`) get caught at the service layer and re-raised as appropriate `HTTPException` instances.

### Tests

- **`pytest` + FastAPI's `TestClient`.**
- **Fixtures in `conftest.py`** for shared setup (test DB, test client, factory functions).
- **One test file per router/service module.** `test_accounts.py` for `routers/accounts.py`.
- **Test patterns to cover per endpoint:**
  - Happy path
  - Validation failure (bad input)
  - Not found (`404`)
  - Cross-tenant access (`403` — accessing another user's data)
- **Use Faker** for realistic test data, not hardcoded values.

## TypeScript / JavaScript (later phases)

### General

- **Strict TypeScript.** `tsconfig.json` with `"strict": true` and friends.
- **No `any`.** Use `unknown` and narrow, or define a proper type.
- **Functional components**, hooks, no classes.
- **Single named export per file** for components.

### Imports (TypeScript)

- **Order:** React → third-party → `@/` aliased → relative.
- **Use absolute imports (`@/components/Foo`) within `apps/web`**, not deep relatives.

### State

- **TanStack Query** for server state. Never put server data in local state without a clear reason.
- **`useState` / `useReducer`** for UI-only state.
- **No Redux** unless we have an extremely good reason. Most apps don't.

### Naming (TypeScript)

- **`camelCase`** for variables and functions.
- **`PascalCase`** for components and types.
- **`kebab-case`** for filenames except components, which match their export name (`AccountList.tsx`).

## Git

- **Conventional commits** preferred but not strict:
  - `feat:` new feature
  - `fix:` bug fix
  - `refactor:` no behavior change
  - `docs:` documentation only
  - `chore:` tooling, deps
  - `test:` adding tests
- **One concept per commit.** Migrations + schema changes + tests can be one commit; mixing unrelated work isn't.
- **Always commit migrations with the model change** that produced them.
- **Never commit `.env`, `cdk.out/`, `node_modules/`, `.venv/`.** (Gitignored.)

## Documentation

- **Docstrings on public functions** that aren't obviously self-explanatory.
- **One-line comments are fine; long comments are a smell** — extract the logic into a well-named function.
- **Type hints are documentation.** A function with `-> Account | None` doesn't need to say "returns the account or None if not found".
