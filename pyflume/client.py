"""Complete resource client for documented and portal-discovered Flume routes."""

from typing import (
    Any,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)
from urllib.parse import urljoin

from requests import Response, Session

from .auth import FlumeAuth, FlumePortalAuth
from .constants import API_BASE_URL
from .errors import FlumeCapabilityError, FlumeHTTPError, FlumeRateLimitError
from .models import (
    AccuracyResult,
    ApiClient,
    Budget,
    Contact,
    CurrentFlow,
    Device,
    DoNotAlertSchedule,
    FlumeModel,
    FlumeResponse,
    Insurer,
    Integration,
    Leak,
    Location,
    LocationAccess,
    LocationProfiles,
    Notification,
    ProService,
    PurchaseOption,
    QueryResult,
    Span,
    SpanType,
    Subscription,
    UsageAlert,
    UsageAlertRule,
    User,
)
from .types import JSONDict, JSONValue, RequestParams, ResourceId

ModelT = TypeVar("ModelT", bound=FlumeModel)

DEFAULT_PORTAL_SPAN_TYPES: Tuple[str, ...] = (
    "OUTDOOR",
    "INDOOR",
    "SHOWER",
    "TOILET",
    "SOFTENER",
    "CLOTHES_WASHER",
    "DISH_WASHER",
    "POOL",
    "REVERSE_OSMOSIS",
)


class FlumeClient:
    """Call Flume endpoints with a PersonalAuth or PortalAuth object."""

    def __init__(
        self,
        auth: Union[FlumeAuth, FlumePortalAuth],
        http_session: Optional[Session] = None,
        base_url: str = API_BASE_URL,
        timeout: float = 30,
    ) -> None:
        self.auth: Union[FlumeAuth, FlumePortalAuth] = auth
        auth_session = getattr(auth, "_http_session", None)
        self._http_session: Session = http_session or (
            auth_session if isinstance(auth_session, Session) else Session()
        )
        self.base_url: str = base_url.rstrip("/")
        self.timeout: float = timeout
        self.last_response: Optional[Response] = None
        self.rate_limit = auth.rate_limit

    def request(
        self,
        method: str,
        path: str,
        params: Optional[RequestParams] = None,
        json: Optional[JSONValue] = None,
        data: Any = None,
        **kwargs: Any,
    ) -> JSONDict:
        """Return the complete Flume response envelope.

        A 401 is retried once after refreshing the auth object. All other
        errors retain the response envelope and are raised as typed errors.
        """
        url = (
            path
            if path.startswith("http")
            else urljoin(self.base_url + "/", path.lstrip("/"))
        )
        retried = False
        request_timeout = kwargs.pop("timeout", self.timeout)
        while True:
            self.auth.ensure_valid()
            response = self._http_session.request(
                method.upper(),
                url,
                headers=self.auth.authorization_header,
                params=cast(Any, params),
                json=json,
                data=data,
                timeout=request_timeout,
                **kwargs,
            )
            self.last_response = response
            if self.rate_limit is not None:
                self.rate_limit.update_from_headers(response.headers)
            try:
                envelope = response.json()
            except ValueError as exc:
                envelope = {}
                if response.status_code < 200 or response.status_code >= 300:
                    raise FlumeHTTPError(
                        "Flume returned a non-JSON error", response
                    ) from exc
            if response.status_code == 401 and not retried:
                self.auth.refresh()
                retried = True
                continue
            if response.status_code == 429:
                raise FlumeRateLimitError(
                    "Flume API rate limit exceeded", response, envelope
                )
            if response.status_code < 200 or response.status_code >= 300:
                raise FlumeHTTPError("Flume API request failed", response, envelope)
            return envelope

    @overload
    def data(
        self,
        method: str,
        path: str,
        model: Type[ModelT],
        **kwargs: Any,
    ) -> Union[ModelT, List[ModelT]]: ...

    @overload
    def data(
        self,
        method: str,
        path: str,
        model: None = None,
        **kwargs: Any,
    ) -> JSONValue: ...

    def data(
        self,
        method: str,
        path: str,
        model: Optional[Type[FlumeModel]] = None,
        **kwargs: Any,
    ) -> Any:
        """Return the response data parsed into portal-shaped models."""
        required_capability = kwargs.pop("requires_capability", None)
        if required_capability is not None:
            self._require_capability(required_capability)
        return self.response(method, path, model=model, **kwargs).data

    @overload
    def response(
        self,
        method: str,
        path: str,
        model: Type[ModelT],
        **kwargs: Any,
    ) -> FlumeResponse[ModelT]: ...

    @overload
    def response(
        self,
        method: str,
        path: str,
        model: None = None,
        **kwargs: Any,
    ) -> FlumeResponse[JSONValue]: ...

    def response(
        self,
        method: str,
        path: str,
        model: Optional[Type[FlumeModel]] = None,
        **kwargs: Any,
    ) -> FlumeResponse[Any]:
        """Return a typed Flume response envelope."""
        return FlumeResponse(self.request(method, path, **kwargs), model=model)

    def data_one(
        self,
        method: str,
        path: str,
        model: Type[ModelT],
        **kwargs: Any,
    ) -> Optional[ModelT]:
        """Return the first parsed resource, matching portal ``model()`` calls."""
        value = self.data(method, path, model, **kwargs)
        if isinstance(value, list):
            return value[0] if value else None
        return cast(Optional[ModelT], value)

    @overload
    def list_all(
        self,
        path: str,
        params: Optional[RequestParams],
        model: Type[ModelT],
    ) -> List[ModelT]: ...

    @overload
    def list_all(
        self,
        path: str,
        params: Optional[RequestParams] = None,
    ) -> List[FlumeModel]: ...

    def list_all(
        self,
        path: str,
        params: Optional[RequestParams] = None,
        model: Type[FlumeModel] = FlumeModel,
    ) -> Any:
        """Fetch every page from a paginated Flume list endpoint."""
        results: List[FlumeModel] = []
        for page in self.iter_pages(path, params=params, model=model):
            page_data = page.data or []
            if isinstance(page_data, list):
                results.extend(cast(List[FlumeModel], page_data))
            else:
                results.append(cast(FlumeModel, page_data))
        return results

    @overload
    def iter_pages(
        self,
        path: str,
        params: Optional[RequestParams],
        model: Type[ModelT],
    ) -> Iterator[FlumeResponse[ModelT]]: ...

    @overload
    def iter_pages(
        self,
        path: str,
        params: Optional[RequestParams] = None,
    ) -> Iterator[FlumeResponse[FlumeModel]]: ...

    def iter_pages(
        self,
        path: str,
        params: Optional[RequestParams] = None,
        model: Type[FlumeModel] = FlumeModel,
    ) -> Any:
        """Yield typed response envelopes for each page of a list endpoint.

        A repeated pagination link is treated as a server-side pagination
        failure and stops traversal instead of causing an infinite loop.
        """
        request_params = dict(params or {})
        request_params.setdefault("limit", 2000)
        request_params.setdefault("offset", 0)
        next_path: Optional[str] = path
        seen: Set[Tuple[str, Tuple[Tuple[str, str], ...]]] = set()
        while next_path:
            marker = (
                next_path,
                tuple(
                    sorted((key, repr(value)) for key, value in request_params.items())
                ),
            )
            if marker in seen:
                raise RuntimeError("Flume pagination returned a repeated next link")
            seen.add(marker)
            page = self.response("GET", next_path, model=model, params=request_params)
            yield page
            next_path = page.next_url
            request_params = {}

    def _user_path(self, suffix: str = "") -> str:
        return "/users/{0}{1}".format(self.auth.user_id, suffix)

    def _require_capability(self, capability: str) -> None:
        """Raise before transport when auth lacks a named capability."""
        if capability not in getattr(self.auth, "capabilities", frozenset()):
            raise FlumeCapabilityError(
                "This operation requires '{0}'. Use PortalAuth instead of "
                "PersonalAuth.".format(capability),
            )

    # Documented user, device, query, and flow routes.
    def get_user(self) -> Optional[User]:
        return self.data_one("GET", self._user_path(), User)

    def list_devices(self, **params: JSONValue) -> List[Device]:
        return self.list_all(self._user_path("/devices"), params, Device)

    def list_portal_devices(self, **params: JSONValue) -> List[Device]:
        """List devices using the user-scoped route with portal auth data."""
        return self.list_devices(**params)

    def get_device(
        self, device_id: ResourceId, **params: JSONValue
    ) -> Optional[Device]:
        return self.data_one(
            "GET",
            self._user_path("/devices/{0}".format(device_id)),
            Device,
            params=params,
        )

    def get_portal_device(
        self, device_id: ResourceId, **params: JSONValue
    ) -> Optional[Device]:
        """Fetch one device using the user-scoped route with portal auth data."""
        return self.get_device(device_id, **params)

    def query(self, device_id: ResourceId, payload: JSONDict) -> List[QueryResult]:
        return cast(
            List[QueryResult],
            self.data(
                "POST",
                self._user_path("/devices/{0}/query".format(device_id)),
                QueryResult,
                json=payload,
            ),
        )

    def portal_query(
        self, device_id: ResourceId, payload: JSONDict
    ) -> List[QueryResult]:
        """Run the read-only device query using the user-scoped route."""
        return self.query(device_id, payload)

    def get_current_flow(self, device_id: ResourceId) -> Optional[CurrentFlow]:
        return self.data_one(
            "GET",
            self._user_path("/devices/{0}/query/active".format(device_id)),
            CurrentFlow,
        )

    def get_portal_current_flow(self, device_id: ResourceId) -> Optional[CurrentFlow]:
        """Read current flow using the user-scoped route with portal auth."""
        return self.get_current_flow(device_id)

    # Locations and account mutations.
    def list_locations(self, **params: JSONValue) -> List[Location]:
        return self.list_all(self._user_path("/locations"), params, Location)

    def list_portal_locations(self, **params: JSONValue) -> List[Location]:
        """List locations using the user-scoped route with portal auth data."""
        return self.list_locations(**params)

    def get_location_profiles(self) -> Optional[LocationProfiles]:
        """Fetch the portal's appliance/profile metadata."""
        return self.data_one("GET", "/location-profiles", LocationProfiles)

    def get_location(self, location_id: ResourceId) -> Optional[Location]:
        return self.data_one(
            "GET", self._user_path("/locations/{0}".format(location_id)), Location
        )

    def get_portal_location(self, location_id: ResourceId) -> Optional[Location]:
        """Fetch one location using the user-scoped route with portal auth data."""
        return self.get_location(location_id)

    def create_location(self, payload: JSONDict) -> JSONValue:
        return self.data("POST", self._user_path("/locations"), json=payload)

    def create_portal_location(self, payload: JSONDict) -> JSONValue:
        """Create a location through the portal's root location route."""
        self._require_capability("portal_writes")
        return self.data("POST", "/locations", json=payload)

    def update_location(self, location_id: ResourceId, payload: JSONDict) -> JSONValue:
        return self.data(
            "PATCH", self._user_path("/locations/{0}".format(location_id)), json=payload
        )

    def update_portal_location(
        self, location_id: ResourceId, payload: JSONDict
    ) -> JSONValue:
        """Update a location through the portal's root location route."""
        self._require_capability("portal_writes")
        return self.data("PATCH", "/locations/{0}".format(location_id), json=payload)

    def update_user(self, payload: JSONDict) -> JSONValue:
        return self.data("PATCH", self._user_path(), json=payload)

    def update_portal_user(self, payload: JSONDict) -> JSONValue:
        """Update the current user through the portal's collection route."""
        self._require_capability("portal_writes")
        return self.data("PATCH", "/users/{0}".format(self.auth.user_id), json=payload)

    def update_password(self, payload: JSONDict) -> JSONValue:
        return self.data("PATCH", self._user_path("/password"), json=payload)

    def update_email(self, payload: JSONDict) -> JSONValue:
        return self.data("PATCH", self._user_path("/email"), json=payload)

    # Notifications, alerts, and rules.
    def list_notifications(self, **params: JSONValue) -> List[Notification]:
        return self.list_all(self._user_path("/notifications"), params, Notification)

    def list_portal_notifications(self, **params: JSONValue) -> List[Notification]:
        """List notifications using the user-scoped route with portal auth data."""
        return self.list_notifications(**params)

    def get_notification(self, notification_id: ResourceId) -> Optional[Notification]:
        return self.data_one(
            "GET",
            self._user_path("/notifications/{0}".format(notification_id)),
            Notification,
        )

    def get_portal_notification(
        self, notification_id: ResourceId
    ) -> Optional[Notification]:
        """Fetch one notification using the user-scoped route with portal auth."""
        return self.get_notification(notification_id)

    def update_notification(
        self, notification_id: ResourceId, payload: JSONDict
    ) -> JSONValue:
        return self.data(
            "PATCH",
            self._user_path("/notifications/{0}".format(notification_id)),
            json=payload,
        )

    def update_portal_notification(
        self,
        notification_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        """Update a notification through the portal's root route."""
        self._require_capability("portal_writes")
        return self.data(
            "PATCH", "/notifications/{0}".format(notification_id), json=payload
        )

    def delete_notification(self, notification_id: ResourceId) -> JSONValue:
        return self.data(
            "DELETE", self._user_path("/notifications/{0}".format(notification_id))
        )

    def delete_portal_notification(self, notification_id: ResourceId) -> JSONValue:
        """Delete a notification through the portal's root route."""
        self._require_capability("portal_writes")
        return self.data("DELETE", "/notifications/{0}".format(notification_id))

    def set_notification_read(
        self,
        notification_id: ResourceId,
        read: bool = True,
        portal: bool = True,
    ) -> JSONValue:
        """Set notification read state using the portal's frontend payload."""
        if portal:
            return self.update_portal_notification(
                notification_id, {"read": bool(read)}
            )
        return self.update_notification(notification_id, {"read": bool(read)})

    def list_usage_alerts(self, **params: JSONValue) -> List[UsageAlert]:
        return self.list_all(self._user_path("/usage-alerts"), params, UsageAlert)

    def list_event_rules(
        self,
        device_id: ResourceId,
        **params: JSONValue,
    ) -> List[UsageAlertRule]:
        return self.list_all(
            self._user_path("/devices/{0}/rules".format(device_id)),
            params,
            UsageAlertRule,
        )

    def list_usage_alert_rules(
        self,
        device_id: ResourceId,
        **params: JSONValue,
    ) -> List[UsageAlertRule]:
        return self.list_all(
            self._user_path("/devices/{0}/rules/usage-alerts".format(device_id)),
            params,
            UsageAlertRule,
        )

    def list_portal_usage_alert_rules(
        self,
        device_id: ResourceId,
        **params: JSONValue,
    ) -> List[UsageAlertRule]:
        """List usage rules using the user-scoped route with portal auth data."""
        return self.list_usage_alert_rules(device_id, **params)

    def get_usage_alert_rule(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
    ) -> Optional[UsageAlertRule]:
        return self.data_one(
            "GET",
            self._user_path(
                "/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id)
            ),
            UsageAlertRule,
        )

    def get_portal_usage_alert_rule(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
    ) -> Optional[UsageAlertRule]:
        """Fetch one usage rule using the user-scoped route with portal auth."""
        return self.get_usage_alert_rule(device_id, rule_id)

    def create_usage_alert_rule(
        self, device_id: ResourceId, payload: JSONDict
    ) -> JSONValue:
        return self.data(
            "POST",
            self._user_path("/devices/{0}/rules/usage-alerts".format(device_id)),
            json=payload,
        )

    def create_portal_usage_alert_rule(
        self,
        device_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        """Create a rule through the portal's root device route."""
        self._require_capability("portal_writes")
        return self.data(
            "POST", "/devices/{0}/rules/usage-alerts".format(device_id), json=payload
        )

    def update_usage_alert_rule(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        self._require_capability("portal_writes")
        return self.data(
            "PATCH",
            self._user_path(
                "/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id)
            ),
            json=payload,
        )

    def update_portal_usage_alert_rule(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        """Update a rule using the portal service's collection PATCH form."""
        self._require_capability("portal_writes")
        return self.data(
            "PATCH",
            "/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id),
            json=payload,
        )

    def delete_usage_alert_rule(
        self, device_id: ResourceId, rule_id: ResourceId
    ) -> JSONValue:
        return self.data(
            "DELETE",
            self._user_path(
                "/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id)
            ),
        )

    def delete_portal_usage_alert_rule(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
    ) -> JSONValue:
        """Delete a rule through the portal service's collection route."""
        self._require_capability("portal_writes")
        return self.data(
            "DELETE", "/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id)
        )

    def set_usage_alert_rule_active(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
        active: bool,
    ) -> JSONValue:
        return self.update_usage_alert_rule(
            device_id, rule_id, {"active": bool(active)}
        )

    def set_portal_usage_alert_rule_active(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
        active: bool,
    ) -> JSONValue:
        """Toggle a rule using the portal service's collection PATCH form."""
        self._require_capability("portal_writes")
        return self.update_portal_usage_alert_rule(
            device_id,
            rule_id,
            {"active": bool(active)},
        )

    def list_leaks(self, device_id: ResourceId) -> Optional[Leak]:
        return self.data_one(
            "GET", self._user_path("/devices/{0}/leaks/active".format(device_id)), Leak
        )

    def list_portal_leaks(self, device_id: ResourceId) -> List[Leak]:
        """Read active leaks through the portal's user-scoped route."""
        return cast(
            List[Leak],
            self.data(
                "GET",
                self._user_path("/devices/{0}/leaks/active".format(device_id)),
                Leak,
            ),
        )

    def get_leak(self, device_id: ResourceId, leak_id: ResourceId) -> Optional[Leak]:
        return self.data_one(
            "GET",
            self._user_path("/devices/{0}/leaks/{1}".format(device_id, leak_id)),
            Leak,
        )

    def get_portal_leak(
        self, device_id: ResourceId, leak_id: ResourceId
    ) -> Optional[Leak]:
        """Read one active leak through the portal's user-scoped route."""
        return self.data_one(
            "GET",
            self._user_path("/devices/{0}/leaks/{1}".format(device_id, leak_id)),
            Leak,
        )

    # Budgets and subscriptions.
    def list_budgets(self, device_id: ResourceId, **params: JSONValue) -> List[Budget]:
        return self.list_all(
            self._user_path("/devices/{0}/budgets".format(device_id)), params, Budget
        )

    def list_portal_budgets(
        self, device_id: ResourceId, **params: JSONValue
    ) -> List[Budget]:
        """List budgets using the user-scoped route with portal auth data."""
        return self.list_budgets(device_id, **params)

    def get_budget(
        self, device_id: ResourceId, budget_id: ResourceId
    ) -> Optional[Budget]:
        return self.data_one(
            "GET",
            self._user_path("/devices/{0}/budgets/{1}".format(device_id, budget_id)),
            Budget,
        )

    def get_portal_budget(
        self,
        device_id: ResourceId,
        budget_id: ResourceId,
    ) -> Optional[Budget]:
        """Fetch one budget using the user-scoped route with portal auth."""
        return self.get_budget(device_id, budget_id)

    def create_budget(self, device_id: ResourceId, payload: JSONDict) -> JSONValue:
        return self.data(
            "POST",
            self._user_path("/devices/{0}/budgets".format(device_id)),
            json=payload,
        )

    def create_portal_budget(
        self, device_id: ResourceId, payload: JSONDict
    ) -> JSONValue:
        """Create a budget through the portal's root device route."""
        return self.data("POST", "/devices/{0}/budgets".format(device_id), json=payload)

    def update_budget(
        self,
        device_id: ResourceId,
        budget_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        return self.data(
            "PATCH",
            self._user_path("/devices/{0}/budgets/{1}".format(device_id, budget_id)),
            json=payload,
        )

    def update_portal_budget(
        self,
        device_id: ResourceId,
        budget_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        """Update a budget using the portal service's collection PATCH form."""
        return self.data(
            "PATCH",
            "/devices/{0}/budgets/{1}".format(device_id, budget_id),
            json=payload,
        )

    def delete_budget(self, device_id: ResourceId, budget_id: ResourceId) -> JSONValue:
        return self.data(
            "DELETE",
            self._user_path("/devices/{0}/budgets/{1}".format(device_id, budget_id)),
        )

    def delete_portal_budget(
        self, device_id: ResourceId, budget_id: ResourceId
    ) -> JSONValue:
        """Delete a budget using the portal service's collection route."""
        return self.data(
            "DELETE", "/devices/{0}/budgets/{1}".format(device_id, budget_id)
        )

    def list_subscriptions(self, **params: JSONValue) -> List[Subscription]:
        return self.list_all(self._user_path("/subscriptions"), params, Subscription)

    def list_portal_subscriptions(self, **params: JSONValue) -> List[Subscription]:
        """List subscriptions using the user-scoped route with portal auth data."""
        return self.list_subscriptions(**params)

    def get_subscription(self, subscription_id: ResourceId) -> Optional[Subscription]:
        return self.data_one(
            "GET",
            self._user_path("/subscriptions/{0}".format(subscription_id)),
            Subscription,
        )

    def get_portal_subscription(
        self, subscription_id: ResourceId
    ) -> Optional[Subscription]:
        """Fetch a subscription using the user-scoped route with portal auth."""
        return self.get_subscription(subscription_id)

    def create_location_subscription(
        self,
        location_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        return self.data(
            "POST",
            self._user_path("/locations/{0}/subscriptions".format(location_id)),
            json=payload,
        )

    def create_portal_subscription(
        self,
        location_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        """Create a subscription through the portal's root location route."""
        return self.data(
            "POST", "/locations/{0}/subscriptions".format(location_id), json=payload
        )

    def update_subscription(
        self, subscription_id: ResourceId, payload: JSONDict
    ) -> JSONValue:
        return self.data(
            "PATCH",
            self._user_path("/subscriptions/{0}".format(subscription_id)),
            json=payload,
        )

    def update_portal_subscription(
        self,
        subscription_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        """Update a subscription through the portal's collection PATCH form."""
        return self.data(
            "PATCH", "/subscriptions/{0}".format(subscription_id), json=payload
        )

    def delete_subscription(self, subscription_id: ResourceId) -> JSONValue:
        return self.data(
            "DELETE", self._user_path("/subscriptions/{0}".format(subscription_id))
        )

    def delete_portal_subscription(self, subscription_id: ResourceId) -> JSONValue:
        """Delete a subscription through the portal's collection route."""
        return self.data("DELETE", "/subscriptions/{0}".format(subscription_id))

    def create_stripe_portal(self, return_url: str) -> JSONValue:
        return self.data(
            "POST", self._user_path("/stripe-portal"), json={"return_url": return_url}
        )

    def subscribe(self, return_url: str) -> JSONValue:
        return self.data(
            "POST", self._user_path("/subscribe"), json={"return_url": return_url}
        )

    # Portal-only usage schedules and shutoff configuration.
    def list_do_not_alert_schedules(
        self,
        device_id: ResourceId,
        **params: JSONValue,
    ) -> List[DoNotAlertSchedule]:
        return self.list_all(
            self._user_path("/devices/{0}/do-not-alert-schedules".format(device_id)),
            params,
            DoNotAlertSchedule,
        )

    def list_portal_do_not_alert_schedules(
        self,
        device_id: ResourceId,
        **params: JSONValue,
    ) -> List[DoNotAlertSchedule]:
        """List DNA schedules through the portal's user-scoped route."""
        return self.list_all(
            self._user_path("/devices/{0}/do-not-alert-schedules".format(device_id)),
            params,
            DoNotAlertSchedule,
        )

    def create_do_not_alert_schedule(
        self,
        device_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        return self.data(
            "POST",
            self._user_path("/devices/{0}/do-not-alert-schedules".format(device_id)),
            json=payload,
        )

    def create_portal_do_not_alert_schedule(
        self,
        device_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        """Create a DNA schedule using the portal payload."""
        return self.data(
            "POST",
            self._user_path("/devices/{0}/do-not-alert-schedules".format(device_id)),
            json=payload,
        )

    def update_do_not_alert_schedule(
        self,
        device_id: ResourceId,
        schedule_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        return self.data(
            "PATCH",
            self._user_path(
                "/devices/{0}/do-not-alert-schedules/{1}".format(device_id, schedule_id)
            ),
            json=payload,
        )

    def update_portal_do_not_alert_schedule(
        self,
        device_id: ResourceId,
        schedule_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        """Update a DNA schedule using the portal collection PATCH form."""
        return self.data(
            "PATCH",
            self._user_path(
                "/devices/{0}/do-not-alert-schedules/{1}".format(device_id, schedule_id)
            ),
            json=payload,
        )

    def delete_do_not_alert_schedule(
        self,
        device_id: ResourceId,
        schedule_id: ResourceId,
    ) -> JSONValue:
        return self.data(
            "DELETE",
            self._user_path(
                "/devices/{0}/do-not-alert-schedules/{1}".format(device_id, schedule_id)
            ),
        )

    def delete_portal_do_not_alert_schedule(
        self,
        device_id: ResourceId,
        schedule_id: ResourceId,
    ) -> JSONValue:
        """Delete a DNA schedule using the portal collection route."""
        return self.data(
            "DELETE",
            self._user_path(
                "/devices/{0}/do-not-alert-schedules/{1}".format(device_id, schedule_id)
            ),
        )

    def update_rule_schedules(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        return self.data(
            "PATCH",
            self._user_path(
                "/devices/{0}/rules/usage-alerts/{1}/do-not-alert-schedules".format(
                    device_id, rule_id
                )
            ),
            json=payload,
        )

    def toggle_usage_alert_schedule(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
        schedule_id: ResourceId,
        active: bool,
    ) -> JSONValue:
        """Associate a DNA schedule with a rule and set its active state."""
        path = self._user_path(
            "/devices/{0}/rules/usage-alerts/{1}/do-not-alert-schedules".format(
                device_id,
                rule_id,
            ),
        )
        return self.data(
            "PATCH",
            path,
            params={"id": schedule_id},
            json={"active": bool(active)},
        )

    def update_rule_shutoff_config(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        return self.data(
            "PATCH",
            self._user_path(
                "/devices/{0}/rules/usage-alerts/{1}/shutoff-config".format(
                    device_id, rule_id
                )
            ),
            json=payload,
        )

    # Sharing, integrations, diagnostics, and support endpoints discovered in the portal.
    def list_location_access(
        self,
        location_id: ResourceId,
        **params: JSONValue,
    ) -> List[LocationAccess]:
        return self.list_all(
            self._user_path("/locations/{0}/access".format(location_id)),
            params,
            LocationAccess,
        )

    def list_portal_location_access(
        self,
        location_id: ResourceId,
        **params: JSONValue,
    ) -> List[LocationAccess]:
        """List sharing records using the user-scoped route with portal auth."""
        return self.list_location_access(location_id, **params)

    def get_location_access(
        self,
        location_id: ResourceId,
        access_id: ResourceId,
    ) -> Optional[LocationAccess]:
        return self.data_one(
            "GET",
            self._user_path("/locations/{0}/access/{1}".format(location_id, access_id)),
            LocationAccess,
        )

    def get_portal_location_access(
        self,
        location_id: ResourceId,
        access_id: ResourceId,
    ) -> Optional[LocationAccess]:
        """Fetch a sharing record using the user-scoped route with portal auth."""
        return self.get_location_access(location_id, access_id)

    def grant_location_access(
        self, location_id: ResourceId, payload: JSONDict
    ) -> JSONValue:
        return self.data(
            "POST",
            self._user_path("/locations/{0}/access".format(location_id)),
            json=payload,
        )

    def grant_portal_location_access(
        self,
        location_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        """Grant sharing access through the portal's root location route."""
        return self.data(
            "POST", "/locations/{0}/access".format(location_id), json=payload
        )

    def revoke_location_access(
        self,
        location_id: ResourceId,
        access_id: ResourceId,
    ) -> JSONValue:
        return self.data(
            "DELETE",
            self._user_path("/locations/{0}/access/{1}".format(location_id, access_id)),
        )

    def revoke_portal_location_access(
        self,
        location_id: ResourceId,
        access_id: ResourceId,
    ) -> JSONValue:
        """Revoke sharing access through the portal collection route."""
        return self.data(
            "DELETE", "/locations/{0}/access/{1}".format(location_id, access_id)
        )

    def list_integrations(
        self, device_id: ResourceId, **params: JSONValue
    ) -> List[Integration]:
        return self.list_all(
            self._user_path("/devices/{0}/integrations".format(device_id)),
            params,
            Integration,
        )

    def list_portal_integrations(
        self,
        device_id: ResourceId,
        **params: JSONValue,
    ) -> List[Integration]:
        """List integrations through the portal's user-scoped route."""
        return self.list_all(
            self._user_path("/devices/{0}/integrations".format(device_id)),
            params,
            Integration,
        )

    def get_integration(
        self,
        device_id: ResourceId,
        integration_id: ResourceId,
    ) -> Optional[Integration]:
        return self.data_one(
            "GET",
            self._user_path(
                "/devices/{0}/integrations/{1}".format(device_id, integration_id)
            ),
            Integration,
        )

    def get_portal_integration(
        self,
        device_id: ResourceId,
        integration_id: ResourceId,
    ) -> Optional[Integration]:
        return self.data_one(
            "GET",
            self._user_path(
                "/devices/{0}/integrations/{1}".format(device_id, integration_id)
            ),
            Integration,
        )

    def command_integration(
        self,
        device_id: ResourceId,
        integration_id: ResourceId,
        state: JSONValue,
    ) -> JSONValue:
        return self.data(
            "POST",
            self._user_path(
                "/devices/{0}/integrations/{1}/command".format(
                    device_id, integration_id
                )
            ),
            json={"state": state},
        )

    def command_portal_integration(
        self,
        device_id: ResourceId,
        integration_id: ResourceId,
        state: JSONValue,
    ) -> JSONValue:
        return self.data(
            "POST",
            self._user_path(
                "/devices/{0}/integrations/{1}/command".format(
                    device_id, integration_id
                )
            ),
            json={"state": state},
        )

    def refresh_integration(
        self,
        device_id: ResourceId,
        integration_id: ResourceId,
    ) -> JSONValue:
        return self.data(
            "POST",
            self._user_path(
                "/devices/{0}/integrations/{1}/refresh".format(
                    device_id, integration_id
                )
            ),
            json={},
        )

    def refresh_portal_integration(
        self,
        device_id: ResourceId,
        integration_id: ResourceId,
    ) -> JSONValue:
        return self.data(
            "POST",
            self._user_path(
                "/devices/{0}/integrations/{1}/refresh".format(
                    device_id, integration_id
                )
            ),
            json={},
        )

    def delete_integration(
        self, device_id: ResourceId, integration_id: ResourceId
    ) -> JSONValue:
        return self.data(
            "DELETE",
            self._user_path(
                "/devices/{0}/integrations/{1}".format(device_id, integration_id)
            ),
        )

    def unlink_portal_integration(
        self,
        device_id: ResourceId,
        integration_id: Optional[ResourceId] = None,
        payload: Optional[JSONDict] = None,
    ) -> JSONValue:
        """Unlink an integration using the portal's collection DELETE form."""
        path = self._user_path("/devices/{0}/integrations".format(device_id))
        if integration_id is not None:
            path += "/{0}".format(integration_id)
        return self.data("DELETE", path, json=payload)

    def list_shutoff_integrations(self, device_id: ResourceId) -> List[Integration]:
        """List portal shutoff-valve integrations."""
        return self.list_all(
            self._user_path("/devices/{0}/integrations".format(device_id)),
            {"type": "SHUTOFF_VALVE"},
            Integration,
        )

    def list_spans(
        self,
        device_id: ResourceId,
        since_datetime: str,
        until_datetime: str,
        units: str = "gallons",
        span_types: Optional[Sequence[str]] = None,
    ) -> List[Span]:
        """List portal usage spans for a time range and classification set.

        ``since_datetime`` and ``until_datetime`` use the portal's
        ``YYYY-MM-DD HH:MM:SS`` format. When ``span_types`` is omitted, the
        same classification keys used by the current customer portal are sent.
        """
        selected_types = span_types or DEFAULT_PORTAL_SPAN_TYPES
        params: RequestParams = {
            "since_datetime": since_datetime,
            "until_datetime": until_datetime,
            "units": units,
            "types": ",".join(selected_types),
        }
        return self.list_all(
            self._user_path("/devices/{0}/spans".format(device_id)), params, Span
        )

    def update_span(
        self,
        device_id: ResourceId,
        span_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        return self.data(
            "PATCH",
            self._user_path("/devices/{0}/spans/{1}".format(device_id, span_id)),
            json=payload,
        )

    def update_span_type(
        self,
        device_id: ResourceId,
        span_id: ResourceId,
        span_type: str,
    ) -> JSONValue:
        """Set a span's type using the portal's exact payload shape."""
        return self.update_span(device_id, span_id, {"type": span_type})

    def list_span_types(
        self, location_id: ResourceId, **params: JSONValue
    ) -> List[SpanType]:
        return self.list_all(
            self._user_path("/locations/{0}/span-types".format(location_id)),
            params,
            SpanType,
        )

    def submit_feedback(self, device_id: ResourceId, payload: JSONDict) -> JSONValue:
        return self.data(
            "POST",
            self._user_path("/devices/{0}/feedback".format(device_id)),
            json=payload,
        )

    def submit_device_feedback(
        self, device_id: ResourceId, payload: JSONDict
    ) -> JSONValue:
        """Submit device feedback through the portal route."""
        return self.submit_feedback(device_id, payload)

    def get_meter_accuracy(self, device_id: ResourceId) -> List[AccuracyResult]:
        return cast(
            List[AccuracyResult],
            self.data(
                "GET",
                self._user_path("/devices/{0}/meters/accuracy".format(device_id)),
                AccuracyResult,
            ),
        )

    def submit_meter_accuracy(
        self, device_id: ResourceId, payload: JSONDict
    ) -> JSONValue:
        return self.data(
            "POST",
            self._user_path("/devices/{0}/meters/accuracy".format(device_id)),
            json=payload,
        )

    def submit_meter_accuracy_readings(
        self,
        device_id: ResourceId,
        since_datetime: str,
        until_datetime: str,
        since_reading: float,
        until_reading: float,
        since_image: str,
        until_image: str,
        units: str,
    ) -> JSONValue:
        """Submit the portal meter-accuracy form payload."""
        return self.submit_meter_accuracy(
            device_id,
            {
                "since_datetime": since_datetime,
                "until_datetime": until_datetime,
                "since_reading": since_reading,
                "until_reading": until_reading,
                "since_image": since_image,
                "until_image": until_image,
                "units": units,
            },
        )

    def initiate_accuracy_conversation(self, payload: JSONDict) -> JSONValue:
        return self.data(
            "POST", self._user_path("/initiate-accuracy-conversation"), json=payload
        )

    def start_accuracy_conversation(
        self,
        message: str,
        since_url: str,
        since_datetime: str,
        since_reading: float,
        until_url: str,
        until_datetime: str,
        until_reading: float,
        units: str,
        reading_diff: float,
        queried_diff: float,
        accuracy: float,
    ) -> JSONValue:
        """Start the portal's accuracy-support conversation payload."""
        return self.initiate_accuracy_conversation(
            {
                "message": message,
                "since_url": since_url,
                "since_datetime": since_datetime,
                "since_reading": since_reading,
                "until_url": until_url,
                "until_datetime": until_datetime,
                "until_reading": until_reading,
                "units": units,
                "reading_diff": reading_diff,
                "queried_diff": queried_diff,
                "accuracy": accuracy,
            },
        )

    def list_purchase_options(
        self,
        device_id: ResourceId,
        **params: JSONValue,
    ) -> List[PurchaseOption]:
        return self.list_all(
            self._user_path("/devices/{0}/purchase-options".format(device_id)),
            params,
            PurchaseOption,
        )

    def get_purchase_options(self, device_id: ResourceId) -> List[PurchaseOption]:
        """Fetch device purchase options through the portal route."""
        return self.list_purchase_options(device_id)

    def list_pro_services(self, **params: JSONValue) -> List[ProService]:
        return self.list_all("/pro-services", params, ProService)

    def list_insurers(self, **params: JSONValue) -> List[Insurer]:
        return self.list_all("/insurers", params, Insurer)

    def list_portal_insurers(self, **params: JSONValue) -> List[Insurer]:
        """List insurers through the portal root route."""
        return self.list_all("/insurers", params, Insurer)

    def list_clients(self, **params: JSONValue) -> List[ApiClient]:
        return self.list_all("/clients", params, ApiClient)

    def list_portal_clients(self, **params: JSONValue) -> List[ApiClient]:
        """List API clients through the portal root route."""
        return self.list_all("/clients", params, ApiClient)

    def create_client(self, payload: Optional[JSONDict] = None) -> JSONValue:
        return self.data("POST", "/clients", json=payload or {})

    def generate_api_client(self) -> JSONValue:
        """Generate a portal API client using the portal's empty payload."""
        return self.create_client({})

    def get_contact_info(self, **params: JSONValue) -> List[Contact]:
        return self.list_all("/contacts", params, Contact)

    def raw(self, method: str, path: str, **kwargs: Any) -> JSONDict:
        """Call any current or future Flume endpoint without a new wrapper."""
        return self.request(method, path, **kwargs)

    def raw_response(self, method: str, path: str, **kwargs: Any) -> Response:
        """Call an endpoint and return the underlying Requests response."""
        self.request(method, path, **kwargs)
        assert self.last_response is not None
        return self.last_response
