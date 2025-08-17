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
    libatlas-base-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
# Use --prefer-binary to avoid compiling from source when possible
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefer-binary --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/replays data/cache data/players && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "src.main"]
