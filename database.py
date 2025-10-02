"""
Database Configuration - FIXED for SQLAlchemy 2.0+
Save as: backend/database.py
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from config import settings

# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def init_db():
    """Initialize database - create all tables"""
    from models import Base
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")

def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """Context manager for manual database operations"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def check_db_connection():
    """Check if database is accessible - FIXED for SQLAlchemy 2.0+"""
    try:
        db = SessionLocal()
        # Use text() wrapper for raw SQL in SQLAlchemy 2.0+
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False