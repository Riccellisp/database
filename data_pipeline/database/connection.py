import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database configuration environment variables
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "strongpassword123")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "13306")
DB_NAME = os.getenv("DB_NAME", "serving_db")

# Detect if we should use MySQL or fallback to SQLite for offline testing/development
USE_MYSQL = os.getenv("USE_MYSQL", "false").lower() == "true" or os.getenv("DB_HOST") is not None

if USE_MYSQL:
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    # MySQL engine parameters
    engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
else:
    # Local SQLite fallback for host-based integration testing
    sqlite_path = Path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "serving_database.db"))
    DATABASE_URL = f"sqlite:///{sqlite_path}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_sql_db():
    """
    Creates all tables if they do not exist.
    """
    from data_pipeline.database.models import SilverTelemetry, GoldEquipmentFeatures
    from sqlalchemy import text
    
    # 1. Run create_all first to ensure all physical tables exist
    Base.metadata.create_all(bind=engine)
    
    # 2. Drop silver_telemetry table and replace it with a view pointing to stg_silver_telemetry
    with engine.begin() as conn:
        if engine.dialect.name == "mysql":
            conn.execute(text("DROP TABLE IF EXISTS silver_telemetry;"))
            conn.execute(text("CREATE OR REPLACE VIEW silver_telemetry AS SELECT * FROM stg_silver_telemetry;"))
        else:
            # SQLite fallback (testing/offline dev)
            res = conn.execute(text("SELECT type FROM sqlite_master WHERE name='silver_telemetry';")).fetchone()
            if res and res[0] == "table":
                conn.execute(text("DROP TABLE silver_telemetry;"))
            conn.execute(text("CREATE VIEW IF NOT EXISTS silver_telemetry AS SELECT * FROM stg_silver_telemetry;"))

def get_db_session():
    """
    Context manager for database sessions.
    """
    session = SessionLocal()
    try:
        return session
    finally:
        pass
