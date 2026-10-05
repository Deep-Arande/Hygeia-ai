"""Agent tools: function declarations (what the model may call) and executors
(what actually writes to the DB). All DB writes in the system go through these.
"""

from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    ConfidenceTier,
    DaySession,
    ExerciseLog,
    FoodItem,
    FoodLog,
    MealType,
    User,
)
from ..time_utils import user_local_now

# --- Function declarations (JSON-schema form; google-genai accepts these directly) ---

LOG_FOOD_DECL = {
    "name": "log_food",
    "description": "Record food/drink the user reports eating. Call this whenever the "
    "message describes something consumed.",
    "parameters_json_schema": {
        "type": "object",
        "properties": {
            "meal_type": {
                "type": "string",
                "enum": ["breakfast", "lunch", "dinner", "snack", "other"],
                "description": "Best guess of the meal from context.",
            },
            "items": {
                "type": "array",
                "description": "One entry per distinct food/drink item.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit": {"type": "string", "description": "e.g. roti, katori, bowl, glass, g, ml"},
                        "calories": {"type": "number", "description": "Estimated kcal for this item."},
                        "protein_g": {"type": "number"},
                        "carbs_g": {"type": "number"},
                        "fat_g": {"type": "number"},
                        "fiber_g": {"type": "number"},
                    },
                    "required": ["name"],
                },
            },
        },
        "required": ["items"],
    },
}

LOG_EXERCISE_DECL = {
    "name": "log_exercise",
    "description": "Record physical activity/exercise the user reports doing.",
    "parameters_json_schema": {
        "type": "object",
        "properties": {
            "exercise_type": {"type": "string", "description": "e.g. walking, running, cycling, yoga"},
            "duration_min": {"type": "number"},
            "calories_burned": {"type": "number", "description": "Estimated kcal burned."},
        },
        "required": ["exercise_type"],
    },
}

FUNCTION_DECLARATIONS = [LOG_FOOD_DECL, LOG_EXERCISE_DECL]


def build_tools() -> list:
    """Build the google-genai Tool list from the declarations (lazy import)."""
    from google.genai import types

    return [types.Tool(function_declarations=FUNCTION_DECLARATIONS)]


# --- Executors ---


def _coerce_meal_type(value: Any) -> MealType | None:
    if value in {m.value for m in MealType}:
        return MealType(value)
    return None


def execute_log_food(
    db: Session, *, user: User, session: DaySession, raw_message: str, args: dict, trace_id: str | None = None
) -> dict:
    items = args.get("items") or []
    log = FoodLog(
        user_id=user.id,
        session_id=session.id,
        raw_message=raw_message,
        meal_type=_coerce_meal_type(args.get("meal_type")),
        confidence_tier=ConfidenceTier.high,  # Phase 1: single tier; tiers arrive in Phase 2
        confidence_score=1.0,
        log_date=session.session_date,
        logged_at=user_local_now(user.timezone),
        langfuse_trace_id=trace_id,
        prompt_version=settings.prompt_version,
    )
    db.add(log)
    db.flush()  # assign log.id

    names: list[str] = []
    total_calories = 0.0
    for it in items:
        item = FoodItem(
            food_log_id=log.id,
            name=it.get("name") or "item",
            quantity=it.get("quantity"),
            unit=it.get("unit"),
            calories=it.get("calories"),
            protein_g=it.get("protein_g"),
            carbs_g=it.get("carbs_g"),
            fat_g=it.get("fat_g"),
            fiber_g=it.get("fiber_g"),
        )
        db.add(item)
        names.append(item.name)
        if item.calories:
            total_calories += item.calories

    return {
        "food_log_id": log.id,
        "items": names,
        "total_calories": round(total_calories, 1),
        "meal_type": log.meal_type.value if log.meal_type else None,
    }


def execute_log_exercise(
    db: Session, *, user: User, session: DaySession, raw_message: str, args: dict, trace_id: str | None = None
) -> dict:
    log = ExerciseLog(
        user_id=user.id,
        session_id=session.id,
        raw_message=raw_message,
        exercise_type=args.get("exercise_type"),
        duration_min=args.get("duration_min"),
        calories_burned=args.get("calories_burned"),
        confidence_tier=ConfidenceTier.high,
        confidence_score=1.0,
        log_date=session.session_date,
        logged_at=user_local_now(user.timezone),
        langfuse_trace_id=trace_id,
        prompt_version=settings.prompt_version,
    )
    db.add(log)
    db.flush()
    return {
        "exercise_log_id": log.id,
        "exercise_type": log.exercise_type,
        "duration_min": log.duration_min,
        "calories_burned": log.calories_burned,
    }


TOOL_EXECUTORS = {
    "log_food": execute_log_food,
    "log_exercise": execute_log_exercise,
}
