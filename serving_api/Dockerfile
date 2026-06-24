FROM python:3.11-slim

WORKDIR /app

# Copy requirements from the root context
COPY serving_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy directories (including data_pipeline for DB models)
COPY data_pipeline ./data_pipeline
COPY serving_api ./serving_api

# Set PYTHONPATH to allow cross-imports
ENV PYTHONPATH=/app

# Expose FastAPI default port
EXPOSE 8000

# Start the application using Uvicorn
CMD ["uvicorn", "serving_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
