"""
Application Configuration
Centralized settings using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    Similar to Django settings but with type validation
    """
    
    # === APPLICATION ===
    APP_NAME: str = "Charro Bot API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # === API ===
    API_V1_STR: str = "/api/v1"
    
    # === CORS ===
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",  # React/Next.js frontend
        "http://localhost:8080",  # Vue frontend
        "http://127.0.0.1:3000",
    ]
    
    # === OLLAMA LLM ===
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_TIMEOUT: int = 30
    
    # === DATABASE ===
    DATABASE_URL: str = "sqlite:///./data/charro_bot.db"  # Default SQLite (mapped volume)
    # For PostgreSQL: "postgresql://user:password@localhost/dbname"
    
    # === SECURITY ===
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # === RAG/VECTOR STORE ===
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    class Config:
        env_file = ".env"  # Load from .env file
        case_sensitive = True


# Global settings instance
settings = Settings() 