"""
Moviroo AI Chatbot - Configuration
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    app_name: str = "Moviroo AI Chatbot"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    # Database
    database_url: str = "postgresql+asyncpg://postgres:1878@localhost:8001/Moviroo_DB_V2"

    # Embedding model
    embedding_model: str = "paraphrase-multilingual-mpnet-base-v2"
    embedding_dimension: int = 768

    # FAISS
    faiss_index_type: str = "IndexFlatIP"
    top_k_results: int = 5
    similarity_threshold: float = 0.45

    # RAG thresholds
    high_confidence_threshold: float = 0.82
    low_confidence_threshold: float = 0.55

    # LLM (Ollama)
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "mistral"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 400
    llm_timeout: float = 30.0

    # Paths
    models_dir: str = "models_data"
    data_dir: str = "data"
    log_file: str = "logs/app.log"
    log_level: str = "INFO"
    log_rotation: str = "10 MB"
    log_retention: str = "7 days"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    cors_allow_credentials: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Create required directories
for d in [settings.models_dir, settings.data_dir, "logs"]:
    os.makedirs(d, exist_ok=True)
