from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.settings import settings

SQLALCHEMY_DATABASE_URL = settings.database_url

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=3,           # Keep a small resident pool (Supabase Session mode has strict limits)
    max_overflow=2,        # Allow up to 5 total connections (3 + 2) under burst load
    pool_recycle=300,      # Recycle connections every 5 min to avoid stale/timed-out connections
    pool_pre_ping=True,    # Test connections before use to detect dropped connections early
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
