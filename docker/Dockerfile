# Dockerfile for Fraud Detection API
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY ../requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY ../api /app/api
COPY ../models /app/models
COPY ../streaming /app/streaming
COPY ../config.py /app/config.py

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "-m", "api.app"]

