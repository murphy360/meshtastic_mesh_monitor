#!/bin/bash

# Docker and Docker Compose installation script for Ubuntu 25.05 server
# Meshtastic Mesh Monitor Dependencies

set -e

echo "Installing Docker and Docker Compose on Ubuntu 25.05..."
echo "======================================================"

# Step 1: Update Package Repositories
echo "Step 1: Updating package repositories..."
sudo apt update

# Step 2: Install Docker Dependencies
echo "Step 2: Installing Docker dependencies..."
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Step 3: Add Docker GPG Key
echo "Step 3: Adding Docker GPG key..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Step 4: Set up the Docker Stable Repository
echo "Step 4: Setting up Docker stable repository..."
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Step 5: Install Docker Engine
echo "Step 5: Installing Docker Engine..."
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Step 6: Enable and Start Docker Service
echo "Step 6: Enabling and starting Docker service..."
sudo systemctl enable docker
sudo systemctl start docker

# Step 7: Verify Docker Installation
echo "Step 7: Verifying Docker installation..."
sudo docker run hello-world

# Step 8: Install Docker Compose
echo "Step 8: Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Step 9: Verify Docker Compose Installation
echo "Step 9: Verifying Docker Compose installation..."
docker-compose --version

# Additional: Add current user to docker group (optional)
echo "Additional: Adding current user to docker group..."
sudo usermod -aG docker $USER

echo "======================================================"
echo "Installation completed successfully!"
echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker-compose --version)"
echo ""
echo "IMPORTANT: Please log out and log back in for docker group changes to take effect."
echo "After logging back in, you can run Docker commands without sudo."
echo "To test: docker run hello-world"
