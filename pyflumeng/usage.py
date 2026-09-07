"""Retrieve usage alert notifications from the Flume API."""

from typing import Any, List, Optional, Type, TypeVar, Union, cast

from requests import Session

from .auth import FlumeAuth, FlumePortalAuth  # noqa: WPS300
from .constants import (  # noqa: WPS300
    API_BASE_URL,
    API_USAGE_RULE_URL,
    API_USAGE_RULES_URL,
    API_USAGE_URL,
    DEFAULT_TIMEOUT,
)
from .models import FlumeModel, UsageAlert, UsageAlertRule, modelize  # noqa: WPS300
from .types import JSONDict, JSONValue, RequestParams, ResourceId  # noqa: WPS300
from .utils import configure_logger, flume_response_error  # noqa: WPS300

# Configure logging
LOGGER = configure_logger(__name__)
ModelT = TypeVar("ModelT", bound=FlumeModel)


class FlumeUsageAlertList:
    """Get Flume Usage Alert list from API."""

    def __init__(
        self,
        flume_auth: Union[FlumeAuth, FlumePortalAuth],
        http_session: Optional[Session] = None,
        timeout: float = DEFAULT_TIMEOUT,
        read: str = "false",
    ) -> None:
        """

        Initialize the data object.

        Args:
            flume_auth: Authentication object.
            http_session: Requests Session()
            timeout: Requests timeout for throttling.
            read: state of usage alert list, have they been read, not read.

        """
        self._timeout: float = timeout
        self._flume_auth: Union[FlumeAuth, FlumePortalAuth] = flume_auth
        self._read: str = read

        if http_session is None:
            self._http_session: Session = Session()
        else:
            self._http_session = http_session

        self.has_next: bool = False
        self.next_page: Optional[str] = None
        self.usage_alert_list: List[UsageAlert] = self.get_usage_alerts()

    def get_usage_alerts(self) -> List[UsageAlert]:
        """Return initial page of usage alerts from devices owned by the user.

        Returns:
            Returns JSON list of usage alerts.
        """

        api_url = API_USAGE_URL.format(user_id=self._flume_auth.user_id)
        query_string: RequestParams = {
            "limit": "50",
            "offset": "0",
            "sort_direction": "ASC",
            "read": self._read,
        }
        return cast(List[UsageAlert], self._get_usage_request(api_url, query_string))

    def get_next_usage_alerts(self) -> List[UsageAlert]:
        """Return next page of usage alerts from devices owned by the user.

        Returns:
            Returns JSON list of usage alerts.

        Raises:
            ValueError: If no next page is available.
        """
        if self.has_next:
            api_url = f"{API_BASE_URL}{self.next_page}"
            query_string: RequestParams = {}
        else:
            raise ValueError("No next page available.")
        return cast(List[UsageAlert], self._get_usage_request(api_url, query_string))

    def get_usage_alert_rules(self, device_id: ResourceId) -> List[UsageAlertRule]:
        """Return usage alert rules configured for a device.

        Args:
            device_id (string): Device ID owning the rules.

        Returns:
            Returns JSON list of usage alert rules.
        """
        api_url = API_USAGE_RULES_URL.format(
            user_id=self._flume_auth.user_id,
            device_id=device_id,
        )
        return cast(
            List[UsageAlertRule],
            self._get_usage_request(
                api_url,
                {},
                update_pagination=False,
                model=UsageAlertRule,
            ),
        )

    def get_usage_alert_rule(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
    ) -> List[UsageAlertRule]:
        """Return a single usage alert rule for a device.

        Args:
            device_id (string): Device ID owning the rule.
            rule_id (string/int): Usage alert rule ID.

        Returns:
            Returns JSON object (or single-element list) for the rule.
        """
        api_url = API_USAGE_RULE_URL.format(
            user_id=self._flume_auth.user_id,
            device_id=device_id,
            rule_id=rule_id,
        )
        return cast(
            List[UsageAlertRule],
            self._get_usage_request(
                api_url,
                {},
                update_pagination=False,
                model=UsageAlertRule,
            ),
        )

    def update_usage_alert_rule(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
        payload: JSONDict,
    ) -> JSONValue:
        """Update a usage alert rule for a device.

        Example:
            update_usage_alert_rule(device_id, rule_id, {"active": False})

        Args:
            device_id (string): Device ID owning the rule.
            rule_id (string/int): Usage alert rule ID.
            payload (dict): Fields to patch, e.g. {"active": False}.

        Returns:
            object: Response data from API. Note: live API returns an empty
                list on PATCH success, so re-GET the rule to verify state.
        """
        api_url = API_USAGE_RULE_URL.format(
            user_id=self._flume_auth.user_id,
            device_id=device_id,
            rule_id=rule_id,
        )
        response = self._http_session.request(
            "PATCH",
            api_url,
            headers=self._flume_auth.authorization_header,
            json=payload,
            timeout=self._timeout,
        )

        LOGGER.debug(f"update_usage_alert_rule Response: {response.text}")

        # Check for response errors.
        flume_response_error("Impossible to update usage alert rule", response)

        return response.json()["data"]

    def set_usage_alert_rule_active(
        self,
        device_id: ResourceId,
        rule_id: ResourceId,
        active: bool,
    ) -> JSONValue:
        """Enable or disable a usage alert rule for a device.

        Args:
            device_id (string): Device ID owning the rule.
            rule_id (string/int): Usage alert rule ID.
            active (bool): True to enable the rule, False to disable it.

        Returns:
            object: Response in JSON format from API.
        """
        return self.update_usage_alert_rule(
            device_id,
            rule_id,
            {"active": bool(active)},
        )

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

    def _get_usage_request(
        self,
        api_url: str,
        query_string: RequestParams,
        update_pagination: bool = True,
        model: Type[FlumeModel] = UsageAlert,
    ) -> List[FlumeModel]:
        """Make an API request to get usage alerts from the Flume API.

        Args:
            api_url (string): URL for request
            query_string (object): query string options
            update_pagination (bool): Whether to update usage-alert list
                pagination state for this request.
            model (type): Model used to normalize response data.

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

        LOGGER.debug(f"_get_usage_request Response: {response.text}")

        # Check for response errors.
        flume_response_error("Impossible to retrieve usage alert", response)

        response_json = response.json()
        if not update_pagination:
            return cast(List[FlumeModel], modelize(response_json["data"], model))

        if self._has_next_page(response_json):
            self.next_page = response_json["pagination"]["next"]
            self.has_next = True
            LOGGER.debug(
                f"Next page for Usage results: {self.next_page}",
            )
        else:
            self.has_next = False
            self.next_page = None
            LOGGER.debug("No further pages for Usage results.")
        return cast(List[FlumeModel], modelize(response_json["data"], model))
