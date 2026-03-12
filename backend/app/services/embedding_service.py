"""Embedding service using Azure OpenAI embeddings."""

import logging
from typing import List
from langchain_openai import AzureOpenAIEmbeddings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using Azure OpenAI."""
    
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        model: str = "text-embedding-ada-002",
        api_version: str = "2024-02-15-preview"
    ):
        """Initialize embedding service.
        
        Args:
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
            model: Embedding model deployment name
            api_version: Azure OpenAI API version
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.api_version = api_version
        self.embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=endpoint,
            api_key=api_key,
            model=model,
            api_version=api_version
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
            embedding = await self.embeddings.aembed_query(text)
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
            embeddings = await self.embeddings.aembed_documents(texts)
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
        # text-embedding-ada-002 produces 1536-dimensional vectors
        return 1536
