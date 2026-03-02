# Development Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements-dev.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-dev.txt

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/logs

EXPOSE 8000

# Development command (can be overridden in docker-compose.yml)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
