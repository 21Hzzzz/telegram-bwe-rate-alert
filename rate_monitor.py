"""State machine for detecting message bursts."""

from __future__ import annotations

from collections import deque


class BurstDetector:
    """Trigger once when `threshold` arrivals occur inside `window_seconds`."""

    def __init__(self, threshold: int = 5, window_seconds: float = 60) -> None:
        if threshold < 1 or window_seconds <= 0:
            raise ValueError("threshold must be positive and window_seconds must be greater than zero")
        self.threshold = threshold
        self.window_seconds = window_seconds
        self.timestamps: deque[float] = deque()
        self.alert_active = False

    def record(self, timestamp: float) -> bool:
        """Record an arrival and return whether this starts a new burst."""
        cutoff = timestamp - self.window_seconds
        while self.timestamps and self.timestamps[0] <= cutoff:
            self.timestamps.popleft()

        if len(self.timestamps) < self.threshold:
            self.alert_active = False

        self.timestamps.append(timestamp)
        if len(self.timestamps) >= self.threshold and not self.alert_active:
            self.alert_active = True
            return True
        return False
