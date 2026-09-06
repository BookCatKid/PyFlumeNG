"""Authenticates to Flume API."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Dict, FrozenSet, Mapping, Optional, cast
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import jwt  # install pyjwt
from jwt.types import Options
from requests import Session

from .constants import (  # noqa: WPS300
    DEFAULT_TIMEOUT,
    PORTAL_API_URL,
    PORTAL_CLIENT_ID,
    PORTAL_OAUTH_AUTHORIZE_URL,
    PORTAL_OAUTH_TOKEN_URL,
    PORTAL_REDIRECT_URI,
    URL_OAUTH_TOKEN,
)
from .rate_limit import RateLimitState  # noqa: WPS300
from .types import FlumeToken, JSONDict, ResourceId  # noqa: WPS300
from .utils import (  # noqa: WPS300
    FlumeResponseError,
    configure_logger,
    flume_response_error,
)

# Configure logging
LOGGER = configure_logger(__name__)


def _validated_token(token: Mapping[str, Any]) -> FlumeToken:
    """Validate required OAuth token fields while preserving extra fields."""
    access_token = token.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise FlumeResponseError(
            "Flume token response did not include an access token."
        )
    return cast(FlumeToken, cast(object, dict(token)))


class FlumeAuth:  # noqa: WPS214
    """Interact with API Authentication."""

    capabilities: ClassVar[FrozenSet[str]] = frozenset({"personal_api"})

    def __init__(  # noqa: WPS211
        self,
        username: str,
        password: str,
        client_id: str,
        client_secret: str,
        flume_token: Optional[Mapping[str, Any]] = None,
        http_session: Optional[Session] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """

        Initialize the data object.

        Args:
            username: Username to authenticate.
            password: Password to authenticate.
            client_id: API client id.
            client_secret: API client secret.
            flume_token: Pass flume token to variable.
            http_session: Requests Session()
            timeout: Requests timeout for throttling.

        """

        self._creds: Dict[str, str] = {
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
        }

        if http_session is None:
            self._http_session = Session()
        else:
            self._http_session = http_session

        self._timeout: float = timeout
        self._token: Optional[FlumeToken] = None
        self._decoded_token: Optional[Dict[str, Any]] = None
        self.user_id: Optional[ResourceId] = None
        self.authorization_header: Optional[Dict[str, str]] = None
        self.rate_limit: RateLimitState = RateLimitState(120)

        self._load_token(flume_token)
        self._verify_token()

    @property
    def token(self) -> Optional[FlumeToken]:
        """
            Return authorization token for session.

        Returns:
            Returns the current JWT token.

        """
        return self._token

    def refresh_token(self) -> None:
        """Refresh authorization token for session."""
        if self._token is None or "refresh_token" not in self._token:
            self.retrieve_token()
            return
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._token["refresh_token"],
            "client_id": self._creds["client_id"],
            "client_secret": self._creds["client_secret"],
        }

        self._load_token(self._request_token(payload))

    def refresh(self) -> None:
        """Refresh through the common PyFlumeNG auth interface."""
        self.refresh_token()

    def ensure_valid(self) -> None:
        """Refresh when the token expires within twelve hours."""
        self._verify_token()

    def retrieve_token(self) -> None:
        """Return authorization token for session."""

        payload = dict({"grant_type": "password"}, **self._creds)
        self._load_token(self._request_token(payload))

    def _load_token(self, token: Optional[Mapping[str, Any]]) -> None:
        """
        Update _token, decode token, user_id and auth header.

        Args:
            token: Authentication bearer token to be decoded.

        """
        if token is None:
            self.retrieve_token()
            return

        jwt_options: Options = {"verify_signature": False}
        self._token = _validated_token(token)
        try:
            self._decoded_token = jwt.decode(
                self._token["access_token"],
                options=jwt_options,
            )
        except jwt.exceptions.DecodeError:
            LOGGER.debug("Poorly formatted Access Token, fetching token using _creds")
            self.retrieve_token()
        except TypeError:
            LOGGER.debug("Token TypeError, fetching token using _creds")
            self.retrieve_token()

        if self._decoded_token is None:
            raise FlumeResponseError("Flume token could not be decoded.")
        self.user_id = self._decoded_token["user_id"]

        self.authorization_header = {
            "authorization": "Bearer {0}".format(self._token.get("access_token")),
        }

    def _request_token(self, payload: Mapping[str, str]) -> FlumeToken:
        """

        Request Authorization Payload.

        Args:
            payload: Request payload to get token request.

        Returns:
            Return response Authentication Bearer token from request.

        """

        headers = {"content-type": "application/json"}
        response = self._http_session.request(
            "POST",
            URL_OAUTH_TOKEN,
            json=payload,
            headers=headers,
            timeout=self._timeout,
        )

        LOGGER.debug("Token Payload: %s", payload)  # noqa: WPS323
        LOGGER.debug("Token Response: %s", response.text)  # noqa: WPS323

        # Check for response errors.
        flume_response_error(
            "Can't get token for user {0}".format(self._creds.get("username")),
            response,
        )

        token_data = json.loads(response.text)["data"][0]
        if not isinstance(token_data, Mapping):
            raise FlumeResponseError("Flume token response was not an object.")
        return _validated_token(token_data)

    def _verify_token(self) -> None:
        """Check to see if token is expiring in 12 hours."""
        if self._decoded_token is None:
            self.retrieve_token()
        if self._decoded_token is None:
            raise FlumeResponseError("Flume token could not be decoded.")
        token_expiration = datetime.fromtimestamp(
            self._decoded_token["exp"], tz=timezone.utc
        )
        time_difference = datetime.now(timezone.utc) + timedelta(hours=12)  # noqa: WPS432
        LOGGER.debug("Token expiration time: %s", token_expiration)  # noqa: WPS323
        LOGGER.debug("Token comparison time: %s", time_difference)  # noqa: WPS323

        if token_expiration <= time_difference:
            self.refresh_token()


class FlumePortalAuth:  # noqa: WPS214
    """Authenticate using the customer portal OAuth authorization-code flow.

    The Personal API password grant produces a token with ``update:personal``
    scope, but usage-alert rule writes require the portal's ``customer-portal``
    client and its broader ``update`` scope.
    """

    capabilities: ClassVar[FrozenSet[str]] = frozenset(
        {"personal_api", "portal_api", "portal_writes"}
    )

    def __init__(
        self,
        username: str,
        password: str,
        flume_token: Optional[Mapping[str, Any]] = None,
        http_session: Optional[Session] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize portal authentication."""
        self._username: str = username
        self._password: str = password
        self._timeout: float = timeout
        self._http_session: Session = http_session or Session()
        self._token: Optional[FlumeToken] = None
        self._decoded_token: Optional[Dict[str, Any]] = None
        self.user_id: Optional[ResourceId] = None
        self.authorization_header: Optional[Dict[str, str]] = None
        self.rate_limit: RateLimitState = RateLimitState(72000)

        if flume_token is None:
            self.retrieve_token()
        else:
            self._load_token(flume_token)
        self._verify_token()

    @property
    def token(self) -> Optional[FlumeToken]:
        """Return the current portal token response."""
        return self._token

    def retrieve_token(self) -> None:
        """Authenticate through the portal and exchange the authorization code."""
        state = uuid4().hex
        response = self._http_session.get(
            PORTAL_API_URL + "/account/login",
            params={
                "client_id": PORTAL_CLIENT_ID,
                "redirect_uri": PORTAL_REDIRECT_URI,
                "state": state,
                "response_type": "code",
            },
            timeout=self._timeout,
        )
        flume_response_error("Can't open portal login", response)
        response = self._http_session.post(
            PORTAL_OAUTH_AUTHORIZE_URL,
            data={
                "username": self._username,
                "password": self._password,
                "response_type": "code",
                "client_id": PORTAL_CLIENT_ID,
                "redirect_uri": PORTAL_REDIRECT_URI,
                "state": state,
            },
            allow_redirects=False,
            timeout=self._timeout,
        )

        if response.status_code not in (301, 302, 303, 307, 308):
            raise FlumeResponseError(
                "Can't authorize user {0}. Response code returned:{1}.".format(
                    self._username,
                    response.status_code,
                ),
            )

        location = response.headers.get("Location")
        params = parse_qs(urlparse(location or "").query)
        code = params.get("code", [None])[0]
        returned_state = params.get("state", [None])[0]
        error = params.get("error", [None])[0]
        if error:
            raise FlumeResponseError(
                "Portal authorization failed: {0}".format(error),
            )
        if code is None or returned_state != state:
            raise FlumeResponseError(
                "Portal authorization did not return a valid code.",
            )

        self._load_token(
            self._request_portal_token(
                {
                    "client_id": PORTAL_CLIENT_ID,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": PORTAL_REDIRECT_URI,
                }
            )
        )

    def refresh_token(self) -> None:
        """Refresh the portal token using its form-encoded refresh flow."""
        if self._token is None or "refresh_token" not in self._token:
            self.retrieve_token()
            return
        response = self._http_session.post(
            PORTAL_OAUTH_TOKEN_URL,
            data=(
                "grant_type=refresh_token&client_id={0}&refresh_token={1}".format(
                    PORTAL_CLIENT_ID,
                    self._token["refresh_token"],
                )
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self._timeout,
        )
        flume_response_error("Can't refresh portal token", response)
        self._load_token(response.json()["data"][0])

    def refresh(self) -> None:
        """Refresh through the common PyFlumeNG auth interface."""
        self.refresh_token()

    def ensure_valid(self) -> None:
        """Refresh when the token expires within twelve hours."""
        self._verify_token()

    def _load_token(self, token: Mapping[str, Any]) -> None:
        """Update token, user ID, decoded claims, and authorization header."""
        self._token = _validated_token(token)
        decoded_token = jwt.decode(
            self._token["access_token"],
            options={"verify_signature": False},
        )
        self._decoded_token = decoded_token
        self.user_id = decoded_token["user_id"]
        self.authorization_header = {
            "authorization": "Bearer {0}".format(self._token["access_token"]),
        }

    def _request_portal_token(self, payload: JSONDict) -> FlumeToken:
        """Exchange a portal authorization code for an access token."""
        response = self._http_session.post(
            PORTAL_OAUTH_TOKEN_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self._timeout,
        )
        flume_response_error("Can't get portal token", response)
        token_data = response.json()["data"][0]
        if not isinstance(token_data, Mapping):
            raise FlumeResponseError("Flume portal token response was not an object.")
        return _validated_token(token_data)

    def _verify_token(self) -> None:
        """Refresh when the token expires within twelve hours."""
        if self._decoded_token is None:
            self.retrieve_token()
        if self._decoded_token is None:
            raise FlumeResponseError("Flume portal token could not be decoded.")
        token_expiration = datetime.fromtimestamp(
            self._decoded_token["exp"], tz=timezone.utc
        )
        time_difference = datetime.now(timezone.utc) + timedelta(hours=12)  # noqa: WPS432
        if token_expiration <= time_difference:
            self.refresh_token()
