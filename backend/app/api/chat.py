"""Chat endpoint — the live agent entrypoint (Phase 1). Requires authentication."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..agent.service import process_message
from ..config import settings
from ..db import get_db
from ..dependencies import get_current_user
from ..models import User
from ..schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    if not settings.gemini_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Gemini is not configured — set GEMINI_API_KEY in the environment.",
        )
    reply = process_message(db, current_user, payload.message)
    return ChatResponse(reply=reply)
