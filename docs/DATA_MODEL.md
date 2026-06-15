# DATA_MODEL.md

Detailed reference for the budgeting app's data model. The SQLAlchemy models in `apps/api/app/models/` are the source of truth; this doc explains the reasoning behind them.

## Entity overview

| Entity | Purpose | Owns | Owned by |
| --- | --- | --- | --- |
| `User` | The person using the app | Accounts, Categories, Transactions, Budgets | — |
| `Account` | A bank/credit/cash account | Transactions | User |
| `Category` | A spending bucket (Groceries, Rent...) | — (referenced by Transactions, Budgets) | User; optionally another Category (parent) |
| `Transaction` | A single money movement | — | User, Account, optionally Category |
| `Budget` | A spending cap for a category over a period | — | User, Category |

## Entity details

### User

- `id: UUID` (PK)
- `email: str` (unique, indexed)
- `cognito_sub: str \| None` (unique, indexed) — links the local user to a Cognito identity
- `created_at: datetime` (timezone-aware, server-default `now()`)

**Why thin?** Auth lives in Cognito. The local user record exists only to anchor foreign keys for owned data and to give us a stable internal ID independent of any auth provider.

### Account

- `id: UUID` (PK)
- `user_id: UUID` (FK → users, CASCADE, indexed)
- `name: str` (max 100)
- `type: AccountType` enum: `checking | savings | credit | cash | investment`
- `current_balance: Decimal(12,2)` (default `0.00`)
- `currency: str(3)` (default `USD`, ISO 4217 format)
- `is_active: bool` (default true)
- `created_at: datetime`

**On balance:** `current_balance` is stored denormalized. The true balance is `SUM(transactions.amount)` for the account, but materializing it on the row makes account list endpoints fast. Update it transactionally whenever transactions are written/edited/deleted. (Phase 2/3 concern: how to keep this consistent — likely via a service layer that owns both transaction CRUD and balance updates.)

### Category

- `id: UUID` (PK)
- `user_id: UUID` (FK → users, CASCADE, indexed)
- `name: str` (max 100)
- `kind: CategoryKind` enum: `expense | income | transfer`
- `parent_id: UUID \| None` (self-FK, SET NULL on parent delete)
- `color: str(7) \| None` (hex like `#FF5733`)
- `is_archived: bool` (default false)
- `created_at: datetime`

**Hierarchical or flat?** The `parent_id` column supports nesting (e.g., "Food → Groceries", "Food → Dining"), but for v1 it's optional to actually use the hierarchy. Flat categories are simpler and most users don't use deep trees.

**Why archive instead of delete?** Deleting a category orphans every historical transaction referencing it. Archiving keeps history intact while hiding it from the UI.

### Transaction

- `id: UUID` (PK)
- `user_id: UUID` (FK → users, CASCADE, indexed)
- `account_id: UUID` (FK → accounts, CASCADE, indexed)
- `category_id: UUID \| None` (FK → categories, SET NULL, indexed)
- `amount: Decimal(12,2)` — signed: negative = outflow, positive = inflow
- `description: str(500)`
- `merchant: str(255) \| None`
- `occurred_on: date` — day-level, not timestamp
- `is_pending: bool` (default false) — for Plaid integration
- `external_id: str(255) \| None` (indexed) — Plaid transaction ID for dedup
- `notes: str(2000) \| None`
- `created_at: datetime`

**Composite index:** `ix_transactions_user_date` on `(user_id, occurred_on)` — the dominant query pattern is "show transactions for user X in date range Y".

**Why signed amounts instead of `direction + amount`?** A separate `direction` column requires every aggregation query to multiply by `CASE WHEN direction='out' THEN -1 ELSE 1 END`. Signed decimals just sum correctly. Display layer can `abs()` and label.

**Why `Date` not `Timestamp` for `occurred_on`?** Banks report at day granularity. Trying to store transaction times leads to timezone confusion across institutions.

### Budget

- `id: UUID` (PK)
- `user_id: UUID` (FK → users, CASCADE, indexed)
- `category_id: UUID` (FK → categories, CASCADE, indexed)
- `amount: Decimal(12,2)` (must be `> 0` — enforced at schema layer)
- `period: BudgetPeriod` enum: `weekly | monthly | yearly`
- `start_date: date`
- `created_at: datetime`

**No `end_date`.** A budget is ongoing until deleted; "budget vs. actual" calculations derive the current period from `period` + `start_date` + today.

## Enums (all `str, enum.Enum` for JSON-serializability)

```python
class AccountType(str, Enum):
    checking, savings, credit, cash, investment

class CategoryKind(str, Enum):
    expense, income, transfer

class BudgetPeriod(str, Enum):
    weekly, monthly, yearly
```

## Conventions across all tables

- **PK:** UUID via `uuid.uuid4` default. Postgres native UUID type with `as_uuid=True`.
- **Timestamps:** `DateTime(timezone=True)` with `server_default=func.now()`. Never naive datetimes.
- **Money:** `Numeric(12, 2)` in DB, `Decimal` in Python, `max_digits=12 decimal_places=2` in Pydantic.
- **Ownership FK:** Every table has `user_id` with `ON DELETE CASCADE`.
- **Soft references:** FKs to optional related entities use `ON DELETE SET NULL` (e.g., `category_id` on transaction).
- **String lengths:** Always set a `max_length` / `String(N)`. No unbounded strings.

## Open design questions (revisit later)

1. **Soft deletes?** No `is_deleted` flag right now. Most production apps soft-delete for audit recovery. Defer until needed.
2. **Multi-currency reports?** Schema supports per-account currency, but conversion (exchange rates, base currency reports) is not implemented. Defer until needed.
3. **Transfer transactions** (moving money between two accounts): Currently a single transaction row with `kind="transfer"` on the category. A double-entry approach (two transactions, one per account) is more correct but more complex. Start simple.
4. **Recurring transactions / scheduled budgets:** Not modeled. Would need a `recurrence` table or RRULE-style field. Phase 6+.
5. **Transaction splits** (one purchase across multiple categories): Not modeled. Would require a `transaction_splits` child table. Defer.

## Index strategy

- `users.email` — unique, indexed (lookup by email during auth)
- `users.cognito_sub` — unique, indexed (lookup by Cognito identity)
- `accounts.user_id` — indexed (list user's accounts)
- `categories.user_id` — indexed (list user's categories)
- `transactions.user_id` — indexed
- `transactions.account_id` — indexed (list transactions in account)
- `transactions.category_id` — indexed (budget aggregations)
- `transactions.external_id` — indexed (Plaid dedup)
- `transactions (user_id, occurred_on)` — composite, indexed (the dominant query)
- `budgets.user_id` — indexed
- `budgets.category_id` — indexed

When a new dominant query pattern emerges, add a matching index via a migration. Don't speculatively index everything — each index slows writes.
