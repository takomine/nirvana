"""Time helpers. Everything internal is timezone-aware UTC; Manila is for display and plan dates."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

UTC = timezone.utc
MANILA = timezone(timedelta(hours=8), "Asia/Manila")


def now_utc() -> datetime:
    return datetime.now(UTC)


def parse_dt(value) -> datetime:
    """Accept a datetime, a date (midnight Manila) or an ISO string. Naive values are Manila time."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, time(0, 0))
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    else:
        raise ValueError(f"not a date/time: {value!r}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MANILA)
    return dt.astimezone(UTC)


def parse_date(value) -> date:
    if isinstance(value, datetime):
        return value.astimezone(MANILA).date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value.strip()[:10])
    raise ValueError(f"not a date: {value!r}")


def manila_date(dt: datetime) -> date:
    return dt.astimezone(MANILA).date()


def fmt_manila(dt: datetime) -> str:
    return dt.astimezone(MANILA).strftime("%Y-%m-%d %H:%M Manila")


def age_hours(then: datetime, now: datetime) -> float:
    return (now - then).total_seconds() / 3600.0
