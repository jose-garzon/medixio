"""Datetimes are timezone-aware UTC in code and DB, shown in Bogotá time."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from medixio.config import get_settings


def local_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().tz_display)


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(local_tz())


def from_local(dt: datetime) -> datetime:
    """Local (naive or aware) datetime -> aware UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=local_tz())
    return dt.astimezone(UTC)


def local_at(day: date, at: time) -> datetime:
    """UTC datetime for `day` at local time `at`."""
    return from_local(datetime.combine(day, at))


def fmt_local(dt: datetime) -> str:
    return to_local(dt).strftime("%Y-%m-%d %H:%M")


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    for d in (day.day, 30, 29, 28):
        try:
            return date(year, month, d)
        except ValueError:
            continue
    raise ValueError(day)


def add_business_days(day: date, days: int) -> date:
    """Weekdays only; Colombian holidays are not accounted for."""
    current = day
    while days > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days -= 1
    return current


def today_local() -> date:
    return to_local(utcnow()).date()
