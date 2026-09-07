"""High-level customer-portal semantics and payload validation helpers."""

from datetime import time
from enum import Enum, IntFlag
from math import floor
from typing import Iterable, List, Optional, Sequence, cast

from .types import JSONDict, JSONValue


class NotificationPreference(IntFlag):
    """Known notification-subscription bits used by the current portal."""

    USAGE_ALERT = 1
    BUDGET = 2
    GENERAL = 4
    CONNECTION = 8
    BATTERY = 16
    DEVICE_MOVED = 32


KNOWN_NOTIFICATION_PREFERENCE_MASK = sum(int(value) for value in NotificationPreference)


def _portal_round(value: float) -> int:
    """Match JavaScript Math.round for the non-negative portal form values."""
    return int(floor(value + 0.5))


class DoNotAlertWeekday(str, Enum):
    """Weekday keys used by the portal's weekly Do Not Alert form."""

    SUNDAY = "SU"
    MONDAY = "MO"
    TUESDAY = "TU"
    WEDNESDAY = "WE"
    THURSDAY = "TH"
    FRIDAY = "FR"
    SATURDAY = "SA"


class BudgetPeriod(str, Enum):
    """Budget recurrence types exposed by the customer portal."""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


def unknown_notification_preference_bits(mask: int) -> int:
    """Return subscription bits not named by the current portal bundle."""
    return int(mask) & ~KNOWN_NOTIFICATION_PREFERENCE_MASK


def set_notification_preference_bit(
    mask: int,
    preference: NotificationPreference,
    enabled: bool,
) -> int:
    """Toggle one known preference while preserving every unrelated/unknown bit."""
    value = int(preference)
    if value not in {int(item) for item in NotificationPreference}:
        raise ValueError("preference must be one known notification bit")
    return (int(mask) | value) if enabled else (int(mask) & ~value)


def _validate_name(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must contain at least one non-whitespace character")
    if len(name) > 32:
        raise ValueError("name must be between 1 and 32 characters")
    return name


def build_usage_alert_rule_payload(
    name: str,
    flow_rate: float,
    duration: int,
    *,
    notify_every: Optional[int] = None,
    active: bool = True,
    shutoff_active: Optional[bool] = None,
    advanced_low_flow: bool = False,
) -> JSONDict:
    """Build a portal-valid usage-alert rule payload.

    ``duration`` and ``notify_every`` are minutes. The frontend's custom-rule
    form limits duration to 23h59m and repeat notifications to 13d23h. The live
    API additionally requires a custom rule's repeat interval to be at least
    twice its duration. When omitted, ``notify_every`` therefore defaults to
    exactly ``2 * duration`` instead of the backend-invalid value zero. For the
    built-in Smart Leak rule (``advanced_low_flow=True``), the portal omits
    name, flow-rate, and shutoff fields when editing it.
    """
    if duration < 5 or duration > (23 * 60 + 59):
        raise ValueError("duration must be between 5 and 1439 minutes")
    if notify_every is None:
        effective_notify_every = 0 if advanced_low_flow else 2 * duration
    else:
        effective_notify_every = int(notify_every)
    if effective_notify_every < 0 or effective_notify_every > (13 * 24 * 60 + 23 * 60):
        raise ValueError("notify_every must be between 0 and 20100 minutes")
    if not advanced_low_flow and effective_notify_every < 2 * duration:
        raise ValueError("notify_every must be at least twice duration")

    payload: JSONDict = {
        "active": bool(active),
        "duration": int(duration),
        "notify_every": effective_notify_every,
        "advanced_low_flow": bool(advanced_low_flow),
    }
    if advanced_low_flow:
        return payload

    _validate_name(name)
    numeric_flow = float(flow_rate)
    if numeric_flow < 0 or numeric_flow > 40.9:
        raise ValueError("flow_rate must be between 0 and 40.9 gallons/minute")
    payload["name"] = name
    payload["flow_rate"] = numeric_flow
    if shutoff_active is not None:
        payload["shutoff_config"] = {"active": bool(shutoff_active)}
    return payload


def build_smart_leak_rule_payload(
    duration: int,
    *,
    notify_every: int = 0,
    active: bool = True,
) -> JSONDict:
    """Build only the fields the portal edits on its built-in Smart Leak rule."""
    return build_usage_alert_rule_payload(
        "",
        0,
        duration,
        notify_every=notify_every,
        active=active,
        advanced_low_flow=True,
    )


def _normalize_time(value: str) -> str:
    try:
        parsed = time.fromisoformat(value)
    except ValueError as err:
        raise ValueError("time must use HH:MM or HH:MM:SS in 24-hour time") from err
    if parsed.tzinfo is not None:
        raise ValueError("time must not include a timezone offset")
    return parsed.strftime("%H:%M:%S")


def _schedule_duration_minutes(start_time: str, end_time: str) -> float:
    start = time.fromisoformat(start_time)
    end = time.fromisoformat(end_time)
    start_seconds = start.hour * 3600 + start.minute * 60 + start.second
    end_seconds = end.hour * 3600 + end.minute * 60 + end.second
    if end_seconds <= start_seconds:
        end_seconds += 24 * 3600
    return (end_seconds - start_seconds) / 60.0


def _weekday_values(weekdays: Iterable[object]) -> List[str]:
    valid = {item.value for item in DoNotAlertWeekday}
    result: List[str] = []
    for item in weekdays:
        value = item.value if isinstance(item, DoNotAlertWeekday) else str(item).upper()
        if value not in valid:
            raise ValueError("weekdays must use SU, MO, TU, WE, TH, FR, or SA")
        if value not in result:
            result.append(value)
    if not result:
        raise ValueError("at least one weekday is required")
    return result


def build_do_not_alert_schedule_payload(
    name: str,
    start_time: str,
    end_time: str,
    weekdays: Sequence[object],
    *,
    interval: int = 1,
    description: str = "",
    span_types: Optional[Sequence[str]] = None,
) -> JSONDict:
    """Build the weekly schedule object submitted by the portal form."""
    _validate_name(name)
    if interval < 1 or interval > 10:
        raise ValueError("interval must be between 1 and 10 weeks")
    normalized_start = _normalize_time(start_time)
    normalized_end = _normalize_time(end_time)
    if _schedule_duration_minutes(normalized_start, normalized_end) < 4:
        raise ValueError("end_time must be at least 4 minutes after start_time")
    day_values = _weekday_values(weekdays)

    payload: JSONDict = {
        "name": name,
        "description": description,
        "start_time": normalized_start,
        "end_time": normalized_end,
        "rrule_obj": {
            "tzid": "",
            "dtstart": "",
            "freq": "WEEKLY",
            "interval": int(interval),
            "byweekday": cast(JSONValue, day_values),
            "byhour": 0,
            "byminute": 0,
            "bysecond": 0,
        },
    }
    if span_types:
        values = [str(value) for value in span_types if str(value)]
        if values:
            payload["span_types"] = cast(JSONValue, values)
    return payload


def build_budget_payload(
    name: str,
    budget_type: BudgetPeriod,
    value: float,
    *,
    threshold_percentages: Sequence[float] = (75, 100),
    recur_multiplier: int = 1,
) -> JSONDict:
    """Build a budget payload using the portal's percentage-to-usage conversion."""
    _validate_name(name)
    numeric_value = float(value)
    if numeric_value < 1 or numeric_value > 1_000_000_000:
        raise ValueError("budget value must be between 1 and 1000000000")
    if recur_multiplier < 1:
        raise ValueError("recur_multiplier must be at least 1")
    percentages = [float(item) for item in threshold_percentages]
    if any(item <= 0 or item > 100 for item in percentages):
        raise ValueError("threshold percentages must be greater than 0 and at most 100")
    thresholds = [_portal_round(item * numeric_value / 100.0) for item in percentages]
    return cast(
        JSONDict,
        {
            "name": name,
            "type": budget_type.value,
            "value": numeric_value,
            "thresholds": thresholds,
            "recur_multiplier": int(recur_multiplier),
        },
    )


def build_emergency_contact_payload(contact_name: str, email_address: str) -> JSONDict:
    """Build the exact subscription payload used for portal emergency contacts."""
    _validate_name(contact_name)
    if not isinstance(email_address, str) or "@" not in email_address:
        raise ValueError("email_address must look like an email address")
    return {
        "contact_name": contact_name,
        "alert_info": {"type": "email", "info": email_address},
        "notification_types": int(NotificationPreference.USAGE_ALERT),
        "emergency_contact": True,
    }
