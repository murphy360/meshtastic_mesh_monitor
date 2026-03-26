# Multi-stage optimized build for Meshtastic Mesh Monitor
# Reduces image size and improves security

FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages in virtual environment
COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app directory and set ownership
RUN mkdir -p /app && chown -R appuser:appuser /app
WORKDIR /app

# Copy application source code
COPY --chown=appuser:appuser app/ .

# Create data and config directories
RUN mkdir -p /data /app/logs /app/config && \
    chown -R appuser:appuser /data /app/logs /app/config

# Switch to non-root user
USER appuser

# Set Python environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port if API is offered
EXPOSE 8080

# Health check - verify database connection
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import sqlite3; sqlite3('/data/mesh.db').execute('SELECT 1')" || exit 1

# Run the application
CMD ["python3", "entrypoint.py"]
