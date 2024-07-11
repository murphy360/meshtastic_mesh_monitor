# From ubuntu lts
FROM ubuntu:20.04

# Install dependencies
RUN apt-get update && apt-get install -y \
python3 \
python3-pip \
sqlite3 \
vim

# Install Required Python Packages
RUN pip3 install meshtastic geopy

# Copy mesh-monitor.py to the container
COPY mesh-monitor.py /app/mesh-monitor.py

# Copy sitrep.py to the container
COPY sitrep.py /app/sitrep.py

# Set the working directory
WORKDIR /app

# Run mesh-monitor.py on startup
CMD ["python3", "mesh-monitor.py"]