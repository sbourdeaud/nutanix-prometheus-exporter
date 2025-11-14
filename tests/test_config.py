"""Tests for configuration module."""

import os
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nutanix_exporter.config.settings import (
    ExporterConfig,
    APIConfig,
    MetricsConfig,
    IPMIConfig,
    ConfigurationError,
)


class TestAPIConfig:
    """Tests for APIConfig."""
    
    def test_default_values(self):
        """Test default API configuration values."""
        config = APIConfig()
        assert config.timeout_seconds == 30
        assert config.retries == 5
        assert config.sleep_between_retries == 15
    
    def test_custom_values(self):
        """Test custom API configuration values."""
        config = APIConfig(timeout_seconds=60, retries=3, sleep_between_retries=10)
        assert config.timeout_seconds == 60
        assert config.retries == 3
        assert config.sleep_between_retries == 10
    
    def test_validation_timeout(self):
        """Test timeout validation."""
        with pytest.raises(Exception):  # Pydantic validation error
            APIConfig(timeout_seconds=0)
        
        with pytest.raises(Exception):
            APIConfig(timeout_seconds=301)


class TestMetricsConfig:
    """Tests for MetricsConfig."""
    
    def test_default_values(self):
        """Test default metrics configuration."""
        config = MetricsConfig()
        assert config.cluster is True
        assert config.hosts is True
        assert config.storage_containers is True
        assert config.disks is False
        assert config.networking is False


class TestExporterConfig:
    """Tests for ExporterConfig."""
    
    def test_from_env_defaults(self):
        """Test loading configuration from environment with defaults."""
        # Clear relevant env vars
        for key in ['PRISM', 'PRISM_USERNAME', 'PRISM_SECRET']:
            if key in os.environ:
                del os.environ[key]
        
        config = ExporterConfig.from_env()
        assert config.prism == '127.0.0.1'
        assert config.prism_username == 'admin'
        assert config.exporter_port == 8000
        assert config.operations_mode == 'v4'
    
    def test_from_env_custom(self):
        """Test loading configuration from environment with custom values."""
        os.environ['PRISM'] = '192.168.1.10'
        os.environ['PRISM_USERNAME'] = 'testuser'
        os.environ['PRISM_SECRET'] = 'testpass'
        os.environ['EXPORTER_PORT'] = '9000'
        os.environ['OPERATIONS_MODE'] = 'legacy'
        
        config = ExporterConfig.from_env()
        assert config.prism == '192.168.1.10'
        assert config.prism_username == 'testuser'
        assert config.prism_secret == 'testpass'
        assert config.exporter_port == 9000
        assert config.operations_mode == 'legacy'
        
        # Cleanup
        for key in ['PRISM', 'PRISM_USERNAME', 'PRISM_SECRET', 'EXPORTER_PORT', 'OPERATIONS_MODE']:
            if key in os.environ:
                del os.environ[key]
    
    def test_operations_mode_validation(self):
        """Test operations mode validation."""
        os.environ['OPERATIONS_MODE'] = 'invalid'
        
        with pytest.raises(ValueError):
            ExporterConfig.from_env()
        
        # Cleanup
        if 'OPERATIONS_MODE' in os.environ:
            del os.environ['OPERATIONS_MODE']
    
    def test_ipmi_config_parsing(self):
        """Test IPMI config JSON parsing."""
        ipmi_json = '[{"ip":"1.1.1.1","name":"host1","username":"ADMIN","password":"pass"}]'
        os.environ['IPMI_CONFIG'] = ipmi_json
        
        config = ExporterConfig.from_env()
        assert len(config.ipmi_config) == 1
        assert config.ipmi_config[0].ip == '1.1.1.1'
        assert config.ipmi_config[0].name == 'host1'
        
        # Cleanup
        if 'IPMI_CONFIG' in os.environ:
            del os.environ['IPMI_CONFIG']


class TestIPMIConfig:
    """Tests for IPMIConfig."""
    
    def test_ipmi_config_creation(self):
        """Test IPMI config creation."""
        config = IPMIConfig(ip='1.1.1.1', name='host1', username='ADMIN', password='pass')
        assert config.ip == '1.1.1.1'
        assert config.name == 'host1'
        assert config.username == 'ADMIN'
        assert config.password == 'pass'
    
    def test_ipmi_config_defaults(self):
        """Test IPMI config default username."""
        config = IPMIConfig(ip='1.1.1.1', name='host1', password='pass')
        assert config.username == 'ADMIN'

