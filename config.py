"""
Configuration Settings
Save as: backend/config.py
"""

from pydantic_settings import BaseSettings
from pathlib import Path
import os

class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/pdf_editor"
    
    # Redis (optional)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_ENABLED: bool = False
    
    # Storage paths
    UPLOAD_DIR: Path = Path("uploads")
    OUTPUT_DIR: Path = Path("outputs")
    THUMBNAIL_DIR: Path = Path("thumbnails")
    
    # File limits
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
    MAX_FILES_PER_USER: int = 100
    ALLOWED_EXTENSIONS: list = [".pdf"]
    
    # Session settings
    SESSION_EXPIRY: int = 21600  # 6 hours
    
    # Security
    SECRET_KEY: str = "change-this-in-production-use-strong-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS settings
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080"
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Initialize settings
settings = Settings()

# Create directories
for directory in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.THUMBNAIL_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

print(f"✅ Config loaded - Database: {settings.DATABASE_URL[:30]}...")