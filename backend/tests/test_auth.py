"""Auth tests: token helpers + the register/login/me flow.

Token tests and the "chat needs auth" check are CI-safe (no DB). The full
register->login->me flow writes a user, so it is DB-guarded and cleans up.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.security import create_access_token, decode_access_token

client = TestClient(app)


# --- CI-safe ---
def test_token_roundtrip() -> None:
    token = create_access_token(123)
    assert decode_access_token(token)["sub"] == "123"


def test_chat_requires_auth() -> None:
    # No Authorization header -> 401 before any DB/LLM work.
    resp = client.post("/chat", json={"message": "hi"})
    assert resp.status_code == 401


# --- DB-guarded flow ---
db_required = pytest.mark.skipif(not settings.runtime_database_url, reason="no database configured")


@db_required
def test_register_login_me_flow() -> None:
    email = f"pytest_auth_{uuid.uuid4().hex[:8]}@example.com"
    password = "secret123"
    headers = None
    try:
        r = client.post(
            "/auth/register",
            json={"email": email, "password": password, "timezone": "Asia/Kolkata"},
        )
        assert r.status_code == 201, r.text

        # login uses OAuth2 form fields (username = email)
        r = client.post("/auth/login", data={"username": email, "password": password})
        assert r.status_code == 200, r.text
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        r = client.get("/auth/me", headers=headers)
        assert r.status_code == 200
        assert r.json()["email"] == email

        # wrong password is rejected
        assert client.post("/auth/login", data={"username": email, "password": "nope"}).status_code == 401
    finally:
        if headers:
            client.delete("/users/me", headers=headers)  # cleanup
