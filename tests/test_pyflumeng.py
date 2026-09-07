"""Tests for the standalone PyFlumeNG package."""

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest

from pyflumeng import (
    AccuracyResult,
    Budget,
    Device,
    DoNotAlertSchedule,
    FlumeClient,
    FlumeData,
    FlumeNotificationList,
    FlumePortalAuth,
    FlumeResponse,
    FlumeUsageAlertList,
    Notification,
    PersonalAuth,
    Span,
    SpanDataPoint,
    UsageAlertRule,
    UsageAlertSchedule,
    UsageBreakdown,
    UsageBreakdownCategory,
)
from pyflumeng.auth import PORTAL_OAUTH_AUTHORIZE_URL, PORTAL_OAUTH_TOKEN_URL
from pyflumeng.constants import API_BASE_URL, PORTAL_API_URL, URL_OAUTH_TOKEN
from pyflumeng.devices import FlumeDeviceList
from pyflumeng.errors import FlumeCapabilityError, FlumeRateLimitError
from pyflumeng.leak import FlumeLeakList
from pyflumeng.rate_limit import RateLimitState

PortalAuth = FlumePortalAuth
PORTAL_AUTHORIZE_URL = PORTAL_OAUTH_AUTHORIZE_URL
PERSONAL_TOKEN_URL = URL_OAUTH_TOKEN
PORTAL_TOKEN_URL = PORTAL_OAUTH_TOKEN_URL


TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJ1c2VyX2lkIjoxMjM0NSwiZXhwIjoyOTk5OTk5OTk3LCJ4IjoiZmFrZSJ9."
    "test-signature-pyflumengng"
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


def test_portal_auth_refreshes_five_minutes_before_expiry(requests_mock):
    """Portal auth uses the frontend's five-minute JWT refresh buffer."""
    portal = PortalAuth("user@example.com", "password", flume_token=token())
    assert portal._decoded_token is not None
    portal._decoded_token["exp"] = int(
        (datetime.now(timezone.utc) + timedelta(minutes=6)).timestamp()
    )
    requests_mock.post(
        PORTAL_TOKEN_URL,
        json={"data": [token("read update delete")], "success": True},
    )

    portal.ensure_valid()
    assert requests_mock.call_count == 0

    portal._decoded_token["exp"] = int(
        (datetime.now(timezone.utc) + timedelta(minutes=4)).timestamp()
    )
    portal.ensure_valid()
    assert requests_mock.call_count == 1


def test_portal_logout_revokes_refresh_token_and_clears_auth(requests_mock):
    """Logout mirrors the portal's refresh-token revocation request."""
    requests_mock.post(
        PORTAL_API_URL + "/oauth/logout",
        json={"success": True, "data": []},
    )
    portal = PortalAuth("user@example.com", "password", flume_token=token())

    result = portal.logout()

    assert result["success"] is True
    assert requests_mock.last_request.json() == {"refresh_token": "refresh-token"}
    assert portal.token is None
    assert portal.user_id is None
    assert portal.authorization_header is None


def test_client_returns_envelope_and_follows_pagination(requests_mock):
    """The raw client preserves envelopes while list_all flattens pages."""
    first_url = PORTAL_API_URL + "/users/12345/devices"
    next_url = PORTAL_API_URL + "/users/12345/devices?offset=1&limit=1"
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


def test_list_devices_matches_portal_pagination_query(requests_mock):
    """Device listing uses the portal's 2,000-record first page."""
    url = API_BASE_URL + "/users/12345/devices"
    requests_mock.get(url, json={"success": True, "data": [{"id": "device"}]})
    client = FlumeClient(auth())

    devices = client.list_devices(user=True, location=True)

    assert [device.id for device in devices] == ["device"]
    assert requests_mock.last_request.query == (
        "user=true&location=true&limit=2000&offset=0"
    )


def test_usage_rule_read_does_not_change_legacy_usage_pagination(requests_mock):
    """Rule reads must not make an existing usage-alert page unavailable."""
    from pyflumeng import FlumeUsageAlertList

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


def test_portal_rate_limit_is_confirmed_from_response_headers(requests_mock):
    """Portal responses advertise the observed 72,000-request quota."""
    requests_mock.get(
        PORTAL_API_URL + "/users/12345",
        headers={
            "X-RateLimit-Limit": "72000",
            "X-RateLimit-Remaining": "71980",
            "X-RateLimit-Reset": "1788677989",
        },
        json={"success": True, "data": [{"id": 12345}]},
    )
    client = FlumeClient(
        PortalAuth("user@example.com", "password", flume_token=token())
    )

    client.get_user()

    assert client.rate_limit.limit == 72000
    assert client.rate_limit.remaining == 71980
    assert client.rate_limit.reset == 1788677989


def test_usage_rule_update_uses_portal_endpoint_and_json(requests_mock):
    """Rule updates use the portal-capable endpoint and preserve empty data."""
    url = PORTAL_API_URL + "/users/12345/devices/device/rules/usage-alerts/rule"
    requests_mock.patch(url, json={"success": True, "code": 612, "data": []})
    client = FlumeClient(
        PortalAuth("user@example.com", "password", flume_token=token())
    )

    result = client.set_usage_alert_rule_active("device", "rule", False)

    assert result == []
    assert requests_mock.last_request.json() == {"active": False}


def test_usage_rule_create_and_delete_use_guarded_unprefixed_methods(requests_mock):
    """Rule CRUD uses the normal names while enforcing portal write scope."""
    collection = PORTAL_API_URL + "/users/12345/devices/device/rules/usage-alerts"
    item = collection + "/rule"
    requests_mock.post(collection, json={"success": True, "data": [{"id": "rule"}]})
    requests_mock.delete(item, json={"success": True, "data": []})
    client = FlumeClient(
        PortalAuth("user@example.com", "password", flume_token=token())
    )

    created = client.create_usage_alert_rule("device", {"name": "Irrigation"})
    deleted = client.delete_usage_alert_rule("device", "rule")

    assert created == [{"id": "rule"}]
    assert deleted == []
    assert requests_mock.request_history[0].json() == {"name": "Irrigation"}

    personal_client = FlumeClient(auth())
    with pytest.raises(FlumeCapabilityError, match="PortalAuth"):
        personal_client.delete_usage_alert_rule("device", "rule")


def test_personal_auth_rejects_portal_rule_write_before_transport(requests_mock):
    """Personal auth reports missing portal capability without an HTTP call."""
    client = FlumeClient(auth())

    with pytest.raises(FlumeCapabilityError, match="PortalAuth"):
        client.set_usage_alert_rule_active("device", "rule", False)

    assert requests_mock.call_count == 0


def test_portal_query_batches_and_combines_more_than_ten_queries(requests_mock):
    """Portal queries reproduce the frontend's ten-query request limit."""
    url = PORTAL_API_URL + "/users/12345/devices/device/query"
    requests_mock.post(
        url,
        [
            {"json": {"success": True, "data": [{"first": [{"value": 1}]}]}},
            {"json": {"success": True, "data": [{"second": [{"value": 2}]}]}},
        ],
    )
    client = FlumeClient(
        PortalAuth("user@example.com", "password", flume_token=token())
    )
    queries = [{"request_id": str(index)} for index in range(12)]

    result = client.portal_query("device", {"queries": queries})

    assert len(requests_mock.request_history) == 2
    assert len(requests_mock.request_history[0].json()["queries"]) == 10
    assert len(requests_mock.request_history[1].json()["queries"]) == 2
    assert result[0].to_dict() == {
        "first": [{"value": 1}],
        "second": [{"value": 2}],
    }


def test_portal_resource_wrappers_match_frontend_routes(requests_mock):
    """Named portal wrappers preserve frontend paths, query, and payloads."""
    requests_mock.get(
        PORTAL_API_URL + "/location-profiles",
        json={"success": True, "data": [{"field": "toilet"}]},
    )
    requests_mock.patch(
        PORTAL_API_URL + "/users/12345/devices/device/spans/span",
        json={"success": True, "data": []},
    )
    requests_mock.patch(
        PORTAL_API_URL
        + "/users/12345/devices/device/rules/usage-alerts/rule/do-not-alert-schedules/16158",
        json={"success": True, "data": []},
    )
    client = FlumeClient(
        PortalAuth("user@example.com", "password", flume_token=token())
    )

    assert client.get_location_profiles()["field"] == "toilet"
    client.update_span_type("device", "span", "IRRIGATION")
    assert requests_mock.request_history[-1].json() == {"type": "IRRIGATION"}
    client.toggle_usage_alert_schedule("device", "rule", 16158, False)
    assert requests_mock.last_request.path.endswith(
        "/rules/usage-alerts/rule/do-not-alert-schedules/16158",
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


def test_usage_breakdown_matches_live_portal_rollup_and_total_query(requests_mock):
    """Breakdown uses whole-house SUM and derives Indoor from live raw spans."""
    requests_mock.get(
        PORTAL_API_URL + "/users/12345/devices/device/spans",
        json={
            "success": True,
            "data": [
                {"id": "1", "type": "IRRIGATION", "total": 1732.58617265},
                {"id": "2", "type": "OUTDOOR", "total": 4.3016936},
                {"id": "3", "type": "SHOWER", "total": 429.9163192},
                {"id": "4", "type": "TOILET", "total": 228.4642123},
                {"id": "5", "type": "CLOTHES_WASHER", "total": 224.0676284},
                {"id": "6", "type": "DISH_WASHER", "total": 13.26882695},
            ],
        },
    )
    query_url = PORTAL_API_URL + "/users/12345/devices/device/query"
    requests_mock.post(
        query_url,
        json={
            "success": True,
            "data": [{"usage_breakdown_total": [{"value": 3645.51}]}],
        },
    )
    requests_mock.get(
        PORTAL_API_URL + "/users/12345/locations/location/span-types",
        json={
            "success": True,
            "data": [
                {
                    "name": "OUTDOOR",
                    "display_name": "Outdoor Unknown",
                    "labeled_as": "Outdoor (Other)",
                    "can_view": True,
                },
                {"name": "INDOOR", "display_name": "Indoor", "can_view": True},
                {"name": "SHOWER", "display_name": "Shower", "can_view": True},
                {"name": "TOILET", "display_name": "Toilet", "can_view": True},
                {
                    "name": "CLOTHES_WASHER",
                    "display_name": "Clothes Washer",
                    "can_view": True,
                },
                {
                    "name": "DISH_WASHER",
                    "display_name": "Dishwasher",
                    "can_view": True,
                },
                {
                    "name": "FUTURE_FIXTURE",
                    "display_name": "Future Fixture",
                    "can_view": True,
                },
            ],
        },
    )
    client = FlumeClient(
        PortalAuth("user@example.com", "password", flume_token=token())
    )

    breakdown = client.get_usage_breakdown(
        "device",
        "2026-09-01 00:00:00",
        "2026-09-06 23:59:59",
        location_id="location",
    )

    assert isinstance(breakdown, UsageBreakdown)
    assert isinstance(breakdown.categories[0], UsageBreakdownCategory)
    assert breakdown.total_usage == pytest.approx(3645.51)
    assert [category.type for category in breakdown.categories] == [
        "OUTDOOR",
        "INDOOR",
        "SHOWER",
        "TOILET",
        "CLOTHES_WASHER",
        "DISH_WASHER",
    ]
    assert breakdown.category("OUTDOOR").usage == pytest.approx(1736.88786625)
    assert breakdown.category("OUTDOOR").display_name == "Outdoor"
    assert breakdown.category("INDOOR").span_count == 0
    assert breakdown.category("INDOOR").usage == pytest.approx(1012.9051469)
    assert [category.rounded_percentage for category in breakdown.categories] == [
        48,
        28,
        12,
        6,
        6,
        0,
    ]
    assert breakdown.category("clothes_washer").usage == pytest.approx(224.0676284)
    assert breakdown.category("DISH_WASHER").display_name == "Dishwasher"
    assert requests_mock.call_count == 3
    sent_query = parse_qs(urlsplit(requests_mock.request_history[1].url).query)
    assert "FUTURE_FIXTURE" in sent_query["types"][0].split(",")
    assert "IRRIGATION" in sent_query["types"][0].split(",")
    assert requests_mock.request_history[2].url == query_url
    assert requests_mock.request_history[2].json() == {
        "queries": [
            {
                "request_id": "usage_breakdown_total",
                "bucket": "MON",
                "since_datetime": "2026-09-01 00:00:00",
                "until_datetime": "2026-09-06 23:59:59",
                "operation": "SUM",
                "units": "GALLONS",
            }
        ]
    }


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
        "data:image/jpeg;base64,before-image",
        "data:image/png;base64,after-image",
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


def test_budget_progress_helpers_expose_used_target_and_percentage():
    """Budget helpers provide dashboard-ready progress without changing API data."""
    budget = Budget({"id": 1, "value": 1000, "actual": 375.5})
    over = Budget({"id": 2, "value": 100, "actual": 125})
    pending = Budget({"id": 3, "value": 0})

    assert budget.target == 1000.0
    assert budget.used == 375.5
    assert budget.remaining == 624.5
    assert budget.percentage_used == pytest.approx(37.55)
    assert budget.is_over_budget is False
    assert over.remaining == -25.0
    assert over.percentage_used == 125.0
    assert over.is_over_budget is True
    assert pending.used is None
    assert pending.percentage_used is None
    assert pending.is_over_budget is None
    assert budget.to_dict() == {"id": 1, "value": 1000, "actual": 375.5}


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


def test_do_not_alert_schedule_has_single_resource_read_and_guarded_writes(
    requests_mock,
):
    """DNA schedule CRUD has coherent unprefixed helpers and portal write guards."""
    collection = PORTAL_API_URL + "/users/12345/devices/device/do-not-alert-schedules"
    url = collection + "/16158"
    requests_mock.get(
        url,
        json={"success": True, "data": [{"id": 16158, "name": "Irrigation"}]},
    )
    requests_mock.post(
        collection,
        json={"success": True, "data": [{"id": 16158, "name": "Irrigation"}]},
    )
    requests_mock.patch(url, json={"success": True, "data": []})
    requests_mock.delete(url, json={"success": True, "data": []})
    client = FlumeClient(
        PortalAuth("user@example.com", "password", flume_token=token())
    )

    schedule = client.get_do_not_alert_schedule("device", 16158)
    created = client.create_do_not_alert_schedule("device", {"name": "Irrigation"})
    client.update_do_not_alert_schedule("device", 16158, {"name": "Sprinklers"})
    deleted = client.delete_do_not_alert_schedule("device", 16158)

    assert isinstance(schedule, DoNotAlertSchedule)
    assert schedule.name == "Irrigation"
    assert created == [{"id": 16158, "name": "Irrigation"}]
    assert requests_mock.request_history[2].json() == {"name": "Sprinklers"}
    assert deleted == []

    personal_client = FlumeClient(auth())
    with pytest.raises(FlumeCapabilityError, match="PortalAuth"):
        personal_client.create_do_not_alert_schedule("device", {"name": "blocked"})


def test_portal_read_aliases_use_working_user_scoped_routes(requests_mock):
    """Portal read aliases do not call the invalid guessed root routes."""
    requests_mock.get(
        PORTAL_API_URL + "/users/12345/devices",
        json={"success": True, "data": [{"id": "device"}]},
    )
    requests_mock.get(
        PORTAL_API_URL + "/users/12345/notifications",
        json={"success": True, "data": [{"id": "notice"}]},
    )
    requests_mock.get(
        PORTAL_API_URL + "/users/12345/devices/device/query/active",
        json={"success": True, "data": [{"active": True, "gpm": 1.5}]},
    )
    client = FlumeClient(
        PortalAuth("user@example.com", "password", flume_token=token())
    )

    assert client.list_portal_devices()[0].id == "device"
    assert client.list_portal_notifications()[0].id == "notice"
    assert client.get_portal_current_flow("device").gpm == 1.5

    assert client.base_url == PORTAL_API_URL


def test_get_notification_filters_collection_because_item_get_is_not_supported(
    requests_mock,
):
    """Single-notification reads use the collection route seen on the live API."""
    requests_mock.get(
        PORTAL_API_URL + "/users/12345/notifications",
        json={
            "success": True,
            "data": [{"id": "first"}, {"id": "wanted"}],
            "pagination": None,
        },
    )
    client = FlumeClient(
        PortalAuth("user@example.com", "password", flume_token=token())
    )

    notification = client.get_notification("wanted")

    assert notification is not None
    assert notification.id == "wanted"
    assert requests_mock.call_count == 1
    assert requests_mock.last_request.path == "/users/12345/notifications"


def test_portal_services_match_frontend_user_scoped_routes(requests_mock):
    """Portal services use the user prefix applied by the frontend fetch layer."""
    requests_mock.post(
        PORTAL_API_URL + "/users/12345/locations",
        json={"success": True, "data": [{"id": "location"}]},
    )
    requests_mock.patch(
        PORTAL_API_URL + "/users/12345/notifications/notice",
        json={"success": True, "data": []},
    )
    requests_mock.post(
        PORTAL_API_URL + "/users/12345/locations/location/access",
        json={"success": True, "data": []},
    )
    requests_mock.get(
        PORTAL_API_URL + "/users/12345/clients",
        json={"success": True, "data": [{"name": "client"}]},
    )
    client = FlumeClient(
        PortalAuth(
            "user@example.com", "password", flume_token=token("read update delete")
        )
    )

    client.create_portal_location({"name": "test"})
    client.update_portal_notification("notice", {"read": True})
    client.grant_portal_location_access(
        "location", {"email_address": "guest@example.com"}
    )
    assert client.list_portal_clients()[0].name == "client"

    assert [request.path for request in requests_mock.request_history] == [
        "/users/12345/locations",
        "/users/12345/notifications/notice",
        "/users/12345/locations/location/access",
        "/users/12345/clients",
    ]


def test_legacy_helpers_use_portal_host_and_keep_pagination_on_portal(requests_mock):
    """Legacy helpers route PortalAuth reads and next pages to api.flumewater.com."""
    auth_obj = PortalAuth("user@example.com", "password", flume_token=token())
    devices_url = PORTAL_API_URL + "/users/12345/devices"
    query_url = PORTAL_API_URL + "/users/12345/devices/device/query"
    leak_url = PORTAL_API_URL + "/users/12345/devices/device/leaks/active"
    notifications_url = PORTAL_API_URL + "/users/12345/notifications"
    notification_next = "/users/12345/notifications?offset=1&limit=1"
    usage_url = PORTAL_API_URL + "/users/12345/usage-alerts"
    usage_next = "/users/12345/usage-alerts?offset=1&limit=1"

    requests_mock.get(
        devices_url,
        json={"success": True, "data": [{"id": "device"}]},
    )
    requests_mock.post(
        query_url,
        json={"success": True, "data": [{"window": [{"value": 12.5}]}]},
    )
    requests_mock.get(
        leak_url,
        json={"success": True, "data": [{"id": "leak", "active": True}]},
    )
    requests_mock.get(
        notifications_url,
        json={
            "success": True,
            "data": [{"id": "notice-1"}],
            "pagination": {"next": notification_next},
        },
    )
    requests_mock.get(
        PORTAL_API_URL + notification_next,
        json={"success": True, "data": [{"id": "notice-2"}], "pagination": None},
    )
    requests_mock.get(
        usage_url,
        json={
            "success": True,
            "data": [{"id": "usage-1"}],
            "pagination": {"next": usage_next},
        },
    )
    requests_mock.get(
        PORTAL_API_URL + usage_next,
        json={"success": True, "data": [{"id": "usage-2"}], "pagination": None},
    )

    assert FlumeDeviceList(auth_obj).device_list[0].id == "device"
    data = FlumeData(
        auth_obj,
        "device",
        "America/Los_Angeles",
        query_payload={
            "queries": [
                {
                    "request_id": "window",
                    "bucket": "MON",
                    "since_datetime": "2026-09-01 00:00:00",
                    "until_datetime": "2026-09-06 21:02:00",
                    "operation": "SUM",
                    "units": "GALLONS",
                }
            ]
        },
        update_on_init=False,
    )
    data.update_force()
    assert data.values == {"window": 12.5}
    assert FlumeLeakList(auth_obj, "device").leak_alert_list[0].active is True

    notices = FlumeNotificationList(auth_obj)
    assert notices.notification_list[0].id == "notice-1"
    assert notices.get_next_notifications()[0].id == "notice-2"

    usage = FlumeUsageAlertList(auth_obj)
    assert usage.usage_alert_list[0].id == "usage-1"
    assert usage.get_next_usage_alerts()[0].id == "usage-2"

    assert all(
        request.url.startswith(PORTAL_API_URL)
        for request in requests_mock.request_history
    )


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


def test_list_spans_rejects_string_span_types(requests_mock):
    """A single string must not be split into one-character span types."""
    url = API_BASE_URL + "/users/12345/devices/device/spans"
    requests_mock.get(url, json={"success": True, "data": []})
    client = FlumeClient(auth())

    with pytest.raises(TypeError, match="span_types"):
        client.list_spans(
            "device",
            "2026-09-06 10:00:00",
            "2026-09-06 11:00:00",
            span_types="OUTDOOR",  # type: ignore[arg-type]
        )
