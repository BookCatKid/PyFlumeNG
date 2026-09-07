"""Retrieve notifications from Flume API."""

from typing import Any, List, Optional, Union, cast

from requests import Session

from .auth import FlumeAuth, FlumePortalAuth  # noqa: WPS300
from .constants import DEFAULT_TIMEOUT  # noqa: WPS300
from .models import Notification, modelize  # noqa: WPS300
from .types import JSONDict, RequestParams  # noqa: WPS300
from .utils import api_url as build_api_url  # noqa: WPS300
from .utils import configure_logger, flume_response_error  # noqa: WPS300

# Configure logging
LOGGER = configure_logger(__name__)


class FlumeNotificationList:
    """Get Flume Notifications list from API."""

    def __init__(  # noqa: WPS211
        self,
        flume_auth: Union[FlumeAuth, FlumePortalAuth],
        http_session: Optional[Session] = None,
        timeout: float = DEFAULT_TIMEOUT,
        read: str = "false",
        sort_direction: str = "ASC",
    ) -> None:
        """
        Initialize the FlumeNotificationList object.

        Args:
            flume_auth: Authentication object.
            http_session: Optional Requests Session().
            timeout: Requests timeout for throttling, default DEFAULT_TIMEOUT.
            read: state of notification list, default "false".
            sort_direction: Which direction to sort notifications on, default "ASC".
        """
        self._timeout: float = timeout
        self._flume_auth: Union[FlumeAuth, FlumePortalAuth] = flume_auth
        self._read: str = read
        self._sort_direction: str = sort_direction
        self._http_session: Session = http_session or Session()
        self.has_next: bool = False
        self.next_page: Optional[str] = None
        self.notification_list: List[Notification] = self.get_notifications()

    def get_notifications(self) -> List[Notification]:
        """Return all notifications from devices owned by the user.

        Returns:
            List[Notification]: Typed notification models.
        """

        api_url = build_api_url(
            self._flume_auth,
            "/users/{0}/notifications".format(self._flume_auth.user_id),
        )

        query_string: RequestParams = {
            "limit": "50",
            "offset": "0",
            "sort_direction": self._sort_direction,
            "read": self._read,
        }

        return self._get_notification_request(api_url, query_string)

    def get_next_notifications(self) -> List[Notification]:
        """Return next page of notification from devices owned by the user.

        Returns:
            Returns JSON list of notifications.

        Raises:
            ValueError: If no next page is available.
        """
        if self.has_next:
            api_url = build_api_url(self._flume_auth, self.next_page or "")
            query_string: RequestParams = {}
        else:
            raise ValueError("No next page available.")
        return self._get_notification_request(api_url, query_string)

    def _has_next_page(self, response_json: Optional[JSONDict]) -> bool:
        """Return True if the next page exists.

        Args:
            response_json (Object): Response from API.

        Returns:
            Boolean: Returns true if next page exists, False if not.
        """
        if response_json is None:
            return False
        pagination = response_json.get("pagination")
        return isinstance(pagination, dict) and pagination.get("next") is not None

    def _get_notification_request(
        self,
        api_url: str,
        query_string: RequestParams,
    ) -> List[Notification]:
        """Make an API request to get usage alerts from the Flume API.

        Args:
            api_url (string): URL for request
            query_string (object): query string options

        Returns:
            object: Reponse in JSON format from API.
        """

        response = self._http_session.request(
            "GET",
            api_url,
            headers=self._flume_auth.authorization_header,
            params=cast(Any, query_string),
            timeout=self._timeout,
        )

        LOGGER.debug(f"_get_notification_request Response: {response.text}")

        # Check for response errors.
        flume_response_error("Impossible to retrieve notifications", response)

        response_json = response.json()
        if self._has_next_page(response_json):
            self.next_page = response_json["pagination"]["next"]
            self.has_next = True
            LOGGER.debug(
                f"Next page for Notification results: {self.next_page}",
            )
        else:
            self.has_next = False
            self.next_page = None
            LOGGER.debug("No further pages for Notification results.")
        return modelize(response_json["data"], Notification)
