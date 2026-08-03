"""User API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_admin, get_current_dispatcher
from app.dependencies.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Build a user service for the active database session."""

    return UserService(UserRepository(db))


@router.get("/", response_model=list[UserResponse])
def list_users(
    user_service: UserService = Depends(get_user_service),
    _current_user: object = Depends(get_current_dispatcher),
) -> list[UserResponse]:
    """Return all users."""

    return user_service.list_users()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    _current_user: object = Depends(get_current_dispatcher),
) -> UserResponse:
    """Return one user by identifier."""

    user = user_service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    user_service: UserService = Depends(get_user_service),
    _current_user: object = Depends(get_current_admin),
) -> UserResponse:
    """Create a new user."""

    return user_service.create_user(payload)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    _current_user: object = Depends(get_current_admin),
) -> UserResponse:
    """Update an existing user."""

    user = user_service.update_user(user_id, payload)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return user


@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    _current_user: object = Depends(get_current_admin),
) -> UserResponse:
    """Delete a user by identifier."""

    user = user_service.delete_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return user