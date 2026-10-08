"""Authentication dependencies for JWT-protected endpoints."""

from app.core.security import decode_access_token
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenData
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


INVALID_CREDENTIALS = "Could not validate credentials."
INACTIVE_USER = "Inactive user."
INSUFFICIENT_PERMISSIONS = "Not enough permissions."


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail=INVALID_CREDENTIALS,
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the current user resolved from a validated JWT."""

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    try:
        token_data = TokenData.model_validate(payload)
    except ValidationError:
        raise credentials_exception

    repo = UserRepository(db)
    user = repo.get_by_email(token_data.email)

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=INACTIVE_USER,
        )

    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the current user only when they are an administrator."""

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=INSUFFICIENT_PERMISSIONS,
        )

    return current_user


def get_current_dispatcher(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the current user when they have dispatcher-level access."""

    if current_user.role not in {
        UserRole.ADMIN,
        UserRole.DISPATCHER,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=INSUFFICIENT_PERMISSIONS,
        )

    return current_user
