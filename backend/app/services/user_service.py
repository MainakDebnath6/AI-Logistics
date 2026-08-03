"""Business logic for user operations."""

from uuid import UUID

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Coordinate user persistence and business rules."""

    def __init__(self, repository: UserRepository) -> None:
        """Initialize the service with a user repository."""

        self.repository = repository

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user record."""

        user = User(
            full_name=user_data.full_name,
            email=str(user_data.email),
            hashed_password=hash_password(user_data.password),
            role=user_data.role,
            is_active=True,
        )
        return self.repository.create(user)

    def get_user(self, user_id: UUID) -> User | None:
        """Return a user by identifier."""

        return self.repository.get_by_id(user_id)

    def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Return users with pagination."""

        return self.repository.get_all(skip=skip, limit=limit)

    def update_user(self, user_id: UUID, user_data: UserUpdate) -> User | None:
        """Update the mutable fields for a user."""

        user = self.repository.get_by_id(user_id)
        if user is None:
            return None

        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        if user_data.role is not None:
            user.role = user_data.role
        if user_data.is_active is not None:
            user.is_active = user_data.is_active

        return self.repository.update(user)

    def delete_user(self, user_id: UUID) -> User | None:
        """Delete a user by identifier."""

        user = self.repository.get_by_id(user_id)
        if user is None:
            return None

        self.repository.delete(user)
        return user