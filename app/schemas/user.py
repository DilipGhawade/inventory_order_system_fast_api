from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr = Field(description="Unique user email address")
    full_name: str = Field(min_length=2, max_length=150, description="Full legal or display name")


class UserCreate(UserBase):
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Strong password containing letters and digits",
    )
    

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one numeric digit.")
        if not any(char.isalpha() for char in v):
            raise ValueError("Password must contain at least one alphabetic character.")
        return v


class UserAdminCreate(UserCreate):
    role: UserRole = Field(default=UserRole.USER, description="Assigned system role")
    is_active: bool = Field(default=True, description="Whether the account is active")


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def validate_optional_password(cls, v: str | None) -> str | None:
        if v is not None:
            if not any(char.isdigit() for char in v):
                raise ValueError("Password must contain at least one numeric digit.")
            if not any(char.isalpha() for char in v):
                raise ValueError("Password must contain at least one alphabetic character.")
        return v


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime