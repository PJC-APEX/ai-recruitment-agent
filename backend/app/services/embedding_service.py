"""Embedding service using an OpenAI-compatible embeddings API."""

import logging
import asyncio
import random
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
        api_version: str = "2024-02-15-preview",
        max_concurrency: int = 4,
        timeout_seconds: float = 60.0,
        max_retries: int = 5,
        retry_min_seconds: float = 1.0,
        retry_max_seconds: float = 20.0,
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
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self.max_retries = max(0, int(max_retries))
        self.retry_min_seconds = max(0.1, float(retry_min_seconds))
        self.retry_max_seconds = max(self.retry_min_seconds, float(retry_max_seconds))
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=endpoint,
            timeout=self.timeout_seconds,
            max_retries=0,
        )
        self.logger = logger
        self.max_concurrency = max(1, max_concurrency)
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    async def _create_embedding(self, text: str):
        """Call the provider with bounded exponential-backoff retries."""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return await self.client.embeddings.create(
                    model=self.model,
                    input=text,
                )
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                delay = min(
                    self.retry_max_seconds,
                    self.retry_min_seconds * (2 ** attempt),
                )
                delay = delay * (0.8 + random.random() * 0.4)
                self.logger.warning(
                    "Embedding request failed (attempt %d/%d, endpoint=%s): %s; retrying in %.1fs",
                    attempt + 1,
                    self.max_retries + 1,
                    self.endpoint,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
        raise last_error
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            async with self._semaphore:
                response = await self._create_embedding(text)
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
            async def embed_one(text: str) -> List[float]:
                async with self._semaphore:
                    response = await self._create_embedding(text)
                    return response.data[0].embedding

            # Bounded concurrency prevents a burst of uploads from creating an
            # unbounded number of provider requests.  Batch task creation also
            # avoids holding thousands of coroutine objects for a large PDF.
            embeddings = []
            batch_size = max(1, self.max_concurrency * 4)
            for start in range(0, len(texts), batch_size):
                embeddings.extend(
                    await asyncio.gather(
                        *(embed_one(text) for text in texts[start:start + batch_size])
                    )
                )
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
