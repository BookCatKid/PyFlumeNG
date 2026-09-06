"""Portal-shaped Flume resource models.

The portal models are deliberately open rather than restrictive. Flume adds
fields over time, so known fields get typed/defaulted while every unrecognised
field is retained in the model and included by :meth:`to_dict`.
"""

from copy import deepcopy


class FlumeModel:
    """Open resource model compatible with both attributes and mappings."""

    defaults = {}
    nested = {}

    def __init__(self, value=None, **fields):
        source = dict(value or {})
        source.update(fields)
        for key, default in self.defaults.items():
            setattr(self, key, deepcopy(default))
        for key, value in source.items():
            model = self.nested.get(key)
            if model is not None and value is not None:
                if isinstance(value, list):
                    value = [model(item) for item in value]
                elif isinstance(value, dict):
                    value = model(value)
            setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __eq__(self, other):
        if isinstance(other, FlumeModel):
            return self.to_dict() == other.to_dict()
        if isinstance(other, dict):
            return all(self.get(key) == value for key, value in other.items())
        return NotImplemented

    def keys(self):
        return self.to_dict().keys()

    def items(self):
        return self.to_dict().items()

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue
            if isinstance(value, FlumeModel):
                value = value.to_dict()
            elif isinstance(value, list):
                value = [item.to_dict() if isinstance(item, FlumeModel) else item for item in value]
            result[key] = deepcopy(value)
        return result

    def __repr__(self):
        return "{0}({1!r})".format(type(self).__name__, self.to_dict())


class User(FlumeModel):
    """Portal user resource."""

    defaults = {"id": None, "email_address": "", "first_name": "", "last_name": ""}

    @property
    def name(self):
        return " ".join(part for part in (self.first_name, self.last_name) if part).strip()


class Device(FlumeModel):
    """Flume bridge or water-sensor device."""

    defaults = {
        "id": None,
        "type": None,
        "location_id": None,
        "user_id": None,
        "bridge_id": None,
        "oriented": False,
        "last_seen": "",
        "connected": False,
        "battery_level": None,
        "product": None,
    }
    nested = {"user": User, "location": lambda value: Location(value)}


class Location(FlumeModel):
    """Flume location/home resource."""

    defaults = {
        "id": None,
        "user_id": None,
        "name": "",
        "primary_location": False,
        "address": None,
        "address_2": None,
        "city": None,
        "state": None,
        "postal_code": None,
        "country": None,
        "tz": None,
        "installation": None,
        "insurer_id": None,
        "building_type": None,
        "away_mode": False,
    }


class Notification(FlumeModel):
    """Portal notification resource."""

    defaults = {
        "id": None,
        "device_id": None,
        "user_id": None,
        "type": None,
        "message": "",
        "created_datetime": None,
        "title": "",
        "read": False,
        "extra": None,
        "event_rule": None,
    }


class UsageAlert(FlumeModel):
    """Triggered usage-alert event."""

    defaults = {
        "id": None,
        "device_id": None,
        "triggered_datetime": None,
        "flume_leak": False,
        "query": None,
        "event_rule_name": None,
    }


class QueryResult(FlumeModel):
    """A query result keyed by request ID with portal fields preserved."""


class CurrentFlow(FlumeModel):
    """Current flow-rate reading."""

    defaults = {"active": False, "gpm": 0, "datetime": None}


class ShutoffConfig(FlumeModel):
    """Usage-alert shutoff configuration."""

    defaults = {"active": False}


class UsageAlertRule(FlumeModel):
    """Portal usage-alert rule, including portal-derived display helpers."""

    defaults = {
        "id": None,
        "device_id": None,
        "name": "",
        "active": False,
        "flow_rate": 0,
        "duration": 0,
        "notify_every": 0,
        "advanced_low_flow": False,
        "shutoff_config": None,
        "schedules": [],
        "expected_usage_config": None,
        "descHTML": "",
        "notifyHTML": "",
    }
    nested = {"shutoff_config": ShutoffConfig}

    @property
    def duration_hour_min(self):
        return {"hour": self.duration // 60, "min": self.duration % 60}

    @duration_hour_min.setter
    def duration_hour_min(self, value):
        self.duration = 60 * value["hour"] + value["min"]

    @property
    def notify_every_day_hour(self):
        return {
            "day": self.notify_every // (60 * 24),
            "hour": (self.notify_every // 60) % 24,
        }

    @notify_every_day_hour.setter
    def notify_every_day_hour(self, value):
        self.notify_every = 24 * value["day"] * 60 + 60 * value["hour"]


class Budget(FlumeModel):
    """Daily, weekly, or monthly water budget."""

    defaults = {
        "id": None,
        "name": "",
        "type": None,
        "value": 0,
        "thresholds": [],
        "actual": None,
    }


class Subscription(FlumeModel):
    """Notification subscription or emergency contact."""

    defaults = {
        "id": None,
        "user_id": None,
        "alert_type": None,
        "alert_info": None,
        "device_id": None,
        "notification_types": 0,
        "created_datetime": None,
        "updated_datetime": None,
        "emergency_contact": False,
        "contact_name": None,
    }

    def has_notification_type(self, notification_type):
        return bool(self.notification_types & notification_type)

    def enable_notification_type(self, notification_type):
        self.notification_types |= notification_type

    def disable_notification_type(self, notification_type):
        self.notification_types &= ~notification_type


class DoNotAlertSchedule(FlumeModel):
    """Portal Do Not Alert schedule."""

    defaults = {
        "id": None,
        "device_id": None,
        "name": "",
        "description": "",
        "currently_active": False,
        "start_time": "",
        "end_time": "",
        "last_start": "",
        "last_end": "",
        "next_start": "",
        "next_end": "",
        "span_types": [],
        "rrule_str": "",
        "rrule_obj": {"tzid": "", "dtstart": "", "freq": "", "interval": 0, "byweekday": [], "byhour": 0, "byminute": 0, "bysecond": 0},
        "created_datetime": "",
        "updated_datetime": "",
    }


class LocationAccess(FlumeModel):
    """Shared location access record."""

    defaults = {"id": None, "user_id": None, "location_id": None, "email_address": None}


class Integration(FlumeModel):
    """External device integration, including shutoff valves."""

    defaults = {"id": None, "type": None, "state": None, "status": None, "device_id": None}


class Span(FlumeModel):
    """Water-usage span/appliance classification."""

    defaults = {"id": None, "device_id": None, "type": None, "start_datetime": None, "end_datetime": None}


class SpanType(FlumeModel):
    """Available span classification metadata."""

    defaults = {"id": None, "name": None, "type": None, "display": None}


class Leak(FlumeModel):
    """Leak status or leak event."""

    defaults = {"id": None, "device_id": None, "active": False, "created_datetime": None}


class PurchaseOption(FlumeModel):
    """Device purchase option."""


class Contact(FlumeModel):
    """Flume support contact information."""

    defaults = {"id": None, "category": None, "type": None, "detail": None}


class Insurer(FlumeModel):
    """Insurer metadata."""


class ApiClient(FlumeModel):
    """Generated Personal API client metadata."""


class LocationProfiles(FlumeModel):
    """Appliance/profile metadata returned by `/location-profiles`."""

    defaults = {"residents": None, "bathrooms": None, "indoor": [], "outdoor": []}


def modelize(value, model):
    """Convert API data to one model or a list of models."""
    if model is None:
        return value
    if isinstance(value, list):
        return [model(item) if not isinstance(item, model) else item for item in value]
    if isinstance(value, dict):
        return model(value)
    return value
