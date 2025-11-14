#!/bin/bash
# test_enhanced.sh - Quick test script for enhanced branch

echo "=== Testing Enhanced Branch ==="
echo ""

# Test 1: Check Python version
echo -n "1. Python version: "
python3 --version || echo "FAIL - Python 3 not found"

# Test 2: Check dependencies
echo -n "2. Checking pydantic: "
python3 -c "import pydantic; print('✓ OK')" 2>/dev/null || echo "✗ FAIL - Run: pip install -r requirements.txt"

# Test 3: Test configuration
echo -n "3. Testing configuration module: "
python3 -c "
import sys
sys.path.insert(0, 'src')
from nutanix_exporter.config.settings import ExporterConfig
config = ExporterConfig.from_env()
print('✓ OK')
" 2>/dev/null || echo "✗ FAIL"

# Test 4: Test logging
echo -n "4. Testing logging module: "
python3 -c "
import sys
sys.path.insert(0, 'src')
from nutanix_exporter.utils.logger import setup_logger
logger = setup_logger()
print('✓ OK')
" 2>/dev/null || echo "✗ FAIL"

# Test 5: Test exceptions
echo -n "5. Testing exceptions module: "
python3 -c "
import sys
sys.path.insert(0, 'src')
from nutanix_exporter.utils.exceptions import NutanixAPIError
print('✓ OK')
" 2>/dev/null || echo "✗ FAIL"

# Test 6: Syntax check on main file
echo -n "6. Syntax check on main file: "
python3 -m py_compile nutanix_prometheus_exporter.py 2>/dev/null && echo "✓ OK" || echo "✗ FAIL"

# Test 7: Check if new modules exist
echo -n "7. Checking module structure: "
if [ -d "src/nutanix_exporter" ] && [ -f "src/nutanix_exporter/config/settings.py" ]; then
    echo "✓ OK"
else
    echo "✗ FAIL - Module structure missing"
fi

echo ""
echo "=== Tests Complete ==="
echo ""
echo "To run the exporter:"
echo "  export PRISM=your_prism_ip"
echo "  export PRISM_USERNAME=admin"
echo "  export PRISM_SECRET=your_secret"
echo "  python3 nutanix_prometheus_exporter.py"
echo ""
echo "Or with Docker:"
echo "  docker build -t nutanix-prometheus-exporter:enhanced ."
echo "  docker run -d -p 8000:8000 -e PRISM=... -e PRISM_USERNAME=... -e PRISM_SECRET=... nutanix-prometheus-exporter:enhanced"

