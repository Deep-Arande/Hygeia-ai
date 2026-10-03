"""FastAPI application entrypoint."""

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text

from .api import users
from .config import settings
from .db import engine

app = FastAPI(title=settings.app_name)

app.include_router(users.router)


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
