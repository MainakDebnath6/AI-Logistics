"""Pydantic schemas for user CRUD operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    """Shared user fields."""

    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    """Payload used to create a new user account."""

    hashed_password: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.DRIVER
    is_active: bool = True


class UserUpdate(BaseModel):
    """Payload used to update an existing user account."""

    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=255)
    hashed_password: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """Public user representation returned by API endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
