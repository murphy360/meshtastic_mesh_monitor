#!/bin/bash

# Simple Docker build and run script
image_name="meshtastic_mesh_monitor"
container_name="meshtastic_mesh_monitor"

function print_section() {
    printf "\n\n\n***************************************************\n"
    printf "$1\n"
    printf "***************************************************\n\n\n"
}

# Stop and remove existing container
print_section "Stopping and removing existing container..."
docker stop $container_name 2>/dev/null || true
docker rm $container_name 2>/dev/null || true

# Build the Docker image
print_section "Building the Docker image..."
docker build -f docker/Dockerfile -t $image_name .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully"
    docker image ls | grep $image_name
else
    echo "❌ Docker build failed"
    exit 1
fi

# Create necessary host directories
print_section "Creating host directories..."
mkdir -p ~/mesh-monitor/data
mkdir -p ~/mesh-monitor/config
mkdir -p ~/mesh-monitor/logs

# Copy config example if it doesn't exist
if [ ! -f ~/mesh-monitor/config/config.json ]; then
    print_section "Copying config example..."
    cp config/config.json.example ~/mesh-monitor/config/config.json
    echo "📝 Please edit ~/mesh-monitor/config/config.json with your settings"
fi

# Run the container
print_section "Starting the container..."
docker run -d \
    --name $container_name \
    -v ~/mesh-monitor/data:/app/data \
    -v ~/mesh-monitor/config:/app/config \
    -v ~/mesh-monitor/logs:/app/logs \
    -e RADIO_IP=${RADIO_IP:-192.168.68.73} \
    -e GEMINI_API_KEY=${GEMINI_API_KEY} \
    --device=/dev/ttyACM1:/dev/ttyUSB0 \
    $image_name

if [ $? -eq 0 ]; then
    echo "✅ Container started successfully"
    print_section "Container status..."
    docker ps | grep $container_name
    
    print_section "Following logs (Ctrl+C to exit)..."
    docker logs -f $container_name
else
    echo "❌ Failed to start container"
    exit 1
fi
