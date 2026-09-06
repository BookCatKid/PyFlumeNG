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
    Set,
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
    _present_fields: Set[str]

    def __init__(
        self,
        value: Optional[Mapping[str, Any]] = None,
        **fields: Any,
    ) -> None:
        source = dict(value or {})
        source.update(fields)
        object.__setattr__(self, "_present_fields", set(source))
        for key, default in self.defaults.items():
            object.__setattr__(self, key, deepcopy(default))
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
            object.__setattr__(self, key, item)

    def __setattr__(self, key: str, value: Any) -> None:
        object.__setattr__(self, key, value)
        if key.startswith("_"):
            return
        present_fields = self.__dict__.get("_present_fields")
        if present_fields is not None:
            present_fields.add(key)

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
        present_fields = self._present_fields
        for key, value in self.__dict__.items():
            if key.startswith("_") or key not in present_fields:
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
            object.__setattr__(
                self,
                "data",
                cast(
                    Any,
                    modelize(cast(List[Mapping[str, Any]], self.data), model),
                ),
            )
        elif model is not None and isinstance(self.data, Mapping):
            object.__setattr__(self, "data", cast(Any, modelize(self.data, model)))

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
    invalidate_datetime: Optional[str]
    plan: Optional["UserPlan"]
    referral_link: Optional[str]

    defaults = {
        "id": None,
        "email_address": "",
        "first_name": "",
        "last_name": "",
        "type": None,
        "phone": None,
        "status": None,
        "signup_datetime": None,
        "invalidate_datetime": None,
        "plan": None,
        "referral_link": None,
    }

    @property
    def name(self) -> str:
        return " ".join(
            part for part in (self.first_name, self.last_name) if part
        ).strip()


class UserPlan(FlumeModel):
    """Subscription/entitlement details returned with portal user reads."""

    entitlement: str
    expire_datetime: Optional[str]
    frequency: Optional[str]
    one_time_purchase: bool
    origin: str
    prev_origin: Optional[str]
    price: Optional[Union[int, float, str]]
    renews: bool
    subscribed: bool
    trial: bool

    defaults = {
        "entitlement": "",
        "expire_datetime": None,
        "frequency": None,
        "one_time_purchase": False,
        "origin": "",
        "prev_origin": None,
        "price": None,
        "renews": False,
        "subscribed": False,
        "trial": False,
    }


User.nested["plan"] = UserPlan


class Coordinates(FlumeModel):
    """Latitude/longitude pair returned on portal location reads."""

    latitude: float
    longitude: float

    defaults = {"latitude": 0.0, "longitude": 0.0}


class LocationFeatures(FlumeModel):
    """Feature flags returned for a portal location."""

    compatible_meter: bool
    disaggregation: str
    free_batteries: str
    monthly_emails: bool
    use_profile_for_disag: bool

    defaults = {
        "compatible_meter": False,
        "disaggregation": "",
        "free_batteries": "",
        "monthly_emails": False,
        "use_profile_for_disag": False,
    }


class LocationProfile(FlumeModel):
    """Household fixture/profile values returned with portal locations."""

    residents: int
    bathrooms: int
    auto_fill_pool: bool
    bathtub: bool
    clothes_washer: bool
    dish_washer: bool
    drip_irrigation: bool
    evaporative_cooler: bool
    faucet: bool
    hose_irrigation: bool
    humidifier: bool
    ice_maker: bool
    manual_fill_pool: bool
    non_wifi_irrigation_controller: bool
    ro_system: bool
    shower: bool
    soaker_hose: bool
    sprinklers: bool
    toilet: bool
    water_softener: bool
    wifi_irrigation_controller: bool

    defaults = {
        "residents": 0,
        "bathrooms": 0,
        "auto_fill_pool": False,
        "bathtub": False,
        "clothes_washer": False,
        "dish_washer": False,
        "drip_irrigation": False,
        "evaporative_cooler": False,
        "faucet": False,
        "hose_irrigation": False,
        "humidifier": False,
        "ice_maker": False,
        "manual_fill_pool": False,
        "non_wifi_irrigation_controller": False,
        "ro_system": False,
        "shower": False,
        "soaker_hose": False,
        "sprinklers": False,
        "toilet": False,
        "water_softener": False,
        "wifi_irrigation_controller": False,
    }


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
    coords: Optional[Coordinates]
    geo: Optional[Coordinates]
    features: Optional[LocationFeatures]
    has_irrigation: bool
    has_pool: bool
    profile: Optional[LocationProfile]

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
        "coords": None,
        "geo": None,
        "features": None,
        "has_irrigation": False,
        "has_pool": False,
        "profile": None,
    }
    nested = {
        "coords": Coordinates,
        "geo": Coordinates,
        "features": LocationFeatures,
        "profile": LocationProfile,
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
    battery_level: Optional[str]
    product: Optional[str]
    supports_ap: bool
    supports_bluetooth: bool
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
        "supports_ap": False,
        "supports_bluetooth": False,
        "user": None,
        "location": None,
    }
    nested = {"user": User, "location": Location}


class Notification(FlumeModel):
    """Portal notification resource."""

    id: Optional[ResourceId]
    device_id: Optional[ResourceId]
    user_id: Optional[ResourceId]
    type: Optional[int]
    message: str
    created_datetime: Optional[str]
    title: str
    read: bool
    extra: Optional["NotificationExtra"]
    event_rule: JSONValue
    event_rule_id: Optional[int]
    event_triggered: bool

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
        "event_rule_id": None,
        "event_triggered": False,
    }


class NotificationQuery(FlumeModel):
    """Query metadata embedded in notification ``extra`` payloads."""

    bucket: str
    request_id: str
    since_datetime: str
    tz: str
    until_datetime: str

    defaults = {
        "bucket": "",
        "request_id": "",
        "since_datetime": "",
        "tz": "",
        "until_datetime": "",
    }


class NotificationExtra(FlumeModel):
    """Known fields in the portal notification ``extra`` object."""

    advanced_low_flow: bool
    budget_start: Optional[str]
    budget_type: Optional[str]
    event_rule_name: Optional[str]
    percentage: Optional[int]
    query: Optional[NotificationQuery]

    defaults = {
        "advanced_low_flow": False,
        "budget_start": None,
        "budget_type": None,
        "event_rule_name": None,
        "percentage": None,
        "query": None,
    }
    nested = {"query": NotificationQuery}


Notification.nested["extra"] = NotificationExtra


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


class UsageAlertSchedule(FlumeModel):
    """Compact schedule association nested in a usage-alert rule."""

    schedule_id: Optional[ResourceId]
    active: bool
    name: str
    description: str

    defaults = {
        "schedule_id": None,
        "active": False,
        "name": "",
        "description": "",
    }


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
    notification_type: Optional[str]
    shutoff_config: Optional[ShutoffConfig]
    schedules: List[UsageAlertSchedule]
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
        "notification_type": None,
        "shutoff_config": None,
        "schedules": [],
        "expected_usage_config": None,
        "descHTML": "",
        "notifyHTML": "",
    }
    nested = {
        "shutoff_config": ShutoffConfig,
        "schedules": UsageAlertSchedule,
    }

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
    value: Union[int, float]
    thresholds: List[int]
    actual: Optional[float]
    start_date: Optional[str]
    end_date: Optional[str]
    recur_multiplier: Optional[int]

    defaults = {
        "id": None,
        "name": "",
        "type": None,
        "value": 0.0,
        "thresholds": [],
        "actual": None,
        "start_date": None,
        "end_date": None,
        "recur_multiplier": None,
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
    span_types: List[str]
    rrule_str: str
    rrule_obj: "RecurrenceRule"
    created_datetime: str
    updated_datetime: Optional[str]

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
        "rrule_obj": None,
        "created_datetime": "",
        "updated_datetime": None,
    }


class RecurrenceRule(FlumeModel):
    """Recurrence fields returned in a Do Not Alert schedule."""

    tzid: str
    dtstart: str
    freq: str
    interval: int
    byweekday: List[str]
    byhour: int
    byminute: int
    bysecond: int

    defaults = {
        "tzid": "",
        "dtstart": "",
        "freq": "",
        "interval": 0,
        "byweekday": [],
        "byhour": 0,
        "byminute": 0,
        "bysecond": 0,
    }


DoNotAlertSchedule.nested["rrule_obj"] = RecurrenceRule


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


class SpanDataPoint(FlumeModel):
    """One time/value sample inside a portal water-usage span."""

    datetime: str
    value: Union[int, float]

    defaults = {
        "datetime": "",
        "value": 0.0,
    }


class Span(FlumeModel):
    """Water-usage span returned by the customer portal."""

    id: str
    type: str
    start: str
    end: str
    data: List[SpanDataPoint]
    is_editable: bool
    max_flowrate: float
    mode_gpm: float
    origin: str
    total: float
    value: float
    version: str

    defaults = {
        "id": "",
        "type": "",
        "start": "",
        "end": "",
        "data": [],
        "is_editable": False,
        "max_flowrate": 0.0,
        "mode_gpm": 0.0,
        "origin": "",
        "total": 0.0,
        "value": 0.0,
        "version": "",
    }


Span.nested["data"] = SpanDataPoint


class SpanType(FlumeModel):
    """Available span classification metadata."""

    name: str
    display_name: str
    labeled_as: str
    can_relabel: bool
    can_view: bool

    defaults = {
        "name": "",
        "display_name": "",
        "labeled_as": "",
        "can_relabel": False,
        "can_view": False,
    }


class Leak(FlumeModel):
    """Leak status or leak event."""

    id: Optional[ResourceId]
    device_id: Optional[ResourceId]
    active: bool
    created_datetime: Optional[str]
    expected_usage_config_enabled: bool
    suppressed: bool

    defaults = {
        "id": None,
        "device_id": None,
        "active": False,
        "created_datetime": None,
        "expected_usage_config_enabled": False,
        "suppressed": False,
    }


class PurchaseOption(FlumeModel):
    """Device purchase option exposed by the customer portal."""

    id: Optional[ResourceId]
    type: Optional[str]
    link: Optional[str]
    price: Optional[str]

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
    """Insurer metadata returned by the root insurer list."""

    id: Optional[ResourceId]
    name: str

    defaults = {"id": None, "name": ""}


class ApiClient(FlumeModel):
    """Undocumented API-client metadata; all returned fields remain accessible."""


class ProService(FlumeModel):
    """Local professional service listing displayed by the portal."""

    id: Optional[ResourceId]
    name: str
    description: str
    discount: int
    provider: str
    url: str

    defaults = {
        "id": None,
        "name": "",
        "description": "",
        "discount": 0,
        "provider": "",
        "url": "",
    }


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
