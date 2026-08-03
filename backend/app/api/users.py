"""User API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Build a user service for the active database session."""

    return UserService(UserRepository(db))


@router.get("/", response_model=list[UserResponse])
def list_users(user_service: UserService = Depends(get_user_service)) -> list[User]:
    """Return all users."""

    return user_service.list_users()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, user_service: UserService = Depends(get_user_service)) -> User:
    """Return one user by identifier."""

    user = user_service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, user_service: UserService = Depends(get_user_service)) -> User:
    """Create a new user."""

    return user_service.create_user(payload)