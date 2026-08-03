"""User CRUD routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserResponse])
def list_users(session: Session = Depends(get_db)) -> list[UserResponse]:
    """Return all users."""

    return UserService().list_users(session)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, session: Session = Depends(get_db)) -> UserResponse:
    """Return one user by identifier."""

    return UserService().get_user(session, user_id)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, session: Session = Depends(get_db)) -> UserResponse:
    """Create a new user."""

    return UserService().create_user(session, payload)