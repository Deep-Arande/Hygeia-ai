"""Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None
    timezone: str = "Asia/Kolkata"
    goals: dict | None = None
    health_conditions: dict | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    timezone: str | None = None
    goals: dict | None = None
    health_conditions: dict | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str | None
    timezone: str
    goals: dict | None
    health_conditions: dict | None
    created_at: datetime


# --- Auth ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Chat (Phase 1) ---
class ChatRequest(BaseModel):
    # The user is resolved from the bearer token, not the request body.
    message: str


class ChatResponse(BaseModel):
    reply: str
