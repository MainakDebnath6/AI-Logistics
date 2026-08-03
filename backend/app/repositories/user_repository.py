"""Database access helpers for user persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Encapsulate SQLAlchemy operations for user records."""

    def __init__(self, db: Session) -> None:
        """Initialize the repository with an active database session."""

        self.db = db

    def create(self, user: User) -> User:
        """Persist a new user and return the stored ORM object."""

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: UUID) -> User | None:
        """Return a user by primary key if it exists."""

        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        """Return a user by email address if it exists."""

        statement = select(User).where(User.email == email)
        return self.db.scalars(statement).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Return users ordered by newest first with pagination."""

        statement = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(statement).all())

    def update(self, user: User) -> User:
        """Persist changes to an existing user and return the stored object."""

        updated_user = self.db.merge(user)
        self.db.commit()
        self.db.refresh(updated_user)
        return updated_user

    def delete(self, user: User) -> None:
        """Delete a user from the database."""

        persistent_user = self.db.merge(user)
        self.db.delete(persistent_user)
        self.db.commit()