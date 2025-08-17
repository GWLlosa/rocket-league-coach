# Use Python 3.9 slim image for better compatibility
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies needed for numpy/scipy/carball
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gfortran \
    libblas-dev \
    liblapack-dev \
    pkg-config \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and app directory
RUN useradd --create-home --shell /bin/bash app && \
    mkdir -p /app/data/replays /app/data/cache /app/data/players && \
    chown -R app:app /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
# Use --prefer-binary to avoid compiling from source when possible
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefer-binary --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure proper ownership of all files
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "src.main"]
