"""
Moviroo AI Chatbot - Configuration Module
Handles all application settings and environment variables
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = Field(default="Moviroo AI Chatbot", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=4, env="API_WORKERS")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:1878@localhost:8001/Moviroo_DB_V2",
        env="DATABASE_URL",
        connect_args={"ssl": True}
    )
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    
    # AI Model Configuration
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        env="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=768, env="EMBEDDING_DIMENSION")
    faiss_index_type: str = Field(default="IndexFlatIP", env="FAISS_INDEX_TYPE")
    similarity_threshold: float = Field(default=0.45, env="SIMILARITY_THRESHOLD")
    top_k_results: int = Field(default=5, env="TOP_K_RESULTS")
    
    # Language Support
    supported_languages: str = Field(
        default="en,fr,ar,franco-arabic",
        env="SUPPORTED_LANGUAGES"
    )
    default_language: str = Field(default="en", env="DEFAULT_LANGUAGE")
    
    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30,
        env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/moviroo.log", env="LOG_FILE")
    log_rotation: str = Field(default="500 MB", env="LOG_ROTATION")
    log_retention: str = Field(default="30 days", env="LOG_RETENTION")
    
    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # Feedback & Learning
    auto_learning_enabled: bool = Field(default=True, env="AUTO_LEARNING_ENABLED")
    feedback_threshold: int = Field(default=4, env="FEEDBACK_THRESHOLD")
    min_confidence_score: float = Field(default=0.5, env="MIN_CONFIDENCE_SCORE")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # Paths
    data_dir: str = Field(default="data", env="DATA_DIR")
    models_dir: str = Field(default="models", env="MODELS_DIR")
    logs_dir: str = Field(default="logs", env="LOGS_DIR")
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def supported_languages_list(self) -> List[str]:
        """Parse supported languages from comma-separated string"""
        return [lang.strip() for lang in self.supported_languages.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Ensure directories exist
os.makedirs(settings.data_dir, exist_ok=True)
os.makedirs(settings.models_dir, exist_ok=True)
os.makedirs(settings.logs_dir, exist_ok=True)
