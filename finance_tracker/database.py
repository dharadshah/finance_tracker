from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from contextlib import contextmanager
from typing import Generator

from finance_tracker.config import settings


class Base(DeclarativeBase):
    """
    Single declarative base shared by all ORM models.
    All models import from here — never create a second Base.
    """
    pass


def _create_engine():
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=settings.is_development,
    )

    # Enable WAL mode and foreign key enforcement for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine = _create_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Always use this — never instantiate SessionLocal directly.

    Usage:
        with get_session() as session:
            session.add(record)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """
    Create all tables if they do not exist.
    Called once at application startup.
    Safe to call multiple times — does not drop existing data.
    """
    import finance_tracker.models  # noqa: F401 — registers all models with Base
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
