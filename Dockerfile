FROM ubuntu:20.04

# Install dependencies and required Python packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    sqlite3 \
    vim && \
    pip3 install meshtastic geopy folium Flask

# Copy only files in src directory to /app
COPY src/ /app

# Set the working directory
WORKDIR /app

# Run mesh-monitor.py on startup
CMD ["python3", "mesh-monitor.py"]