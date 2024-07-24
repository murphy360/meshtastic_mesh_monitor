#!/bin/bash

# git pull
printf "Pulling the latest changes from the repository...\n"
git pull

# Build the Docker image
printf "Building the Docker image...\n"
docker build -t meshtastic_mesh_monitor .

# Change directory to ~/docker
printf "Changing directory to ~/docker...\n"
cd ~/docker

# Run Docker Compose in detached mode
printf "***************************************************"
printf "Running Docker Compose in detached mode...\n"
printf "***************************************************"

docker compose up -d