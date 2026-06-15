from fastapi import Depends, FastAPI
from mangum import Mangum
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

app = FastAPI(
    title="Budgeting API",
    version="0.1.0",
)


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
