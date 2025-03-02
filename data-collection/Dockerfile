# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        # Dependencies for web scraping
        chromium \
        chromium-driver \
        playwright \
        # Dependencies for data processing
        libgomp1 \
        # Dependencies for geographic data
        gdal-bin \
        libgdal-dev \
        # Dependencies for database clients
        libpq-dev \
        # Dependencies for prophet
        cmake \
        # Additional tools
        procps \
        htop \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional ML models and language resources
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download en_core_web_lg
RUN python -m nltk.downloader punkt stopwords averaged_perceptron_tagger wordnet

# Install Playwright browsers
RUN playwright install chromium

# Set up Chrome WebDriver for Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Set Python path
ENV PYTHONPATH=/app

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app

# Create data directories and set permissions
RUN mkdir -p /app/data/raw \
    /app/data/processed \
    /app/data/interim \
    /app/data/external \
    /app/logs \
    /app/models \
    && chown -R appuser:appuser /app/data \
    && chown -R appuser:appuser /app/logs \
    && chown -R appuser:appuser /app/models

# Switch to non-root user
USER appuser

# Copy source code
COPY . .

# Expose service ports
EXPOSE 8000
EXPOSE 8080
EXPOSE 8793
EXPOSE 5555
EXPOSE 8888

# Set up Airflow
ENV AIRFLOW_HOME=/app/airflow
RUN airflow db init
RUN airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com

# Set up Prefect
ENV PREFECT_HOME=/app/prefect
RUN prefect config set PREFECT_API_URL="http://localhost:4200/api"

# Set up environment for data collection
ENV DATA_COLLECTION_ENV=production
ENV DATA_STORAGE_PATH=/app/data
ENV MODELS_PATH=/app/models
ENV LOG_PATH=/app/logs

# Start services
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
