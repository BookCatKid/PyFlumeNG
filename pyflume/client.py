"""Complete resource client for documented and portal-discovered Flume routes."""

from urllib.parse import urljoin

from requests import Session

from .constants import API_BASE_URL
from .errors import FlumeHTTPError, FlumeRateLimitError


class FlumeClient:
    """Call Flume endpoints with a PersonalAuth or PortalAuth object."""

    def __init__(self, auth, http_session=None, base_url=API_BASE_URL, timeout=30):
        self.auth = auth
        self._http_session = http_session or getattr(auth, "_http_session", Session())
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.last_response = None

    def request(self, method, path, params=None, json=None, data=None, **kwargs):
        """Return the complete Flume response envelope.

        A 401 is retried once after refreshing the auth object. All other
        errors retain the response envelope and are raised as typed errors.
        """
        url = path if path.startswith("http") else urljoin(self.base_url + "/", path.lstrip("/"))
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
            try:
                envelope = response.json()
            except ValueError as exc:
                envelope = {}
                if response.status_code < 200 or response.status_code >= 300:
                    raise FlumeHTTPError("Flume returned a non-JSON error", response) from exc
            if response.status_code == 401 and not retried:
                self.auth.refresh()
                retried = True
                continue
            if response.status_code == 429:
                raise FlumeRateLimitError("Flume API rate limit exceeded", response, envelope)
            if response.status_code < 200 or response.status_code >= 300:
                raise FlumeHTTPError("Flume API request failed", response, envelope)
            return envelope

    def data(self, method, path, **kwargs):
        """Return only the response envelope's data field."""
        return self.request(method, path, **kwargs).get("data", [])

    def list_all(self, path, params=None):
        """Fetch every page from a paginated Flume list endpoint."""
        params = dict(params or {})
        params.setdefault("limit", 2000)
        params.setdefault("offset", 0)
        results = []
        next_path = path
        while next_path:
            envelope = self.request("GET", next_path, params=params)
            page = envelope.get("data") or []
            results.extend(page if isinstance(page, list) else [page])
            next_path = (envelope.get("pagination") or {}).get("next")
            params = {}
        return results

    def _user_path(self, suffix=""):
        return "/users/{0}{1}".format(self.auth.user_id, suffix)

    # Documented user, device, query, and flow routes.
    def get_user(self):
        return self.data("GET", self._user_path())

    def list_devices(self, **params):
        return self.list_all(self._user_path("/devices"), params)

    def get_device(self, device_id, **params):
        return self.data("GET", self._user_path("/devices/{0}".format(device_id)), params=params)

    def query(self, device_id, payload):
        return self.data("POST", self._user_path("/devices/{0}/query".format(device_id)), json=payload)

    def get_current_flow(self, device_id):
        return self.data("GET", self._user_path("/devices/{0}/query/active".format(device_id)))

    # Locations and account mutations.
    def list_locations(self, **params):
        return self.list_all(self._user_path("/locations"), params)

    def get_location(self, location_id):
        return self.data("GET", self._user_path("/locations/{0}".format(location_id)))

    def create_location(self, payload):
        return self.data("POST", self._user_path("/locations"), json=payload)

    def update_location(self, location_id, payload):
        return self.data("PATCH", self._user_path("/locations/{0}".format(location_id)), json=payload)

    def update_user(self, payload):
        return self.data("PATCH", self._user_path(), json=payload)

    def update_password(self, payload):
        return self.data("PATCH", self._user_path("/password"), json=payload)

    def update_email(self, payload):
        return self.data("PATCH", self._user_path("/email"), json=payload)

    # Notifications, alerts, and rules.
    def list_notifications(self, **params):
        return self.list_all(self._user_path("/notifications"), params)

    def get_notification(self, notification_id):
        return self.data("GET", self._user_path("/notifications/{0}".format(notification_id)))

    def update_notification(self, notification_id, payload):
        return self.data("PATCH", self._user_path("/notifications/{0}".format(notification_id)), json=payload)

    def delete_notification(self, notification_id):
        return self.data("DELETE", self._user_path("/notifications/{0}".format(notification_id)))

    def list_usage_alerts(self, **params):
        return self.list_all(self._user_path("/usage-alerts"), params)

    def list_event_rules(self, device_id, **params):
        return self.list_all(self._user_path("/devices/{0}/rules".format(device_id)), params)

    def list_usage_alert_rules(self, device_id, **params):
        return self.list_all(self._user_path("/devices/{0}/rules/usage-alerts".format(device_id)), params)

    def get_usage_alert_rule(self, device_id, rule_id):
        return self.data("GET", self._user_path("/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id)))

    def create_usage_alert_rule(self, device_id, payload):
        return self.data("POST", self._user_path("/devices/{0}/rules/usage-alerts".format(device_id)), json=payload)

    def update_usage_alert_rule(self, device_id, rule_id, payload):
        return self.data("PATCH", self._user_path("/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id)), json=payload)

    def delete_usage_alert_rule(self, device_id, rule_id):
        return self.data("DELETE", self._user_path("/devices/{0}/rules/usage-alerts/{1}".format(device_id, rule_id)))

    def set_usage_alert_rule_active(self, device_id, rule_id, active):
        return self.update_usage_alert_rule(device_id, rule_id, {"active": bool(active)})

    def list_leaks(self, device_id):
        return self.data("GET", self._user_path("/devices/{0}/leaks/active".format(device_id)))

    def get_leak(self, device_id, leak_id):
        return self.data("GET", self._user_path("/devices/{0}/leaks/{1}".format(device_id, leak_id)))

    # Budgets and subscriptions.
    def list_budgets(self, device_id, **params):
        return self.list_all(self._user_path("/devices/{0}/budgets".format(device_id)), params)

    def get_budget(self, device_id, budget_id):
        return self.data("GET", self._user_path("/devices/{0}/budgets/{1}".format(device_id, budget_id)))

    def create_budget(self, device_id, payload):
        return self.data("POST", self._user_path("/devices/{0}/budgets".format(device_id)), json=payload)

    def update_budget(self, device_id, budget_id, payload):
        return self.data("PATCH", self._user_path("/devices/{0}/budgets/{1}".format(device_id, budget_id)), json=payload)

    def delete_budget(self, device_id, budget_id):
        return self.data("DELETE", self._user_path("/devices/{0}/budgets/{1}".format(device_id, budget_id)))

    def list_subscriptions(self, **params):
        return self.list_all(self._user_path("/subscriptions"), params)

    def get_subscription(self, subscription_id):
        return self.data("GET", self._user_path("/subscriptions/{0}".format(subscription_id)))

    def create_location_subscription(self, location_id, payload):
        return self.data("POST", self._user_path("/locations/{0}/subscriptions".format(location_id)), json=payload)

    def update_subscription(self, subscription_id, payload):
        return self.data("PATCH", self._user_path("/subscriptions/{0}".format(subscription_id)), json=payload)

    def delete_subscription(self, subscription_id):
        return self.data("DELETE", self._user_path("/subscriptions/{0}".format(subscription_id)))

    def create_stripe_portal(self, return_url):
        return self.data("POST", self._user_path("/stripe-portal"), json={"return_url": return_url})

    def subscribe(self, return_url):
        return self.data("POST", self._user_path("/subscribe"), json={"return_url": return_url})

    # Portal-only usage schedules and shutoff configuration.
    def list_do_not_alert_schedules(self, device_id, **params):
        return self.list_all(self._user_path("/devices/{0}/do-not-alert-schedules".format(device_id)), params)

    def create_do_not_alert_schedule(self, device_id, payload):
        return self.data("POST", self._user_path("/devices/{0}/do-not-alert-schedules".format(device_id)), json=payload)

    def update_do_not_alert_schedule(self, device_id, schedule_id, payload):
        return self.data("PATCH", self._user_path("/devices/{0}/do-not-alert-schedules/{1}".format(device_id, schedule_id)), json=payload)

    def delete_do_not_alert_schedule(self, device_id, schedule_id):
        return self.data("DELETE", self._user_path("/devices/{0}/do-not-alert-schedules/{1}".format(device_id, schedule_id)))

    def update_rule_schedules(self, device_id, rule_id, payload):
        return self.data("PATCH", self._user_path("/devices/{0}/rules/usage-alerts/{1}/do-not-alert-schedules".format(device_id, rule_id)), json=payload)

    def update_rule_shutoff_config(self, device_id, rule_id, payload):
        return self.data("PATCH", self._user_path("/devices/{0}/rules/usage-alerts/{1}/shutoff-config".format(device_id, rule_id)), json=payload)

    # Sharing, integrations, diagnostics, and support endpoints discovered in the portal.
    def list_location_access(self, location_id, **params):
        return self.list_all(self._user_path("/locations/{0}/access".format(location_id)), params)

    def get_location_access(self, location_id, access_id):
        return self.data("GET", self._user_path("/locations/{0}/access/{1}".format(location_id, access_id)))

    def grant_location_access(self, location_id, payload):
        return self.data("POST", self._user_path("/locations/{0}/access".format(location_id)), json=payload)

    def revoke_location_access(self, location_id, access_id):
        return self.data("DELETE", self._user_path("/locations/{0}/access/{1}".format(location_id, access_id)))

    def list_integrations(self, device_id, **params):
        return self.list_all(self._user_path("/devices/{0}/integrations".format(device_id)), params)

    def get_integration(self, device_id, integration_id):
        return self.data("GET", self._user_path("/devices/{0}/integrations/{1}".format(device_id, integration_id)))

    def command_integration(self, device_id, integration_id, state):
        return self.data("POST", self._user_path("/devices/{0}/integrations/{1}/command".format(device_id, integration_id)), json={"state": state})

    def refresh_integration(self, device_id, integration_id):
        return self.data("POST", self._user_path("/devices/{0}/integrations/{1}/refresh".format(device_id, integration_id)), json={})

    def delete_integration(self, device_id, integration_id):
        return self.data("DELETE", self._user_path("/devices/{0}/integrations/{1}".format(device_id, integration_id)))

    def list_spans(self, device_id, **params):
        return self.list_all(self._user_path("/devices/{0}/spans".format(device_id)), params)

    def update_span(self, device_id, span_id, payload):
        return self.data("PATCH", self._user_path("/devices/{0}/spans/{1}".format(device_id, span_id)), json=payload)

    def list_span_types(self, location_id, **params):
        return self.list_all(self._user_path("/locations/{0}/span-types".format(location_id)), params)

    def submit_feedback(self, device_id, payload):
        return self.data("POST", self._user_path("/devices/{0}/feedback".format(device_id)), json=payload)

    def get_meter_accuracy(self, device_id):
        return self.data("GET", self._user_path("/devices/{0}/meters/accuracy".format(device_id)))

    def submit_meter_accuracy(self, device_id, payload):
        return self.data("POST", self._user_path("/devices/{0}/meters/accuracy".format(device_id)), json=payload)

    def initiate_accuracy_conversation(self, payload):
        return self.data("POST", self._user_path("/initiate-accuracy-conversation"), json=payload)

    def list_purchase_options(self, device_id, **params):
        return self.list_all(self._user_path("/devices/{0}/purchase-options".format(device_id)), params)

    def list_pro_services(self, **params):
        return self.list_all("/pro-services", params)

    def list_insurers(self, **params):
        return self.list_all("/insurers", params)

    def list_clients(self, **params):
        return self.list_all("/clients", params)

    def create_client(self, payload=None):
        return self.data("POST", "/clients", json=payload or {})

    def get_contact_info(self, **params):
        return self.list_all("/contacts", params)

    def raw(self, method, path, **kwargs):
        """Call any current or future Flume endpoint without a new wrapper."""
        return self.request(method, path, **kwargs)

    def raw_response(self, method, path, **kwargs):
        """Call an endpoint and return the underlying Requests response."""
        self.request(method, path, **kwargs)
        return self.last_response
