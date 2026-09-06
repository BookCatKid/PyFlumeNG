"""Complete resource client for documented and portal-discovered Flume routes."""

from urllib.parse import urljoin

from requests import Session

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


class FlumeClient:
    """Call Flume endpoints with a PersonalAuth or PortalAuth object."""

    def __init__(self, auth, http_session=None, base_url=API_BASE_URL, timeout=30):
        self.auth = auth
        self._http_session = http_session or getattr(auth, "_http_session", Session())
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.last_response = None
        self.rate_limit = getattr(auth, "rate_limit", None)

    def request(self, method, path, params=None, json=None, data=None, **kwargs):
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
                params=params,
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

    def data(self, method, path, model=None, **kwargs):
        """Return the response data parsed into portal-shaped models."""
        required_capability = kwargs.pop("requires_capability", None)
        if required_capability is not None:
            self._require_capability(required_capability)
        return self.response(method, path, model=model, **kwargs).data

    def response(self, method, path, model=None, **kwargs):
        """Return a typed Flume response envelope."""
        return FlumeResponse(self.request(method, path, **kwargs), model=model)

    def data_one(self, method, path, model=None, **kwargs):
        """Return the first parsed resource, matching portal ``model()`` calls."""
        value = self.data(method, path, model, **kwargs)
        if isinstance(value, list):
            return value[0] if value else None
        return value

    def list_all(self, path, params=None, model=None):
        """Fetch every page from a paginated Flume list endpoint."""
        results = []
        for page in self.iter_pages(path, params=params, model=model):
            page = page.data or []
            results.extend(page if isinstance(page, list) else [page])
        return results

    def iter_pages(self, path, params=None, model=None):
        """Yield typed response envelopes for each page of a list endpoint.

        A repeated pagination link is treated as a server-side pagination
        failure and stops traversal instead of causing an infinite loop.
        """
        request_params = dict(params or {})
        request_params.setdefault("limit", 2000)
        request_params.setdefault("offset", 0)
        next_path = path
        seen = set()
        while next_path:
            marker = (next_path, tuple(sorted(request_params.items())))
            if marker in seen:
                raise RuntimeError("Flume pagination returned a repeated next link")
            seen.add(marker)
            page = self.response("GET", next_path, model=model, params=request_params)
            yield page
            next_path = page.next_url
            request_params = {}

    def _user_path(self, suffix=""):
        return "/users/{0}{1}".format(self.auth.user_id, suffix)

    def _require_capability(self, capability):
        """Raise before transport when auth lacks a named capability."""
        if capability not in getattr(self.auth, "capabilities", frozenset()):
            raise FlumeCapabilityError(
                "This operation requires '{0}'. Use PortalAuth instead of "
                "PersonalAuth.".format(capability),
            )

    # Documented user, device, query, and flow routes.
    def get_user(self):
        return self.data_one("GET", self._user_path(), User)

    def list_devices(self, **params):
        return self.list_all(self._user_path("/devices"), params, Device)

    def list_portal_devices(self, **params):
        """List devices through the portal's root device route."""
        return self.list_all("/devices", params, Device)

    def get_device(self, device_id, **params):
        return self.data_one(
            "GET",
            self._user_path("/devices/{0}".format(device_id)),
            Device,
            params=params,
        )

    def get_portal_device(self, device_id, **params):
        """Fetch one device through the portal's root device route."""
        return self.data_one(
            "GET", "/devices/{0}".format(device_id), Device, params=params
        )

    def query(self, device_id, payload):
        return self.data(
            "POST",
            self._user_path("/devices/{0}/query".format(device_id)),
            QueryResult,
            json=payload,
        )

    def portal_query(self, device_id, payload):
        """Submit a query through the portal's root device route."""
        return self.data(
            "POST", "/devices/{0}/query".format(device_id), QueryResult, json=payload
        )

    def get_current_flow(self, device_id):
        return self.data_one(
            "GET",
            self._user_path("/devices/{0}/query/active".format(device_id)),
            CurrentFlow,
        )

    def get_portal_current_flow(self, device_id):
        """Read current flow through the portal's root device route."""
        return self.data_one(
            "GET", "/devices/{0}/query/active".format(device_id), CurrentFlow
        )

    # Locations and account mutations.
    def list_locations(self, **params):
        return self.list_all(self._user_path("/locations"), params, Location)

    def list_portal_locations(self, **params):
        """List locations through the portal's root location route."""
        return self.list_all("/locations", params, Location)

    def get_location_profiles(self):
        """Fetch the portal's appliance/profile metadata."""
        return self.data_one("GET", "/location-profiles", LocationProfiles)

    def get_location(self, location_id):
        return self.data_one(
            "GET", self._user_path("/locations/{0}".format(location_id)), Location
        )

    def get_portal_location(self, location_id):
        """Fetch one location through the portal's root location route."""
        return self.data_one("GET", "/locations/{0}".format(location_id), Location)

    def create_location(self, payload):
        return self.data("POST", self._user_path("/locations"), json=payload)

    def create_portal_location(self, payload):
        """Create a location through the portal's root location route."""
        self._require_capability("portal_writes")
        return self.data("POST", "/locations", json=payload)

    def update_location(self, location_id, payload):
        return self.data(
            "PATCH", self._user_path("/locations/{0}".format(location_id)), json=payload
        )

    def update_portal_location(self, location_id, payload):
        """Update a location through the portal's root location route."""
        self._require_capability("portal_writes")
        return self.data("PATCH", "/locations/{0}".format(location_id), json=payload)

    def update_user(self, payload):
        return self.data("PATCH", self._user_path(), json=payload)

    def update_portal_user(self, payload):
        """Update the current user through the portal's collection route."""
        self._require_capability("portal_writes")
        return self.data("PATCH", "/users/{0}".format(self.auth.user_id), json=payload)

    def update_password(self, payload):
        return self.data("PATCH", self._user_path("/password"), json=payload)

    def update_email(self, payload):
        return self.data("PATCH", self._user_path("/email"), json=payload)

    # Notifications, alerts, and rules.
    def list_notifications(self, **params):
        return self.list_all(self._user_path("/notifications"), params, Notification)

    def list_portal_notifications(self, **params):
        """List notifications through the portal's root notification route."""
        return self.list_all("/notifications", params, Notification)

    def get_notification(self, notification_id):
        return self.data_one(
            "GET",
            self._user_path("/notifications/{0}".format(notification_id)),
            Notification,
        )

    def get_portal_notification(self, notification_id):
        """Fetch one notification through the portal's root route."""
        return self.data_one(
            "GET", "/notifications/{0}".format(notification_id), Notification
        )

    def update_notification(self, notification_id, payload):
        return self.data(
            "PATCH",
            self._user_path("/notifications/{0}".format(notification_id)),
            json=payload,
        )

    def update_portal_notification(self, notification_id, payload):
        """Update a notification through the portal's root route."""
        self._require_capability("portal_writes")
        return self.data(
            "PATCH", "/notifications/{0}".format(notification_id), json=payload
        )

    def delete_notification(self, notification_id):
        return self.data(
            "DELETE", self._user_path("/notifications/{0}".format(notification_id))
        )

    def delete_portal_notification(self, notification_id):
        """Delete a notification through the portal's root route."""
        self._require_capability("portal_writes")
        return self.data("DELETE", "/notifications/{0}".format(notification_id))

    def set_notification_read(self, notification_id, read=True, portal=True):
        """Set notification read state using the portal's frontend payload."""
        if portal:
            return self.update_portal_notification(
                notification_id, {"read": bool(read)}
            )
        return self.update_notification(notification_id, {"read": bool(read)})

    def list_usage_alerts(self, **params):
        return self.list_all(self._user_path("/usage-alerts"), params, UsageAlert)

    def list_event_rules(self, device_id, **params):
        return self.list_all(
            self._user_path("/devices/{0}/rules".format(device_id)),
            params,
            UsageAlertRule,
        )

    def list_usage_alert_rules(self, device_id, **params):
        return self.list_all(
            self._user_path("/devices/{0}/rules/usage-alerts".format(device_id)),
            params,
            UsageAlertRule,
        )

    def list_portal_usage_alert_rules(self, device_id, **params):
        """List rules through the portal's root device route."""
        return self.list_all(
            "/devices/{0}/rules/usage-alerts".format(device_id), params, UsageAlertRule
        )

    def get_usage_alert_rule(self, device_id, rule_id):
        return self.data_one(
            "GET",
            self._user_path(
                "/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id)
            ),
            UsageAlertRule,
        )

    def get_portal_usage_alert_rule(self, device_id, rule_id):
        """Fetch one rule through the portal's root device route."""
        return self.data_one(
            "GET",
            "/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id),
            UsageAlertRule,
        )

    def create_usage_alert_rule(self, device_id, payload):
        return self.data(
            "POST",
            self._user_path("/devices/{0}/rules/usage-alerts".format(device_id)),
            json=payload,
        )

    def create_portal_usage_alert_rule(self, device_id, payload):
        """Create a rule through the portal's root device route."""
        self._require_capability("portal_writes")
        return self.data(
            "POST", "/devices/{0}/rules/usage-alerts".format(device_id), json=payload
        )

    def update_usage_alert_rule(self, device_id, rule_id, payload):
        self._require_capability("portal_writes")
        return self.data(
            "PATCH",
            self._user_path(
                "/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id)
            ),
            json=payload,
        )

    def update_portal_usage_alert_rule(self, device_id, rule_id, payload):
        """Update a rule using the portal service's collection PATCH form."""
        self._require_capability("portal_writes")
        return self.data(
            "PATCH",
            "/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id),
            json=payload,
        )

    def delete_usage_alert_rule(self, device_id, rule_id):
        return self.data(
            "DELETE",
            self._user_path(
                "/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id)
            ),
        )

    def delete_portal_usage_alert_rule(self, device_id, rule_id):
        """Delete a rule through the portal service's collection route."""
        self._require_capability("portal_writes")
        return self.data(
            "DELETE", "/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id)
        )

    def set_usage_alert_rule_active(self, device_id, rule_id, active):
        return self.update_usage_alert_rule(
            device_id, rule_id, {"active": bool(active)}
        )

    def set_portal_usage_alert_rule_active(self, device_id, rule_id, active):
        """Toggle a rule using the portal service's collection PATCH form."""
        self._require_capability("portal_writes")
        return self.update_portal_usage_alert_rule(
            device_id,
            rule_id,
            {"active": bool(active)},
        )

    def list_leaks(self, device_id):
        return self.data_one(
            "GET", self._user_path("/devices/{0}/leaks/active".format(device_id)), Leak
        )

    def list_portal_leaks(self, device_id):
        """Read active leaks through the portal's user-scoped route."""
        return self.data(
            "GET", self._user_path("/devices/{0}/leaks/active".format(device_id))
        )

    def get_leak(self, device_id, leak_id):
        return self.data_one(
            "GET",
            self._user_path("/devices/{0}/leaks/{1}".format(device_id, leak_id)),
            Leak,
        )

    def get_portal_leak(self, device_id, leak_id):
        """Read one active leak through the portal's user-scoped route."""
        return self.data(
            "GET", self._user_path("/devices/{0}/leaks/{1}".format(device_id, leak_id))
        )

    # Budgets and subscriptions.
    def list_budgets(self, device_id, **params):
        return self.list_all(
            self._user_path("/devices/{0}/budgets".format(device_id)), params, Budget
        )

    def list_portal_budgets(self, device_id, **params):
        """List budgets through the portal's root device route."""
        return self.list_all("/devices/{0}/budgets".format(device_id), params, Budget)

    def get_budget(self, device_id, budget_id):
        return self.data_one(
            "GET",
            self._user_path("/devices/{0}/budgets/{1}".format(device_id, budget_id)),
            Budget,
        )

    def get_portal_budget(self, device_id, budget_id):
        """Fetch one budget using the portal service's collection GET form."""
        return self.data_one(
            "GET", "/devices/{0}/budgets/{1}".format(device_id, budget_id), Budget
        )

    def create_budget(self, device_id, payload):
        return self.data(
            "POST",
            self._user_path("/devices/{0}/budgets".format(device_id)),
            json=payload,
        )

    def create_portal_budget(self, device_id, payload):
        """Create a budget through the portal's root device route."""
        return self.data("POST", "/devices/{0}/budgets".format(device_id), json=payload)

    def update_budget(self, device_id, budget_id, payload):
        return self.data(
            "PATCH",
            self._user_path("/devices/{0}/budgets/{1}".format(device_id, budget_id)),
            json=payload,
        )

    def update_portal_budget(self, device_id, budget_id, payload):
        """Update a budget using the portal service's collection PATCH form."""
        return self.data(
            "PATCH",
            "/devices/{0}/budgets/{1}".format(device_id, budget_id),
            json=payload,
        )

    def delete_budget(self, device_id, budget_id):
        return self.data(
            "DELETE",
            self._user_path("/devices/{0}/budgets/{1}".format(device_id, budget_id)),
        )

    def delete_portal_budget(self, device_id, budget_id):
        """Delete a budget using the portal service's collection route."""
        return self.data(
            "DELETE", "/devices/{0}/budgets/{1}".format(device_id, budget_id)
        )

    def list_subscriptions(self, **params):
        return self.list_all(self._user_path("/subscriptions"), params, Subscription)

    def list_portal_subscriptions(self, **params):
        """List subscriptions through the portal's root route."""
        return self.list_all("/subscriptions", params, Subscription)

    def get_subscription(self, subscription_id):
        return self.data_one(
            "GET",
            self._user_path("/subscriptions/{0}".format(subscription_id)),
            Subscription,
        )

    def get_portal_subscription(self, subscription_id):
        """Fetch a subscription through the portal's collection GET form."""
        return self.data_one(
            "GET", "/subscriptions/{0}".format(subscription_id), Subscription
        )

    def create_location_subscription(self, location_id, payload):
        return self.data(
            "POST",
            self._user_path("/locations/{0}/subscriptions".format(location_id)),
            json=payload,
        )

    def create_portal_subscription(self, location_id, payload):
        """Create a subscription through the portal's root location route."""
        return self.data(
            "POST", "/locations/{0}/subscriptions".format(location_id), json=payload
        )

    def update_subscription(self, subscription_id, payload):
        return self.data(
            "PATCH",
            self._user_path("/subscriptions/{0}".format(subscription_id)),
            json=payload,
        )

    def update_portal_subscription(self, subscription_id, payload):
        """Update a subscription through the portal's collection PATCH form."""
        return self.data(
            "PATCH", "/subscriptions/{0}".format(subscription_id), json=payload
        )

    def delete_subscription(self, subscription_id):
        return self.data(
            "DELETE", self._user_path("/subscriptions/{0}".format(subscription_id))
        )

    def delete_portal_subscription(self, subscription_id):
        """Delete a subscription through the portal's collection route."""
        return self.data("DELETE", "/subscriptions/{0}".format(subscription_id))

    def create_stripe_portal(self, return_url):
        return self.data(
            "POST", self._user_path("/stripe-portal"), json={"return_url": return_url}
        )

    def subscribe(self, return_url):
        return self.data(
            "POST", self._user_path("/subscribe"), json={"return_url": return_url}
        )

    # Portal-only usage schedules and shutoff configuration.
    def list_do_not_alert_schedules(self, device_id, **params):
        return self.list_all(
            self._user_path("/devices/{0}/do-not-alert-schedules".format(device_id)),
            params,
            DoNotAlertSchedule,
        )

    def list_portal_do_not_alert_schedules(self, device_id, **params):
        """List DNA schedules through the portal's user-scoped route."""
        return self.list_all(
            self._user_path("/devices/{0}/do-not-alert-schedules".format(device_id)),
            params,
            DoNotAlertSchedule,
        )

    def create_do_not_alert_schedule(self, device_id, payload):
        return self.data(
            "POST",
            self._user_path("/devices/{0}/do-not-alert-schedules".format(device_id)),
            json=payload,
        )

    def create_portal_do_not_alert_schedule(self, device_id, payload):
        """Create a DNA schedule using the portal payload."""
        return self.data(
            "POST",
            self._user_path("/devices/{0}/do-not-alert-schedules".format(device_id)),
            json=payload,
        )

    def update_do_not_alert_schedule(self, device_id, schedule_id, payload):
        return self.data(
            "PATCH",
            self._user_path(
                "/devices/{0}/do-not-alert-schedules/{1}".format(device_id, schedule_id)
            ),
            json=payload,
        )

    def update_portal_do_not_alert_schedule(self, device_id, schedule_id, payload):
        """Update a DNA schedule using the portal collection PATCH form."""
        return self.data(
            "PATCH",
            self._user_path(
                "/devices/{0}/do-not-alert-schedules/{1}".format(device_id, schedule_id)
            ),
            json=payload,
        )

    def delete_do_not_alert_schedule(self, device_id, schedule_id):
        return self.data(
            "DELETE",
            self._user_path(
                "/devices/{0}/do-not-alert-schedules/{1}".format(device_id, schedule_id)
            ),
        )

    def delete_portal_do_not_alert_schedule(self, device_id, schedule_id):
        """Delete a DNA schedule using the portal collection route."""
        return self.data(
            "DELETE",
            self._user_path(
                "/devices/{0}/do-not-alert-schedules/{1}".format(device_id, schedule_id)
            ),
        )

    def update_rule_schedules(self, device_id, rule_id, payload):
        return self.data(
            "PATCH",
            self._user_path(
                "/devices/{0}/rules/usage-alerts/{1}/do-not-alert-schedules".format(
                    device_id, rule_id
                )
            ),
            json=payload,
        )

    def toggle_usage_alert_schedule(self, device_id, rule_id, schedule_id, active):
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

    def update_rule_shutoff_config(self, device_id, rule_id, payload):
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
    def list_location_access(self, location_id, **params):
        return self.list_all(
            self._user_path("/locations/{0}/access".format(location_id)),
            params,
            LocationAccess,
        )

    def list_portal_location_access(self, location_id, **params):
        """List sharing records through the portal's root location route."""
        return self.list_all(
            "/locations/{0}/access".format(location_id), params, LocationAccess
        )

    def get_location_access(self, location_id, access_id):
        return self.data_one(
            "GET",
            self._user_path("/locations/{0}/access/{1}".format(location_id, access_id)),
            LocationAccess,
        )

    def get_portal_location_access(self, location_id, access_id):
        """Fetch sharing records through the portal collection GET form."""
        return self.data_one(
            "GET",
            "/locations/{0}/access/{1}".format(location_id, access_id),
            LocationAccess,
        )

    def grant_location_access(self, location_id, payload):
        return self.data(
            "POST",
            self._user_path("/locations/{0}/access".format(location_id)),
            json=payload,
        )

    def grant_portal_location_access(self, location_id, payload):
        """Grant sharing access through the portal's root location route."""
        return self.data(
            "POST", "/locations/{0}/access".format(location_id), json=payload
        )

    def revoke_location_access(self, location_id, access_id):
        return self.data(
            "DELETE",
            self._user_path("/locations/{0}/access/{1}".format(location_id, access_id)),
        )

    def revoke_portal_location_access(self, location_id, access_id):
        """Revoke sharing access through the portal collection route."""
        return self.data(
            "DELETE", "/locations/{0}/access/{1}".format(location_id, access_id)
        )

    def list_integrations(self, device_id, **params):
        return self.list_all(
            self._user_path("/devices/{0}/integrations".format(device_id)),
            params,
            Integration,
        )

    def list_portal_integrations(self, device_id, **params):
        """List integrations through the portal's user-scoped route."""
        return self.list_all(
            self._user_path("/devices/{0}/integrations".format(device_id)),
            params,
            Integration,
        )

    def get_integration(self, device_id, integration_id):
        return self.data_one(
            "GET",
            self._user_path(
                "/devices/{0}/integrations/{1}".format(device_id, integration_id)
            ),
            Integration,
        )

    def get_portal_integration(self, device_id, integration_id):
        return self.data_one(
            "GET",
            self._user_path(
                "/devices/{0}/integrations/{1}".format(device_id, integration_id)
            ),
            Integration,
        )

    def command_integration(self, device_id, integration_id, state):
        return self.data(
            "POST",
            self._user_path(
                "/devices/{0}/integrations/{1}/command".format(
                    device_id, integration_id
                )
            ),
            json={"state": state},
        )

    def command_portal_integration(self, device_id, integration_id, state):
        return self.data(
            "POST",
            self._user_path(
                "/devices/{0}/integrations/{1}/command".format(
                    device_id, integration_id
                )
            ),
            json={"state": state},
        )

    def refresh_integration(self, device_id, integration_id):
        return self.data(
            "POST",
            self._user_path(
                "/devices/{0}/integrations/{1}/refresh".format(
                    device_id, integration_id
                )
            ),
            json={},
        )

    def refresh_portal_integration(self, device_id, integration_id):
        return self.data(
            "POST",
            self._user_path(
                "/devices/{0}/integrations/{1}/refresh".format(
                    device_id, integration_id
                )
            ),
            json={},
        )

    def delete_integration(self, device_id, integration_id):
        return self.data(
            "DELETE",
            self._user_path(
                "/devices/{0}/integrations/{1}".format(device_id, integration_id)
            ),
        )

    def unlink_portal_integration(self, device_id, integration_id=None, payload=None):
        """Unlink an integration using the portal's collection DELETE form."""
        path = self._user_path("/devices/{0}/integrations".format(device_id))
        if integration_id is not None:
            path += "/{0}".format(integration_id)
        return self.data("DELETE", path, json=payload)

    def list_shutoff_integrations(self, device_id):
        """List portal shutoff-valve integrations."""
        return self.list_all(
            self._user_path("/devices/{0}/integrations".format(device_id)),
            {"type": "SHUTOFF_VALVE"},
        )

    def list_spans(self, device_id, **params):
        return self.list_all(
            self._user_path("/devices/{0}/spans".format(device_id)), params, Span
        )

    def update_span(self, device_id, span_id, payload):
        return self.data(
            "PATCH",
            self._user_path("/devices/{0}/spans/{1}".format(device_id, span_id)),
            json=payload,
        )

    def update_span_type(self, device_id, span_id, span_type):
        """Set a span's type using the portal's exact payload shape."""
        return self.update_span(device_id, span_id, {"type": span_type})

    def list_span_types(self, location_id, **params):
        return self.list_all(
            self._user_path("/locations/{0}/span-types".format(location_id)),
            params,
            SpanType,
        )

    def submit_feedback(self, device_id, payload):
        return self.data(
            "POST",
            self._user_path("/devices/{0}/feedback".format(device_id)),
            json=payload,
        )

    def submit_device_feedback(self, device_id, payload):
        """Submit device feedback through the portal route."""
        return self.submit_feedback(device_id, payload)

    def get_meter_accuracy(self, device_id):
        return self.data(
            "GET",
            self._user_path("/devices/{0}/meters/accuracy".format(device_id)),
            AccuracyResult,
        )

    def submit_meter_accuracy(self, device_id, payload):
        return self.data(
            "POST",
            self._user_path("/devices/{0}/meters/accuracy".format(device_id)),
            json=payload,
        )

    def submit_meter_accuracy_readings(
        self,
        device_id,
        since_datetime,
        until_datetime,
        since_reading,
        until_reading,
        since_image,
        until_image,
        units,
    ):
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

    def initiate_accuracy_conversation(self, payload):
        return self.data(
            "POST", self._user_path("/initiate-accuracy-conversation"), json=payload
        )

    def start_accuracy_conversation(
        self,
        message,
        since_url,
        since_datetime,
        since_reading,
        until_url,
        until_datetime,
        until_reading,
        units,
        reading_diff,
        queried_diff,
        accuracy,
    ):
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

    def list_purchase_options(self, device_id, **params):
        return self.list_all(
            self._user_path("/devices/{0}/purchase-options".format(device_id)),
            params,
            PurchaseOption,
        )

    def get_purchase_options(self, device_id):
        """Fetch device purchase options through the portal route."""
        return self.list_purchase_options(device_id)

    def list_pro_services(self, **params):
        return self.list_all("/pro-services", params, ProService)

    def list_insurers(self, **params):
        return self.list_all("/insurers", params, Insurer)

    def list_portal_insurers(self, **params):
        """List insurers through the portal root route."""
        return self.list_all("/insurers", params, Insurer)

    def list_clients(self, **params):
        return self.list_all("/clients", params, ApiClient)

    def list_portal_clients(self, **params):
        """List API clients through the portal root route."""
        return self.list_all("/clients", params, ApiClient)

    def create_client(self, payload=None):
        return self.data("POST", "/clients", json=payload or {})

    def generate_api_client(self):
        """Generate a portal API client using the portal's empty payload."""
        return self.create_client({})

    def get_contact_info(self, **params):
        return self.list_all("/contacts", params, Contact)

    def raw(self, method, path, **kwargs):
        """Call any current or future Flume endpoint without a new wrapper."""
        return self.request(method, path, **kwargs)

    def raw_response(self, method, path, **kwargs):
        """Call an endpoint and return the underlying Requests response."""
        self.request(method, path, **kwargs)
        return self.last_response
