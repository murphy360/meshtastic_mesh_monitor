#!/bin/bash

# git pull
print "Pulling the latest changes from the repository...\n"
git pull

# Build the Docker image
print "Building the Docker image...\n"
docker build -t meshtastic_mesh_monitor .

# Change directory to ~/docker
print "Changing directory to ~/docker...\n"
cd ~/docker

# Run Docker Compose in detached mode
print "***************************************************"
print "Running Docker Compose in detached mode...\n"
print "***************************************************"

docker compose up -d