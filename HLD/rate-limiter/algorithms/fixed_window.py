"""
Fixed Window Rate Limiter

Implements a fixed window algorithm that allows a certain number of requests
to be processed within a fixed-size time window.
"""

import time


class FixedWindow:
    def __init__(self, max_requests: int, window_size: float):
        """
        Initialize a Fixed Window rate limiter.

        Args:
            max_requests (int): Maximum number of requests allowed per window.
            window_size (float): Size of the time window in seconds.
        """
        self.max_requests = max_requests
        self.window_size = window_size
        self.request_count = 0
        self.window_start = time.time()

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

        if current_time - self.window_start >= self.window_size:
            self.reset(current_time)

        if self.request_count < self.max_requests:
            self.request_count += 1
            return True

        return False

    def reset(self, current_time: float) -> None:
        """
        Reset the window start time and request counter.

        Args:
            current_time (float): The timestamp to set as the new window start.
        """
        self.request_count = 0
        self.window_start = current_time
