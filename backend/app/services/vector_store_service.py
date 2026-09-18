"""Vector store service using ChromaDB."""

import logging
import asyncio
import threading
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
        # Protect synchronous writes within one process.  Cross-process writes
        # are serialized by the ingestion worker/queue in production.
        self._write_lock = threading.Lock()
        
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
            
            # Upsert makes retries safe when an ingestion job is resumed after
            # a worker interruption.  IDs are supplied by the caller and must
            # be deterministic for this guarantee to hold.
            await self.upsert_documents(
                texts=texts,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings,
            )
            
            self.logger.info(f"Added {len(texts)} documents to vector store")
            
        except Exception as e:
            self.logger.error(f"Error adding documents to vector store: {str(e)}")
            raise Exception(f"Failed to add documents: {str(e)}")

    async def upsert_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """Upsert documents without blocking the event loop.

        Embedding generation remains asynchronous; Chroma's local persistent
        client is synchronous and is therefore executed in the default thread
        pool.  Upsert, rather than add, makes a retried job idempotent.
        """
        try:
            vectors = embeddings
            if vectors is None:
                vectors = await self.embedding_service.embed_documents(texts)
            await asyncio.to_thread(
                self._upsert_sync,
                texts,
                metadatas,
                ids,
                vectors,
            )
            self.logger.info(f"Upserted {len(texts)} documents to vector store")
        except Exception as e:
            self.logger.error(f"Error upserting documents to vector store: {str(e)}")
            raise Exception(f"Failed to upsert documents: {str(e)}")

    def _upsert_sync(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        embeddings: List[List[float]],
    ) -> None:
        with self._write_lock:
            self.collection.upsert(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
    
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
            
            # Chroma's local client is synchronous; do not block FastAPI while
            # it performs disk/SQLite work.
            results = await asyncio.to_thread(
                self._query_sync,
                query_embedding,
                top_k,
                filter_metadata,
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

    def _query_sync(
        self,
        query_embedding: List[float],
        top_k: int,
        filter_metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata,
        )

    async def get_by_metadata_async(
        self,
        filter_metadata: Dict[str, Any],
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(self.get_by_metadata, filter_metadata, limit)

    async def get_all_metadata_async(self) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self.get_all_metadata)

    async def get_collection_count_async(self) -> int:
        return await asyncio.to_thread(self.get_collection_count)

    def get_by_metadata(
        self,
        filter_metadata: Dict[str, Any],
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieve stored documents directly by metadata, without embeddings."""
        try:
            kwargs = {
                "where": filter_metadata,
                "include": ["documents", "metadatas"],
            }
            if limit is not None:
                kwargs["limit"] = limit
            results = self.collection.get(**kwargs)
            return {
                "documents": results.get("documents") or [],
                "metadatas": results.get("metadatas") or [],
                "ids": results.get("ids") or [],
            }
        except Exception as e:
            self.logger.error(f"Error retrieving documents by metadata: {str(e)}")
            raise Exception(f"Failed to retrieve documents by metadata: {str(e)}")
    
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
            with self._write_lock:
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
