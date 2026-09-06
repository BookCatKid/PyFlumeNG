"""Exceptions raised by PyFlumeNG."""

from typing import Optional

from requests import Response

from .types import JSONDict, JSONValue


class FlumeError(Exception):
    """Base exception for PyFlumeNG."""


class FlumeAuthError(FlumeError):
    """Raised when authentication or token exchange fails."""


class FlumeCapabilityError(FlumeError):
    """Raised when an auth flow lacks a required API capability."""


class FlumeHTTPError(FlumeError):
    """Raised for a non-successful Flume API response."""

    def __init__(
        self,
        message: str,
        response: Optional[Response] = None,
        envelope: Optional[JSONDict] = None,
    ) -> None:
        self.message: str = message
        self.response: Optional[Response] = response
        self.envelope: JSONDict = envelope or {}
        self.status_code: Optional[int] = getattr(response, "status_code", None)
        code = self.envelope.get("code")
        self.code: Optional[int] = code if isinstance(code, int) else None
        self.detailed: Optional[JSONValue] = self.envelope.get("detailed")
        detail = self.envelope.get("message") or self.detailed or message
        super().__init__(
            "{0} (HTTP {1}, Flume code {2}): {3}".format(
                message,
                self.status_code,
                self.code,
                detail,
            ),
        )


class FlumeRateLimitError(FlumeHTTPError):
    """Raised when Flume rejects a request because of rate limiting."""

    @property
    def retry_after(self) -> Optional[str]:
        """Return the server Retry-After value, when provided."""
        if self.response is None:
            return None
        return self.response.headers.get("Retry-After")
