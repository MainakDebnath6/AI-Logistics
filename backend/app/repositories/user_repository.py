"""Database access helpers for user persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Encapsulate SQLAlchemy operations for user records."""

    def create_user(self, session: Session, user: User) -> User:
        """Persist a new user and refresh the instance."""

        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    def get_by_id(self, session: Session, user_id: UUID) -> User | None:
        """Return a user by primary key if it exists."""

        return session.get(User, user_id)

    def get_by_email(self, session: Session, email: str) -> User | None:
        """Return a user by email address if it exists."""

        statement = select(User).where(User.email == email)
        return session.scalars(statement).first()

    def get_all(self, session: Session) -> list[User]:
        """Return all users ordered by newest first."""

        statement = select(User).order_by(User.created_at.desc())
        return list(session.scalars(statement).all())