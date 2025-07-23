# Docker Setup Documentation

## Updated Docker Configuration

The Docker setup has been updated to work with the new project structure:

### Files Structure
```
docker/
├── Dockerfile              # Main container definition
└── docker-compose-example.yaml  # Compose configuration example
```

### Key Changes Made

#### 1. Dockerfile Updates
- **Build Context**: Now builds from project root with `docker/Dockerfile`
- **Source Copying**: Copies entire `src/` structure to maintain module hierarchy
- **Configuration**: Copies `config/` directory for centralized configuration
- **Directories**: Creates `/app/data` and `/app/logs` directories
- **Entry Point**: Runs `main.py` instead of `mesh-monitor.py`

#### 2. Docker Compose Updates
- **Build Context**: Uses `..` (parent directory) as context
- **Dockerfile Path**: References `docker/Dockerfile`
- **Volume Mounts**: Added config and logs directory mounts
- **Host Paths**: 
  - `~/mesh-monitor/data:/app/data` (database storage)
  - `~/mesh-monitor/config:/app/config` (configuration files)
  - `~/mesh-monitor/logs:/app/logs` (application logs)

#### 3. .dockerignore Added
- Excludes development files, tests, and local data
- Optimizes build performance
- Prevents sensitive local configs from being copied

### Building and Running

#### Option 1: Using Docker Compose (Recommended)
```bash
# From project root
cd docker
docker-compose -f docker-compose-example.yaml up --build
```

#### Option 2: Manual Docker Build
```bash
# From project root
docker build -f docker/Dockerfile -t meshtastic_mesh_monitor .
docker run -v ~/mesh-monitor/data:/app/data \
           -v ~/mesh-monitor/config:/app/config \
           -v ~/mesh-monitor/logs:/app/logs \
           --device=/dev/ttyACM1:/dev/ttyUSB0 \
           -e RADIO_IP=192.168.68.73 \
           meshtastic_mesh_monitor
```

#### Option 3: Using Deployment Script
```bash
# From project root
./scripts/deployment/build_and_deploy_image.sh [branch_name]
```

### Configuration Setup

1. **Create host directories**:
   ```bash
   mkdir -p ~/mesh-monitor/data
   mkdir -p ~/mesh-monitor/config
   mkdir -p ~/mesh-monitor/logs
   ```

2. **Copy configuration**:
   ```bash
   cp config/config.json.example ~/mesh-monitor/config/config.json
   # Edit ~/mesh-monitor/config/config.json as needed
   ```

3. **Set environment variables** in docker-compose-example.yaml:
   - `RADIO_IP`: IP address of your Meshtastic device
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - Add other environment variables as needed

### Troubleshooting

#### Import Errors
If you see import errors, ensure:
- The entire `src/` directory structure is copied to the container
- `main.py` is in the container's `/app` directory
- The `WORKDIR` is set to `/app`

#### Configuration Not Loading
- Verify config files are mounted to `/app/config/`
- Check that `config.json` exists in the mounted directory
- Ensure file permissions allow read access

#### Database Issues
- Verify `/app/data` directory exists and is writable
- Check that the volume mount for data directory is correct
- Ensure SQLite database path is `/app/data/mesh_monitor.db`

### Migration Notes

- **Entry Point**: Changed from `mesh-monitor.py` to `main.py`
- **Module Structure**: Application now uses organized module imports
- **Configuration**: Centralized in `/app/config/` directory
- **Logging**: Centralized in `/app/logs/` directory
- **Backward Compatibility**: Original files still present during transition
