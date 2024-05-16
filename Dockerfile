FROM ubuntu:latest

# Install dependencies
RUN apt-get update && apt-get install -y python3 

# Install pip
RUN python3 -m ensurepip --upgrade

# Install Meshtastic
RUN pip3 install meshtastic

# Copy mesh-monitor.py to the container
COPY mesh-monitor.py /app/mesh-monitor.py

# Copy sitrep.py to the container
COPY sitrep.py /app/sitrep.py

# Set the working directory
WORKDIR /app

# Run mesh-monitor.py on startup
CMD ["python3", "mesh-monitor.py"]