"""Legacy API client for Nutanix Prism Element (v1/v2/v3 APIs)."""

import json
import time
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..utils.exceptions import (
    NutanixAPIError,
    AuthenticationError,
    ConnectionError,
    TimeoutError,
    RateLimitError
)
from ..utils.logger import get_logger
from ..config.settings import APIConfig

logger = get_logger(__name__)


class LegacyAPIClient:
    """Client for Nutanix Prism Element legacy APIs."""
    
    def __init__(
        self,
        api_server: str,
        username: str,
        password: str,
        port: int = 9440,
        secure: bool = False,
        api_config: Optional[APIConfig] = None
    ):
        """
        Initialize the legacy API client.
        
        Args:
            api_server: Prism Element IP or FQDN
            username: Prism username
            password: Prism password
            port: API port (default: 9440)
            secure: Whether to verify SSL certificates
            api_config: API configuration
        """
        self.api_server = api_server
        self.username = username
        self.password = password
        self.port = port
        self.secure = secure
        self.api_config = api_config or APIConfig()
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.api_config.retries,
            backoff_factor=self.api_config.sleep_between_retries / 10,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        """
        Make an HTTP request with proper error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint
            payload: Optional request payload
            headers: Optional request headers
            
        Returns:
            Response object
            
        Raises:
            NutanixAPIError: For API errors
            AuthenticationError: For authentication failures
            ConnectionError: For connection errors
            TimeoutError: For timeout errors
            RateLimitError: For rate limit errors
        """
        url = f"https://{self.api_server}:{self.port}{endpoint}"
        
        default_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if headers:
            default_headers.update(headers)
        
        response: Optional[requests.Response] = None
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(
                    url,
                    headers=default_headers,
                    auth=(self.username, self.password),
                    verify=self.secure,
                    timeout=self.api_config.timeout_seconds
                )
            elif method.upper() == 'POST':
                response = self.session.post(
                    url,
                    headers=default_headers,
                    data=json.dumps(payload) if payload else None,
                    auth=(self.username, self.password),
                    verify=self.secure,
                    timeout=self.api_config.timeout_seconds
                )
            elif method.upper() == 'PUT':
                response = self.session.put(
                    url,
                    headers=default_headers,
                    data=json.dumps(payload) if payload else None,
                    auth=(self.username, self.password),
                    verify=self.secure,
                    timeout=self.api_config.timeout_seconds
                )
            elif method.upper() == 'PATCH':
                response = self.session.patch(
                    url,
                    headers=default_headers,
                    data=json.dumps(payload) if payload else None,
                    auth=(self.username, self.password),
                    verify=self.secure,
                    timeout=self.api_config.timeout_seconds
                )
            elif method.upper() == 'DELETE':
                response = self.session.delete(
                    url,
                    headers=default_headers,
                    data=json.dumps(payload) if payload else None,
                    auth=(self.username, self.password),
                    verify=self.secure,
                    timeout=self.api_config.timeout_seconds
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check response status
            if response.status_code == 401:
                error_msg = f"Authentication failed for {url}"
                logger.error(error_msg)
                raise AuthenticationError(error_msg, response.status_code, response.text)
            
            if response.status_code == 429:
                error_msg = f"Rate limit exceeded for {url}"
                logger.warning(error_msg)
                raise RateLimitError(error_msg, response.status_code, response.text)
            
            if response.status_code >= 500:
                error_msg = f"Server error {response.status_code} for {url}: {response.text}"
                logger.error(error_msg)
                raise NutanixAPIError(error_msg, response.status_code, response.text)
            
            if not response.ok:
                error_msg = f"Request failed with status {response.status_code} for {url}: {response.text}"
                logger.error(error_msg)
                raise NutanixAPIError(error_msg, response.status_code, response.text)
            
            return response
            
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timeout for {url}: {str(e)}"
            logger.error(error_msg)
            raise TimeoutError(error_msg) from e
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error for {url}: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e
            
        except (AuthenticationError, RateLimitError, NutanixAPIError):
            # Re-raise our custom exceptions
            raise
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error for {url}: {str(e)}"
            logger.error(error_msg)
            raise NutanixAPIError(error_msg) from e
    
    def get_cluster(self) -> Dict[str, Any]:
        """Get cluster information."""
        endpoint = "/PrismGateway/services/rest/v2.0/clusters/"
        response = self._make_request('GET', endpoint)
        json_resp = response.json()
        if json_resp.get('entities'):
            return json_resp['entities'][0]
        raise NutanixAPIError("No cluster entities found in response")
    
    def get_vms(self) -> list:
        """Get list of VMs."""
        endpoint = "/PrismGateway/services/rest/v2.0/vms/"
        response = self._make_request('GET', endpoint)
        json_resp = response.json()
        return json_resp.get('entities', [])
    
    def get_vm(self, vm_name: str) -> Optional[Dict[str, Any]]:
        """Get specific VM by name."""
        endpoint = f"/PrismGateway/services/rest/v2.0/vms/?filter=vm_name=={vm_name}"
        response = self._make_request('GET', endpoint)
        json_resp = response.json()
        entities = json_resp.get('entities', [])
        return entities[0] if entities else None
    
    def get_hosts(self) -> list:
        """Get list of hosts."""
        endpoint = "/PrismGateway/services/rest/v2.0/hosts/"
        response = self._make_request('GET', endpoint)
        json_resp = response.json()
        return json_resp.get('entities', [])
    
    def get_storage_containers(self) -> list:
        """Get list of storage containers."""
        endpoint = "/PrismGateway/services/rest/v2.0/storage_containers/"
        response = self._make_request('GET', endpoint)
        json_resp = response.json()
        return json_resp.get('entities', [])
    
    def get_volume_groups(self) -> list:
        """Get list of volume groups."""
        endpoint = "/PrismGateway/services/rest/v2.0/volume_groups/"
        response = self._make_request('GET', endpoint)
        json_resp = response.json()
        return json_resp.get('entities', [])

