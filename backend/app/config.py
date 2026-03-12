"""Application configuration management."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Azure OpenAI Configuration
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_model: str = "gpt-4"
    azure_openai_embedding_model: str = "text-embedding-ada-002"
    azure_openai_api_version: str = "2024-02-15-preview"
    
    # Application Settings
    app_name: str = "Resume Screening System"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Vector Database
    chroma_persist_directory: str = "./chroma_db"
    
    # File Upload
    max_upload_size: int = 10485760  # 10MB
    allowed_extensions: str = "pdf"
    
    # Chunking Configuration
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Retrieval Configuration
    top_k_results: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
