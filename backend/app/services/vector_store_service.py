"""Vector store service using ChromaDB."""

import logging
from typing import List, Dict, Any, Optional
import chromadb
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Service for managing ChromaDB vector store."""
    
    def __init__(self, persist_directory: str, embedding_service: EmbeddingService):
        """Initialize vector store service.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            embedding_service: Service for generating embeddings
        """
        self.persist_directory = persist_directory
        self.embedding_service = embedding_service
        self.logger = logger
        
        # Initialize ChromaDB persistent client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection
        self.collection_name = "resumes"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Resume embeddings collection"}
        )
        
        self.logger.info(f"Initialized vector store at {persist_directory}")
    
    async def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """Add documents to the vector store.
        
        Args:
            texts: List of text chunks
            metadatas: List of metadata dictionaries
            ids: List of unique document IDs
        """
        try:
            # Generate embeddings
            embeddings = await self.embedding_service.embed_documents(texts)
            
            # Add to collection
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            self.logger.info(f"Added {len(texts)} documents to vector store")
            
        except Exception as e:
            self.logger.error(f"Error adding documents to vector store: {str(e)}")
            raise Exception(f"Failed to add documents: {str(e)}")
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search for similar documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            Search results with documents, metadatas, and distances
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.embed_text(query)
            
            # Search collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata
            )
            
            self.logger.info(f"Found {len(results['documents'][0])} results for query")
            
            return {
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else [],
                "ids": results["ids"][0] if results["ids"] else []
            }
            
        except Exception as e:
            self.logger.error(f"Error searching vector store: {str(e)}")
            raise Exception(f"Failed to search: {str(e)}")
    
    def get_collection_count(self) -> int:
        """Get the number of documents in the collection.
        
        Returns:
            Number of documents
        """
        return self.collection.count()
    
    def delete_by_metadata(self, metadata_filter: Dict[str, Any]) -> None:
        """Delete documents by metadata filter.
        
        Args:
            metadata_filter: Metadata filter for deletion
        """
        try:
            self.collection.delete(where=metadata_filter)
            self.logger.info(f"Deleted documents matching filter: {metadata_filter}")
        except Exception as e:
            self.logger.error(f"Error deleting documents: {str(e)}")
            raise Exception(f"Failed to delete documents: {str(e)}")
    
    def get_all_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all documents in the collection.
        
        Returns:
            List of metadata dictionaries
        """
        try:
            results = self.collection.get()
            return results["metadatas"] if results["metadatas"] else []
        except Exception as e:
            self.logger.error(f"Error retrieving metadata: {str(e)}")
            return []
