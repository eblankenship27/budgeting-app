import uuid
from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, ForeignKey, create_engine, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry

from app.config import Settings, settings


class Base(DeclarativeBase):
    """Base class for all ORM models"""

    pass


class UserOwned:
    """A mixin class for user owned"""

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )


def make_engine(s: Settings) -> Engine:
    if not s.db_iam_auth:
        return create_engine(
            s.database_url,
            echo=settings.environment == "local",  # log SQL in dev
            pool_pre_ping=True,  # check connections are alive before using
        )

    import boto3  # imported only in AWS, so local runs and tests don't pay for it

    engine = create_engine(
        s.database_url,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )
    rds = boto3.client("rds")

    @event.listens_for(engine, "do_connect")
    def _use_iam_token(
        dialect: Dialect,
        conn_rec: ConnectionPoolEntry,
        cargs: tuple[Any, ...],
        cparams: dict[str, Any],
    ) -> None:
        cparams["password"] = rds.generate_db_auth_token(
            DBHostname=cparams["host"],
            Port=cparams.get("port", 5432),
            DBUsername=cparams["user"],
        )

    return engine


engine = make_engine(settings)

SessionLocal = sessionmaker(autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependancy for getting DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
