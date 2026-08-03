"""SQLAlchemy 2.0 engine, session factory, and FastAPI database dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()

# Create a production-friendly engine with pre-ping enabled so stale connections
# are detected before use.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
)

# Session factory used by request handlers and background services.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and always close it after use."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
