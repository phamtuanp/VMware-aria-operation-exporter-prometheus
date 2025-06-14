# VMware Aria Operations Prometheus Exporter Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY vmware_aria_exporter.py .
COPY vmware_aria_exporter_advanced.py .
COPY config.yaml .

# Create non-root user
RUN useradd --create-home --shell /bin/bash exporter
USER exporter

# Expose metrics port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/metrics || exit 1

# Default command
CMD ["python", "vmware_aria_exporter_advanced.py", "--config", "config.yaml"]