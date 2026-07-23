from fastapi import Depends, FastAPI
from mangum import Mangum
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers import accounts_router, budgets_router, categories_router, transactions_router

app = FastAPI(
    title="Budgeting API",
    version="0.1.0",
)

app.include_router(accounts_router)
app.include_router(categories_router)
app.include_router(transactions_router)
app.include_router(budgets_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def db_health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """Verify the database is working correctly"""
    result = db.execute(text("SELECT 1")).scalar()
    return {"status": "ok", "result": str(result)}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Budgeting API is running"}


# Lambda entrypoint — unused locally, used in phase 3
handler = Mangum(app)
