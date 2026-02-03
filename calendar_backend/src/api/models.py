from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password (min 6 chars)")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class AuthResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")


class EventBase(BaseModel):
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description/details")
    start: datetime = Field(..., description="Event start datetime (ISO)")
    end: datetime = Field(..., description="Event end datetime (ISO)")
    all_day: bool = Field(False, description="Whether the event is all-day")
    reminder_minutes_before: Optional[int] = Field(
        None, ge=0, le=10080, description="Reminder time in minutes before start (max 7 days)"
    )


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Event title")
    description: Optional[str] = Field(None, description="Event description/details")
    start: Optional[datetime] = Field(None, description="Event start datetime (ISO)")
    end: Optional[datetime] = Field(None, description="Event end datetime (ISO)")
    all_day: Optional[bool] = Field(None, description="Whether the event is all-day")
    reminder_minutes_before: Optional[int] = Field(
        None, ge=0, le=10080, description="Reminder time in minutes before start (max 7 days)"
    )


class EventOut(EventBase):
    id: str = Field(..., description="Event id")
    user_id: str = Field(..., description="Owner user id")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
