FROM ubuntu:22.04

# Install dependencies and required Python packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    sqlite3 \
    vim

# Copy requirements.txt before installing Python packages
COPY requirements.txt /app/requirements.txt

# Install Python packages from requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Copy the entire src directory structure to /app
COPY src/ /app/

# Copy configuration files to /app/config_files (separate from Python config module)
COPY config/ /app/config_files/

# Copy Docker entrypoint script
COPY docker/entrypoint.py /app/entrypoint.py

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Set the working directory
WORKDIR /app

# Set Python path to include the app directory  
ENV PYTHONPATH=/app

# Use our custom entrypoint that ensures proper Python path
CMD ["python3", "entrypoint.py"]
