"""Configuration settings using Pydantic for validation."""

import json
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from ..utils.exceptions import ConfigurationError


def parse_bool_env_var(value: Optional[str], default: bool = False) -> bool:
    """Parse boolean environment variable."""
    if value is None:
        return default
    return value.lower() in ("true", "1", "t", "y", "yes")


class IPMIConfig(BaseModel):
    """Configuration for a single IPMI interface."""
    ip: str
    name: str
    username: str = "ADMIN"
    password: str


class APIConfig(BaseModel):
    """API request configuration."""
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retries: int = Field(default=5, ge=0, le=10)
    sleep_between_retries: int = Field(default=15, ge=1, le=60)


class MetricsConfig(BaseModel):
    """Configuration for which metrics to collect."""
    cluster: bool = True
    hosts: bool = True
    storage_containers: bool = True
    disks: bool = False
    networking: bool = False
    files: bool = False
    object: bool = False
    volumes: bool = False
    ncm_ssp: bool = False
    prism_central: bool = False
    microseg: bool = False
    ipmi: bool = False
    ipmi_additional: bool = False


class ExporterConfig(BaseModel):
    """Main configuration for the exporter."""
    
    # Prism/API Configuration
    prism: str = Field(default="127.0.0.1")
    prism_username: str = Field(default="admin")
    prism_secret: str = Field(default="secret")
    prism_secure: bool = Field(default=False)
    app_port: int = Field(default=9440, ge=1, le=65535)
    
    # Exporter Configuration
    exporter_port: int = Field(default=8000, ge=1, le=65535)
    polling_interval_seconds: int = Field(default=30, ge=1, le=3600)
    operations_mode: str = Field(default="v4")
    
    @field_validator('operations_mode')
    @classmethod
    def validate_operations_mode(cls, v: str) -> str:
        """Validate operations mode."""
        if v not in ('v4', 'legacy', 'redfish'):
            raise ValueError("operations_mode must be one of: v4, legacy, redfish")
        return v
    
    # API Configuration
    api: APIConfig = Field(default_factory=APIConfig)
    
    # Metrics Configuration
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    
    # VM Configuration
    vm_list: str = Field(default="")
    
    # IPMI Configuration
    ipmi_username: str = Field(default="ADMIN")
    ipmi_secret: Optional[str] = None
    ipmi_secure: bool = Field(default=False)
    ipmi_config: List[IPMIConfig] = Field(default_factory=list)
    
    # Feature Flags
    show_stats_only: bool = Field(default=False)
    
    # Pagination
    page_limit: int = Field(default=100, ge=1, le=1000)
    max_workers: int = Field(default=10, ge=1, le=50)
    sampling_interval: int = Field(default=30, ge=1, le=3600)
    
    @field_validator('ipmi_config', mode='before')
    @classmethod
    def parse_ipmi_config(cls, v: Any) -> List[Dict[str, Any]]:
        """Parse IPMI config from JSON string."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v if isinstance(v, list) else []
    
    @classmethod
    def from_env(cls) -> 'ExporterConfig':
        """
        Create configuration from environment variables.
        
        Returns:
            ExporterConfig instance
            
        Raises:
            ConfigurationError: If required configuration is invalid
        """
        try:
            # Parse IPMI config
            ipmi_config_str = os.getenv('IPMI_CONFIG', '[]')
            ipmi_config_list = json.loads(ipmi_config_str) if ipmi_config_str else []
            ipmi_config = [IPMIConfig(**item) for item in ipmi_config_list]
            
            # Create API config
            api_config = APIConfig(
                timeout_seconds=int(os.getenv("API_REQUESTS_TIMEOUT_SECONDS", "30")),
                retries=int(os.getenv("API_REQUESTS_RETRIES", "5")),
                sleep_between_retries=int(os.getenv("API_SLEEP_SECONDS_BETWEEN_RETRIES", "15"))
            )
            
            # Create metrics config
            metrics_config = MetricsConfig(
                cluster=parse_bool_env_var(os.getenv('CLUSTER_METRICS', 'True')),
                hosts=parse_bool_env_var(os.getenv('HOSTS_METRICS', 'True')),
                storage_containers=parse_bool_env_var(os.getenv('STORAGE_CONTAINERS_METRICS', 'True')),
                disks=parse_bool_env_var(os.getenv('DISKS_METRICS', 'False')),
                networking=parse_bool_env_var(os.getenv('NETWORKING_METRICS', 'False')),
                files=parse_bool_env_var(os.getenv('FILES_METRICS', 'False')),
                object=parse_bool_env_var(os.getenv('OBJECT_METRICS', 'False')),
                volumes=parse_bool_env_var(os.getenv('VOLUMES_METRICS', 'False')),
                ncm_ssp=parse_bool_env_var(os.getenv('NCM_SSP_METRICS', 'False')),
                prism_central=parse_bool_env_var(os.getenv('PRISM_CENTRAL_METRICS', 'False')),
                microseg=parse_bool_env_var(os.getenv('MICROSEG_METRICS', 'False')),
                ipmi=parse_bool_env_var(os.getenv('IPMI_METRICS', 'False')),
                ipmi_additional=parse_bool_env_var(os.getenv('IPMI_ADDITIONAL_METRICS', 'False'))
            )
            
            return cls(
                prism=os.getenv('PRISM', '127.0.0.1'),
                prism_username=os.getenv('PRISM_USERNAME', 'admin'),
                prism_secret=os.getenv('PRISM_SECRET', 'secret'),
                prism_secure=parse_bool_env_var(os.getenv('PRISM_SECURE', '')),
                app_port=int(os.getenv("APP_PORT", "9440")),
                exporter_port=int(os.getenv("EXPORTER_PORT", "8000")),
                polling_interval_seconds=int(os.getenv("POLLING_INTERVAL_SECONDS", "30")),
                operations_mode=os.getenv('OPERATIONS_MODE', 'v4'),
                api=api_config,
                metrics=metrics_config,
                vm_list=os.getenv('VM_LIST', ''),
                ipmi_username=os.getenv('IPMI_USERNAME', 'ADMIN'),
                ipmi_secret=os.getenv('IPMI_SECRET'),
                ipmi_secure=parse_bool_env_var(os.getenv('IPMI_SECURE', '')),
                ipmi_config=ipmi_config,
                show_stats_only=parse_bool_env_var(os.getenv('SHOW_STATS_ONLY', 'False')),
                page_limit=int(os.getenv('PAGE_LIMIT', '100')),
                max_workers=int(os.getenv('MAX_WORKERS', '10')),
                sampling_interval=int(os.getenv('SAMPLING_INTERVAL', '30'))
            )
        except (ValueError, TypeError) as e:
            raise ConfigurationError(f"Invalid configuration: {e}") from e

