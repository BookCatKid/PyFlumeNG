"""Rate-limit state for Flume authentication and API responses."""

from datetime import datetime, timezone


class RateLimitState:
    """Track a baseline and the latest server-advertised quota."""

    def __init__(self, baseline):
        self.baseline = baseline
        self.limit = baseline
        self.remaining = None
        self.reset = None
        self.retry_after = None

    @property
    def reset_at(self):
        """Return reset time as a UTC datetime, if available."""
        if self.reset is None:
            return None
        return datetime.fromtimestamp(self.reset, timezone.utc)

    def update_from_headers(self, headers):
        """Update values from standard Flume rate-limit headers."""
        values = {
            "limit": headers.get("X-RateLimit-Limit"),
            "remaining": headers.get("X-RateLimit-Remaining"),
            "reset": headers.get("X-RateLimit-Reset"),
            "retry_after": headers.get("Retry-After"),
        }
        for key in ("limit", "remaining", "reset"):
            if values[key] is not None:
                try:
                    values[key] = int(values[key])
                except (TypeError, ValueError):
                    continue
                setattr(self, key, values[key])
        if values["retry_after"] is not None:
            self.retry_after = values["retry_after"]

    def to_dict(self):
        """Return serializable rate-limit state."""
        return {
            "baseline": self.baseline,
            "limit": self.limit,
            "remaining": self.remaining,
            "reset": self.reset,
            "retry_after": self.retry_after,
        }
