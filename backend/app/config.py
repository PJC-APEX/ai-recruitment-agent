"""Application configuration management."""

from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI-compatible chat model configuration.
    # The legacy attribute names are kept because existing dependencies use them.
    azure_openai_endpoint: str = Field(
        validation_alias=AliasChoices(
            "OPENAI_BASE_URL", "AZURE_OPENAI_ENDPOINT", "azure_openai_endpoint"
        )
    )
    azure_openai_api_key: str = Field(
        validation_alias=AliasChoices(
            "OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "azure_openai_api_key"
        )
    )
    azure_openai_model: str = Field(
        default="deepseek-chat",
        validation_alias=AliasChoices(
            "OPENAI_MODEL", "AZURE_OPENAI_MODEL", "azure_openai_model"
        )
    )
    azure_openai_embedding_model: str = Field(
        default="text-embedding-v3",
        validation_alias=AliasChoices(
            "EMBEDDING_MODEL",
            "AZURE_OPENAI_EMBEDDING_MODEL",
            "azure_openai_embedding_model",
        )
    )
    azure_openai_api_version: str = "2024-02-15-preview"

    # Embedding service can use a separate provider/key from the chat model.
    embedding_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBEDDING_API_KEY", "embedding_api_key"),
    )
    embedding_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBEDDING_BASE_URL", "embedding_base_url"),
    )
    
    # Application Settings
    app_name: str = "Resume Screening System"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Vector Database
    chroma_persist_directory: str = "./chroma_db"

    # LangGraph short-term conversation checkpoint storage
    checkpoint_db_path: str = "./data/checkpoints.sqlite"
    short_term_max_messages: int = 20
    
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
        populate_by_name = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
