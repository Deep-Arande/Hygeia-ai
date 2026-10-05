"""Agent orchestration: one user message → LLM → tool calls → DB writes → reply.

This is the live agent loop (Phase 1, happy path — single confidence tier, no
corrections/undo yet). Flow:

  1. get/create today's session, record the user message
  2. ask Gemini (with tools) to parse the message
  3. if it calls tools, execute them (DB writes) and feed results back
  4. get a short natural-language confirmation and record it

Everything is wrapped in one Langfuse trace per message (best-effort).
"""

from sqlalchemy.orm import Session

from ..config import settings
from ..models import LLMMonitoringLog, MessageRole, User
from ..observability import get_langfuse
from ..services.sessions import get_or_create_today_session, record_message
from .client import generate
from .prompts import SYSTEM_PROMPT
from .tools import TOOL_EXECUTORS, build_tools

_FALLBACK_REPLY = "Got it — logged."


def _log_llm(db: Session, user: User, meta: dict, operation: str, trace_id: str | None) -> None:
    usage = meta.get("usage") or {}
    db.add(
        LLMMonitoringLog(
            user_id=user.id,
            operation=operation,
            model=meta.get("model"),
            prompt_tokens=usage.get("input"),
            completion_tokens=usage.get("output"),
            total_tokens=usage.get("total"),
            latency_ms=meta.get("latency_ms"),
            success=True,
            langfuse_trace_id=trace_id,
            prompt_version=settings.prompt_version,
        )
    )


def _build_config():
    from google.genai import types

    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=build_tools(),
        temperature=0.3,
        # We drive the tool loop manually (executors need DB context), so disable
        # the SDK's automatic function calling.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def _run_agent(db: Session, user: User, session, text: str, trace_id: str | None) -> str:
    from google.genai import types

    config = _build_config()
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=text)])]

    response, meta = generate(contents=contents, config=config, operation="chat.parse")
    _log_llm(db, user, meta, "chat.parse", trace_id)

    function_calls = response.function_calls or []

    # Nothing to log — plain conversational reply.
    if not function_calls:
        reply = getattr(response, "text", None) or "How can I help you log your meals or workouts?"
        record_message(db, session=session, user=user, role=MessageRole.assistant, content=reply, trace_id=trace_id)
        return reply

    # Execute each tool call (DB writes) and collect responses for the model.
    tool_result_parts = []
    for fc in function_calls:
        args = dict(fc.args or {})
        executor = TOOL_EXECUTORS.get(fc.name)
        if executor is None:
            result = {"error": f"unknown tool: {fc.name}"}
        else:
            result = executor(db, user=user, session=session, raw_message=text, args=args, trace_id=trace_id)
        record_message(
            db,
            session=session,
            user=user,
            role=MessageRole.tool,
            tool_name=fc.name,
            tool_calls={"name": fc.name, "args": args, "result": result},
            trace_id=trace_id,
        )
        tool_result_parts.append(types.Part.from_function_response(name=fc.name, response=result))

    # Feed tool results back for a natural-language confirmation.
    contents.append(response.candidates[0].content)
    contents.append(types.Content(role="user", parts=tool_result_parts))

    confirm_response, confirm_meta = generate(contents=contents, config=config, operation="chat.confirm")
    _log_llm(db, user, confirm_meta, "chat.confirm", trace_id)

    reply = getattr(confirm_response, "text", None) or _FALLBACK_REPLY
    record_message(db, session=session, user=user, role=MessageRole.assistant, content=reply, trace_id=trace_id)
    return reply


def process_message(db: Session, user: User, text: str) -> str:
    """Handle one user message end-to-end; returns the assistant's reply."""
    session = get_or_create_today_session(db, user)
    record_message(db, session=session, user=user, role=MessageRole.user, content=text)

    lf = get_langfuse()
    root_cm = None
    trace_id = None
    if lf is not None:
        try:
            root_cm = lf.start_as_current_span(name="chat_message", input=text)
            root_cm.__enter__()
            trace_id = lf.get_current_trace_id()
        except Exception:  # noqa: BLE001
            root_cm = None

    try:
        reply = _run_agent(db, user, session, text, trace_id)
        if root_cm is not None:
            try:
                root_cm.__exit__(None, None, None)
                root_cm = None
            except Exception:  # noqa: BLE001
                pass
        db.commit()
        return reply
    except Exception:
        db.rollback()
        raise
    finally:
        if root_cm is not None:
            try:
                root_cm.__exit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass
        if lf is not None:
            try:
                lf.flush()
            except Exception:  # noqa: BLE001
                pass
