"""Basic tests for flume usage alerts. This module contains unittest classes for testing different functionalities of flume."""

# Standard library imports
import unittest

# Third-party imports
import requests_mock

# Local application/library-specific imports
import pyflumeng

from .constants import (
    CONST_CLIENT_ID,
    CONST_CLIENT_SECRET,
    CONST_FLUME_TOKEN,
    CONST_HTTP_METHOD_POST,
    CONST_PASSWORD,
    CONST_TOKEN_FILE,
    CONST_USER_ID,
    CONST_USERNAME,
)
from .utils import load_fixture


class TestFlumeUsageAlerts(unittest.TestCase):
    """Test Flume Usage Alerts Test."""

    @requests_mock.Mocker()
    def test_usage(self, mock):
        """

        Test initialization for Flume Usage Alerts List.

        Args:
            mock: Requests mock.

        """
        mock.register_uri(
            CONST_HTTP_METHOD_POST,
            pyflumeng.constants.URL_OAUTH_TOKEN,
            text=load_fixture(CONST_TOKEN_FILE),
        )
        mock.register_uri(
            "get",
            pyflumeng.constants.API_USAGE_URL.format(user_id=CONST_USER_ID),
            text=load_fixture("usage.json"),
        )
        flume_auth = pyflumeng.FlumeAuth(
            CONST_USERNAME,
            CONST_PASSWORD,
            CONST_CLIENT_ID,
            CONST_CLIENT_SECRET,
            CONST_FLUME_TOKEN,
        )

        flume_alerts = pyflumeng.FlumeUsageAlertList(flume_auth)
        alerts = flume_alerts.get_usage_alerts()
        assert len(alerts) == 50  # noqa: S101, WPS432
        assert isinstance(alerts[0], pyflumeng.UsageAlert)  # noqa: S101
        assert alerts[0]["device_id"] == "6248148189204194987"  # noqa: S101
        assert alerts[0]["event_rule_name"] == "High Flow Alert"  # noqa: S101
        assert flume_alerts.has_next  # noqa: S101

        mock.register_uri(
            "get",
            flume_alerts.next_page,
            text=load_fixture("usage_next.json"),
        )

        alerts_next = flume_alerts.get_next_usage_alerts()
        assert len(alerts_next) == 50  # noqa: S101, WPS432
        assert alerts_next[0]["device_id"] == "6248148189204194987"  # noqa: S101
        assert alerts_next[0]["event_rule_name"] == "High Flow Alert"  # noqa: S101
        assert flume_alerts.has_next is False  # noqa: S101

        mock.register_uri(
            "get",
            pyflumeng.constants.API_USAGE_URL.format(user_id=CONST_USER_ID),
            text=load_fixture("usage_nopage.json"),
        )

        alerts_nopage = flume_alerts.get_usage_alerts()
        assert len(alerts_nopage) == 50  # noqa: S101, WPS432
        assert alerts_nopage[0]["device_id"] == "6248148189204194987"  # noqa: S101
        assert alerts_nopage[0]["event_rule_name"] == "High Flow Alert"  # noqa: S101
        assert flume_alerts.has_next is False  # noqa: S101

    @requests_mock.Mocker()
    def test_usage_alert_rules(self, mock):
        """

        Test fetching and updating usage alert rules for a device.

        Args:
            mock: Requests mock.

        """
        mock.register_uri(
            CONST_HTTP_METHOD_POST,
            pyflumeng.constants.URL_OAUTH_TOKEN,
            text=load_fixture(CONST_TOKEN_FILE),
        )
        mock.register_uri(
            "get",
            pyflumeng.constants.API_USAGE_URL.format(user_id=CONST_USER_ID),
            text=load_fixture("usage_nopage.json"),
        )
        device_id = "6248148189204194987"
        rule_id = "test-rule-01"
        mock.register_uri(
            "get",
            pyflumeng.constants.API_USAGE_RULES_URL.format(
                user_id=CONST_USER_ID,
                device_id=device_id,
            ),
            text=load_fixture("usage_rules.json"),
        )
        mock.register_uri(
            "get",
            pyflumeng.constants.API_USAGE_RULE_URL.format(
                user_id=CONST_USER_ID,
                device_id=device_id,
                rule_id=rule_id,
            ),
            text=load_fixture("usage_rule.json"),
        )
        mock.register_uri(
            "patch",
            pyflumeng.constants.API_USAGE_RULE_URL.format(
                user_id=CONST_USER_ID,
                device_id=device_id,
                rule_id=rule_id,
            ),
            text=load_fixture("usage_rule.json"),
        )
        flume_auth = pyflumeng.FlumeAuth(
            CONST_USERNAME,
            CONST_PASSWORD,
            CONST_CLIENT_ID,
            CONST_CLIENT_SECRET,
            CONST_FLUME_TOKEN,
        )

        flume_alerts = pyflumeng.FlumeUsageAlertList(flume_auth)

        rules = flume_alerts.get_usage_alert_rules(device_id)
        assert len(rules) == 2  # noqa: S101
        assert isinstance(rules[0], pyflumeng.UsageAlertRule)  # noqa: S101
        assert rules[0]["id"] == rule_id  # noqa: S101
        assert rules[0]["active"]  # noqa: S101

        rule = flume_alerts.get_usage_alert_rule(device_id, rule_id)
        assert rule[0]["id"] == rule_id  # noqa: S101

        updated = flume_alerts.set_usage_alert_rule_active(
            device_id,
            rule_id,
            False,
        )
        assert updated[0]["active"] is False  # noqa: S101
        assert mock.last_request.json() == {"active": False}  # noqa: S101
