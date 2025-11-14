"""Tests for logging module."""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nutanix_exporter.utils.logger import setup_logger, get_logger, ColoredFormatter


class TestLogger:
    """Tests for logger module."""
    
    def test_setup_logger(self):
        """Test logger setup."""
        logger = setup_logger(name="test_logger", level="INFO")
        assert logger is not None
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
    
    def test_get_logger(self):
        """Test getting logger instance."""
        logger = get_logger("test_logger_2")
        assert logger is not None
        assert isinstance(logger, logging.Logger)
    
    def test_colored_formatter(self):
        """Test colored formatter."""
        formatter = ColoredFormatter('%(levelname)s %(message)s')
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        formatted = formatter.format(record)
        assert "INFO" in formatted or "\033[92m" in formatted  # Green color code or INFO

