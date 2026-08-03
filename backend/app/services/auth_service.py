"""Authentication business logic for user registration and login."""

from app.core.security import (create_access_token, hash_password,
                               verify_password)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate


class AuthService:
    """Coordinate user registration and login flows."""

    def __init__(self, repository: UserRepository) -> None:
        """Initialize the service with a user repository."""

        self.repository = repository

    def register(self, user_data: UserCreate) -> User:
        """Register a new user after enforcing email uniqueness."""

        existing_user = self.repository.get_by_email(str(user_data.email))
        if existing_user is not None:
            raise ValueError("Email already registered.")

        user = User(
            full_name=user_data.full_name,
            email=str(user_data.email),
            hashed_password=hash_password(user_data.password),
            role=user_data.role,
            is_active=True,
        )
        return self.repository.create(user)

    def login(self, login_data: LoginRequest) -> Token:
        """Authenticate a user and return a signed access token."""

        user = self.repository.get_by_email(str(login_data.email))
        if user is None:
            raise ValueError("Invalid email or password.")

        if not verify_password(login_data.password, user.hashed_password):
            raise ValueError("Invalid email or password.")

        access_token = create_access_token(
            data={
                "user_id": str(user.id),
                "email": str(user.email),
                "role": user.role.value,
            }
        )
        return Token(access_token=access_token, token_type="bearer")
