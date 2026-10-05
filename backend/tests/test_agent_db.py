"""Tool-executor + session-service tests against the real database.

These exercise DB writes, so they need a configured database (Supabase). They
roll back, leaving no data behind, and auto-skip when no DB is configured
(e.g. in CI, which has no credentials).
"""

import pytest

from app.agent.tools import execute_log_exercise, execute_log_food
from app.config import settings
from app.db import SessionLocal
from app.models import ExerciseLog, FoodItem, FoodLog, User
from app.services.sessions import get_or_create_today_session

pytestmark = pytest.mark.skipif(not settings.runtime_database_url, reason="no database configured")


@pytest.fixture
def db():
    assert SessionLocal is not None
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()  # discard all test writes
        session.close()


def _make_user(db) -> User:
    user = User(email="pytest_agent@example.com", password_hash="x", timezone="Asia/Kolkata")
    db.add(user)
    db.flush()
    return user


def test_get_or_create_session_is_idempotent(db) -> None:
    user = _make_user(db)
    s1 = get_or_create_today_session(db, user)
    s2 = get_or_create_today_session(db, user)
    assert s1.id == s2.id


def test_log_food_writes_log_and_items(db) -> None:
    user = _make_user(db)
    session = get_or_create_today_session(db, user)
    result = execute_log_food(
        db,
        user=user,
        session=session,
        raw_message="2 rotis and a bowl of dal",
        args={
            "meal_type": "dinner",
            "items": [
                {"name": "roti", "quantity": 2, "unit": "roti", "calories": 160},
                {"name": "dal", "quantity": 1, "unit": "katori", "calories": 120},
            ],
        },
    )
    assert set(result["items"]) == {"roti", "dal"}
    assert result["total_calories"] == 280.0

    db.flush()  # autoflush is off; push pending FoodItems so we can query them
    log = db.get(FoodLog, result["food_log_id"])
    assert log.raw_message == "2 rotis and a bowl of dal"
    assert log.meal_type.value == "dinner"
    assert log.confidence_tier.value == "high"
    assert log.log_date == session.session_date

    items = db.query(FoodItem).filter_by(food_log_id=log.id).all()
    assert len(items) == 2


def test_log_exercise_writes_log(db) -> None:
    user = _make_user(db)
    session = get_or_create_today_session(db, user)
    result = execute_log_exercise(
        db,
        user=user,
        session=session,
        raw_message="went for a 30 min walk",
        args={"exercise_type": "walking", "duration_min": 30, "calories_burned": 120},
    )
    log = db.get(ExerciseLog, result["exercise_log_id"])
    assert log.exercise_type == "walking"
    assert log.duration_min == 30
    assert log.log_date == session.session_date
