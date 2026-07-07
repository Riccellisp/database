import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database configurations
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "strongpassword123")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "13306")
    DB_NAME = os.getenv("DB_NAME", "serving_db")
    
    # Detect MySQL vs local SQLite fallback
    USE_MYSQL = os.getenv("USE_MYSQL", "false").lower() == "true" or os.getenv("DB_HOST") is not None
