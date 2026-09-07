"""Rate-limit state for Flume authentication and API responses."""

from datetime import datetime, timezone
from typing import Dict, Mapping, Optional, Union


class RateLimitState:
    """Track a baseline and the latest server-advertised quota."""

    def __init__(self, baseline: int) -> None:
        self.baseline: int = baseline
        self.limit: int = baseline
        self.remaining: Optional[int] = None
        self.reset: Optional[int] = None
        self.retry_after: Optional[str] = None

    @property
    def reset_at(self) -> Optional[datetime]:
        """Return reset time as a UTC datetime, if available."""
        if self.reset is None:
            return None
        return datetime.fromtimestamp(self.reset, timezone.utc)

    def update_from_headers(self, headers: Mapping[str, str]) -> None:
        """Update values from standard Flume rate-limit headers."""
        numeric_headers = {
            "limit": headers.get("X-RateLimit-Limit"),
            "remaining": headers.get("X-RateLimit-Remaining"),
            "reset": headers.get("X-RateLimit-Reset"),
        }
        for key, raw_value in numeric_headers.items():
            if raw_value is None:
                continue
            try:
                value = int(raw_value)
            except ValueError:
                continue
            setattr(self, key, value)

        retry_after = headers.get("Retry-After")
        if retry_after is not None:
            self.retry_after = retry_after

    def to_dict(self) -> Dict[str, Optional[Union[int, str]]]:
        """Return serializable rate-limit state."""
        return {
            "baseline": self.baseline,
            "limit": self.limit,
            "remaining": self.remaining,
            "reset": self.reset,
            "retry_after": self.retry_after,
        }
