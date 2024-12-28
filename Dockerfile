FROM ubuntu:20.04

# Install dependencies and required Python packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    sqlite3 \
    vim

# Copy requirements.txt before installing Python packages
COPY requirements.txt /app/requirements.txt

# Install Python packages from requirements.txt
RUN pip3 install -r /app/requirements.txt

# Copy only files in src directory to /app
COPY src/ /app

# Set the working directory
WORKDIR /app

# Run mesh-monitor.py on startup
CMD ["python3", "mesh-monitor.py"]