"""Rate limiting utilities for API calls."""

import time
from threading import Lock
from typing import Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Simple token bucket rate limiter for API calls.
    
    Args:
        max_calls: Maximum number of calls allowed
        period: Time period in seconds
    """
    
    def __init__(self, max_calls: int = 100, period: float = 60.0):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls per period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls: list[float] = []
        self.lock = Lock()
    
    def wait_if_needed(self) -> None:
        """
        Wait if rate limit would be exceeded.
        
        This method should be called before making an API call.
        """
        with self.lock:
            now = time.time()
            # Remove calls older than the period
            self.calls = [call_time for call_time in self.calls if now - call_time < self.period]
            
            if len(self.calls) >= self.max_calls:
                # Calculate how long to wait
                oldest_call = min(self.calls)
                wait_time = self.period - (now - oldest_call) + 0.1  # Add small buffer
                
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached ({len(self.calls)}/{self.max_calls} calls). "
                        f"Waiting {wait_time:.2f} seconds..."
                    )
                    time.sleep(wait_time)
                    # Update now after waiting
                    now = time.time()
                    # Clean up again after waiting
                    self.calls = [call_time for call_time in self.calls if now - call_time < self.period]
            
            # Record this call
            self.calls.append(now)
    
    def reset(self) -> None:
        """Reset the rate limiter."""
        with self.lock:
            self.calls.clear()


class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that adjusts based on API responses.
    
    Automatically reduces rate if 429 (rate limit) errors are encountered.
    """
    
    def __init__(self, max_calls: int = 100, period: float = 60.0, min_period: float = 10.0):
        """
        Initialize adaptive rate limiter.
        
        Args:
            max_calls: Maximum number of calls per period
            period: Initial time period in seconds
            min_period: Minimum time period (won't go below this)
        """
        super().__init__(max_calls, period)
        self.initial_period = period
        self.min_period = min_period
        self.consecutive_429_errors = 0
    
    def handle_rate_limit_error(self) -> None:
        """Handle a 429 rate limit error by increasing the period."""
        with self.lock:
            self.consecutive_429_errors += 1
            # Increase period by 50% for each consecutive error, up to 5x
            multiplier = min(1.5 ** self.consecutive_429_errors, 5.0)
            self.period = min(self.initial_period * multiplier, 300.0)  # Cap at 5 minutes
            logger.warning(
                f"Rate limit error encountered. Adjusting period to {self.period:.1f}s "
                f"(consecutive errors: {self.consecutive_429_errors})"
            )
            # Reset calls to give immediate relief
            self.calls.clear()
    
    def handle_success(self) -> None:
        """Handle a successful call by gradually reducing the period."""
        with self.lock:
            if self.consecutive_429_errors > 0:
                self.consecutive_429_errors = max(0, self.consecutive_429_errors - 1)
                # Gradually reduce period back to initial
                if self.consecutive_429_errors == 0:
                    self.period = self.initial_period
                    logger.info(f"Rate limit recovered. Period reset to {self.period:.1f}s")

