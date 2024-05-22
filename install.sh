#!/bin/bash

# Install dependencies
echo "Installing dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip

# Install pytap2
echo "Installing pytap2..."
pip3 install --upgrade pytap2

# Install Meshtastic
echo "Installing Meshtastic..."
pip3 install --upgrade meshtastic

echo "Installation complete!"