"""Gemini client wrapper, traced through Langfuse.

Every LLM call goes through `generate()`, which records a Langfuse generation
(nested under the per-message trace created in the service layer). All tracing is
best-effort — a tracing failure never breaks the actual LLM call.
"""

import time
from typing import Any

from ..config import settings
from ..observability import get_langfuse

_gemini = None


def get_gemini():
    """Lazily construct the google-genai client. Requires GEMINI_API_KEY."""
    global _gemini
    if _gemini is None:
        if not settings.gemini_enabled:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        from google import genai

        _gemini = genai.Client(api_key=settings.gemini_api_key)
    return _gemini


def _usage(response) -> dict[str, int]:
    um = getattr(response, "usage_metadata", None)
    if not um:
        return {}
    return {
        "input": um.prompt_token_count or 0,
        "output": um.candidates_token_count or 0,
        "total": um.total_token_count or 0,
    }


def _input_preview(contents: Any) -> Any:
    """Best-effort readable input for the trace (never raises)."""
    try:
        texts: list[str] = []
        for c in contents if isinstance(contents, list) else [contents]:
            if isinstance(c, str):
                texts.append(c)
            else:
                for part in getattr(c, "parts", []) or []:
                    if getattr(part, "text", None):
                        texts.append(part.text)
        return "\n".join(texts) if texts else str(contents)
    except Exception:  # noqa: BLE001
        return "<unserializable contents>"


def generate(*, contents: Any, config: Any, operation: str) -> tuple[Any, dict]:
    """Call Gemini and return (response, meta).

    meta = {"usage": {...}, "latency_ms": int, "model": str}.
    """
    client = get_gemini()
    lf = get_langfuse()
    start = time.perf_counter()

    gen_cm = None
    generation = None
    if lf is not None:
        try:
            gen_cm = lf.start_as_current_generation(
                name=operation,
                model=settings.gemini_model,
                input=_input_preview(contents),
                metadata={"prompt_version": settings.prompt_version},
            )
            generation = gen_cm.__enter__()
        except Exception:  # noqa: BLE001
            gen_cm = generation = None

    try:
        response = client.models.generate_content(
            model=settings.gemini_model, contents=contents, config=config
        )
        usage = _usage(response)
        if generation is not None:
            try:
                generation.update(output=getattr(response, "text", None), usage_details=usage)
            except Exception:  # noqa: BLE001
                pass
        return response, {
            "usage": usage,
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "model": settings.gemini_model,
        }
    finally:
        if gen_cm is not None:
            try:
                gen_cm.__exit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass
