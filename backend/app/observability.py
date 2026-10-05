"""Langfuse client bootstrap.

Observability must never break the app: if Langfuse is not configured (no keys),
everything here no-ops and the agent runs normally.
"""

from .config import settings

_client = None
_initialized = False


def init_langfuse():
    """Initialize the global Langfuse client once, if keys are present."""
    global _client, _initialized
    if _initialized:
        return _client
    _initialized = True
    if not settings.langfuse_enabled:
        return None
    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception:  # noqa: BLE001 - never let tracing setup crash startup
        _client = None
    return _client


def get_langfuse():
    """Return the Langfuse client, initializing on first use. May be None."""
    if not _initialized:
        return init_langfuse()
    return _client
