FROM python:3.11-slim

WORKDIR /app

# Copy requirements from the root context
COPY data_pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application and shared dependency directories
COPY data_pipeline ./data_pipeline
COPY monitoring_service ./monitoring_service

# Set PYTHONPATH to allow cross-imports
ENV PYTHONPATH=/app

CMD ["python", "-m", "data_pipeline.main_pipeline"]
