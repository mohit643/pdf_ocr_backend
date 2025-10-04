"""
Configuration Settings
"""
from pydantic_settings import BaseSettings
from pathlib import Path
import os

class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # OAuth Settings
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    
    # JWT Settings
    SECRET_KEY: str = "change-this-in-production-use-strong-key"
    JWT_SECRET_KEY: str = "change-this-in-production-use-strong-key"  # Add this line
    ALGORITHM: str = "HS256"
    JWT_ALGORITHM: str = "HS256"  # Add this line
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_EXPIRATION_HOURS: int = 24
    
    # Storage paths
    UPLOAD_DIR: Path = Path("uploads")
    OUTPUT_DIR: Path = Path("outputs")
    THUMBNAIL_DIR: Path = Path("thumbnails")
    
    # File limits
    MAX_FILE_SIZE: int = 50 * 1024 * 1024
    MAX_FILES_PER_USER: int = 100
    ALLOWED_EXTENSIONS: list = [".pdf"]
    
    # Session settings
    SESSION_EXPIRY: int = 21600
    
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

print(f"✅ Config loaded - OAuth enabled")