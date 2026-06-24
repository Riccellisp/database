import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database configuration environment variables
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "strongpassword123")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "serving_db")

# Detect if we should use PostgreSQL or fallback to SQLite for offline testing/development
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true" or os.getenv("DB_HOST") is not None

if USE_POSTGRES:
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    # Postgres engine parameters
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
        if engine.dialect.name == "postgresql":
            # If silver_telemetry is a BASE TABLE, drop it
            conn.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                          AND table_name = 'silver_telemetry' 
                          AND table_type = 'BASE TABLE'
                    ) THEN
                        DROP TABLE public.silver_telemetry CASCADE;
                    END IF;
                END $$;
            """))
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
