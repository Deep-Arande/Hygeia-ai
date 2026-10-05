"""Session + conversation-message helpers.

One session per calendar day per user (the day is computed in the user's own
timezone). Every turn — user, assistant, and tool calls — is recorded.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import ConversationMessage, DaySession, MessageRole, User
from ..time_utils import user_local_date


def get_or_create_today_session(db: Session, user: User) -> DaySession:
    today = user_local_date(user.timezone)
    session = db.scalar(
        select(DaySession).where(DaySession.user_id == user.id, DaySession.session_date == today)
    )
    if session is None:
        session = DaySession(user_id=user.id, session_date=today)
        db.add(session)
        db.flush()
    return session


def record_message(
    db: Session,
    *,
    session: DaySession,
    user: User,
    role: MessageRole,
    content: str | None = None,
    tool_name: str | None = None,
    tool_calls: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> ConversationMessage:
    message = ConversationMessage(
        session_id=session.id,
        user_id=user.id,
        role=role,
        content=content,
        tool_name=tool_name,
        tool_calls=tool_calls,
        langfuse_trace_id=trace_id,
        prompt_version=settings.prompt_version,
    )
    db.add(message)
    db.flush()
    return message
