#!/bin/bash

# git pull
print "\n\n\n***************************************************\n"
print "Pulling the latest changes from the repository...\n"
print "***************************************************\n\n\n"
git pull

# Build the Docker image
print "Building the Docker image...\n"
docker build -t meshtastic_mesh_monitor .

# Change directory to ~/docker
print "\n\n\n***************************************************\n"
print "Changing directory to ~/docker...\n"
print "***************************************************\n\n\n"
cd ~/docker

# Run Docker Compose in detached mode
print "\n\n\n***************************************************\n"
print "Running Docker Compose in detached mode...\n"
print "***************************************************\n\n\n"
docker compose up -d