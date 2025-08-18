FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for scipy and numpy
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install wheel first
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Install numpy first (required for scipy)
RUN pip install --no-cache-dir 'numpy>=1.22.4,<2.0'

# Install scipy with numpy already present
RUN pip install --no-cache-dir 'scipy>=1.7.0,<2.0'

# Install the rest of the requirements
RUN pip install --no-cache-dir -r requirements.txt || true

# Install carball separately without strict dependencies
RUN pip install --no-cache-dir --no-deps carball || true

# Create necessary directories
RUN mkdir -p /app/data/replays /app/data/cache /app/data/players /app/logs

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 app && \
    chown -R app:app /app

USER app

# Set Python path
ENV PYTHONPATH=/app:/app/src:$PYTHONPATH

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "src.main"]
