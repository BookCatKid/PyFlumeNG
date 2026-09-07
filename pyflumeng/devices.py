"""Retrieve devices from the Flume API."""

from typing import List, Optional, Union

from requests import Session

from .auth import FlumeAuth, FlumePortalAuth  # noqa: WPS300
from .constants import DEFAULT_TIMEOUT  # noqa: WPS300
from .models import Device, modelize  # noqa: WPS300
from .utils import api_url, configure_logger, flume_response_error  # noqa: WPS300

# Configure logging
LOGGER = configure_logger(__name__)


class FlumeDeviceList:
    """Get Flume Device List from API."""

    def __init__(
        self,
        flume_auth: Union[FlumeAuth, FlumePortalAuth],
        http_session: Optional[Session] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """

        Initialize the data object.

        Args:
            flume_auth: Authentication object.
            http_session: Requests Session()
            timeout: Requests timeout for throttling.

        """
        self._timeout: float = timeout
        self._flume_auth: Union[FlumeAuth, FlumePortalAuth] = flume_auth

        if http_session is None:
            self._http_session: Session = Session()
        else:
            self._http_session = http_session

        self.device_list = self.get_devices()

    def get_devices(self) -> List[Device]:
        """
        Return all available devices from Flume API.

        Returns:
            Json device list.

        """

        url = api_url(
            self._flume_auth, "/users/{0}/devices".format(self._flume_auth.user_id)
        )
        query_string = {"user": "true", "location": "true"}

        response = self._http_session.request(
            "GET",
            url,
            headers=self._flume_auth.authorization_header,
            params=query_string,
            timeout=self._timeout,
        )

        LOGGER.debug("get_devices Response: %s", response.text)  # noqa: WPS323

        # Check for response errors.
        flume_response_error("Impossible to retreive devices", response)

        return modelize(response.json()["data"], Device)
