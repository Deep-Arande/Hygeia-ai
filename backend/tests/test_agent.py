"""Agent unit tests that need neither a database nor an API key (CI-safe)."""

from datetime import date

from app.agent.tools import FUNCTION_DECLARATIONS, build_tools
from app.time_utils import user_local_date


def test_user_local_date_returns_date() -> None:
    assert isinstance(user_local_date("Asia/Kolkata"), date)


def test_tool_declarations_present() -> None:
    names = {d["name"] for d in FUNCTION_DECLARATIONS}
    assert names == {"log_food", "log_exercise"}


def test_build_tools_produces_declarations() -> None:
    tools = build_tools()
    assert tools
    decls = tools[0].function_declarations
    assert {d.name for d in decls} == {"log_food", "log_exercise"}
