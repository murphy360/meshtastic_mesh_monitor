#!/bin/bash

# git pull
printf "***************************************************\n"
printf "Pulling the latest changes from the repository...\n"
printf "***************************************************\n\n\n"
git pull

# Build the Docker image
printf "***************************************************\n"
printf "Building the Docker image...\n"
printf "***************************************************\n\n\n"
docker build -t meshtastic_mesh_monitor .

# Change directory to ~/docker
printf "***************************************************\n"
printf "Changing directory to ~/docker...\n"
printf "***************************************************\n\n\n"
cd ~/docker

# Run Docker Compose in detached mode
printf "***************************************************\n"
printf "Running Docker Compose in detached mode...\n"
printf "***************************************************\n\n\n"
docker compose up -d