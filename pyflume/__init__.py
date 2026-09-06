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
from .models import (  # noqa: WPS300, F401
    ApiClient,
    Budget,
    Contact,
    CurrentFlow,
    Device,
    DoNotAlertSchedule,
    FlumeModel,
    Integration,
    Insurer,
    Leak,
    Location,
    LocationAccess,
    LocationProfiles,
    Notification,
    PurchaseOption,
    QueryResult,
    Span,
    SpanType,
    Subscription,
    UsageAlert,
    UsageAlertRule,
    User,
)
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
    "FlumeModel",
    "User",
    "Device",
    "Location",
    "LocationProfiles",
    "Notification",
    "UsageAlert",
    "UsageAlertRule",
    "Budget",
    "Subscription",
    "DoNotAlertSchedule",
    "LocationAccess",
    "Integration",
    "Span",
    "SpanType",
    "Leak",
    "CurrentFlow",
    "QueryResult",
    "PurchaseOption",
    "Contact",
    "Insurer",
    "ApiClient",
    "FlumeError",
    "FlumeAuthError",
    "FlumeHTTPError",
    "FlumeRateLimitError",
]
