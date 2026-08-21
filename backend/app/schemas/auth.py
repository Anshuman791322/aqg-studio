"""Pydantic schemas for authentication and user profile endpoints."""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class UserQuotaSummary(BaseModel):
    """Daily token and assessment quota usage."""

    today_requests: int = Field(default=0, description="Requests made today")
    today_input_tokens: int = Field(default=0, description="Input tokens used today")
    today_output_tokens: int = Field(default=0, description="Output tokens used today")
    today_assessments: int = Field(default=0, description="Assessments generated today")


class UserProfileData(BaseModel):
    """Authenticated user profile data."""

    user_id: uuid.UUID
    email: str | None = None
    role: str = "authenticated"
    display_name: str | None = None
    app_metadata: dict[str, Any] = Field(default_factory=dict)
    user_metadata: dict[str, Any] = Field(default_factory=dict)
    quota: UserQuotaSummary = Field(default_factory=UserQuotaSummary)


class UserProfileResponse(BaseModel):
    """Canonical response envelope for user profile."""

    success: bool = True
    data: UserProfileData
