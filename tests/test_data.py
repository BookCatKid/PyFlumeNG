"""Basic tests for flume Data. This module contains unittest classes for testing different functionalities of flume."""

# Standard library imports
import unittest

import requests_mock

# Third-party imports
from requests import Session

# Local application/library-specific imports
import pyflumeng

from .constants import (
    CONST_CLIENT_ID,
    CONST_CLIENT_SECRET,
    CONST_FLUME_TOKEN,
    CONST_HTTP_METHOD_POST,
    CONST_PASSWORD,
    CONST_SCAN_INTERVAL,
    CONST_TOKEN_FILE,
    CONST_USER_ID,
    CONST_USERNAME,
)
from .utils import load_fixture


class TestFlumeData(unittest.TestCase):
    """Test Flume Data Test."""

    @requests_mock.Mocker()
    def test_data(self, mock):
        """Test initialization for Flume Data.

        Args:
            mock: Requests mock.
        """
        mock.register_uri(
            CONST_HTTP_METHOD_POST,
            pyflumeng.constants.URL_OAUTH_TOKEN,
            text=load_fixture(CONST_TOKEN_FILE),
        )
        mock.register_uri(
            CONST_HTTP_METHOD_POST,
            pyflumeng.constants.API_QUERY_URL.format(
                user_id=CONST_USER_ID,
                device_id="device_id",
            ),
            text=load_fixture("query.json"),
        )

        flume_auth = pyflumeng.FlumeAuth(
            CONST_USERNAME,
            CONST_PASSWORD,
            CONST_CLIENT_ID,
            CONST_CLIENT_SECRET,
            CONST_FLUME_TOKEN,
        )

        flume = pyflumeng.FlumeData(
            flume_auth,
            "device_id",
            "America/Los_Angeles",
            CONST_SCAN_INTERVAL,
            http_session=Session(),
            update_on_init=False,
        )
        assert flume.values == {}  # noqa: S101,WPS520
        flume.update()

        assert flume.values == {  # noqa: S101
            "current_interval": 14.38855184,
            "today": 56.6763912,
            "week_to_date": 1406.07065872,
            "month_to_date": 56.6763912,
            "last_60_min": 14.38855184,
            "last_24_hrs": 258.9557672,
            "last_30_days": 5433.56753264,
        }

    @requests_mock.Mocker()
    def test_custom_query_payload_is_preserved(self, mock):
        """A caller-supplied query payload must be sent unchanged on update."""
        mock.register_uri(
            CONST_HTTP_METHOD_POST,
            pyflumeng.constants.URL_OAUTH_TOKEN,
            text=load_fixture(CONST_TOKEN_FILE),
        )
        query_url = pyflumeng.constants.API_QUERY_URL.format(
            user_id=CONST_USER_ID,
            device_id="device_id",
        )
        mock.register_uri(
            CONST_HTTP_METHOD_POST,
            query_url,
            json={"data": [{"custom": [{"value": 12.5}]}]},
        )
        custom_payload = {
            "queries": [
                {
                    "request_id": "custom",
                    "bucket": "MIN",
                    "since_datetime": "2026-09-06 12:00:00",
                    "until_datetime": "2026-09-06 13:00:00",
                    "operation": "SUM",
                    "units": "GALLONS",
                }
            ]
        }
        flume_auth = pyflumeng.FlumeAuth(
            CONST_USERNAME,
            CONST_PASSWORD,
            CONST_CLIENT_ID,
            CONST_CLIENT_SECRET,
            CONST_FLUME_TOKEN,
        )

        flume = pyflumeng.FlumeData(
            flume_auth,
            "device_id",
            "America/Los_Angeles",
            query_payload=custom_payload,
            http_session=Session(),
            update_on_init=False,
        )
        flume.update_force()

        assert mock.last_request.json() == custom_payload  # noqa: S101
        assert flume.query_payload == custom_payload  # noqa: S101
        assert flume.values == {"custom": 12.5}  # noqa: S101

    def test_generate_api_query_payload_is_public_class_method(self):
        """The default query payload can be generated without an instance."""
        payload = pyflumeng.FlumeData.generate_api_query_payload(
            CONST_SCAN_INTERVAL,
            "America/Los_Angeles",
        )

        assert [query["request_id"] for query in payload["queries"]] == [  # noqa: S101
            "current_interval",
            "today",
            "week_to_date",
            "month_to_date",
            "last_60_min",
            "last_24_hrs",
            "last_30_days",
        ]
