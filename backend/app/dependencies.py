"""Dependency injection for FastAPI routes."""

from functools import lru_cache
from app.config import get_settings, Settings
from app.services.vector_store_service import VectorStoreService
from app.services.embedding_service import EmbeddingService
from app.services.resume_parser import ResumeParserService
from app.services.chunking_service import ChunkingService
from app.services.ranking_service import RankingService
from app.llm.llm_client import LLMClient
from app.rag.retrieval_pipeline import RetrievalPipeline
from app.rag.scoring_pipeline import ScoringPipeline
from app.agents.recruitment_agent import RecruitmentAgent
from app.agents.tools import (
    create_search_candidates_tool,
    create_list_all_candidates_tool,
    create_get_candidate_details_tool
)


@lru_cache()
def get_llm_client() -> LLMClient:
    """Get cached LLM client instance."""
    settings = get_settings()
    return LLMClient(
        api_key=settings.azure_openai_api_key,
        endpoint=settings.azure_openai_endpoint,
        model=settings.azure_openai_model,
        api_version=settings.azure_openai_api_version
    )


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Get cached embedding service instance."""
    settings = get_settings()
    return EmbeddingService(
        api_key=settings.azure_openai_api_key,
        endpoint=settings.azure_openai_endpoint,
        model=settings.azure_openai_embedding_model,
        api_version=settings.azure_openai_api_version
    )


@lru_cache()
def get_vector_store_service() -> VectorStoreService:
    """Get cached vector store service instance."""
    settings = get_settings()
    embedding_service = get_embedding_service()
    return VectorStoreService(
        persist_directory=settings.chroma_persist_directory,
        embedding_service=embedding_service
    )


@lru_cache()
def get_resume_parser_service() -> ResumeParserService:
    """Get cached resume parser service instance."""
    llm_client = get_llm_client()
    return ResumeParserService(llm_client=llm_client)


@lru_cache()
def get_chunking_service() -> ChunkingService:
    """Get cached chunking service instance."""
    settings = get_settings()
    return ChunkingService(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap
    )


@lru_cache()
def get_ranking_service() -> RankingService:
    """Get cached ranking service instance."""
    llm_client = get_llm_client()
    return RankingService(llm_client=llm_client)


@lru_cache()
def get_retrieval_pipeline() -> RetrievalPipeline:
    """Get cached retrieval pipeline instance."""
    vector_store = get_vector_store_service()
    settings = get_settings()
    return RetrievalPipeline(
        vector_store=vector_store,
        top_k=settings.top_k_results
    )


@lru_cache()
def get_scoring_pipeline() -> ScoringPipeline:
    """Get cached scoring pipeline instance."""
    llm_client = get_llm_client()
    return ScoringPipeline(llm_client=llm_client)


@lru_cache()
def get_recruitment_agent() -> RecruitmentAgent:
    """Get cached recruitment agent instance.
    
    Following Dependency Inversion Principle:
    - Agent depends on abstractions (tools, LLM) not concrete implementations
    - Easy to add new tools without modifying this function
    """
    llm_client = get_llm_client()
    retrieval_pipeline = get_retrieval_pipeline()
    settings = get_settings()
    
    # Create tools (following Open/Closed Principle - easy to add more)
    tools = [
        create_list_all_candidates_tool(retrieval_pipeline),
        create_search_candidates_tool(retrieval_pipeline),
        create_get_candidate_details_tool(retrieval_pipeline)
    ]
    
    # Create and return agent
    return RecruitmentAgent(
        llm_client=llm_client,
        tools=tools,
        max_iterations=15,  # Allow more iterations for complex multi-candidate comparisons
        verbose=settings.debug  # Show agent reasoning in debug mode
    )
