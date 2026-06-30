"""Authentication models and schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request schema."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username for authentication",
        examples=["admin", "demo", "user"],
    )
    password: str = Field(
        ...,
        min_length=4,
        max_length=100,
        description="User password",
        examples=["admin123", "demo123", "user123"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"username": "admin", "password": "admin123"},
                {"username": "demo", "password": "demo123"},
            ]
        }
    }


class LoginResponse(BaseModel):
    """Login response schema."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    username: str
    roles: list[str] = Field(
        default_factory=list, description="User roles (admin, user, etc.)"
    )
    message: str = "Login successful"


class User(BaseModel):
    """User model."""

    username: str
    roles: list[str] = Field(default_factory=list, description="User roles")
    is_active: bool = True
