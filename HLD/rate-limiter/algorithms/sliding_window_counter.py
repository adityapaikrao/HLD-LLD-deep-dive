import time

class SlidingWindowCounter:
    def __init__(self, max_requests: int, window_size: float):
        """
        Initialize a Sliding Window Counter rate limiter.

        Args:
            max_requests (int): Maximum number of requests allowed per window.
            window_size (float): Size of the time window in seconds.
        """
        self.max_requests = max_requests
        self.window_size = window_size
        self.request_counts = [0] * int(window_size)
        self.start_time = time.time()
        self.current_window = 0

    def is_allowed(self, current_time: float) -> bool:
        """
        Check whether a request is allowed based on the current time.

        Args:
            current_time (float): The current timestamp in seconds (can be fractional).

        Returns:
            bool: True if the request is allowed, False otherwise.
        """
        # Calculate relative time since start
        elapsed = current_time - self.start_time
        window_index = int(elapsed) % int(self.window_size)

        # If we jumped ahead by multiple windows, reset intermediate windows
        if window_index != self.current_window:
            steps_ahead = (window_index - self.current_window) % int(self.window_size)
            for i in range(1, steps_ahead + 1):
                self.request_counts[(self.current_window + i) % int(self.window_size)] = 0
            self.current_window = window_index

        # Check if request is allowed
        if self.request_counts[window_index] < self.max_requests:
            self.request_counts[window_index] += 1
            return True

        return False
