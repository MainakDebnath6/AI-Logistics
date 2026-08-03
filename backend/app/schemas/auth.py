"""Pydantic schemas for authentication payloads and JWT tokens."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class LoginRequest(BaseModel):
    """Credentials used to request an access token."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT access token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded JWT payload fields used by the application."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
