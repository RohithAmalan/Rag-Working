"""Authentication models and schemas."""

from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    token_type: str = "bearer"
    username: str
    message: str = "Login successful"


class User(BaseModel):
    """User model."""
    username: str
    is_active: bool = True
