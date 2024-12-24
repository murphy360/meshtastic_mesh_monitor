#!/bin/bash

# Argument check (Accepts branch name as an argument, defaults to main)
if [ -z "$1" ]; then
    branch="main"
else
    branch=$1
fi

# git pull
printf "\n\n\n***************************************************\n"
printf "Pulling the latest changes from the repository...\n"
printf "***************************************************\n\n\n"
git pull

# Checkout to the specified branch
printf "\n\n\n***************************************************\n"
printf "Checking out to the specified branch...\n"
printf "***************************************************\n\n\n"
git checkout $branch

# Stop and remove the Docker container
printf "\n\n\n***************************************************\n"
printf "Stopping and removing the Docker container...\n"
printf "***************************************************\n\n\n"
docker compose down
docker container ls -a | grep mesh
docker container ls -a | grep mesh | awk '{print $1}' | xargs docker container rm


# Build the Docker image
printf "\n\n\n***************************************************\n"
printf "Building the Docker image...\n"
printf "***************************************************\n\n\n"
docker build -t meshtastic_mesh_monitor .

docker image ls | grep mesh
ls -la

# Run Docker Compose in detached mode
printf "\n\n\n***************************************************\n"
printf "Running Docker Compose in detached mode...\n"
printf "***************************************************\n\n\n"
docker compose up -d

# run docker logs -f
printf "\n\n\n***************************************************\n"
printf "Running docker logs -f...\n"
printf "***************************************************\n\n\n"
docker logs -f meshtastic_mesh_monitor