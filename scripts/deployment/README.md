# Deployment Scripts

This directory contains scripts to deploy the Meshtastic Mesh Monitor application.

## Scripts

### build_and_deploy_image.sh
Full deployment script using Docker Compose. This is the recommended approach for production deployments.

Features:
- Builds Docker image
- Uses Docker Compose for orchestration
- Sets up volumes and networks
- Shows container logs

Usage:
```bash
cd /path/to/meshtastic_mesh_monitor
chmod +x scripts/deployment/build_and_deploy_image.sh
./scripts/deployment/build_and_deploy_image.sh
```

### simple_deploy.sh
Simple Docker deployment without Docker Compose. Good for testing or single-container deployments.

Features:
- Builds Docker image
- Runs container directly
- Sets up volume mounts
- Shows logs

Usage:
```bash
cd /path/to/meshtastic_mesh_monitor
chmod +x scripts/deployment/simple_deploy.sh
./scripts/deployment/simple_deploy.sh
```

## Prerequisites

1. Docker installed
2. Docker Compose installed (for build_and_deploy_image.sh)
3. Environment variables set (optional):
   - `RADIO_IP`: IP address of your Meshtastic radio (default: 192.168.68.73)
   - `GEMINI_API_KEY`: Your Google Gemini API key

## Configuration

Both scripts will create a config directory at `~/mesh-monitor/config/` and copy the example configuration if it doesn't exist.

Edit `~/mesh-monitor/config/config.json` with your specific settings before running.

## Data Persistence

Data is persisted in:
- `~/mesh-monitor/data/`: Database and data files
- `~/mesh-monitor/config/`: Configuration files
- `~/mesh-monitor/logs/`: Application logs

## Troubleshooting

1. **Permission errors**: Make sure scripts are executable (`chmod +x script_name.sh`)
2. **Device access**: Ensure Docker has access to serial devices
3. **Network issues**: Check that the radio IP is accessible
4. **Build failures**: Check Dockerfile and ensure all dependencies are available
