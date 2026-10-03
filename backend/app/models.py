"""SQLAlchemy models — the full Phase 0 data model (all 10 tables).

Tables: users, sessions, conversation_messages, food_logs, food_items,
exercise_logs, daily_summaries, user_memory, reports, llm_monitoring_logs.

Traceability columns (langfuse_trace_id, prompt_version) live on food_logs,
conversation_messages and reports from day one, per the design doc.
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


# --- Enums ---
class ConfidenceTier(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class MealType(str, enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"
    other = "other"


class ReportType(str, enum.Enum):
    weekly = "weekly"
    monthly = "monthly"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    tool = "tool"
    system = "system"


# --- Mixin ---
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# --- Users ---
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120))
    # IANA timezone, e.g. "Asia/Kolkata". Every midnight-cutoff check uses this, never UTC.
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, server_default="Asia/Kolkata")
    goals: Mapped[dict | None] = mapped_column(JSONB)
    health_conditions: Mapped[dict | None] = mapped_column(JSONB)

    sessions: Mapped[list["DaySession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    memory: Mapped["UserMemory | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


# --- Sessions (one row per calendar day per user) ---
class DaySession(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Idempotency flag for the midnight EOD job (safe retries, no double-counting).
    memory_summarized: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    user: Mapped["User"] = relationship(back_populates="sessions")

    __table_args__ = (UniqueConstraint("user_id", "session_date", name="uq_sessions_user_date"),)


# --- Conversation messages (full chat history incl. tool calls) ---
class ConversationMessage(Base, TimestampMixin):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole, name="message_role"), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    tool_name: Mapped[str | None] = mapped_column(String(100))
    tool_calls: Mapped[dict | None] = mapped_column(JSONB)  # tool calls + parameters recorded
    # Traceability
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(100), index=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50))


# --- Food logs (raw message always kept) ---
class FoodLog(Base, TimestampMixin):
    __tablename__ = "food_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"), index=True)
    raw_message: Mapped[str] = mapped_column(Text, nullable=False)  # always stored, reprocessable
    meal_type: Mapped[MealType | None] = mapped_column(SAEnum(MealType, name="meal_type"))
    confidence_tier: Mapped[ConfidenceTier | None] = mapped_column(SAEnum(ConfidenceTier, name="confidence_tier"))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    # User-timezone calendar date — the single value the write-permission cutoff compares.
    log_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    logged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Traceability
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(100), index=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50))

    items: Mapped[list["FoodItem"]] = relationship(back_populates="food_log", cascade="all, delete-orphan")


# --- Food items (parsed items + macros/nutrients per log) ---
class FoodItem(Base, TimestampMixin):
    __tablename__ = "food_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    food_log_id: Mapped[int] = mapped_column(ForeignKey("food_logs.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(50))
    calories: Mapped[float | None] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    carbs_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)
    fiber_g: Mapped[float | None] = mapped_column(Float)
    micronutrients: Mapped[dict | None] = mapped_column(JSONB)

    food_log: Mapped["FoodLog"] = relationship(back_populates="items")


# --- Exercise logs ---
class ExerciseLog(Base, TimestampMixin):
    __tablename__ = "exercise_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"), index=True)
    raw_message: Mapped[str] = mapped_column(Text, nullable=False)
    exercise_type: Mapped[str | None] = mapped_column(String(120))
    duration_min: Mapped[float | None] = mapped_column(Float)
    calories_burned: Mapped[float | None] = mapped_column(Float)
    confidence_tier: Mapped[ConfidenceTier | None] = mapped_column(SAEnum(ConfidenceTier, name="confidence_tier"))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    log_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    logged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(100), index=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50))


# --- Daily summaries (aggregated totals; reports read these, not raw logs) ---
class DailySummary(Base, TimestampMixin):
    __tablename__ = "daily_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    summary_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_calories: Mapped[float | None] = mapped_column(Float)
    total_protein_g: Mapped[float | None] = mapped_column(Float)
    total_carbs_g: Mapped[float | None] = mapped_column(Float)
    total_fat_g: Mapped[float | None] = mapped_column(Float)
    total_fiber_g: Mapped[float | None] = mapped_column(Float)
    calories_burned: Mapped[float | None] = mapped_column(Float)
    meals_logged: Mapped[int | None] = mapped_column(Integer)
    exercises_logged: Mapped[int | None] = mapped_column(Integer)
    totals: Mapped[dict | None] = mapped_column(JSONB)  # extra aggregates

    __table_args__ = (UniqueConstraint("user_id", "summary_date", name="uq_daily_summaries_user_date"),)


# --- User memory (one row per user; living profile) ---
class UserMemory(Base, TimestampMixin):
    __tablename__ = "user_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    food_preferences: Mapped[dict | None] = mapped_column(JSONB)
    usual_meals: Mapped[dict | None] = mapped_column(JSONB)
    eating_patterns: Mapped[dict | None] = mapped_column(JSONB)
    typical_calories: Mapped[dict | None] = mapped_column(JSONB)
    health_notes: Mapped[dict | None] = mapped_column(JSONB)
    misc: Mapped[dict | None] = mapped_column(JSONB)

    user: Mapped["User"] = relationship(back_populates="memory")


# --- Reports (weekly/monthly; generated once, never regenerated) ---
class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    report_type: Mapped[ReportType] = mapped_column(SAEnum(ReportType, name="report_type"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    detected_patterns: Mapped[dict | None] = mapped_column(JSONB)  # tagged by source
    ai_insights: Mapped[str | None] = mapped_column(Text)
    chart_data: Mapped[dict | None] = mapped_column(JSONB)
    # Traceability
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(100), index=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        UniqueConstraint("user_id", "report_type", "period_start", name="uq_reports_user_type_start"),
    )


# --- LLM monitoring logs (one row per AI call) ---
class LLMMonitoringLog(Base, TimestampMixin):
    __tablename__ = "llm_monitoring_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)  # e.g. food_parsing, eod_summary
    model: Mapped[str | None] = mapped_column(String(80))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 6))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Float)
    success: Mapped[bool | None] = mapped_column(Boolean)
    error: Mapped[str | None] = mapped_column(Text)
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(100), index=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50))
