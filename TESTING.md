# Testing Guide - cursor-enhanced Branch

This guide explains how to test the enhanced branch.

## Prerequisites

- Python 3.9+ (3.11 recommended)
- pip
- Docker (optional, for containerized testing)

## Quick Start

### 1. Install Dependencies

```bash
# Install all dependencies including new pydantic
pip install -r requirements.txt
```

### 2. Test New Modules

#### Test Configuration Module

```bash
python3 -c "
import sys
sys.path.insert(0, 'src')
from nutanix_exporter.config.settings import ExporterConfig
import os

# Set test environment variables
os.environ['PRISM'] = '192.168.1.10'
os.environ['PRISM_USERNAME'] = 'admin'
os.environ['PRISM_SECRET'] = 'test123'

# Test configuration loading
config = ExporterConfig.from_env()
print(f'✓ Configuration loaded successfully')
print(f'  Prism: {config.prism}')
print(f'  Port: {config.exporter_port}')
print(f'  Operations Mode: {config.operations_mode}')
print(f'  Cluster Metrics: {config.metrics.cluster}')
"
```

#### Test Logging Module

```bash
python3 -c "
import sys
sys.path.insert(0, 'src')
from nutanix_exporter.utils.logger import setup_logger

logger = setup_logger(level='INFO')
logger.info('✓ Logging system works!')
logger.warning('This is a warning')
logger.error('This is an error (test)')
"
```

#### Test Exceptions Module

```bash
python3 -c "
import sys
sys.path.insert(0, 'src')
from nutanix_exporter.utils.exceptions import (
    NutanixAPIError,
    AuthenticationError,
    RateLimitError
)

# Test exception creation
try:
    raise AuthenticationError('Test authentication error', status_code=401)
except AuthenticationError as e:
    print(f'✓ Custom exceptions work!')
    print(f'  Error: {e}')
    print(f'  Status Code: {e.status_code}')
"
```

### 3. Test Original Script (With Bug Fixes)

The original script still works but with critical bugs fixed:

```bash
# Set environment variables
export PRISM=192.168.1.10
export PRISM_USERNAME=admin
export PRISM_SECRET=your_secret_here
export OPERATIONS_MODE=v4
export EXPORTER_PORT=8000

# Run the exporter
python3 nutanix_prometheus_exporter.py
```

The script will:
- Start the HTTP server on port 8000
- Begin collecting metrics
- Display colored output

**Test the metrics endpoint:**
```bash
# In another terminal
curl http://localhost:8000/metrics
```

### 4. Test Exception Handling Fix

To verify the bug fix works, you can test with an invalid endpoint:

```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from nutanix_prometheus_exporter import process_request
import requests

# This should now handle errors properly without NameError
try:
    result = process_request(
        url='https://invalid-host:9440/test',
        method='GET',
        user='admin',
        password='secret',
        headers={'Content-Type': 'application/json'},
        api_requests_timeout_seconds=5,
        api_requests_retries=1,
        secure=False
    )
except Exception as e:
    print(f'✓ Exception handling works: {type(e).__name__}')
    print(f'  Error: {str(e)[:100]}...')
"
```

### 5. Test with Docker

#### Build the Image

```bash
docker build -t nutanix-prometheus-exporter:enhanced .
```

#### Run the Container

```bash
docker run -d \
  --name nutanix-exporter-test \
  -p 8000:8000 \
  -e PRISM=192.168.1.10 \
  -e PRISM_USERNAME=admin \
  -e PRISM_SECRET=your_secret_here \
  -e OPERATIONS_MODE=v4 \
  nutanix-prometheus-exporter:enhanced
```

#### Check Container Health

```bash
# Check if container is running
docker ps | grep nutanix-exporter-test

# Check logs
docker logs nutanix-exporter-test

# Check health status
docker inspect --format='{{.State.Health.Status}}' nutanix-exporter-test

# Test metrics endpoint
curl http://localhost:8000/metrics
```

#### Stop and Remove

```bash
docker stop nutanix-exporter-test
docker rm nutanix-exporter-test
```

## Comprehensive Test Script

Create a test script to verify everything:

```bash
#!/bin/bash
# test_enhanced.sh

echo "=== Testing Enhanced Branch ==="

# Test 1: Check Python version
echo -n "1. Python version: "
python3 --version

# Test 2: Check dependencies
echo -n "2. Checking pydantic: "
python3 -c "import pydantic; print('OK')" || echo "FAIL - Run: pip install -r requirements.txt"

# Test 3: Test configuration
echo -n "3. Testing configuration module: "
python3 -c "
import sys
sys.path.insert(0, 'src')
from nutanix_exporter.config.settings import ExporterConfig
config = ExporterConfig.from_env()
print('OK')
" || echo "FAIL"

# Test 4: Test logging
echo -n "4. Testing logging module: "
python3 -c "
import sys
sys.path.insert(0, 'src')
from nutanix_exporter.utils.logger import setup_logger
logger = setup_logger()
print('OK')
" || echo "FAIL"

# Test 5: Test exceptions
echo -n "5. Testing exceptions module: "
python3 -c "
import sys
sys.path.insert(0, 'src')
from nutanix_exporter.utils.exceptions import NutanixAPIError
print('OK')
" || echo "FAIL"

# Test 6: Syntax check on main file
echo -n "6. Syntax check on main file: "
python3 -m py_compile nutanix_prometheus_exporter.py && echo "OK" || echo "FAIL"

echo "=== Tests Complete ==="
```

Make it executable and run:
```bash
chmod +x test_enhanced.sh
./test_enhanced.sh
```

## Testing Specific Features

### Test Configuration Validation

```bash
python3 -c "
import sys
sys.path.insert(0, 'src')
from nutanix_exporter.config.settings import ExporterConfig
import os

# Test invalid operations mode
os.environ['OPERATIONS_MODE'] = 'invalid'
try:
    config = ExporterConfig.from_env()
    print('FAIL: Should have raised ValueError')
except ValueError as e:
    print(f'✓ Validation works: {e}')
"
```

### Test API Client (if you have a test Prism instance)

```bash
python3 -c "
import sys
sys.path.insert(0, 'src')
from nutanix_exporter.api.legacy_client import LegacyAPIClient
from nutanix_exporter.config.settings import APIConfig

# Replace with your test Prism details
api_config = APIConfig(timeout_seconds=10, retries=2)
client = LegacyAPIClient(
    api_server='192.168.1.10',
    username='admin',
    password='your_password',
    secure=False,
    api_config=api_config
)

try:
    cluster = client.get_cluster()
    print(f'✓ API client works! Cluster: {cluster.get(\"name\", \"unknown\")}')
except Exception as e:
    print(f'API call failed (expected if Prism not accessible): {type(e).__name__}')
"
```

## Verification Checklist

- [ ] Dependencies install successfully
- [ ] Configuration module loads from environment
- [ ] Logging system works
- [ ] Custom exceptions work
- [ ] Original script runs without errors
- [ ] Exception handling fix works (no NameError)
- [ ] Docker image builds successfully
- [ ] Container runs and healthcheck passes
- [ ] Metrics endpoint responds

## Troubleshooting

### Issue: ModuleNotFoundError for pydantic
**Solution**: `pip install -r requirements.txt`

### Issue: Import errors for new modules
**Solution**: Make sure you're in the project root and `src/` directory exists

### Issue: Docker build fails
**Solution**: Check Dockerfile syntax and ensure all files are present

### Issue: Container healthcheck fails
**Solution**: Wait a bit longer (40s start period) or check if exporter is actually running

## Next Steps

After testing:
1. Review the logs for any warnings
2. Test with your actual Nutanix environment
3. Verify metrics are being collected correctly
4. Check that the bug fixes resolved previous issues

