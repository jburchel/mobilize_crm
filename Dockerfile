# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create an empty firebase-credentials.json file if it doesn't exist
RUN if [ ! -f firebase-credentials.json ]; then echo "{}" > firebase-credentials.json; fi

# Verify that all necessary directories and files exist
RUN echo "Verifying necessary directories and files..." && \
    ls -la && \
    echo "Checking templates directory:" && \
    ls -la templates/ || echo "Templates directory not found!" && \
    echo "Checking static directory:" && \
    ls -la static/ || echo "Static directory not found!"

# Expose port
EXPOSE 8080

# Run the application with Gunicorn
CMD exec gunicorn --bind :8080 --workers 1 --threads 8 --timeout 0 app:app 