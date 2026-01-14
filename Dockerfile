# Multi-stage build for fitness tracker
# Base image: Python 3.12.0
FROM python:3.12.0-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies including Playwright requirements
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libsqlite3-dev \
    curl \
    # Playwright/Chromium dependencies
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only for TrainingPeaks sync)
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs data/ai_coach_output data/proposed_workout_jsons data/rag_context data/trainingpeaks_downloads data/trainingpeaks_extracted

# Set permissions
RUN chmod +x docker-entrypoint.sh || true

# Expose ports
# 8000 - FastAPI
# 8501 - Streamlit
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Entry point
ENTRYPOINT ["./docker-entrypoint.sh"]
