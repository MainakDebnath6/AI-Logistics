"""Authentication business logic for user registration and login."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse


class AuthService:
    """Coordinate user registration, login, and token creation."""

    def __init__(self, user_repository: UserRepository | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def register_user(self, session: Session, payload: UserCreate) -> UserResponse:
        """Create a new user account after validating uniqueness."""

        existing_user = self.user_repository.get_by_email(session, payload.email)
        if existing_user is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with that email already exists.")

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        created_user = self.user_repository.create(session, user)
        return UserResponse.model_validate(created_user)

    def authenticate_user(self, session: Session, payload: UserLogin) -> TokenResponse:
        """Validate credentials and return a JWT token response."""

        user = self.user_repository.get_by_email(session, payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")

        access_token = create_access_token(subject=str(user.id), additional_claims={"role": user.role.value})
        return TokenResponse(access_token=access_token)