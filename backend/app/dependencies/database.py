"""Database dependency wrapper for FastAPI route handlers."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.database import get_db as _get_db


def get_db() -> Generator[Session, None, None]:
    """Expose the shared SQLAlchemy session generator as a FastAPI dependency."""

    yield from _get_db()
