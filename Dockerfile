FROM ubuntu:latest

# Install dependencies
RUN apt update && apt install -y python3 

# Install pip
RUN apt install python3-pip

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