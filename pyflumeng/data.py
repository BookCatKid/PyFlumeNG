"""Retrieve data from Flume API."""

import sys
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Union, cast

from ratelimit import limits, sleep_and_retry
from requests import Session

from .auth import FlumeAuth, FlumePortalAuth  # noqa: WPS300
from .constants import (  # noqa: WPS300
    API_LIMIT,
    API_QUERY_URL,
    CONST_OPERATION,
    CONST_UNIT_OF_MEASUREMENT,
    DEFAULT_TIMEOUT,
)
from .types import QueryPayload, QuerySpec, QueryValues, ResourceId  # noqa: WPS300
from .utils import (  # noqa: WPS300
    configure_logger,
    flume_response_error,
    format_start_month,
    format_start_today,
    format_start_week,
    format_time,
)

if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo  # noqa: WPS433
else:  # pragma: no cover - exercised on Python 3.8
    from backports.zoneinfo import ZoneInfo  # noqa: WPS433,WPS440

# Configure logging
LOGGER = configure_logger(__name__)


class FlumeData:
    """Get the latest data and update the states."""

    def __init__(  # noqa: WPS211
        self,
        flume_auth: Union[FlumeAuth, FlumePortalAuth],
        device_id: ResourceId,
        device_tz: str,
        scan_interval: timedelta = timedelta(minutes=60),
        update_on_init: bool = True,
        http_session: Optional[Session] = None,
        timeout: float = DEFAULT_TIMEOUT,
        query_payload: Optional[QueryPayload] = None,
    ) -> None:
        """

        Initialize the data object.

        Args:
            flume_auth: Authentication object.
            device_id: flume device id.
            device_tz: timezone of device
            scan_interval: duration of scan, ex: 60 minutes.
            update_on_init: update on initialization.
            http_session: Requests Session()
            timeout: Requests timeout for throttling.
            query_payload: Specific query_payload to request for device.

        """
        self._timeout: float = timeout
        self._flume_auth: Union[FlumeAuth, FlumePortalAuth] = flume_auth
        self._scan_interval: timedelta = scan_interval
        self.device_id: ResourceId = device_id
        self.device_tz: str = device_tz
        self.values: QueryValues = {}  # noqa: WPS110
        self._uses_default_query_payload = query_payload is None
        if query_payload is None:
            self.query_payload = self.generate_api_query_payload(
                self._scan_interval,
                device_tz,
            )
        else:
            self.query_payload = query_payload
        if http_session is None:
            self._http_session: Session = Session()
        else:
            self._http_session = http_session
        if update_on_init:
            self.update()

    @sleep_and_retry
    @limits(calls=2, period=API_LIMIT)
    def update(self) -> None:
        """
        Return updated value for session.

        Returns:
            Returns status of update

        """
        return self.update_force()

    def update_force(self) -> None:
        """Return updated value for session without auto retry or limits."""
        if self._uses_default_query_payload:
            self.query_payload = self.generate_api_query_payload(
                self._scan_interval,
                self.device_tz,
            )
        query_keys = [query["request_id"] for query in self.query_payload["queries"]]

        url = API_QUERY_URL.format(
            user_id=self._flume_auth.user_id,
            device_id=self.device_id,
        )
        response = self._http_session.post(
            url,
            json=cast(Any, self.query_payload),
            headers=self._flume_auth.authorization_header,
            timeout=self._timeout,
        )

        LOGGER.debug("Update URL: %s", url)  # noqa: WPS323
        LOGGER.debug("Update query_payload: %s", self.query_payload)  # noqa: WPS323
        LOGGER.debug("Update Response: %s", response.text)  # noqa: WPS323

        # Check for response errors.
        flume_response_error(
            "Can't update flume data for user id {0}".format(self._flume_auth.user_id),
            response,
        )

        responses = response.json()["data"][0]

        # Step 1: Initialize an empty dictionary
        values_dict: QueryValues = {}

        # Step 2: Loop through each key requested in the payload that was sent
        for key in query_keys:
            # Step 3: Check the length of the responses for the current key
            if len(responses[key]) == 1:
                # Step 4: Assign the value to the dictionary if the condition is met
                values_dict[key] = responses[key][0]["value"]
            else:
                # Step 5: Assign None to the dictionary if the condition is not met
                values_dict[key] = None

        # Step 6: Assign the result to self.values
        self.values = values_dict  # noqa: WPS110

    @classmethod
    def generate_api_query_payload(
        cls,
        scan_interval: timedelta,
        device_tz: str,
    ) -> QueryPayload:
        """Generate API Query payload to support getting data from Flume API.

        Args:
            scan_interval (_type_): Interval to scan.
            device_tz (_type_): Time Zone of Flume device.

        Returns:
            JSON: API Query to retrieve API details.
        """
        _ = cls
        datetime_localtime = datetime.now(timezone.utc).astimezone(ZoneInfo(device_tz))

        queries: List[QuerySpec] = [
            {
                "request_id": "current_interval",
                "bucket": "MIN",
                "since_datetime": format_time(
                    (datetime_localtime - scan_interval).replace(second=0),
                ),
                "until_datetime": format_time(datetime_localtime.replace(second=0)),
                "operation": CONST_OPERATION,
                "units": CONST_UNIT_OF_MEASUREMENT,
            },
            {
                "request_id": "today",
                "bucket": "DAY",
                "since_datetime": format_start_today(datetime_localtime),
                "until_datetime": format_time(datetime_localtime),
                "operation": CONST_OPERATION,
                "units": CONST_UNIT_OF_MEASUREMENT,
            },
            {
                "request_id": "week_to_date",
                "bucket": "DAY",
                "since_datetime": format_start_week(datetime_localtime),
                "until_datetime": format_time(datetime_localtime),
                "operation": CONST_OPERATION,
                "units": CONST_UNIT_OF_MEASUREMENT,
            },
            {
                "request_id": "month_to_date",
                "bucket": "MON",
                "since_datetime": format_start_month(datetime_localtime),
                "until_datetime": format_time(datetime_localtime),
                "units": CONST_UNIT_OF_MEASUREMENT,
            },
            {
                "request_id": "last_60_min",
                "bucket": "MIN",
                "since_datetime": format_time(
                    datetime_localtime - timedelta(minutes=60),
                ),
                "until_datetime": format_time(datetime_localtime),
                "operation": CONST_OPERATION,
                "units": CONST_UNIT_OF_MEASUREMENT,
            },
            {
                "request_id": "last_24_hrs",
                "bucket": "HR",
                "since_datetime": format_time(datetime_localtime - timedelta(hours=24)),
                "until_datetime": format_time(datetime_localtime),
                "operation": CONST_OPERATION,
                "units": CONST_UNIT_OF_MEASUREMENT,
            },
            {
                "request_id": "last_30_days",
                "bucket": "DAY",
                "since_datetime": format_time(
                    datetime_localtime - timedelta(days=30),  # noqa: WPS432
                ),
                "until_datetime": format_time(datetime_localtime),
                "operation": CONST_OPERATION,
                "units": CONST_UNIT_OF_MEASUREMENT,
            },
        ]
        return {"queries": queries}
