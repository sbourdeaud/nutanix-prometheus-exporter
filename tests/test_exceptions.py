"""Tests for exception classes."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nutanix_exporter.utils.exceptions import (
    NutanixExporterError,
    NutanixAPIError,
    AuthenticationError,
    RateLimitError,
    ConnectionError,
    TimeoutError,
    ConfigurationError,
)


class TestExceptions:
    """Tests for custom exceptions."""
    
    def test_nutanix_exporter_error(self):
        """Test base exception."""
        error = NutanixExporterError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_nutanix_api_error(self):
        """Test API error with status code."""
        error = NutanixAPIError("API error", status_code=500, response_text="Server error")
        assert str(error) == "API error"
        assert error.status_code == 500
        assert error.response_text == "Server error"
    
    def test_authentication_error(self):
        """Test authentication error."""
        error = AuthenticationError("Auth failed", status_code=401)
        assert str(error) == "Auth failed"
        assert error.status_code == 401
        assert isinstance(error, NutanixAPIError)
    
    def test_rate_limit_error(self):
        """Test rate limit error."""
        error = RateLimitError("Rate limited", status_code=429)
        assert str(error) == "Rate limited"
        assert error.status_code == 429
        assert isinstance(error, NutanixAPIError)
    
    def test_connection_error(self):
        """Test connection error."""
        error = ConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, NutanixExporterError)
    
    def test_timeout_error(self):
        """Test timeout error."""
        error = TimeoutError("Request timeout")
        assert str(error) == "Request timeout"
        assert isinstance(error, NutanixExporterError)
    
    def test_configuration_error(self):
        """Test configuration error."""
        error = ConfigurationError("Invalid config")
        assert str(error) == "Invalid config"
        assert isinstance(error, NutanixExporterError)

