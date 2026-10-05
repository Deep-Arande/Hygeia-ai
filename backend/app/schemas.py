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


# --- Chat (Phase 1) ---
class ChatRequest(BaseModel):
    user_id: int
    message: str


class ChatResponse(BaseModel):
    reply: str
