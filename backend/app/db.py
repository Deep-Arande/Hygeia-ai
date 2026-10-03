"""SQLAlchemy engine, session factory, and declarative Base.

The runtime engine targets the Supabase pooler (transaction mode). Because the
transaction pooler does not support server-side prepared statements, we disable
psycopg3's auto-prepare (`prepare_threshold=None`). This is harmless on a direct
connection too, so it is always set.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def _normalize_url(url: str) -> str:
    """Force the psycopg3 driver regardless of how the URL is written."""
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


# Import here to avoid a circular import at module load of config.
from .config import settings  # noqa: E402

engine = None
SessionLocal: sessionmaker[Session] | None = None

if settings.runtime_database_url:
    engine = create_engine(
        _normalize_url(settings.runtime_database_url),
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},  # pooler-safe (transaction mode)
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL / DATABASE_POOL_URL is not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
