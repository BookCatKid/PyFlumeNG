"""Tests for the standalone PyFlumeNG package."""

from urllib.parse import parse_qs, urlsplit

import pytest

from pyflume import (
    AccuracyResult,
    Budget,
    Device,
    DoNotAlertSchedule,
    FlumeClient,
    FlumePortalAuth,
    FlumeResponse,
    Notification,
    PersonalAuth,
    Span,
    SpanDataPoint,
    UsageAlertRule,
    UsageAlertSchedule,
)
from pyflume.auth import PORTAL_OAUTH_AUTHORIZE_URL, PORTAL_OAUTH_TOKEN_URL
from pyflume.constants import API_BASE_URL, URL_OAUTH_TOKEN
from pyflume.devices import FlumeDeviceList
from pyflume.errors import FlumeCapabilityError, FlumeRateLimitError
from pyflume.leak import FlumeLeakList
from pyflume.rate_limit import RateLimitState

PortalAuth = FlumePortalAuth
PORTAL_AUTHORIZE_URL = PORTAL_OAUTH_AUTHORIZE_URL
PERSONAL_TOKEN_URL = URL_OAUTH_TOKEN
PORTAL_TOKEN_URL = PORTAL_OAUTH_TOKEN_URL


TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJ1c2VyX2lkIjoxMjM0NSwiZXhwIjoyOTk5OTk5OTk3LCJ4IjoiZmFrZSJ9."
    "test-signature-pyflumeng"
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
    assert (
        requests_mock.request_history[1]
        .headers["Content-Type"]
        .startswith(
            "application/x-www-form-urlencoded",
        )
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
    client = FlumeClient(
        PortalAuth("user@example.com", "password", flume_token=token())
    )

    envelope = client.request("GET", "/users/12345/devices", params={"limit": 1})
    devices = client.list_all("/users/12345/devices", {"limit": 1})

    assert envelope["success"] is True
    assert [device["id"] for device in devices] == ["first", "second"]


def test_usage_rule_read_does_not_change_legacy_usage_pagination(requests_mock):
    """Rule reads must not make an existing usage-alert page unavailable."""
    from pyflume import FlumeUsageAlertList

    usage_url = "https://api.flumetech.com/users/12345/usage-alerts"
    rule_url = "https://api.flumetech.com/users/12345/devices/device/rules/usage-alerts"
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

    next_alerts = legacy.get_next_usage_alerts()
    assert len(next_alerts) == 1
    assert next_alerts[0].id == 2
    assert legacy.has_next is False


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

    assert client.get_user()["id"] == 12345
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


def test_rate_limit_uses_auth_baseline_and_server_headers(requests_mock):
    """Auth type supplies a baseline that live headers can replace."""
    assert auth().rate_limit.limit == 120
    assert (
        PortalAuth("user@example.com", "password", flume_token=token()).rate_limit.limit
        == 72000
    )

    requests_mock.get(
        API_BASE_URL + "/users/12345",
        headers={
            "X-RateLimit-Limit": "17",
            "X-RateLimit-Remaining": "9",
            "X-RateLimit-Reset": "1788685189",
        },
        json={"success": True, "data": [{"id": 12345}]},
    )
    client = FlumeClient(auth())
    client.get_user()

    assert client.rate_limit.limit == 17
    assert client.rate_limit.remaining == 9
    assert client.rate_limit.reset == 1788685189
    assert client.rate_limit.reset_at.tzinfo is not None


def test_rate_limit_state_ignores_invalid_header_values():
    """Malformed optional headers do not destroy known rate-limit state."""
    state = RateLimitState(120)
    state.update_from_headers({"X-RateLimit-Limit": "bad", "Retry-After": "3"})

    assert state.limit == 120
    assert state.retry_after == "3"


def test_usage_rule_update_uses_portal_endpoint_and_json(requests_mock):
    """Rule updates use the portal-capable endpoint and preserve empty data."""
    url = API_BASE_URL + "/users/12345/devices/device/rules/usage-alerts/rule"
    requests_mock.patch(url, json={"success": True, "code": 612, "data": []})
    client = FlumeClient(
        PortalAuth("user@example.com", "password", flume_token=token())
    )

    result = client.set_usage_alert_rule_active("device", "rule", False)

    assert result == []
    assert requests_mock.last_request.json() == {"active": False}


def test_personal_auth_rejects_portal_rule_write_before_transport(requests_mock):
    """Personal auth reports missing portal capability without an HTTP call."""
    client = FlumeClient(auth())

    with pytest.raises(FlumeCapabilityError, match="PortalAuth"):
        client.set_usage_alert_rule_active("device", "rule", False)

    assert requests_mock.call_count == 0


def test_portal_resource_wrappers_match_frontend_routes(requests_mock):
    """Named portal wrappers preserve frontend paths, query, and payloads."""
    requests_mock.get(
        API_BASE_URL + "/location-profiles",
        json={"success": True, "data": [{"field": "toilet"}]},
    )
    requests_mock.patch(
        API_BASE_URL + "/users/12345/devices/device/spans/span",
        json={"success": True, "data": []},
    )
    requests_mock.patch(
        API_BASE_URL
        + "/users/12345/devices/device/rules/usage-alerts/rule/do-not-alert-schedules",
        json={"success": True, "data": []},
    )
    client = FlumeClient(auth())

    assert client.get_location_profiles()["field"] == "toilet"
    client.update_span_type("device", "span", "IRRIGATION")
    assert requests_mock.request_history[-1].json() == {"type": "IRRIGATION"}
    client.toggle_usage_alert_schedule("device", "rule", 16158, False)
    assert requests_mock.last_request.path.endswith(
        "/rules/usage-alerts/rule/do-not-alert-schedules",
    )
    assert requests_mock.last_request.json() == {"active": False}


def test_span_read_matches_live_portal_shape_and_roundtrips(requests_mock):
    """Portal span reads expose the observed fields and typed series points."""
    url = API_BASE_URL + "/users/12345/devices/device/spans"
    payload = {
        "id": "span-id",
        "type": "OUTDOOR",
        "start": "2026-09-06 10:00:00",
        "end": "2026-09-06 10:02:00",
        "data": [
            {"datetime": "2026-09-06 10:00:00", "value": 0},
            {"datetime": "2026-09-06 10:01:00", "value": 1.25},
        ],
        "is_editable": True,
        "max_flowrate": 2.75,
        "mode_gpm": 1.25,
        "origin": "DISAGGREGATION",
        "total": 2.5,
        "value": 2.5,
        "version": "1",
    }
    requests_mock.get(url, json={"success": True, "data": [payload]})

    result = FlumeClient(auth()).list_spans(
        "device",
        "2026-09-06 10:00:00",
        "2026-09-06 11:00:00",
        span_types=["OUTDOOR", "SHOWER"],
    )

    assert len(result) == 1
    assert isinstance(result[0], Span)
    assert isinstance(result[0].data[0], SpanDataPoint)
    assert result[0].data[1].value == 1.25
    assert result[0].to_dict() == payload
    assert requests_mock.last_request.qs["since_datetime"] == ["2026-09-06 10:00:00"]
    assert requests_mock.last_request.qs["until_datetime"] == ["2026-09-06 11:00:00"]
    assert requests_mock.last_request.qs["units"] == ["gallons"]
    sent_query = parse_qs(urlsplit(requests_mock.last_request.url).query)
    assert sent_query["types"] == ["OUTDOOR,SHOWER"]


def test_portal_accuracy_payload_wrapper(requests_mock):
    """The accuracy helper constructs the same fields as the portal form."""
    requests_mock.post(
        API_BASE_URL + "/users/12345/devices/device/meters/accuracy",
        json={"success": True, "data": []},
    )
    client = FlumeClient(auth())

    client.submit_meter_accuracy_readings(
        "device",
        "2026-09-06 10:00:00",
        "2026-09-06 11:00:00",
        100,
        101,
        "before-image",
        "after-image",
        "GALLONS",
    )

    assert requests_mock.last_request.json() == {
        "since_datetime": "2026-09-06 10:00:00",
        "until_datetime": "2026-09-06 11:00:00",
        "since_reading": 100,
        "until_reading": 101,
        "since_image": "before-image",
        "until_image": "after-image",
        "units": "GALLONS",
    }


def test_meter_accuracy_keeps_api_list_shape_and_types_items(requests_mock):
    """Accuracy normalization must not collapse Flume's data list."""
    requests_mock.get(
        API_BASE_URL + "/users/12345/devices/device/meters/accuracy",
        json={
            "success": True,
            "data": [
                {
                    "type": "ACCURACY",
                    "title": None,
                    "description": None,
                },
            ],
        },
    )

    result = FlumeClient(auth()).get_meter_accuracy("device")

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], AccuracyResult)
    assert result[0].type == "ACCURACY"


def test_portal_list_helpers_follow_pagination(requests_mock):
    """Portal list helpers return all records, not only the first page."""
    base = API_BASE_URL + "/users/12345/devices/device/integrations"
    options = API_BASE_URL + "/users/12345/devices/device/purchase-options"
    requests_mock.get(
        base,
        json={
            "data": [{"id": "one"}],
            "pagination": {"next": "/users/12345/devices/device/integrations?offset=1"},
        },
    )
    requests_mock.get(
        API_BASE_URL + "/users/12345/devices/device/integrations?offset=1",
        json={"data": [{"id": "two"}], "pagination": None},
    )
    requests_mock.get(
        options,
        json={
            "data": [{"id": "option-one"}],
            "pagination": {
                "next": "/users/12345/devices/device/purchase-options?offset=1"
            },
        },
    )
    requests_mock.get(
        API_BASE_URL + "/users/12345/devices/device/purchase-options?offset=1",
        json={"data": [{"id": "option-two"}], "pagination": None},
    )
    client = FlumeClient(auth())

    assert [item["id"] for item in client.list_shutoff_integrations("device")] == [
        "one",
        "two",
    ]
    assert [item["id"] for item in client.get_purchase_options("device")] == [
        "option-one",
        "option-two",
    ]


def test_iter_pages_returns_typed_envelopes(requests_mock):
    """Pagination can be consumed page-by-page with response metadata."""
    url = API_BASE_URL + "/users/12345/devices"
    requests_mock.get(
        url,
        json={
            "success": True,
            "data": [{"id": "one"}],
            "pagination": {"next": "/users/12345/devices?offset=1"},
        },
    )
    requests_mock.get(
        API_BASE_URL + "/users/12345/devices?offset=1",
        json={"success": True, "data": [{"id": "two"}], "pagination": None},
    )

    pages = list(FlumeClient(auth()).iter_pages(url, model=Device))

    assert pages[0].data[0].id == "one"
    assert pages[0].next_url.endswith("offset=1")
    assert pages[1].data[0].id == "two"


def test_iter_pages_rejects_repeated_links(requests_mock):
    """A broken server pagination link cannot hang the client."""
    url = API_BASE_URL + "/users/12345/devices"
    requests_mock.get(
        url,
        json={"data": [], "pagination": {"next": "/users/12345/devices"}},
    )

    with pytest.raises(RuntimeError, match="repeated next link"):
        list(FlumeClient(auth()).iter_pages(url))


def test_models_follow_portal_shapes_and_preserve_unknown_fields():
    """Models expose portal behavior without dropping future fields."""
    rule = UsageAlertRule(
        {
            "id": 10,
            "duration": 125,
            "notify_every": 1500,
            "shutoff_config": {"active": True},
            "future_portal_field": {"enabled": True},
        },
    )
    device = Device({"id": "device", "future_device_field": "kept"})

    assert rule.duration_hour_min == {"hour": 2, "min": 5}
    assert rule.notify_every_day_hour == {"day": 1, "hour": 1}
    assert rule.shutoff_config.active is True
    assert rule["future_portal_field"] == {"enabled": True}
    assert device.to_dict()["future_device_field"] == "kept"
    assert isinstance(Budget({"id": 1}), Budget)


def test_rule_nested_schedules_round_trip_as_portal_models():
    """Usage-alert schedules are typed and serialize back to API-shaped data."""
    rule = UsageAlertRule(
        {
            "id": 1,
            "schedules": [
                {
                    "schedule_id": 16158,
                    "active": True,
                    "name": "Grass Watering",
                    "description": "Suppress alerts while irrigation runs",
                },
            ],
        },
    )

    assert isinstance(rule.schedules[0], UsageAlertSchedule)
    assert rule.schedules[0].name == "Grass Watering"
    assert rule.schedules[0].active is True
    assert rule.to_dict()["schedules"][0]["schedule_id"] == 16158


def test_sparse_notification_extra_preserves_api_shape_on_round_trip():
    """Typed defaults stay readable without inventing omitted API fields."""
    payload = {
        "id": 42,
        "extra": {
            "event_rule_name": "High Flow",
            "query": {
                "bucket": "MINUTE",
                "request_id": "notification_query",
            },
        },
    }

    notification = Notification(payload)

    assert notification.extra is not None
    assert notification.extra.percentage is None
    assert notification.extra.advanced_low_flow is False
    assert notification.extra.query is not None
    assert notification.extra.query.tz == ""
    assert notification.to_dict() == payload


def test_full_do_not_alert_schedule_allows_null_updated_datetime():
    """The full schedule resource is distinct from a rule's compact association."""
    schedule = DoNotAlertSchedule(
        {
            "id": 16158,
            "updated_datetime": None,
            "rrule_obj": {
                "tzid": "America/Los_Angeles",
                "dtstart": "2026-09-06T08:00:00",
                "freq": "WEEKLY",
                "interval": 1,
                "byweekday": ["SU"],
                "byhour": 8,
                "byminute": 0,
                "bysecond": 0,
            },
        },
    )

    assert schedule.updated_datetime is None
    assert schedule.rrule_obj.freq == "WEEKLY"


def test_portal_read_aliases_use_working_user_scoped_routes(requests_mock):
    """Portal read aliases do not call the invalid guessed root routes."""
    requests_mock.get(
        API_BASE_URL + "/users/12345/devices",
        json={"success": True, "data": [{"id": "device"}]},
    )
    requests_mock.get(
        API_BASE_URL + "/users/12345/notifications",
        json={"success": True, "data": [{"id": "notice"}]},
    )
    requests_mock.get(
        API_BASE_URL + "/users/12345/devices/device/query/active",
        json={"success": True, "data": [{"value": 1.5}]},
    )
    client = FlumeClient(
        PortalAuth("user@example.com", "password", flume_token=token())
    )

    assert client.list_portal_devices()[0].id == "device"
    assert client.list_portal_notifications()[0].id == "notice"
    assert client.get_portal_current_flow("device").value == 1.5

    assert [request.path for request in requests_mock.request_history] == [
        "/users/12345/devices",
        "/users/12345/notifications",
        "/users/12345/devices/device/query/active",
    ]


def test_client_returns_typed_models(requests_mock):
    """Named client helpers return models while request retains the envelope."""
    requests_mock.get(
        API_BASE_URL + "/users/12345/devices",
        json={"success": True, "data": [{"id": "device", "connected": True}]},
    )
    requests_mock.get(
        API_BASE_URL + "/users/12345/devices/device/rules/usage-alerts/rule",
        json={"success": True, "data": [{"id": "rule", "duration": 30}]},
    )
    client = FlumeClient(auth())

    devices = client.list_all("/users/12345/devices", {"limit": 50}, Device)
    rule = client.get_usage_alert_rule("device", "rule")

    assert isinstance(devices[0], Device)
    assert devices[0].connected is True
    assert isinstance(rule, UsageAlertRule)
    assert rule.duration == 30


def test_response_returns_typed_envelope_and_metadata(requests_mock):
    """Typed response envelopes preserve mutation metadata and data models."""
    requests_mock.patch(
        API_BASE_URL + "/users/12345/devices/device/rules/usage-alerts/rule",
        json={
            "success": True,
            "code": 612,
            "message": "Record successfully updated",
            "http_code": 200,
            "data": [{"id": "rule", "active": False}],
            "count": 1,
        },
    )
    response = FlumeClient(auth()).response(
        "PATCH",
        "/users/12345/devices/device/rules/usage-alerts/rule",
        model=UsageAlertRule,
        json={"active": False},
    )

    assert isinstance(response, FlumeResponse)
    assert response.code == 612
    assert response.message == "Record successfully updated"
    assert isinstance(response.data[0], UsageAlertRule)
    assert response.data[0].active is False


def test_legacy_resource_classes_return_models(requests_mock):
    """The original class names use the same typed model layer."""
    requests_mock.get(
        API_BASE_URL + "/users/12345/devices",
        json={"success": True, "data": [{"id": "device"}]},
    )
    requests_mock.get(
        API_BASE_URL + "/users/12345/devices/device/leaks/active",
        json={"success": True, "data": [{"id": "leak", "active": True}]},
    )
    devices = FlumeDeviceList(auth())
    leaks = FlumeLeakList(auth(), "device")

    assert isinstance(devices.device_list[0], Device)
    assert leaks.leak_alert_list[0].active is True
