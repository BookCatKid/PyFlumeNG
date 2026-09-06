"""Portal-shaped Flume resource models.

The portal models are deliberately open rather than restrictive. Flume adds
fields over time, so known fields get typed/defaulted while every unrecognised
field is retained in the model and included by :meth:`to_dict`.
"""

from copy import deepcopy
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    ItemsView,
    KeysView,
    List,
    Mapping,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from .types import JSONDict, JSONValue, ResourceId

ModelT = TypeVar("ModelT", bound="FlumeModel")
ResponseT = TypeVar("ResponseT")
ModelFactory = Callable[[Mapping[str, Any]], "FlumeModel"]


class FlumeModel:
    """Open resource model compatible with both attributes and mappings."""

    defaults: ClassVar[Dict[str, Any]] = {}
    nested: ClassVar[Dict[str, ModelFactory]] = {}

    def __init__(
        self,
        value: Optional[Mapping[str, Any]] = None,
        **fields: Any,
    ) -> None:
        source = dict(value or {})
        source.update(fields)
        for key, default in self.defaults.items():
            setattr(self, key, deepcopy(default))
        for key, item in source.items():
            model = self.nested.get(key)
            if model is not None and item is not None:
                if isinstance(item, list):
                    item = [
                        model(value) if isinstance(value, Mapping) else value
                        for value in item
                    ]
                elif isinstance(item, Mapping):
                    item = model(item)
            setattr(self, key, item)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FlumeModel):
            return self.to_dict() == other.to_dict()
        return NotImplemented

    def keys(self) -> KeysView[str]:
        return self.to_dict().keys()

    def items(self) -> ItemsView[str, JSONValue]:
        return self.to_dict().items()

    def to_dict(self) -> JSONDict:
        result: Dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue
            if isinstance(value, FlumeModel):
                value = value.to_dict()
            elif isinstance(value, list):
                value = [
                    item.to_dict() if isinstance(item, FlumeModel) else item
                    for item in value
                ]
            result[key] = deepcopy(value)
        return cast(JSONDict, result)

    def update(self: ModelT, values: Mapping[str, Any]) -> ModelT:
        """Update model fields from a mapping and return the model."""
        for key, value in values.items():
            setattr(self, key, value)
        return self

    def __repr__(self) -> str:
        return "{0}({1!r})".format(type(self).__name__, self.to_dict())


class FlumeResponse(FlumeModel, Generic[ResponseT]):
    """Flume response envelope with typed data and preserved metadata."""

    success: bool
    code: Optional[int]
    message: Optional[str]
    http_code: Optional[int]
    http_message: Optional[str]
    detailed: JSONValue
    data: Union[ResponseT, List[ResponseT], JSONValue]
    count: int
    pagination: Optional[JSONDict]

    defaults = {
        "success": False,
        "code": None,
        "message": None,
        "http_code": None,
        "http_message": None,
        "detailed": None,
        "data": [],
        "count": 0,
        "pagination": None,
    }

    def __init__(
        self,
        value: Optional[Mapping[str, Any]] = None,
        model: Optional[Type[FlumeModel]] = None,
    ) -> None:
        super().__init__(value)
        if model is not None and isinstance(self.data, list):
            self.data = cast(
                Any,
                modelize(cast(List[Mapping[str, Any]], self.data), model),
            )
        elif model is not None and isinstance(self.data, Mapping):
            self.data = cast(Any, modelize(self.data, model))

    @property
    def next_url(self) -> Optional[str]:
        pagination = self.pagination or {}
        value = pagination.get("next")
        return value if isinstance(value, str) else None

    @property
    def previous_url(self) -> Optional[str]:
        pagination = self.pagination or {}
        value = pagination.get("prev")
        return value if isinstance(value, str) else None


class User(FlumeModel):
    """Portal user resource."""

    id: Optional[ResourceId]
    email_address: str
    first_name: str
    last_name: str
    type: Optional[str]
    phone: Optional[str]
    status: Optional[str]
    signup_datetime: Optional[str]

    defaults = {
        "id": None,
        "email_address": "",
        "first_name": "",
        "last_name": "",
        "type": None,
        "phone": None,
        "status": None,
        "signup_datetime": None,
    }

    @property
    def name(self) -> str:
        return " ".join(
            part for part in (self.first_name, self.last_name) if part
        ).strip()


class Location(FlumeModel):
    """Flume location/home resource."""

    id: Optional[ResourceId]
    user_id: Optional[ResourceId]
    name: str
    primary_location: bool
    address: Optional[str]
    address_2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    country: Optional[str]
    tz: Optional[str]
    installation: JSONValue
    insurer_id: Optional[ResourceId]
    building_type: Optional[str]
    away_mode: bool
    usage_profile: JSONValue

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
        "usage_profile": None,
    }


class Device(FlumeModel):
    """Flume bridge or water-sensor device."""

    id: Optional[ResourceId]
    type: Optional[int]
    location_id: Optional[ResourceId]
    user_id: Optional[ResourceId]
    bridge_id: Optional[ResourceId]
    name: Optional[str]
    description: Optional[str]
    registered: Optional[bool]
    added_datetime: Optional[str]
    oriented: bool
    last_seen: str
    connected: bool
    battery_level: Optional[float]
    product: JSONValue
    user: Optional[User]
    location: Optional[Location]

    defaults = {
        "id": None,
        "type": None,
        "location_id": None,
        "user_id": None,
        "bridge_id": None,
        "name": None,
        "description": None,
        "registered": None,
        "added_datetime": None,
        "oriented": False,
        "last_seen": "",
        "connected": False,
        "battery_level": None,
        "product": None,
        "user": None,
        "location": None,
    }
    nested = {"user": User, "location": Location}


class Notification(FlumeModel):
    """Portal notification resource."""

    id: Optional[ResourceId]
    device_id: Optional[ResourceId]
    user_id: Optional[ResourceId]
    type: Optional[str]
    message: str
    created_datetime: Optional[str]
    title: str
    read: bool
    extra: JSONValue
    event_rule: JSONValue

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

    id: Optional[ResourceId]
    device_id: Optional[ResourceId]
    triggered_datetime: Optional[str]
    flume_leak: bool
    query: JSONValue
    event_rule_name: Optional[str]

    defaults = {
        "id": None,
        "device_id": None,
        "triggered_datetime": None,
        "flume_leak": False,
        "query": None,
        "event_rule_name": None,
    }


class QueryResult(FlumeModel):
    """Query result whose keys are the caller-supplied request IDs."""


class CurrentFlow(FlumeModel):
    """Current flow-rate reading."""

    active: bool
    gpm: float
    datetime: Optional[str]

    defaults = {"active": False, "gpm": 0.0, "datetime": None}


class ShutoffConfig(FlumeModel):
    """Usage-alert shutoff configuration."""

    active: bool

    defaults = {"active": False}


class UsageAlertRule(FlumeModel):
    """Portal usage-alert rule, including portal-derived display helpers."""

    id: Optional[ResourceId]
    device_id: Optional[ResourceId]
    name: str
    active: bool
    flow_rate: float
    duration: int
    notify_every: int
    advanced_low_flow: bool
    shutoff_config: Optional[ShutoffConfig]
    schedules: List["DoNotAlertSchedule"]
    expected_usage_config: JSONValue
    descHTML: str
    notifyHTML: str

    defaults = {
        "id": None,
        "device_id": None,
        "name": "",
        "active": False,
        "flow_rate": 0.0,
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
    def duration_hour_min(self) -> Dict[str, int]:
        return {"hour": self.duration // 60, "min": self.duration % 60}

    @duration_hour_min.setter
    def duration_hour_min(self, value: Mapping[str, int]) -> None:
        self.duration = 60 * value["hour"] + value["min"]

    @property
    def notify_every_day_hour(self) -> Dict[str, int]:
        return {
            "day": self.notify_every // (60 * 24),
            "hour": (self.notify_every // 60) % 24,
        }

    @notify_every_day_hour.setter
    def notify_every_day_hour(self, value: Mapping[str, int]) -> None:
        self.notify_every = 24 * value["day"] * 60 + 60 * value["hour"]


class Budget(FlumeModel):
    """Daily, weekly, or monthly water budget."""

    id: Optional[ResourceId]
    name: str
    type: Optional[str]
    value: float
    thresholds: List[JSONValue]
    actual: Optional[float]

    defaults = {
        "id": None,
        "name": "",
        "type": None,
        "value": 0.0,
        "thresholds": [],
        "actual": None,
    }


class Subscription(FlumeModel):
    """Notification subscription or emergency contact."""

    id: Optional[ResourceId]
    user_id: Optional[ResourceId]
    alert_type: Optional[str]
    alert_info: JSONValue
    device_id: Optional[ResourceId]
    notification_types: int
    created_datetime: Optional[str]
    updated_datetime: Optional[str]
    emergency_contact: bool
    contact_name: Optional[str]

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

    def has_notification_type(self, notification_type: int) -> bool:
        return bool(self.notification_types & notification_type)

    def enable_notification_type(self, notification_type: int) -> None:
        self.notification_types |= notification_type

    def disable_notification_type(self, notification_type: int) -> None:
        self.notification_types &= ~notification_type


class DoNotAlertSchedule(FlumeModel):
    """Portal Do Not Alert schedule."""

    id: Optional[ResourceId]
    device_id: Optional[ResourceId]
    name: str
    description: str
    currently_active: bool
    start_time: str
    end_time: str
    last_start: str
    last_end: str
    next_start: str
    next_end: str
    span_types: List[JSONValue]
    rrule_str: str
    rrule_obj: JSONDict
    created_datetime: str
    updated_datetime: str

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
        "rrule_obj": {
            "tzid": "",
            "dtstart": "",
            "freq": "",
            "interval": 0,
            "byweekday": [],
            "byhour": 0,
            "byminute": 0,
            "bysecond": 0,
        },
        "created_datetime": "",
        "updated_datetime": "",
    }


class LocationAccess(FlumeModel):
    """Shared location access record."""

    id: Optional[ResourceId]
    user_id: Optional[ResourceId]
    location_id: Optional[ResourceId]
    email_address: Optional[str]

    defaults = {
        "id": None,
        "user_id": None,
        "location_id": None,
        "email_address": None,
    }


class Integration(FlumeModel):
    """External device integration, including shutoff valves."""

    id: Optional[ResourceId]
    type: Optional[str]
    state: JSONValue
    status: JSONValue
    device_id: Optional[ResourceId]

    defaults = {
        "id": None,
        "type": None,
        "state": None,
        "status": None,
        "device_id": None,
    }


class Span(FlumeModel):
    """Water-usage span/appliance classification."""

    id: Optional[ResourceId]
    device_id: Optional[ResourceId]
    type: Optional[str]
    start_datetime: Optional[str]
    end_datetime: Optional[str]

    defaults = {
        "id": None,
        "device_id": None,
        "type": None,
        "start_datetime": None,
        "end_datetime": None,
    }


class SpanType(FlumeModel):
    """Available span classification metadata."""

    id: Optional[ResourceId]
    name: Optional[str]
    type: Optional[str]
    display: JSONValue

    defaults = {"id": None, "name": None, "type": None, "display": None}


class Leak(FlumeModel):
    """Leak status or leak event."""

    id: Optional[ResourceId]
    device_id: Optional[ResourceId]
    active: bool
    created_datetime: Optional[str]

    defaults = {
        "id": None,
        "device_id": None,
        "active": False,
        "created_datetime": None,
    }


class PurchaseOption(FlumeModel):
    """Device purchase option exposed by the customer portal."""

    id: Optional[ResourceId]
    type: Optional[str]
    link: Optional[str]
    price: JSONValue

    defaults = {
        "id": None,
        "type": None,
        "link": None,
        "price": None,
    }


class Contact(FlumeModel):
    """Flume support contact information."""

    id: Optional[ResourceId]
    category: Optional[str]
    type: Optional[str]
    detail: JSONValue

    defaults = {"id": None, "category": None, "type": None, "detail": None}


class Insurer(FlumeModel):
    """Undocumented insurer metadata; all returned fields remain accessible."""


class ApiClient(FlumeModel):
    """Undocumented API-client metadata; all returned fields remain accessible."""


class ProService(FlumeModel):
    """Local professional service listing displayed by the portal."""

    name: Optional[str]
    url: Optional[str]

    defaults = {"name": None, "url": None}


class AccuracyResult(FlumeModel):
    """Meter-accuracy precheck or comparison result."""

    type: Optional[str]
    title: Optional[str]
    description: Optional[str]
    accuracy: Optional[float]
    since_url: Optional[str]
    until_url: Optional[str]
    reading_diff: Optional[float]
    queried_diff: Optional[float]

    defaults = {
        "type": None,
        "title": None,
        "description": None,
        "accuracy": None,
        "since_url": None,
        "until_url": None,
        "reading_diff": None,
        "queried_diff": None,
    }


class LocationProfiles(FlumeModel):
    """Appliance/profile metadata returned by ``/location-profiles``."""

    residents: JSONValue
    bathrooms: JSONValue
    indoor: List[JSONValue]
    outdoor: List[JSONValue]

    defaults = {"residents": None, "bathrooms": None, "indoor": [], "outdoor": []}


@overload
def modelize(value: List[Mapping[str, Any]], model: Type[ModelT]) -> List[ModelT]: ...


@overload
def modelize(value: Mapping[str, Any], model: Type[ModelT]) -> ModelT: ...


@overload
def modelize(value: JSONValue, model: None) -> JSONValue: ...


def modelize(value: Any, model: Optional[Type[ModelT]]) -> Any:
    """Convert API data to one model or a list of models."""
    if model is None:
        return value
    if isinstance(value, list):
        return [model(item) if not isinstance(item, model) else item for item in value]
    if isinstance(value, Mapping):
        return model(value)
    return value


# The portal constructs schedules as concrete models nested on usage rules.
UsageAlertRule.nested["schedules"] = DoNotAlertSchedule
