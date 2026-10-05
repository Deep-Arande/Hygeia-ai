"""Timezone helpers.

All day-boundary logic uses the user's own stored IANA timezone — never server/UTC
time — per the design doc's strict-midnight rule.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo


def user_local_now(tz: str) -> datetime:
    """Current time in the user's timezone."""
    return datetime.now(ZoneInfo(tz))


def user_local_date(tz: str) -> date:
    """Today's calendar date in the user's timezone."""
    return user_local_now(tz).date()
