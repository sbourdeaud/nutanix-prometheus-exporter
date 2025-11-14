"""Custom exceptions for the Nutanix Prometheus Exporter."""


class NutanixExporterError(Exception):
    """Base exception for all exporter errors."""
    pass


class NutanixAPIError(NutanixExporterError):
    """Exception raised for Nutanix API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class AuthenticationError(NutanixAPIError):
    """Exception raised for authentication failures."""
    pass


class RateLimitError(NutanixAPIError):
    """Exception raised when API rate limit is exceeded."""
    pass


class ConnectionError(NutanixExporterError):
    """Exception raised for connection errors."""
    pass


class TimeoutError(NutanixExporterError):
    """Exception raised for timeout errors."""
    pass


class ConfigurationError(NutanixExporterError):
    """Exception raised for configuration errors."""
    pass

