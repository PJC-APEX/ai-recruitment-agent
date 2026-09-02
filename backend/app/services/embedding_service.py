"""Embedding service using an OpenAI-compatible embeddings API."""

import logging
from typing import List
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using an OpenAI-compatible API."""
    
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        model: str = "text-embedding-v3",
        api_version: str = "2024-02-15-preview"
    ):
        """Initialize embedding service.
        
        Args:
            api_key: OpenAI-compatible API key
            endpoint: OpenAI-compatible API base URL
            model: Embedding model name
            api_version: Retained for compatibility with existing callers
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.api_version = api_version
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=endpoint,
        )
        self.logger = logger
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            embedding = response.data[0].embedding
            self.logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}")
            raise Exception(f"Failed to generate embedding: {str(e)}")
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            # DashScope's OpenAI-compatible endpoint is more reliable when
            # each document is sent as a string rather than as a batch list.
            embeddings = []
            for text in texts:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=text,
                )
                embeddings.append(response.data[0].embedding)
            self.logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {str(e)}")
            raise Exception(f"Failed to generate embeddings: {str(e)}")
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors.
        
        Returns:
            Embedding dimension
        """
        # DashScope text-embedding-v3 produces 1024-dimensional vectors by default.
        return 1024
