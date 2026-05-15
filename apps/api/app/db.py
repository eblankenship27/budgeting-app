from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

class Base(DeclarativeBase):
    """Base class for all ORM models"""
    pass

engine = create_engine(
    settings.database_url,
    echo=settings.environment == "local",  # log SQL in dev
    pool_pre_ping=True,  # check connections are alive before using
)

SessionLocal = sessionmaker(autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependancy for getting DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()