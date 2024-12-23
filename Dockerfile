# From ubuntu lts
FROM ubuntu:20.04

# Install dependencies
RUN apt-get update && apt-get install -y \
python3 \
python3-pip \
sqlite3 \
vim

# Install Required Python Packages
RUN pip3 install meshtastic geopy folium flask

# Copy only files in src directory to /app do not copy the src directory itself
COPY src/ /app

# Set the working directory
WORKDIR /app

# Run mesh-monitor.py on startup
CMD ["python3", "mesh-visualizer.py"]