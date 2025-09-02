"""
Sliding Window Log Rate Limiter

Implements a sliding window log algorithm that allows a certain number of requests
to be processed within a sliding time window.
"""

from collections import deque
from typing import Deque
import time


class SlidingWindowLog:
    def __init__(self, max_requests: int, window_size: float):
        """
        Initialize a Sliding Window Log rate limiter.

        Args:
            max_requests (int): Maximum number of requests allowed per window.
            window_size (float): Size of the time window in seconds.
        """
        self.max_requests: int = max_requests
        self.window_size: float = window_size
        self.request_times: Deque[float] = deque()

    def _cleanup_expired_requests(self, current_time: float) -> None:
        """Remove timestamps that are outside the sliding window."""
        while self.request_times and current_time - self.request_times[0] >= self.window_size:
            self.request_times.popleft()

    def is_allowed(self, current_time: float | None = None) -> bool:
        """
        Check whether a request is allowed based on the current time.

        Args:
            current_time (float, optional): The current timestamp in seconds (can be fractional).
                                            Defaults to `time.time()` if not provided.

        Returns:
            bool: True if the request is allowed, False otherwise.
        """
        if current_time is None:
            current_time = time.time()

        self._cleanup_expired_requests(current_time)

        if len(self.request_times) < self.max_requests:
            self.request_times.append(current_time)
            return True

        return False
