from app.routers.accounts import router as accounts_router
from app.routers.budgets import router as budgets_router
from app.routers.categories import router as categories_router
from app.routers.transactions import router as transactions_router

__all__ = ["accounts_router", "budgets_router", "categories_router", "transactions_router"]
