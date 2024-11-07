# meshtastic_mesh_monitor
Monitors the mesh

# Docker Install (Raspberry Pi 4 64bit)
curl -sSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Ensure docker can run as a service
systemctl enable docker