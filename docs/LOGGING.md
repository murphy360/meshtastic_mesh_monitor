# Unified Logging System

The Meshtastic Mesh Monitor uses a unified logging system that provides consistent, configurable logging across all modules. This system supports both development testing and production deployment scenarios.

## Quick Start

### Method 1: Environment Variables (Recommended)

Set environment variables to configure logging:

```bash
# Development setup
export LOG_LEVEL=DEBUG
export LOG_TO_FILE=true
export LOG_CONSOLE=true

# Production setup  
export LOG_LEVEL=INFO
export LOG_TO_FILE=true
export LOG_CONSOLE=true
```

### Method 2: Configuration File

Add a logging section to your `config.json`:

```json
{
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "to_file": true,
    "console": true,
    "file_max_size_mb": 10,
    "backup_count": 5,
    "environment_preset": "production"
  }
}
```

### Method 3: Copy Environment Template

```bash
cp config/logging.env.example .env
# Edit .env file with your preferences
```

## Using the Logger in Your Code

```python
from utils.logger import get_logger

# Get a logger for your module
logger = get_logger(__name__)

# Use the logger
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error")
```

## Configuration Options

### Log Levels
- `DEBUG`: Detailed information for diagnosing problems
- `INFO`: General information about program execution
- `WARNING`: Something unexpected happened, but the software is still working
- `ERROR`: A serious problem occurred
- `CRITICAL`: A very serious error occurred

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_FORMAT` | See below | Custom log message format |
| `LOG_TO_FILE` | `true` | Enable file logging |
| `LOG_FILE_PATH` | Auto-generated | Custom log file path |
| `LOG_FILE_MAX_SIZE` | `10485760` | Max file size in bytes (10MB) |
| `LOG_FILE_BACKUP_COUNT` | `5` | Number of backup files to keep |
| `LOG_CONSOLE` | `true` | Enable console output |

### Default Log Format

```
%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s
```

## Environment Presets

### Development Preset
```python
from utils.logger import setup_development_logging
setup_development_logging()
```
- **Level**: DEBUG
- **Format**: Includes function names and line numbers
- **Output**: Both console and file
- **Use case**: Local development and debugging

### Production Preset
```python
from utils.logger import setup_production_logging
setup_production_logging()
```
- **Level**: INFO
- **Format**: Clean, structured format
- **Output**: Both console and file
- **Use case**: Production deployment

### Testing Preset
```python
from utils.logger import setup_quiet_logging
setup_quiet_logging()
```
- **Level**: WARNING
- **Format**: Minimal
- **Output**: File only
- **Use case**: Automated testing

## File Management

### Log File Locations

- **Docker**: `/data/mesh_monitor_YYYYMMDD_HHMMSS.log`
- **Local Development**: `./logs/mesh_monitor_YYYYMMDD_HHMMSS.log`
- **Custom**: Set via `LOG_FILE_PATH` environment variable

### Log Rotation

The system automatically rotates log files when they reach the maximum size:
- Files are rotated with `.1`, `.2`, `.3` extensions
- Old files are automatically deleted based on `LOG_FILE_BACKUP_COUNT`
- No manual intervention required

## Integration with Config Manager

You can also manage logging through the configuration system:

```python
from config.config_manager import ConfigManager

config_manager = ConfigManager()

# Apply a preset
config_manager.apply_logging_preset("development")

# Update specific settings
config_manager.update_logging_config(level="DEBUG", console=True)

# Get current logging config
logging_config = config_manager.get_logging_config()
```

## Docker Deployment

The logging system automatically detects Docker environments and adjusts paths accordingly. No special configuration needed.

### Docker Compose Example

```yaml
services:
  mesh-monitor:
    build: .
    environment:
      - LOG_LEVEL=INFO
      - LOG_TO_FILE=true
      - LOG_CONSOLE=true
    volumes:
      - ./data:/data
```

## Troubleshooting

### Common Issues

1. **Logs not appearing**: Check `LOG_CONSOLE=true` and `LOG_LEVEL`
2. **File not created**: Verify write permissions and `LOG_TO_FILE=true`
3. **Too much output**: Set `LOG_LEVEL=WARNING` or higher
4. **Missing log entries**: Check if log level is appropriate

### Debug Mode

For maximum logging detail:

```bash
export LOG_LEVEL=DEBUG
export LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(process)d - %(thread)d - %(message)s"
```

### Performance Considerations

- **DEBUG level**: Generates significant output, use only for development
- **File logging**: Minimal performance impact with rotation
- **Console logging**: May slow down in high-volume scenarios

## Migration from Old Logging

The new system is backward compatible. Existing `logging.*` calls will continue to work, but consider updating to use the new logger:

```python
# Old way (still works)
import logging
logging.info("Message")

# New way (recommended)
from utils.logger import get_logger
logger = get_logger(__name__)
logger.info("Message")
```

## Examples

### Development Setup
```bash
# Maximum detail for debugging
export LOG_LEVEL=DEBUG
export LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
export LOG_TO_FILE=true
export LOG_CONSOLE=true
```

### Production Setup
```bash
# Clean, efficient logging
export LOG_LEVEL=INFO
export LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
export LOG_TO_FILE=true
export LOG_CONSOLE=true
export LOG_FILE_MAX_SIZE=52428800  # 50MB
export LOG_FILE_BACKUP_COUNT=10
```

### Testing Setup
```bash
# Minimal noise during tests
export LOG_LEVEL=WARNING
export LOG_TO_FILE=true
export LOG_CONSOLE=false
```

### Custom Format Examples

```bash
# Timestamp only
export LOG_FORMAT="%(asctime)s - %(levelname)s: %(message)s"

# With thread info for concurrent debugging
export LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(thread)d - %(message)s"

# Minimal for embedded systems
export LOG_FORMAT="%(levelname)s: %(message)s"
```
