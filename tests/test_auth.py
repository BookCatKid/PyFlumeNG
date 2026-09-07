"""Basic tests for flume Auth. This module contains unittest classes for testing different functionalities of flume."""

# Standard library imports
import unittest
from urllib.parse import parse_qs

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
    CONST_TOKEN_FILE,
    CONST_USER_ID,
    CONST_USERNAME,
)
from .utils import load_fixture


class TestFlumeAuth(unittest.TestCase):
    """Flume Auth Test Case."""

    @requests_mock.Mocker()
    def test_auth(self, mock):
        """

        Test initialization for Flume Auth.

        Args:
            mock: Requests mock.

        """
        mock.register_uri(
            CONST_HTTP_METHOD_POST,
            pyflumeng.constants.URL_OAUTH_TOKEN,
            text=load_fixture(CONST_TOKEN_FILE),
        )
        auth = pyflumeng.FlumeAuth(
            CONST_USERNAME,
            CONST_PASSWORD,
            CONST_CLIENT_ID,
            CONST_CLIENT_SECRET,
            CONST_FLUME_TOKEN,
            http_session=Session(),
        )
        assert auth.user_id == CONST_USER_ID  # noqa: S101

    @requests_mock.Mocker()
    def test_portal_auth(self, mock):
        """Test the customer portal authorization-code flow."""
        mock.register_uri(
            "get",
            pyflumeng.constants.PORTAL_API_URL + "/account/login",
            text="<form />",
        )

        def authorize(request, context):
            state = parse_qs(request.text)["state"][0]
            context.status_code = 302
            context.headers["Location"] = "{0}?code=test-code&state={1}".format(
                pyflumeng.constants.PORTAL_REDIRECT_URI,
                state,
            )
            return ""

        mock.register_uri(
            "post",
            pyflumeng.constants.PORTAL_OAUTH_AUTHORIZE_URL,
            text=authorize,
        )
        mock.register_uri(
            "post",
            pyflumeng.constants.PORTAL_OAUTH_TOKEN_URL,
            text=load_fixture(CONST_TOKEN_FILE),
        )

        auth = pyflumeng.FlumePortalAuth(CONST_USERNAME, CONST_PASSWORD)
        assert auth.user_id == CONST_USER_ID  # noqa: S101
        assert auth.authorization_header["authorization"].startswith("Bearer ")
