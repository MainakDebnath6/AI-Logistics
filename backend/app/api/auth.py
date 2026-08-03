"""Authentication routes for user registration and JWT login."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_active_user
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register_user(payload: UserCreate, session: Session = Depends(get_db)) -> UserResponse:
    """Create a new user account."""

    return AuthService().register_user(session, payload)


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLogin, session: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate a user and return a bearer token."""

    return AuthService().authenticate_user(session, payload)


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """Return the authenticated user profile."""

    return UserResponse.model_validate(current_user)