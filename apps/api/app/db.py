import uuid
from collections.abc import Generator

from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models"""

    pass


class UserOwned:
    """A mixin class for user owned"""

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )


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
