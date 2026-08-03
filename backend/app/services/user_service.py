"""Business logic for user CRUD operations."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserResponse, UserUpdate


class UserService:
    """Coordinate user creation and retrieval use-cases."""

    def __init__(self, user_repository: UserRepository | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def create_user(self, session: Session, payload: UserCreate) -> UserResponse:
        """Create a user after checking that the email is unique."""

        existing_user = self.user_repository.get_by_email(session, payload.email)
        if existing_user is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with that email already exists.")

        user = User(
            full_name=payload.full_name,
            email=payload.email,
            hashed_password=payload.hashed_password,
            role=payload.role,
            is_active=payload.is_active,
        )
        created_user = self.user_repository.create_user(session, user)
        return UserResponse.model_validate(created_user)

    def get_user(self, session: Session, user_id: UUID) -> UserResponse:
        """Return a single user by identifier."""

        user = self.user_repository.get_by_id(session, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        return UserResponse.model_validate(user)

    def list_users(self, session: Session) -> list[UserResponse]:
        """Return all users in the system."""

        users = self.user_repository.get_all(session)
        return [UserResponse.model_validate(user) for user in users]