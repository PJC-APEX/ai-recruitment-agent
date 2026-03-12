"""Chunking service using LangChain RecursiveCharacterTextSplitter."""

import logging
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for chunking text documents."""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """Initialize chunking service.
        
        Args:
            chunk_size: Maximum size of each chunk
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        self.logger = logger
    
    async def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        try:
            chunks = self.text_splitter.split_text(text)
            self.logger.info(f"Created {len(chunks)} chunks from text")
            return chunks
        except Exception as e:
            self.logger.error(f"Error chunking text: {str(e)}")
            raise Exception(f"Failed to chunk text: {str(e)}")
    
    def get_chunk_info(self) -> dict:
        """Get chunking configuration information.
        
        Returns:
            Dictionary with chunk configuration
        """
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap
        }
