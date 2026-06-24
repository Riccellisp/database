FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into a subdirectory to preserve import path namespace
COPY . ./monitoring_service

# Set PYTHONPATH to allow importing monitoring_service modules
ENV PYTHONPATH=/app

CMD ["python", "-m", "monitoring_service.main"]
