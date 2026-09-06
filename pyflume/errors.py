"""Exceptions raised by PyFlumeNG."""


class FlumeError(Exception):
    """Base exception for PyFlumeNG."""


class FlumeAuthError(FlumeError):
    """Raised when authentication or token exchange fails."""


class FlumeHTTPError(FlumeError):
    """Raised for a non-successful Flume API response."""

    def __init__(self, message, response=None, envelope=None):
        self.message = message
        self.response = response
        self.envelope = envelope or {}
        self.status_code = getattr(response, "status_code", None)
        self.code = self.envelope.get("code")
        self.detailed = self.envelope.get("detailed")
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
    def retry_after(self):
        """Return the server Retry-After value, when provided."""
        if self.response is None:
            return None
        return self.response.headers.get("Retry-After")
