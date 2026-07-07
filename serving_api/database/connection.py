import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from serving_api.config import Config

# DB URL resolution
if Config.USE_MYSQL:
    DATABASE_URL = f"mysql+pymysql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
else:
    # Fallback to local SQLite file for offline testing / development
    sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "serving_database.db"))
    DATABASE_URL = f"sqlite:///{sqlite_path}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    FastAPI dependency yielding a database session and closing it
    once the request context finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
