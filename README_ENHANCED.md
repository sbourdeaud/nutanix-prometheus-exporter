# Nutanix Prometheus Exporter - Enhanced Branch

This is the `cursor-enhanced` branch containing significant code quality improvements and bug fixes.

## Quick Start

The enhanced branch maintains full backward compatibility. You can use it exactly like the original:

```bash
docker build -t nutanix-prometheus-exporter:enhanced .
docker run -d --name nutanix-exporter \
  -p 8000:8000 \
  -e PRISM=192.168.0.10 \
  -e PRISM_USERNAME=admin \
  -e PRISM_SECRET=mysecret \
  nutanix-prometheus-exporter:enhanced
```

## What's New

### ✅ Critical Bug Fixes
- Fixed exception handling bug where `response` variable was accessed before definition
- Improved error handling throughout the codebase

### ✅ New Features
- **Configuration Management**: Type-safe configuration using Pydantic
- **Logging System**: Proper logging with colored output
- **Custom Exceptions**: Better error handling with specific exception types
- **Improved API Client**: Enhanced legacy API client with retry logic
- **Code Quality Tools**: Black, MyPy, Flake8 configurations

### ✅ Security Improvements
- Dockerfile runs as non-root user
- Added healthcheck to Dockerfile
- Pinned Python version

### ✅ Code Structure
- New modular package structure (`src/nutanix_exporter/`)
- Foundation for future refactoring
- Better separation of concerns

## File Structure

```
.
├── src/nutanix_exporter/          # New modular structure
│   ├── config/                    # Configuration management
│   ├── api/                       # API clients
│   ├── utils/                     # Utilities (logging, exceptions)
│   ├── metrics/                   # (Future: metric classes)
│   └── exporter/                  # (Future: exporter logic)
├── nutanix_prometheus_exporter.py # Original file (with bug fixes)
├── Dockerfile                     # Enhanced with security
├── requirements.txt               # Updated with pydantic
├── pyproject.toml                 # Code quality tool configs
├── .black                         # Black formatter config
├── .flake8                        # Flake8 linter config
├── .editorconfig                  # Editor consistency
├── CHANGELOG.md                   # Change tracking
└── ENHANCEMENTS.md                # Detailed improvements
```

## Using New Features

### Configuration Example

```python
from nutanix_exporter.config.settings import ExporterConfig

# Load from environment variables
config = ExporterConfig.from_env()

# Access configuration
print(f"Prism: {config.prism}")
print(f"Port: {config.exporter_port}")
print(f"Cluster metrics: {config.metrics.cluster}")
```

### Logging Example

```python
from nutanix_exporter.utils.logger import setup_logger

logger = setup_logger(level="INFO")
logger.info("Starting exporter")
logger.error("An error occurred")
```

### API Client Example

```python
from nutanix_exporter.api.legacy_client import LegacyAPIClient
from nutanix_exporter.config.settings import APIConfig

api_config = APIConfig(timeout_seconds=30, retries=5)
client = LegacyAPIClient(
    api_server="192.168.1.10",
    username="admin",
    password="secret",
    secure=False,
    api_config=api_config
)

try:
    cluster = client.get_cluster()
    print(f"Cluster: {cluster['name']}")
except AuthenticationError:
    print("Authentication failed")
except NutanixAPIError as e:
    print(f"API error: {e}")
```

## Development

### Code Quality

```bash
# Format code
black src/ nutanix_prometheus_exporter.py

# Type checking
mypy src/nutanix_exporter/

# Linting
flake8 src/ nutanix_prometheus_exporter.py
```

### Testing

The new modules are ready for use but the main script still uses the original code (with bug fixes). This allows for gradual migration.

## Migration Notes

- **Backward Compatible**: All existing functionality works as before
- **Environment Variables**: No changes required
- **API Behavior**: Preserved exactly
- **Only Fixes**: Critical bugs fixed, no breaking changes

## Next Steps

Future improvements can include:
1. Full integration of new modules into main script
2. Complete type hints
3. Unit tests
4. Rate limiting
5. Async support

## Documentation

- See `ENHANCEMENTS.md` for detailed improvement descriptions
- See `CHANGELOG.md` for change history
- Original README.md still applies for usage

## Contributing

When contributing to this branch:
1. Follow the code quality standards (Black, Flake8)
2. Add type hints where possible
3. Use the new logging system
4. Write tests for new features
5. Update CHANGELOG.md

## Support

For issues or questions:
- Check `ENHANCEMENTS.md` for implementation details
- Review the original README.md for usage
- The code maintains backward compatibility

