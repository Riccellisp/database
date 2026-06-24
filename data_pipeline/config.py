import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Kafka Configurations
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")
    TELEMETRY_TOPIC = os.getenv("TELEMETRY_TOPIC", "telemetry")

    # MinIO / S3 Configurations
    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "admin")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "strongpassword123")
    
    # Bucket Names
    BRONZE_BUCKET = os.getenv("BRONZE_BUCKET", "bronze-telemetry")
    SILVER_BUCKET = os.getenv("SILVER_BUCKET", "silver-telemetry")
    GOLD_BUCKET = os.getenv("GOLD_BUCKET", "gold-telemetry")

    # ETL Configurations
    INTERPOLATION_GAP_LIMIT_HOURS = int(os.getenv("INTERPOLATION_GAP_LIMIT_HOURS", "2"))
