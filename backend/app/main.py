"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text

from .api import chat, users
from .config import settings
from .db import engine
from .observability import init_langfuse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize tracing once at startup (no-ops if Langfuse keys are absent).
    init_langfuse()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(users.router)
app.include_router(chat.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    """Liveness check — does not touch the database."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/health/db", tags=["health"])
def health_db() -> dict:
    """Readiness check — verifies a round-trip to the database."""
    if engine is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Database not configured")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - surface the cause in the response
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Database error: {exc}") from exc
    return {"database": "ok"}
