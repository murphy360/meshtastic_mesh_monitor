#!/bin/bash

image_name="meshtastic_mesh_monitor"

# Argument check (Accepts branch name as an argument, defaults to main)
branch=${1:-main}

function print_section() {
    printf "\n\n\n***************************************************\n"
    printf "$1\n"
    printf "***************************************************\n\n\n"
}

# Checkout to the specified branch
print_section "Checking out to the specified branch..."
git fetch
git checkout $branch

# git pull
print_section "Pulling the latest changes from the repository..."
git pull

# Stop and remove the Docker container
print_section "Stopping and removing the Docker container..."
docker compose -f docker/docker-compose-example.yaml down
# Clean up any leftover containers
docker container ls -a | grep $image_name | awk '{print $1}' | xargs -r docker container rm 2>/dev/null || true

# Build the Docker image
print_section "Building the Docker image..."
docker build -f docker/Dockerfile -t $image_name .

docker image ls | grep $image_name || echo "Image built successfully but not showing in grep output"

# Run Docker Compose in detached mode
print_section "Running Docker Compose in detached mode..."
docker compose -f docker/docker-compose-example.yaml up -d

# run docker logs -f
print_section "Running docker logs -f..."
docker logs meshtastic_mesh_monitor -f 