"""Pydantic schemas for users."""

from datetime import datetime
from uuid import UUID

from app.models.user import UserRole
from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    """Input used to create a user."""

    full_name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.DRIVER


class UserUpdate(BaseModel):
    """Input used to update a user."""

    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Public user representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
