"""Tests for the standalone PyFlumeNG package."""

from urllib.parse import parse_qs

import pytest
from pyflume import FlumeAuth, FlumeClient, PersonalAuth, FlumePortalAuth
from pyflume.auth import PORTAL_OAUTH_AUTHORIZE_URL, PORTAL_OAUTH_TOKEN_URL
from pyflume.constants import API_BASE_URL, URL_OAUTH_TOKEN
from pyflume.errors import FlumeRateLimitError

PortalAuth = FlumePortalAuth
PORTAL_AUTHORIZE_URL = PORTAL_OAUTH_AUTHORIZE_URL
PERSONAL_TOKEN_URL = URL_OAUTH_TOKEN
PORTAL_TOKEN_URL = PORTAL_OAUTH_TOKEN_URL


TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJ1c2VyX2lkIjoyNDM4NCwiZXhwIjoyOTk5OTk5OTk3LCJzY29wZSI6WyJyZWFkIl19."
    "utb2yzcMImBFhDx_mssC_HU0mbfo0D_-VAQOetw5_h0"
)


def token(scope="read"):
    """Return a token fixture with a valid future payload."""
    return {
        "access_token": TOKEN,
        "refresh_token": "refresh-token",
        "scope": scope,
    }


def auth():
    """Return a PersonalAuth without making a token request."""
    return PersonalAuth(
        "user@example.com",
        "password",
        "client-id",
        "client-secret",
        flume_token=token(),
    )


def test_portal_auth_uses_browser_oauth_flow(requests_mock):
    """Portal auth follows login, authorize, and token exchange."""
    requests_mock.get("https://api.flumewater.com/account/login", text="<form />")

    def authorize(request, context):
        state = parse_qs(request.text)["state"][0]
        context.status_code = 302
        context.headers["Location"] = (
            "https://portal.flumewater.com?code=one-time-code&state=" + state
        )
        return ""

    requests_mock.post(PORTAL_AUTHORIZE_URL, text=authorize)
    requests_mock.post(
        PORTAL_TOKEN_URL,
        json={"data": [token("read update delete")], "success": True},
    )

    portal = PortalAuth("user@example.com", "password")

    assert portal.user_id == 12345
    assert portal.authorization_header["authorization"].startswith("Bearer ")
    assert [request.method for request in requests_mock.request_history] == [
        "GET",
        "POST",
        "POST",
    ]
    assert requests_mock.request_history[1].headers["Content-Type"].startswith(
        "application/x-www-form-urlencoded",
    )


def test_client_returns_envelope_and_follows_pagination(requests_mock):
    """The raw client preserves envelopes while list_all flattens pages."""
    first_url = API_BASE_URL + "/users/12345/devices"
    next_url = API_BASE_URL + "/users/12345/devices?offset=1&limit=1"
    requests_mock.get(
        first_url,
        json={
            "success": True,
            "data": [{"id": "first"}],
            "pagination": {"next": "/users/12345/devices?offset=1&limit=1"},
        },
    )
    requests_mock.get(
        next_url,
        json={"success": True, "data": [{"id": "second"}], "pagination": None},
    )
    client = FlumeClient(auth())

    envelope = client.request("GET", "/users/12345/devices", params={"limit": 1})
    devices = client.list_all("/users/12345/devices", {"limit": 1})

    assert envelope["success"] is True
    assert [device["id"] for device in devices] == ["first", "second"]


def test_usage_rule_read_does_not_change_legacy_usage_pagination(requests_mock):
    """Rule reads must not make an existing usage-alert page unavailable."""
    from pyflume import FlumeUsageAlertList

    usage_url = "https://api.flumetech.com/users/12345/usage-alerts"
    rule_url = (
        "https://api.flumetech.com/users/12345/devices/device/rules/"
        "usage-alerts"
    )
    requests_mock.get(
        usage_url,
        json={
            "data": [{"id": 1}],
            "pagination": {"next": "/users/12345/usage-alerts?offset=1"},
        },
    )
    requests_mock.get(rule_url, json={"data": [{"id": "rule"}], "pagination": None})
    requests_mock.get(
        "https://api.flumetech.com/users/12345/usage-alerts?offset=1",
        json={"data": [{"id": 2}], "pagination": None},
    )
    legacy = FlumeUsageAlertList(auth())
    legacy.get_usage_alert_rules("device")

    assert legacy.get_next_usage_alerts() == [{"id": 2}]


def test_client_refreshes_once_after_401(requests_mock):
    """A stale access token is refreshed and the request is retried once."""
    requests_mock.get(
        API_BASE_URL + "/users/12345",
        [
            {"status_code": 401, "json": {"message": "expired"}},
            {"status_code": 200, "json": {"success": True, "data": [{"id": 12345}]}},
        ],
    )
    requests_mock.post(
        PERSONAL_TOKEN_URL,
        json={"data": [token("read refreshed")], "success": True},
    )
    client = FlumeClient(auth())

    assert client.get_user()[0]["id"] == 12345
    assert requests_mock.call_count == 3


def test_rate_limit_exposes_retry_after_and_envelope(requests_mock):
    """429 responses are raised with server retry metadata intact."""
    requests_mock.get(
        API_BASE_URL + "/users/12345",
        status_code=429,
        headers={"Retry-After": "60"},
        json={"success": False, "code": 429, "message": "slow down"},
    )
    client = FlumeClient(auth())

    with pytest.raises(FlumeRateLimitError) as error:
        client.get_user()

    assert error.value.retry_after == "60"
    assert error.value.code == 429


def test_usage_rule_update_uses_portal_endpoint_and_json(requests_mock):
    """Rule updates use the portal-capable endpoint and preserve empty data."""
    url = (
        API_BASE_URL + "/users/12345/devices/device/rules/"
        "usage-alerts/rule"
    )
    requests_mock.patch(url, json={"success": True, "code": 612, "data": []})
    client = FlumeClient(auth())

    result = client.set_usage_alert_rule_active("device", "rule", False)

    assert result == []
    assert requests_mock.last_request.json() == {"active": False}
