"""Tests for rate limiter module."""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nutanix_exporter.utils.rate_limiter import RateLimiter, AdaptiveRateLimiter


class TestRateLimiter:
    """Tests for RateLimiter."""
    
    def test_rate_limiter_creation(self):
        """Test rate limiter creation."""
        limiter = RateLimiter(max_calls=10, period=60.0)
        assert limiter.max_calls == 10
        assert limiter.period == 60.0
    
    def test_rate_limiter_wait(self):
        """Test rate limiter wait functionality."""
        limiter = RateLimiter(max_calls=2, period=1.0)
        
        # First two calls should not wait
        start = time.time()
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        assert elapsed < 0.5  # Should be fast
        
        # Third call should wait
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        assert elapsed >= 0.9  # Should wait almost a second
    
    def test_rate_limiter_reset(self):
        """Test rate limiter reset."""
        limiter = RateLimiter(max_calls=1, period=1.0)
        limiter.wait_if_needed()
        limiter.reset()
        # After reset, should be able to call immediately
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        assert elapsed < 0.5


class TestAdaptiveRateLimiter:
    """Tests for AdaptiveRateLimiter."""
    
    def test_adaptive_rate_limiter_creation(self):
        """Test adaptive rate limiter creation."""
        limiter = AdaptiveRateLimiter(max_calls=10, period=60.0, min_period=10.0)
        assert limiter.max_calls == 10
        assert limiter.period == 60.0
        assert limiter.min_period == 10.0
    
    def test_handle_rate_limit_error(self):
        """Test handling rate limit errors."""
        limiter = AdaptiveRateLimiter(max_calls=10, period=60.0)
        initial_period = limiter.period
        
        limiter.handle_rate_limit_error()
        assert limiter.period > initial_period
        assert limiter.consecutive_429_errors == 1
    
    def test_handle_success(self):
        """Test handling successful calls."""
        limiter = AdaptiveRateLimiter(max_calls=10, period=60.0)
        limiter.handle_rate_limit_error()
        limiter.handle_rate_limit_error()
        assert limiter.consecutive_429_errors == 2
        
        limiter.handle_success()
        # Should reduce by 1
        assert limiter.consecutive_429_errors == 1

