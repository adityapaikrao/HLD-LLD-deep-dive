"""
Token Bucket Rate Limiter

Implements a token bucket algorithm that allows for burst traffic while
enforcing a smooth average rate over time.
"""

import time

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize a token bucket.

        Args:
            capacity (int): Maximum number of tokens in the bucket.
            refill_rate (float): Tokens added per second.
        """
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.current_tokens = float(capacity)
        self.last_refill_timestamp = time.monotonic()

    def add_tokens(self, tokens: float) -> None:
        """
        Add tokens to the bucket, without exceeding capacity.
        
        Args:
            tokens (float): Number of tokens to add.
        """
        self.current_tokens = min(self.capacity, self.current_tokens + tokens)

    def is_allowed(self, tokens: float) -> bool:
        """
        Attempt to consume tokens from the bucket.

        Args:
            tokens (float): Number of tokens requested.

        Returns:
            bool: True if enough tokens are available and consumed, False otherwise.
        """
        self.refill()
        if tokens <= self.current_tokens:
            self.current_tokens -= tokens
            return True
        return False

    def refill(self) -> None:
        """
        Refill tokens based on elapsed time since last refill.
        """
        now = time.monotonic()
        elapsed = now - self.last_refill_timestamp
        if elapsed > 0:
            new_tokens = elapsed * self.refill_rate
            self.add_tokens(new_tokens)
            self.last_refill_timestamp = now