"""Retrieve leak notifications from the Flume API."""

from typing import List, Optional, Union

from requests import Session

from .auth import FlumeAuth, FlumePortalAuth  # noqa: WPS300
from .constants import API_LEAK_URL, DEFAULT_TIMEOUT  # noqa: WPS300
from .models import Leak, modelize  # noqa: WPS300
from .types import ResourceId  # noqa: WPS300
from .utils import configure_logger, flume_response_error  # noqa: WPS300

# Configure logging
LOGGER = configure_logger(__name__)


class FlumeLeakList:
    """Get Flume Flume Leak Notifications from API."""

    def __init__(  # noqa: WPS211
        self,
        flume_auth: Union[FlumeAuth, FlumePortalAuth],
        device_id: ResourceId,
        http_session: Optional[Session] = None,
        timeout: float = DEFAULT_TIMEOUT,
        read: str = "false",
    ) -> None:
        """

        Initialize the data object.

        Args:
            flume_auth: Authentication object.
            device_id: The Device ID to query.
            http_session: Requests Session()
            timeout: Requests timeout for throttling.
            read: state of leak notification list, have they been read, not read.

        """
        self._timeout: float = timeout
        self._flume_auth: Union[FlumeAuth, FlumePortalAuth] = flume_auth
        self._read: str = read
        self.device_id: ResourceId = device_id

        if http_session is None:
            self._http_session: Session = Session()
        else:
            self._http_session = http_session

        self.leak_alert_list = self.get_leaks()

    def get_leaks(self) -> List[Leak]:
        """Return all leak alerts from devices owned by the user.

        Returns:
            Returns JSON list of leak notifications.
        """

        url = API_LEAK_URL.format(
            user_id=self._flume_auth.user_id,
            device_id=self.device_id,
        )

        query_string = {
            "limit": "50",
            "offset": "0",
            "sort_direction": "ASC",
            "read": self._read,
        }

        response = self._http_session.request(
            "GET",
            url,
            headers=self._flume_auth.authorization_header,
            params=query_string,
            timeout=self._timeout,
        )

        LOGGER.debug(f"get_leaks Response: {response.text}")

        # Check for response errors.
        flume_response_error("Impossible to retrieve leak alerts", response)
        return modelize(response.json()["data"], Leak)
