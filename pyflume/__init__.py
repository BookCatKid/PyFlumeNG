"""PyFlumeNG: a complete Flume API client with portal capabilities."""

from .auth import FlumeAuth, FlumePortalAuth  # noqa: WPS300, F401
from .auth import FlumeAuth as PersonalAuth  # noqa: WPS300, F401
from .auth import FlumePortalAuth as PortalAuth  # noqa: WPS300, F401
from .client import FlumeClient  # noqa: WPS300, F401
from .data import FlumeData  # noqa: WPS300, F401
from .devices import FlumeDeviceList  # noqa: WPS300, F401
from .errors import (  # noqa: WPS300, F401
    FlumeAuthError,
    FlumeError,
    FlumeHTTPError,
    FlumeRateLimitError,
)
from .leak import FlumeLeakList  # noqa: WPS300, F401
from .notifications import FlumeNotificationList  # noqa: WPS300, F401
from .usage import FlumeUsageAlertList  # noqa: WPS300, F401

__all__ = [
    "FlumeAuth",
    "PersonalAuth",
    "FlumePortalAuth",
    "FlumeClient",
    "FlumeData",
    "FlumeDeviceList",
    "FlumeLeakList",
    "FlumeNotificationList",
    "FlumeUsageAlertList",
    "FlumeError",
    "FlumeAuthError",
    "FlumeHTTPError",
    "FlumeRateLimitError",
]
