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
    # Context-window safeguards (override with CONTEXT_* environment vars).
    context_window_tokens: int = 32768
    context_output_reserve_tokens: int = 2000
    max_user_message_tokens: int = 8000
    memory_sqlite_path: str = "./data/memories.sqlite"
    memory_enabled: bool = True
    memory_top_k: int = 5
    memory_collection_name: str = "user_memories"
    memory_min_confidence: float = 0.7
    
    # File Upload
    max_upload_size: int = 10485760  # 10MB
    allowed_extensions: str = "pdf"
    upload_data_directory: str = "./data/resumes"

    # Optional ARQ/Redis ingestion queue. Disabled by default so the local
    # quickstart remains usable without Redis; enable it in production with
    # INGESTION_QUEUE_ENABLED=true and REDIS_URL=redis://....
    redis_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )
    ingestion_queue_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("INGESTION_QUEUE_ENABLED", "ingestion_queue_enabled"),
    )
    ingestion_queue_name: str = "resume-ingestion"
    ingestion_worker_max_jobs: int = 4
    ingestion_embedding_concurrency: int = 4
    ingestion_embedding_batch_size: int = 16
    embedding_timeout_seconds: float = 60.0
    embedding_max_retries: int = 5
    embedding_retry_min_seconds: float = 1.0
    embedding_retry_max_seconds: float = 20.0
    ingestion_job_ttl_seconds: int = 86400
    ingestion_lock_ttl_seconds: int = 300
    ingestion_artifact_directory: str = "./data/ingestion"
    sync_thread_pool_workers: int = 8

    # Optional Langfuse observability for Agent/LLM/tool performance.
    # Disabled by default and configured through environment variables.
    langfuse_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("LANGFUSE_ENABLED", "langfuse_enabled"),
    )
    langfuse_public_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_PUBLIC_KEY", "langfuse_public_key"),
    )
    langfuse_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_SECRET_KEY", "langfuse_secret_key"),
    )
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        validation_alias=AliasChoices("LANGFUSE_HOST", "langfuse_host"),
    )
    langfuse_sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("LANGFUSE_SAMPLE_RATE", "langfuse_sample_rate"),
    )
    langfuse_capture_content: bool = Field(
        default=False,
        validation_alias=AliasChoices("LANGFUSE_CAPTURE_CONTENT", "langfuse_capture_content"),
    )
    
    # Chunking Configuration
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Retrieval Configuration
    top_k_results: int = 5

    # Optional Feishu bot integration.  These values are intentionally
    # optional so existing local/API deployments continue to work when the
    # Feishu bot is not configured.
    feishu_app_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FEISHU_APP_ID", "feishu_app_id"),
    )
    feishu_app_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FEISHU_APP_SECRET", "feishu_app_secret"),
    )
    feishu_verification_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "FEISHU_VERIFICATION_TOKEN", "feishu_verification_token"
        ),
    )
    feishu_encrypt_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FEISHU_ENCRYPT_KEY", "feishu_encrypt_key"),
    )
    feishu_api_base_url: str = Field(
        default="https://open.feishu.cn",
        validation_alias=AliasChoices("FEISHU_API_BASE_URL", "feishu_api_base_url"),
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        populate_by_name = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
