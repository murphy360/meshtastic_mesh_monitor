#!/bin/bash

# git pull
git pull

# Build the Docker image
docker build -t meshtastic_mesh_monitor .

# Change directory to ~/docker
cd ~/docker

# Run Docker Compose in detached mode
docker compose up -d